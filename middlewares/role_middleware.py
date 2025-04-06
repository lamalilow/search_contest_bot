from aiogram import BaseMiddleware
from aiogram.types import Message
from services.database import users_col


class RoleMiddleware(BaseMiddleware):
    def __init__(self, allowed_roles: list[str]):
        super().__init__()
        self.allowed_roles = allowed_roles

    async def __call__(self, handler, event: Message, data: dict):
        # Находим пользователя в базе данных
        user = users_col.find_one({"telegram_id": event.from_user.id})

        if not user:
            await event.answer("Вы не зарегистрированы в системе.")
            return

        # Получаем роль пользователя
        user_role = user.get("role")

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
        await event.answer("У вас нет прав для выполнения этого действия.")