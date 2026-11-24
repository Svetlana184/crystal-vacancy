import json
import os
import re
from typing import List

import ollama

from src.schemas import NormalizedVacancy, VacancyIssue

MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")

PROMPT = """Ты помогаешь редактору вакансий. Найди неоднозначные формулировки и противоречия между полями, из-за которых соискателю непонятны условия.
Правила:
- Используй только данные ниже. Не выдумывай факты, не делай выводов о нарушении закона.
- quote: дословная цитата из значения поля field. Для противоречия: field = "поле1, поле2", quote = "цитата1 | цитата2".
- Для противоречия указывай именно те два поля, в которых лежат конфликтующие фразы. Например, если в duty написано про подработку на 2 часа в день, а в schedule указан полный рабочий день, то field = "duty, schedule", а не "schedule, employment".
- Если конкретика есть в другом поле, не требуй повторять её в описании.
- workPlaceQuota="False" означает, что место не квотируемое. Если в тексте сказано про квоту или инвалидов, это противоречие.
- Неоднозначности, которые нужно отмечать:
  * оплата "по договорённости" или "достойная" без суммы, если конкретной суммы нет ни в одном поле;
  * общие обязанности вроде "разные задачи по поручению руководителя", "выполнение поручений", "другие обязанности", из которых не понять реальную работу;
  * слишком общее название должности ("Специалист", "Сотрудник", "Работник") без указания сферы или профиля, если сферу не раскрывают другие поля;
  * "гибкий график" без дней и смен.
- recommendation: короткий вопрос или просьба к работодателю по существу, например "Уточните у работодателя размер заработной платы и от чего он зависит". Не упоминай названия полей, только суть.
- Не придирайся к пустякам. Если всё понятно, верни {{"issues": []}}.
Темы: должность, обязанности, требования, оплата, график, место работы, тип занятости.
Верни только JSON: {{"issues": [{{"topic": "", "field": "", "quote": "", "issue": "", "recommendation": ""}}]}}

Поля вакансии:
{fields}
"""


def get_fields(v: NormalizedVacancy) -> dict:
    raw = v.raw_fields or {}
    f = {
        "job_name": v.job_name, "duty": v.duty, "requirements": v.requirements,
        "salary_text": v.salary_text, "schedule": v.schedule,
        "employment": v.employment, "work_place": v.work_place,
        "shift": ", ".join(map(str, raw.get("shift") or [])),
        "benefitDetails": raw.get("benefitDetails") or "",
        "workPlaceQuota": str((raw.get("workPlaceType") or {}).get("workPlaceQuota", "")),
    }
    f = {k: (x or "").strip() for k, x in f.items()}
    return {k: x for k, x in f.items() if x}  # пустые поля не отправляем: их ловят правила


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _valid(i: VacancyIssue, f: dict) -> bool:
    fields = [x.strip() for x in i.field.split(",")]
    quotes = [x.strip() for x in i.quote.split("|")]
    if not i.quote or len(fields) != len(quotes):
        return False
    return all(k in f and q and _norm(q) in _norm(f[k]) for k, q in zip(fields, quotes))


async def analyze_with_llm(vacancy: NormalizedVacancy) -> List[VacancyIssue]:
    f = get_fields(vacancy)
    prompt = PROMPT.format(fields=json.dumps(f, ensure_ascii=False, indent=1))
    client = ollama.AsyncClient()
    for _ in range(3):
        try:
            r = await client.chat(model=MODEL, format="json", options={"temperature": 0},
                                  messages=[{"role": "user", "content": prompt}])
            data = json.loads(r["message"]["content"])["issues"]
            items = [VacancyIssue.model_validate(x) for x in data]
        except (ValueError, KeyError, TypeError):
            continue
        return [i for i in items if _valid(i, f)]
    return []