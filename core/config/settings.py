from zoneinfo import ZoneInfo
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    # Telegram Bot
    BOT_TOKEN: str

    # Gemini API
    GEMINI_API_KEY: str

    # WebSearch API
    SERPER_API_KEY: str

    # Database
    DB_HOST: str
    DB_PORT: str
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    model_config = SettingsConfigDict(
        env_file=ROOT / "app" / ".env",
        env_file_encoding="utf-8"
    )

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    DATABASE_ECHO: bool = True

    DB_MIN_POOL_SIZE: int = 1
    DB_MAX_POOL_SIZE: int = 10

    USER_TIMEZONE: str = "Europe/Moscow"

    @field_validator("USER_TIMEZONE")
    @classmethod
    def _timezone_must_exists(cls, value: str) -> str:
        try :
            ZoneInfo(value)
        except Exception as exc:
            raise ValueError(f"Unknown timezone: {value!r}") from exc
        return value

    @property
    def user_tz(self) -> ZoneInfo:
        return ZoneInfo(self.USER_TIMEZONE)

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    DEBUG: bool = False

    # Redis Cache
    REDIS_HOST: str
    REDIS_PORT: str
    REDIS_DB: str

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()