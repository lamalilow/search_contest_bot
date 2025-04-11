from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from datetime import datetime
import io
from aiogram.types import BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import calendar
from bson import ObjectId
import logging

from utils.self_assessment_utils import generate_monthly_report, create_excel_report
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
    self_assessments = list(db.self_assessments.find())
    
    for assessment in self_assessments:
        # Получаем дату создания записи
        created_at = assessment.get("created_at")
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
        await message.answer("В базе данных нет записей самообследования для генерации отчета.")
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
    data, images = await generate_monthly_report(month, year)
    
    if not data:
        await callback.message.answer("За выбранный период нет данных для отчета.")
        await callback.answer()
        return
    
    # Создаем Excel файл
    excel_data = await create_excel_report(data, images)
    
    # Отправляем файл
    await callback.message.answer_document(
        document=BufferedInputFile(
            excel_data,
            filename=f"report_{year}_{month:02d}.xlsx"
        ),
        caption=f"Отчет за {RUSSIAN_MONTHS[month]} {year}"
    )
    
    await callback.answer()

@router.callback_query(ReportState.selecting_month, F.data == "cancel_report")
async def cancel_report(callback: CallbackQuery, state: FSMContext):
    """Отмена выбора месяца для отчета"""
    await state.clear()
    await callback.message.edit_text("Генерация отчета отменена")
    await callback.answer() 