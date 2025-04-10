from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId

from services.database import users_col, contests_col
from config import logger
from utils.role_utils import send_role_keyboard

# Создаем роутер
router = Router()


# Хэндлер для отображения списка ответственных
@router.message(lambda message: message.text == "Список ответственных")
async def show_responsible_list(message: types.Message):
    responsibles = list(users_col.find({"role": "responsible"}).sort("full_name", 1))
    if not responsibles:
        await message.answer("Ответственные не найдены.")
        return

    # Создание инлайн-клавиатуры с ответственными
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for responsible in responsibles:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=responsible["full_name"],
                                                              callback_data=f"responsible_{responsible['telegram_id']}")])

    await message.answer("Выберите ответственного за конкурс:", reply_markup=keyboard)


# Хэндлер для обработки выбора ответственного
@router.callback_query(lambda query: query.data.startswith("responsible_"))
async def process_responsible_selection(query: types.CallbackQuery):
    responsible_id = int(query.data.split("_")[1])  # Получаем ID ответственного
    contest = contests_col.find_one({"telegram_id": query.from_user.id, "step": "responsible"})
    if not contest:
        await query.answer("Конкурс не найден.")
        return

    # Формируем сообщение с информацией о конкурсе
    start_date_str = (
        contest["start_date"].strftime("%d.%m.%Y")
        if "start_date" in contest and contest["start_date"]
        else "Не указана"
    )
    # Обновляем конкурс, добавляя ID ответственного
    contests_col.update_one(
        {"_id": contest["_id"]},
        {"$set": {"responsible_id": responsible_id, "step": None}}
    )

    # Получаем имя ответственного
    responsible = users_col.find_one({"telegram_id": responsible_id})
    responsible_name = responsible["full_name"] if responsible else "Неизвестно"

    # Отправляем подтверждение администратору
    await query.answer(f"Ответственный {responsible_name} успешно назначен.")

    # Отправляем уведомление ответственному
    try:
        await query.bot.send_message(
            responsible_id,
            f"Вас назначили ответственным за конкурс:\n"
            f"Название: {contest['name']}\n"
            f"Даты проведения: {start_date_str} - {contest['end_date'].strftime('%d.%m.%Y')}\n"
            f"Описание: {contest.get('description', 'Описание отсутствует')}"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление ответственному {responsible_id}: {e}")

    await query.message.edit_text(f"Ответственный {responsible_name} назначен за конкурс.", )
    user = users_col.find_one({"telegram_id": query.from_user.id})
    if user:
        await send_role_keyboard(query.bot, query.from_user.id, user.get("role"))

        # Уведомление пользователей после добавления
    contest = contests_col.find_one({"_id": contest["_id"]})
    logger.warning('Уведомление пользователей: '+ str(contest))
    if contest and contest.get("name"):
        from handlers.admin_utils import notify_all_users
        await notify_all_users(contest["name"], query.bot)


# Хэндлер для отображения списка конкурсов с участниками
@router.message(lambda message: message.text == "Список участников")
async def show_contests_with_participants(message: types.Message):
    # Находим все конкурсы, за которые отвечает текущий пользователь
    contests = list(contests_col.find({"responsible_id": message.from_user.id}).sort("start_date", 1))
    if not contests:
        await message.answer("Конкурсы не найдены.")
        return

    # Создание инлайн-клавиатуры с конкурсами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for contest in contests:
        # Формируем сообщение с информацией о конкурсе
        start_date_str = (
            contest["start_date"].strftime("%d.%m.%Y")
            if "start_date" in contest and contest["start_date"]
            else "Не указана"
        )
        button_text = f"{contest['name']} ({start_date_str} - {contest['end_date'].strftime('%d.%m.%Y')})"
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=button_text, callback_data=f"participants_{contest['_id']}")])

    await message.answer("Выберите конкурс для просмотра списка участников:", reply_markup=keyboard)


# Хэндлер для обработки выбора конкурса и отображения списка участников
@router.callback_query(lambda query: query.data.startswith("participants_"))
async def process_contest_participants(query: types.CallbackQuery):
    contest_id = query.data.split("_")[1]
    try:
        # Находим конкурс
        contest = contests_col.find_one({"_id": ObjectId(contest_id)})
        if not contest:
            await query.answer("Конкурс не найден.")
            return

        # Получаем список участников
        participants = contest.get("participants", [])
        if not participants:
            await query.answer("Участники не найдены.")
            return

        # Формируем сообщение с информацией об участниках
        participants_info = "Список участников:\n"
        for participant_id in participants:
            participant = users_col.find_one({"telegram_id": participant_id})
            if participant:
                participants_info += f"- {participant['full_name']}\n"

        await query.message.answer(participants_info)
    except Exception as e:
        logger.error(f"Ошибка при обработке списка участников: {e}")
        await query.answer("Произошла ошибка при обработке списка участников.")
