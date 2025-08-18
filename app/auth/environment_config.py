"""Environment-specific authentication configuration module.

Provides EnvironmentAuthConfig for detecting environment and configuring OAuth.
Follows 300-line module limit and 8-line function limit (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All (Free, Early, Mid, Enterprise)
2. Business Goal: Ensure reliable auth across all environments  
3. Value Impact: Auth failures = 100% user churn
4. Revenue Impact: Critical for all revenue streams
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

# Import from existing schema types for consistency
from app.schemas.config_types import Environment

logger = logging.getLogger(__name__)

__all__ = ["EnvironmentAuthConfig", "Environment", "OAuthConfig", "auth_env_config"]


@dataclass
class OAuthConfig:
    """OAuth configuration for specific environment."""
    client_id: str = ""
    client_secret: str = ""
    redirect_uris: List[str] = None
    javascript_origins: List[str] = None
    allow_dev_login: bool = False
    allow_mock_auth: bool = False
    use_proxy: bool = False
    proxy_url: str = ""

    def __post_init__(self):
        """Initialize empty lists if None provided."""
        if self.redirect_uris is None:
            self.redirect_uris = []
        if self.javascript_origins is None:
            self.javascript_origins = []


class EnvironmentAuthConfig:
    """Environment-specific authentication configuration manager."""
    
    def __init__(self):
        """Initialize environment detection and configuration."""
        self._environment = self._detect_environment()
        self._is_pr_environment = self._detect_pr_environment()
        self._pr_number = os.getenv("PR_NUMBER", "")
        
    @property
    def environment(self) -> Environment:
        """Get detected environment."""
        return self._environment
        
    @property
    def is_pr_environment(self) -> bool:
        """Check if running in PR environment."""
        return self._is_pr_environment
        
    @property
    def pr_number(self) -> str:
        """Get PR number if in PR environment."""
        return self._pr_number
        
    def _detect_environment(self) -> Environment:
        """Detect current environment from various indicators."""
        env_override = os.getenv("ENVIRONMENT", "").lower()
        if env_override:
            return self._parse_environment_string(env_override)
        if self._is_testing_environment():
            return Environment.TESTING
        return self._detect_from_cloud_run()
        
    def _parse_environment_string(self, env_str: str) -> Environment:
        """Parse environment string to Environment enum."""
        env_mapping = {
            "development": Environment.DEVELOPMENT,
            "testing": Environment.TESTING,
            "staging": Environment.STAGING,
            "production": Environment.PRODUCTION,
        }
        result = env_mapping.get(env_str, Environment.DEVELOPMENT)
        if env_str not in env_mapping:
            logger.warning(f"Unknown environment '{env_str}', defaulting to development")
        return result
        
    def _is_testing_environment(self) -> bool:
        """Check if TESTING flag indicates testing environment."""
        testing_flag = os.getenv("TESTING", "").lower()
        return testing_flag in ["true", "1"]
        
    def _detect_from_cloud_run(self) -> Environment:
        """Detect environment from Cloud Run service variables."""
        k_service = os.getenv("K_SERVICE", "")
        k_revision = os.getenv("K_REVISION", "")
        if not k_service and not k_revision:
            return Environment.DEVELOPMENT
        return self._analyze_cloud_run_names(k_service, k_revision)
        
    def _analyze_cloud_run_names(self, k_service: str, k_revision: str) -> Environment:
        """Analyze Cloud Run service/revision names for environment."""
        # K_SERVICE takes precedence over K_REVISION
        if k_service:
            if self._contains_staging_keywords(k_service, ""):
                return Environment.STAGING
            if self._contains_production_keywords(k_service, ""):
                return Environment.PRODUCTION
        if k_revision:
            if self._contains_staging_keywords("", k_revision):
                return Environment.STAGING
            if self._contains_production_keywords("", k_revision):
                return Environment.PRODUCTION
        return Environment.PRODUCTION  # Default for Cloud Run ambiguous cases
        
    def _contains_production_keywords(self, k_service: str, k_revision: str) -> bool:
        """Check if service/revision names contain production keywords."""
        names = f"{k_service} {k_revision}".lower()
        prod_keywords = ["prod", "production"]
        # Special case: services ending with just service name (e.g., netra-backend)
        # are considered production if they don't contain staging
        if "staging" not in names and any(keyword in names for keyword in prod_keywords):
            return True
        # Also check for services that don't contain staging and have backend/auth
        if "staging" not in names and ("backend" in names or "auth" in names):
            return True
        return False
        
    def _contains_staging_keywords(self, k_service: str, k_revision: str) -> bool:
        """Check if service/revision names contain staging keywords."""
        names = f"{k_service} {k_revision}".lower()
        staging_keywords = ["staging", "-pr-"]
        return any(keyword in names for keyword in staging_keywords)
        
    def _detect_pr_environment(self) -> bool:
        """Detect if running in PR environment."""
        pr_number = os.getenv("PR_NUMBER")
        k_service = os.getenv("K_SERVICE", "").lower()
        k_revision = os.getenv("K_REVISION", "").lower()
        # PR environment if PR_NUMBER exists and staging context
        if pr_number:
            if "staging" in k_service or "staging" in k_revision:
                return True
            if "pr" in k_service or "pr" in k_revision:
                return True
        return False
        
    def get_oauth_config(self) -> OAuthConfig:
        """Get OAuth configuration for current environment."""
        logger.info(f"Getting OAuth config for environment: {self.environment.value}")
        if self.is_pr_environment:
            logger.info(f"PR environment detected: PR #{self.pr_number}")
        config_methods = {
            Environment.DEVELOPMENT: self._get_development_oauth_config,
            Environment.TESTING: self._get_testing_oauth_config,
            Environment.STAGING: self._get_staging_oauth_config,
            Environment.PRODUCTION: self._get_production_oauth_config,
        }
        method = config_methods.get(self.environment, self._get_fallback_oauth_config)
        return method()
        
    def _get_development_oauth_config(self) -> OAuthConfig:
        """Get OAuth configuration for development environment."""
        client_id = self._get_oauth_env_var("DEV", "CLIENT_ID")
        client_secret = self._get_oauth_env_var("DEV", "CLIENT_SECRET")
        return OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=self._get_dev_redirect_uris(),
            javascript_origins=self._get_dev_javascript_origins(),
            allow_dev_login=True,
            allow_mock_auth=True,
            use_proxy=False
        )
        
    def _get_testing_oauth_config(self) -> OAuthConfig:
        """Get OAuth configuration for testing environment."""
        client_id = self._get_oauth_env_var("TEST", "CLIENT_ID")
        client_secret = self._get_oauth_env_var("TEST", "CLIENT_SECRET")
        return OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=["http://test.local:8000/api/auth/callback"],
            javascript_origins=["http://test.local:3000"],
            allow_dev_login=False,
            allow_mock_auth=True,
            use_proxy=False
        )
        
    def _get_staging_oauth_config(self) -> OAuthConfig:
        """Get OAuth configuration for staging environment."""
        client_id = self._get_oauth_env_var("STAGING", "CLIENT_ID")
        client_secret = self._get_oauth_env_var("STAGING", "CLIENT_SECRET")
        if self.is_pr_environment:
            return self._get_pr_oauth_config(client_id, client_secret)
        return self._get_standard_staging_oauth_config(client_id, client_secret)
        
    def _get_production_oauth_config(self) -> OAuthConfig:
        """Get OAuth configuration for production environment."""
        client_id = self._get_oauth_env_var("PROD", "CLIENT_ID")
        client_secret = self._get_oauth_env_var("PROD", "CLIENT_SECRET")
        return OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=self._get_prod_redirect_uris(),
            javascript_origins=self._get_prod_javascript_origins(),
            allow_dev_login=False,
            allow_mock_auth=False,
            use_proxy=False
        )
        
    def _get_pr_oauth_config(self, client_id: str, client_secret: str) -> OAuthConfig:
        """Get OAuth configuration for PR environment with proxy."""
        proxy_url = "https://auth.staging.netrasystems.ai"
        redirect_uris = [f"{proxy_url}/callback"]
        js_origins = [proxy_url]
        if self.pr_number:
            pr_origin = f"https://pr-{self.pr_number}.staging.netrasystems.ai"
            pr_api_origin = f"https://pr-{self.pr_number}-api.staging.netrasystems.ai"
            js_origins.extend([pr_origin, pr_api_origin])
        return OAuthConfig(
            client_id=client_id, client_secret=client_secret,
            redirect_uris=redirect_uris, javascript_origins=js_origins,
            allow_dev_login=False, allow_mock_auth=False,
            use_proxy=True, proxy_url=proxy_url
        )
        
    def _get_standard_staging_oauth_config(self, client_id: str, client_secret: str) -> OAuthConfig:
        """Get standard staging OAuth configuration."""
        return OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=self._get_staging_redirect_uris(),
            javascript_origins=self._get_staging_javascript_origins(),
            allow_dev_login=False,
            allow_mock_auth=False,
            use_proxy=False
        )
        
    def _get_fallback_oauth_config(self) -> OAuthConfig:
        """Get fallback OAuth configuration when detection fails."""
        logger.warning("Using fallback OAuth configuration")
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        return OAuthConfig(
            client_id=client_id,
            client_secret="",
            redirect_uris=["https://api.staging.netrasystems.ai/api/auth/callback"],
            javascript_origins=["https://staging.netrasystems.ai"],
            allow_dev_login=False,
            allow_mock_auth=False,
            use_proxy=False
        )
        
    def _get_oauth_env_var(self, env_suffix: str, cred_type: str) -> str:
        """Get OAuth environment variable with fallback."""
        primary_var = f"GOOGLE_OAUTH_{cred_type}_{env_suffix}"
        primary_value = os.getenv(primary_var, "")
        if primary_value:
            return primary_value
        fallback_value = self._get_fallback_oauth_credential(cred_type)
        if not fallback_value:
            logger.error(f"Missing OAuth credential: {primary_var}")
        return fallback_value
        
    def _get_fallback_oauth_credential(self, cred_type: str) -> str:
        """Get fallback OAuth credential from generic environment variables."""
        if cred_type == "CLIENT_ID":
            return os.getenv("GOOGLE_CLIENT_ID", "")
        return os.getenv(f"GOOGLE_CLIENT_{cred_type}", "")
        
    def _get_dev_redirect_uris(self) -> List[str]:
        """Get development environment redirect URIs."""
        return [
            "http://localhost:8000/api/auth/callback",
            "http://localhost:3000/api/auth/callback",
            "http://localhost:3010/api/auth/callback",
            "http://localhost:3000/auth/callback",
            "http://localhost:3010/auth/callback"
        ]
        
    def _get_dev_javascript_origins(self) -> List[str]:
        """Get development environment JavaScript origins."""
        return [
            "http://localhost:3000",
            "http://localhost:3010", 
            "http://localhost:8000"
        ]
        
    def _get_staging_redirect_uris(self) -> List[str]:
        """Get staging environment redirect URIs."""
        return [
            "https://staging.netrasystems.ai/api/auth/callback",
            "https://api.staging.netrasystems.ai/auth/callback"
        ]
        
    def _get_staging_javascript_origins(self) -> List[str]:
        """Get staging environment JavaScript origins."""
        return [
            "https://staging.netrasystems.ai",
            "https://api.staging.netrasystems.ai"
        ]
        
    def _get_prod_redirect_uris(self) -> List[str]:
        """Get production environment redirect URIs."""
        return [
            "https://api.netrasystems.ai/api/auth/callback",
            "https://netrasystems.ai/auth/callback"
        ]
        
    def _get_prod_javascript_origins(self) -> List[str]:
        """Get production environment JavaScript origins."""
        return [
            "https://netrasystems.ai",
            "https://api.netrasystems.ai"
        ]
        
    def get_frontend_config(self) -> Dict[str, Any]:
        """Get frontend configuration including PR-specific data."""
        oauth_config = self.get_oauth_config()
        config = {
            "environment": self.environment.value,
            "google_client_id": oauth_config.client_id,
            "allow_dev_login": oauth_config.allow_dev_login,
            "javascript_origins": oauth_config.javascript_origins,
            "use_proxy": oauth_config.use_proxy,
            "proxy_url": oauth_config.proxy_url
        }
        if self.is_pr_environment and self.pr_number:
            config["pr_number"] = self.pr_number
        return config

    def validate_redirect_uri(self, uri: str) -> bool:
        """Validate redirect URI for current environment."""
        oauth_config = self.get_oauth_config()
        return uri in oauth_config.redirect_uris

    def get_oauth_state_data(self) -> Dict[str, Any]:
        """Get OAuth state data for CSRF protection."""
        import time
        state_data = {
            "environment": self.environment.value,
            "timestamp": int(time.time())
        }
        if self.is_pr_environment and self.pr_number:
            state_data["pr_number"] = self.pr_number
        return state_data


# Create singleton instance for global access
auth_env_config = EnvironmentAuthConfig()