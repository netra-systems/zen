"""Database Environment Validation Service

Ensures proper separation between development, testing, and production databases.
"""

from netra_backend.app.config import settings
from netra_backend.app.logging_config import central_logger
import os

logger = central_logger.get_logger(__name__)

class DatabaseEnvironmentValidator:
    """Validates database configuration based on environment"""
    
    PROD_KEYWORDS = ["prod", "production", "live"]
    TEST_KEYWORDS = ["test", "testing", "staging"]
    DEV_KEYWORDS = ["dev", "development", "local"]
    
    @classmethod
    def _get_environment_settings(cls) -> tuple[str, str]:
        """Get normalized environment and database URL settings."""
        environment = settings.environment.lower()
        database_url = settings.database_url.lower() if settings.database_url else ""
        return environment, database_url
    
    @classmethod
    def _validate_by_environment(cls, environment: str, database_url: str) -> None:
        """Route validation based on environment type."""
        if environment == "production":
            cls._validate_production_database(database_url)
        elif environment == "testing":
            cls._validate_testing_database(database_url)
        elif environment == "development":
            cls._validate_development_database(database_url)
    
    @classmethod
    def validate_database_environment(cls) -> None:
        """Validate that database URL matches the current environment"""
        environment, database_url = cls._get_environment_settings()
        if not database_url:
            logger.warning("No database URL configured")
            return
        cls._validate_by_environment(environment, database_url)
        logger.info(f"Database environment validation passed for {environment}")
    
    @classmethod
    def _validate_production_database(cls, database_url: str) -> None:
        """Ensure production environment uses production database"""
        for keyword in cls.TEST_KEYWORDS + cls.DEV_KEYWORDS:
            if keyword in database_url:
                raise ValueError(
                    f"Production environment cannot use database with '{keyword}' in URL. "
                    f"Please configure a production database."
                )
    
    @classmethod
    def _validate_testing_database(cls, database_url: str) -> None:
        """Ensure testing environment uses test database"""
        for keyword in cls.PROD_KEYWORDS:
            if keyword in database_url:
                raise ValueError(
                    f"Testing environment cannot use production database. "
                    f"Please configure a test database."
                )
    
    @classmethod
    def _validate_development_database(cls, database_url: str) -> None:
        """Ensure development environment doesn't use production database"""
        for keyword in cls.PROD_KEYWORDS:
            if keyword in database_url:
                logger.warning(
                    f"Development environment is using a database with '{keyword}' in URL. "
                    f"Consider using a development database instead."
                )

def validate_database_environment() -> None:
    """Convenience function for database environment validation"""
    DatabaseEnvironmentValidator.validate_database_environment()