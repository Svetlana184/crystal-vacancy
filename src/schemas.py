from typing import List, Optional
from pydantic import BaseModel, Field

# 1. Контракт между Парсером и Анализаторами
class NormalizedVacancy(BaseModel):
    id: str
    url: Optional[str] = None
    job_name: str = ""
    duty: str = ""
    requirements: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_text: str = ""
    schedule: str = ""
    employment: str = ""
    work_place: str = ""
    raw_fields: dict = Field(default_factory=dict)

# 2. Контракт одного замечания
class VacancyIssue(BaseModel):
    topic: str = Field(..., description="Тема: должность, обязанности, требования, оплата, график, место работы, тип занятости")
    field: str = Field(..., description="Поле или поля источника")
    quote: str = Field(default="", description="Точная цитата. Пустая для пропусков. Оба значения через '|' для противоречий")
    issue: str = Field(..., description="Суть проблемы")
    recommendation: str = Field(..., description="Конкретный вопрос для работодателя")

# 3. Итоговый контракт отчёта по одной вакансии
class VacancyReport(BaseModel):
    id: str
    url: Optional[str] = None
    issues: List[VacancyIssue] = Field(default_factory=list)

# 4. Финальный отчёт
class FullReport(BaseModel):
    generated_at: str
    vacancies_count: int
    vacancies: List[VacancyReport]