from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.database import users_col
from utils.role_utils import send_role_keyboard

router = Router()

# Переменная для отслеживания состояния изменения имени
editing_name = {}


# Хэндлер для настроек
@router.message(lambda message: message.text == "Настройки")
async def settings_handler(message: types.Message):
    # Получаем данные пользователя из базы данных
    user = users_col.find_one({"telegram_id": message.from_user.id})
    if not user:
        await message.answer("Пользователь не найден.")
        return

    # Определяем текущее состояние уведомлений
    notifications_enabled = user.get("notifications_enabled", True)

    # Создаем inline-клавиатуру для настроек
    if notifications_enabled:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отключить уведомления", callback_data="disable_notifications")],
            [InlineKeyboardButton(text="Редактировать имя", callback_data="edit_name")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Включить уведомления", callback_data="enable_notifications")],
            [InlineKeyboardButton(text="Редактировать имя", callback_data="edit_name")]
        ])

    await message.answer("Настройки:", reply_markup=keyboard)


# Хэндлер для обработки нажатия на "Редактировать имя"
@router.callback_query(lambda query: query.data == "edit_name")
async def edit_name_handler(query: types.CallbackQuery):
    # Устанавливаем флаг, что пользователь находится в процессе изменения имени
    editing_name[query.from_user.id] = True

    # Запрашиваем у пользователя новое имя
    await query.message.answer("Введите новое имя:")

    # Закрываем callback_query
    await query.answer()


# Хэндлер для обработки ввода нового имени
@router.message(lambda message: editing_name.get(message.from_user.id, False))
async def process_new_name(message: types.Message):
    # Убираем флаг изменения имени
    editing_name[message.from_user.id] = False

    # Проверяем, что пользователь существует
    user = users_col.find_one({"telegram_id": message.from_user.id})
    if not user:
        await message.answer("Пользователь не найден.")
        return

    # Обновляем имя пользователя в базе данных
    new_name = message.text.strip()  # Убираем лишние пробелы
    users_col.update_one(
        {"telegram_id": message.from_user.id},
        {"$set": {"full_name": new_name}}
    )

    await message.answer(f"Имя успешно изменено на: {new_name}.",
                         reply_markup=await send_role_keyboard(message.bot, message.from_user.id, user.get("role")))


# Хэндлер для обработки нажатия на "Отключить уведомления"
@router.callback_query(lambda query: query.data == "disable_notifications")
async def disable_notifications_handler(query: types.CallbackQuery):
    # Обновляем статус уведомлений в базе данных
    users_col.update_one(
        {"telegram_id": query.from_user.id},
        {"$set": {"notifications_enabled": False}}
    )

    await query.message.answer("Уведомления отключены.",
                             )
    await query.answer()


# Хэндлер для обработки нажатия на "Включить уведомления"
@router.callback_query(lambda query: query.data == "enable_notifications")
async def enable_notifications_handler(query: types.CallbackQuery):
    # Обновляем статус уведомлений в базе данных
    users_col.update_one(
        {"telegram_id": query.from_user.id},
        {"$set": {"notifications_enabled": True}}
    )

    await query.message.answer("Уведомления включены.",
                               )
    await query.answer()
