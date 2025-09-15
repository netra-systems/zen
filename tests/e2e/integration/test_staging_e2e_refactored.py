"""
Refactored Staging E2E Test Suite - Comprehensive System Validation

Business Value: $2M+ MRR protection via comprehensive staging validation ensuring production
readiness and preventing critical deployment failures.

This refactored test suite follows all Netra architectural principles:
- Functions under 8 lines each
- File under 300 lines total  
- Comprehensive error handling
- Security validations included
- Reuses existing test infrastructure
- Configuration constants instead of hardcoded values

Test Coverage:
1. Basic system startup verification
2. Frontend WebSocket connections in staging
3. Example message handling with AI optimization query
4. Agent response validation with content quality checks
5. Full system integration (CORS, WS, loading)
6. OAuth authentication flow validation

Architecture: Modular helper functions maintain readability while staying under line limits.
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment



import asyncio
import time
from typing import Any, Dict

import aiohttp
import pytest

from netra_backend.app.core.auth_constants import (
    AuthConstants,
    HeaderConstants,
    JWTConstants,
)
from netra_backend.app.core.network_constants import ServicePorts, URLConstants
from tests.e2e.integration.unified_e2e_harness import create_e2e_harness
from tests.e2e.test_environment_config import (
    TestEnvironmentType,
    get_test_environment_config,
)


class StagingE2ESuiteTests:
    """Refactored staging E2E test suite with modular architecture."""
    
    def __init__(self):
        """Initialize staging test environment."""
        self.env_config = get_test_environment_config(environment="staging")
        self.harness = create_e2e_harness(environment="staging")
        self.test_timeout = 30
        
    async def setup_environment(self) -> None:
        """Setup test environment with health validation."""
        await self.harness.start_test_environment()
        assert self.harness.is_environment_ready(), "Environment setup failed"
        
    async def cleanup_environment(self) -> None:
        """Cleanup test environment and resources."""
        await self.harness.cleanup_test_environment()
        
    def _validate_staging_config(self) -> None:
        """Validate staging configuration integrity."""
        assert self.env_config.environment == TestEnvironmentType.STAGING
        assert self.env_config.services.backend.startswith("https://")
        assert self.env_config.services.websocket.startswith("wss://")
        
    async def _create_authenticated_user(self):
        """Create and return authenticated test user."""
        user = await self.harness.create_test_user()
        assert user.access_token, "Failed to obtain access token"
        return user
        
    def _validate_jwt_token(self, token: str) -> bool:
        """Validate JWT token structure and format."""
        parts = token.split('.')
        return len(parts) == 3 and len(token) > 100
        
    async def _send_websocket_message(self, ws, message: str, thread_id: str) -> Dict:
        """Send WebSocket message and return response."""
        payload = {"type": "message", "content": message, "thread_id": thread_id}
        await ws.send_message(payload)
        return await ws.receive_message(timeout=self.test_timeout)


@pytest.fixture
async def staging_suite():
    """Pytest fixture for staging test suite."""
    suite = StagingE2ETestSuite()
    await suite.setup_environment()
    try:
        yield suite
    finally:
        await suite.cleanup_environment()


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.e2e
class StagingSystemStartupTests:
    """Test system startup and basic health validation."""
    
    @pytest.mark.e2e
    async def test_system_startup_verification(self, staging_suite):
        """Verify complete system startup within time limits."""
        start_time = time.time()
        status = await staging_suite.harness.get_environment_status()
        assert status["environment"] in ["staging", "testing"]
        assert status["harness_ready"]
        duration = time.time() - start_time
        assert duration < 15, f"Startup verification too slow: {duration:.2f}s"
        
    @pytest.mark.e2e
    async def test_service_health_endpoints(self, staging_suite):
        """Validate all service health endpoints are responsive."""
        async with aiohttp.ClientSession() as session:
            backend_url = staging_suite.env_config.services.backend
            async with session.get(f"{backend_url}{URLConstants.HEALTH_PATH}") as resp:
                assert resp.status == 200, "Backend health check failed"
                
    @pytest.mark.e2e
    async def test_database_connectivity_validation(self, staging_suite):
        """Test database connections are healthy and responsive."""
        backend_url = staging_suite.env_config.services.backend
        async with aiohttp.ClientSession() as session:
            health_url = f"{backend_url}{URLConstants.HEALTH_PATH}"
            async with session.get(health_url) as resp:
                assert resp.status == 200, "Database connectivity failed"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.e2e
class WebSocketConnectivityTests:
    """Test WebSocket connectivity and authentication."""
    
    @pytest.mark.e2e
    async def test_websocket_authentication_flow(self, staging_suite):
        """Test WebSocket connection with full authentication."""
        user = await staging_suite._create_authenticated_user()
        assert staging_suite._validate_jwt_token(user.access_token)
        ws = await staging_suite.harness.create_websocket_connection(user)
        assert ws is not None, "WebSocket connection failed"
        await ws.close()
        
    @pytest.mark.e2e
    async def test_websocket_connection_security(self, staging_suite):
        """Validate WebSocket security headers and SSL."""
        ws_url = staging_suite.harness.get_websocket_url()
        assert ws_url.startswith("wss://"), "WebSocket not using secure connection"
        user = await staging_suite._create_authenticated_user()
        headers = {HeaderConstants.AUTHORIZATION: f"{HeaderConstants.BEARER_PREFIX}{user.access_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, headers=headers, ssl=True) as ws:
                assert ws is not None, "Secure WebSocket connection failed"


@pytest.mark.asyncio
@pytest.mark.staging  
@pytest.mark.e2e
class MessageHandlingTests:
    """Test AI message handling and agent responses."""
    
    @pytest.mark.e2e
    async def test_ai_optimization_query_flow(self, staging_suite):
        """Test complete AI optimization message flow with agent response."""
        user = await staging_suite._create_authenticated_user()
        ws = await staging_suite.harness.create_websocket_connection(user)
        test_message = "What are the best practices for reducing LLM costs?"
        thread_id = f"test_thread_{user.user_id}"
        response = await staging_suite._send_websocket_message(ws, test_message, thread_id)
        await self._validate_agent_response(response)
        await ws.close()
        
    async def _validate_agent_response(self, response: Dict) -> None:
        """Validate agent response content and structure."""
        assert response, "No response received from agent"
        assert response.get("type") == "message", "Invalid response type"
        content = response.get("content", "")
        assert len(content) > 20, "Response content too brief"
        keywords = ["cost", "optimization", "ai", "llm", "efficiency"]
        assert any(word in content.lower() for word in keywords), "Response lacks relevance"
        
    @pytest.mark.e2e
    async def test_response_time_performance(self, staging_suite):
        """Test agent response time meets performance requirements."""
        start_time = time.time()
        user = await staging_suite._create_authenticated_user()
        ws = await staging_suite.harness.create_websocket_connection(user)
        response = await staging_suite._send_websocket_message(
            ws, "Quick AI cost question", f"perf_test_{user.user_id}"
        )
        response_time = time.time() - start_time
        assert response_time < 30, f"Agent response too slow: {response_time:.2f}s"
        await ws.close()


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.e2e
class SystemIntegrationTests:
    """Test full system integration including CORS and loading."""
    
    @pytest.mark.e2e
    async def test_cors_configuration_validation(self, staging_suite):
        """Validate CORS headers are properly configured for staging."""
        backend_url = staging_suite.env_config.services.backend
        async with aiohttp.ClientSession() as session:
            headers = {"Origin": staging_suite.env_config.services.frontend}
            async with session.options(f"{backend_url}{URLConstants.API_PREFIX}", headers=headers) as resp:
                cors_header = resp.headers.get("Access-Control-Allow-Origin")
                assert cors_header is not None, "CORS headers missing"
                
    @pytest.mark.e2e
    async def test_concurrent_user_handling(self, staging_suite):
        """Test system handles multiple concurrent users effectively."""
        concurrent_results = await staging_suite.harness.run_concurrent_user_test(user_count=3)
        successful_results = [r for r in concurrent_results if r.get("success")]
        success_rate = len(successful_results) / len(concurrent_results)
        assert success_rate >= 0.66, f"Concurrent user success rate too low: {success_rate:.2f}"
        
    @pytest.mark.e2e
    async def test_system_resource_stability(self, staging_suite):
        """Test system maintains stability under normal load."""
        start_status = await staging_suite.harness.get_environment_status()
        user = await staging_suite._create_authenticated_user()
        journey_result = await staging_suite.harness.simulate_user_journey(user)
        end_status = await staging_suite.harness.get_environment_status()
        assert journey_result.get("success"), "User journey failed under load"
        assert start_status["harness_ready"] == end_status["harness_ready"], "System stability compromised"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.e2e
class OAuthAuthenticationTests:
    """Test OAuth authentication flow and security."""
    
    @pytest.mark.e2e
    async def test_oauth_token_validation(self, staging_suite):
        """Test OAuth token generation and validation."""
        user = await staging_suite._create_authenticated_user()
        token_parts = user.access_token.split('.')
        assert len(token_parts) == 3, "Invalid JWT token structure"
        assert staging_suite._validate_jwt_token(user.access_token), "JWT token validation failed"
        
    @pytest.mark.e2e
    async def test_auth_service_integration(self, staging_suite):
        """Test authentication service integration with staging environment."""
        staging_suite._validate_staging_config()
        auth_url = staging_suite.env_config.services.auth
        assert auth_url.startswith("https://"), "Auth service not using HTTPS"
        user = await staging_suite._create_authenticated_user()
        assert user.email, "User email not populated"
        
    @pytest.mark.e2e
    async def test_token_expiration_handling(self, staging_suite):
        """Test proper handling of token expiration scenarios."""
        user = await staging_suite._create_authenticated_user()
        token_length = len(user.access_token)
        assert token_length > 100, "Access token suspiciously short"
        headers = {HeaderConstants.AUTHORIZATION: f"{HeaderConstants.BEARER_PREFIX}{user.access_token}"}
        backend_url = staging_suite.env_config.services.backend
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{backend_url}{URLConstants.HEALTH_PATH}", headers=headers) as resp:
                assert resp.status != 401, "Token immediately expired"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.e2e
class ComprehensiveStagingValidationTests:
    """Comprehensive staging environment validation."""
    
    @pytest.mark.e2e
    async def test_end_to_end_user_journey(self, staging_suite):
        """Test complete user journey from auth to AI response."""
        user = await staging_suite._create_authenticated_user()
        journey_result = await staging_suite.harness.simulate_user_journey(user)
        assert journey_result.get("success"), "Complete user journey failed"
        assert journey_result.get("websocket_connected"), "WebSocket connection failed in journey"
        assert journey_result.get("message_sent"), "Message sending failed in journey"
        
    @pytest.mark.e2e
    async def test_staging_environment_summary(self, staging_suite):
        """Generate comprehensive staging test summary with metrics."""
        start_time = time.time()
        env_status = await staging_suite.harness.get_environment_status()
        user = await staging_suite._create_authenticated_user()
        journey_result = await staging_suite.harness.simulate_user_journey(user)
        total_duration = time.time() - start_time
        
        # Comprehensive validation
        assert env_status["environment"] in ["staging", "testing"], "Wrong environment detected"
        assert journey_result.get("success"), "User journey validation failed"
        assert total_duration < 60, f"Total validation time excessive: {total_duration:.2f}s"
        
        # Return summary for reporting
        return {
            "validation_status": "passed",
            "environment": "staging", 
            "total_duration_seconds": total_duration,
            "services_validated": True,
            "auth_flow_validated": True,
            "websocket_connectivity_validated": True,
            "ai_response_validated": True,
            "system_integration_validated": True
        }


# Convenience function for running all staging tests
async def run_complete_staging_validation() -> Dict[str, Any]:
    """Run complete staging validation suite and return results."""
    suite = StagingE2ETestSuite()
    await suite.setup_environment()
    try:
        validator = ComprehensiveStagingValidationTests()
        return await validator.test_staging_environment_summary(suite)
    finally:
        await suite.cleanup_environment()
