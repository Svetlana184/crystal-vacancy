from typing import Dict, Any
from bs4 import BeautifulSoup
import html
from src.schemas import NormalizedVacancy

def clean_text(text: Any) -> str:
    """Очистка HTML и сущностей без перефразирования."""
    if text is None:
        return ""
    text = str(text)
    soup = BeautifulSoup(text, "html.parser")
    cleaned = soup.get_text(separator=" ", strip=True)
    cleaned = html.unescape(cleaned)
    return " ".join(cleaned.split())

def normalize_vacancy(raw: Dict[str, Any]) -> NormalizedVacancy:
    """Приводит сырую вакансию API к контракту NormalizedVacancy."""
    
    # Адрес
    addresses = raw.get("addresses", {})
    address_list = addresses.get("address", [])
    location = address_list[0].get("location", "") if address_list else ""

    # График + смены
    shift = raw.get("shift", [])
    shift_text = ", ".join(shift) if isinstance(shift, list) else ""
    schedule_text = ", ".join(filter(None, [raw.get("schedule", ""), shift_text]))

    # Зарплата (текстовая)
    salary_text = ""
    if raw.get("salary"):
        currency = (raw.get("currency") or "руб.").replace("«", "").replace("»", "")
        salary_text = f"{raw['salary']} {currency}".strip()

    normalized = NormalizedVacancy(
        id=str(raw.get("id", "")),
        url=clean_text(raw.get("vac_url", "")),
        job_name=clean_text(raw.get("job-name", "")),
        duty=clean_text(raw.get("duty", "")),
        requirements=clean_text(raw.get("requirements", "")),
        salary_min=raw.get("salary_min"),
        salary_max=raw.get("salary_max"),
        salary_text=salary_text,
        schedule=clean_text(schedule_text),
        employment=clean_text(raw.get("employment", "")),
        work_place=clean_text(location),
        raw_fields={
            "job-name": raw.get("job-name", ""),
            "duty": raw.get("duty", ""),
            "requirements": raw.get("requirements", ""),
            "salary": raw.get("salary", ""),
            "schedule": raw.get("schedule", ""),
            "employment": raw.get("employment", ""),
            "location": location,
        },
    )
    return normalized