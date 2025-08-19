"""
OAuth configuration and environment detection for auth client.
Handles OAuth settings for different environments and deployment contexts.
"""

import os
import logging
from typing import List
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Environment types for auth configuration."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class OAuthConfig:
    """OAuth configuration for environment."""
    client_id: str = ""
    client_secret: str = ""
    redirect_uris: List[str] = None
    javascript_origins: List[str] = None
    allow_dev_login: bool = False
    allow_mock_auth: bool = False
    use_proxy: bool = False
    proxy_url: str = ""

    def __post_init__(self):
        """Initialize lists if None."""
        if self.redirect_uris is None:
            self.redirect_uris = []
        if self.javascript_origins is None:
            self.javascript_origins = []


class EnvironmentDetector:
    """Detects current deployment environment from various indicators."""
    
    def detect_environment(self) -> Environment:
        """Detect current environment from environment variables."""
        env_override = os.getenv("ENVIRONMENT", "").lower()
        if env_override:
            return self._parse_environment(env_override)
        if self._check_testing_flag():
            return Environment.TESTING
        return self._detect_from_cloud_run()
    
    def _create_env_mapping(self) -> dict:
        """Create environment string to enum mapping."""
        return {
            "development": Environment.DEVELOPMENT,
            "testing": Environment.TESTING,
            "staging": Environment.STAGING,
            "production": Environment.PRODUCTION,
        }
    
    def _handle_unknown_environment(self, env_str: str) -> Environment:
        """Handle unknown environment string."""
        logger.warning(f"Unknown environment '{env_str}', defaulting to development")
        return Environment.DEVELOPMENT
    
    def _parse_environment(self, env_str: str) -> Environment:
        """Parse environment string to enum."""
        env_map = self._create_env_mapping()
        if env_str in env_map:
            return env_map[env_str]
        return self._handle_unknown_environment(env_str)
    
    def _check_testing_flag(self) -> bool:
        """Check if TESTING flag is set."""
        return os.getenv("TESTING") in ["true", "1"]
    
    def _get_cloud_run_vars(self) -> tuple[str, str]:
        """Get Cloud Run environment variables."""
        k_service = os.getenv("K_SERVICE", "")
        k_revision = os.getenv("K_REVISION", "")
        return k_service, k_revision
    
    def _log_cloud_run_fallback(self) -> None:
        """Log fallback to staging for Cloud Run detection."""
        logger.warning("Could not detect environment from Cloud Run variables, defaulting to staging")
    
    def _detect_from_cloud_run(self) -> Environment:
        """Detect environment from Cloud Run variables."""
        k_service, k_revision = self._get_cloud_run_vars()
        if k_service or k_revision:
            return self._detect_cloud_run_environment(k_service, k_revision)
        self._log_cloud_run_fallback()
        return Environment.STAGING
    
    def _detect_cloud_run_environment(self, k_service: str, k_revision: str) -> Environment:
        """Detect environment from Cloud Run service names."""
        if self._is_production_service(k_service) or self._is_production_service(k_revision):
            return Environment.PRODUCTION
        if self._is_staging_service(k_service) or self._is_staging_service(k_revision):
            return Environment.STAGING
        return Environment.STAGING
    
    def _is_production_service(self, name: str) -> bool:
        """Check if service name indicates production."""
        name_lower = name.lower()
        # More precise production detection - must explicitly have 'prod' or 'production'
        # 'backend' alone is not enough as staging can have backends too
        return any(prod in name_lower for prod in ["prod", "production"])
    
    def _is_staging_service(self, name: str) -> bool:
        """Check if service name indicates staging."""
        return "staging" in name.lower()


class OAuthCredentialManager:
    """Manages OAuth credential retrieval with fallback chain."""
    
    def _build_env_var_name(self, cred_type: str, env_suffix: str) -> str:
        """Build environment variable name for credential."""
        # Handle CLIENT_SECRET to avoid double CLIENT_
        if cred_type == "CLIENT_SECRET":
            return f"GOOGLE_OAUTH_{cred_type}_{env_suffix}"
        return f"GOOGLE_OAUTH_CLIENT_{cred_type}_{env_suffix}"
    
    def _try_primary_credential(self, env_var: str) -> str:
        """Try to get primary credential from environment."""
        return os.getenv(env_var, "")
    
    def _log_missing_credential(self, env_var: str) -> None:
        """Log missing credential warning."""
        logger.error(f"Missing OAuth credential: {env_var}")
    
    def get_oauth_credential(self, env_suffix: str, cred_type: str) -> str:
        """Get OAuth credential with fallback chain."""
        env_var = self._build_env_var_name(cred_type, env_suffix)
        credential = self._try_primary_credential(env_var)
        if not credential:
            credential = self._get_fallback_credential(cred_type)
        return self._validate_credential_result(credential, env_var)
    
    def _validate_credential_result(self, credential: str, env_var: str) -> str:
        """Validate credential result and log if missing."""
        if not credential:
            self._log_missing_credential(env_var)
        return credential
    
    def _get_fallback_credential(self, cred_type: str) -> str:
        """Get fallback OAuth credential."""
        if cred_type == "CLIENT_ID":
            fallback_var = "GOOGLE_CLIENT_ID"
        else:
            fallback_var = f"GOOGLE_CLIENT_{cred_type}"
        return os.getenv(fallback_var, "")


