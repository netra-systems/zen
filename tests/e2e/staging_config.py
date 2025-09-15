"""
Staging Environment Configuration for E2E Tests

This module provides centralized configuration for staging environment URLs
and connection settings for E2E tests that run against deployed staging services.

Business Value:
- Enables testing against real deployed staging environment
- Validates production-like behavior before deployment
- Prevents $50K+ MRR loss from staging environment issues
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass
import logging
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class StagingURLs:
    """Centralized staging environment URLs from deployed GCP services."""
    
    # Primary staging URLs (Golden Path domains)
    backend_url: str = "https://api.staging.netrasystems.ai"
    auth_url: str = "https://auth.staging.netrasystems.ai"
    frontend_url: str = "https://app.staging.netrasystems.ai"
    
    # WebSocket URL (derived from backend)
    @property
    def websocket_url(self) -> str:
        """Get WebSocket URL from backend URL."""
        return self.backend_url.replace("https://", "wss://") + "/ws"
    
    # API endpoints
    @property
    def api_base_url(self) -> str:
        """Get API base URL."""
        return f"{self.backend_url}/api/v1"
    
    @property
    def health_endpoints(self) -> Dict[str, str]:
        """Get health check endpoints for all services."""
        return {
            "backend": f"{self.backend_url}/health",
            "auth": f"{self.auth_url}/auth/health",
            "frontend": f"{self.frontend_url}/health"
        }


class StagingTestConfig:
    """Configuration for staging E2E tests."""
    
    def __init__(self):
        """Initialize staging test configuration."""
        self.urls = StagingURLs()
        self.environment = "staging"
        self.timeout = 30.0  # Longer timeout for Cloud Run cold starts
        self.max_retries = 3
        self.verify_ssl = True
        
        # OAUTH SIMULATION configuration
        env = get_env()
        self.E2E_OAUTH_SIMULATION_KEY = env.get("E2E_OAUTH_SIMULATION_KEY") or "staging-e2e-test-bypass-key-2025"
        self.test_user_email = "e2e-test@staging.netrasystems.ai"
        self.test_user_name = "E2E Test User"
        
        # WebSocket configuration
        self.ws_heartbeat_interval = 30
        self.ws_reconnect_delay = 2
        self.ws_max_reconnect_attempts = 5
        
        # Compatibility attributes - expose URL properties directly for legacy tests
        self.backend_url = self.urls.backend_url
        self.auth_url = self.urls.auth_url
        self.auth_service_url = self.urls.auth_url  # Alternative name for legacy compatibility
        self.frontend_url = self.urls.frontend_url
        self.websocket_url = self.urls.websocket_url
        
    def get_auth_headers(self, token: str) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Environment": "staging",
            "X-Test-Suite": "e2e"
        }
    
    def get_websocket_headers(self, token: str) -> Dict[str, str]:
        """Get headers for WebSocket connection."""
        return {
            "Authorization": f"Bearer {token}",
            "X-Environment": "staging",
            "X-Client-Type": "e2e-test"
        }
    
    def get_bypass_auth_headers(self) -> Dict[str, str]:
        """Get headers for OAUTH SIMULATION endpoint."""
        if not self.E2E_OAUTH_SIMULATION_KEY:
            raise ValueError("E2E_OAUTH_SIMULATION_KEY not set in environment")
        
        return {
            "X-E2E-Bypass-Key": self.E2E_OAUTH_SIMULATION_KEY,
            "Content-Type": "application/json"
        }
    
    def validate_configuration(self) -> bool:
        """Validate that all required configuration is present."""
        issues = []
        
        if not self.E2E_OAUTH_SIMULATION_KEY:
            # Try to get fallback value from environment again during validation
            fallback_key = get_env().get("E2E_OAUTH_SIMULATION_KEY") or "staging-e2e-test-bypass-key-2025"
            if fallback_key:
                self.E2E_OAUTH_SIMULATION_KEY = fallback_key
                logger.warning(f"Using fallback E2E_OAUTH_SIMULATION_KEY during validation: {fallback_key}")
            else:
                issues.append("E2E_OAUTH_SIMULATION_KEY not set and no fallback available")
        
        if not self.urls.backend_url:
            issues.append("Backend URL not configured")
            
        if not self.urls.auth_url:
            issues.append("Auth URL not configured")
            
        if not self.urls.frontend_url:
            issues.append("Frontend URL not configured")
        
        if issues:
            logger.error(f"Staging configuration validation failed: {', '.join(issues)}")
            return False
        
        logger.info("Staging configuration validated successfully")
        return True
    
    def log_configuration(self) -> None:
        """Log current staging configuration for debugging."""
        logger.info("=== Staging Test Configuration ===")
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Backend URL: {self.urls.backend_url}")
        logger.info(f"Auth URL: {self.urls.auth_url}")
        logger.info(f"Frontend URL: {self.urls.frontend_url}")
        logger.info(f"WebSocket URL: {self.urls.websocket_url}")
        logger.info(f"API Base URL: {self.urls.api_base_url}")
        logger.info(f"Test User: {self.test_user_email}")
        logger.info(f"Timeout: {self.timeout}s")
        logger.info(f"SSL Verification: {self.verify_ssl}")
        logger.info("=================================")


# Singleton instance
_staging_config: Optional[StagingTestConfig] = None


def get_staging_config() -> StagingTestConfig:
    """Get or create staging test configuration singleton."""
    global _staging_config
    if _staging_config is None:
        _staging_config = StagingTestConfig()
        # Only validate configuration when actually running against staging
        current_env = get_env().get("ENVIRONMENT", get_env().get("TEST_ENV", "test")).lower()
        if current_env == "staging":
            _staging_config.validate_configuration()
            _staging_config.log_configuration()
        else:
            logger.info(f"Staging config loaded for environment '{current_env}' - skipping staging validation")
    return _staging_config


def is_staging_available() -> bool:
    """Check if staging environment is available"""
    import httpx
    import os
    # Override for golden path validation testing
    if os.environ.get("BYPASS_STAGING_HEALTH_CHECK") == "true":
        logger.info("[TEST OVERRIDE] Bypassing staging health check for golden path validation")
        return True
    
    try:
        config = get_staging_config()
        health_url = f"{config.urls.backend_url}/health"
        
        with httpx.Client(timeout=10.0, verify=config.verify_ssl) as client:
            response = client.get(health_url)
            if response.status_code == 200:
                logger.info(f"Staging backend health check passed: {health_url}")
                return True
            else:
                logger.warning(f"Staging backend health check failed: {health_url} returned {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Staging availability check failed: {e}")
        return False


# Export for convenience
staging_urls = StagingURLs()
staging_config = get_staging_config()
