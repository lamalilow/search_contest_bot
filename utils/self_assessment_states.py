from aiogram.fsm.state import State, StatesGroup

class SelfAssessmentStates(StatesGroup):
    """Состояния для процесса заполнения листа самообследования"""
    # Выбор типа мероприятия
    selecting_event_type = State()
    
    # Для конкурсов (2.1.1, 2.1.2, 2.1.3)
    selecting_contest = State()
    entering_contest_name = State()
    
    # Общие поля для всех типов мероприятий
    entering_event_name = State()
    entering_event_description = State()
    entering_event_result = State()
    entering_social_media_link = State()
    uploading_confirmation_file = State() 