from aiogram import Bot
from keyboards import admin_keyboard, responsible_keyboard, teacher_keyboard


async def send_role_keyboard(bot: Bot, user_id: int, role):
    """
    Отправляет клавиатуру в зависимости от роли пользователя
    
    Args:
        bot: Объект бота
        user_id: ID пользователя
        role: Роль пользователя (строка или массив ролей)
    """
    # Если роль - массив, используем приоритет ролей для определения клавиатуры
    if isinstance(role, list):
        if "admin" in role:
            keyboard = await admin_keyboard.create_admin_keyboard()
            role_name = "admin"
        elif "responsible" in role:
            keyboard = await responsible_keyboard.create_responsible_keyboard()
            role_name = "responsible"
        else:
            keyboard = await teacher_keyboard.create_teacher_keyboard()
            role_name = "teacher"
    else:
        # Если роль - строка
        if role == "admin":
            keyboard = await admin_keyboard.create_admin_keyboard()
            role_name = "admin"
        elif role == "responsible":
            keyboard = await responsible_keyboard.create_responsible_keyboard()
            role_name = "responsible"
        else:
            keyboard = await teacher_keyboard.create_teacher_keyboard()
            role_name = "teacher"

    await bot.send_message(
        user_id,
        f"Главное меню для роли: {role_name}",
        reply_markup=keyboard
    )
