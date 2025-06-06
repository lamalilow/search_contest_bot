import os
from datetime import datetime, timedelta

from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId
from aiogram.filters import Command

from config import logger
from services.database import users_col
from utils.user_utils import show_user_list
from utils.role_utils import send_role_keyboard

router = Router()


@router.message(lambda message: message.text == "Добавить администратора")
async def add_admin(message: types.Message):
    await show_user_list(message, "admin")


# Хэндлер для добавления ответственного
@router.message(lambda message: message.text == "Добавить ответственного")
async def add_responsible(message: types.Message):
    await show_user_list(message, "responsible")


# Хэндлер для добавления преподавателя
@router.message(lambda message: message.text == "Добавить преподавателя")
async def add_teacher(message: types.Message):
    await show_user_list(message, "teacher")


# Хэндлер для открытия всех пользователей
@router.message(lambda message: message.text == "Список пользователей")
async def show_users_list(message: types.Message):
    # Используем функцию show_user_list для отображения списка пользователей
    await show_user_list(message, "view_user_info")


# Хэндлер для просмотра информации о пользователе
@router.callback_query(lambda query: query.data.startswith("userinfo_"))
async def view_user_info_handler(query: types.CallbackQuery):
    logger.info(query.data)
    parts = query.data.split("_")
    logger.info(parts)
    if len(parts) < 3:
        await query.answer("Некорректные данные.")
        return

    _, user_id, role = parts[0], parts[1], "_".join(parts[2:])  # Объединяем оставшиеся части для роли

    # Если роль "view_user_info", отображаем полную информацию о пользователе
    logger.info(role)
    if role == "view_user_info":
        user = users_col.find_one({"telegram_id": int(user_id)})
        if not user:
            await query.answer("Пользователь не найден.")
            return

        # Формируем сообщение с полной информацией о пользователе
        user_info = (
            f"👤 Имя: {user.get('full_name', 'Не указано')}\n"
            f"🆔 Telegram ID: {user.get('telegram_id', 'Не указан')}\n"
            f"📞 Телефон: {user.get('phone', 'Не указан')}\n"
            f"🎭 Роль: {user.get('role', 'Не указана')}\n"
            f"🔔 Уведомления: {'Включены' if user.get('notifications_enabled', False) else 'Отключены'}"
        )

        # Добавляем текстовое сообщение с инструкцией для перехода в чат
        user_info += "\n\nℹ️ Чтобы перейти в чат с этим пользователем, найдите его вручную по Telegram ID."

        # Создаем inline-клавиатуру с кнопкой для удаления пользователя
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Удалить пользователя", callback_data=f"confirm_delete_user_{user_id}")]
        ])

        await query.message.edit_text(user_info, reply_markup=keyboard)
        await query.answer()
        return

# Хэндлер для подтверждения удаления пользователя
@router.callback_query(lambda query: query.data.startswith("confirm_delete_user_"))
async def confirm_delete_user_handler(query: types.CallbackQuery):
    user_id = query.data.split("_")[3]  # Получаем ID пользователя из callback_data

    # Создаем inline-клавиатуру для подтверждения удаления
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_user_{user_id}")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"cancel_delete_user_{user_id}")]
    ])

    await query.message.edit_text(
        "Вы уверены, что хотите удалить этого пользователя?",
        reply_markup=keyboard
    )
    await query.answer()


# Хэндлер для удаления пользователя
@router.callback_query(lambda query: query.data.startswith("delete_user_"))
async def delete_user_handler(query: types.CallbackQuery):
    user_id = query.data.split("_")[2]  # Получаем ID пользователя из callback_data

    # Получаем данные пользователя из базы данных
    user = users_col.find_one({"telegram_id": int(user_id)})
    if not user:
        await query.message.edit_text("Пользователь не найден.")
        await query.answer()
        return

    # Проверяем, является ли пользователь администратором
    if user.get("role") == "admin":
        await query.message.edit_text("❌ Невозможно удалить пользователя с ролью 'админ'.")
        await query.answer()
        return

    # Удаляем пользователя из базы данных
    result = users_col.delete_one({"telegram_id": int(user_id)})

    if result.deleted_count > 0:
        await query.message.edit_text("Пользователь успешно удален.")
    else:
        await query.message.edit_text("Не удалось удалить пользователя.")

    await query.answer()


# Хэндлер для отмены удаления пользователя
@router.callback_query(lambda query: query.data.startswith("cancel_delete_user_"))
async def cancel_delete_user_handler(query: types.CallbackQuery):
    user_id = query.data.split("_")[3]  # Получаем ID пользователя из callback_data

    # Возвращаемся к информации о пользователе
    await view_user_info_handler(query)
    await query.answer()


