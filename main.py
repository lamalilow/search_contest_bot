from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import os

from dotenv import load_dotenv

from middlewares.role_middleware import RoleMiddleware
from handlers import start_handler, contact_handler, name_handler, admin_handlers, responsible_handlers, \
    contest_handlers, user_handlers
from services.scheduler import start_scheduler  # Импортируем планировщик

admin_router = admin_handlers.router

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не указан BOT_TOKEN в переменных окружения.")

bot = Bot(token=BOT_TOKEN)  # Инициализируем бота

# Диспетчер
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

admin_router.message.middleware(RoleMiddleware(allowed_roles=["admin"]))
admin_router.callback_query.middleware(RoleMiddleware(allowed_roles=["admin"]))

responsible_router = responsible_handlers.router
responsible_router.message.middleware(RoleMiddleware(allowed_roles=["responsible", "admin"]))

contest_router = contest_handlers.router
contest_router.message.middleware(RoleMiddleware(allowed_roles=["teacher", "responsible", "admin"]))

user_router = user_handlers.router
user_router.message.middleware(RoleMiddleware(allowed_roles=["teacher", "responsible", "admin"]))
user_router.callback_query.middleware(RoleMiddleware(allowed_roles=["teacher", "responsible", "admin"]))

# Подключаем роутеры к диспетчеру
dp.include_router(start_handler.router)
dp.include_router(contact_handler.router)
dp.include_router(user_handlers.router)
dp.include_router(name_handler.router)
dp.include_router(admin_handlers.router)
dp.include_router(responsible_handlers.router)
dp.include_router(contest_handlers.router)


async def main():
    # Запуск планировщика
    start_scheduler(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
