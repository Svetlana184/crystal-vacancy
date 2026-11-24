"""Роль 2: парсинг и нормализование вакансий «Работа в России» (API региона 39).

Вход:  сырой объект вакансии из API (или ответ API целиком, или локальный JSON).
Выход: NormalizedVacancy (см. schemas.py) — чистый текст + исходные значения в raw_fields.
"""
from __future__ import annotations

import argparse
import html
import json
import logging
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------- очистка текста

PLACEHOLDERS = {
    "не указано", "не указан", "не указана", "не указаны",
    "нет данных", "неизвестно", "отсутствует", "n/a", "null", "none", "нет",
}

_BLOCK_TAGS = {
    "p", "br", "li", "ul", "ol", "div", "tr", "td", "th", "table",
    "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "blockquote",
}
_SKIP_TAGS = {"script", "style"}

_TAG_RE = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
_ESCAPED_TAG_RE = re.compile(r"&lt;\s*/?\s*[a-zA-Z].*?&gt;", re.IGNORECASE | re.DOTALL)
_INVISIBLE_RE = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u00ad]")
_SPACES_RE = re.compile(r"\s+")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1
        if tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_startendtag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1
        if tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def clean_text(value: Any) -> str:
    """HTML -> простой текст. Слова не меняем, только убираем разметку и пробельный мусор."""
    if value is None or isinstance(value, bool):
        return ""
    text = value if isinstance(value, str) else str(value)

    if _ESCAPED_TAG_RE.search(text):
        text = html.unescape(text)
    if _TAG_RE.search(text):
        parser = _TextExtractor()
        parser.feed(text)
        parser.close()
        text = "".join(parser.parts)
    if "&" in text:
        text = html.unescape(text)

    text = _INVISIBLE_RE.sub("", text)
    return _SPACES_RE.sub(" ", text).strip()


def is_placeholder(text: str) -> bool:
    stripped = text.strip(" .,:;–—-_*").lower()
    return stripped == "" or stripped in PLACEHOLDERS


def clean_field(value: Any) -> str:
    """clean_text + заглушки («не указано», «-», «null») превращаем в пустую строку."""
    text = clean_text(value)
    return "" if is_placeholder(text) else text


# ---------------------------------------------------------------- вспомогательное

REQUIREMENT_LABELS = {
    "education": "Образование",
    "experience": "Опыт работы (лет)",
    "qualification": "Квалификация",
}
_GEO_KEYS = {"lat", "lng", "latitude", "longitude", "fias", "okato", "oktmo"}


def _scalar_to_text(value: Any) -> str:
    if isinstance(value, bool):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (int, float)):
        return str(value)
    return clean_field(value)


def flatten(value: Any, labels: Optional[dict] = None) -> str:
    """Любое значение (строка / число / dict / список) -> одна строка текста."""
    if value is None:
        return ""
    if isinstance(value, dict):
        parts = []
        for key, sub in value.items():
            if key in _GEO_KEYS:
                continue
            text = flatten(sub)
            if not text:
                continue
            label = (labels or {}).get(key)
            parts.append(f"{label}: {text}" if label else text)
        return "; ".join(parts)
    if isinstance(value, (list, tuple)):
        return "; ".join(t for t in (flatten(v) for v in value) if t)
    return _scalar_to_text(value)


