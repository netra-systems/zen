# /v2/config.py
import os
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    Centralized application configuration.
    Values are loaded from environment variables.
    """
    # Database
    # Example: "postgresql://user:password@host:port/database"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./v2_netra_main.db")

    # Security & Auth
    SESSION_SECRET_KEY: str = os.getenv("SESSION_SECRET_KEY", "default_super_secret_key_for_dev")
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")
    
    # GCP Configuration for Secret Manager
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID")

    # API Configuration
    API_V2_STR: str = "/api/v2"

    class Config:
        case_sensitive = True

settings = Settings()
