"""
Agent Cold Start Test - Complete System Initialization Test

Tests complete system cold start from zero state through first meaningful agent interaction.
This is the ultimate end-to-end test protecting 100% of agent functionality.

Business Value Justification (BVJ):
1. Segment: ALL customer segments (Free, Early, Mid, Enterprise)
2. Business Goal: Protect 100% of agent functionality - CRITICAL revenue protection
3. Value Impact: Prevents system initialization failures that block all user interactions
4. Revenue Impact: Protects entire $200K+ MRR by ensuring reliable cold start process

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- NO MOCKS - Real services only
- Real Auth service with JWT validation
- Real WebSocket connections
- Real agent initialization flows
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional
import pytest
from contextlib import asynccontextmanager

# Test infrastructure
from .config import TEST_CONFIG, TestTier, get_test_user
from .harness_complete import (
    UnifiedTestHarnessComplete, TestHarnessContext,
    get_auth_service_url, get_backend_service_url
)
from .test_harness import UnifiedTestHarness

# HTTP client for API calls
import httpx

# WebSocket client for real connections  
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException


class ColdStartTestManager:
    """Manages cold start test execution and validation."""
    
    def __init__(self):
        """Initialize cold start test manager."""
        self.harness: Optional[UnifiedTestHarnessComplete] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.ws_connection = None
        self.test_user = get_test_user(TestTier.EARLY.value)
        self.auth_token: Optional[str] = None
    
    async def setup_http_client(self) -> None:
        """Setup HTTP client for API requests."""
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True
        )
    
    async def cleanup_http_client(self) -> None:
        """Cleanup HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
    
    async def authenticate_user(self) -> str:
        """Authenticate user with real Auth service and get JWT token."""
        auth_url = f"{get_auth_service_url()}/auth/login"
        login_data = self._get_login_data()
        response = await self.http_client.post(auth_url, json=login_data)
        self._validate_auth_response(response)
        return response.json()["access_token"]
    
    def _get_login_data(self) -> Dict[str, str]:
        """Get login data for authentication."""
        return {
            "username": self.test_user.email,
            "password": "testpass123"
        }
    
    def _validate_auth_response(self, response) -> None:
        """Validate authentication response."""
        assert response.status_code == 200, f"Auth failed: {response.status_code}"
    
    async def connect_websocket(self, token: str) -> None:
        """Connect WebSocket with JWT token."""
        ws_url = f"ws://localhost:8000/ws?token={token}"
        self.ws_connection = await websockets.connect(
            ws_url,
            extra_headers={"Authorization": f"Bearer {token}"}
        )
    
    async def send_first_message(self, content: str) -> Dict[str, Any]:
        """Send first message to agent system."""
        message = self._create_chat_message(content)
        await self.ws_connection.send(json.dumps(message))
        response = await self.ws_connection.recv()
        return json.loads(response)
    
    def _create_chat_message(self, content: str) -> Dict[str, Any]:
        """Create chat message payload."""
        return {
            "type": "chat_message",
            "content": content,
            "timestamp": time.time()
        }
    
    async def validate_agent_response(self, response: Dict[str, Any]) -> None:
        """Validate agent response contains expected components."""
        assert "type" in response, "Response missing type field"
        assert "content" in response, "Response missing content field"
        assert len(response["content"]) > 0, "Response content is empty"


class ColdStartTestValidator:
    """Validates cold start test results and performance."""
    
    def __init__(self, manager: ColdStartTestManager):
        """Initialize validator with test manager."""
        self.manager = manager
        self.start_time: Optional[float] = None
    
    def start_performance_timer(self) -> None:
        """Start performance measurement."""
        self.start_time = time.time()
    
    def validate_performance(self, max_seconds: float = 5.0) -> None:
        """Validate response time meets requirements."""
        assert self.start_time is not None, "Performance timer not started"
        duration = time.time() - self.start_time
        assert duration < max_seconds, f"Cold start took {duration:.2f}s, max {max_seconds}s"
    
    def validate_supervisor_initialization(self, response: Dict[str, Any]) -> None:
        """Validate SupervisorAgent initialized correctly."""
        # Check for supervisor agent indicators in response
        content = response.get("content", "").lower()
        assert "supervisor" in content or "agent" in content, "No supervisor indication"
    
    def validate_triage_routing(self, response: Dict[str, Any]) -> None:
        """Validate TriageSubAgent routing worked correctly.""" 
        # Check for triage routing indicators
        assert response.get("agent_type") == "triage" or "triage" in response.get("metadata", {}), "Triage routing failed"
    
    def validate_meaningful_response(self, response: Dict[str, Any]) -> None:
        """Validate response is meaningful and not error."""
        content = response.get("content", "")
        assert len(content) >= 10, "Response too short to be meaningful"
        error_indicators = ["error", "failed", "exception", "timeout"]
        assert not any(indicator in content.lower() for indicator in error_indicators), "Response indicates error"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.real_services
