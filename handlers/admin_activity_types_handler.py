from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import hashlib

from services.database import db
from keyboards.cancel_keyboard import create_cancel_keyboard

router = Router()

class ActivityTypeStates(StatesGroup):
    """Состояния для процесса управления видами деятельности"""
    adding_activity = State()
    deleting_activity = State()
    viewing_activities = State()

# Список всех видов деятельности
ACTIVITY_TYPES = [
    "1.1.2. Организация и оформление музея, выставочной площади внутри техникума",
    "1.2.1. Организация и проведение открытого занятия, открытого классного часа (в соответствин с планом работы)",
    "1.2.2. Организация и проведение на базе техникума олимпиады (чемпионата) (в соответствии с планом работы)",
    "1.2.3. Организация и проведение на базе техникума семинара, конференции (в соответствии с планом работы)",
    "1.2.4. Организация и проведение на базе техникума культурно-массовых, спортивных и иных мероприятий (в соответствии с планом работы)",
    "1.3.1. Публичные выступления от имени техникума на конференциях, форумах, конгрессах (по согласованию с методическим советом техникума)",
    "1.3.2. Участие от имени техникума в олимпиадах, чемпионатах и конкурсах в качестве экспертов (по согласованию c заместителями директора (по направлениям))",
    "1.3.3. Публикации в профессиональных журналах, сборниках от имени техникума (по согласованию с методическим советом техникума)",
    "1.4.1. Организация и проведение мероприятий по направлениям реализации воспитательной работы",
    "1.5.1. Участие в Дне открытых дверей (по согласованию с зам. директора)",
    "1.5.2. Участие в работе приемной комиссии по набору абитурнентов (по согласованию с директором)",
    "1.5.3. Подготовка раздаточных материалов, видеороликов профорнентационной направленности",
    "1.6.1. Разработка документации по дополнительной образовательной программе (по согласованню с зав. отделением ДОУ)",
    "1.6.2. Привлечение внешних сл их слушателей (не из числа обучающихся) для получения платных образовательных услуг по дополнительным программам (по согласованню с зав отделением ДОУ)",
    "1.7.1 Программы наставничества ПОО «педагог-студент» ((по согласованню с заместителями директора (по направлениям))",
    "1.7.2 Программы наставничества ПОО «педагог-педагог» (по согласованию заместителями директора (по направлениям))",
    "1.8.1. Участие в работе оценочной комиссии по расчету стимулирующих выплат преподавателям техникума (по согласованню с Советом техникума)",
    "2.1.1. Наличие призового места на олимпиаде, конкурсе, проводимых рамках ФГОС (по плану работы Минобриауки Челябинской области, Минпросвящения РФ и Минобривуки РФ)",
    "2.1.2. Наличие призового места на олимпиаде/ чен чемпионате профессионального мастерства",
    "2.1.3. Наличне призового места на иных олимпиадах, конкурсах",
    "2.2.1. Первая категория",
    "2.2.2. Высшая категория",
    "2.3.2 Доктор наук",
    "2.4.1. Наличие звания",
    "2.5.1. Абсолютная успеваемость",
    "2.5.2. Качественная успеваемость",
    "2.6.1. Своевременное и качественное ведение журналов учебных групп (по согласованию с заместителями лиректора по УР)",
    "2.6.2. Своевременное и качественное ведение зачетных и экзаменационных педомостей (по согласованию заместителями директора по УР)",
    "2.6.3. Своевременное и качественное заполнение отчетов преподавателей по итогам работы (по согласованию с заместителями директора по УР)",
    "2.7.1 Привлечение грантовых средств",
    "2.7.2 Курирование реализации гранта и подготовка отчетной документации по итогам реализации гранта",
    "3.1.1. Наличие педагогического стажа",
    "4.1. Стимулирование повышения качества успеваемости обучающихся (в течении 1 семестра с момента трудоустройства в техникуме)",
    "4.1. Выплата молодым педагогам в возрасте до 30 лет, начавшим педагогическую деятельность в техникуме (выплачивается в течение 1-го года работы)",
    "5.1.1. На областном уровне",
    "5.1.2. На всероссийском уровне",
    "5.2.1 Руководство курсовыми и дипломными работами (проектами), получившими практические результаты (внедрение в производственный процесс) - при наличии соответствующих отзывов представителей предприятий",
    "5.2.2. Привлечение спонсорской помощи со стороны работодателей и иных социальных партнеров для формировання и развития материально-технической базы техникума",
    "5.2.3. Участие в подготовке, оформлении и заключении договоров с социальными партнерами (предприятиями, учреждениями, организациями и хозяйствами) прохождении производственной практики, обеспечение выполнения договорных обязательств, подбор рабочих мест, соответствующих уровню квалификации обучающихся и учебным программам",
    "5.2.4. Разработка актуального комплекта учебно- методической документации по дисциплине, модулю (при наличии согласования и утверждения методическим советом техникума)",
    "5.2.5. Разработка КОС по дисциплине, модулю (при наличии согласования и утверждения методическим советом техникума)",
    "5.2.6. Премиальная выплата по итогам отчетного периода (по представлению руководителя структурного подразделения)",
    "5.3.1. Отсутствие по итогам промежуточной аттестации академических задолженностей среди обучающихся в курируемой группе (для классных руководителей)",
    "5.3.2. Сохранность контингента обучающихся по итогам промежуточной аттестации в курируемой группе не менее 95% (для классных руководителей)",
    "5.3.3. Для классных руководителей: развитие платных образовательных услуг и иной приносящей доход деятельности, при условии, что дебиторская задолженность среди обучающихся и слушателей по курируемой группе составляет (за счет средств от приносящей доход деятельности)",
    "5.4.1. Выполнение особо важных работ по поручению руководителя"
]

