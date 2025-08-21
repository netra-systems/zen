"""External Services Configuration Management

**CRITICAL: Unified Service Configuration Management**

Manages LLM, Redis, OAuth, and external service configurations.
Eliminates scattered service configuration across the codebase.

**CONFIGURATION MANAGER**: This module is part of the configuration system
and requires some direct os.environ access for bootstrapping. Application
code should use the unified configuration system instead.

Business Value: Ensures reliable service integrations for Enterprise customers.
Prevents service configuration inconsistencies affecting revenue.

Each function ≤8 lines, file ≤300 lines.
"""

import os
from typing import Dict, List, Optional, Any
from netra_backend.app.schemas.Config import AppConfig
from netra_backend.app.schemas.llm_types import LLMProvider
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.core.network_constants import ServicePorts, HostConstants, URLConstants, ServiceEndpoints
from netra_backend.app.core.environment_constants import (
    Environment, EnvironmentVariables, get_current_environment
)


class ServiceConfigManager:
    """Unified external services configuration management.
    
    **MANDATORY**: All service configuration MUST use this manager.
    Ensures consistency across LLM, OAuth, and external integrations.
    """
    
    def __init__(self):
        """Initialize service configuration manager."""
        self._logger = logger
        self._environment = self._get_environment()
        self._service_modes = self._load_service_modes()
        self._service_defaults = self._load_service_defaults()
    
    def _get_environment(self) -> str:
        """Get current environment for service configuration."""
        return get_current_environment()
    
    def _load_service_modes(self) -> Dict[str, str]:
        """Load service operation modes from environment.
        
        CONFIG MANAGER: Direct env access required for service mode bootstrapping.
        """
        # CONFIG BOOTSTRAP: Direct env access for service mode configuration
        return {
            "llm": os.environ.get(EnvironmentVariables.LLM_MODE, "shared").lower(),
            "redis": os.environ.get(EnvironmentVariables.REDIS_MODE, "shared").lower(),
            "clickhouse": os.environ.get(EnvironmentVariables.CLICKHOUSE_MODE, "shared").lower(),
            "auth": os.environ.get(EnvironmentVariables.AUTH_MODE, "shared").lower()
        }
    
    def _load_service_defaults(self) -> Dict[str, dict]:
        """Load default service configurations per environment."""
        return {
            Environment.DEVELOPMENT.value: self._get_development_defaults(),
            Environment.STAGING.value: self._get_staging_defaults(),
            Environment.PRODUCTION.value: self._get_production_defaults(),
            Environment.TESTING.value: self._get_testing_defaults()
        }
    
    def _get_development_defaults(self) -> dict:
        """Get development environment service defaults."""
        return {
            "llm_enabled": True,
            "redis_enabled": True,
            "auth_service_url": ServiceEndpoints.build_auth_service_url(
                port=ServicePorts.AUTH_SERVICE_TEST
            ),
            "frontend_url": ServiceEndpoints.build_frontend_url()
        }
    
    def _get_staging_defaults(self) -> dict:
        """Get staging environment service defaults."""
        return {
            "llm_enabled": True,
            "redis_enabled": True,
            "auth_service_url": "https://auth-staging.netrasystems.ai",
            "frontend_url": URLConstants.STAGING_FRONTEND
        }
    
    def _get_production_defaults(self) -> dict:
        """Get production environment service defaults."""
        return {
            "llm_enabled": True,
            "redis_enabled": True,
            "auth_service_url": "https://auth.netrasystems.ai",
            "frontend_url": URLConstants.PRODUCTION_APP
        }
    
    def _get_testing_defaults(self) -> dict:
        """Get testing environment service defaults."""
        return {
            "llm_enabled": False,
            "redis_enabled": False,
            "auth_service_url": ServiceEndpoints.build_auth_service_url(
                port=ServicePorts.AUTH_SERVICE_TEST
            ),
            "frontend_url": ServiceEndpoints.build_frontend_url()
        }
    
    def populate_service_config(self, config: AppConfig) -> None:
        """Populate all service configuration in config object."""
        self._populate_service_modes(config)
        self._populate_llm_config(config)
        self._populate_service_flags(config)
        self._populate_external_urls(config)
        self._populate_oauth_config(config)
        self._populate_cors_config(config)
        self._populate_environment_vars(config)
        self._logger.info(f"Populated service config for {self._environment}")
    
    def _populate_service_modes(self, config: AppConfig) -> None:
        """Populate service modes into config."""
        config.redis_mode = self._service_modes.get("redis", "shared")
        config.clickhouse_mode = self._service_modes.get("clickhouse", "shared")
        config.llm_mode = self._service_modes.get("llm", "shared")
    
    def _populate_llm_config(self, config: AppConfig) -> None:
        """Populate LLM configuration."""
        llm_api_key = self._get_llm_api_key()
        if llm_api_key:
            self._set_llm_api_keys(config, llm_api_key)
        self._configure_llm_settings(config)
    
    def _populate_service_flags(self, config: AppConfig) -> None:
        """Populate service enabled flags based on modes."""
        defaults = self._service_defaults.get(self._environment, {})
        config.dev_mode_llm_enabled = self._get_service_enabled_status("llm", defaults)
        config.dev_mode_redis_enabled = self._get_service_enabled_status("redis", defaults)
        config.dev_mode_clickhouse_enabled = self._get_service_enabled_status("clickhouse", defaults)
    
    def _populate_external_urls(self, config: AppConfig) -> None:
        """Populate external service URLs.
        
        CONFIG MANAGER: Direct env access for URL configuration loading.
        """
        # CONFIG BOOTSTRAP: Direct env access for URL configuration
        defaults = self._service_defaults.get(self._environment, {})
        config.frontend_url = os.environ.get("FRONTEND_URL", defaults.get("frontend_url"))
        config.api_base_url = os.environ.get("API_BASE_URL", self._get_api_base_url())
    
    def _populate_oauth_config(self, config: AppConfig) -> None:
        """Populate OAuth configuration."""
        if hasattr(config, 'oauth_config'):
            self._set_oauth_urls(config)
            self._set_oauth_scopes(config)
    
    def _populate_cors_config(self, config: AppConfig) -> None:
        """Populate CORS configuration from environment.
        
        CONFIG MANAGER: Direct env access for CORS configuration loading.
        """
        # CONFIG BOOTSTRAP: Direct env access for CORS configuration
        cors_origins_env = os.environ.get("CORS_ORIGINS")
        if cors_origins_env:
            config.cors_origins = self._parse_cors_origins(cors_origins_env)
    
    def _get_llm_api_key(self) -> Optional[str]:
        """Get LLM API key from environment.
        
        CONFIG MANAGER: Direct env access for API key configuration loading.
        """
        # CONFIG BOOTSTRAP: Direct env access for API key loading
        return os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY")
    
    def _set_llm_api_keys(self, config: AppConfig, api_key: str) -> None:
        """Set API key for all LLM configurations."""
        if hasattr(config, 'llm_configs'):
            for llm_name, llm_config in config.llm_configs.items():
                if hasattr(llm_config, 'api_key'):
                    llm_config.api_key = api_key
    
    def _configure_llm_settings(self, config: AppConfig) -> None:
        """Configure LLM-specific settings.
        
        CONFIG MANAGER: Direct env access for LLM configuration loading.
        """
        # CONFIG BOOTSTRAP: Direct env access for LLM settings
        config.llm_cache_enabled = self._get_bool_env("LLM_CACHE_ENABLED", True)
        config.llm_cache_ttl = int(os.environ.get("LLM_CACHE_TTL", "3600"))
        config.llm_heartbeat_enabled = self._get_bool_env("LLM_HEARTBEAT_ENABLED", True)
        config.llm_data_logging_enabled = self._get_bool_env("LLM_DATA_LOGGING_ENABLED", True)
    
    def _get_service_enabled_status(self, service: str, defaults: dict) -> bool:
        """Get service enabled status based on mode and defaults."""
        mode = self._service_modes.get(service, "shared")
        if mode == "disabled":
            return False
        return defaults.get(f"{service}_enabled", True)
    
    def _get_api_base_url(self) -> str:
        """Get API base URL for current environment."""
        if self._environment == Environment.PRODUCTION.value:
            return "https://api.netrasystems.ai"
        elif self._environment == Environment.STAGING.value:
            return "https://api-staging.netrasystems.ai"
        return ServiceEndpoints.build_backend_service_url()
    
    def _set_oauth_urls(self, config: AppConfig) -> None:
        """Set OAuth redirect URLs based on environment."""
        if self._environment == Environment.DEVELOPMENT.value:
            self._set_development_oauth_urls(config)
        elif self._environment == Environment.STAGING.value:
            self._set_staging_oauth_urls(config)
        elif self._environment == Environment.PRODUCTION.value:
            self._set_production_oauth_urls(config)
    
    def _set_development_oauth_urls(self, config: AppConfig) -> None:
        """Set development OAuth URLs."""
        config.oauth_config.authorized_redirect_uris = [
            URLConstants.build_http_url(
                port=ServicePorts.BACKEND_DEFAULT,
                path=URLConstants.API_PREFIX + URLConstants.AUTH_CALLBACK_PATH
            ),
            URLConstants.build_http_url(
                port=ServicePorts.AUTH_SERVICE_TEST,
                path=URLConstants.API_PREFIX + URLConstants.AUTH_CALLBACK_PATH
            ),
            URLConstants.build_http_url(
                port=ServicePorts.FRONTEND_DEFAULT,
                path=URLConstants.AUTH_CALLBACK_PATH
            )
        ]
    
    def _set_staging_oauth_urls(self, config: AppConfig) -> None:
        """Set staging OAuth URLs."""
        config.oauth_config.authorized_redirect_uris = [
            URLConstants.STAGING_FRONTEND + URLConstants.AUTH_CALLBACK_PATH,
            "https://api-staging.netrasystems.ai" + URLConstants.API_PREFIX + URLConstants.AUTH_CALLBACK_PATH
        ]
    
    def _set_production_oauth_urls(self, config: AppConfig) -> None:
        """Set production OAuth URLs."""
        config.oauth_config.authorized_redirect_uris = [
            URLConstants.PRODUCTION_APP + URLConstants.AUTH_CALLBACK_PATH,
            "https://api.netrasystems.ai" + URLConstants.API_PREFIX + URLConstants.AUTH_CALLBACK_PATH
        ]
    
    def _set_oauth_scopes(self, config: AppConfig) -> None:
        """Set OAuth scopes for current environment."""
        config.oauth_config.scopes = ["openid", "email", "profile"]
        if self._environment == Environment.DEVELOPMENT.value:
            config.oauth_config.scopes.append("https://www.googleapis.com/auth/userinfo.email")
    
    def _get_bool_env(self, env_var: str, default: bool) -> bool:
        """Get boolean environment variable with default.
        
        CONFIG MANAGER: Direct env access for boolean configuration parsing.
        """
        # CONFIG BOOTSTRAP: Direct env access for boolean parsing
        value = os.environ.get(env_var, str(default)).lower()
        return value in ["true", "1", "yes", "on"]
    
    def _parse_cors_origins(self, cors_origins_env: str) -> List[str]:
        """Parse CORS origins from environment string."""
        if cors_origins_env.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    
    def validate_service_consistency(self, config: AppConfig) -> List[str]:
        """Validate service configuration consistency."""
        issues = []
        issues.extend(self._validate_llm_consistency(config))
        issues.extend(self._validate_url_consistency(config))
        issues.extend(self._validate_oauth_consistency(config))
        return issues
    
    def _validate_llm_consistency(self, config: AppConfig) -> List[str]:
        """Validate LLM configuration consistency."""
        issues = []
        if hasattr(config, 'llm_configs'):
            api_keys = set()
            for llm_name, llm_config in config.llm_configs.items():
                if hasattr(llm_config, 'api_key') and llm_config.api_key:
                    api_keys.add(llm_config.api_key)
            if len(api_keys) > 1:
                issues.append("Inconsistent LLM API keys across configurations")
        return issues
    
    def _validate_url_consistency(self, config: AppConfig) -> List[str]:
        """Validate URL configuration consistency."""
        issues = []
        if hasattr(config, 'frontend_url') and hasattr(config, 'api_base_url'):
            if self._environment == Environment.PRODUCTION.value:
                if "localhost" in config.frontend_url:
                    issues.append("Production frontend_url contains localhost")
                if "localhost" in config.api_base_url:
                    issues.append("Production api_base_url contains localhost")
        return issues
    
    def _validate_oauth_consistency(self, config: AppConfig) -> List[str]:
        """Validate OAuth configuration consistency."""
        issues = []
        if hasattr(config, 'oauth_config'):
            if not config.oauth_config.authorized_redirect_uris:
                issues.append("No OAuth redirect URIs configured")
            elif self._environment == Environment.PRODUCTION.value:
                for uri in config.oauth_config.authorized_redirect_uris:
                    if "localhost" in uri:
                        issues.append("Production OAuth redirect URI contains localhost")
        return issues
    
    def get_enabled_services_count(self) -> int:
        """Get count of enabled services for monitoring."""
        enabled_count = 0
        for service, mode in self._service_modes.items():
            if mode != "disabled":
                enabled_count += 1
        return enabled_count
    
    def _populate_environment_vars(self, config: AppConfig) -> None:
        """Populate environment variables into config.
        
        CONFIG MANAGER: Direct env access for configuration variable loading.
        """
        # CONFIG BOOTSTRAP: Direct env access for configuration population
        # Environment detection variables
        config.pytest_current_test = os.environ.get("PYTEST_CURRENT_TEST")
        config.testing = os.environ.get("TESTING")
        config.environment = os.environ.get("ENVIRONMENT", config.environment)
        
        # Auth service configuration
        config.auth_service_url = os.environ.get("AUTH_SERVICE_URL", config.auth_service_url)
        config.auth_service_enabled = os.environ.get("AUTH_SERVICE_ENABLED", config.auth_service_enabled)
        config.auth_fast_test_mode = os.environ.get("AUTH_FAST_TEST_MODE", config.auth_fast_test_mode)
        config.auth_cache_ttl_seconds = os.environ.get("AUTH_CACHE_TTL_SECONDS", config.auth_cache_ttl_seconds)
        config.service_id = os.environ.get("SERVICE_ID", config.service_id)
        config.service_secret = os.environ.get("SERVICE_SECRET", config.service_secret)
        
        # Cloud Run environment variables
        config.k_service = os.environ.get("K_SERVICE")
        config.k_revision = os.environ.get("K_REVISION")
        
        # PR environment variables
        config.pr_number = os.environ.get("PR_NUMBER")
        
        # OAuth client ID fallback variables
        config.google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
        config.google_oauth_client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")

    def get_service_summary(self) -> Dict[str, Any]:
        """Get service configuration summary for monitoring."""
        return {
            "environment": self._environment,
            "service_modes": self._service_modes,
            "llm_configured": bool(self._get_llm_api_key()),
            "oauth_configured": bool(os.environ.get("GOOGLE_CLIENT_ID")),  # CONFIG BOOTSTRAP
            "enabled_services": self.get_enabled_services_count()
        }