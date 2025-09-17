"""
Issue #1176 Phase 2: Staging Test Configuration

Creates missing staging test configuration to resolve coordination gaps.
This module addresses the missing 'tests.e2e.staging.staging_test_config' import
that causes coordination failures.

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Staging environment validates Golden Path reliability
- Value Impact: Staging coordination prevents production deployment failures
- Strategic Impact: Reliable staging protects $500K+ ARR from coordination bugs
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from shared.isolated_environment import get_env

@dataclass
class StagingConfig:
    """Staging environment configuration for E2E coordination tests."""

    # Primary service endpoints (canonical URLs) - Issue #1278 domain fix
    BASE_URL: str = "https://staging.netrasystems.ai"
    AUTH_URL: str = "https://staging.netrasystems.ai"
    FRONTEND_URL: str = "https://staging.netrasystems.ai"

    # WebSocket coordination endpoints
    WEBSOCKET_URL: str = "wss://api.staging.netrasystems.ai/ws"
    WEBSOCKET_HTTP_URL: str = "https://api.staging.netrasystems.ai"

    # Service coordination timeouts (Issue #1176 coordination gap mitigation)
    SERVICE_DISCOVERY_TIMEOUT: int = 30
    AUTH_COORDINATION_TIMEOUT: int = 15
    WEBSOCKET_COORDINATION_TIMEOUT: int = 10
    HEALTH_CHECK_TIMEOUT: int = 5

    # Database coordination settings
    DATABASE_COORDINATION_TIMEOUT: int = 20
    REDIS_COORDINATION_TIMEOUT: int = 10

    # Authentication coordination settings
    JWT_VALIDATION_TIMEOUT: int = 5
    AUTH_TOKEN_REFRESH_TIMEOUT: int = 10

    # WebSocket event coordination settings
    WEBSOCKET_EVENT_TIMEOUT: int = 15
    AGENT_COMPLETION_TIMEOUT: int = 60

    # Retry coordination settings for flaky staging environment
    MAX_COORDINATION_RETRIES: int = 3
    COORDINATION_RETRY_DELAY: float = 2.0

    @classmethod
    def from_environment(cls) -> 'StagingConfig':
        """Create staging config from environment variables with SSOT compliance."""
        env = get_env()

        # Use environment overrides if available
        config = cls()

        # Service URL coordination overrides
        if env.get("STAGING_BASE_URL"):
            config.BASE_URL = env.get("STAGING_BASE_URL")
        if env.get("STAGING_AUTH_URL"):
            config.AUTH_URL = env.get("STAGING_AUTH_URL")
        if env.get("STAGING_FRONTEND_URL"):
            config.FRONTEND_URL = env.get("STAGING_FRONTEND_URL")
        if env.get("STAGING_WEBSOCKET_URL"):
            config.WEBSOCKET_URL = env.get("STAGING_WEBSOCKET_URL")

        # Timeout coordination overrides for different environments
        if env.get("STAGING_SERVICE_TIMEOUT"):
            config.SERVICE_DISCOVERY_TIMEOUT = int(env.get("STAGING_SERVICE_TIMEOUT"))
        if env.get("STAGING_AUTH_TIMEOUT"):
            config.AUTH_COORDINATION_TIMEOUT = int(env.get("STAGING_AUTH_TIMEOUT"))
        if env.get("STAGING_WEBSOCKET_TIMEOUT"):
            config.WEBSOCKET_COORDINATION_TIMEOUT = int(env.get("STAGING_WEBSOCKET_TIMEOUT"))

        return config

    def get_coordination_headers(self) -> Dict[str, str]:
        """Get headers for service coordination."""
        return {
            "X-Staging-Test": "true",
            "X-Issue-1176": "phase2-coordination",
            "X-Coordination-Source": "staging-e2e-tests",
            "User-Agent": "Issue-1176-Phase2-Coordination-Tests"
        }

    def get_websocket_coordination_params(self) -> Dict[str, Any]:
        """Get WebSocket coordination parameters for Issue #1176 testing."""
        return {
            "headers": self.get_coordination_headers(),
            "timeout": self.WEBSOCKET_COORDINATION_TIMEOUT,
            "max_retries": self.MAX_COORDINATION_RETRIES,
            "retry_delay": self.COORDINATION_RETRY_DELAY
        }

    def get_auth_coordination_config(self) -> Dict[str, Any]:
        """Get authentication coordination configuration."""
        return {
            "base_url": self.AUTH_URL,
            "timeout": self.AUTH_COORDINATION_TIMEOUT,
            "jwt_validation_timeout": self.JWT_VALIDATION_TIMEOUT,
            "token_refresh_timeout": self.AUTH_TOKEN_REFRESH_TIMEOUT,
            "headers": self.get_coordination_headers()
        }

    def get_service_health_endpoints(self) -> Dict[str, str]:
        """Get service health check endpoints for coordination validation."""
        return {
            "backend": f"{self.BASE_URL}/health",
            "auth": f"{self.AUTH_URL}/health",
            "frontend": f"{self.FRONTEND_URL}/health",
            "websocket": f"{self.WEBSOCKET_HTTP_URL}/ws/health"
        }

    def validate_coordination_readiness(self) -> Dict[str, bool]:
        """Validate staging environment coordination readiness."""
        import asyncio
        import aiohttp

        async def check_endpoint(session: aiohttp.ClientSession, name: str, url: str) -> bool:
            """Check individual endpoint coordination readiness."""
            try:
                async with session.get(
                    url,
                    headers=self.get_coordination_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.HEALTH_CHECK_TIMEOUT)
                ) as response:
                    return response.status == 200
            except Exception:
                return False

        async def check_all_endpoints() -> Dict[str, bool]:
            """Check all service endpoint coordination."""
            endpoints = self.get_service_health_endpoints()
            results = {}

            async with aiohttp.ClientSession() as session:
                for name, url in endpoints.items():
                    results[name] = await check_endpoint(session, name, url)

            return results

        # Run coordination readiness check
        try:
            return asyncio.run(check_all_endpoints())
        except Exception as e:
            # Return all False if coordination check fails
            return {name: False for name in self.get_service_health_endpoints().keys()}

# Global staging configuration instance for Issue #1176 coordination
staging_config = StagingConfig.from_environment()

# Compatibility exports for existing code
STAGING_BASE_URL = staging_config.BASE_URL
STAGING_AUTH_URL = staging_config.AUTH_URL
STAGING_FRONTEND_URL = staging_config.FRONTEND_URL
STAGING_WEBSOCKET_URL = staging_config.WEBSOCKET_URL

# Coordination timeout exports
SERVICE_COORDINATION_TIMEOUT = staging_config.SERVICE_DISCOVERY_TIMEOUT
AUTH_COORDINATION_TIMEOUT = staging_config.AUTH_COORDINATION_TIMEOUT
WEBSOCKET_COORDINATION_TIMEOUT = staging_config.WEBSOCKET_COORDINATION_TIMEOUT

def get_staging_config() -> StagingConfig:
    """Get staging configuration instance for Issue #1176 coordination testing."""
    return staging_config

def get_staging_coordination_headers() -> Dict[str, str]:
    """Get staging coordination headers for Issue #1176 testing."""
    return staging_config.get_coordination_headers()

def validate_staging_coordination() -> Dict[str, bool]:
    """Validate staging environment coordination for Issue #1176 testing."""
    return staging_config.validate_coordination_readiness()