ITEMS_PER_PAGE = 5  # Количество элементов на странице

def get_activity_hash(activity):
    """Создает короткий хеш для идентификации вида деятельности"""
    return hashlib.md5(activity.encode()).hexdigest()[:8]

def create_pagination_keyboard(items, page, total_pages, action_type):
    """Создает клавиатуру с пагинацией"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    # Добавляем элементы текущей страницы
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(items))
    
    for item in items[start_idx:end_idx]:
        item_hash = get_activity_hash(item)
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=item,
                callback_data=f"{action_type}_{item_hash}"
            )
        ])
    
    # Добавляем кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"nav_{action_type}_{page-1}"
        ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"nav_{action_type}_{page+1}"
        ))
    if nav_buttons:
        keyboard.inline_keyboard.append(nav_buttons)
    
    # Добавляем кнопку отмены
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="Отмена", callback_data="cancel")
    ])
    
    return keyboard

@router.message(Command("manage_activity_types"))
async def cmd_manage_activity_types(message: types.Message):
    """Обработчик команды /manage_activity_types для управления видами деятельности"""
    # Проверяем, является ли пользователь администратором
    user = db.users.find_one({"telegram_id": message.from_user.id})
    if not user or user.get("role") != "admin":
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    # Создаем клавиатуру с действиями
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить вид деятельности", callback_data="add_activity_type")],
        [InlineKeyboardButton(text="Удалить вид деятельности", callback_data="delete_activity_type")],
        [InlineKeyboardButton(text="Добавить все виды деятельности", callback_data="add_all_activity_types")]
    ])

    await message.answer(
        "Выберите действие:",
        reply_markup=keyboard
    )

@router.callback_query(lambda query: query.data == "add_all_activity_types")
async def add_all_activity_types_handler(query: types.CallbackQuery):
    """Обработчик добавления всех видов деятельности"""
    # Получаем текущие виды деятельности из базы данных
    current_activities = db.activity_types.find_one({}) or {"types": []}
    
    # Добавляем все виды деятельности в базу данных
    db.activity_types.update_one(
        {},
        {"$set": {"types": ACTIVITY_TYPES}},
        upsert=True
    )
    
    # Подсчитываем количество добавленных видов деятельности
    added_count = len(ACTIVITY_TYPES) - len(current_activities["types"])
    
    await query.message.edit_text(
        f"Все виды деятельности успешно добавлены. "
        f"Добавлено {added_count} новых видов деятельности."
    )

@router.callback_query(lambda query: query.data == "add_activity_type")
async def add_activity_type_handler(query: types.CallbackQuery, state: FSMContext):
    """Обработчик добавления вида деятельности"""
    # Получаем текущие виды деятельности из базы данных
    current_activities = db.activity_types.find_one({}) or {"types": []}
    
    # Фильтруем доступные для добавления виды деятельности
    available_activities = [act for act in ACTIVITY_TYPES if act not in current_activities["types"]]
    
    if not available_activities:
        await query.message.edit_text("Все виды деятельности уже добавлены.")
        return
    
    # Сохраняем текущую страницу в состоянии
    await state.set_state(ActivityTypeStates.adding_activity)
    await state.update_data(page=0)
    
    # Создаем клавиатуру с пагинацией
    total_pages = (len(available_activities) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    keyboard = create_pagination_keyboard(available_activities, 0, total_pages, "select")
    
    await query.message.edit_text(
        "Выберите вид деятельности для добавления:",
        reply_markup=keyboard
    )

@router.callback_query(lambda query: query.data.startswith("nav_"))
async def handle_pagination(query: types.CallbackQuery, state: FSMContext):
    """Обработчик пагинации"""
    try:
        # Получаем тип действия и номер страницы
        parts = query.data.split("_")
        
        # Проверяем формат callback_data
        if len(parts) != 3:
            await query.message.edit_text(
                f"Ошибка формата данных: {query.data}. Ожидался формат 'nav_action_page'."
            )
            return
            
        # Извлекаем данные
        action_type = parts[1]
        page_str = parts[2]
        
        # Преобразуем номер страницы в число
        try:
            page = int(page_str)
        except ValueError:
            await query.message.edit_text(
                f"Ошибка: '{page_str}' не является числом. Номер страницы должен быть целым числом."
            )
            return
        
        # Получаем текущие данные из состояния
        state_data = await state.get_data()
        current_state = await state.get_state()
        
        # Определяем тип действия и создаем соответствующую клавиатуру
        if current_state == ActivityTypeStates.adding_activity.state:
            # Для добавления видов деятельности
            current_activities = db.activity_types.find_one({}) or {"types": []}
            available_activities = [act for act in ACTIVITY_TYPES if act not in current_activities["types"]]
            total_pages = (len(available_activities) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            
            # Проверяем, что страница существует
            if page < 0 or page >= total_pages:
                await query.message.edit_text(
                    f"Ошибка: страница {page} не существует. Всего страниц: {total_pages}."
                )
                return
                
            keyboard = create_pagination_keyboard(available_activities, page, total_pages, "select")
            message_text = "Выберите вид деятельности для добавления:"
        else:
            # Для удаления видов деятельности
            current_activities = db.activity_types.find_one({}) or {"types": []}
            total_pages = (len(current_activities["types"]) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            
            # Проверяем, что страница существует
            if page < 0 or page >= total_pages:
                await query.message.edit_text(
                    f"Ошибка: страница {page} не существует. Всего страниц: {total_pages}."
                )
                return
                
            keyboard = create_pagination_keyboard(current_activities["types"], page, total_pages, "remove")
            message_text = "Выберите вид деятельности для удаления:"
        
        # Сохраняем текущую страницу в состоянии
        await state.update_data(page=page)
        
        # Обновляем сообщение с новой клавиатурой
        await query.message.edit_text(message_text, reply_markup=keyboard)
        
    except Exception as e:
        # Обрабатываем любые непредвиденные ошибки
        await query.message.edit_text(
            f"Произошла непредвиденная ошибка: {str(e)}. Пожалуйста, попробуйте еще раз."
        )

@router.callback_query(lambda query: query.data.startswith("select_"))
async def select_activity_handler(query: types.CallbackQuery):
    """Обработчик выбора вида деятельности для добавления"""
    activity_hash = query.data.replace("select_", "")
    
    # Находим вид деятельности по хешу
    activity = None
    for act in ACTIVITY_TYPES:
        if get_activity_hash(act) == activity_hash:
            activity = act
            break
    
    if not activity:
        await query.message.edit_text("Произошла ошибка при выборе вида деятельности.")
        return
    
    # Добавляем вид деятельности в базу данных
    db.activity_types.update_one(
        {},
        {"$addToSet": {"types": activity}},
        upsert=True
    )

    await query.message.edit_text(f"Вид деятельности '{activity}' успешно добавлен.")

@router.callback_query(lambda query: query.data == "delete_activity_type")
async def delete_activity_type_handler(query: types.CallbackQuery, state: FSMContext):
    """Обработчик удаления вида деятельности"""
    # Получаем текущие виды деятельности из базы данных
    current_activities = db.activity_types.find_one({}) or {"types": []}
    
    if not current_activities["types"]:
        await query.message.edit_text("Нет доступных видов деятельности для удаления.")
        return
    
    # Сохраняем текущую страницу в состоянии
    await state.set_state(ActivityTypeStates.deleting_activity)
    await state.update_data(page=0)
    
    # Создаем клавиатуру с пагинацией
    total_pages = (len(current_activities["types"]) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    keyboard = create_pagination_keyboard(current_activities["types"], 0, total_pages, "remove")
    
    await query.message.edit_text(
        "Выберите вид деятельности для удаления:",
        reply_markup=keyboard
    )

@router.callback_query(lambda query: query.data.startswith("remove_"))
async def remove_activity_handler(query: types.CallbackQuery):
    """Обработчик удаления выбранного вида деятельности"""
    activity_hash = query.data.replace("remove_", "")
    
    # Находим вид деятельности по хешу
    activity = None
    for act in ACTIVITY_TYPES:
        if get_activity_hash(act) == activity_hash:
            activity = act
            break
    
    if not activity:
        await query.message.edit_text("Произошла ошибка при выборе вида деятельности.")
        return
    
    # Удаляем вид деятельности из базы данных
    db.activity_types.update_one(
        {},
        {"$pull": {"types": activity}}
    )

    await query.message.edit_text(f"Вид деятельности '{activity}' успешно удален.")

@router.callback_query(lambda query: query.data == "cancel")
async def cancel_handler(query: types.CallbackQuery, state: FSMContext):
    """Обработчик отмены действия"""
    await state.clear()
    await query.message.edit_text("Действие отменено.") 