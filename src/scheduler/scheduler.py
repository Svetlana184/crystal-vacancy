from apscheduler.schedulers.blocking import BlockingScheduler
from src.config import config

def start_scheduler(task):
    """Запуск задачи по cron-расписанию."""
    scheduler = BlockingScheduler()
    
    # Парсинг cron: "0 9 * * *" → minute=0, hour=9
    parts = config.schedule.cron.split()
    if len(parts) == 5:
        minute, hour, day, month, day_of_week = parts
        scheduler.add_job(
            task,
            "cron",
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        )
    else:
        raise ValueError(f"Неверный формат cron: {config.schedule.cron}")

    print(f"[Scheduler] Активен. Расписание: {config.schedule.cron}")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[Scheduler] Остановлен.")