import hashlib

from aiogram import Router, types
from services.database import users_col

# Создаем роутер
router = Router()

# Функция для хеширования номера телефона
def hash_phone_number(phone_number: str) -> str:
    # Используем SHA-256 для хеширования
    return hashlib.sha256(phone_number.encode()).hexdigest()

# Хэндлер для получения контакта (номер телефона)
@router.message(lambda message: message.contact is not None)
async def contact_handler(message: types.Message):
    if not message.contact or message.contact.user_id != message.from_user.id:
        await message.answer("Пожалуйста, отправьте свой собственный номер телефона.")
        return

    # Хешируем номер телефона
    hashed_phone = hash_phone_number(message.contact.phone_number)

    # Обновляем данные пользователя в базе данных
    users_col.update_one(
        {"telegram_id": message.from_user.id},
        {"$set": {"phone": hashed_phone, "role": "teacher", "notifications_enabled": True}},
        upsert=True
    )

    await message.answer("Спасибо! Теперь введите ваше полное имя (ФИО).")