class OAuthConfigGenerator:
    """Generates OAuth configuration for different environments."""
    
    def __init__(self):
        self.credential_manager = OAuthCredentialManager()
    
    def _create_config_mapping(self) -> dict:
        """Create environment to config function mapping."""
        return {
            Environment.DEVELOPMENT: self._get_dev_oauth_config,
            Environment.TESTING: self._get_test_oauth_config,
            Environment.STAGING: self._get_staging_oauth_config,
            Environment.PRODUCTION: self._get_prod_oauth_config,
        }
    
    def _validate_config_for_env(self, config: OAuthConfig, environment: Environment) -> bool:
        """Validate config for production environments."""
        critical_envs = [Environment.STAGING, Environment.PRODUCTION]
        return not (not config.client_id and environment in critical_envs)
    
    def _handle_config_validation_failure(self, environment: Environment) -> OAuthConfig:
        """Handle config validation failure."""
        logger.error(f"Missing OAuth client ID for environment: {environment.value}")
        return self._get_fallback_oauth_config()
    
    def _handle_config_exception(self, error: Exception) -> OAuthConfig:
        """Handle config generation exception."""
        logger.error(f"Failed to get OAuth config: {error}", exc_info=True)
        return self._get_fallback_oauth_config()
    
    def get_oauth_config(self, environment: Environment) -> OAuthConfig:
        """Get OAuth configuration for current environment."""
        try:
            config_map = self._create_config_mapping()
            config_func = config_map.get(environment, self._get_fallback_oauth_config)
            config = config_func()
            return self._validate_and_return_config(config, environment)
        except Exception as e:
            return self._handle_config_exception(e)
    
    def _validate_and_return_config(self, config: OAuthConfig, environment: Environment) -> OAuthConfig:
        """Validate config and return or fallback."""
        if not self._validate_config_for_env(config, environment):
            return self._handle_config_validation_failure(environment)
        return config
    
    def _get_dev_credentials(self) -> tuple[str, str]:
        """Get development OAuth credentials."""
        client_id = self.credential_manager.get_oauth_credential("DEV", "CLIENT_ID")
        client_secret = self.credential_manager.get_oauth_credential("DEV", "CLIENT_SECRET")
        return client_id, client_secret
    
    def _get_dev_oauth_config(self) -> OAuthConfig:
        """Get development OAuth configuration."""
        client_id, client_secret = self._get_dev_credentials()
        return self._build_dev_config(client_id, client_secret)
    
    def _build_dev_config(self, client_id: str, client_secret: str) -> OAuthConfig:
        """Build development OAuth configuration."""
        return OAuthConfig(
            client_id=client_id, client_secret=client_secret,
            redirect_uris=self._get_dev_redirect_uris(),
            javascript_origins=self._get_dev_js_origins(),
            allow_dev_login=True, allow_mock_auth=True, use_proxy=False
        )
    
    def _get_test_credentials(self) -> tuple[str, str]:
        """Get testing OAuth credentials."""
        client_id = self.credential_manager.get_oauth_credential("TEST", "CLIENT_ID")
        client_secret = self.credential_manager.get_oauth_credential("TEST", "CLIENT_SECRET")
        return client_id, client_secret
    
    def _get_test_oauth_config(self) -> OAuthConfig:
        """Get testing OAuth configuration."""
        client_id, client_secret = self._get_test_credentials()
        return self._build_test_config(client_id, client_secret)
    
    def _build_test_config(self, client_id: str, client_secret: str) -> OAuthConfig:
        """Build testing OAuth configuration."""
        return OAuthConfig(
            client_id=client_id, client_secret=client_secret,
            redirect_uris=["http://test.local:8000/api/auth/callback"],
            javascript_origins=["http://test.local:3000"],
            allow_dev_login=False, allow_mock_auth=True, use_proxy=False
        )
    
    def _get_staging_credentials(self) -> tuple[str, str]:
        """Get staging OAuth credentials."""
        client_id = self.credential_manager.get_oauth_credential("STAGING", "CLIENT_ID")
        client_secret = self.credential_manager.get_oauth_credential("STAGING", "CLIENT_SECRET")
        return client_id, client_secret
    
    def _check_pr_environment(self) -> bool:
        """Check if running in PR environment."""
        return bool(os.getenv("PR_NUMBER"))
    
    def _get_staging_oauth_config(self) -> OAuthConfig:
        """Get staging OAuth configuration."""
        client_id, client_secret = self._get_staging_credentials()
        if self._check_pr_environment():
            return self._get_pr_oauth_config(client_id, client_secret)
        return self._build_staging_config(client_id, client_secret)
    
    def _build_staging_config(self, client_id: str, client_secret: str) -> OAuthConfig:
        """Build staging OAuth configuration."""
        return OAuthConfig(
            client_id=client_id, client_secret=client_secret,
            redirect_uris=self._get_staging_redirect_uris(),
            javascript_origins=self._get_staging_js_origins(),
            allow_dev_login=False, allow_mock_auth=False, use_proxy=False
        )
    
    def _get_prod_credentials(self) -> tuple[str, str]:
        """Get production OAuth credentials."""
        client_id = self.credential_manager.get_oauth_credential("PROD", "CLIENT_ID")
        client_secret = self.credential_manager.get_oauth_credential("PROD", "CLIENT_SECRET")
        return client_id, client_secret
    
    def _get_prod_oauth_config(self) -> OAuthConfig:
        """Get production OAuth configuration."""
        client_id, client_secret = self._get_prod_credentials()
        return self._build_prod_config(client_id, client_secret)
    
    def _build_prod_config(self, client_id: str, client_secret: str) -> OAuthConfig:
        """Build production OAuth configuration."""
        return OAuthConfig(
            client_id=client_id, client_secret=client_secret,
            redirect_uris=self._get_prod_redirect_uris(),
            javascript_origins=self._get_prod_js_origins(),
            allow_dev_login=False, allow_mock_auth=False, use_proxy=False
        )
    
    def _build_pr_origins(self, proxy_url: str, pr_number: str) -> List[str]:
        """Build PR environment JavaScript origins."""
        origins = [proxy_url]
        if pr_number:
            origins.append(f"https://pr-{pr_number}.staging.netrasystems.ai")
        return origins
    
    def _get_pr_oauth_config(self, client_id: str, client_secret: str) -> OAuthConfig:
        """Get PR environment OAuth configuration with proxy."""
        pr_number = os.getenv("PR_NUMBER", "")
        proxy_url = "https://auth.staging.netrasystems.ai"
        origins = self._build_pr_origins(proxy_url, pr_number)
        return self._build_pr_config(client_id, client_secret, proxy_url, origins)
    
    def _build_pr_config(self, client_id: str, client_secret: str, proxy_url: str, origins: List[str]) -> OAuthConfig:
        """Build PR OAuth configuration."""
        return OAuthConfig(
            client_id=client_id, client_secret=client_secret,
            redirect_uris=[f"{proxy_url}/callback"], javascript_origins=origins,
            allow_dev_login=False, allow_mock_auth=False,
            use_proxy=True, proxy_url=proxy_url
        )
    
    def _get_dev_redirect_uris(self) -> List[str]:
        """Get development redirect URIs."""
        base_uris = ["http://localhost:8000/api/auth/callback",
                     "http://localhost:3000/api/auth/callback",
                     "http://localhost:3010/api/auth/callback"]
        auth_uris = ["http://localhost:3000/auth/callback",
                     "http://localhost:3010/auth/callback"]
        return base_uris + auth_uris
    
    def _get_dev_js_origins(self) -> List[str]:
        """Get development JavaScript origins."""
        return ["http://localhost:3000", "http://localhost:3010", "http://localhost:8000"]
    
    def _get_staging_redirect_uris(self) -> List[str]:
        """Get staging redirect URIs."""
        return ["https://staging.netrasystems.ai/auth/callback",
                "https://auth.staging.netrasystems.ai/auth/callback",
                "https://app.staging.netrasystems.ai/auth/callback"]
    
    def _get_staging_js_origins(self) -> List[str]:
        """Get staging JavaScript origins."""
        return ["https://staging.netrasystems.ai", 
                "https://auth.staging.netrasystems.ai",
                "https://app.staging.netrasystems.ai"]
    
    def _get_prod_redirect_uris(self) -> List[str]:
        """Get production redirect URIs."""
        return ["https://netrasystems.ai/auth/callback",
                "https://auth.netrasystems.ai/auth/callback",
                "https://app.netrasystems.ai/auth/callback"]
    
    def _get_prod_js_origins(self) -> List[str]:
        """Get production JavaScript origins."""
        return ["https://netrasystems.ai", 
                "https://auth.netrasystems.ai",
                "https://app.netrasystems.ai"]
    
    def _get_fallback_client_id(self) -> str:
        """Get fallback client ID with multiple attempts."""
        return (
            os.getenv("GOOGLE_CLIENT_ID") or 
            os.getenv("GOOGLE_OAUTH_CLIENT_ID") or 
            ""
        )
    
    def _create_fallback_config(self, client_id: str) -> OAuthConfig:
        """Create fallback configuration object."""
        return OAuthConfig(
            client_id=client_id,
            client_secret="",  # Empty but service can still start
            redirect_uris=["https://api.staging.netrasystems.ai/api/auth/callback"],
            javascript_origins=["https://staging.netrasystems.ai"],
            allow_dev_login=False,
            allow_mock_auth=False,
            use_proxy=False
        )
    
    def _get_fallback_oauth_config(self) -> OAuthConfig:
        """Get fallback OAuth configuration when normal config fails."""
        logger.warning("Using fallback OAuth configuration")
        client_id = self._get_fallback_client_id()
        return self._create_fallback_config(client_id)