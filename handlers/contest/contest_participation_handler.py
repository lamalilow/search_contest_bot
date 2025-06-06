import os
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.contest_states import ContestParticipationStates
from utils.contest_utils import save_contest_participation
from utils.file_utils import compress_and_save_image
from services.database import db
from aiogram.utils.markdown import hbold, hcode
import logging
from bson import ObjectId
import aiofiles
import asyncio

logger = logging.getLogger(__name__)

router = Router()

LEVELS = [
    "Внутривузовский/внутритехникумовский",
    "Муниципальный",
    "Региональный",
    "Областной",
    "Всероссийский",
    "Международный"
]

# Словарь для маппинга коротких кодов на полные названия уровней
LEVEL_CODES = {
    "vnutr": "Внутривузовский/внутритехникумовский",
    "mun": "Муниципальный",
    "reg": "Региональный",
    "obl": "Областной",
    "vser": "Всероссийский",
    "mezh": "Международный"
}

PARTICIPATION_FORMS = ["Очная", "Заочная"]
PARTICIPANT_TYPES = ["Преподаватель", "Студент"]

def get_summary_text(data: dict) -> str:
    fields = [
        ("Конкурс", data.get("contest_name")),
        ("Дата", data.get("date")),
        ("Уровень", data.get("level")),
        ("ФИО преподавателя", data.get("teacher_name")),
        ("Номинация", data.get("nomination")),
        ("Форма участия", data.get("participation_form")),
        ("Участник", data.get("participant_type")),
        ("ФИО студента", data.get("student_name")),
        ("Группа", data.get("group")),
        ("Результат", data.get("result")),
        ("Фото", f"{len(data.get('confirmation_files', []))} файл(ов)" if data.get('confirmation_files') else None),
    ]
    summary = [f"<b>Ваши данные:</b>"]
    for name, value in fields:
        if value:
            summary.append(f"• {name}: {hcode(str(value))}")
    return "\n".join(summary)

def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]])

def with_cancel_keyboard(keyboard=None):
    if keyboard is None:
        return cancel_keyboard()
    # Добавить кнопку отмены в конец
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return keyboard

# --- Стартовая команда ---
@router.message(Command("contest"))
async def cmd_contest(message: Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} ({message.from_user.full_name}) начал заполнение участия в конкурсе")
    current_state = await state.get_state()
    logger.info(f"Текущее состояние FSM перед очисткой: {current_state}")
    await state.clear()
    await state.set_state(ContestParticipationStates.selecting_contest)
    new_state = await state.get_state()
    logger.info(f"Новое состояние FSM после установки: {new_state}")
    contests = list(db.contests.find({}))
    if not contests:
        logger.warning(f"Пользователь {message.from_user.id}: в базе нет конкурсов")
        await message.answer("В базе нет конкурсов. Обратитесь к администратору.")
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Окон. {contest['end_date'].strftime('%d.%m.%Y')} - {contest['name']}", callback_data=f"participate_contest_{str(contest['_id'])}")]
            for contest in contests
        ]
    )
    await message.answer(
        "<b>Заполнение участия в конкурсе</b>\n\nВыберите конкурс для участия:",
        reply_markup=with_cancel_keyboard(keyboard),
        parse_mode="HTML"
    )

