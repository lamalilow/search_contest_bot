from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
import os
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat, CallbackQuery

from dotenv import load_dotenv

from config import logger
from middlewares.role_middleware import RoleMiddleware
from handlers.user import start_handler, contact_handler, name_handler
from handlers.admin import admin_user_handlers, admin_contest_handlers
from handlers.contest import responsible_handlers
from handlers.watcher import watcher_handler
from handlers.admin import admin_handlers
from handlers.user import user_handlers
from handlers.contest import contest_handlers
from handlers.contest import self_assessment_handler
from handlers.admin import admin_activity_types_handler
from handlers.admin.admin_activity_types_handler import router as admin_activity_types_router
from services.scheduler import start_scheduler  # Импортируем планировщик

# Создаем общий роутер для админских обработчиков
from aiogram import Router
admin_router = Router()
admin_router.include_router(admin_user_handlers.router)
admin_router.include_router(admin_contest_handlers.router)
admin_router.include_router(admin_activity_types_router)  # Добавляем роутер для управления видами деятельности

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

# Роутер для самообследования
self_assessment_router = self_assessment_handler.router
# Разрешаем всем пользователям, включая watcher, использовать функционал самообследования
self_assessment_roles = ["teacher", "responsible", "admin", "watcher"]
self_assessment_router.message.middleware(RoleMiddleware(allowed_roles=self_assessment_roles))
self_assessment_router.callback_query.middleware(RoleMiddleware(allowed_roles=self_assessment_roles))

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
dp.include_router(self_assessment_router)
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
        BotCommand(command="self_assessment", description="Заполнить лист самообследования")
    ]
    
    # Команды для наблюдателей (watcher)
    watcher_commands = [
        BotCommand(command="start", description="Начать работу с ботом или перезапустить"),
        BotCommand(command="watcher", description="Посмотреть доступные команды для наблюдателей"),
        BotCommand(command="self_assessment", description="Заполнить лист самообследования"),
        BotCommand(command="get_report", description="Получить отчет за период")
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
    
    for user in watcher_users:
        try:
            user_id = user.get("telegram_id")
            if user_id:
                await bot.set_my_commands(
                    watcher_commands,
                    scope=BotCommandScopeChat(chat_id=user_id)
                )
                logger.info(f"Установлены специальные команды для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при установке команд для пользователя {user.get('telegram_id')}: {e}")


# Обработчик для обновления команд после добавления роли watcher
# Используем прямой импорт F из aiogram вместо filters.F

# Регистрируем обработчик для обновления команд после изменения роли пользователя
@dp.callback_query(F.data == "confirm_watcher")
async def update_commands_after_role_change(callback: CallbackQuery):
    # Вызываем после завершения работы текущего обработчика
    await callback.answer()  # Важно не убирать этот вызов для завершения callback
    # Затем обновляем команды
    await set_default_commands(callback.bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
