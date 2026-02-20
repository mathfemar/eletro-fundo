from pydantic_settings import BaseSettings
from functools import lru_cache


class APISettings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8528
    debug: bool = True

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    database_path: str = "Fundinho"
    cache_dir: str = "cache"

    model_config = {"env_prefix": "FUNDINHO_API_", "env_file": ".env"}


@lru_cache()
def get_settings() -> APISettings:
    return APISettings()