# --- Выбор конкурса для участия ---
@router.callback_query(ContestParticipationStates.selecting_contest, F.data.startswith("participate_contest_"))
async def process_selecting_contest(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    logger.info(f"Обработчик выбора конкурса: текущее состояние FSM: {current_state}")
    contest_id = callback.data.split("_", 2)[2]
    logger.info(f"Пользователь {callback.from_user.id} выбрал конкурс participate_contest_{contest_id} (FSM selecting_contest)")
    try:
        contest = db.contests.find_one({"_id": ObjectId(contest_id)})
        if not contest:
            logger.error(f"Пользователь {callback.from_user.id}: конкурс {contest_id} не найден (FSM selecting_contest)")
            await callback.answer("Конкурс не найден.", show_alert=True)
            return
        logger.info(f"Найден конкурс: {contest['name']}")
        await state.update_data(contest_id=contest_id, contest_name=contest["name"])
        data = await state.get_data()
        logger.info(f"Данные в FSM после обновления: {data}")
        date = contest.get("start_date")
        if date:
            date_str = date.strftime("%d.%m.%Y")
            await state.update_data(date=date_str)
            await state.set_state(ContestParticipationStates.selecting_level)
            logger.info(f"Пользователь {callback.from_user.id}: дата конкурса {date_str}, переход к выбору уровня")
            await callback.message.answer(
                f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 2/10</b>\n\nДата конкурса: {hcode(date_str)}\n\nВыберите уровень конкурса:",
                reply_markup=with_cancel_keyboard(level_keyboard()),
                parse_mode="HTML"
            )
        else:
            await state.set_state(ContestParticipationStates.entering_date)
            logger.info(f"Пользователь {callback.from_user.id}: требуется ввод даты конкурса вручную")
            await callback.message.answer(
                f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 2/10</b>\n\nВведите дату проведения конкурса (дд.мм.гггг):",
                reply_markup=cancel_keyboard(),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Ошибка при поиске конкурса: {e}")
        await callback.answer("Произошла ошибка при поиске конкурса.", show_alert=True)
    await callback.answer()

@router.message(ContestParticipationStates.entering_date)
async def process_entering_date(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
    except Exception:
        logger.warning(f"Пользователь {message.from_user.id}: некорректный формат даты '{date_str}'")
        await message.answer("Некорректный формат даты. Введите в формате дд.мм.гггг:", reply_markup=cancel_keyboard())
        return
    logger.info(f"Пользователь {message.from_user.id}: ввёл дату {date_str}")
    await state.update_data(date=date_str)
    await state.set_state(ContestParticipationStates.selecting_level)
    try:
        await message.answer(
            f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 3/10</b>\n\nВыберите уровень конкурса:",
            reply_markup=with_cancel_keyboard(level_keyboard()),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения с клавиатурой: {e}")
        # Пробуем отправить сообщение без клавиатуры
        try:
            await message.answer(
                f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 3/10</b>\n\nВыберите уровень конкурса:",
                parse_mode="HTML"
            )
            # Отправляем клавиатуру отдельным сообщением
            await message.answer(
                "Выберите уровень:",
                reply_markup=with_cancel_keyboard(level_keyboard())
            )
        except Exception as e2:
            logger.error(f"Ошибка при отправке сообщения без клавиатуры: {e2}")
            await message.answer("Произошла ошибка при отображении уровней. Пожалуйста, попробуйте снова через /contest")
            await state.clear()

# --- Уровень конкурса ---
@router.callback_query(ContestParticipationStates.selecting_level)
async def process_selecting_level(callback: CallbackQuery, state: FSMContext):
    level_code = callback.data.split("_")[1]
    level = LEVEL_CODES.get(level_code)
    if not level:
        logger.warning(f"Пользователь {callback.from_user.id}: выбрал некорректный уровень '{level_code}'")
        await callback.answer("Выберите уровень из списка.", show_alert=True)
        return
    logger.info(f"Пользователь {callback.from_user.id}: выбрал уровень {level}")
    await state.update_data(level=level)
    await state.set_state(ContestParticipationStates.selecting_teacher_name)
    await callback.message.answer(
        f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 4/10</b>\n\nВыберите ФИО преподавателя:",
        reply_markup=with_cancel_keyboard(teacher_name_keyboard(callback.from_user.id)),
        parse_mode="HTML"
    )
    await callback.answer()

def level_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=level, callback_data=f"level_{code}")]
            for code, level in LEVEL_CODES.items()
        ]
    )

