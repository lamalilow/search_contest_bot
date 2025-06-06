import os
from datetime import datetime
from bson import ObjectId

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import logger
from utils.self_assessment_utils import save_self_assessment, get_contests_by_type, get_activity_types
from utils.file_utils import compress_and_save_image
from keyboards.contest_keyboard import get_contest_selection_keyboard, get_cancel_keyboard
from utils.self_assessment_states import SelfAssessmentStates
from keyboards.event_type_keyboard import get_event_type_keyboard_with_pagination

router = Router()

# Создаем папку для загрузки файлов, если она не существует
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@router.message(Command("self_assessment"))
async def cmd_self_assessment(message: Message, state: FSMContext):
    """Обработчик команды /self_assessment"""
    logger.info(f"Пользователь {message.from_user.id} ({message.from_user.full_name}) начал заполнение листа самообследования")
    await state.set_state(SelfAssessmentStates.selecting_event_type)
    await state.update_data(confirmation_files=[])  # Инициализируем список файлов
    
    # Более дружелюбное и подробное сообщение
    await message.answer(
        "📝 ЗАПОЛНЕНИЕ ЛИСТА САМООБСЛЕДОВАНИЯ\n\n"
        "Сейчас Вам нужно выбрать тип мероприятия из списка ниже.\n"
        "Просто нажмите на нужную кнопку 👇\n\n"
        "Если нужный тип мероприятия не отображается, нажмите кнопку «Вперед ▶️» для просмотра остальных вариантов.",
        reply_markup=await get_event_type_keyboard_with_pagination()
    )

@router.callback_query(lambda query: query.data.startswith("event_page_"))
async def process_event_type_pagination(callback: CallbackQuery, state: FSMContext):
    """Обработка пагинации списка типов мероприятий"""
    # Получаем номер страницы из callback_data
    page = int(callback.data.split("_")[2])
    logger.info(f"Пользователь {callback.from_user.id} перешел на страницу {page} списка типов мероприятий")
    
    # Обновляем сообщение с новой клавиатурой
    await callback.message.edit_text(
        "📝 ЗАПОЛНЕНИЕ ЛИСТА САМООБСЛЕДОВАНИЯ\n\n"
        "Выберите тип мероприятия, нажав на соответствующую кнопку ниже 👇\n\n"
        "Используйте кнопки «◀️ Назад» и «Вперед ▶️» для навигации между страницами с доступными типами мероприятий.",
        reply_markup=await get_event_type_keyboard_with_pagination(page=page)
    )

