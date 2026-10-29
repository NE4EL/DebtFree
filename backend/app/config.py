from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"  # development | production
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/debtfree"
    jwt_secret: str = DEV_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: list[str] = ["http://localhost:5173"]
    docs_enabled: bool = True  # Swagger UI на /docs

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def require_secret_in_production(self) -> "Settings":
        if self.is_production and (self.jwt_secret == DEV_SECRET or len(self.jwt_secret) < 32):
            raise ValueError("В production задайте JWT_SECRET длиной не меньше 32 символов")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
