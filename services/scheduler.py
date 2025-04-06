import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from services.database import contests_col

# Настройка логгера
logger = logging.getLogger(__name__)

# Инициализация планировщика
scheduler = AsyncIOScheduler()

# Функция для удаления старых конкурсов
async def remove_old_contests():
    try:
        three_weeks_ago = datetime.now() - timedelta(weeks=3)
        # Находим конкурсы, которые нужно удалить
        contests_to_delete = list(contests_col.find({"end_date": {"$lt": three_weeks_ago}}))

        if contests_to_delete:
            for contest in contests_to_delete:
                logger.info(
                    f"Удален конкурс: '{contest['name']}' (Дата окончания: {contest['end_date'].strftime('%d.%m.%Y')})")

        result = contests_col.delete_many({"end_date": {"$lt": three_weeks_ago}})
        logger.info(f"Удалено {result.deleted_count} старых конкурсов.")
    except Exception as e:
        logger.error(f"Ошибка при удалении старых конкурсов: {e}")

# Запуск планировщика
def start_scheduler(bot):
    try:
        # Добавляем задачу на выполнение каждые 24 часа
        scheduler.add_job(remove_old_contests, 'interval', hours=24)
        scheduler.start()
        logger.info("Планировщик успешно запущен.")
    except Exception as e:
        logger.error(f"Не удалось запустить планировщик: {e}")



# Остановка планировщика при завершении работы бота
import atexit
atexit.register(lambda: scheduler.shutdown())