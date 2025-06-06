from config import logger
from services.database import users_col


# Уведомление всех пользователей о новом конкурсе
async def notify_all_users(contest_name, bot):
    if not contest_name:
        logger.error("Название конкурса не указано.")
        return

    users = users_col.find({"notifications_enabled": True})
    if users is None:
        logger.info("Не найдено пользователей для уведомления.")
        return

    logger.info(f"Bot: {bot}")

    for user in users:
        try:
            await bot.send_message(user["telegram_id"], f"Уведомление: новый конкурс {contest_name}.")
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user['telegram_id']}: {e}") 