async def test_complete_agent_cold_start():
    """
    Complete agent cold start test - the ultimate system validation.
    Tests complete flow from zero state to meaningful agent response < 5 seconds.
    """
    manager = ColdStartTestManager()
    validator = ColdStartTestValidator(manager)
    await _execute_cold_start_test(manager, validator)


async def _execute_cold_start_test(manager: ColdStartTestManager, validator: ColdStartTestValidator) -> None:
    """Execute the complete cold start test flow."""
    try:
        validator.start_performance_timer()
        await _run_test_phases(manager, validator)
    finally:
        await _cleanup_test_resources(manager)


async def _run_test_phases(manager: ColdStartTestManager, validator: ColdStartTestValidator) -> None:
    """Run all test phases within harness context."""
    async with TestHarnessContext("cold_start_test", seed_data=True) as harness:
        manager.harness = harness
        await _execute_authentication_phase(manager, validator)


async def _execute_authentication_phase(manager: ColdStartTestManager, validator: ColdStartTestValidator) -> None:
    """Execute authentication and WebSocket connection phases."""
    await manager.setup_http_client()
    await _wait_for_auth_service_ready(manager)
    token = await manager.authenticate_user()
    await _execute_websocket_phase(manager, validator, token)


async def _execute_websocket_phase(manager: ColdStartTestManager, validator: ColdStartTestValidator, token: str) -> None:
    """Execute WebSocket connection and agent interaction phases."""
    await _wait_for_backend_service_ready(manager)
    await manager.connect_websocket(token)
    response = await manager.send_first_message("Hello, can you help me optimize my AI costs?")
    await _validate_all_components(manager, validator, response)


async def _validate_all_components(manager: ColdStartTestManager, validator: ColdStartTestValidator, response: Dict[str, Any]) -> None:
    """Validate all test components and performance."""
    await manager.validate_agent_response(response)
    validator.validate_supervisor_initialization(response)
    validator.validate_triage_routing(response)
    validator.validate_meaningful_response(response)
    validator.validate_performance(max_seconds=5.0)


async def _cleanup_test_resources(manager: ColdStartTestManager) -> None:
    """Cleanup test resources."""
    if manager.ws_connection:
        await manager.ws_connection.close()
    await manager.cleanup_http_client()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cold_start_with_different_user_tiers():
    """Test cold start works for all customer tiers."""
    tiers_to_test = [TestTier.FREE, TestTier.EARLY, TestTier.MID, TestTier.ENTERPRISE]
    
    for tier in tiers_to_test:
        await _test_tier_cold_start(tier)


async def _test_tier_cold_start(tier: TestTier) -> None:
    """Test cold start for specific customer tier."""
    manager = ColdStartTestManager()
    manager.test_user = get_test_user(tier.value)
    validator = ColdStartTestValidator(manager)
    await _execute_tier_test(manager, validator, tier)


async def _execute_tier_test(manager: ColdStartTestManager, validator: ColdStartTestValidator, tier: TestTier) -> None:
    """Execute tier-specific cold start test."""
    try:
        validator.start_performance_timer()
        await _run_tier_test_flow(manager, validator, tier)
    finally:
        await _cleanup_test_resources(manager)


async def _run_tier_test_flow(manager: ColdStartTestManager, validator: ColdStartTestValidator, tier: TestTier) -> None:
    """Run the tier test flow."""
    async with TestHarnessContext(f"cold_start_{tier.value}") as harness:
        manager.harness = harness
        await _execute_tier_phases(manager, validator, tier)


