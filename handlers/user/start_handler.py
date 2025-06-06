from aiogram import Router, types
from aiogram.filters import Command
from services.database import users_col
from keyboards.phone_keyboard import create_phone_keyboard
from utils.role_utils import send_role_keyboard

# Создаем роутер
router = Router()

# Хэндлер команды /start
@router.message(Command("start"))
async def start_handler(message: types.Message):
    user = users_col.find_one({"telegram_id": message.from_user.id})
    if user and user.get("phone"):
        await send_role_keyboard(message.bot, message.from_user.id, user.get("role"))
    else:
        phone_keyboard = create_phone_keyboard()
        await message.answer("Добро пожаловать! Для начала отправьте свой номер телефона.", reply_markup=phone_keyboard)