@router.callback_query(lambda query: query.data.startswith("event_") and not query.data.startswith("event_page_"))
async def process_event_type_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа мероприятия через callback"""
    # Получаем тип мероприятия из callback_data
    event_code = callback.data.replace("event_", "")
    logger.info(f"Пользователь {callback.from_user.id} выбрал тип мероприятия: {event_code}")
    
    # Получаем типы мероприятий из базы данных
    event_types = await get_activity_types()
    
    # Ищем полный код мероприятия
    full_event_code = None
    for code, _ in event_types:
        # Проверяем, начинается ли код с выбранного кода
        if code.startswith(event_code):
            full_event_code = code
            break
    
    if not full_event_code:
        logger.error(f"Не найден полный код для: {event_code}")
        await callback.answer("Произошла ошибка при выборе типа мероприятия.")
        return
    
    # Получаем полное название типа мероприятия
    event_types_dict = dict(event_types)
    event_type = event_types_dict.get(full_event_code, "Неизвестный тип мероприятия")
    logger.info(f"Полный код: {full_event_code}, полное название: {event_type}")
    
    # Если выбран тип конкурса (2.1.1, 2.1.2, 2.1.3)
    if full_event_code in ["2.1.1", "2.1.2", "2.1.3"]:
        logger.info(f"Пользователь {callback.from_user.id} выбрал тип конкурса: {full_event_code}")
        # Получаем все конкурсы без фильтрации по типу
        contests = await get_contests_by_type()
        logger.info(f"Получено {len(contests)} конкурсов")
        await state.update_data(event_type=event_type)
        await state.set_state(SelfAssessmentStates.selecting_contest)
        
        # Получаем клавиатуру с выбором конкурса
        contest_keyboard = get_contest_selection_keyboard(contests)
        
        # Добавляем кнопку "Назад" в конец клавиатуры
        contest_keyboard.inline_keyboard.append([InlineKeyboardButton(
            text="◀️ Назад к выбору мероприятия", 
            callback_data="back_to_event_selection"
        )])
        
        await callback.message.edit_text(
            f"✅ Вы выбрали: {event_type}\n\n"
            f"Теперь выберите конкурс из списка ниже или добавьте новый, нажав на кнопку внизу 👇",
            reply_markup=contest_keyboard
        )
    else:
        logger.info(f"Пользователь {callback.from_user.id} выбрал обычный тип мероприятия: {full_event_code}")
        await state.update_data(event_type=event_type)
        await state.set_state(SelfAssessmentStates.entering_event_name)
        # Создаем инлайн-клавиатуру с кнопкой отмены и кнопкой "Назад"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к выбору мероприятия", callback_data="back_to_event_selection")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ])
        await callback.message.edit_text(
            f"✅ Вы выбрали: {event_type}\n\n"
            f"Теперь введите название мероприятия (напишите текстом):\n\n"
            f"Например: \"Городская олимпиада по математике\" или \"Конкурс чтецов\"",
            reply_markup=keyboard
        )

@router.callback_query(SelfAssessmentStates.selecting_contest, lambda query: query.data.startswith("self_contest_") or query.data == "new_contest")
async def process_contest_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора конкурса"""
    if callback.data == "new_contest":
        logger.info(f"Пользователь {callback.from_user.id} выбрал создание нового конкурса")
        await state.set_state(SelfAssessmentStates.entering_contest_name)
        await callback.message.answer(
            "📝 Вы выбрали добавление нового конкурса\n\n"
            "Введите название нового конкурса (напишите текстом):",
            reply_markup=get_cancel_keyboard()
        )
    else:
        try:
            # Получаем ID конкурса из callback data
            contest_id = callback.data.split("_")[2]  # Теперь ID в 3-й части (self_contest_ID)
            logger.info(f"Пользователь {callback.from_user.id} выбрал существующий конкурс с ID: {contest_id}")
            
            # Получаем информацию о выбранном конкурсе из базы данных
            from services.database import db
            
            # Пробуем использовать ObjectId, если это возможно
            try:
                oid = ObjectId(contest_id)
                contest = db.contests.find_one({"_id": oid})
                logger.info(f"Поиск конкурса по ObjectId: {oid}, результат: {contest is not None}")
            except:
                # Если не удалось преобразовать в ObjectId, ищем по строковому ID
                logger.info(f"Не удалось преобразовать ID {contest_id} в ObjectId, ищем по строковому ID")
                contest = db.contests.find_one({"_id": contest_id})
                logger.info(f"Поиск конкурса по строковому ID: {contest_id}, результат: {contest is not None}")
            
            if contest:
                # Сохраняем ID и название конкурса в состоянии
                contest_name = contest.get("name", "")
                logger.info(f"Найден конкурс с названием: {contest_name}")
                
                await state.update_data(
                    contest_id=contest_id,
                    event_name=contest_name  # Автоматически устанавливаем название мероприятия
                )
                
                # Переходим сразу к описанию мероприятия
                await state.set_state(SelfAssessmentStates.entering_event_description)
                
                # Отвечаем пользователю новым сообщением
                await callback.message.delete()  # Удаляем старое сообщение со списком
                await callback.message.answer(
                    f"✅ Вы выбрали конкурс: {contest_name}\n\n"
                    f"Теперь введите краткую характеристику мероприятия (напишите текстом):\n\n"
                    f"Например: \"Участие в дистанционной олимпиаде\" или \"Проведение мастер-класса\"",
                    reply_markup=get_cancel_keyboard()
                )
                # Отвечаем на callback, чтобы убрать часы загрузки
                await callback.answer()
            else:
                # Если конкурс не найден, выводим сообщение об ошибке
                logger.error(f"Конкурс с ID {contest_id} не найден в базе данных")
                await callback.answer("Ошибка: конкурс не найден", show_alert=True)
                
                # Предлагаем пользователю ввести название самостоятельно
                await state.update_data(contest_id=contest_id)
                await state.set_state(SelfAssessmentStates.entering_event_name)
                await callback.message.answer(
                    "К сожалению, не удалось найти выбранный конкурс.\n\n"
                    "Пожалуйста, введите название мероприятия (напишите текстом):",
                    reply_markup=get_cancel_keyboard()
                )
        except Exception as e:
            logger.error(f"Ошибка при обработке выбора конкурса: {str(e)}")
            await callback.answer("Произошла ошибка при выборе конкурса")
            await callback.message.answer(
                "К сожалению, произошла ошибка.\n\n"
                "Пожалуйста, введите название мероприятия (напишите текстом):",
                reply_markup=get_cancel_keyboard()
            )
            await state.set_state(SelfAssessmentStates.entering_event_name)

