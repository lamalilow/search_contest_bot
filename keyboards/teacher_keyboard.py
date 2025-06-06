from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

async def create_teacher_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Список конкурсов")],
            [KeyboardButton(text="Добавить участие")],
            [KeyboardButton(text="Настройки")]
        ],
        resize_keyboard=True
    )
    return keyboard