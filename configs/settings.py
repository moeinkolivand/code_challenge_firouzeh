from typing import List
from pydantic_settings import BaseSettings

__all__ = [
    'Settings'
]

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI App"
    VERSION: str = "0.1.0"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/fastapi_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    ALLOWED_HOSTS: List[str] = ["*"]
    SECRET_KEY: str = "your-secret-key-here"

    class Config:
        env_file = ".env"
