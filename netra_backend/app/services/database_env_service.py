"""Database Environment Validation Service

Ensures proper separation between development, testing, and production databases.
"""

import os
import re
from typing import Dict, Any, List
from urllib.parse import urlparse

from netra_backend.app.config import get_config
settings = get_config()
from netra_backend.app.logging_config import central_logger

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
    
    @staticmethod
    def get_environment_info() -> Dict[str, Any]:
        """Get environment information for health endpoint.
        
        Returns:
            Dictionary containing environment details needed by health endpoint
        """
        try:
            environment = settings.environment.lower() if settings.environment else "unknown"
            database_url = settings.database_url if settings.database_url else ""
            debug_mode = getattr(settings, 'debug', False) or environment in ["development", "testing"]
            
            return {
                "environment": environment,
                "database_url": database_url,
                "debug": debug_mode,
                "host": DatabaseEnvironmentValidator._extract_host_from_url(database_url),
                "port": DatabaseEnvironmentValidator._extract_port_from_url(database_url),
                "database_name": DatabaseEnvironmentValidator._extract_database_name_from_url(database_url)
            }
        except Exception as e:
            logger.error(f"Failed to get environment info: {e}")
            return {
                "environment": "unknown",
                "database_url": "",
                "debug": False,
                "host": "unknown",
                "port": "unknown", 
                "database_name": "unknown"
            }
    
    @staticmethod
    def validate_database_url(database_url: str, environment: str) -> Dict[str, Any]:
        """Validate database URL for given environment.
        
        Args:
            database_url: Database URL to validate
            environment: Environment name (development, testing, staging, production)
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        database_name = "unknown"
        
        try:
            if not database_url:
                errors.append("Database URL is empty")
                return {
                    "database_name": database_name,
                    "valid": False,
                    "errors": errors,
                    "warnings": warnings
                }
            
            # Extract database name from URL
            database_name = DatabaseEnvironmentValidator._extract_database_name_from_url(database_url)
            
            # Validate URL format
            try:
                parsed = urlparse(database_url)
                if not parsed.scheme:
                    errors.append("Database URL missing scheme")
                if not parsed.hostname and "sqlite" not in database_url.lower():
                    errors.append("Database URL missing hostname")
            except Exception as e:
                errors.append(f"Invalid URL format: {e}")
            
            # Environment-specific validation
            environment = environment.lower()
            database_url_lower = database_url.lower()
            
            if environment == "production":
                for keyword in ["test", "testing", "dev", "development", "local"]:
                    if keyword in database_url_lower:
                        errors.append(f"Production environment using {keyword} database")
            elif environment in ["testing", "test"]:
                for keyword in ["prod", "production", "live"]:
                    if keyword in database_url_lower:
                        errors.append(f"Testing environment using production database")
                if "test" not in database_url_lower:
                    warnings.append("Testing environment should use database with 'test' in name")
            elif environment == "development":
                for keyword in ["prod", "production", "live"]:
                    if keyword in database_url_lower:
                        warnings.append(f"Development environment using production-like database")
            
            # Check for common security issues
            if "password" in database_url_lower and database_url_lower.count("@") > 0:
                # Extract password portion for validation
                try:
                    parsed = urlparse(database_url)
                    if parsed.password:
                        password = parsed.password
                        if len(password) < 8:
                            warnings.append("Database password appears to be short")
                        if password.lower() in ["password", "admin", "root", "test"]:
                            errors.append("Database using weak/default password")
                except:
                    pass  # Skip password validation if parsing fails
            
            return {
                "database_name": database_name,
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.error(f"Database URL validation failed: {e}")
            return {
                "database_name": database_name,
                "valid": False,
                "errors": [f"Validation error: {e}"],
                "warnings": warnings
            }
    
    @staticmethod
    def get_safe_database_name(environment: str) -> str:
        """Generate safe database name for environment.
        
        Args:
            environment: Environment name
            
        Returns:
            Safe database name without special characters
        """
        if not environment:
            environment = "unknown"
        
        # Normalize environment name
        safe_name = environment.lower().strip()
        
        # Remove unsafe characters
        safe_name = re.sub(r'[^a-z0-9_]', '_', safe_name)
        
        # Ensure it doesn't start with a number
        if safe_name and safe_name[0].isdigit():
            safe_name = f"env_{safe_name}"
        
        # Add netra prefix for consistency
        if safe_name and not safe_name.startswith("netra_"):
            safe_name = f"netra_{safe_name}"
        
        # Fallback if empty
        if not safe_name:
            safe_name = "netra_unknown"
        
        return safe_name
    
    @staticmethod
    def _extract_host_from_url(database_url: str) -> str:
        """Extract host from database URL."""
        try:
            if not database_url:
                return "unknown"
            parsed = urlparse(database_url)
            return parsed.hostname or "localhost"
        except:
            return "unknown"
    
    @staticmethod
    def _extract_port_from_url(database_url: str) -> str:
        """Extract port from database URL."""
        try:
            if not database_url:
                return "unknown"
            parsed = urlparse(database_url)
            if parsed.port:
                return str(parsed.port)
            # Default ports
            if "postgresql" in database_url.lower():
                return "5432"
            elif "mysql" in database_url.lower():
                return "3306"
            return "unknown"
        except:
            return "unknown"
    
    @staticmethod
    def _extract_database_name_from_url(database_url: str) -> str:
        """Extract database name from URL."""
        try:
            if not database_url:
                return "unknown"
            parsed = urlparse(database_url)
            if parsed.path and len(parsed.path) > 1:
                # Remove leading slash and get database name
                db_name = parsed.path[1:].split('/')[0]
                return db_name if db_name else "unknown"
            return "unknown"
        except:
            return "unknown"
    
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