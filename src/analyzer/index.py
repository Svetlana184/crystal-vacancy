from typing import List
from src.schemas import NormalizedVacancy, VacancyIssue
from src.analyzer.rules import check_rules

async def analyze_vacancy(vacancy: NormalizedVacancy) -> List[VacancyIssue]:
    """
    Анализатор вакансий.
    Сначала запускает детерминированные правила (Роль 3),
    затем сюда же добавится вызов LLM (Роль 4).
    """
    issues = check_rules(vacancy)
    
    # TODO (Роль 4): добавить вызов LLM и объединить списки:
    # llm_issues = await analyze_with_llm(vacancy)
    # issues.extend(llm_issues)
    
    return issues