def to_int(value: Any) -> Optional[int]:
    """Число из API. 0, отрицательное, пустое значение и мусор -> None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = int(value)
    else:
        raw = str(value).replace("\xa0", "").replace(" ", "").replace(",", ".")
        try:
            number = int(float(raw))
        except ValueError:
            return None
    return number if number > 0 else None


def _extract_work_place(vac: dict) -> str:
    parts: list[str] = []

    addresses = vac.get("addresses")
    items: Any = addresses.get("address") if isinstance(addresses, dict) else addresses
    if isinstance(items, dict):
        items = [items]
    for item in items or []:
        if isinstance(item, dict) and "location" in item:
            text = clean_field(item.get("location"))
        else:
            text = flatten(item)
        if text:
            parts.append(text)

    work_places = flatten(vac.get("work_places"))
    if work_places:
        parts.append(work_places)

    seen, unique = set(), []
    for part in parts:
        if part not in seen:
            seen.add(part)
            unique.append(part)
    return "; ".join(unique)


_CURRENCY_RE = re.compile(r"руб|₽|rub|usd|eur|\$|€", re.IGNORECASE)


def _salary_text(vac: dict, s_min: Optional[int], s_max: Optional[int]) -> str:
    """Текст зарплаты из поля salary, либо сборка из salary_min/salary_max если salary пустое."""
    currency = clean_text(vac.get("currency")).replace("«", "").replace("»", "") or "руб."
    text = clean_field(vac.get("salary"))

    if text and re.fullmatch(r"0+(?:\s*(?:руб\.?|₽|rub))?", text.lower()):
        text = ""

    if text:
        if not re.search(r"\d", text) or _CURRENCY_RE.search(text):
            return text
        return f"{text} {currency}".strip()

    if s_min and s_max and s_min != s_max:
        return f"от {s_min} до {s_max} {currency}".strip()
    if s_min:
        return f"от {s_min} {currency}".strip()
    if s_max:
        return f"до {s_max} {currency}".strip()

    return ""


def _schedule_text(vac: dict) -> str:
    """График = поле schedule + смены (shift), если API их отдаёт."""
    parts = [clean_field(vac.get("schedule"))]
    shift = vac.get("shift")
    if isinstance(shift, (list, tuple)):
        parts.extend(clean_field(item) for item in shift)
    elif shift:
        parts.append(clean_field(shift))
    return ", ".join(p for p in parts if p)


def _requirements_text(vac: dict) -> str:
    """В боевом API требования лежат в `requirement` (объект), в учебных файлах — `requirements`."""
    return flatten(vac.get("requirement"), REQUIREMENT_LABELS) or flatten(
        vac.get("requirements"), REQUIREMENT_LABELS
    )


def _duty_text(vac: dict) -> str:
    """Обязанности + дополнительные условия из поля term (если они не дублируют duty)."""
    duty = clean_field(vac.get("duty"))
    term = flatten(vac.get("term"))
    if term and term not in duty:
        return f"{duty} {term}".strip() if duty else term
    return duty


def _first_location(vac: dict) -> str:
    addresses = vac.get("addresses")
    items = addresses.get("address") if isinstance(addresses, dict) else addresses
    if isinstance(items, dict):
        items = [items]
    for item in items or []:
        if isinstance(item, dict) and item.get("location"):
            return str(item["location"])
    return ""


_RAW_KEYS = (
    "id", "vac_url", "job-name", "duty", "requirement", "requirements", "salary", "salary_min",
    "salary_max", "currency", "schedule", "shift", "employment", "term", "addresses", "work_places",
)


# ---------------------------------------------------------------- главная функция

def normalize_to_dict(raw: dict) -> dict:
    """Сырая вакансия -> dict с полями NormalizedVacancy."""
    vac = raw["vacancy"] if isinstance(raw, dict) and isinstance(raw.get("vacancy"), dict) else raw
    if not isinstance(vac, dict):
        raise ValueError("вакансия должна быть объектом (dict)")

    vac_id = clean_text(vac.get("id"))
    if not vac_id:
        raise ValueError("у вакансии нет id")

    raw_fields = {key: vac[key] for key in _RAW_KEYS if key in vac}
    raw_fields["location"] = _first_location(vac)
    company = vac.get("company")
    if isinstance(company, dict) and company.get("name"):
        raw_fields["company_name"] = company["name"]

    url = clean_text(vac.get("vac_url") or vac.get("url")) or None
    s_min = to_int(vac.get("salary_min"))
    s_max = to_int(vac.get("salary_max"))

    return {
        "id": vac_id,
        "url": url,
        "job_name": clean_field(vac.get("job-name") or vac.get("job_name")),
        "duty": _duty_text(vac),
        "requirements": _requirements_text(vac),
        "salary_min": s_min,
        "salary_max": s_max,
        "salary_text": _salary_text(vac, s_min, s_max),
        "schedule": _schedule_text(vac),
        "employment": clean_field(vac.get("employment")),
        "work_place": _extract_work_place(vac),
        "raw_fields": raw_fields,
    }


def _model_class():
    from src.schemas import NormalizedVacancy
    return NormalizedVacancy


def normalize_vacancy(raw: dict):
    """Сырая вакансия -> NormalizedVacancy (pydantic)."""
    return _model_class()(**normalize_to_dict(raw))


# ---------------------------------------------------------------- загрузка и пачки

def extract_vacancies(data: Any) -> list[dict]:
    """Достаёт список вакансий из любого формата API или локального файла."""
    if isinstance(data, dict):
        if isinstance(data.get("results"), (dict, list)):
            data = data["results"]
        if isinstance(data, dict):
            if "vacancies" in data:
                data = data["vacancies"]
            elif "vacancy" in data or "id" in data:
                data = [data]
            else:
                return []
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("vacancy"), dict):
            item = item["vacancy"]
        if isinstance(item, dict):
            result.append(item)
    return result


def load_vacancies_file(path: str | Path) -> list[dict]:
    """Локальный JSON (проверочный режим) -> список сырых вакансий."""
    with open(path, encoding="utf-8") as fh:
        return extract_vacancies(json.load(fh))


def normalize_many(
    items: Iterable[dict],
    max_vacancies: Optional[int] = None,
    as_dict: bool = False,
) -> list:
    """Пачка сырых вакансий -> список нормализованных без дублей по ID."""
    out, seen = [], set()
    for raw in items:
        if max_vacancies is not None and len(out) >= max_vacancies:
            break
        try:
            data = normalize_to_dict(raw)
        except ValueError as exc:
            log.warning("вакансия пропущена: %s", exc)
            continue
        if data["id"] in seen:
            log.info("дубль id %s пропущен", data["id"])
            continue
        seen.add(data["id"])
        out.append(data if as_dict else _model_class()(**data))
    return out


# ---------------------------------------------------------------- CLI

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Нормализация вакансий из JSON в формате API")
    parser.add_argument("path", help="путь к JSON (ответ API или список вакансий)")
    parser.add_argument("--max", type=int, default=None, help="максимум вакансий")
    args = parser.parse_args(argv)

    vacancies = normalize_many(load_vacancies_file(args.path), args.max, as_dict=True)
    json.dump(vacancies, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