@router.message(SelfAssessmentStates.entering_contest_name)
async def process_contest_name(message: Message, state: FSMContext):
    """Обработка ввода названия нового конкурса"""
    contest_name = message.text
    logger.info(f"Пользователь {message.from_user.id} ввел название нового конкурса: {contest_name}")
    await state.update_data(contest_name=contest_name)
    await state.set_state(SelfAssessmentStates.entering_event_name)
    await message.answer(
        f"✅ Вы добавили новый конкурс: {contest_name}\n\n"
        f"Теперь введите название мероприятия (напишите текстом):\n\n"
        f"Например: \"Районная олимпиада по информатике\" или \"Конкурс чтецов\"",
        reply_markup=get_cancel_keyboard()
    )

@router.message(SelfAssessmentStates.entering_event_name)
async def process_event_name(message: Message, state: FSMContext):
    """Обработка ввода названия мероприятия"""
    event_name = message.text
    logger.info(f"Пользователь {message.from_user.id} ввел название мероприятия: {event_name}")
    await state.update_data(event_name=event_name)
    await state.set_state(SelfAssessmentStates.entering_event_description)
    await message.answer(
        f"✅ Название мероприятия: {event_name}\n\n"
        f"Теперь введите краткую характеристику мероприятия (напишите текстом):\n\n"
        f"Например: \"Участие в дистанционной олимпиаде\" или \"Проведение мастер-класса\"",
        reply_markup=get_cancel_keyboard()
    )

@router.message(SelfAssessmentStates.entering_event_description)
async def process_event_description(message: Message, state: FSMContext):
    """Обработка ввода характеристики мероприятия"""
    description = message.text
    logger.info(f"Пользователь {message.from_user.id} ввел характеристику мероприятия: {description[:50]}...")
    await state.update_data(description=description)
    await state.set_state(SelfAssessmentStates.entering_event_result)
    await message.answer(
        f"✅ Характеристика мероприятия сохранена\n\n"
        f"Теперь введите результат участия (напишите текстом):\n\n"
        f"Например: \"Диплом I степени\" или \"Сертификат участника\"",
        reply_markup=get_cancel_keyboard()
    )

@router.message(SelfAssessmentStates.entering_event_result)
async def process_event_result(message: Message, state: FSMContext):
    """Обработка ввода результата участия"""
    result = message.text
    logger.info(f"Пользователь {message.from_user.id} ввел результат участия: {result[:50]}...")
    await state.update_data(result=result)
    await state.set_state(SelfAssessmentStates.entering_social_media_link)
    await message.answer(
        f"✅ Результат участия: {result}\n\n"
        f"Теперь введите ссылку на публикацию в соцсетях (если есть)\n"
        f"или напишите слово \"нет\", если публикации нет",
        reply_markup=get_cancel_keyboard()
    )

