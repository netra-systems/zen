"""Staging Test Helpers and Utilities

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity and Test Infrastructure
- Value Impact: Reduces code duplication and standardizes staging test patterns
- Strategic Impact: Enables faster, more reliable staging validation

Provides shared utilities for staging tests:
- StagingTestSuite class for consistent test setup
- ServiceHealthStatus for health check results
- Common test fixtures and helpers
- Shared cleanup and error handling
"""

import asyncio
import json
import os
import sys
import time
import pytest
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import httpx

from netra_backend.app.core.configuration.base import (
    UnifiedConfigManager,
    get_unified_config,
    validate_config_integrity,
)
from tests.e2e.unified_e2e_harness import (
    UnifiedE2ETestHarness,
    create_e2e_harness,
)
from tests.e2e.service_manager import RealServicesManager
from tests.e2e.config import (
    TestEnvironmentConfig,
    TestEnvironmentType,
    get_test_environment_config,
)


@dataclass
class ServiceHealthStatus:
    """Service health check result container."""
    service_name: str
    url: str
    status_code: int
    response_time_ms: int
    healthy: bool
    details: Optional[Dict] = None


@dataclass
class StagingTestResult:
    """Container for staging test results with business metrics."""
    test_name: str
    status: str
    duration_seconds: float
    error_message: Optional[str] = None
    details: Optional[Dict] = None


