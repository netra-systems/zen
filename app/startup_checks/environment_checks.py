"""
Environment Checks

Handles environment variable and configuration validation.
Maintains 8-line function limit and focused responsibility.
"""

import os
from typing import List
from app.config import settings
from .models import StartupCheckResult


class EnvironmentChecker:
    """Handles environment and configuration checks"""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.is_staging = self.environment == "staging" or os.getenv("K_SERVICE")
    
    async def check_environment_variables(self) -> StartupCheckResult:
        """Check required environment variables are set"""
        required_vars = self._get_required_vars()
        optional_vars = self._get_optional_vars()
        missing_required = self._check_missing_vars(required_vars)
        missing_optional = self._check_missing_vars(optional_vars)
        
        if missing_required:
            return self._create_missing_vars_result(missing_required)
        return self._create_success_result(missing_optional)
    
    async def check_configuration(self) -> StartupCheckResult:
        """Validate application configuration"""
        try:
            self._validate_all_configs()
            return self._create_config_success_result()
        except Exception as e:
            return self._create_config_failure_result(e)
    
    def _get_required_vars(self) -> List[str]:
        """Get required environment variables"""
        # Always require these critical variables
        return ["DATABASE_URL", "SECRET_KEY"]
    
    def _get_optional_vars(self) -> List[str]:
        """Get optional environment variables"""
        return [
            "REDIS_URL",
            "CLICKHOUSE_URL",
            "ANTHROPIC_API_KEY",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET"
        ]
    
    def _check_missing_vars(self, vars_list: List[str]) -> List[str]:
        """Check for missing variables"""
        return [var for var in vars_list if not os.getenv(var)]
    
    def _create_success_result(self, missing_optional: List[str]) -> StartupCheckResult:
        """Create success result with optional variables info"""
        msg = self._build_success_message(missing_optional)
        return StartupCheckResult(
            name="environment_variables", success=True,
            message=msg, critical=True
        )
    
    def _validate_database_config(self) -> None:
        """Validate database configuration"""
        if not self.is_staging and not settings.database_url:
            raise ValueError("DATABASE_URL is not configured")
    
    def _validate_secret_key(self) -> None:
        """Validate secret key configuration"""
        if not settings.secret_key or len(settings.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
    
    def _validate_environment(self) -> None:
        """Validate environment setting"""
        valid_environments = ["development", "testing", "staging", "production"]
        if settings.environment not in valid_environments:
            raise ValueError(f"Invalid environment: {settings.environment}")
    
    def _create_missing_vars_result(self, missing_required: List[str]) -> StartupCheckResult:
        """Create result for missing required variables"""
        return StartupCheckResult(
            name="environment_variables", success=False, critical=not self.is_staging,
            message=f"Missing required environment variables: {', '.join(missing_required)}"
        )
    
    def _validate_all_configs(self) -> None:
        """Validate all configuration settings"""
        self._validate_database_config()
        self._validate_secret_key()
        self._validate_environment()
    
    def _create_config_success_result(self) -> StartupCheckResult:
        """Create successful configuration result"""
        return StartupCheckResult(
            name="configuration", success=True, critical=not self.is_staging,
            message=f"Configuration valid for {settings.environment} environment"
        )
    
    def _create_config_failure_result(self, error: Exception) -> StartupCheckResult:
        """Create failed configuration result"""
        return StartupCheckResult(
            name="configuration", success=False, critical=not self.is_staging,
            message=str(error)
        )
    
    def _build_success_message(self, missing_optional: List[str]) -> str:
        """Build success message with optional variables info"""
        msg = "All required environment variables are set"
        if self.environment == "development":
            msg = "Development mode - using default configs"
        if missing_optional:
            msg += f" (Optional missing: {', '.join(missing_optional)})"
        return msg