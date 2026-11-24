import os
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

class APIConfig(BaseModel):
    url: str
    region: int
    pages_limit: int
    page_size: int
    max_vacancies: int

class ScheduleConfig(BaseModel):
    cron: str

class ReportConfig(BaseModel):
    output_dir: str
    latest_file: str

class LLMConfig(BaseModel):
    provider: str = Field(default="")
    model: str = Field(default="")
    api_key: str = Field(default="")
    base_url: str = Field(default="")

class Config(BaseModel):
    api: APIConfig
    schedule: ScheduleConfig
    mode: str
    report: ReportConfig
    llm: LLMConfig

def load_config() -> Config:
    settings_path = Path("config/settings.yaml")
    with open(settings_path, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)
    
    return Config(
        api=APIConfig(**settings["api"]),
        schedule=ScheduleConfig(**settings["schedule"]),
        mode=settings["mode"],
        report=ReportConfig(**settings["report"]),
        llm=LLMConfig(
            provider=os.getenv("LLM_PROVIDER", ""),
            model=os.getenv("LLM_MODEL", ""),
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", ""),
        ),
    )

config = load_config()