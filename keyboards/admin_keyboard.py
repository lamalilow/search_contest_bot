from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


async def create_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить конкурс"), KeyboardButton(text="Список конкурсов"), ],
            [KeyboardButton(text='Удалить конкурсы')],
            [KeyboardButton(text="Добавить преподавателя"), KeyboardButton(text="Добавить администратора"),
             KeyboardButton(text="Добавить ответственного")],
            [KeyboardButton(text="Список пользователей")],
            [KeyboardButton(text="Заполнить лист самообследования")],
            [KeyboardButton(text="Настройки")]
        ],
        resize_keyboard=True
    )
    return keyboard
