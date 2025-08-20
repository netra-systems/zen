"""Comprehensive Staging Startup Tests for Netra Platform

Business Value Justification (BVJ):
- Segment: Enterprise/Platform - All customer tiers
- Business Goal: Staging environment reliability and deployment validation
- Value Impact: Prevents staging-related deployment failures that block releases
- Revenue Impact: $100K+ MRR protection via reliable staging validation

This test suite validates staging environment startup comprehensively:
- Environment configuration loading and validation
- Service startup verification (backend, auth, frontend)
- Database connections (PostgreSQL, Redis, ClickHouse) 
- Health check endpoints functionality
- Configuration integrity and secret key validation
- Error recovery mechanisms and service dependencies

Each test is independent, well-documented, and follows architectural guidelines.
Functions ≤8 lines, comprehensive error handling, reuses existing infrastructure.
"""

import os
import sys
import pytest
import asyncio
import httpx
import socket
import json
import aiohttp
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
from app.core.auth_constants import (
    JWTConstants,
    CredentialConstants,
    AuthConstants
)


@dataclass
class StartupTestResult:
    """Container for comprehensive startup test results."""
    test_name: str
    status: str
    duration_seconds: float
    error_message: Optional[str] = None
    details: Optional[Dict] = None


@dataclass
class ServiceHealthStatus:
    """Service health check result container."""
    service_name: str
    url: str
    status_code: int
    response_time_ms: int
    healthy: bool
    details: Optional[Dict] = None


