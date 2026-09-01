from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent
WEAK_PASSWORDS = {"", "change-me-before-production", "replace-with-a-strong-password", "admin", "password"}


class Settings(BaseSettings):
    app_name: str = "AI Legal Office Assistant"
    app_env: str = "development"
    secret_key: str = "dev-only-change-me"
    database_url: str = f"sqlite:///{ROOT_DIR / 'legal_scheduler.db'}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    trusted_hosts: str = "localhost,127.0.0.1"
    timezone: str = "Europe/Skopje"
    working_day_start: str = "09:00"
    working_day_end: str = "17:00"
    lunch_start: str = "12:00"
    lunch_end: str = "13:00"
    slot_interval_minutes: int = 30
    calendar_mode: str = "demo"
    google_calendar_id: str = "primary"
    google_credentials_file: str = "credentials.json"
    google_token_file: str = "token.json"
    google_allow_browser_oauth: bool = False
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    admin_username: str = "admin"
    admin_password: str = "change-me-before-production"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    rate_limit_per_minute: int = 30
    secure_cookies: bool = False
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def trusted_host_list(self) -> list[str]:
        hosts = [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]
        return hosts or ["localhost", "127.0.0.1"]

    def google_credentials_path(self) -> Path:
        path = Path(self.google_credentials_file)
        return path if path.is_absolute() else ROOT_DIR / path

    def google_token_path(self) -> Path:
        path = Path(self.google_token_file)
        return path if path.is_absolute() else ROOT_DIR / path

    @field_validator("calendar_mode")
    @classmethod
    def calendar_mode_allowed(cls, value: str) -> str:
        mode = value.lower().strip()
        if mode not in {"demo", "google"}:
            raise ValueError("CALENDAR_MODE must be demo or google.")
        return mode

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.is_production:
            if self.secret_key in {"", "dev-only-change-me"}:
                raise ValueError("Set a strong SECRET_KEY before running in production.")
            if self.admin_password in WEAK_PASSWORDS or len(self.admin_password) < 12:
                raise ValueError("Set a strong ADMIN_PASSWORD (12+ characters) before production.")
            if self.is_sqlite:
                raise ValueError("Use PostgreSQL (DATABASE_URL) in production.")
        if self.calendar_mode == "google" and self.is_production and self.google_allow_browser_oauth:
            raise ValueError("Disable GOOGLE_ALLOW_BROWSER_OAUTH in production; use a stored refresh token.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
