"""Environment-specific OAuth configuration management."""

import os
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.logging_config import central_logger as logger
from app.config import get_config


class Environment(Enum):
    """Application environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class OAuthConfig:
    """OAuth configuration for an environment."""
    client_id: str
    client_secret: str
    redirect_uris: List[str]
    javascript_origins: List[str]
    use_proxy: bool = False
    proxy_url: Optional[str] = None
    allow_dev_login: bool = False
    allow_mock_auth: bool = False


class EnvironmentAuthConfig:
    """Manages environment-specific authentication configuration."""
    
    def __init__(self) -> None:
        self.environment = self._detect_environment()
        self.pr_number = os.getenv("PR_NUMBER")
        self.is_pr_environment = bool(self.pr_number and self.environment == Environment.STAGING)
        
    def _detect_environment(self) -> Environment:
        """Detect the current environment."""
        if os.getenv("TESTING"):
            return Environment.TESTING
            
        # Check for Cloud Run deployment
        if os.getenv("K_SERVICE") or os.getenv("K_REVISION"):
            service_name = os.getenv("K_SERVICE", "").lower()
            if "staging" in service_name or os.getenv("PR_NUMBER"):
                return Environment.STAGING
            return Environment.PRODUCTION
            
        # Explicit environment override
        env_name = os.getenv("ENVIRONMENT", "development").lower()
        
        try:
            return Environment(env_name)
        except ValueError:
            logger.warning(f"Unknown environment: {env_name}, defaulting to development")
            return Environment.DEVELOPMENT
    
    def get_oauth_config(self) -> OAuthConfig:
        """Get OAuth configuration for the current environment."""
        configs = {
            Environment.DEVELOPMENT: self._get_dev_config(),
            Environment.TESTING: self._get_test_config(),
            Environment.STAGING: self._get_staging_config(),
            Environment.PRODUCTION: self._get_prod_config(),
        }
        
        config = configs[self.environment]
        logger.info(f"Loaded OAuth config for {self.environment.value} environment")
        if self.is_pr_environment:
            logger.info(f"PR environment detected: PR #{self.pr_number}")
        
        return config
    
    def _get_dev_config(self) -> OAuthConfig:
        """Development environment OAuth configuration."""
        # Get OAuth credentials from config first, then fallback to env vars
        config = get_config()
        
        # Support multiple naming conventions for dev OAuth credentials
        # Priority order: Config > DEV specific > Generic > Empty
        client_id = (
            config.oauth_config.client_id or
            os.getenv("GOOGLE_OAUTH_CLIENT_ID_DEV") or 
            os.getenv("GOOGLE_CLIENT_ID") or
            os.getenv("GOOGLE_OAUTH_CLIENT_ID") or
            ""
        )
        client_secret = (
            config.oauth_config.client_secret or
            os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_DEV") or 
            os.getenv("GOOGLE_CLIENT_SECRET") or
            os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or
            ""
        )
        
        # Log configuration status
        if client_id:
            logger.info(f"OAuth client ID configured: {client_id[:20]}...")
        else:
            logger.error("No OAuth client ID found! Set GOOGLE_CLIENT_ID in .env")
        
        if not client_secret:
            logger.error("No OAuth client secret found! Set GOOGLE_CLIENT_SECRET in .env")
        
        return OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=[
                "http://localhost:8000/api/auth/callback",
                "http://localhost:3000/api/auth/callback",
                "http://localhost:3010/api/auth/callback",
                "http://localhost:3000/auth/callback",
                "http://localhost:3010/auth/callback",
            ],
            javascript_origins=[
                "http://localhost:3000",
                "http://localhost:3010",
                "http://localhost:8000",
            ],
            allow_dev_login=True,
            allow_mock_auth=True,
        )
    
    def _get_test_config(self) -> OAuthConfig:
        """Testing environment OAuth configuration."""
        return OAuthConfig(
            client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID_TEST", ""),
            client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_TEST", ""),
            redirect_uris=[
                "http://api.test.local/api/auth/callback",
            ],
            javascript_origins=[
                "http://test.local",
                "http://api.test.local",
            ],
            allow_dev_login=False,
            allow_mock_auth=True,
        )
    
    def _get_staging_config(self) -> OAuthConfig:
        """Staging environment OAuth configuration."""
        # Get OAuth credentials from config (loaded from Secret Manager)
        config = get_config()
        client_id = config.oauth_config.client_id or os.getenv("GOOGLE_OAUTH_CLIENT_ID_STAGING", "")
        client_secret = config.oauth_config.client_secret or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_STAGING", "")
        
        # For PR environments, use the OAuth proxy
        if self.is_pr_environment:
            return OAuthConfig(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uris=[
                    "https://auth.staging.netrasystems.ai/callback",
                ],
                javascript_origins=[
                    "https://auth.staging.netrasystems.ai",
                    f"https://pr-{self.pr_number}.staging.netrasystems.ai",
                    f"https://pr-{self.pr_number}-api.staging.netrasystems.ai",
                ],
                use_proxy=True,
                proxy_url="https://auth.staging.netrasystems.ai",
                allow_dev_login=False,
                allow_mock_auth=False,
            )
        
        # Regular staging environment
        return OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=[
                "https://staging.netrasystems.ai/api/auth/callback",
                "https://api.staging.netrasystems.ai/auth/callback",
            ],
            javascript_origins=[
                "https://staging.netrasystems.ai",
                "https://api.staging.netrasystems.ai",
            ],
            allow_dev_login=False,
            allow_mock_auth=False,
        )
    
    def _get_prod_config(self) -> OAuthConfig:
        """Production environment OAuth configuration."""
        # Get OAuth credentials from config (loaded from Secret Manager)
        config = get_config()
        client_id = config.oauth_config.client_id or os.getenv("GOOGLE_OAUTH_CLIENT_ID_PROD", "")
        client_secret = config.oauth_config.client_secret or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_PROD", "")
        
        return OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=[
                "https://api.netrasystems.ai/api/auth/callback",
                "https://netrasystems.ai/auth/callback",
            ],
            javascript_origins=[
                "https://netrasystems.ai",
                "https://api.netrasystems.ai",
            ],
            allow_dev_login=False,
            allow_mock_auth=False,
        )
    
    def get_frontend_config(self) -> Dict:
        """Get frontend-specific auth configuration."""
        config = self.get_oauth_config()
        base_config = {
            "environment": self.environment.value,
            "google_client_id": config.client_id,
            "allow_dev_login": config.allow_dev_login,
            "javascript_origins": config.javascript_origins,
        }
        
        if self.is_pr_environment:
            base_config.update({
                "pr_number": self.pr_number,
                "use_proxy": True,
                "proxy_url": config.proxy_url,
            })
        
        return base_config
    
    def validate_redirect_uri(self, uri: str) -> bool:
        """Validate if a redirect URI is allowed for this environment."""
        config = self.get_oauth_config()
        
        # For PR environments with proxy, check if it's the proxy URL
        if config.use_proxy and config.proxy_url:
            if uri.startswith(config.proxy_url):
                return True
        
        # Check against configured redirect URIs
        return uri in config.redirect_uris
    
    def get_oauth_state_data(self) -> Dict:
        """Get data to encode in OAuth state parameter."""
        data = {
            "environment": self.environment.value,
            "timestamp": int(time.time()),
        }
        
        if self.is_pr_environment:
            data["pr_number"] = self.pr_number
            
        return data


# Singleton instance
auth_env_config = EnvironmentAuthConfig()