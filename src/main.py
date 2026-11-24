#!/usr/bin/env python3
import json
import sys
from pathlib import Path
import click
from src.config import config
from src.api.trudvsem import fetch_vacancies
from src.parser.clean import normalize_vacancy
from src.analyzer.index import analyze_vacancy
from src.report.report import build_report, save_report, load_last_successful_report
from src.scheduler.scheduler import start_scheduler

def load_raw_vacancies(mode: str, file_path: str | None) -> list:
    """Загрузка вакансий из API или локального JSON."""
    if mode == "local":
        if not file_path:
            raise ValueError("В режиме local необходимо указать --file <путь>")
        
        abs_path = Path(file_path).resolve()
        if not abs_path.exists():
            raise FileNotFoundError(f"Файл не найден: {abs_path}")

        data = json.loads(abs_path.read_text(encoding="utf-8"))
        
        # Поддержка разных форматов
        if isinstance(data, list):
            raw_list = [item.get("vacancy", item) for item in data]
        elif isinstance(data, dict) and "results" in data:
            raw_list = [item["vacancy"] for item in data["results"].get("vacancies", [])]
        else:
            raise ValueError("Неизвестный формат JSON")

        print(f"[Local] Загружено {len(raw_list)} вакансий из {abs_path}")
        return raw_list
    
    return fetch_vacancies()

async def run_pipeline(mode: str, file_path: str | None):
    """Основной пайплайн."""
    print(f"\n=== Запуск пайплайна (mode={mode}) ===\n")

    raw_vacancies = load_raw_vacancies(mode, file_path)
    normalized = [normalize_vacancy(v) for v in raw_vacancies]

    analyzed = []
    for v in normalized:
        print(f"[Analyze] ID: {v.id} | {v.job_name or '(без названия)'}")
        issues = await analyze_vacancy(v)
        analyzed.append({**v.model_dump(), "issues": issues})

    report = build_report(analyzed)
    save_report(report)

    total_issues = sum(len(v.issues) for v in report.vacancies)
    print(f"\n=== Готово. Обработано вакансий: {report.vacancies_count}. Всего замечаний: {total_issues} ===\n")
    return report

def safe_run(mode: str, file_path: str | None):
    """Обёртка с fail-safe."""
    import asyncio
    try:
        return asyncio.run(run_pipeline(mode, file_path))
    except Exception as e:
        print(f"\n[ERROR] Критическая ошибка: {e}")
        last_report = load_last_successful_report()
        if last_report:
            print("[FAIL-SAFE] Используем последний успешный отчёт.")
            print(f"[FAIL-SAFE] Дата: {last_report.generated_at}")
            print(f"[FAIL-SAFE] Вакансий: {last_report.vacancies_count}")
            return last_report
        print("[FAIL-SAFE] Успешных отчётов нет.")
        sys.exit(1)

@click.command()
@click.argument("command", type=click.Choice(["run", "schedule"]))
@click.option("--mode", type=click.Choice(["api", "local"]), default=None)
@click.option("--file", "file_path", type=str, default=None)
def cli(command, mode, file_path):
    """CLI для запуска анализатора."""
    if command == "run":
        run_mode = mode or config.mode
        safe_run(run_mode, file_path)
    elif command == "schedule":
        print(f"[Scheduler] Инициализация: {config.schedule.cron}")
        start_scheduler(lambda: safe_run(config.mode, None))

if __name__ == "__main__":
    cli()