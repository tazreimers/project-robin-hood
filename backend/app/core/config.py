from functools import lru_cache
from decimal import Decimal

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
    default_total_stake: Decimal = Decimal("1000")
    min_arbitrage_margin: Decimal = Decimal("0.01")
    max_odds_age_seconds: int = 60
    daily_quota_budget: int = 500
    min_requests_remaining_buffer: int = 20
    max_scans_per_hour: int = 12
    enable_quota_guard: bool = True
    low_priority_scan_minutes: int = 30
    normal_priority_scan_minutes: int = 5
    high_priority_scan_seconds: int = 60
    urgent_priority_scan_seconds: int = 30
    near_arb_threshold: Decimal = Decimal("0.03")
    min_market_confidence: Decimal = Decimal("0.85")
    max_event_start_time_diff_minutes: int = 5
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