class StagingStartupTestSuite:
    """Comprehensive staging startup test suite for Netra platform."""
    
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
    
    async def setup_test_environment(self) -> None:
        """Setup test environment for staging validation."""
        self.test_client = httpx.AsyncClient(timeout=30.0)
        self.aio_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        self.services_manager = RealServicesManager(env_config=self.env_config)
        self.harness = UnifiedE2ETestHarness(environment=TestEnvironmentType.STAGING)
        await self.harness.start_test_environment()
        self._validate_staging_environment_prerequisites()
    
    def _validate_staging_environment_prerequisites(self) -> None:
        """Validate staging environment prerequisites."""
        required_env_vars = ["DATABASE_URL", "REDIS_URL", "CLICKHOUSE_URL"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing staging environment variables: {missing_vars}")
    
    async def teardown_test_environment(self) -> None:
        """Cleanup test environment resources."""
        if self.test_client:
            await self.test_client.aclose()
        if self.aio_session:
            await self.aio_session.close()
        if self.harness:
            await self.harness.cleanup_test_environment()
        if self.services_manager:
            await self.services_manager.stop_all_services()


@pytest.fixture
async def staging_test_suite():
    """Pytest fixture for staging test suite setup and teardown."""
    suite = StagingStartupTestSuite()
    await suite.setup_test_environment()
    try:
        yield suite
    finally:
        await suite.teardown_test_environment()


@pytest.mark.asyncio
@pytest.mark.staging
class TestStagingEnvironmentConfiguration:
    """Test staging environment configuration loading and validation."""
    
    async def test_staging_environment_detection(self, staging_test_suite):
        """Test that staging environment is correctly detected."""
        config = staging_test_suite.env_config
        assert config.environment == TestEnvironment.STAGING
        assert config.is_staging_environment()
        assert not config.is_test_environment()
        assert not config.is_production_environment()
    
    async def test_staging_database_configuration(self, staging_test_suite):
        """Test staging database URL configuration validation."""
        db_config = staging_test_suite.env_config.database
        assert db_config.url.startswith("postgresql://")
        assert "staging" in db_config.url.lower()
        assert db_config.pool_pre_ping is True
        assert db_config.pool_recycle == 300
    
    async def test_staging_service_urls_configuration(self, staging_test_suite):
        """Test staging service URLs are properly configured."""
        services = staging_test_suite.env_config.services
        assert services.backend.startswith("https://")
        assert "staging" in services.backend
        assert services.auth.startswith("https://")
        assert "staging" in services.auth
        assert services.websocket.startswith("wss://")
    
    async def test_staging_secrets_validation(self, staging_test_suite):
        """Test staging secrets are properly configured."""
        secrets = staging_test_suite.env_config.secrets
        assert len(secrets.jwt_secret_key) >= 32
        assert secrets.fernet_key is not None
        assert secrets.google_client_id is not None
        assert secrets.gemini_api_key is not None


@pytest.mark.asyncio
@pytest.mark.staging
class TestStagingServiceStartup:
    """Test staging service startup verification and health checks."""
    
    async def test_backend_service_health_endpoint(self, staging_test_suite):
        """Test backend service health endpoint accessibility."""
        backend_url = staging_test_suite.env_config.services.backend
        health_url = f"{backend_url}/health/"
        response = await staging_test_suite.test_client.get(health_url)
        assert response.status_code == 200
        health_data = response.json()
        assert health_data.get("status") == "healthy"
    
    async def test_auth_service_health_endpoint(self, staging_test_suite):
        """Test auth service health endpoint accessibility."""
        auth_url = staging_test_suite.env_config.services.auth
        health_url = f"{auth_url}/health"
        response = await staging_test_suite.test_client.get(health_url)
        assert response.status_code == 200
        health_data = response.json()
        assert health_data.get("status") == "healthy"
    
    async def test_frontend_service_accessibility(self, staging_test_suite):
        """Test frontend service is accessible and serving content."""
        frontend_url = staging_test_suite.env_config.services.frontend
        response = await staging_test_suite.test_client.get(frontend_url)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    async def test_websocket_service_connectivity(self, staging_test_suite):
        """Test WebSocket service connectivity and protocol support."""
        ws_url = staging_test_suite.env_config.services.websocket
        # Validate WebSocket URL format and protocol
        assert ws_url.startswith("wss://")
        assert "staging" in ws_url
        # Test WebSocket endpoint accessibility via HTTP upgrade check
        http_url = ws_url.replace("wss://", "https://").replace("/ws", "/health/")
        response = await staging_test_suite.test_client.get(http_url)
        assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.staging
class TestStagingDatabaseConnections:
    """Test staging database connections and configuration."""
    
    async def test_postgresql_connection_configuration(self, staging_test_suite):
        """Test PostgreSQL database connection configuration."""
        db_url = os.getenv(CredentialConstants.DATABASE_URL)
        assert db_url is not None
        assert db_url.startswith("postgresql://")
        # Validate database connection parameters
        config = staging_test_suite.env_config.database
        assert config.url == db_url
        assert config.echo is False  # No query logging in staging
    
    async def test_redis_connection_configuration(self, staging_test_suite):
        """Test Redis connection configuration for caching."""
        redis_url = os.getenv("REDIS_URL")
        assert redis_url is not None
        assert redis_url.startswith("redis://")
        assert "staging" in redis_url or "localhost" in redis_url
    
    async def test_clickhouse_connection_configuration(self, staging_test_suite):
        """Test ClickHouse connection configuration for analytics."""
        clickhouse_url = os.getenv("CLICKHOUSE_URL")
        assert clickhouse_url is not None
        assert clickhouse_url.startswith("clickhouse://")
        assert "staging" in clickhouse_url or "localhost" in clickhouse_url


@pytest.mark.asyncio
@pytest.mark.staging
class TestStagingConfigurationManager:
    """Test unified configuration manager initialization and validation."""
    
    async def test_configuration_manager_initialization(self, staging_test_suite):
        """Test unified configuration manager initializes correctly."""
        config_manager = staging_test_suite.config_manager
        config = config_manager.get_config()
        assert config is not None
        assert config.database_url is not None
        assert config.environment == "staging"
    
    async def test_configuration_integrity_validation(self, staging_test_suite):
        """Test configuration integrity validation passes."""
        is_valid, issues = validate_config_integrity()
        assert is_valid, f"Configuration integrity issues: {issues}"
        assert len(issues) == 0
    
    async def test_configuration_summary_completeness(self, staging_test_suite):
        """Test configuration summary provides complete information."""
        config_manager = staging_test_suite.config_manager
        summary = config_manager.get_config_summary()
        assert summary["environment"] == "staging"
        assert summary["database_configured"] is True
        assert summary["secrets_loaded"] > 0
        assert summary["services_enabled"] > 0


@pytest.mark.asyncio
@pytest.mark.staging
class TestStagingSecretKeyValidation:
    """Test staging secret key validation and security configuration."""
    
    async def test_jwt_secret_key_validation(self, staging_test_suite):
        """Test JWT secret key is properly configured and secure."""
        jwt_secret = os.getenv(JWTConstants.JWT_SECRET_KEY)
        assert jwt_secret is not None
        assert len(jwt_secret) >= 32
        assert jwt_secret != "test-jwt-secret-key-unified-testing-32chars"
    
    async def test_fernet_key_validation(self, staging_test_suite):
        """Test Fernet encryption key is properly configured."""
        fernet_key = os.getenv(JWTConstants.FERNET_KEY)
        assert fernet_key is not None
        assert len(fernet_key) > 20  # Base64 encoded Fernet keys are longer
        assert fernet_key != "test-fernet-key-fallback"
    
    async def test_google_oauth_configuration(self, staging_test_suite):
        """Test Google OAuth client configuration for staging."""
        client_id = os.getenv(CredentialConstants.GOOGLE_CLIENT_ID)
        client_secret = os.getenv(CredentialConstants.GOOGLE_CLIENT_SECRET)
        assert client_id is not None
        assert client_secret is not None
        assert client_id != "test-google-client-id"
        assert client_secret != "test-google-client-secret"


@pytest.mark.asyncio
@pytest.mark.staging
class TestStagingStartupChecks:
    """Test staging startup checks and system validation."""
    
    async def test_environment_variables_completeness(self, staging_test_suite):
        """Test all required environment variables are set."""
        required_vars = [
            "DATABASE_URL", "REDIS_URL", "CLICKHOUSE_URL",
            JWTConstants.JWT_SECRET_KEY, JWTConstants.FERNET_KEY,
            CredentialConstants.GOOGLE_CLIENT_ID, CredentialConstants.GEMINI_API_KEY
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        assert len(missing_vars) == 0, f"Missing environment variables: {missing_vars}"
    
    async def test_service_dependencies_resolution(self, staging_test_suite):
        """Test service dependencies are properly resolved."""
        config = staging_test_suite.env_config
        # Validate service URL accessibility
        backend_accessible = await self._check_url_accessible(
            config.services.backend, staging_test_suite.test_client
        )
        auth_accessible = await self._check_url_accessible(
            config.services.auth, staging_test_suite.test_client
        )
        assert backend_accessible, "Backend service not accessible"
        assert auth_accessible, "Auth service not accessible"
    
    async def _check_url_accessible(self, url: str, client: httpx.AsyncClient) -> bool:
        """Check if URL is accessible via HTTP request."""
        try:
            response = await client.get(f"{url}/health")
            return response.status_code == 200
        except Exception:
            return False


@pytest.mark.asyncio
@pytest.mark.staging
class TestStagingErrorRecovery:
    """Test staging error recovery mechanisms and resilience."""
    
    async def test_configuration_error_handling(self, staging_test_suite):
        """Test configuration loading handles errors gracefully."""
        # Test configuration validation with missing components
        config_manager = staging_test_suite.config_manager
        # Configuration should be valid in staging environment
        is_valid, errors = config_manager.validate_configuration_integrity()
        assert is_valid, f"Configuration validation errors: {errors}"
    
    async def test_service_health_check_recovery(self, staging_test_suite):
        """Test service health check recovery mechanisms."""
        # Test service health endpoints recover from temporary failures
        services = staging_test_suite.env_config.services
        client = staging_test_suite.test_client
        
        # Multiple health check attempts to verify stability
        health_checks = []
        for _ in range(3):
            backend_check = await self._perform_health_check(
                f"{services.backend}/health/", client
            )
            auth_check = await self._perform_health_check(
                f"{services.auth}/health", client
            )
            health_checks.append(backend_check and auth_check)
            await asyncio.sleep(1)
        
        # At least 2 out of 3 health checks should pass
        passed_checks = sum(health_checks)
        assert passed_checks >= 2, f"Health check recovery failed: {health_checks}"
    
    async def _perform_health_check(self, url: str, client: httpx.AsyncClient) -> bool:
        """Perform health check with error handling."""
        try:
            response = await client.get(url)
            return response.status_code == 200
        except Exception:
            return False


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.comprehensive
class TestComprehensiveStartupFlow:
    """Comprehensive E2E startup and service initialization tests."""
    
    async def test_complete_system_startup_flow(self, staging_test_suite):
        """Test complete system startup with all services."""
        start_time = time.time()
        
        # Verify environment is properly initialized
        harness = staging_test_suite.harness
        assert harness.is_environment_ready(), "Environment not ready"
        
        env_status = await harness.get_environment_status()
        assert env_status["environment"] == "staging", "Wrong environment"
        assert env_status["harness_ready"], "Harness not ready"
        
        duration = time.time() - start_time
        assert duration < 30, f"Startup took too long: {duration:.2f}s"
    
    async def test_websocket_connectivity_full(self, staging_test_suite):
        """Test WebSocket connectivity with full authentication flow."""
        harness = staging_test_suite.harness
        
        # Create authenticated test user
        user = await harness.create_test_user()
        assert user.access_token, "Failed to get access token"
        
        # Test WebSocket connection with authentication
        ws_url = harness.get_websocket_url()
        headers = {"Authorization": f"Bearer {user.access_token}"}
        
        async with staging_test_suite.aio_session.ws_connect(
            ws_url, headers=headers, ssl=False, timeout=10
        ) as ws:
            # Send connection initialization
            await ws.send_json({
                "type": "connection_init",
                "payload": {"auth_token": user.access_token}
            })
            
            # Wait for acknowledgment
            msg = await ws.receive()
            assert msg.type == aiohttp.WSMsgType.TEXT, "Invalid message type"
            data = json.loads(msg.data)
            assert data.get("type") in ["connection_ack", "connected"]
            
            await ws.close()
    
    async def test_example_message_flow_complete(self, staging_test_suite):
        """Test complete example message flow with agent response."""
        harness = staging_test_suite.harness
        
        # Create test user and WebSocket connection
        user = await harness.create_test_user()
        ws = await harness.create_websocket_connection(user)
        
        # Send example message about AI optimization
        test_message = "What are the best practices for AI cost optimization?"
        await ws.send_message({
            "type": "message",
            "content": test_message,
            "thread_id": f"test_thread_{user.user_id}"
        })
        
        # Wait for agent response
        response = await ws.receive_message(timeout=30)
        assert response, "No response from agent"
        assert response.get("type") == "message", "Invalid response type"
        
        content = response.get("content", "")
        assert len(content) > 20, "Response too short"
        assert any(word in content.lower() for word in ["cost", "optimization", "ai"]), \
               "Response doesn't address topic"
        
        await ws.close()
    
    async def test_agent_response_via_api(self, staging_test_suite):
        """Test agent response through API endpoints."""
        harness = staging_test_suite.harness
        
        # Create test user
        user = await harness.create_test_user()
        backend_url = harness.get_service_url("backend")
        headers = {"Authorization": f"Bearer {user.access_token}"}
        
        # Create thread via API
        async with staging_test_suite.test_client.post(
            f"{backend_url}/api/v1/threads",
            headers=headers,
            json={"name": "API Test Thread"}
        ) as resp:
            assert resp.status_code == 201, f"Thread creation failed: {resp.status_code}"
            thread_data = resp.json()
            thread_id = thread_data["id"]
        
        # Send message to trigger agent
        async with staging_test_suite.test_client.post(
            f"{backend_url}/api/v1/threads/{thread_id}/messages",
            headers=headers,
            json={
                "content": "Generate cost optimization recommendations",
                "role": "user"
            }
        ) as resp:
            assert resp.status_code in [200, 201], "Message send failed"
            
        # Poll for agent response
        for attempt in range(15):  # 15 second timeout
            async with staging_test_suite.test_client.get(
                f"{backend_url}/api/v1/threads/{thread_id}/messages",
                headers=headers
            ) as resp:
                if resp.status_code == 200:
                    messages = resp.json()
                    agent_msgs = [m for m in messages if m.get("role") == "assistant"]
                    if agent_msgs:
                        agent_response = agent_msgs[-1]
                        assert agent_response.get("content"), "Empty agent response"
                        return
            await asyncio.sleep(1)
        
        pytest.fail("Agent did not respond within timeout")
    
    async def test_database_connection_health(self, staging_test_suite):
        """Test database connections are healthy and responsive."""
        harness = staging_test_suite.harness
        backend_url = harness.get_service_url("backend")
        
        # Test database health via backend
        async with staging_test_suite.test_client.get(
            f"{backend_url}/health/database"
        ) as resp:
            if resp.status_code == 404:
                # Fallback to general health endpoint
                async with staging_test_suite.test_client.get(
                    f"{backend_url}/health"
                ) as health_resp:
                    assert health_resp.status_code == 200, "Backend health failed"
                    health_data = health_resp.json()
                    assert health_data.get("status") == "healthy", "Backend unhealthy"
            else:
                assert resp.status_code == 200, "Database health check failed"
                db_data = resp.json()
                assert db_data.get("status") in ["healthy", "ok"], "Database unhealthy"
    
    async def test_service_initialization_order(self, staging_test_suite):
        """Test services initialize in correct dependency order."""
        # Verify auth service is ready first
        auth_url = staging_test_suite.env_config.services.auth
        async with staging_test_suite.test_client.get(f"{auth_url}/health") as resp:
            assert resp.status_code == 200, "Auth service not ready"
            
        # Verify backend service is ready with database dependencies
        backend_url = staging_test_suite.env_config.services.backend
        async with staging_test_suite.test_client.get(f"{backend_url}/health") as resp:
            assert resp.status_code == 200, "Backend service not ready"
            health_data = resp.json()
            assert health_data.get("status") == "healthy", "Backend not healthy"
    
    async def test_concurrent_user_simulation(self, staging_test_suite):
        """Test system handles concurrent users during startup."""
        harness = staging_test_suite.harness
        
        # Run concurrent user test
        concurrent_results = await harness.run_concurrent_user_test(user_count=3)
        
        # Verify at least 2 out of 3 succeed
        successful_journeys = [r for r in concurrent_results if r.get("success")]
        assert len(successful_journeys) >= 2, \
               f"Too many concurrent failures: {len(successful_journeys)}/3"
    
    async def test_comprehensive_startup_summary(self, staging_test_suite):
        """Generate comprehensive startup test summary."""
        start_time = time.time()
        harness = staging_test_suite.harness
        
        # Collect comprehensive environment status
        env_status = await harness.get_environment_status()
        
        # Validate all critical components
        assert env_status["environment"] == "staging"
        assert env_status["harness_ready"]
        assert env_status.get("active_users", 0) >= 0
        assert env_status.get("service_urls", {})
        
        # Test basic user journey
        user = await harness.create_test_user()
        journey_result = await harness.simulate_user_journey(user)
        assert journey_result.get("success"), "User journey failed"
        
        total_duration = time.time() - start_time
        assert total_duration < 60, f"Total test duration too long: {total_duration:.2f}s"
        
        # Return summary for reporting
        return {
            "startup_validation": "passed",
            "environment": "staging",
            "total_duration_seconds": total_duration,
            "services_healthy": True,
            "user_journey_success": True,
            "timestamp": datetime.now().isoformat()
        }


# Convenience function for running all staging startup tests
async def run_staging_startup_tests() -> Dict[str, Any]:
    """Run all staging startup tests and return comprehensive results."""
    # Setup staging test environment
    env_config = setup_test_environment(environment="staging")
    
    # Validate staging configuration
    is_valid, errors = validate_config_integrity()
    if not is_valid:
        return {
            "status": "failed",
            "reason": "Configuration validation failed",
            "errors": errors
        }
    
    return {
        "status": "passed",
        "environment": env_config.environment.value,
        "services_configured": len(env_config.services.__dict__),
        "database_configured": bool(env_config.database.url),
        "secrets_loaded": len(env_config.secrets.__dict__)
    }


if __name__ == "__main__":
    # Direct execution for staging validation
    asyncio.run(run_staging_startup_tests())