from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from datetime import datetime
import io
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import calendar
from bson import ObjectId
import logging

from utils.contest_utils import generate_contest_report, create_contest_excel_report, create_contest_html_report
from services.database import db

# Настраиваем логгер
logger = logging.getLogger(__name__)

router = Router()

# Словарь с названиями месяцев на русском языке
RUSSIAN_MONTHS = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь"
}

class ReportState(StatesGroup):
    """Состояния для процесса получения отчета"""
    selecting_month = State()

@router.message(Command("get_report"))
async def cmd_get_report(message: Message, state: FSMContext):
    """Обработчик команды /get_report для получения отчета за выбранный месяц"""
    # Проверяем, есть ли у пользователя роль watcher
    user = db.users.find_one({"telegram_id": message.from_user.id})
    
    # Получаем роли пользователя
    user_roles = user.get("role") if user else None
    
    # Проверяем, есть ли роль watcher
    has_watcher_role = False
    if isinstance(user_roles, list):
        has_watcher_role = "watcher" in user_roles
    elif isinstance(user_roles, str):
        has_watcher_role = user_roles == "watcher"
    
    if not user or not has_watcher_role:
        await message.answer("У вас нет прав для получения отчетов.")
        return
    
    # Получаем уникальные месяцы и годы из записей самообследования
    available_months = set()
    
    # Получаем все записи самообследования
    participations = list(db.contest_participations.find())
    
    for part in participations:
        # Получаем дату создания записи
        created_at = part.get("created_at")
        if created_at:
            # Преобразуем строку в объект datetime, если это строка
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except ValueError:
                    continue
            
            # Добавляем месяц и год в множество
            available_months.add((created_at.year, created_at.month))
    
    if not available_months:
        await message.answer("В базе данных нет записей для генерации отчета.")
        return
    
    # Сортируем месяцы по убыванию (от новых к старым)
    available_months = sorted(available_months, reverse=True)
    
    # Создаем клавиатуру с доступными месяцами
    keyboard = []
    row = []
    
    for year, month in available_months:
        # Получаем название месяца на русском языке
        month_name = RUSSIAN_MONTHS.get(month, f"Месяц {month}")
        
        # Добавляем кнопку с месяцем и годом
        row.append({
            "text": f"{month_name} {year}",
            "callback_data": f"report_{year}_{month}"
        })
        
        # После каждых 2 кнопок или в конце списка, добавляем строку в клавиатуру
        if len(row) == 2 or (year, month) == available_months[-1]:
            keyboard.append(row)
            row = []
    
    # Добавляем кнопку отмены
    keyboard.append([{"text": "Отмена", "callback_data": "cancel_report"}])
    
    await state.set_state(ReportState.selecting_month)
    await message.answer(
        "Выберите месяц, за который нужно получить отчет:",
        reply_markup={"inline_keyboard": keyboard}
    )

@router.callback_query(F.data.startswith("report_"))
async def process_month_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора месяца для отчета"""
    # Получаем год и месяц из callback_data
    _, year, month = callback.data.split("_")
    year = int(year)
    month = int(month)
    
    # Получаем данные и изображения
    data, images = await generate_contest_report(month, year)
    
    if not data:
        await callback.message.answer("За выбранный период нет данных для отчета.")
        await callback.answer()
        return
    
    # Создаем Excel файл
    excel_data = await create_contest_excel_report(data, images)
    
    # Создаем HTML файл
    html_report = await create_contest_html_report(data, images)
    
    # Отправляем Excel файл
    await callback.message.answer_document(
        document=BufferedInputFile(
            excel_data,
            filename=f"contest_report_{year}_{month:02d}.xlsx"
        ),
        caption=f"Отчет по конкурсам за {RUSSIAN_MONTHS[month]} {year} (Excel)"
    )
    
    # Отправляем HTML файл
    await callback.message.answer_document(
        document=BufferedInputFile(
            html_report.encode('utf-8'),
            filename=f"contest_report_{year}_{month:02d}.html"
        ),
        caption=f"Отчет по конкурсам за {RUSSIAN_MONTHS[month]} {year} (HTML с возможностью сортировки)"
    )
    
    await callback.answer()

@router.callback_query(ReportState.selecting_month, F.data == "cancel_report")
async def cancel_report(callback: CallbackQuery, state: FSMContext):
    """Отмена выбора месяца для отчета"""
    await state.clear()
    await callback.message.edit_text("Генерация отчета отменена")
    await callback.answer()

@router.message(Command("watcher"))
async def cmd_watcher(message: Message):
    """Обработчик команды /watcher для отображения доступных команд наблюдателя"""
    # Проверяем, есть ли у пользователя роль watcher
    user = db.users.find_one({"telegram_id": message.from_user.id})
    
    # Получаем роли пользователя
    user_roles = user.get("role") if user else None
    
    # Проверяем, есть ли роль watcher
    has_watcher_role = False
    if isinstance(user_roles, list):
        has_watcher_role = "watcher" in user_roles
    elif isinstance(user_roles, str):
        has_watcher_role = user_roles == "watcher"
    
    if not user or not has_watcher_role:
        await message.answer("У вас нет прав для использования команд наблюдателя.")
        return
    
    # Отображаем доступные команды для наблюдателя
    await message.answer(
        "🔍 <b>Доступные команды наблюдателя:</b>\n\n"
        "/get_report - Получить отчет по конкурсам за выбранный месяц\n",
        parse_mode="HTML"
    )

