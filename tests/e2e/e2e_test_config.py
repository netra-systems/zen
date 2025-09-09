#!/usr/bin/env python
"""
SSOT E2E Test Configuration Module
===================================

MISSION CRITICAL: Single Source of Truth for E2E test environment configuration.
Enables seamless switching between local Docker and staging GCP environments.

CLAUDE.md COMPLIANCE:
- SSOT for test environment configuration
- Real services only (NO MOCKS)
- IsolatedEnvironment for environment access
- Absolute imports only

Business Value:
- Enables testing against both local and staging environments
- Ensures consistency across all E2E tests
- Reduces configuration duplication
"""

import os
import sys
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.isolated_environment import get_env as get_env_instance
from loguru import logger


class TestEnvironment(Enum):
    """Available test environments"""
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"  # Never use for testing!


@dataclass
class E2ETestConfig:
    """SSOT configuration for E2E tests"""
    
    # Core configuration
    environment: TestEnvironment
    backend_url: str
    api_url: str
    websocket_url: str
    auth_url: str
    frontend_url: Optional[str] = None
    
    # Authentication
    test_api_key: Optional[str] = None
    test_jwt_token: Optional[str] = None
    test_user_email: str = "test@example.com"
    test_user_password: str = "test_password_123"
    
    # Test behavior
    timeout: int = 60  # seconds
    retry_count: int = 3
    retry_delay: float = 2.0  # seconds
    websocket_timeout: int = 30  # seconds
    max_concurrent_users: int = 5
    
    # Feature flags
    skip_auth_tests: bool = False
    skip_websocket_auth: bool = False
    use_real_llm: bool = True
    validate_all_events: bool = True
    
    # Performance thresholds
    connection_timeout: float = 10.0
    first_event_max_delay: float = 15.0
    agent_completion_timeout: float = 120.0
    min_response_quality_score: float = 0.7
    
    # Database configuration (for local tests)
    postgres_host: Optional[str] = None
    postgres_port: Optional[int] = None
    redis_host: Optional[str] = None
    redis_port: Optional[int] = None
    
    @property
    def health_endpoint(self) -> str:
        """Get health check endpoint"""
        return f"{self.backend_url}/health"
    
    @property
    def api_health_endpoint(self) -> str:
        """Get API health endpoint"""
        return f"{self.api_url}/health"
    
    @property
    def agent_execute_endpoint(self) -> str:
        """Get agent execution endpoint"""
        return f"{self.api_url}/agent/execute"
    
    @property
    def service_discovery_endpoint(self) -> str:
        """Get service discovery endpoint"""
        return f"{self.api_url}/discovery/services"
    
    def get_headers(self, include_auth: bool = False) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Test-Session": "e2e-test",
            "X-Test-Environment": self.environment.value
        }
        
        if include_auth:
            if self.test_api_key:
                headers["Authorization"] = f"Bearer {self.test_api_key}"
            elif self.test_jwt_token:
                headers["Authorization"] = f"Bearer {self.test_jwt_token}"
                
        return headers
    
    def get_websocket_headers(self) -> Dict[str, str]:
        """Get headers for WebSocket connection"""
        headers = {
            "X-Test-Session": "e2e-test",
            "X-Test-Environment": self.environment.value
        }
        
        if self.test_jwt_token:
            headers["Authorization"] = f"Bearer {self.test_jwt_token}"
            
        return headers
    
    def get_websocket_params(self, user_id: str, session_id: str) -> Dict[str, str]:
        """Get WebSocket connection parameters"""
        params = {
            "user_id": user_id,
            "session_id": session_id
        }
        
        if self.test_jwt_token:
            params["token"] = self.test_jwt_token
            
        return params
    
    def is_available(self) -> bool:
        """Check if the test environment is available"""
        import httpx
        try:
            response = httpx.get(self.health_endpoint, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Environment {self.environment.value} not available: {e}")
            return False


def get_local_config() -> E2ETestConfig:
    """Get configuration for local Docker environment"""
    return E2ETestConfig(
        environment=TestEnvironment.LOCAL,
        backend_url="http://localhost:8000",
        api_url="http://localhost:8000/api",
        websocket_url="ws://localhost:8000/ws",
        auth_url="http://localhost:8081",
        frontend_url="http://localhost:3000",
        
        # Local test credentials
        test_api_key=get_env_instance().get("TEST_API_KEY", "test_api_key_local"),
        test_jwt_token=get_env_instance().get("TEST_JWT_TOKEN", None),
        
        # Local database configuration
        postgres_host="localhost",
        postgres_port=5434,  # Test port
        redis_host="localhost",
        redis_port=6381,  # Test port
        
        # Local test behavior
        skip_auth_tests=False,
        skip_websocket_auth=True,  # Local doesn't require auth for WebSocket
        use_real_llm=get_env_instance().get("USE_REAL_LLM", "true").lower() == "true"
    )


def get_staging_config() -> E2ETestConfig:
    """Get configuration for staging GCP environment"""
    return E2ETestConfig(
        environment=TestEnvironment.STAGING,
        # CRITICAL: Use load balancer endpoints, not direct Cloud Run URLs
        backend_url="https://api.staging.netrasystems.ai",
        api_url="https://api.staging.netrasystems.ai/api",
        websocket_url="wss://api.staging.netrasystems.ai/ws",
        auth_url="https://auth.staging.netrasystems.ai",
        frontend_url="https://app.staging.netrasystems.ai",
        
        # Staging test credentials
        test_api_key=get_env_instance().get("STAGING_TEST_API_KEY", None),
        test_jwt_token=get_env_instance().get("STAGING_TEST_JWT_TOKEN", None),
        
        # Staging test behavior
        skip_auth_tests=True,  # Auth service not deployed yet
        skip_websocket_auth=True,  # WebSocket requires auth
        use_real_llm=True,  # Always use real LLM in staging
        
        # Staging timeouts (longer for network latency)
        timeout=90,
        websocket_timeout=45,
        connection_timeout=15.0,
        first_event_max_delay=20.0
    )


# SSOT: Global configuration instance
_current_config: Optional[E2ETestConfig] = None


def get_e2e_config(force_environment: Optional[str] = None) -> E2ETestConfig:
    """
    Get the current E2E test configuration (SSOT).
    
    Args:
        force_environment: Optional environment to force ("local" or "staging")
        
    Returns:
        E2ETestConfig instance for the selected environment
        
    Environment selection priority:
    1. force_environment parameter
    2. E2E_TEST_ENV environment variable
    3. Default to "local"
    """
    global _current_config
    
    # Determine environment
    if force_environment:
        env_name = force_environment.lower()
    else:
        env_name = get_env_instance().get("E2E_TEST_ENV", "local").lower()
    
    # Validate environment
    if env_name not in ["local", "staging"]:
        logger.warning(f"Invalid test environment '{env_name}', defaulting to 'local'")
        env_name = "local"
    
    # Create or update configuration
    if _current_config is None or force_environment:
        if env_name == "staging":
            _current_config = get_staging_config()
        else:
            _current_config = get_local_config()
        
        logger.info(f"E2E test configuration set to: {_current_config.environment.value}")
        logger.info(f"Backend URL: {_current_config.backend_url}")
        logger.info(f"WebSocket URL: {_current_config.websocket_url}")
        logger.info(f"Using real LLM: {_current_config.use_real_llm}")
    
    return _current_config


def reset_config():
    """Reset the global configuration (useful for testing)"""
    global _current_config
    _current_config = None


# MISSION CRITICAL: WebSocket event requirements
REQUIRED_WEBSOCKET_EVENTS = {
    "agent_started": "User must see agent began processing their problem",
    "agent_thinking": "Real-time reasoning visibility",
    "tool_executing": "Tool usage transparency",
    "tool_completed": "Tool results display",
    "agent_completed": "User must know when valuable response is ready"
}


def validate_websocket_events(events: list) -> Tuple[bool, list]:
    """
    Validate that all required WebSocket events are present.
    
    Args:
        events: List of event dictionaries received
        
    Returns:
        Tuple of (is_valid, missing_events)
    """
    event_types = {event.get("type") for event in events if isinstance(event, dict)}
    missing = [event for event in REQUIRED_WEBSOCKET_EVENTS if event not in event_types]
    return len(missing) == 0, missing


# Export the main function and constants
__all__ = [
    "E2ETestConfig",
    "TestEnvironment", 
    "get_e2e_config",
    "get_local_config",
    "get_staging_config",
    "reset_config",
    "REQUIRED_WEBSOCKET_EVENTS",
    "validate_websocket_events"
]