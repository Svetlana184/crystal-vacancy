#!/usr/bin/env python3
"""Быстрая проверка доступности API."""
import httpx

URL = "http://opendata.trudvsem.ru/api/v1/vacancies?region=39&offset=0&count=1"

print(f"Проверяем: {URL}\n")

try:
    with httpx.Client(timeout=15.0) as client:
        response = client.get(URL, headers={"Accept": "application/json"})
        print(f"Статус: {response.status_code} {response.reason_phrase}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        text = response.text[:500]
        print(f"\nПервые 500 символов:\n{text}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                count = len(data.get("results", {}).get("vacancies", []))
                print(f"\n✅ API работает. Вакансий на странице: {count}")
            except Exception:
                print("\n⚠️  Ответ получен, но это не JSON")
        else:
            print("\n❌ API вернул ошибку")
except Exception as e:
    print(f"\n❌ Ошибка соединения: {e}")
    print("\nВозможные причины:")
    print("  1. Используется HTTPS вместо HTTP")
    print("  2. Нет доступа к opendata.trudvsem.ru")
    print("  3. API временно недоступен")