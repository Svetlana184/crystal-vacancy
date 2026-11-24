import httpx
from typing import List, Dict, Any
from src.config import config

def fetch_vacancies() -> List[Dict[str, Any]]:
    """
    Клиент API «Работа в России».
    ВАЖНО: API работает ТОЛЬКО по HTTP.
    """
    api_cfg = config.api
    base_url = api_cfg.url.replace("https://", "http://")
    all_vacancies = []

    for page in range(api_cfg.pages_limit):
        offset = page * api_cfg.page_size
        full_url = f"{base_url}?region={api_cfg.region}&offset={offset}&count={api_cfg.page_size}"
        
        print(f"[API] Страница {page + 1}/{api_cfg.pages_limit}: GET {full_url}")

        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(
                    full_url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "TransparentVacancy/1.0",
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"[API] Ошибка на странице {page + 1}: {e}")

        try:
            data = response.json()
        except Exception as e:
            raise RuntimeError(f"[API] Не удалось распарсить JSON на странице {page + 1}: {e}")

        # Структура: data["results"]["vacancies"] — массив объектов {"vacancy": {...}}
        raw_list = data.get("results", {}).get("vacancies", [])
        if not raw_list:
            print(f"[API] Страница {page + 1} пуста — останавливаемся.")
            break

        vacancies = [item["vacancy"] for item in raw_list if "vacancy" in item]
        all_vacancies.extend(vacancies)
        print(f"[API] Получено {len(vacancies)} вакансий (всего: {len(all_vacancies)})")

        if len(all_vacancies) >= api_cfg.max_vacancies:
            break

    limited = all_vacancies[:api_cfg.max_vacancies]
    print(f"[API] Итого загружено: {len(limited)} вакансий")
    return limited