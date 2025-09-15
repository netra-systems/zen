"""
NetraOptimizer Configuration - Single Source of Truth

All configuration settings for the NetraOptimizer system.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class NetraOptimizerConfig(BaseSettings):
    """
    Centralized configuration for NetraOptimizer system.
    Uses Pydantic BaseSettings for validation and environment variable support.
    """

    # Database Configuration
    db_host: str = Field(default="localhost", alias="NETRA_DB_HOST")
    db_port: int = Field(default=5432, alias="NETRA_DB_PORT")
    db_name: str = Field(default="netra_optimizer", alias="NETRA_DB_NAME")
    db_user: str = Field(default="netra", alias="NETRA_DB_USER")
    db_password: str = Field(default="", alias="NETRA_DB_PASSWORD")

    # Claude Executable Configuration
    claude_executable: str = Field(default="claude", alias="CLAUDE_EXECUTABLE")
    claude_timeout: int = Field(default=600, alias="CLAUDE_TIMEOUT")  # seconds

    # Analytics Configuration
    enable_analytics: bool = Field(default=True, alias="NETRA_ENABLE_ANALYTICS")
    batch_prediction_enabled: bool = Field(default=False, alias="NETRA_BATCH_PREDICTION")

    # Performance Configuration
    max_concurrent_executions: int = Field(default=10, alias="NETRA_MAX_CONCURRENT")
    startup_delay_seconds: int = Field(default=0, alias="NETRA_STARTUP_DELAY")

    # Logging Configuration
    log_level: str = Field(default="INFO", alias="NETRA_LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, alias="NETRA_LOG_FILE")

    # Cache Configuration
    redis_host: Optional[str] = Field(default=None, alias="NETRA_REDIS_HOST")
    redis_port: int = Field(default=6379, alias="NETRA_REDIS_PORT")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
        "populate_by_name": True
    }

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL for asyncpg."""
        if self.db_password:
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        return f"postgresql://{self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def sync_database_url(self) -> str:
        """Construct synchronous PostgreSQL database URL for setup scripts."""
        if self.db_password:
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        return f"postgresql://{self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}"


# Global configuration instance
config = NetraOptimizerConfig()