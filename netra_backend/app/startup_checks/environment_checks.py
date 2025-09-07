"""
Environment Checks

Handles environment variable and configuration validation.
Maintains 25-line function limit and focused responsibility.
"""

from typing import List

from netra_backend.app.core.configuration import unified_config_manager
from netra_backend.app.startup_checks.models import StartupCheckResult


class EnvironmentChecker:
    """Handles environment and configuration checks"""
    
    def __init__(self):
        config = unified_config_manager.get_config()
        self.environment = config.environment.lower()
        self.is_staging = self.environment == "staging" or (hasattr(config, 'k_service') and config.k_service)
    
    async def check_environment_variables(self) -> StartupCheckResult:
        """Check required environment variables are set"""
        check_data = self._prepare_environment_check_data()
        return self._evaluate_environment_variables(check_data)
    
    def _prepare_environment_check_data(self) -> dict:
        """Prepare data for environment variable checks"""
        required_vars = self._get_required_vars()
        optional_vars = self._get_optional_vars()
        return {
            "missing_required": self._check_missing_vars(required_vars),
            "missing_optional": self._check_missing_vars(optional_vars)
        }
    
    def _evaluate_environment_variables(self, check_data: dict) -> StartupCheckResult:
        """Evaluate environment variable check results"""
        if check_data["missing_required"]:
            return self._create_missing_vars_result(check_data["missing_required"])
        return self._create_success_result(check_data["missing_optional"])
    
    async def check_configuration(self) -> StartupCheckResult:
        """Validate application configuration"""
        try:
            self._validate_all_configs()
            return self._create_config_success_result()
        except Exception as e:
            return self._create_config_failure_result(e)
    
    def _get_required_vars(self) -> List[str]:
        """Get required environment variables"""
        # In development mode, these can use defaults from settings
        if self.environment == "development":
            return []  # Allow defaults in development
        # In production/staging, require explicit configuration
        # #removed-legacyis built from individual POSTGRES_* variables via DatabaseURLBuilder
        return ["SECRET_KEY"]
    
    def _get_optional_vars(self) -> List[str]:
        """Get optional environment variables"""
        service_vars = self._get_optional_service_vars()
        auth_vars = self._get_optional_auth_vars()
        return service_vars + auth_vars
    
    def _get_optional_service_vars(self) -> List[str]:
        """Get optional service environment variables"""
        return ["REDIS_URL", "CLICKHOUSE_URL", "ANTHROPIC_API_KEY"]
    
    def _get_optional_auth_vars(self) -> List[str]:
        """Get optional authentication environment variables"""
        # OAuth credentials are handled by the auth service, not backend
        # Backend only needs JWT tokens and service secrets for auth
        return []
    
    def _check_missing_vars(self, vars_list: List[str]) -> List[str]:
        """Check for missing variables"""
        config = unified_config_manager.get_config()
        missing = []
        for var in vars_list:
            # Convert env var names to config attribute names (lowercase, underscores)
            attr_name = var.lower()
            if not hasattr(config, attr_name) or not getattr(config, attr_name):
                missing.append(var)
        return missing
    
    def _create_success_result(self, missing_optional: List[str]) -> StartupCheckResult:
        """Create success result with optional variables info"""
        msg = self._build_success_message(missing_optional)
        return StartupCheckResult(
            name="environment_variables", success=True,
            message=msg, critical=True
        )
    
    def _validate_database_config(self) -> None:
        """Validate database configuration"""
        # In development, allow default database URL
        if self.environment == "development":
            return  # Skip validation, allow defaults
        config = unified_config_manager.get_config()
        # #removed-legacyis now built from individual POSTGRES_* variables via DatabaseURLBuilder
        # Check that we can construct a database URL (the backend_environment handles this)
        from netra_backend.app.core.backend_environment import get_backend_env
        db_url = get_backend_env().get_database_url()
        if not self.is_staging and not db_url:
            raise ValueError("Database configuration not found (check POSTGRES_* environment variables)")
    
    def _validate_secret_key(self) -> None:
        """Validate secret key configuration"""
        # In development, allow default secret key
        if self.environment == "development":
            return  # Skip validation, allow defaults
        config = unified_config_manager.get_config()
        secret_key = getattr(config, 'secret_key', '')
        if not secret_key or len(secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
    
    def _validate_environment(self) -> None:
        """Validate environment setting"""
        valid_environments = ["development", "testing", "staging", "production"]
        config = unified_config_manager.get_config()
        if config.environment not in valid_environments:
            raise ValueError(f"Invalid environment: {config.environment}")
    
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
            message=f"Configuration valid for {self.environment} environment"
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