class StagingTestSuite:
    """Unified staging test suite with shared utilities and setup."""
    
    def __init__(self):
        """Initialize staging test environment configuration."""
        # Use LOCAL configuration for websocket testing (starts local services)
        self.env_config = get_test_environment_config(
            environment=TestEnvironmentType.LOCAL
        )
        self.config_manager = UnifiedConfigManager()
        self.services_manager: Optional[RealServicesManager] = None
        self.test_client: Optional[httpx.AsyncClient] = None
        self.harness: Optional[UnifiedE2ETestHarness] = None
        self.aio_session: Optional[aiohttp.ClientSession] = None
        self._setup_complete = False
    
    async def setup(self) -> None:
        """Setup test environment for staging validation."""
        if self._setup_complete:
            return
            
        self.test_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self.aio_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        self.services_manager = RealServicesManager(project_root=Path.cwd())
        self.harness = UnifiedE2ETestHarness(environment=TestEnvironmentType.LOCAL)
        
        # Fix: Use the correct method name
        await self.harness.test_start_test_environment()
        self._validate_staging_prerequisites()
        self._setup_complete = True
    
    def _validate_staging_prerequisites(self) -> None:
        """Validate staging environment prerequisites."""
        required_env_vars = ["DATABASE_URL", "REDIS_URL", "CLICKHOUSE_URL"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing staging environment variables: {missing_vars}")
    
    async def check_service_health(self, url: str) -> ServiceHealthStatus:
        """Check service health with comprehensive error handling."""
        start_time = time.time()
        try:
            response = await self.test_client.get(url)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Parse response details
            details = {}
            try:
                if response.headers.get("content-type", "").startswith("application/json"):
                    details = response.json()
            except Exception:
                details = {"raw_content": response.text[:200]}
            
            return ServiceHealthStatus(
                service_name=self._extract_service_name(url),
                url=url,
                status_code=response.status_code,
                response_time_ms=duration_ms,
                healthy=response.status_code == 200,
                details=details
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ServiceHealthStatus(
                service_name=self._extract_service_name(url),
                url=url,
                status_code=0,
                response_time_ms=duration_ms,
                healthy=False,
                details={"error": str(e)}
            )
    
    def _extract_service_name(self, url: str) -> str:
        """Extract service name from URL for identification."""
        if "auth" in url:
            return "auth"
        elif "backend" in url or "api" in url:
            return "backend"
        elif "websocket" in url or "ws" in url:
            return "websocket"
        elif "frontend" in url:
            return "frontend"
        else:
            return "unknown"
    
    async def run_health_checks(self) -> Dict[str, ServiceHealthStatus]:
        """Run health checks for all configured services."""
        services = self.env_config.services
        endpoints = {
            "backend": f"{services.backend}/health/",
            "auth": f"{services.auth}/health",
            "frontend": services.frontend
        }
        
        health_results = {}
        for name, endpoint in endpoints.items():
            try:
                result = await self.check_service_health(endpoint)
                health_results[name] = result
            except Exception as e:
                health_results[name] = ServiceHealthStatus(
                    service_name=name, url=endpoint, status_code=0,
                    response_time_ms=0, healthy=False, details={"error": str(e)}
                )
        return health_results
    
    async def cleanup(self) -> None:
        """Cleanup test environment resources."""
        for client in [self.test_client, self.aio_session]:
            if client:
                try:
                    await client.aclose() if hasattr(client, 'aclose') else await client.close()
                except Exception:
                    pass
        
        for manager in [self.harness, self.services_manager]:
            if manager:
                try:
                    # Fix: Use the correct cleanup method name
                    if hasattr(manager, 'test_cleanup_test_environment'):
                        await manager.test_cleanup_test_environment()
                    elif hasattr(manager, 'cleanup_test_environment'):
                        await manager.cleanup_test_environment()
                    elif hasattr(manager, 'stop_all_services'):
                        await manager.stop_all_services()
                except Exception:
                    pass
        
        self._setup_complete = False


# Global staging suite instance for reuse across tests
_staging_suite: Optional[StagingTestSuite] = None

async def get_staging_suite() -> StagingTestSuite:
    """Get or create shared staging test suite instance."""
    global _staging_suite
    
    if _staging_suite is None:
        _staging_suite = StagingTestSuite()
        await _staging_suite.setup()
    
    return _staging_suite


# Pytest fixture for automatic staging suite management

@pytest.fixture
async def staging_suite():
    """Pytest fixture for staging test suite with automatic cleanup."""
    suite = await get_staging_suite()
    try:
        yield suite
    finally:
        # Note: We don't cleanup the global suite to allow reuse across tests
        # Cleanup happens at the end of the test session
        pass


@pytest.fixture(scope="session", autouse=True)
async def staging_suite_session_cleanup():
    """Session-level fixture to cleanup staging suite at the end."""
    yield
    
    global _staging_suite
    if _staging_suite:
        try:
            await _staging_suite.cleanup()
        except Exception as e:
            print(f"Session cleanup error: {e}")
        finally:
            _staging_suite = None


def validate_staging_environment() -> tuple[bool, List[str]]:
    """Validate staging environment configuration and return issues."""
    required_vars = [
        "DATABASE_URL", "REDIS_URL", "CLICKHOUSE_URL",
        "JWT_SECRET_KEY", "FERNET_KEY", "GOOGLE_CLIENT_ID", "GEMINI_API_KEY"
    ]
    
    issues = [f"Missing: {var}" for var in required_vars if not os.getenv(var)]
    
    # Basic URL validation
    for var, prefix in [("DATABASE_URL", "postgresql://"), ("REDIS_URL", "redis://"), ("CLICKHOUSE_URL", "clickhouse://")]:
        value = os.getenv(var, "")
        if value and not value.startswith(prefix):
            issues.append(f"{var} invalid format")
    
    # JWT secret length check
    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    if jwt_secret and len(jwt_secret) < 32:
        issues.append("JWT_SECRET_KEY too short")
    
    return len(issues) == 0, issues


async def run_staging_environment_check() -> Dict[str, Any]:
    """Run comprehensive staging environment check and return results."""
    try:
        is_valid, issues = validate_staging_environment()
        if not is_valid:
            return {"status": "failed", "issues": issues}
        
        suite = await get_staging_suite()
        health_results = await suite.run_health_checks()
        healthy_count = sum(1 for result in health_results.values() if result.healthy)
        
        return {
            "status": "passed" if healthy_count == len(health_results) else "partial",
            "healthy_services": healthy_count,
            "total_services": len(health_results)
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}


# Convenience functions for common staging test patterns
async def create_test_user_with_token(suite: StagingTestSuite) -> Dict[str, Any]:
    """Create test user and return user data with access token."""
    try:
        # Ensure harness is properly initialized and started
        if not suite.harness or not suite.harness.ready:
            await suite.setup()
            
        user = await suite.harness.create_test_user()
        return {
            "success": True,
            "user_id": getattr(user, 'id', user.id if hasattr(user, 'id') else 'test_user'),
            "access_token": user.tokens.get('access_token') if user.tokens else f"test-token-{user.id}",
            "email": getattr(user, 'email', 'test@example.com')
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def validate_websocket_connection_flow(suite: StagingTestSuite, user_data: Dict[str, Any]) -> bool:
    """Test WebSocket connection flow with user authentication."""
    try:
        if not user_data.get("success") or not user_data.get("access_token"):
            return False
        
        ws_url = suite.harness.get_websocket_url()
        headers = {"Authorization": f"Bearer {user_data['access_token']}"}
        
        async with suite.aio_session.ws_connect(
            ws_url, headers=headers, ssl=False, timeout=10
        ) as ws:
            await ws.send_json({
                "type": "connection_init",
                "payload": {"auth_token": user_data['access_token']}
            })
            
            msg = await ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                return data.get("type") in ["connection_ack", "connected"]
        return False
    except Exception:
        return False


if __name__ == "__main__":
    result = asyncio.run(run_staging_environment_check())
    print(json.dumps(result, indent=2))