@router.message(SelfAssessmentStates.entering_social_media_link)
async def process_social_media_link(message: Message, state: FSMContext):
    """Обработка ввода ссылки на публикацию"""
    social_media_link = None if message.text.lower() == "нет" else message.text
    logger.info(f"Пользователь {message.from_user.id} ввел ссылку на публикацию: {social_media_link if social_media_link else 'нет'}")
    await state.update_data(social_media_link=social_media_link)
    await state.set_state(SelfAssessmentStates.uploading_confirmation_file)
    
    # Создаем клавиатуру с кнопкой "Продолжить без фотографии" и кнопкой "Отмена"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Продолжить без фотографии", callback_data="skip_photo")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])
    
    await message.answer(
        f"✅ Информация о публикации сохранена\n\n"
        f"Теперь отправьте фотографию документа-подтверждения:\n"
        f"📱 Сфотографируйте грамоту, диплом или сертификат и отправьте фото\n\n"
        f"❗ <b>Обратите внимание</b>: для некоторых видов деятельности фотография может быть необязательной.\n"
        f"Если у вас нет документа-подтверждения, вы можете нажать кнопку «Продолжить без фотографии».\n\n"
        f"❓ Как сделать фото: нажмите на значок 📎 или 📷 рядом с полем ввода текста, "
        f"затем выберите 'Камера' или 'Галерея'",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.message(SelfAssessmentStates.uploading_confirmation_file, F.photo)
async def process_confirmation_photo(message: Message, state: FSMContext):
    """Обработка загрузки фото подтверждения"""
    file_id = message.photo[-1].file_id
    file = await message.bot.get_file(file_id)
    file_path = file.file_path
    
    # Создаем уникальное имя файла с временной меткой
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    original_name = f"photo_{timestamp}.jpg"
    unique_filename = f"{file_id}.jpg"
    
    logger.info(f"Пользователь {message.from_user.id} загружает фото подтверждения: {original_name} (сохранено как {unique_filename})")
    
    # Полный путь к целевому файлу
    target_file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    # Скачиваем файл во временную директорию
    temp_file_path = os.path.join(UPLOAD_FOLDER, f"temp_{unique_filename}")
    await message.bot.download_file(file_path, temp_file_path)
    
    # Сжимаем изображение
    success = compress_and_save_image(temp_file_path, target_file_path)
    if not success:
        # В случае ошибки, просто перемещаем файл
        os.rename(temp_file_path, target_file_path)
        logger.warning(f"Не удалось сжать фото {original_name}, сохранен оригинал")
    else:
        # Удаляем временный файл
        os.remove(temp_file_path)
    
    logger.info(f"Фото {original_name} успешно обработано и сохранено в папку {UPLOAD_FOLDER}")
    
    # Получаем текущие данные из состояния
    data = await state.get_data()
    confirmation_files = data.get("confirmation_files", [])
    
    # Сохраняем информацию о файле (ID и оригинальное имя)
    file_info = {
        "file_id": file_id,
        "original_name": original_name,
        "saved_name": unique_filename
    }
    confirmation_files.append(file_info)
    
    # Обновляем состояние
    await state.update_data(confirmation_files=confirmation_files)
    logger.info(f"Фото {original_name} добавлено в список подтверждающих документов. Всего файлов: {len(confirmation_files)}")
    
    await message.answer(
        f"✅ Фото успешно загружено (всего файлов: {len(confirmation_files)})\n\n"
        f"Вы можете:\n"
        f"1️⃣ Отправить еще одно фото, если нужно\n"
        f"2️⃣ Нажать команду /done, чтобы завершить заполнение",
        reply_markup=get_cancel_keyboard()
    )

@router.message(SelfAssessmentStates.uploading_confirmation_file, Command("done"))
async def finish_uploading_files(message: Message, state: FSMContext):
    """Завершение загрузки файлов"""
    logger.info(f"Пользователь {message.from_user.id} завершил загрузку файлов")
    data = await state.get_data()
    
    # Получаем количество загруженных файлов
    confirmation_files = data.get("confirmation_files", [])
    files_count = len(confirmation_files)
    
    if files_count == 0:
        # Вместо требования добавить файлы, сообщаем что будет продолжено без них
        # и спрашиваем подтверждение
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, продолжить без фотографий", callback_data="confirm_no_photos")],
            [InlineKeyboardButton(text="❌ Нет, добавить фотографии", callback_data="add_photos")]
        ])
        
        await message.answer(
            "❗ Вы не загрузили ни одного файла подтверждения\n\n"
            "Для некоторых видов деятельности фотография может быть необязательной.\n"
            "Хотите продолжить без загрузки фотографий?",
            reply_markup=keyboard
        )
        return
    
    # Сохраняем данные в базу
    await save_self_assessment(
        user_id=message.from_user.id,
        event_type=data.get("event_type"),
        event_name=data.get("event_name"),
        description=data.get("description"),
        result=data.get("result"),
        social_media_link=data.get("social_media_link"),
        confirmation_files=confirmation_files,
        contest_id=data.get("contest_id")
    )
    logger.info(f"Данные самообследования пользователя {message.from_user.id} успешно сохранены в базу")
    
    await message.answer(
        f"🎉 ГОТОВО! 🎉\n\n"
        f"Ваш лист самообследования успешно заполнен и сохранен!\n"
        f"Вы загрузили {files_count} {get_files_word(files_count)}\n\n"
        f"Спасибо за использование бота!",
        reply_markup=None
    )
    await state.clear()

