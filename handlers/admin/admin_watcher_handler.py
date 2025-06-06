from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BotCommand, BotCommandScopeChat

from config import logger
from services.database import users_col
from keyboards.contest_keyboard import get_cancel_keyboard
from utils.role_utils import send_role_keyboard

router = Router()

class WatcherState(StatesGroup):
    """Состояния для процесса добавления роли watcher"""
    selecting_user = State()
    confirming = State()

@router.message(Command("add_watcher"))
async def cmd_add_watcher(message: Message, state: FSMContext):
    """Обработчик команды /add_watcher для добавления роли watcher"""
    # Получаем список всех пользователей
    users = list(users_col.find())
    
    # Создаем клавиатуру с пользователями
    keyboard = []
    for user in users:
        # Пропускаем пользователей, у которых уже есть роль watcher
        user_roles = user.get("role")
        if isinstance(user_roles, list) and "watcher" in user_roles:
            continue
        if isinstance(user_roles, str) and user_roles == "watcher":
            continue
        
        # Добавляем пользователя в клавиатуру
        keyboard.append([{
            "text": f"{user.get('full_name', 'Без имени')} ({user.get('telegram_id')})",
            "callback_data": f"watcher_{user.get('telegram_id')}"
        }])
    
    if not keyboard:
        await message.answer("Нет пользователей, которым можно добавить роль watcher.")
        return
    
    await state.set_state(WatcherState.selecting_user)
    await message.answer(
        "Выберите пользователя, которому нужно добавить роль watcher:",
        reply_markup={"inline_keyboard": keyboard}
    )

@router.callback_query(WatcherState.selecting_user, F.data.startswith("watcher_"))
async def process_user_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора пользователя"""
    user_id = int(callback.data.split("_")[1])
    
    # Сохраняем ID пользователя в состоянии
    await state.update_data(selected_user_id=user_id)
    
    # Получаем информацию о пользователе
    user = users_col.find_one({"telegram_id": user_id})
    if not user:
        await callback.message.answer("Пользователь не найден.")
        await state.clear()
        return
    
    # Создаем клавиатуру для подтверждения
    keyboard = [
        [
            {"text": "Да", "callback_data": "confirm_watcher"},
            {"text": "Нет", "callback_data": "cancel_watcher"}
        ]
    ]
    
    await state.set_state(WatcherState.confirming)
    await callback.message.answer(
        f"Вы уверены, что хотите добавить роль watcher пользователю {user.get('full_name', 'Без имени')}?",
        reply_markup={"inline_keyboard": keyboard}
    )
    
    await callback.answer()

@router.callback_query(WatcherState.confirming, F.data == "confirm_watcher")
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обработка подтверждения добавления роли watcher"""
    # Получаем ID пользователя из состояния
    data = await state.get_data()
    user_id = data.get("selected_user_id")
    
    if not user_id:
        await callback.message.answer("Произошла ошибка. Попробуйте еще раз.")
        await state.clear()
        return
    
    # Получаем информацию о пользователе
    user = users_col.find_one({"telegram_id": user_id})
    if not user:
        await callback.message.answer("Пользователь не найден.")
        await state.clear()
        return
    
    # Получаем текущие роли пользователя
    user_roles = user.get("role")
    
    # Добавляем роль watcher
    if isinstance(user_roles, list):
        # Если роль уже является массивом, добавляем watcher, если его еще нет
        if "watcher" not in user_roles:
            user_roles.append("watcher")
    else:
        # Если роль - строка, преобразуем в массив с двумя ролями
        user_roles = [user_roles, "watcher"]
    
    # Обновляем данные пользователя в базе
    users_col.update_one(
        {"telegram_id": user_id},
        {"$set": {"role": user_roles}}
    )

    # Отправляем сообщение пользователю о присвоении роли наблюдателя
    await callback.bot.send_message(
        user_id,
        "Вам была присвоена роль наблюдателя (watcher). "
        "Теперь вы можете получать отчеты по листам самообследования."
    )

    # Обновляем клавиатуру пользователя
    await send_role_keyboard(callback.bot, user_id, user_roles)

    # Обновляем команды для пользователя
    watcher_commands = [
        BotCommand(command="start", description="Начать работу с ботом или перезапустить"),
        BotCommand(command="watcher", description="Посмотреть доступные команды для наблюдателей"),
        BotCommand(command="get_report", description="Получить отчет за период"),
        BotCommand(command="contest", description="Заполнить участие в конкурсе"),
    ]
    
    try:
        await callback.bot.set_my_commands(
            watcher_commands,
            scope=BotCommandScopeChat(chat_id=user_id)
        )
    except Exception as e:
        logger.error(f"Ошибка при установке команд для watcher {user_id}: {e}")

    await callback.message.edit_text(
        f"Пользователю {user.get('full_name', 'Без имени')} (ID: {user_id}) успешно присвоена роль наблюдателя."
    )
    await callback.answer()

    # Очищаем состояние
    await state.clear()

@router.callback_query(WatcherState.confirming, F.data == "cancel_watcher")
async def process_cancellation(callback: CallbackQuery, state: FSMContext):
    """Обработка отмены добавления роли watcher"""
    await callback.message.answer("Операция отменена.")
    await state.clear()
    
    await callback.answer() 