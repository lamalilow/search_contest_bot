from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from services.database import db
from config import logger


class RoleMiddleware(BaseMiddleware):
    def __init__(self, allowed_roles: list[str]):
        super().__init__()
        self.allowed_roles = allowed_roles

    async def __call__(self, handler, event, data: dict):
        # Специальная обработка для callback с "cancel" - позволяет всем пользователям отменять действия
        if isinstance(event, CallbackQuery) and event.data == "cancel":
            logger.debug(f"Пропускаем проверку прав для кнопки отмены, пользователь: {event.from_user.id}")
            return await handler(event, data)
        
        # Определяем ID пользователя в зависимости от типа события
        if isinstance(event, Message):
            user_id = event.from_user.id
            answer_method = event.answer
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            # Для обычных уведомлений, не всплывающих окон
            answer_method = lambda text: event.answer(text, show_alert=False)
        else:
            # Если тип события неизвестен, пропускаем проверку
            logger.warning(f"Неизвестный тип события в middleware: {type(event)}")
            return await handler(event, data)

        # Находим пользователя в базе данных
        user = db.users.find_one({"telegram_id": user_id})

        if not user:
            await answer_method("Вы не зарегистрированы в системе.")
            return

        # Получаем роль пользователя
        user_role = user.get("role")
        
        logger.debug(f"Проверка прав пользователя {user_id}: роль {user_role}, необходимые роли {self.allowed_roles}")

        # Проверяем, является ли роль массивом или строкой
        if isinstance(user_role, list):
            # Если роль — массив, проверяем пересечение с разрешенными ролями
            if any(role in self.allowed_roles for role in user_role):
                return await handler(event, data)
        elif isinstance(user_role, str):
            # Если роль — строка, проверяем её наличие в разрешенных ролях
            if user_role in self.allowed_roles:
                return await handler(event, data)

        # Если роль не найдена или не соответствует разрешенным ролям
        await answer_method("У вас нет прав для выполнения этого действия.")
        return