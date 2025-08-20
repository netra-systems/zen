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

import os
import sys
import asyncio
import httpx
import aiohttp
import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from tests.unified.e2e.unified_e2e_harness import (
    UnifiedE2ETestHarness,
    create_e2e_harness
)
from tests.unified.test_environment_config import (
    get_test_environment_config,
    TestEnvironmentType,
    TestEnvironment,
    setup_test_environment
)
from tests.unified.real_services_manager import RealServicesManager
from app.core.configuration.base import (
    UnifiedConfigManager,
    get_unified_config,
    validate_config_integrity
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
        self.env_config = get_test_environment_config(
            environment=TestEnvironmentType.STAGING
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
            
        self.test_client = httpx.AsyncClient(timeout=30.0)
        self.aio_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        self.services_manager = RealServicesManager(env_config=self.env_config)
        self.harness = UnifiedE2ETestHarness(environment=TestEnvironmentType.STAGING)
        
        await self.harness.start_test_environment()
        self._validate_staging_prerequisites()
        self._setup_complete = True
    
    def _validate_staging_prerequisites(self) -> None:
        """Validate staging environment prerequisites."""
        required_env_vars = ["DATABASE_URL", "REDIS_URL", "CLICKHOUSE_URL"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            import pytest
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
        health_results = {}
        
        # Define service health endpoints
        service_endpoints = {
            "backend": f"{services.backend}/health/",
            "auth": f"{services.auth}/health",
            "frontend": services.frontend,  # Just check accessibility
        }
        
        # Check WebSocket via HTTP health endpoint if available
        if services.websocket:
            ws_health_url = services.websocket.replace("wss://", "https://").replace("/ws", "/health/")
            service_endpoints["websocket"] = ws_health_url
        
        # Run health checks concurrently
        tasks = []
        for service_name, endpoint in service_endpoints.items():
            task = asyncio.create_task(
                self.check_service_health(endpoint),
                name=f"health_check_{service_name}"
            )
            tasks.append((service_name, task))
        
        # Collect results
        for service_name, task in tasks:
            try:
                health_result = await task
                health_results[service_name] = health_result
            except Exception as e:
                health_results[service_name] = ServiceHealthStatus(
                    service_name=service_name,
                    url=service_endpoints.get(service_name, "unknown"),
                    status_code=0,
                    response_time_ms=0,
                    healthy=False,
                    details={"error": f"Health check failed: {str(e)}"}
                )
        
        return health_results
    
    async def cleanup(self) -> None:
        """Cleanup test environment resources."""
        cleanup_errors = []
        
        # Close HTTP clients
        if self.test_client:
            try:
                await self.test_client.aclose()
            except Exception as e:
                cleanup_errors.append(f"test_client cleanup: {e}")
        
        if self.aio_session:
            try:
                await self.aio_session.close()
            except Exception as e:
                cleanup_errors.append(f"aio_session cleanup: {e}")
        
        # Cleanup harness
        if self.harness:
            try:
                await self.harness.cleanup_test_environment()
            except Exception as e:
                cleanup_errors.append(f"harness cleanup: {e}")
        
        # Stop services
        if self.services_manager:
            try:
                await self.services_manager.stop_all_services()
            except Exception as e:
                cleanup_errors.append(f"services cleanup: {e}")
        
        # Log cleanup errors but don't fail
        if cleanup_errors:
            print(f"Cleanup warnings: {cleanup_errors}")
        
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
import pytest

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
    issues = []
    
    # Check critical environment variables
    required_vars = [
        "DATABASE_URL", "REDIS_URL", "CLICKHOUSE_URL",
        "JWT_SECRET_KEY", "FERNET_KEY",
        "GOOGLE_CLIENT_ID", "GEMINI_API_KEY"
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            issues.append(f"Missing environment variable: {var}")
    
    # Validate URL formats
    db_url = os.getenv("DATABASE_URL", "")
    if db_url and not db_url.startswith("postgresql://"):
        issues.append("DATABASE_URL must start with 'postgresql://'")
    
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url and not redis_url.startswith("redis://"):
        issues.append("REDIS_URL must start with 'redis://'")
    
    clickhouse_url = os.getenv("CLICKHOUSE_URL", "")
    if clickhouse_url and not clickhouse_url.startswith("clickhouse://"):
        issues.append("CLICKHOUSE_URL must start with 'clickhouse://'")
    
    # Validate secret key lengths
    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    if jwt_secret and len(jwt_secret) < 32:
        issues.append("JWT_SECRET_KEY must be at least 32 characters")
    
    return len(issues) == 0, issues


async def run_staging_environment_check() -> Dict[str, Any]:
    """Run comprehensive staging environment check and return results."""
    try:
        # Validate environment configuration
        is_valid, issues = validate_staging_environment()
        if not is_valid:
            return {
                "status": "failed",
                "reason": "Environment validation failed",
                "issues": issues
            }
        
        # Test service connectivity
        suite = await get_staging_suite()
        health_results = await suite.run_health_checks()
        
        healthy_services = [name for name, result in health_results.items() if result.healthy]
        unhealthy_services = [name for name, result in health_results.items() if not result.healthy]
        
        return {
            "status": "passed" if len(unhealthy_services) == 0 else "partial",
            "environment": "staging",
            "healthy_services": healthy_services,
            "unhealthy_services": unhealthy_services,
            "total_services": len(health_results),
            "health_details": {
                name: {
                    "healthy": result.healthy,
                    "status_code": result.status_code,
                    "response_time_ms": result.response_time_ms
                }
                for name, result in health_results.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "reason": f"Staging environment check failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


# Convenience functions for common staging test patterns
async def create_test_user_with_token(suite: StagingTestSuite) -> Dict[str, Any]:
    """Create test user and return user data with access token."""
    try:
        user = await suite.harness.create_test_user()
        return {
            "success": True,
            "user_id": user.user_id,
            "access_token": user.access_token,
            "email": getattr(user, 'email', 'test@example.com')
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def test_websocket_connection_flow(suite: StagingTestSuite, user_data: Dict[str, Any]) -> bool:
    """Test WebSocket connection flow with user authentication."""
    try:
        if not user_data.get("success") or not user_data.get("access_token"):
            return False
        
        ws_url = suite.harness.get_websocket_url()
        headers = {"Authorization": f"Bearer {user_data['access_token']}"}
        
        async with suite.aio_session.ws_connect(
            ws_url, headers=headers, ssl=False, timeout=10
        ) as ws:
            # Send connection init
            await ws.send_json({
                "type": "connection_init",
                "payload": {"auth_token": user_data['access_token']}
            })
            
            # Wait for ack
            msg = await ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                return data.get("type") in ["connection_ack", "connected"]
        
        return False
        
    except Exception:
        return False


if __name__ == "__main__":
    # Direct execution for staging environment validation
    result = asyncio.run(run_staging_environment_check())
    print(json.dumps(result, indent=2))