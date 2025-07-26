# /v2/app/config.py
import os
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    Centralized application configuration.
    Values are loaded from environment variables.
    """
    # Postgres Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./v2_netra_main.db")

    # ClickHouse Database
    CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST", "localhost")
    CLICKHOUSE_PORT: int = int(os.getenv("CLICKHOUSE_PORT", 9000))
    CLICKHOUSE_USER: str = os.getenv("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD: str = os.getenv("CLICKHOUSE_PASSWORD", "")
    CLICKHOUSE_DB: str = os.getenv("CLICKHOUSE_DB", "netra")
    
    # Security & Auth
    SESSION_SECRET_KEY: str = os.getenv("SESSION_SECRET_KEY", "default_super_secret_key_for_dev")
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")
    FERNET_KEY: str = os.getenv("FERNET_KEY")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "a_very_secret_jwt_key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # GCP Configuration for Secret Manager
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID")

    # API Configuration
    API_V2_STR: str = "/api/v2"

    class Config:
        case_sensitive = True

settings = Settings()
