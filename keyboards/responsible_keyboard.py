from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

async def create_responsible_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Список конкурсов"), KeyboardButton(text="Список участников")],
            [KeyboardButton(text="Добавить участие")],
            [KeyboardButton(text="Настройки")]
        ],
        resize_keyboard=True
    )
    return keyboard