import os
from datetime import datetime, timedelta

from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId

from config import logger
from handlers.contest.responsible_handlers import show_responsible_list
from keyboards.cancel_keyboard import create_cancel_keyboard
from services.database import users_col, contests_col
from utils.role_utils import send_role_keyboard

router = Router()


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


# Хэндлер для отображения списка конкурсов для изменения
@router.message(lambda message: message.text == "Изменить конкурс")
async def show_contests_for_edit(message: types.Message):
    # Получаем список всех конкурсов
    contests = list(contests_col.find().sort("start_date", 1))

    if not contests:
        await message.answer("Нет доступных конкурсов для редактирования.")
        return

    # Создаем inline-клавиатуру с конкурсами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for contest in contests:
        # Добавляем кнопку с названием конкурса
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=contest["name"], callback_data=f"edit_contest_{contest['_id']}")]
        )

    await message.answer("Выберите конкурс для редактирования:", reply_markup=keyboard)


# Хэндлер для выбора поля конкурса для редактирования
@router.callback_query(lambda query: query.data.startswith("edit_contest_"))
async def select_contest_field(query: types.CallbackQuery):
    contest_id = query.data.split("_")[2]
    contest = contests_col.find_one({"_id": ObjectId(contest_id)})

    if not contest:
        await query.answer("Конкурс не найден.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data=f"edit_field_name_{contest_id}")],
        [InlineKeyboardButton(text="Даты", callback_data=f"edit_field_dates_{contest_id}")],
        [InlineKeyboardButton(text="Описание", callback_data=f"edit_field_description_{contest_id}")],
        [InlineKeyboardButton(text="Файлы", callback_data=f"edit_field_files_{contest_id}")],
        [InlineKeyboardButton(text="Ответственный", callback_data=f"edit_field_responsible_{contest_id}")]
    ])

    await query.message.edit_text(
        f"Выберите поле для редактирования конкурса '{contest['name']}':",
        reply_markup=keyboard
    )


# Хэндлер для редактирования названия
@router.callback_query(lambda query: query.data.startswith("edit_field_name_"))
async def edit_contest_name(query: types.CallbackQuery):
    contest_id = query.data.split("_")[3]
    contests_col.update_one(
        {"_id": ObjectId(contest_id)},
        {"$set": {"edit_step": "name"}}
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_edit")]
    ])
    await query.message.edit_text("Введите новое название конкурса:", reply_markup=keyboard)


# Хэндлер для редактирования дат
@router.callback_query(lambda query: query.data.startswith("edit_field_dates_"))
async def edit_contest_dates(query: types.CallbackQuery):
    contest_id = query.data.split("_")[3]
    contests_col.update_one(
        {"_id": ObjectId(contest_id)},
        {"$set": {"edit_step": "dates"}}
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_edit")]
    ])
    await query.message.edit_text(
        "Введите новые даты проведения конкурса (в формате ДД.ММ.ГГГГ - ДД.ММ.ГГГГ или ДД.ММ.ГГГГ):",
        reply_markup=keyboard
    )


# Хэндлер для редактирования описания
@router.callback_query(lambda query: query.data.startswith("edit_field_description_"))
async def edit_contest_description(query: types.CallbackQuery):
    contest_id = query.data.split("_")[3]
    contests_col.update_one(
        {"_id": ObjectId(contest_id)},
        {"$set": {"edit_step": "description"}}
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_edit")]
    ])
    await query.message.edit_text("Введите новое описание конкурса:", reply_markup=keyboard)


# Хэндлер для редактирования файлов
@router.callback_query(lambda query: query.data.startswith("edit_field_files_"))
async def edit_contest_files(query: types.CallbackQuery):
    contest_id = query.data.split("_")[3]
    contests_col.update_one(
        {"_id": ObjectId(contest_id)},
        {"$set": {"edit_step": "files"}}
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_edit")]
    ])
    await query.message.edit_text(
        "Прикрепите новые файлы (pdf, docx, doc, xlsx). Чтобы закончить загрузку файлов, нажмите /done.",
        reply_markup=keyboard
    )


# Хэндлер для редактирования ответственного
@router.callback_query(lambda query: query.data.startswith("edit_field_responsible_"))
async def edit_contest_responsible(query: types.CallbackQuery):
    contest_id = query.data.split("_")[3]
    contests_col.update_one(
        {"_id": ObjectId(contest_id)},
        {"$set": {"edit_step": "responsible"}}
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_edit")]
    ])
    await query.message.edit_text("Выберите нового ответственного за конкурс:", reply_markup=keyboard)
    await show_responsible_list(query.message)


