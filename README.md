# Прозрачная вакансия — КАНТКОД

Анализатор вакансий Калининградской области (регион 39) с портала «Работа в России».

## Этап 2: Парсинг и данные

Реализованы:
- Загрузка вакансий через API с пагинацией (минимум 2 страницы)
- Локальный режим на учебном JSON
- Очистка HTML и нормализация полей
- Сохранение отчёта с дедупликацией по ID
- Fail-safe: при ошибке API сохраняется последний успешный отчёт
- Cron-расписание и ручной запуск

## Установка

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Скопировать .env (опционально для Этапа 2)
cp .env.example .env
```

## Запуск

```bash
# Режим API
python -m src.main run --mode api

# Проверочный режим
python -m src.main run --mode local --file data/test_vacancies.json

# Запуск по расписанию
python -m src.main schedule

# Проверка доступности API
python scripts/ping_api.py
```

## Формат отчёта

```json
{
  "generated_at": "2026-11-24T09:00:00.000000",
  "vacancies_count": 3,
  "vacancies": [
    {
      "id": "test-001",
      "url": "https://trudvsem.ru/vacancy/card/test-001",
      "issues": []
    }
  ]
}
```