# Хэндлер для обработки выбора буквы
@router.callback_query(lambda query: query.data.startswith("letter_"))
async def process_letter_selection(query: types.CallbackQuery):
    parts = query.data.split("_")
    if len(parts) < 3:
        await query.answer("Некорректные данные.")
        return

    _, letter, role = parts[0], parts[1], "_".join(parts[2:])  # Объединяем оставшиеся части для роли

    users = list(users_col.find({"full_name": {"$regex": f"^{letter}", "$options": "i"}}).sort("full_name", 1))
    if not users:
        await query.answer("Пользователи не найдены.")
        return

    # Создание инлайн-клавиатуры с пользователями
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for user in users:
        if role == "view_user_info":
            # Для просмотра информации о пользователе
            callback_data = f"userinfo_{user['telegram_id']}_view_user_info"
        else:
            # Для изменения роли пользователя
            callback_data = f"usereditrole_{user['telegram_id']}_{role}"

        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=user["full_name"], callback_data=callback_data)]
        )

    await query.message.edit_text(f"Пользователи, фамилии которых начинаются на {letter}:", reply_markup=keyboard)

# Хэндлер для обработки выбора пользователя
@router.callback_query(lambda query: query.data.startswith("usereditrole_"))
async def process_user_selection(query: types.CallbackQuery):
    logger.info(f"Callback data: {query.data}")
    parts = query.data.split("_")
    if len(parts) < 3:
        await query.answer("Некорректные данные.")
        return

    user_id = int(parts[1])
    role = "_".join(parts[2:])  # Объединяем оставшиеся части для роли

    # Проверка, является ли пользователь администратором
    user = users_col.find_one({"telegram_id": user_id})
    if not user:
        await query.answer("Пользователь не найден.")
        return

    user_roles = user.get("role", [])
    if isinstance(user_roles, str):
        user_roles = [user_roles]
    elif user_roles is None:
        user_roles = []

    if "admin" in user_roles:
        await query.answer("Нельзя изменить роль администратора.")
        return

    # Получаем текущие роли пользователя
    current_roles = user_roles

    # Если новая роль уже есть в списке, ничего не делаем
    if role in current_roles:
        await query.answer(f"У пользователя уже есть роль '{role}'.")
        return

    # Добавляем новую роль в список
    current_roles.append(role)

    # Обновление роли пользователя
    users_col.update_one({"telegram_id": user_id}, {"$set": {"role": current_roles}})
    await query.answer(f"Роль '{role}' успешно назначена пользователю.")

    # Уведомление пользователя о новой роли
    try:
        await query.bot.send_message(user_id, f"Вам назначена новая роль: {role}.")
        await send_role_keyboard(query.bot, user_id, current_roles)
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

    # Обновляем сообщение с информацией о пользователе
    user_info = (
        f"👤 Имя: {user.get('full_name', 'Не указано')}\n"
        f"🆔 Telegram ID: {user.get('telegram_id', 'Не указан')}\n"
        f"📞 Телефон: {user.get('phone', 'Не указан')}\n"
        f"🎭 Роли: {', '.join(current_roles)}\n"
        f"🔔 Уведомления: {'Включены' if user.get('notifications_enabled', False) else 'Отключены'}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить пользователя", callback_data=f"confirm_delete_user_{user_id}")]
    ])

    await query.message.edit_text(user_info, reply_markup=keyboard)


# Хэндлер для обработки кнопки "Показать всех пользователей"
@router.callback_query(lambda query: query.data.startswith("show_all_users_"))
async def show_all_users_handler(query: types.CallbackQuery):
    _, role = query.data.split("_", 2)[0], query.data.split("_", 2)[2]  # Получаем роль из callback_data
    
    users = list(users_col.find({"full_name": {"$exists": True}}).sort("full_name", 1))
    if not users:
        await query.answer("Пользователи не найдены.")
        return
    
    # Формируем текстовый список всех пользователей
    user_text = "Список всех пользователей:\n\n"
    for i, user in enumerate(users, 1):
        user_text += f"{i}. {user.get('full_name', 'Без имени')} - {user.get('role', 'Без роли')}\n"
    
    # Создаем кнопку "Назад"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"back_to_letters_{role}")]
    ])
    
    await query.message.edit_text(user_text, reply_markup=keyboard)
    await query.answer()

