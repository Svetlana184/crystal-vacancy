import re
from typing import List
from src.schemas import NormalizedVacancy, VacancyIssue


def check_rules(vacancy: NormalizedVacancy) -> List[VacancyIssue]:
    """
    Детерминированные проверки вакансии без ИИ (Этап 3).
    Проверяет пропуски и явные противоречия в полях NormalizedVacancy.
    """
    issues: List[VacancyIssue] = []

    # 1. Название должности
    if not vacancy.job_name or len(vacancy.job_name.strip()) < 3:
        issues.append(
            VacancyIssue(
                topic="Название должности",
                field="job-name",
                quote=vacancy.job_name or "",
                issue="Не указано или некорректно заполнено название должности.",
                recommendation="Уточните у работодателя точное наименование должности согласно штатному расписанию.",
            )
        )

    # 2. Оплата труда (пропуск и противоречие min > max)
    has_min = vacancy.salary_min is not None and vacancy.salary_min > 0
    has_max = vacancy.salary_max is not None and vacancy.salary_max > 0
    has_text = bool(vacancy.salary_text and vacancy.salary_text.strip())

    if not has_min and not has_max and not has_text:
        issues.append(
            VacancyIssue(
                topic="Оплата",
                field="salary",
                quote="",
                issue="Не указан размер заработной платы ни в числовых полях, ни в текстовом описании.",
                recommendation="Запросите у работодателя оклад или вилку заработной платы до вычета НДФЛ.",
            )
        )
    elif has_min and has_max and vacancy.salary_min > vacancy.salary_max:
        issues.append(
            VacancyIssue(
                topic="Оплата",
                field="salary_min / salary_max",
                quote=f"salary_min: {vacancy.salary_min} | salary_max: {vacancy.salary_max}",
                issue="Минимальная граница заработной платы указана больше максимальной.",
                recommendation="Уточните у работодателя корректную вилку оплаты труда.",
            )
        )

    # 3. Обязанности
    if not vacancy.duty or len(vacancy.duty.strip()) < 15:
        issues.append(
            VacancyIssue(
                topic="Обязанности",
                field="duty",
                quote=vacancy.duty or "",
                issue="Описание должностных обязанностей отсутствует или слишком короткое.",
                recommendation="Запросите у работодателя перечень основных задач и функций сотрудника.",
            )
        )

    # 4. Требования
    if not vacancy.requirements or len(vacancy.requirements.strip()) < 5:
        issues.append(
            VacancyIssue(
                topic="Требования",
                field="requirements",
                quote=vacancy.requirements or "",
                issue="Не указаны требования к квалификации, образованию или опыту кандидата.",
                recommendation="Уточните у работодателя минимальные требования к образованию, стажу и навыкам.",
            )
        )

    # 5. График работы (пропуск или сменный/гибкий без конкретики по сменам)
    if not vacancy.schedule:
        issues.append(
            VacancyIssue(
                topic="График",
                field="schedule",
                quote="",
                issue="Не указан график работы.",
                recommendation="Уточните режим работы (пятидневка, сменный, гибкий) и рабочие часы.",
            )
        )
    elif re.search(r"сменн|гибк|скользящ", vacancy.schedule, flags=re.IGNORECASE):
        combined_text = f"{vacancy.schedule} {vacancy.duty}"
        # Ищем упоминание смен (2/2, 1/3, день/ночь) или точного времени (с 8:00, 8 часов)
        has_shift_details = re.search(
            r"(\d/\d|\d\s*через\s*\d|день/ночь|ночн|с\s*\d{1,2}[:.]\d{2}|до\s*\d{1,2}[:.]\d{2}|\d+\s*час)",
            combined_text,
            flags=re.IGNORECASE,
        )
        if not has_shift_details:
            issues.append(
                VacancyIssue(
                    topic="График",
                    field="schedule",
                    quote=vacancy.schedule,
                    issue=f"Указан «{vacancy.schedule}», но ни в одном поле не уточнены дни и продолжительность смен.",
                    recommendation="Уточните у работодателя чередование смен (например, 2/2), время начала и окончания рабочего дня.",
                )
            )

    # 6. Тип занятости
    if not vacancy.employment:
        issues.append(
            VacancyIssue(
                topic="Тип занятости",
                field="employment",
                quote="",
                issue="Не указан тип занятости.",
                recommendation="Уточните формат трудоустройства: полная занятость, частичная занятость или совместительство.",
            )
        )

    # 7. Место работы
    if not vacancy.work_place:
        issues.append(
            VacancyIssue(
                topic="Место работы",
                field="addresses",
                quote="",
                issue="Не указан адрес или населённый пункт места работы.",
                recommendation="Уточните фактический адрес рабочего места (город, улица, номер дома).",
            )
        )

    return issues