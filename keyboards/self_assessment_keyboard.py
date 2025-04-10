from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_event_type_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора типа мероприятия"""
    keyboard = [
        [KeyboardButton(text="1.1.2. Организация и оформление музея, выставочной площади")],
        [KeyboardButton(text="1.2.1. Организация и проведение открытого занятия")],
        [KeyboardButton(text="1.2.2. Организация и проведение олимпиады")],
        [KeyboardButton(text="1.2.3. Организация и проведение семинара, конференции")],
        [KeyboardButton(text="1.2.4. Организация культурно-массовых мероприятий")],
        [KeyboardButton(text="1.3.1. Публичные выступления")],
        [KeyboardButton(text="1.3.2. Участие в качестве эксперта")],
        [KeyboardButton(text="1.3.3. Публикации в профессиональных журналах")],
        [KeyboardButton(text="1.4.1. Мероприятия по воспитательной работе")],
        [KeyboardButton(text="1.5.1. Участие в Дне открытых дверей")],
        [KeyboardButton(text="1.5.2. Участие в работе приемной комиссии")],
        [KeyboardButton(text="1.5.3. Подготовка профориентационных материалов")],
        [KeyboardButton(text="1.6.1. Разработка документации ДОУ")],
        [KeyboardButton(text="1.6.2. Привлечение внешних слушателей")],
        [KeyboardButton(text="1.7.1. Программа наставничества педагог-студент")],
        [KeyboardButton(text="1.7.2. Программа наставничества педагог-педагог")],
        [KeyboardButton(text="1.8.1. Участие в оценочной комиссии")],
        [KeyboardButton(text="2.1.1. Призовое место на олимпиаде ФГОС")],
        [KeyboardButton(text="2.1.2. Призовое место на олимпиаде профмастерства")],
        [KeyboardButton(text="2.1.3. Призовое место на иных олимпиадах")],
        [KeyboardButton(text="5.1. Призовое место на конкурсе профмастерства")],
        [KeyboardButton(text="5.2. Личный вклад в эффективность работы")],
        [KeyboardButton(text="2.7.1. Привлечение грантовых средств")],
        [KeyboardButton(text="2.7.2. Курирование реализации гранта")],
        [KeyboardButton(text="Иное")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_contest_selection_keyboard(contests: list) -> InlineKeyboardMarkup:
    """Клавиатура для выбора конкурса из списка"""
    keyboard = []
    for contest in contests:
        keyboard.append([InlineKeyboardButton(
            text=contest['name'],
            callback_data=f"contest_{contest['_id']}"
        )])
    keyboard.append([InlineKeyboardButton(
        text="Добавить новый конкурс",
        callback_data="new_contest"
    )])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    keyboard = [[KeyboardButton(text="Отмена")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True) 