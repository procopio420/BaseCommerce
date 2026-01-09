import functools

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: list[str] | str = ["http://localhost:3000", "http://localhost:5173"]
    REDIS_URL: str = "redis://localhost:6379/0"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS_ORIGINS from string (comma-separated) or list."""
        if isinstance(v, str):
            # Se for string separada por vírgulas, converte em lista
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_file = ".env"


@functools.lru_cache()
def get_settings() -> Settings:
    """
    Get Settings instance (cached).
    
    This function lazily initializes Settings to avoid import-time side effects.
    Call this function instead of instantiating Settings directly.
    """
    return Settings()

