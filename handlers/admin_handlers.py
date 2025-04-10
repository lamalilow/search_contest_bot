import os
from datetime import datetime, timedelta

from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId

from config import logger
from handlers.responsible_handlers import show_responsible_list
from keyboards.cancel_keyboard import create_cancel_keyboard
from services.database import users_col, contests_col
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
    _, user_id, role = query.data.split("_")
    user_id = int(user_id)

    # Проверка, является ли пользователь администратором
    user = users_col.find_one({"telegram_id": user_id})
    if user and user.get("role") == "admin":
        await query.answer("Нельзя изменить роль администратора.")
        return

    # Обновление роли пользователя
    users_col.update_one({"telegram_id": user_id}, {"$set": {"role": role}})
    await query.answer(f"Роль '{role}' успешно назначена пользователю.")

    # Уведомление пользователя о новой роли
    try:
        await query.bot.send_message(user_id, f"Вам назначена новая роль: {role}.")
        await send_role_keyboard(query.bot, user_id, role)
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

    await query.message.edit_text(f"Роль '{role}' назначена пользователю.")


# Хэндлер для отмены создания конкурса
@router.message(lambda message: message.text == "❌ Отменить создание конкурса")
async def cancel_contest_creation(message: types.Message):
    # Получаем данные пользователя из базы данных
    user = users_col.find_one({"telegram_id": message.from_user.id})

    if not user:
        await message.answer("Пользователь не найден.", reply_markup=types.ReplyKeyboardRemove())
        return

    # Удаляем конкурс, который находится в процессе создания
    result = contests_col.delete_one({
        "telegram_id": message.from_user.id,
        "step": {"$ne": None}  # Ищем конкурс, у которого шаг не равен None
    })

    if result.deleted_count > 0:
        await message.answer("Создание конкурса отменено.",
                             reply_markup=await send_role_keyboard(message.bot, message.from_user.id, user.get("role")))
    else:
        await message.answer("Нет активного конкурса для отмены.",
                             reply_markup=await send_role_keyboard(message.bot, message.from_user.id, user.get("role")))


# Хэндлер для добавления конкурса
@router.message(lambda message: message.text == "Добавить конкурс")
async def add_contest(message: types.Message):
    # Проверяем, есть ли у пользователя активный конкурс в процессе создания
    active_contest = contests_col.find_one({
        "telegram_id": message.from_user.id,
        "step": {"$ne": None}  # Ищем конкурс, у которого шаг не равен None
    })

    if active_contest:
        await message.answer("У вас уже есть активный конкурс в процессе создания. Завершите его или отмените.")
        return

    # Создаем новый конкурс с уникальным _id
    contest_id = ObjectId()  # Уникальный идентификатор для нового конкурса
    contests_col.insert_one({
        "_id": contest_id,
        "telegram_id": message.from_user.id,
        "step": "name",  # Устанавливаем начальный шаг
        "files": []
    })
    await message.answer("Введите название конкурса:", reply_markup=create_cancel_keyboard())


# Хэндлер для обработки названия конкурса
@router.message(lambda message: contests_col.find_one({"telegram_id": message.from_user.id, "step": "name"}))
async def process_contest_name(message: types.Message):
    if not message.text:
        await message.answer("Пожалуйста, введите название конкурса текстом.")
        return
    # Обновляем конкурс, добавляя название
    contests_col.update_one(
        {"telegram_id": message.from_user.id, "step": "name"},
        {"$set": {"name": message.text, "step": "dates"}}
    )
    await message.answer("Введите даты проведения конкурса (в формате ДД.ММ.ГГГГ - ДД.ММ.ГГГГ или ДД.ММ.ГГГГ):",
                         reply_markup=create_cancel_keyboard())


# Хэндлер для обработки даты конкурса
@router.message(lambda message: contests_col.find_one({"telegram_id": message.from_user.id, "step": "dates"}))
async def process_contest_dates(message: types.Message):
    if not message.text:
        await message.answer("Пожалуйста, введите даты в текстовом формате.")
        return

    try:
        # Разделяем строку на две части
        dates = message.text.split(" - ")

        if len(dates) == 1:
            # Только дата окончания
            end_date = datetime.strptime(dates[0].strip(), "%d.%m.%Y")
            start_date = None
        elif len(dates) == 2:
            # Дата начала и дата окончания
            start_date = datetime.strptime(dates[0].strip(), "%d.%m.%Y")
            end_date = datetime.strptime(dates[1].strip(), "%d.%m.%Y")

            if start_date > end_date:
                await message.answer("Дата начала не может быть позже даты окончания. Попробуйте снова.")
                return
        else:
            await message.answer("Некорректный формат дат. Введите 'ДД.ММ.ГГГГ' или 'ДД.ММ.ГГГГ - ДД.ММ.ГГГГ'.")
            return

        # Обновляем конкурс, добавляя даты
        contests_col.update_one(
            {"telegram_id": message.from_user.id, "step": "dates"},
            {"$set": {
                "start_date": start_date,
                "end_date": end_date,
                "step": "description"
            }}
        )
        await message.answer("Введите описание конкурса:", reply_markup=create_cancel_keyboard())

    except ValueError:
        await message.answer("Некорректный формат дат. Введите 'ДД.ММ.ГГГГ' или 'ДД.ММ.ГГГГ - ДД.ММ.ГГГГ'.")


