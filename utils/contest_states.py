from aiogram.fsm.state import State, StatesGroup

class ContestParticipationStates(StatesGroup):
    selecting_contest = State()              # Выбор конкурса из БД
    entering_date = State()                  # Ввод или подтверждение даты
    selecting_level = State()                # Выбор уровня конкурса
    selecting_teacher_name = State()         # Выбор ФИО преподавателя
    entering_teacher_name = State()          # Ввод ФИО преподавателя
    entering_nomination = State()            # Ввод номинации
    selecting_participation_form = State()   # Очная/заочная
    selecting_participant_type = State()     # Преподаватель/студент
    entering_student_name = State()          # Ввод ФИО студента (если студент)
    entering_group = State()                 # Ввод группы
    entering_result = State()                # Ввод результата
    uploading_confirmation_file = State()    # Загрузка фото 