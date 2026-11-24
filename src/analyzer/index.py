from typing import List
from src.schemas import NormalizedVacancy, VacancyIssue
from src.analyzer.rules import check_rules
from src.analyzer.llm import analyze_with_llm

async def analyze_vacancy(vacancy: NormalizedVacancy) -> List[VacancyIssue]:
    """
    Анализатор вакансий.
    Сначала запускает детерминированные правила (Роль 3),
    затем добавляет замечания от LLM (Роль 4).
    """
    issues = check_rules(vacancy)
    issues.extend(await analyze_with_llm(vacancy))
    return issues
