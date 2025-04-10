from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.self_assessment_states import SelfAssessmentStates
from utils.self_assessment_utils import save_self_assessment, get_contests_by_type
from keyboards.self_assessment_keyboard import (
    get_event_type_keyboard,
    get_contest_selection_keyboard,
    get_cancel_keyboard
)

router = Router()

@router.message(Command("self_assessment"))
async def cmd_self_assessment(message: Message, state: FSMContext):
    """Обработчик команды /self_assessment"""
    await state.set_state(SelfAssessmentStates.selecting_event_type)
    await message.answer(
        "Выберите тип мероприятия:",
        reply_markup=get_event_type_keyboard()
    )

@router.message(SelfAssessmentStates.selecting_event_type)
async def process_event_type(message: Message, state: FSMContext):
    """Обработка выбора типа мероприятия"""
    event_type = message.text
    
    # Если выбран тип конкурса (2.1.1, 2.1.2, 2.1.3)
    if event_type in ["2.1.1. Призовое место на олимпиаде ФГОС",
                      "2.1.2. Призовое место на олимпиаде профмастерства",
                      "2.1.3. Призовое место на иных олимпиадах"]:
        contests = await get_contests_by_type(event_type)
        await state.update_data(event_type=event_type)
        await state.set_state(SelfAssessmentStates.selecting_contest)
        await message.answer(
            "Выберите конкурс из списка или добавьте новый:",
            reply_markup=get_contest_selection_keyboard(contests)
        )
    else:
        await state.update_data(event_type=event_type)
        await state.set_state(SelfAssessmentStates.entering_event_name)
        await message.answer(
            "Введите название мероприятия:",
            reply_markup=get_cancel_keyboard()
        )

@router.callback_query(SelfAssessmentStates.selecting_contest)
async def process_contest_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора конкурса"""
    if callback.data == "new_contest":
        await state.set_state(SelfAssessmentStates.entering_contest_name)
        await callback.message.answer(
            "Введите название нового конкурса:",
            reply_markup=get_cancel_keyboard()
        )
    else:
        contest_id = callback.data.split("_")[1]
        await state.update_data(contest_id=contest_id)
        await state.set_state(SelfAssessmentStates.entering_event_name)
        await callback.message.answer(
            "Введите название мероприятия:",
            reply_markup=get_cancel_keyboard()
        )

@router.message(SelfAssessmentStates.entering_contest_name)
async def process_contest_name(message: Message, state: FSMContext):
    """Обработка ввода названия нового конкурса"""
    await state.update_data(contest_name=message.text)
    await state.set_state(SelfAssessmentStates.entering_event_name)
    await message.answer(
        "Введите название мероприятия:",
        reply_markup=get_cancel_keyboard()
    )

@router.message(SelfAssessmentStates.entering_event_name)
async def process_event_name(message: Message, state: FSMContext):
    """Обработка ввода названия мероприятия"""
    await state.update_data(event_name=message.text)
    await state.set_state(SelfAssessmentStates.entering_event_description)
    await message.answer(
        "Введите краткую характеристику мероприятия:",
        reply_markup=get_cancel_keyboard()
    )

@router.message(SelfAssessmentStates.entering_event_description)
async def process_event_description(message: Message, state: FSMContext):
    """Обработка ввода характеристики мероприятия"""
    await state.update_data(description=message.text)
    await state.set_state(SelfAssessmentStates.entering_event_result)
    await message.answer(
        "Введите результат участия:",
        reply_markup=get_cancel_keyboard()
    )

@router.message(SelfAssessmentStates.entering_event_result)
async def process_event_result(message: Message, state: FSMContext):
    """Обработка ввода результата участия"""
    await state.update_data(result=message.text)
    await state.set_state(SelfAssessmentStates.entering_social_media_link)
    await message.answer(
        "Введите ссылку на публикацию в соцсетях (если есть) или отправьте 'нет':",
        reply_markup=get_cancel_keyboard()
    )

@router.message(SelfAssessmentStates.entering_social_media_link)
async def process_social_media_link(message: Message, state: FSMContext):
    """Обработка ввода ссылки на публикацию"""
    social_media_link = None if message.text.lower() == "нет" else message.text
    await state.update_data(social_media_link=social_media_link)
    await state.set_state(SelfAssessmentStates.uploading_confirmation_file)
    await message.answer(
        "Отправьте файл подтверждения (грамота, диплом, сертификат):",
        reply_markup=get_cancel_keyboard()
    )

@router.message(SelfAssessmentStates.uploading_confirmation_file, F.document)
async def process_confirmation_file(message: Message, state: FSMContext):
    """Обработка загрузки файла подтверждения"""
    file_id = message.document.file_id
    data = await state.get_data()
    
    # Сохраняем данные в базу
    await save_self_assessment(
        user_id=message.from_user.id,
        event_type=data["event_type"],
        event_name=data["event_name"],
        description=data["description"],
        result=data["result"],
        social_media_link=data["social_media_link"],
        confirmation_file_id=file_id,
        contest_id=data.get("contest_id")
    )
    
    await state.clear()
    await message.answer(
        "Данные успешно сохранены!",
        reply_markup=get_event_type_keyboard()
    )

@router.message(SelfAssessmentStates.uploading_confirmation_file, F.photo)
async def process_confirmation_photo(message: Message, state: FSMContext):
    """Обработка загрузки фото подтверждения"""
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    
    # Сохраняем данные в базу
    await save_self_assessment(
        user_id=message.from_user.id,
        event_type=data["event_type"],
        event_name=data["event_name"],
        description=data["description"],
        result=data["result"],
        social_media_link=data["social_media_link"],
        confirmation_file_id=file_id,
        contest_id=data.get("contest_id")
    )
    
    await state.clear()
    await message.answer(
        "Данные успешно сохранены!",
        reply_markup=get_event_type_keyboard()
    ) 