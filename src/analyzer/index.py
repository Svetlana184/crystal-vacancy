from typing import List
from src.schemas import NormalizedVacancy, VacancyIssue

async def analyze_vacancy(vacancy: NormalizedVacancy) -> List[VacancyIssue]:
    """
    Анализатор вакансий.
    Этап 2: возвращает пустой массив (заглушка).
    Этап 3: подключит rules и llm.
    """
    return []