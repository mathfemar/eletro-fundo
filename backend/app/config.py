from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT_DIR / 'main_db'


class Settings(BaseSettings):
    app_name: str = 'Analisador de Fundos'
    database_url: str = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    enable_scheduler: bool = True
    scheduler_live_minutes: int = 30
    default_initial_unit_value: float = 1.0

    model_config = SettingsConfigDict(
        env_prefix='FUND_ANALYZER_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )


settings = Settings()
