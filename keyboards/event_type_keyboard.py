from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.self_assessment_utils import get_activity_types
from config import logger

async def get_event_type_keyboard_with_pagination(page: int = 0, items_per_page: int = 5) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с пагинацией для выбора типа мероприятия
    
    Args:
        page: Номер текущей страницы (начиная с 0)
        items_per_page: Количество элементов на странице
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками выбора типа мероприятия
    """
    # Получаем типы мероприятий из базы данных
    event_types = await get_activity_types()
    logger.debug(f"Получено {len(event_types)} типов мероприятий")
    
    # Вычисляем общее количество страниц
    total_pages = (len(event_types) + items_per_page - 1) // items_per_page
    logger.debug(f"Всего страниц: {total_pages}, текущая страница: {page}")
    
    # Вычисляем индексы для текущей страницы
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(event_types))
    logger.debug(f"Индексы элементов на странице: {start_idx} - {end_idx}")
    
    # Создаем клавиатуру
    keyboard = []
    
    # Добавляем кнопки для типов мероприятий текущей страницы
    for code, text in event_types[start_idx:end_idx]:
        # Используем только код мероприятия в callback_data
        callback_data = f"event_{code}"
        
        # Проверяем длину callback_data (максимум 64 байта)
        if len(callback_data.encode('utf-8')) > 64:
            logger.error(f"Callback data слишком длинный: {callback_data} ({len(callback_data.encode('utf-8'))} байт)")
            # Используем только первую часть кода, если он слишком длинный
            code_parts = code.split('.')
            if len(code_parts) > 1:
                callback_data = f"event_{code_parts[0]}"
            else:
                # Если код не содержит точек, используем только первые 10 символов
                callback_data = f"event_{code[:10]}"
            logger.debug(f"Используем сокращенный callback_data: {callback_data}")
        
        logger.debug(f"Создана кнопка: {text} с callback_data: {callback_data}")
        keyboard.append([InlineKeyboardButton(
            text=text,
            callback_data=callback_data
        )])
    
    # Добавляем кнопки навигации, если есть несколько страниц
    nav_buttons = []
    if page > 0:
        callback_data = f"event_page_{page-1}"
        logger.debug(f"Создана кнопка 'Назад' с callback_data: {callback_data}")
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=callback_data
        ))
    if page < total_pages - 1:
        callback_data = f"event_page_{page+1}"
        logger.debug(f"Создана кнопка 'Вперед' с callback_data: {callback_data}")
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=callback_data
        ))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 