# --- ФИО преподавателя ---
@router.message(ContestParticipationStates.entering_teacher_name)
async def process_teacher_name(message: Message, state: FSMContext):
    teacher_name = message.text.strip()
    logger.info(f"Пользователь {message.from_user.id}: ввёл ФИО преподавателя '{teacher_name}'")
    await state.update_data(teacher_name=teacher_name)
    await state.set_state(ContestParticipationStates.entering_nomination)
    await message.answer(
        f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 5/10</b>\n\nВведите номинацию:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

# --- Выбор типа участника ---
@router.callback_query(ContestParticipationStates.selecting_participant_type)
async def process_participant_type(callback: CallbackQuery, state: FSMContext):
    ptype = callback.data
    if ptype not in PARTICIPANT_TYPES:
        logger.warning(f"Пользователь {callback.from_user.id}: выбрал некорректный тип участника '{ptype}'")
        await callback.answer("Выберите из списка.", show_alert=True)
        return
    logger.info(f"Пользователь {callback.from_user.id}: выбрал тип участника {ptype}")
    await state.update_data(participant_type=ptype)
    
    if ptype == "Студент":
        await state.set_state(ContestParticipationStates.entering_student_name)
        await state.update_data(students=[])  # Инициализируем список студентов
        await callback.message.answer(
            f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 8/10</b>\n\n"
            "Введите ФИО студента. Вы можете добавить несколько студентов.\n"
            "Когда закончите, отправьте команду /done_students",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML"
        )
    else:
        # Если выбран преподаватель, автоматически заполняем поля студента прочерком
        await state.update_data(student_name="-", group="-")
        await state.set_state(ContestParticipationStates.entering_result)
        await callback.message.answer(
            f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 9/10</b>\n\n"
            "Введите результат участия (например: Диплом I степени):",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML"
        )
    await callback.answer()

# --- Выбор ФИО преподавателя ---
@router.callback_query(ContestParticipationStates.selecting_teacher_name)
async def process_selecting_teacher_name(callback: CallbackQuery, state: FSMContext):
    if callback.data == "use_my_name":
        # Получаем имя пользователя из базы данных
        user = db.users.find_one({"telegram_id": callback.from_user.id})
        if user and user.get("full_name"):
            teacher_name = user["full_name"]
            logger.info(f"Пользователь {callback.from_user.id}: выбрал своё имя '{teacher_name}'")
            await state.update_data(teacher_name=teacher_name)
            await state.set_state(ContestParticipationStates.entering_nomination)
            await callback.message.answer(
                f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 5/10</b>\n\nВведите номинацию:",
                reply_markup=cancel_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback.answer("Не удалось найти ваше имя в базе данных. Пожалуйста, введите ФИО вручную.", show_alert=True)
    elif callback.data == "enter_other_name":
        # Переходим к ручному вводу ФИО
        await state.set_state(ContestParticipationStates.entering_teacher_name)
        await callback.message.answer(
            f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 4/10</b>\n\nВведите ФИО преподавателя:",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("Пожалуйста, выберите один из вариантов.", show_alert=True)
    await callback.answer()

def teacher_name_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора ФИО преподавателя"""
    keyboard = []
    # Получаем имя пользователя из базы данных
    user = db.users.find_one({"telegram_id": user_id})
    if user and user.get("full_name"):
        keyboard.append([InlineKeyboardButton(
            text=f"Использовать моё имя ({user['full_name']})",
            callback_data="use_my_name"
        )])
    keyboard.append([InlineKeyboardButton(
        text="Ввести другое имя",
        callback_data="enter_other_name"
    )])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- Номинация ---
@router.message(ContestParticipationStates.entering_nomination)
async def process_nomination(message: Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id}: ввёл номинацию '{message.text.strip()}'")
    await state.update_data(nomination=message.text.strip())
    await state.set_state(ContestParticipationStates.selecting_participation_form)
    await message.answer(
        f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 6/10</b>\n\nВыберите форму участия:",
        reply_markup=with_cancel_keyboard(participation_form_keyboard()),
        parse_mode="HTML"
    )

def participation_form_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=form, callback_data=form)] for form in PARTICIPATION_FORMS]
    )

# --- Форма участия ---
@router.callback_query(ContestParticipationStates.selecting_participation_form)
async def process_participation_form(callback: CallbackQuery, state: FSMContext):
    form = callback.data
    if form not in PARTICIPATION_FORMS:
        logger.warning(f"Пользователь {callback.from_user.id}: выбрал некорректную форму участия '{form}'")
        await callback.answer("Выберите форму из списка.", show_alert=True)
        return
    logger.info(f"Пользователь {callback.from_user.id}: выбрал форму участия {form}")
    await state.update_data(participation_form=form)
    await state.set_state(ContestParticipationStates.selecting_participant_type)
    await callback.message.answer(
        f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 7/10</b>\n\nКто участвует?",
        reply_markup=with_cancel_keyboard(participant_type_keyboard()),
        parse_mode="HTML"
    )
    await callback.answer()

def participant_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=ptype, callback_data=ptype)] for ptype in PARTICIPANT_TYPES]
    )

# --- ФИО студента ---
@router.message(ContestParticipationStates.entering_student_name)
async def process_student_name(message: Message, state: FSMContext):
    if message.text == "/done_students":
        data = await state.get_data()
        students = data.get("students", [])
        if not students:
            await message.answer("Вы не добавили ни одного студента. Пожалуйста, добавьте хотя бы одного студента или выберите тип участника 'Преподаватель'.")
            return
        
        # Сохраняем участие для каждого студента
        for student in students:
            await save_contest_participation(
                contest_id=data["contest_id"],
                contest_name=data["contest_name"],
                date=data["date"],
                level=data["level"],
                teacher_name=data["teacher_name"],
                nomination=data["nomination"],
                participation_form=data["participation_form"],
                participant_type=data["participant_type"],
                student_name=student["name"],
                group=student["group"],
                result=data["result"],
                confirmation_files=student.get("confirmation_files", []),
                user_id=message.from_user.id
            )
        
        await message.answer(
            "✅ Участие в конкурсе успешно сохранено для всех студентов! Спасибо за заполнение!\n\n"
            "Если хотите добавить ещё одно участие — выберите снова 'Добавить участие' в меню.",
            parse_mode="HTML"
        )
        await state.clear()
        return

    student_name = message.text.strip()
    if not student_name:
        await message.answer("Пожалуйста, введите ФИО студента.")
        return
        
    logger.info(f"Пользователь {message.from_user.id}: ввёл ФИО студента '{student_name}'")
    await state.set_state(ContestParticipationStates.entering_group)
    await state.update_data(current_student_name=student_name)
    
    # Отправляем сообщение с клавиатурой для ввода группы
    msg = await message.answer(
        f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 8/10</b>\n\n"
        f"Введите группу для студента {student_name}:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    # Сохраняем ID сообщения для последующего обновления
    await state.update_data(last_message_id=msg.message_id)

# --- Группа ---
@router.message(ContestParticipationStates.entering_group)
async def process_group(message: Message, state: FSMContext):
    data = await state.get_data()
    group = message.text.strip()
    current_student_name = data.get("current_student_name")
    last_message_id = data.get("last_message_id")
    
    if not group:
        await message.answer("Пожалуйста, введите группу студента.")
        return
    
    # Добавляем студента в список
    students = data.get("students", [])
    
    # Если есть предыдущие студенты, копируем confirmation_files от последнего студента
    confirmation_files = []
    if students:
        last_student = students[-1]
        confirmation_files = last_student.get("confirmation_files", [])
    
    students.append({
        "name": current_student_name,
        "group": group,
        "confirmation_files": confirmation_files  # Используем скопированные файлы
    })
    await state.update_data(students=students)
    
    logger.info(f"Пользователь {message.from_user.id}: ввёл группу '{group}' для студента {current_student_name}")
    logger.info(f"Скопированы confirmation_files от предыдущего студента: {confirmation_files}")
    
    # Если это первый студент, запрашиваем результат
    if len(students) == 1:
        await state.set_state(ContestParticipationStates.entering_result)
        await message.answer(
            f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 9/10</b>\n\n"
            "Введите результат участия (например: Диплом I степени):",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML"
        )
    else:
        # Если это не первый студент, возвращаемся к вводу имени студента
        await state.set_state(ContestParticipationStates.entering_student_name)
        # Обновляем существующее сообщение
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_message_id,
                text=f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 8/10</b>\n\n"
                     f"Введите ФИО следующего студента или отправьте /done_students для завершения:",
                reply_markup=cancel_keyboard(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения: {e}")
            # Если не удалось обновить, отправляем новое
            msg = await message.answer(
                f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 8/10</b>\n\n"
                f"Введите ФИО следующего студента или отправьте /done_students для завершения:",
                reply_markup=cancel_keyboard(),
                parse_mode="HTML"
            )
            await state.update_data(last_message_id=msg.message_id)

# --- Результат ---
@router.message(ContestParticipationStates.entering_result)
async def process_result(message: Message, state: FSMContext):
    result = message.text.strip()
    logger.info(f"Пользователь {message.from_user.id}: ввёл результат '{result}'")
    await state.update_data(result=result)
    data = await state.get_data()
    
    # Переходим к загрузке фото для всех типов участников
    await state.set_state(ContestParticipationStates.uploading_confirmation_file)
    await state.update_data(confirmation_files=[])  # Инициализируем пустой список для фото
    msg = await message.answer(
        f"{get_summary_text(await state.get_data())}\n\n<b>Шаг 10/10</b>\n\n"
        "Загрузите фото подтверждения участия (диплом, сертификат и т.д.).\n"
        "Вы можете загрузить несколько фото. Когда закончите — напишите /done.",
        reply_markup=with_cancel_keyboard(skip_photo_keyboard()),
        parse_mode="HTML"
    )
    await state.update_data(last_message_id=msg.message_id)

# --- Фото ---
@router.message(ContestParticipationStates.uploading_confirmation_file, F.photo)
async def process_confirmation_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo = message.photo[-1]
    file_id = photo.file_id
    
    logger.info(f"Начало обработки фото. File ID: {file_id}")
    logger.info(f"Текущие данные в состоянии: {data}")
    
    try:
        # Получаем файл
        file = await message.bot.get_file(file_id)
        file_path = file.file_path
        file_name = f"{file_id}.jpg"
        
        logger.info(f"Получен файл из Telegram. Путь: {file_path}")
        
        # Создаем директорию uploads, если её нет
        os.makedirs("uploads", exist_ok=True)
        
        # Скачиваем файл
        upload_path = os.path.join("uploads", file_name)
        logger.info(f"Начинаем скачивание файла в {upload_path}")
        await message.bot.download_file(file_path, upload_path)
        
        if not os.path.exists(upload_path):
            logger.error(f"Файл не был скачан в {upload_path}")
            raise Exception(f"Файл не был скачан в {upload_path}")
        
        logger.info(f"Файл успешно скачан в {upload_path}")
        
        if data["participant_type"] == "Преподаватель":
            # Для преподавателя добавляем в общий список
            confirmation_files = data.get("confirmation_files", [])
            confirmation_files.append(file_name)
            await state.update_data(confirmation_files=confirmation_files)
            logger.info(f"Название файла добавлено в список преподавателя. Текущий список: {confirmation_files}")
        else:
            # Для студента добавляем в список текущего студента
            students = data.get("students", [])
            if students:
                current_student = students[-1]  # Берем последнего добавленного студента
                if "confirmation_files" not in current_student:
                    current_student["confirmation_files"] = []
                current_student["confirmation_files"].append(file_name)
                await state.update_data(students=students)
                logger.info(f"Название файла добавлено в список студента {current_student['name']}. Текущий список: {current_student['confirmation_files']}")
        
        # Проверяем, что данные действительно обновлены
        updated_data = await state.get_data()
        logger.info(f"Данные в состоянии после обновления: {updated_data}")
        
        logger.info(f"Пользователь {message.from_user.id}: добавил фото {file_name}")
        
        # Отправляем сообщение об успешной загрузке
        await message.answer("✅ Фото успешно загружено и сохранено!")
        
        # Отправляем новое сообщение с информацией
        if data["participant_type"] == "Преподаватель":
            confirmation_files = updated_data.get("confirmation_files", [])
            await message.answer(
                f"{get_summary_text(updated_data)}\n\n"
                f"Фото получено. Всего загружено фото: {len(confirmation_files)}.\n"
                f"Если хотите добавить ещё — отправьте ещё фото.\n"
                f"Когда закончите — напишите /done.",
                reply_markup=cancel_keyboard(),
                parse_mode="HTML"
            )
        else:
            students = updated_data.get("students", [])
            if students:
                current_student = students[-1]
                await message.answer(
                    f"{get_summary_text(updated_data)}\n\n"
                    f"Фото получено для студента {current_student['name']}. "
                    f"Всего загружено фото: {len(current_student.get('confirmation_files', []))}.\n"
                    f"Если хотите добавить ещё — отправьте ещё фото.\n"
                    f"Когда закончите — напишите /done.",
                    reply_markup=cancel_keyboard(),
                    parse_mode="HTML"
                )
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {str(e)}")
        logger.error(f"Тип ошибки: {type(e)}")
        logger.error(f"Детали ошибки: {e.__dict__ if hasattr(e, '__dict__') else 'Нет дополнительных деталей'}")
        await message.answer(
            "❌ Произошла ошибка при сохранении фото. Пожалуйста, попробуйте ещё раз или пропустите загрузку фото.",
            reply_markup=with_cancel_keyboard(skip_photo_keyboard())
        )

@router.message(ContestParticipationStates.uploading_confirmation_file, Command("done"))
async def finish_uploading_files(message: Message, state: FSMContext):
    data = await state.get_data()
    
    if data["participant_type"] == "Преподаватель":
        # Если участник - преподаватель, сохраняем участие
        await save_contest_participation(
            contest_id=data["contest_id"],
            contest_name=data["contest_name"],
            date=data["date"],
            level=data["level"],
            teacher_name=data["teacher_name"],
            nomination=data["nomination"],
            participation_form=data["participation_form"],
            participant_type=data["participant_type"],
            student_name=data["student_name"],
            group=data["group"],
            result=data["result"],
            confirmation_files=data.get("confirmation_files", []),
            user_id=message.from_user.id
        )
        await message.answer(
            "✅ Участие в конкурсе успешно сохранено! Спасибо за заполнение!\n\n"
            "Если хотите добавить ещё одно участие — выберите снова 'Добавить участие' в меню.",
            parse_mode="HTML"
        )
        await state.clear()
        return

    students = data.get("students", [])
    if not students:
        logger.error(f"Пользователь {message.from_user.id}: попытка завершить загрузку фото без студентов")
        await message.answer("Ошибка: не найдены студенты. Пожалуйста, начните процесс заново через /contest")
        await state.clear()
        return
        
    logger.info(f"Пользователь {message.from_user.id}: завершил загрузку фото для всех студентов")
    
    # Отправляем сообщение о завершении загрузки
    await message.answer(
        f"{get_summary_text(await state.get_data())}\n\n"
        f"Фото для всех студентов сохранены.\n\n"
        f"Введите ФИО следующего студента или отправьте /done_students для завершения:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    
    # Возвращаемся к вводу имени студента
    await state.set_state(ContestParticipationStates.entering_student_name)

@router.callback_query(ContestParticipationStates.uploading_confirmation_file, F.data == "skip_photo")
async def skip_photo_upload(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    if data["participant_type"] == "Преподаватель":
        # Если участник - преподаватель, сохраняем участие без фото
        await save_contest_participation(
            contest_id=data["contest_id"],
            contest_name=data["contest_name"],
            date=data["date"],
            level=data["level"],
            teacher_name=data["teacher_name"],
            nomination=data["nomination"],
            participation_form=data["participation_form"],
            participant_type=data["participant_type"],
            student_name=data["student_name"],
            group=data["group"],
            result=data["result"],
            confirmation_files=[],
            user_id=callback.from_user.id
        )
        await callback.message.answer(
            "✅ Участие в конкурсе успешно сохранено без фото! Спасибо за заполнение!\n\n"
            "Если хотите добавить ещё одно участие — выберите снова 'Добавить участие' в меню.",
            parse_mode="HTML"
        )
        await state.clear()
        await callback.answer()
        return

    students = data.get("students", [])
    if not students:
        logger.error(f"Пользователь {callback.from_user.id}: попытка пропустить загрузку фото без студентов")
        await callback.message.answer("Ошибка: не найдены студенты. Пожалуйста, начните процесс заново через /contest")
        await state.clear()
        await callback.answer()
        return
        
    logger.info(f"Пользователь {callback.from_user.id}: пропустил загрузку фото для всех студентов")
    
    # Отправляем новое сообщение
    await callback.message.answer(
        f"{get_summary_text(await state.get_data())}\n\n"
        f"Загрузка фото пропущена.\n\n"
        f"Введите ФИО следующего студента или отправьте /done_students для завершения:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    
    # Возвращаемся к вводу имени студента
    await state.set_state(ContestParticipationStates.entering_student_name)
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback.from_user.id}: отменил заполнение на этапе {await state.get_state()}")
    await state.clear()
    await callback.message.edit_text("❌ Заполнение участия в конкурсе отменено.\n\nВы всегда можете начать заново, выбрав 'Добавить участие' в меню.")
    await callback.answer()

# Fallback-обработчик для выбора конкурса вне FSM
@router.callback_query(F.data.startswith("participate_contest_"))
async def fallback_participate_contest(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    contest_id = callback.data.split("_", 2)[2]
    logger.warning(f"Пользователь {callback.from_user.id} попытался выбрать конкурс participate_contest_{contest_id} вне FSM (state={current_state})")
    
    try:
        # Проверяем, существует ли конкурс
        contest = db.contests.find_one({"_id": ObjectId(contest_id)})
        if not contest:
            logger.error(f"Пользователь {callback.from_user.id}: конкурс {contest_id} не найден в базе")
            await callback.answer("Конкурс не найден в базе.", show_alert=True)
            return
            
        if current_state != ContestParticipationStates.selecting_contest.state:
            logger.error(f"Ошибка выбора конкурса вне FSM: пользователь {callback.from_user.id}, state={current_state}, ожидалось={ContestParticipationStates.selecting_contest.state}")
            await callback.answer(
                "Похоже, вы начали заполнение не с самого начала или использовали старую кнопку. Пожалуйста, выберите 'Добавить участие' в меню и начните заново.",
                show_alert=True
            )
        else:
            logger.info(f"Пользователь {callback.from_user.id}: попытка выбора конкурса в правильном состоянии, но через fallback-обработчик")
            await callback.answer("Пожалуйста, попробуйте выбрать конкурс снова.", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при поиске конкурса в fallback-обработчике: {e}")
        await callback.answer("Произошла ошибка при поиске конкурса.", show_alert=True)
    await callback.answer()

def skip_photo_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⏩ Пропустить", callback_data="skip_photo")]]
    ) 