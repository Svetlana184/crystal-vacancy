import json
import os
from datetime import datetime
from pathlib import Path
from typing import List
from src.config import config
from src.schemas import NormalizedVacancy, VacancyIssue, VacancyReport, FullReport

def build_report(analyzed_vacancies: List[dict]) -> FullReport:
    """Сборка отчёта с дедупликацией по ID."""
    by_id = {}
    for v in analyzed_vacancies:
        report = VacancyReport(
            id=v["id"],
            url=v.get("url"),
            issues=v.get("issues", []),
        )
        by_id[report.id] = report

    full_report = FullReport(
        generated_at=datetime.now().isoformat(),
        vacancies_count=len(by_id),
        vacancies=list(by_id.values()),
    )
    return full_report

def save_report(report: FullReport) -> dict:
    """Атомарное сохранение отчёта."""
    output_dir = Path(config.report.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    dated_path = output_dir / f"report-{date_str}.json"
    latest_path = output_dir / config.report.latest_file
    tmp_path = latest_path.with_suffix(".tmp")

    json_str = report.model_dump_json(indent=2)

    # Атомарная запись
    tmp_path.write_text(json_str, encoding="utf-8")
    os.replace(tmp_path, latest_path)
    dated_path.write_text(json_str, encoding="utf-8")

    print(f"[Report] Сохранено: {dated_path}")
    print(f"[Report] Latest:   {latest_path}")
    return {"dated_path": str(dated_path), "latest_path": str(latest_path)}

def load_last_successful_report() -> FullReport | None:
    """Загрузка последнего успешного отчёта."""
    latest_path = Path(config.report.output_dir) / config.report.latest_file
    if not latest_path.exists():
        return None
    try:
        data = json.loads(latest_path.read_text(encoding="utf-8"))
        return FullReport.model_validate(data)
    except Exception:
        return None