from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import logger
from services.database import users_col


async def show_user_list(message: types.Message, role: str):
    users = list(users_col.find({"full_name": {"$exists": True}}).sort("full_name", 1))
    if not users:
        await message.answer("Пользователи не найдены.")
        return

    user_dict = {}
    for user in users:
        if user.get("full_name"):
            first_letter = user["full_name"][0].upper()
            if first_letter not in user_dict:
                user_dict[first_letter] = []
            user_dict[first_letter].append(user)

    letters = sorted(user_dict.keys())
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    row = []
    for letter in letters:
        row.append(InlineKeyboardButton(text=letter, callback_data=f"letter_{letter}_{role}"))
        logger.info(f'letter_{letter}_{role}')
        if len(row) == 5:
            keyboard.inline_keyboard.append(row)
            row = []
    if row:
        keyboard.inline_keyboard.append(row)
    
    # Добавляем кнопку "Показать всех" внизу клавиатуры
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="Показать всех", callback_data=f"show_all_users_{role}")])

    await message.answer("Выберите первую букву фамилии пользователя или нажмите 'Показать всех':", reply_markup=keyboard)