# Хэндлер для обработки кнопки "Назад" к выбору букв
@router.callback_query(lambda query: query.data.startswith("back_to_letters_"))
async def back_to_letters_handler(query: types.CallbackQuery):
    role = query.data.split("_")[3]  # Получаем роль из callback_data
    
    # Вызываем функцию показа списка пользователей с выбором букв
    await show_user_list(query.message, role)
    await query.answer() 

@router.message(Command("remove_role"))
async def cmd_remove_role(message: types.Message):
    """Обработчик команды /remove_role для удаления роли у пользователя"""
    # Получаем список всех пользователей
    users = list(users_col.find())
    
    # Создаем клавиатуру с пользователями
    keyboard = []
    for user in users:
        # Пропускаем пользователей без ролей
        user_roles = user.get("role")
        if not user_roles:
            continue
            
        # Добавляем пользователя в клавиатуру
        keyboard.append([{
            "text": f"{user.get('full_name', 'Без имени')} ({user.get('telegram_id')})",
            "callback_data": f"remove_role_{user.get('telegram_id')}"
        }])
    
    if not keyboard:
        await message.answer("Нет пользователей с ролями.")
        return
    
    await message.answer(
        "Выберите пользователя, у которого нужно удалить роль:",
        reply_markup={"inline_keyboard": keyboard}
    )

@router.callback_query(lambda query: query.data.startswith("remove_role_"))
async def process_remove_role_selection(query: types.CallbackQuery):
    """Обработка выбора пользователя для удаления роли"""
    user_id = int(query.data.split("_")[2])
    
    # Получаем информацию о пользователе
    user = users_col.find_one({"telegram_id": user_id})
    if not user:
        await query.message.edit_text("Пользователь не найден.")
        await query.answer()
        return
    
    # Получаем текущие роли пользователя
    user_roles = user.get("role")
    
    # Если у пользователя нет ролей
    if not user_roles:
        await query.message.edit_text("У пользователя нет ролей для удаления.")
        await query.answer()
        return
    
    # Создаем клавиатуру с ролями для удаления
    keyboard = []
    if isinstance(user_roles, list):
        for role in user_roles:
            keyboard.append([{
                "text": f"Удалить роль: {role}",
                "callback_data": f"confirm_remove_role_{user_id}_{role}"
            }])
    else:
        keyboard.append([{
            "text": f"Удалить роль: {user_roles}",
            "callback_data": f"confirm_remove_role_{user_id}_{user_roles}"
        }])
    
    await query.message.edit_text(
        f"Выберите роль для удаления у пользователя {user.get('full_name', 'Без имени')}:",
        reply_markup={"inline_keyboard": keyboard}
    )
    await query.answer()

@router.callback_query(lambda query: query.data.startswith("confirm_remove_role_"))
async def process_remove_role_confirmation(query: types.CallbackQuery):
    """Обработка подтверждения удаления роли"""
    parts = query.data.split("_")
    user_id = int(parts[3])
    role_to_remove = "_".join(parts[4:])  # Объединяем оставшиеся части для роли
    
    # Получаем информацию о пользователе
    user = users_col.find_one({"telegram_id": user_id})
    if not user:
        await query.message.edit_text("Пользователь не найден.")
        await query.answer()
        return
    
    # Получаем текущие роли пользователя
    user_roles = user.get("role")
    
    # Проверяем, является ли пользователь администратором
    if role_to_remove == "admin":
        await query.message.edit_text("❌ Невозможно удалить роль 'админ'.")
        await query.answer()
        return
    
    # Обновляем роли пользователя
    if isinstance(user_roles, list):
        if role_to_remove in user_roles:
            user_roles.remove(role_to_remove)
            # Если осталась только одна роль, преобразуем в строку
            if len(user_roles) == 1:
                user_roles = user_roles[0]
            elif not user_roles:  # Если ролей не осталось
                user_roles = None
    else:
        if user_roles == role_to_remove:
            user_roles = None
    
    # Обновляем данные пользователя в базе
    users_col.update_one(
        {"telegram_id": user_id},
        {"$set": {"role": user_roles}}
    )
    
    # Отправляем сообщение пользователю об удалении роли
    try:
        await query.bot.send_message(
            user_id,
            f"У вас была удалена роль: {role_to_remove}"
        )
        if user_roles:
            await send_role_keyboard(query.bot, user_id, user_roles)
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
    
    await query.message.edit_text(
        f"Роль '{role_to_remove}' успешно удалена у пользователя {user.get('full_name', 'Без имени')}."
    )
    await query.answer()