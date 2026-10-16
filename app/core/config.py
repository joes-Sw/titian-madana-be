from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "SPSE Scraper API"
    base_url: str = "https://spse.inaproc.id/lkpp"
    database_url: str = "sqlite:///./spse.db"

    tahun: int = 2026
    page_size: int = 100
    request_delay: float = 1.0
    max_retries: int = 3

    scrape_tender: bool = True
    scrape_nontender: bool = True
    scrape_detail: bool = True

    scheduler_enabled: bool = True
    scrape_interval_hours: int = 6

    log_level: str = "INFO"

    # Auth
    secret_key: str = "change-me-in-production-please-use-a-long-random-string"
    access_token_expire_minutes: int = 60 * 8


settings = Settings()
