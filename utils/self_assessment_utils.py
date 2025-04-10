from datetime import datetime
from typing import Optional
import pandas as pd
from services.database import db

async def save_self_assessment(
    user_id: int,
    event_type: str,
    event_name: str,
    description: str,
    result: str,
    social_media_link: Optional[str],
    confirmation_file_id: str,
    contest_id: Optional[str] = None
) -> None:
    """
    Сохранение данных самообследования в базу данных
    
    Args:
        user_id: ID пользователя
        event_type: Тип мероприятия
        event_name: Название мероприятия
        description: Описание мероприятия
        result: Результат участия
        social_media_link: Ссылка на публикацию в соцсетях
        confirmation_file_id: ID файла подтверждения
        contest_id: ID конкурса (если применимо)
    """
    # Получаем информацию о пользователе
    user = db.users.find_one({"telegram_id": user_id})
    user_name = user.get("full_name", "Неизвестный пользователь") if user else "Неизвестный пользователь"
    
    db.self_assessments.insert_one({
        "user_id": user_id,
        "user_name": user_name,  # Сохраняем имя пользователя
        "event_type": event_type,
        "event_name": event_name,
        "description": description,
        "result": result,
        "social_media_link": social_media_link,
        "confirmation_file_id": confirmation_file_id,
        "contest_id": contest_id,
        "created_at": datetime.now()
    })

async def get_contests_by_type(event_type: str) -> list:
    """
    Получение списка конкурсов по типу мероприятия
    
    Args:
        event_type: Тип мероприятия (2.1.1, 2.1.2, 2.1.3)
    
    Returns:
        list: Список конкурсов
    """
    cursor = db.contests.find({"type": event_type})
    contests = list(cursor)
    return contests

async def generate_monthly_report(month: int, year: int) -> pd.DataFrame:
    """
    Генерация отчета за месяц в формате Excel
    
    Args:
        month: Номер месяца
        year: Год
    
    Returns:
        pd.DataFrame: DataFrame с данными для Excel
    """
    # Получаем все записи за указанный месяц
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    cursor = db.self_assessments.find({
        "created_at": {
            "$gte": start_date,
            "$lt": end_date
        }
    })
    assessments = list(cursor)
    
    # Преобразуем в DataFrame
    data = []
    for assessment in assessments:
        data.append({
            "Пользователь": assessment.get("user_name", "Неизвестный пользователь"),
            "Тип мероприятия": assessment["event_type"],
            "Название мероприятия": assessment["event_name"],
            "Описание": assessment["description"],
            "Результат": assessment["result"],
            "Ссылка на публикацию": assessment["social_media_link"] or "Нет",
            "Дата создания": assessment["created_at"].strftime("%d.%m.%Y")
        })
    
    # Создаем DataFrame и сортируем по имени пользователя
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by="Пользователь")
    
    return df 