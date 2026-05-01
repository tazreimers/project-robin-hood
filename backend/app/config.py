from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Project Robin Hood API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/arbitrage"
    redis_url: str = "redis://redis:6379/0"
    odds_api_key: str = ""
    sport_keys: str = ""
    odds_regions: str = "au"
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> str | list[str]:
        if isinstance(value, str) and value and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def sport_key_list(self) -> list[str]:
        return [key.strip() for key in self.sport_keys.split(",") if key.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