@router.callback_query(SelfAssessmentStates.uploading_confirmation_file, lambda query: query.data == "confirm_no_photos")
async def confirm_no_photos(callback: CallbackQuery, state: FSMContext):
    """Подтверждение сохранения без фотографий"""
    logger.info(f"Пользователь {callback.from_user.id} подтвердил сохранение без фотографий")
    data = await state.get_data()
    
    # Сохраняем данные в базу без фотографий
    await save_self_assessment(
        user_id=callback.from_user.id,
        event_type=data.get("event_type"),
        event_name=data.get("event_name"),
        description=data.get("description"),
        result=data.get("result"),
        social_media_link=data.get("social_media_link"),
        confirmation_files=[],
        contest_id=data.get("contest_id")
    )
    logger.info(f"Данные самообследования пользователя {callback.from_user.id} успешно сохранены в базу (без фотографий)")
    
    try:
        await callback.message.edit_text(
            f"🎉 ГОТОВО! 🎉\n\n"
            f"Ваш лист самообследования успешно заполнен и сохранен без фотографий.\n\n"
            f"Спасибо за использование бота!",
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Не удалось отредактировать сообщение: {str(e)}")
        await callback.message.answer(
            f"🎉 ГОТОВО! 🎉\n\n"
            f"Ваш лист самообследования успешно заполнен и сохранен без фотографий.\n\n"
            f"Спасибо за использование бота!"
        )
    
    await callback.answer("Сохранено без фотографий")
    await state.clear()

@router.callback_query(SelfAssessmentStates.uploading_confirmation_file, lambda query: query.data == "add_photos")
async def add_photos(callback: CallbackQuery):
    """Возврат к загрузке фотографий"""
    logger.info(f"Пользователь {callback.from_user.id} решил добавить фотографии")
    
    await callback.message.edit_text(
        "📱 Отправьте фотографию документа-подтверждения\n\n"
        "Как это сделать:\n"
        "1️⃣ Нажмите на значок 📎 или 📷 рядом с полем ввода текста\n"
        "2️⃣ Выберите пункт 'Камера' для создания фото или 'Галерея' для выбора существующей фотографии\n"
        "3️⃣ Сделайте или выберите фото и отправьте его\n\n"
        "Либо нажмите на кнопку «Продолжить без фотографии» если такая возможность доступна для выбранного типа мероприятия.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 Продолжить без фотографии", callback_data="skip_photo")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ])
    )
    
    await callback.answer()

def get_files_word(count):
    """Возвращает правильное склонение слова 'файл' в зависимости от числа"""
    if count % 10 == 1 and count % 100 != 11:
        return "файл"
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return "файла"
    else:
        return "файлов"