# Хэндлер для отмены редактирования
@router.callback_query(lambda query: query.data == "cancel_edit")
async def cancel_edit(query: types.CallbackQuery):
    contest = contests_col.find_one({"edit_step": {"$ne": None}})
    if contest:
        contests_col.update_one(
            {"_id": contest["_id"]},
            {"$set": {"edit_step": None}}
        )
    await query.message.edit_text(
        "Редактирование отменено.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
    )
    await query.message.answer(
        "Редактирование отменено.",
        reply_markup=await send_role_keyboard(query.bot, query.from_user.id, "admin")
    )


# Обработчики для сохранения изменений
@router.message(lambda message: contests_col.find_one({"edit_step": "name", "telegram_id": message.from_user.id}))
async def save_contest_name(message: types.Message):
    if not message.text:
        await message.answer("Пожалуйста, введите название конкурса текстом.")
        return
    
    contest = contests_col.find_one({"edit_step": "name", "telegram_id": message.from_user.id})
    contests_col.update_one(
        {"_id": contest["_id"]},
        {"$set": {"name": message.text, "edit_step": None}}
    )
    await message.answer(
        f"Название конкурса успешно изменено на: {message.text}",
        reply_markup=await send_role_keyboard(message.bot, message.from_user.id, "admin")
    )


@router.message(lambda message: contests_col.find_one({"edit_step": "dates", "telegram_id": message.from_user.id}))
async def save_contest_dates(message: types.Message):
    if not message.text:
        await message.answer("Пожалуйста, введите даты в текстовом формате.")
        return

    try:
        dates = message.text.split(" - ")
        if len(dates) == 1:
            end_date = datetime.strptime(dates[0].strip(), "%d.%m.%Y")
            start_date = None
        elif len(dates) == 2:
            start_date = datetime.strptime(dates[0].strip(), "%d.%m.%Y")
            end_date = datetime.strptime(dates[1].strip(), "%d.%m.%Y")
            if start_date > end_date:
                await message.answer("Дата начала не может быть позже даты окончания. Попробуйте снова.")
                return
        else:
            await message.answer("Некорректный формат дат. Введите 'ДД.ММ.ГГГГ' или 'ДД.ММ.ГГГГ - ДД.ММ.ГГГГ'.")
            return

        contest = contests_col.find_one({"edit_step": "dates", "telegram_id": message.from_user.id})
        contests_col.update_one(
            {"_id": contest["_id"]},
            {"$set": {
                "start_date": start_date,
                "end_date": end_date,
                "edit_step": None
            }}
        )
        await message.answer(
            "Даты конкурса успешно изменены.",
            reply_markup=await send_role_keyboard(message.bot, message.from_user.id, "admin")
        )

    except ValueError:
        await message.answer("Некорректный формат дат. Введите 'ДД.ММ.ГГГГ' или 'ДД.ММ.ГГГГ - ДД.ММ.ГГГГ'.")


@router.message(lambda message: contests_col.find_one({"edit_step": "description", "telegram_id": message.from_user.id}))
async def save_contest_description(message: types.Message):
    if not message.text:
        await message.answer("Пожалуйста, введите описание конкурса текстом.")
        return
    
    contest = contests_col.find_one({"edit_step": "description", "telegram_id": message.from_user.id})
    contests_col.update_one(
        {"_id": contest["_id"]},
        {"$set": {"description": message.text, "edit_step": None}}
    )
    await message.answer(
        "Описание конкурса успешно изменено.",
        reply_markup=await send_role_keyboard(message.bot, message.from_user.id, "admin")
    )


@router.message(lambda message: contests_col.find_one({"edit_step": "files", "telegram_id": message.from_user.id}))
async def save_contest_files(message: types.Message):
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

        contest = contests_col.find_one({"edit_step": "files", "telegram_id": message.from_user.id})
        contests_col.update_one(
            {"_id": contest["_id"]},
            {"$push": {"files": file_name}}
        )
        await message.answer(f"Файл {file_name} успешно загружен. Прикрепите еще файлы или нажмите /done.")
    elif message.text == "/done":
        contest = contests_col.find_one({"edit_step": "files", "telegram_id": message.from_user.id})
        contests_col.update_one(
            {"_id": contest["_id"]},
            {"$set": {"edit_step": None}}
        )
        await message.answer(
            "Загрузка файлов завершена.",
            reply_markup=await send_role_keyboard(message.bot, message.from_user.id, "admin")
        )
    else:
        await message.answer(
            "Пожалуйста, прикрепите файл или нажмите /done для завершения.",
            reply_markup=create_cancel_keyboard()
        ) 