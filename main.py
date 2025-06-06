from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
import os
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat, CallbackQuery

from dotenv import load_dotenv

from config import logger
from middlewares.role_middleware import RoleMiddleware
from handlers.user import start_handler, contact_handler, name_handler
from handlers.admin import admin_user_handlers, admin_contest_handlers, admin_watcher_handler
from handlers.contest import responsible_handlers
from handlers.watcher import watcher_handler

from handlers.user import user_handlers
from handlers.contest import contest_handlers
from handlers.contest.contest_participation_handler import router as contest_participation_router
from services.scheduler import start_scheduler  # Импортируем планировщик

# Создаем общий роутер для админских обработчиков
from aiogram import Router
admin_router = Router()
admin_router.include_router(admin_user_handlers.router)
admin_router.include_router(admin_contest_handlers.router)
admin_router.include_router(admin_watcher_handler.router)  # Добавляем роутер для обработчика add_watcher

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

# Добавляем middleware для роутера участия в конкурсах
contest_participation_router.message.middleware(RoleMiddleware(allowed_roles=["teacher", "responsible", "admin", "watcher"]))
contest_participation_router.callback_query.middleware(RoleMiddleware(allowed_roles=["teacher", "responsible", "admin", "watcher"]))

user_router = user_handlers.router
user_router.message.middleware(RoleMiddleware(allowed_roles=["teacher", "responsible", "admin"]))
user_router.callback_query.middleware(RoleMiddleware(allowed_roles=["teacher", "responsible", "admin"]))

# Роутер для watcher
watcher_router = watcher_handler.router
watcher_router.message.middleware(RoleMiddleware(allowed_roles=["watcher"]))

# Подключаем роутеры к диспетчеру
dp.include_router(start_handler.router)
dp.include_router(contact_handler.router)
dp.include_router(user_handlers.router)
dp.include_router(name_handler.router)
dp.include_router(admin_router)  # Используем новый admin_router
dp.include_router(responsible_handlers.router)
dp.include_router(contest_handlers.router)
dp.include_router(contest_participation_router)  # Добавляем роутер участия в конкурсах
dp.include_router(watcher_router)


async def main():
    # Устанавливаем команды по умолчанию для всех пользователей
    await set_default_commands(bot)
    
    # Запуск планировщика
    start_scheduler(bot)
    await dp.start_polling(bot)


async def set_default_commands(bot: Bot):
    """Устанавливает команды бота для разных ролей пользователей"""
    # Команды по умолчанию для всех пользователей
    default_commands = [
        BotCommand(command="start", description="Начать работу с ботом или перезапустить"),
        BotCommand(command="contest", description="Заполнить участие в конкурсе"),
    ]
    
    # Команды для администраторов
    admin_commands = [
        BotCommand(command="start", description="Начать работу с ботом или перезапустить"),
        BotCommand(command="contest", description="Заполнить участие в конкурсе"),
        BotCommand(command="add_watcher", description="Добавить роль наблюдателя"),
        BotCommand(command="remove_role", description="Удалить роль у пользователя"),
    ]
    
    # Команды для наблюдателей (watcher)
    watcher_commands = [
        BotCommand(command="start", description="Начать работу с ботом или перезапустить"),
        BotCommand(command="watcher", description="Посмотреть доступные команды для наблюдателей"),
        BotCommand(command="get_report", description="Получить отчет за период"),
        BotCommand(command="contest", description="Заполнить участие в конкурсе"),
    ]
    
    # Установка команд по умолчанию
    await bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())
    
    # Находим всех пользователей с ролью watcher и устанавливаем им специальные команды
    from services.database import db
    
    watcher_users = list(db.users.find({
        "$or": [
            {"role": "watcher"},
            {"role": {"$in": ["watcher"]}}
        ]
    }))
    
    logger.info(f"Найдено {len(watcher_users)} пользователей с ролью watcher")
    
    # Устанавливаем команды для каждого watcher
    for user in watcher_users:
        try:
            await bot.set_my_commands(
                watcher_commands,
                scope=BotCommandScopeChat(chat_id=user["telegram_id"])
            )
        except Exception as e:
            logger.error(f"Ошибка при установке команд для watcher {user['telegram_id']}: {e}")
    
    # Находим всех администраторов и устанавливаем им специальные команды
    admin_users = list(db.users.find({
        "$or": [
            {"role": "admin"},
            {"role": {"$in": ["admin"]}}
        ]
    }))
    
    logger.info(f"Найдено {len(admin_users)} пользователей с ролью admin")
    
    # Устанавливаем команды для каждого администратора
    for user in admin_users:
        try:
            await bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=user["telegram_id"])
            )
        except Exception as e:
            logger.error(f"Ошибка при установке команд для admin {user['telegram_id']}: {e}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