@router.callback_query(lambda query: query.data == "cancel")
async def process_cancel_universal(callback: CallbackQuery, state: FSMContext):
    """Универсальный обработчик нажатия кнопки отмены, работающий во всех состояниях"""
    current_state = await state.get_state()
    logger.debug(f"Пользователь {callback.from_user.id} нажал кнопку отмены в состоянии {current_state}")
    
    # Очищаем состояние пользователя
    await state.clear()
    
    try:
        # Пробуем изменить текст сообщения
        await callback.message.edit_text(
            "❌ Заполнение листа самообследования отменено\n\n"
            "Вы всегда можете начать заново, используя команду /self_assessment",
            reply_markup=None
        )
    except Exception as e:
        # Если не удалось изменить текст, отправляем новое сообщение
        logger.error(f"Ошибка при обработке отмены: {str(e)}")
        await callback.message.answer(
            "❌ Заполнение листа самообследования отменено\n\n"
            "Вы всегда можете начать заново, используя команду /self_assessment"
        )
    
    # Отвечаем на callback запрос, чтобы убрать часы загрузки
    try:
        await callback.answer("Отменено")
    except Exception as e:
        logger.error(f"Не удалось ответить на callback: {str(e)}")

@router.message(SelfAssessmentStates.uploading_confirmation_file)
async def process_unsupported_content(message: Message, state: FSMContext):
    """Обработка неподдерживаемого содержимого при загрузке подтверждения"""
    logger.info(f"Пользователь {message.from_user.id} отправил неподдерживаемый контент в состоянии загрузки подтверждения")
    
    await message.answer(
        "❗ Необходимо отправить фотографию документа\n\n"
        "Как это сделать:\n"
        "1️⃣ Нажмите на значок 📎 или 📷 рядом с полем ввода текста\n"
        "2️⃣ Выберите пункт 'Камера' для создания фото или 'Галерея' для выбора существующей фотографии\n"
        "3️⃣ Сделайте или выберите фото и отправьте его\n\n"
        "Если Вы уже загрузили все документы и хотите завершить, отправьте команду /done",
        reply_markup=get_cancel_keyboard()
    )

@router.callback_query(SelfAssessmentStates.uploading_confirmation_file, lambda query: query.data == "skip_photo")
async def skip_photo_upload(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска загрузки фотографии"""
    logger.info(f"Пользователь {callback.from_user.id} решил продолжить без загрузки фотографии")
    data = await state.get_data()
    
    # Получаем текущие данные и тип мероприятия
    event_type = data.get("event_type")
    
    # Сохраняем данные в базу без фотографий
    await save_self_assessment(
        user_id=callback.from_user.id,
        event_type=event_type,
        event_name=data.get("event_name"),
        description=data.get("description"),
        result=data.get("result"),
        social_media_link=data.get("social_media_link"),
        confirmation_files=[],
        contest_id=data.get("contest_id")
    )
    logger.info(f"Данные самообследования пользователя {callback.from_user.id} успешно сохранены в базу (без фотографий)")
    
    try:
        await callback.message.edit_text(
            f"🎉 ГОТОВО! 🎉\n\n"
            f"Ваш лист самообследования успешно заполнен и сохранен без фотографий.\n\n"
            f"Спасибо за использование бота!",
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Не удалось отредактировать сообщение: {str(e)}")
        await callback.message.answer(
            f"🎉 ГОТОВО! 🎉\n\n"
            f"Ваш лист самообследования успешно заполнен и сохранен без фотографий.\n\n"
            f"Спасибо за использование бота!"
        )
    
    # Отвечаем на callback запрос
    await callback.answer("Сохранено без фотографий")
    await state.clear()

@router.callback_query(lambda query: query.data == "back_to_event_selection")
async def back_to_event_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки возврата к выбору типа мероприятия"""
    logger.info(f"Пользователь {callback.from_user.id} вернулся к выбору типа мероприятия")
    
    # Установка состояния выбора типа мероприятия
    await state.set_state(SelfAssessmentStates.selecting_event_type)
    
    # Отображаем список типов мероприятий снова
    await callback.message.edit_text(
        "📝 ЗАПОЛНЕНИЕ ЛИСТА САМООБСЛЕДОВАНИЯ\n\n"
        "Выберите тип мероприятия из списка ниже.\n"
        "Просто нажмите на нужную кнопку 👇\n\n"
        "Если нужный тип мероприятия не отображается, нажмите кнопку «Вперед ▶️» для просмотра остальных вариантов.",
        reply_markup=await get_event_type_keyboard_with_pagination()
    )
    
    # Отвечаем на callback запрос
    await callback.answer() 