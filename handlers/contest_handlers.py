from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from bson import ObjectId

from services.database import contests_col, users_col
from config import logger
import os

# Создаем роутер
router = Router()




# Хэндлер для отображения списка конкурсов
@router.message(lambda message: message.text == "Список конкурсов")
async def show_contests_list(message: types.Message):
    contests = list(contests_col.find({}).sort("start_date", 1))  # Сортировка по дате начала
    if not contests:
        await message.answer("Конкурсы не найдены.")
        return

    # Создание инлайн-клавиатуры с конкурсами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for contest in contests:
        # Проверяем наличие обязательных полей
        if "name" in contest and "end_date" in contest:
            start_date_str = (
                contest["start_date"].strftime("%d.%m.%Y")
                if "start_date" in contest and contest["start_date"]
                else "Не указана"
            )
            button_text = f"{contest['name']} ({start_date_str} - {contest['end_date'].strftime('%d.%m.%Y')})"
            keyboard.inline_keyboard.append(
                [InlineKeyboardButton(text=button_text, callback_data=f"contest_{contest['_id']}")]
            )
        else:
            logger.warning(f"Конкурс с _id {contest['_id']} пропущен из-за отсутствия обязательных полей.")

    await message.answer("Список конкурсов:", reply_markup=keyboard)


# Хэндлер для обработки выбора конкурса
@router.callback_query(lambda query: query.data.startswith("contest_"))
async def process_contest_selection(query: types.CallbackQuery):
    contest_id = query.data.split("_")[1]
    user_id = query.from_user.id

    try:
        # Преобразуем строку в ObjectId
        contest = contests_col.find_one({"_id": ObjectId(contest_id)})
        if not contest:
            await query.answer("Конкурс не найден.")
            return

        # Получаем имя ответственного
        responsible = users_col.find_one({"telegram_id": contest.get("responsible_id")})
        responsible_name = responsible["full_name"] if responsible else "Неизвестно"

        # Формируем сообщение с информацией о конкурсе
        start_date_str = (
            contest["start_date"].strftime("%d.%m.%Y")
            if "start_date" in contest and contest["start_date"]
            else "Не указана"
        )
        contest_info = (
            f"Название: {contest['name']}\n"
            f"Описание: {contest.get('description', 'Описание отсутствует')}\n"
            f"Даты проведения: {start_date_str} - {contest['end_date'].strftime('%d.%m.%Y')}\n"
            f"Ответственный: {responsible_name}\n"
            f"Файлы: {', '.join(contest.get('files', [])) if contest.get('files') else 'Файлы не прикреплены'}"
        )

        # Проверяем, участвует ли пользователь в конкурсе
        is_participant = user_id in contest.get("participants", [])

        # Создаём клавиатуру только для пользователей, которые ещё не участвуют
        keyboard = None
        if not is_participant:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Участвовать", callback_data=f"join_{contest_id}")]
            ])

        # Отправляем информацию о конкурсе
        await query.message.answer(contest_info, reply_markup=keyboard)

        # Если есть файлы, отправляем их
        if contest.get("files"):
            for file_name in contest["files"]:
                file_path = os.path.join("uploads", file_name)
                if os.path.exists(file_path):  # Проверяем, существует ли файл
                    try:
                        # Используем FSInputFile для отправки файла
                        file_to_send = FSInputFile(file_path)
                        await query.message.answer_document(file_to_send)
                    except Exception as e:
                        logger.error(f"Не удалось отправить файл {file_name}: {e}")
                        await query.message.answer(f"Произошла ошибка при отправке файла {file_name}.")
                else:
                    logger.error(f"Файл не найден: {file_path}")
                    await query.message.answer(f"Файл {file_name} не найден.")
    except Exception as e:
        logger.error(f"Ошибка при обработке конкурса: {e}")
        await query.answer("Произошла ошибка при обработке конкурса.")

# Хэндлер для обработки нажатия на кнопку "Участвовать"
@router.callback_query(lambda query: query.data.startswith("join_"))
async def process_join_contest(query: types.CallbackQuery):
    contest_id = query.data.split("_")[1]
    user_id = query.from_user.id

    try:
        # Находим конкурс
        contest = contests_col.find_one({"_id": ObjectId(contest_id)})
        if not contest:
            await query.answer("Конкурс не найден.")
            return

        # Находим пользователя
        user = users_col.find_one({"telegram_id": user_id})
        if not user:
            await query.answer("Пользователь не найден.")
            return

        # Формируем сообщение с информацией о конкурсе
        start_date_str = (
            contest["start_date"].strftime("%d.%m.%Y")
            if "start_date" in contest and contest["start_date"]
            else "Не указана"
        )

        # Добавляем пользователя в список участников конкурса
        contests_col.update_one(
            {"_id": ObjectId(contest_id)},
            {"$addToSet": {"participants": user_id}}  # Используем $addToSet, чтобы избежать дубликатов
        )

        # Удаляем кнопку "Участвовать" и редактируем сообщение
        await query.message.edit_reply_markup(reply_markup=None)  # Убираем кнопку
        await query.answer(f"Вы успешно присоединились к конкурсу {contest['name']}.")

        # Отправляем уведомление ответственному
        responsible_id = contest.get("responsible_id")
        if responsible_id:
            responsible = users_col.find_one({"telegram_id": responsible_id})
            if responsible:
                await query.bot.send_message(
                    responsible_id,
                    f"Новый участник конкурса:\n"
                    f"Название конкурса: {contest['name']}\n"
                    f"Даты проведения: {start_date_str} - {contest['end_date'].strftime('%d.%m.%Y')}\n"
                    f"Участник: {user['full_name']}"
                )
                await query.message.answer("Ответственному отправлено уведомление.")
    except Exception as e:
        logger.error(f"Ошибка при присоединении к конкурсу: {e}")
        await query.answer("Произошла ошибка при присоединении к конкурсу.")
