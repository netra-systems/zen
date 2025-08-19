"""
E2E Agent Startup Tests - Phase 1 Implementation

Implements the first two critical agent startup E2E tests using REAL services only.
NO MOCKS - Complete validation from zero state to meaningful agent response.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - 100% customer impact
- Business Goal: Protect 100% agent functionality - Core revenue protection  
- Value Impact: Prevents complete system failures blocking all user interactions
- Revenue Impact: Protects entire $200K+ MRR by ensuring reliable agent startup

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
import os
from typing import Dict, Any, Optional, List
import pytest
from contextlib import asynccontextmanager

# Test infrastructure  
from .real_services_manager import create_real_services_manager
from .real_http_client import RealHTTPClient
from .real_websocket_client import RealWebSocketClient
from .real_client_types import create_test_config, ClientConfig
from .config import TEST_CONFIG, TestTier, get_test_user, TestDataFactory


class AgentStartupE2EManager:
    """Manages E2E agent startup test execution with real services."""
    
    def __init__(self, test_name: str = "agent_startup_e2e"):
        """Initialize E2E manager with real services."""
        self.test_name = test_name
        self.services_manager = create_real_services_manager()
        self.http_client: Optional[RealHTTPClient] = None
        self.ws_client: Optional[RealWebSocketClient] = None
        self.test_user = get_test_user(TestTier.EARLY.value)
        self.auth_token: Optional[str] = None
    
    async def setup_real_services(self) -> None:
        """Start all real services for testing."""
        await self.services_manager.start_all_services()
        await self._validate_services_healthy()
        self.http_client = RealHTTPClient("http://localhost:8081", create_test_config())
        await self._setup_websocket_client()
    
    async def _validate_services_healthy(self) -> None:
        """Validate all services are healthy."""
        if not self.services_manager.is_all_ready():
            raise RuntimeError("Services not healthy")
    
    async def _setup_websocket_client(self) -> None:
        """Setup WebSocket client for agent communication."""
        ws_url = "ws://localhost:8000/ws"
        config = create_test_config(timeout=30.0)
        self.ws_client = RealWebSocketClient(ws_url, config)
    
    async def authenticate_test_user(self) -> str:
        """Authenticate test user and get JWT token."""
        login_data = self._create_login_payload()
        response = await self.http_client.post("/auth/login", login_data)
        token = response.get("access_token")
        if not token:
            raise RuntimeError("Authentication failed")
        self.auth_token = token
        return token
    
    def _create_login_payload(self) -> Dict[str, str]:
        """Create login payload for test user."""
        return {
            "username": self.test_user.email,
            "password": "testpass123"
        }
    
    async def connect_websocket_with_token(self, token: str) -> bool:
        """Connect WebSocket with JWT authentication."""
        headers = TestDataFactory.create_websocket_auth(token)
        return await self.ws_client.connect(headers)
    
    async def send_agent_message(self, content: str) -> Dict[str, Any]:
        """Send message to agent system and get response."""
        message = self._create_agent_message(content)
        response = await self.ws_client.send_and_wait(message, timeout=10.0)
        if not response:
            raise RuntimeError("No agent response received")
        return response
    
    def _create_agent_message(self, content: str) -> Dict[str, Any]:
        """Create agent message payload."""
        return {
            "type": "chat_message",
            "content": content,
            "timestamp": time.time(),
            "user_id": self.test_user.id
        }


class AgentStartupValidator:
    """Validates agent startup test results and performance."""
    
    def __init__(self):
        """Initialize validation metrics."""
        self.start_time: Optional[float] = None
        self.validation_errors: List[str] = []
    
    def start_timing(self) -> None:
        """Start performance timing."""
        self.start_time = time.time()
    
    def validate_response_time(self, max_seconds: float = 5.0) -> None:
        """Validate response received within time limit."""
        if self.start_time is None:
            raise ValueError("Timing not started")
        duration = time.time() - self.start_time
        if duration > max_seconds:
            self._add_error(f"Response took {duration:.2f}s, max {max_seconds}s")
    
    def validate_agent_initialization(self, response: Dict[str, Any]) -> None:
        """Validate agent system initialized correctly."""
        required_fields = ["type", "content", "agent_metadata"]
        for field in required_fields:
            if field not in response:
                self._add_error(f"Response missing required field: {field}")
    
    def validate_meaningful_response(self, response: Dict[str, Any]) -> None:
        """Validate response contains meaningful content."""
        content = response.get("content", "")
        if len(content) < 10:
            self._add_error("Response too short to be meaningful")
        
        error_keywords = ["error", "failed", "exception", "timeout"]
        if any(keyword in content.lower() for keyword in error_keywords):
            self._add_error("Response contains error indicators")
    
    def validate_llm_provider_active(self, response: Dict[str, Any]) -> None:
        """Validate LLM provider is active and responding."""
        metadata = response.get("agent_metadata", {})
        provider = metadata.get("llm_provider")
        if not provider:
            self._add_error("No LLM provider information in response")
        
        if metadata.get("provider_status") != "active":
            self._add_error("LLM provider not in active state")
    
    def _add_error(self, error: str) -> None:
        """Add validation error to list."""
        self.validation_errors.append(error)
    
    def assert_all_valid(self) -> None:
        """Assert all validations passed."""
        if self.validation_errors:
            errors = "; ".join(self.validation_errors)
            raise AssertionError(f"Validation failures: {errors}")


class LLMProviderTestHelper:
    """Helper for testing LLM provider initialization and fallback."""
    
    def __init__(self, manager: AgentStartupE2EManager):
        """Initialize with test manager."""
        self.manager = manager
        self.primary_provider = os.getenv("PRIMARY_LLM_PROVIDER", "openai")
        self.fallback_provider = os.getenv("FALLBACK_LLM_PROVIDER", "anthropic")
    
    async def test_primary_provider_initialization(self) -> Dict[str, Any]:
        """Test primary LLM provider initialization."""
        message = "Test primary provider initialization"
        response = await self.manager.send_agent_message(message)
        self._validate_provider_response(response, self.primary_provider)
        return response
    
    async def simulate_provider_failure(self) -> None:
        """Simulate primary provider failure."""
        # This would typically involve setting environment variables
        # or sending specific test commands to trigger provider failure
        os.environ["FORCE_PRIMARY_PROVIDER_FAILURE"] = "true"
    
    async def test_fallback_provider(self) -> Dict[str, Any]:
        """Test fallback to secondary provider."""
        await self.simulate_provider_failure()
        message = "Test fallback provider after primary failure"
        response = await self.manager.send_agent_message(message)
        self._validate_fallback_response(response)
        return response
    
    def _validate_provider_response(self, response: Dict[str, Any], 
                                  expected_provider: str) -> None:
        """Validate response came from expected provider."""
        metadata = response.get("agent_metadata", {})
        actual_provider = metadata.get("llm_provider")
        if actual_provider != expected_provider:
            raise AssertionError(f"Expected {expected_provider}, got {actual_provider}")
    
    def _validate_fallback_response(self, response: Dict[str, Any]) -> None:
        """Validate fallback provider response."""
        metadata = response.get("agent_metadata", {})
        if metadata.get("fallback_activated") is not True:
            raise AssertionError("Fallback mechanism not activated")


@pytest.mark.asyncio
@pytest.mark.integration  
@pytest.mark.real_services
async def test_complete_cold_start_to_first_meaningful_response():
    """
    Test 1: Complete cold start to first meaningful response.
    
    Validates complete flow from zero state through agent initialization
    to meaningful response within 5 seconds.
    
    Success Criteria: <5 seconds, meaningful response with actual content
    """
    manager = AgentStartupE2EManager("cold_start_meaningful")
    validator = AgentStartupValidator()
    
    try:
        await _execute_cold_start_test(manager, validator)
    finally:
        await _cleanup_test_resources(manager)


async def _execute_cold_start_test(manager: AgentStartupE2EManager, 
                                 validator: AgentStartupValidator) -> None:
    """Execute complete cold start test flow."""
    validator.start_timing()
    await manager.setup_real_services()
    token = await manager.authenticate_test_user()
    connected = await manager.connect_websocket_with_token(token)
    assert connected, "WebSocket connection failed"
    
    await _send_test_message_and_validate(manager, validator)


async def _send_test_message_and_validate(manager: AgentStartupE2EManager,
                                        validator: AgentStartupValidator) -> None:
    """Send test message and validate response."""
    test_message = "Hello, can you help me optimize my AI infrastructure costs?"
    response = await manager.send_agent_message(test_message)
    
    validator.validate_agent_initialization(response)
    validator.validate_meaningful_response(response)
    validator.validate_response_time(max_seconds=5.0)
    validator.assert_all_valid()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.real_services
async def test_agent_llm_provider_initialization_and_fallback():
    """
    Test 2: Agent LLM provider initialization and fallback.
    
    Validates real LLM provider initialization and automatic fallback
    to secondary provider on failure.
    
    Success Criteria: Seamless failover, no message loss
    """
    manager = AgentStartupE2EManager("llm_provider_fallback")
    validator = AgentStartupValidator()
    
    try:
        await _execute_llm_provider_test(manager, validator)
    finally:
        await _cleanup_test_resources(manager)


async def _execute_llm_provider_test(manager: AgentStartupE2EManager,
                                   validator: AgentStartupValidator) -> None:
    """Execute LLM provider initialization and fallback test."""
    await manager.setup_real_services()
    token = await manager.authenticate_test_user()
    connected = await manager.connect_websocket_with_token(token)
    assert connected, "WebSocket connection failed"
    
    await _test_provider_initialization_and_fallback(manager, validator)


async def _test_provider_initialization_and_fallback(manager: AgentStartupE2EManager,
                                                   validator: AgentStartupValidator) -> None:
    """Test provider initialization and fallback mechanisms."""
    helper = LLMProviderTestHelper(manager)
    
    # Test primary provider
    validator.start_timing()
    primary_response = await helper.test_primary_provider_initialization()
    validator.validate_llm_provider_active(primary_response)
    
    # Test fallback provider
    fallback_response = await helper.test_fallback_provider()
    validator.validate_meaningful_response(fallback_response)
    validator.validate_response_time(max_seconds=8.0)
    validator.assert_all_valid()


async def _cleanup_test_resources(manager: AgentStartupE2EManager) -> None:
    """Clean up all test resources."""
    if manager.ws_client:
        await manager.ws_client.close()
    if manager.http_client:
        await manager.http_client.close()
    await manager.services_manager.stop_all_services()


# Additional helper function for test runner integration
def get_startup_test_names() -> List[str]:
    """Get list of startup test names for test runner."""
    return [
        "test_complete_cold_start_to_first_meaningful_response",
        "test_agent_llm_provider_initialization_and_fallback"
    ]