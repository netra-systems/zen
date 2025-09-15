"""
Centralized staging environment configuration.
Single Source of Truth (SSOT) for all staging test configurations.
"""

from typing import Dict, Optional
from shared.isolated_environment import IsolatedEnvironment


class StagingConfig:
    """Centralized configuration for staging environment tests."""
    
    # GCP Project Configuration
    GCP_PROJECT_ID = "netra-staging"
    GCP_PROJECT_NUMBER = "701982941522"
    GCP_REGION = "us-central1"
    
    # Default environment - CRITICAL: Must be 'staging' for staging tests
    DEFAULT_ENVIRONMENT = "staging"
    
    # Service URLs - Use canonical staging URLs per CLAUDE.md deployment requirements
    SERVICE_URLS = {
        "staging": {
            "NETRA_BACKEND_URL": "https://api.staging.netrasystems.ai",
            "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
            "FRONTEND_URL": "https://app.staging.netrasystems.ai",
            "NETRA_API_URL": "https://api.staging.netrasystems.ai",
            "WEBSOCKET_URL": "wss://api.staging.netrasystems.ai/ws"
        },
        "development": {
            "NETRA_BACKEND_URL": "http://localhost:8088",
            "AUTH_SERVICE_URL": "http://localhost:8001",
            "FRONTEND_URL": "http://localhost:3000",
            "NETRA_API_URL": "http://localhost:8088",
            "WEBSOCKET_URL": "ws://localhost:8088/ws"
        }
    }
    
    # Test credentials for staging
    TEST_CREDENTIALS = {
        "test_email": "test_user@example.com",
        "test_password": "TestPassword123!",
        "test_username": "test_user"
    }
    
    # Timeout configurations
    TIMEOUTS = {
        "default": 30,
        "websocket": 60,
        "agent_execution": 120,
        "health_check": 10
    }
    
    @classmethod
    def get_environment(cls) -> str:
        """Get the current environment, defaulting to staging."""
        env = IsolatedEnvironment()
        return env.get("ENVIRONMENT", cls.DEFAULT_ENVIRONMENT)
    
    @classmethod
    def get_service_url(cls, service: str, environment: Optional[str] = None) -> str:
        """Get the URL for a specific service."""
        env = environment or cls.get_environment()
        if env not in cls.SERVICE_URLS:
            raise ValueError(f"Unknown environment: {env}")
        
        service_key = f"{service.upper()}_URL"
        if service_key not in cls.SERVICE_URLS[env]:
            # Try with _SERVICE suffix
            service_key = f"{service.upper()}_SERVICE_URL"
            if service_key not in cls.SERVICE_URLS[env]:
                raise ValueError(f"Unknown service: {service}")
        
        return cls.SERVICE_URLS[env][service_key]
    
    @classmethod
    def get_headers(cls, auth_token: Optional[str] = None) -> Dict[str, str]:
        """Get standard headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        return headers
    
    @classmethod
    def is_staging_environment(cls) -> bool:
        """Check if we're running in staging environment."""
        return cls.get_environment() == "staging"
    
    @classmethod
    def validate_staging_urls(cls) -> bool:
        """Validate that all staging URLs are properly configured."""
        env = "staging"
        required_services = ["NETRA_BACKEND_URL", "AUTH_SERVICE_URL", "FRONTEND_URL"]
        
        for service in required_services:
            url = cls.SERVICE_URLS[env].get(service)
            if not url or "localhost" in url:
                return False
            # Validate canonical staging URLs per CLAUDE.md requirements
            if "staging.netrasystems.ai" not in url:
                return False
        
        return True
