import os
from functools import lru_cache
from pydantic_settings import BaseSettings  # <-- CORRECTED IMPORT
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    Manages application settings and environment variables.
    It automatically reads variables from a .env file or the environment.
    """
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    CLICKHOUSE_HOST: str
    CLICKHOUSE_PORT: int
    CLICKHOUSE_USER: str
    CLICKHOUSE_PASSWORD: str
    CLICKHOUSE_DB: str

    class Config:
        # Specifies the file to load environment variables from.
        env_file = ".env"

@lru_cache()
def get_settings():
    """
    Returns a cached instance of the settings.
    Using lru_cache ensures the settings are loaded only once.
    """
    return Settings()

# Create a global settings instance to be used across the application
settings = get_settings()
