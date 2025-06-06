from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from services.database import db
from utils.role_utils import send_role_keyboard
from keyboards.event_type_keyboard import get_event_type_keyboard_with_pagination
from handlers.contest.contest_participation_handler import cmd_contest

router = Router()

# Переменная для отслеживания состояния изменения имени
editing_name = {}


# Хэндлер для настроек
@router.message(lambda message: message.text == "Настройки")
async def settings_handler(message: types.Message):
    # Получаем данные пользователя из базы данных
    user = db.users.find_one({"telegram_id": message.from_user.id})
    if not user:
        await message.answer("Пользователь не найден.")
        return

    # Определяем текущее состояние уведомлений
    notifications_enabled = user.get("notifications_enabled", True)

    # Создаем inline-клавиатуру для настроек
    if notifications_enabled:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отключить уведомления", callback_data="disable_notifications")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Включить уведомления", callback_data="enable_notifications")]
        ])

    await message.answer("Настройки:", reply_markup=keyboard)








# Хэндлер для включения уведомлений
@router.callback_query(lambda query: query.data == "enable_notifications")
async def enable_notifications_handler(query: types.CallbackQuery):
    # Обновляем настройки уведомлений в базе данных
    db.users.update_one(
        {"telegram_id": query.from_user.id},
        {"$set": {"notifications_enabled": True}}
    )

    # Получаем роль пользователя
    user = db.users.find_one({"telegram_id": query.from_user.id})
    user_role = user.get("role")

    await query.message.edit_text("Уведомления включены.")
    await send_role_keyboard(query.bot, query.from_user.id, user_role)
    await query.answer()


# Хэндлер для отключения уведомлений
@router.callback_query(lambda query: query.data == "disable_notifications")
async def disable_notifications_handler(query: types.CallbackQuery):
    # Обновляем настройки уведомлений в базе данных
    db.users.update_one(
        {"telegram_id": query.from_user.id},
        {"$set": {"notifications_enabled": False}}
    )

    # Получаем роль пользователя
    user = db.users.find_one({"telegram_id": query.from_user.id})
    user_role = user.get("role")

    await query.message.edit_text("Уведомления отключены.")
    await send_role_keyboard(query.bot, query.from_user.id, user_role)
    await query.answer()


# Хэндлер для кнопки "Добавить участие"
@router.message(lambda message: message.text == "Добавить участие")
async def contest_participation_handler(message: types.Message, state: FSMContext):
    await cmd_contest(message, state)
