from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_contest_selection_keyboard(contests, page: int = 0, items_per_page: int = 5) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с пагинацией для выбора конкурса
    
    Args:
        contests: Список конкурсов
        page: Номер текущей страницы (начиная с 0)
        items_per_page: Количество элементов на странице
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками выбора конкурса
    """
    # Вычисляем общее количество страниц
    total_pages = (len(contests) + items_per_page - 1) // items_per_page
    
    # Вычисляем индексы для текущей страницы
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(contests))
    
    # Создаем клавиатуру
    keyboard = []
    
    # Добавляем кнопки для конкурсов текущей страницы
    for contest in contests[start_idx:end_idx]:
        keyboard.append([InlineKeyboardButton(
            text=contest["name"],
            callback_data=f"self_contest_{contest['_id']}"
        )])
    
    # Добавляем кнопку для создания нового конкурса
    keyboard.append([InlineKeyboardButton(
        text="➕ Добавить новый конкурс",
        callback_data="new_contest"
    )])
    
    # Добавляем кнопки навигации, если есть несколько страниц
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"contest_page_{page-1}"
        ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"contest_page_{page+1}"
        ))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой отмены
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой отмены
    """
    keyboard = [[InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="cancel"
    )]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 