# Хэндлер для обработки описания конкурса
@router.message(lambda message: contests_col.find_one({"telegram_id": message.from_user.id, "step": "description"}))
async def process_contest_description(message: types.Message):
    if not message.text:
        await message.answer("Пожалуйста, введите описание конкурса текстом.")
        return
    # Обновляем конкурс, добавляя описание
    contests_col.update_one(
        {"telegram_id": message.from_user.id, "step": "description"},
        {"$set": {"description": message.text, "step": "file"}}
    )
    await message.answer("Прикрепите файл (pdf, docx, doc, xlsx). Чтобы закончить загрузку файлов, нажмите /done.",
                         reply_markup=create_cancel_keyboard())


# Хэндлер для обработки файла
@router.message(lambda message: contests_col.find_one({"telegram_id": message.from_user.id, "step": "file"}))
async def process_contest_file(message: types.Message):
    if message.document:
        file_ext = message.document.file_name.split(".")[-1].lower()
        if file_ext not in ["pdf", "docx", "doc", "xlsx"]:
            await message.answer("Недопустимый формат файла. Разрешены только pdf, docx, doc, xlsx.")
            return

        file_id = message.document.file_id
        file = await message.bot.get_file(file_id)
        file_path = file.file_path
        file_name = message.document.file_name
        await message.bot.download_file(file_path, os.path.join("uploads", file_name))

        # Добавляем файл в список файлов конкурса
        contests_col.update_one(
            {"telegram_id": message.from_user.id, "step": "file"},
            {"$push": {"files": file_name}}
        )
        await message.answer(f"Файл {file_name} успешно загружен. Прикрепите еще файлы или нажмите /done.")
    elif message.text == "/done":
        # Если пользователь нажал /done, завершаем загрузку файлов
        contest = contests_col.find_one({"telegram_id": message.from_user.id, "step": "file"})
        if contest:
            contests_col.update_one(
                {"telegram_id": message.from_user.id, "step": "file"},
                {"$set": {"step": "responsible"}}
            )
            await message.answer("Загрузка файлов завершена. Теперь выберите ответственного за конкурс.")
            await show_responsible_list(message)
    else:
        await message.answer("Пожалуйста, прикрепите файл или нажмите /done для завершения.",
                             reply_markup=create_cancel_keyboard())


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


#  Хэндлер для отображения списка конкурсов
@router.message(lambda message: message.text == "Удалить конкурсы")
async def edit_contests(message: types.Message):
    # Получаем список всех конкурсов
    contests = list(contests_col.find().sort("start_date", 1))

    if not contests:
        await message.answer("Нет доступных конкурсов для редактирования.")
        return

    # Создаем inline-клавиатуру с конкурсами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for contest in contests:
        contest_name = contest["name"]
        end_date = contest["end_date"]

        # Проверяем, прошло ли две недели с даты окончания конкурса
        if datetime.now() > end_date + timedelta(weeks=2):
            contest_name += " 🗑️"  # Добавляем значок для предложения удалить

        # Добавляем кнопку с названием конкурса
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=contest_name, callback_data=f"select_contest_{contest['_id']}")]
        )

    await message.answer("Выберите конкурс для удаления:", reply_markup=keyboard)


# Хэндлер для обработки выбора конкурса
@router.callback_query(lambda query: query.data.startswith("select_contest_"))
async def select_contest(query: types.CallbackQuery):
    # Получаем ID конкурса из callback_data
    contest_id = query.data.split("_")[2]

    # Ищем конкурс в базе данных
    contest = contests_col.find_one({"_id": ObjectId(contest_id)})

    if not contest:
        await query.answer("Конкурс не найден.")
        return

    # Создаем inline-кнопку для удаления
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить", callback_data=f"delete_contest_{contest_id}")]
    ])

    await query.message.edit_text(
        f"Выбран конкурс: {contest['name']}. Удалить его?",
        reply_markup=keyboard
    )


# Хэндлер для удаления конкурса
@router.callback_query(lambda query: query.data.startswith("delete_contest_"))
async def delete_contest(query: types.CallbackQuery):
    # Получаем ID конкурса из callback_data
    contest_id = query.data.split("_")[2]

    # Ищем конкурс в базе данных
    contest = contests_col.find_one({"_id": ObjectId(contest_id)})

    if not contest:
        await query.answer("Конкурс не найден.")
        return

    # Удаляем конкурс из базы данных
    result = contests_col.delete_one({"_id": ObjectId(contest_id)})

    if result.deleted_count > 0:
        await query.message.edit_text(f"Конкурс '{contest['name']}' успешно удален.")
    else:
        await query.message.edit_text("Не удалось удалить конкурс.")


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