async def _execute_tier_phases(manager: ColdStartTestManager, validator: ColdStartTestValidator, tier: TestTier) -> None:
    """Execute tier test phases."""
    await manager.setup_http_client()
    await _wait_for_auth_service_ready(manager)
    token = await manager.authenticate_user()
    await _finish_tier_test(manager, validator, tier, token)


async def _finish_tier_test(manager: ColdStartTestManager, validator: ColdStartTestValidator, tier: TestTier, token: str) -> None:
    """Finish tier test execution."""
    await _wait_for_backend_service_ready(manager)
    await manager.connect_websocket(token)
    response = await manager.send_first_message(f"Test message for {tier.value} user")
    await manager.validate_agent_response(response)
    validator.validate_performance(max_seconds=6.0)


async def _wait_for_auth_service_ready(manager: ColdStartTestManager) -> None:
    """Wait for Auth service to be ready."""
    max_attempts = 30
    for attempt in range(max_attempts):
        if await _check_auth_service_health(manager):
            return
        await asyncio.sleep(1)
    raise RuntimeError("Auth service not ready after 30 seconds")


async def _check_auth_service_health(manager: ColdStartTestManager) -> bool:
    """Check if auth service is healthy."""
    try:
        response = await manager.http_client.get(f"{get_auth_service_url()}/health")
        return response.status_code == 200
    except Exception:
        return False


async def _wait_for_backend_service_ready(manager: ColdStartTestManager) -> None:
    """Wait for Backend service to be ready."""
    max_attempts = 30
    for attempt in range(max_attempts):
        if await _check_backend_service_health(manager):
            return
        await asyncio.sleep(1)
    raise RuntimeError("Backend service not ready after 30 seconds")


async def _check_backend_service_health(manager: ColdStartTestManager) -> bool:
    """Check if backend service is healthy."""
    try:
        response = await manager.http_client.get(f"{get_backend_service_url()}/health")
        return response.status_code == 200
    except Exception:
        return False


@pytest.mark.asyncio
@pytest.mark.stress
async def test_concurrent_cold_starts():
    """Test multiple concurrent cold start scenarios."""
    concurrent_users = 3
    tasks = [_run_concurrent_cold_start(f"concurrent_user_{i}") for i in range(concurrent_users)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    _validate_concurrent_results(results)


def _validate_concurrent_results(results: list) -> None:
    """Validate all concurrent tests passed."""
    for i, result in enumerate(results):
        assert not isinstance(result, Exception), f"Concurrent test {i} failed: {result}"
        

async def _run_concurrent_cold_start(user_suffix: str) -> Dict[str, Any]:
    """Run single concurrent cold start test."""
    manager = ColdStartTestManager()
    validator = ColdStartTestValidator(manager)
    return await _execute_concurrent_test(manager, validator, user_suffix)


async def _execute_concurrent_test(manager: ColdStartTestManager, validator: ColdStartTestValidator, user_suffix: str) -> Dict[str, Any]:
    """Execute concurrent test flow."""
    try:
        validator.start_performance_timer()
        return await _run_concurrent_test_flow(manager, validator, user_suffix)
    finally:
        await _cleanup_test_resources(manager)


async def _run_concurrent_test_flow(manager: ColdStartTestManager, validator: ColdStartTestValidator, user_suffix: str) -> Dict[str, Any]:
    """Run concurrent test flow within harness context."""
    async with TestHarnessContext(f"concurrent_{user_suffix}") as harness:
        manager.harness = harness
        return await _execute_concurrent_phases(manager, validator, user_suffix)


async def _execute_concurrent_phases(manager: ColdStartTestManager, validator: ColdStartTestValidator, user_suffix: str) -> Dict[str, Any]:
    """Execute concurrent test phases."""
    await manager.setup_http_client()
    await _wait_for_auth_service_ready(manager)
    token = await manager.authenticate_user()
    return await _finish_concurrent_test(manager, validator, user_suffix, token)


async def _finish_concurrent_test(manager: ColdStartTestManager, validator: ColdStartTestValidator, user_suffix: str, token: str) -> Dict[str, Any]:
    """Finish concurrent test execution."""
    await _wait_for_backend_service_ready(manager)
    await manager.connect_websocket(token)
    response = await manager.send_first_message(f"Concurrent test from {user_suffix}")
    await manager.validate_agent_response(response)
    validator.validate_performance(max_seconds=8.0)
    return {"status": "success", "user": user_suffix, "response": response}