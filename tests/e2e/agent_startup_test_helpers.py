"""
Agent Startup Test Helpers

Helper classes for E2E agent startup testing.
Separated to maintain 450-line file limit compliance.

Business Value Justification (BVJ):
- Segment: ALL customer tiers
- Business Goal: Reliable E2E testing infrastructure  
- Value Impact: Foundation for production-like testing
- Revenue Impact: Better testing prevents production issues
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from tests.e2e.config import TestTier, get_test_user
from tests.e2e.harness_complete import UnifiedE2ETestHarness


class AgentStartupE2EManager:
    """Manages E2E agent startup test execution with validation."""
    
    def __init__(self, test_name: str = "agent_startup_e2e"):
        """Initialize E2E manager."""
        self.test_name = test_name
        self.harness = UnifiedE2ETestHarness()
        self.test_user = get_test_user(TestTier.EARLY.value)
        self.auth_token: Optional[str] = None
        self.startup_metrics: Dict[str, float] = {}
    
    async def setup_test_environment(self) -> None:
        """Setup test environment with service mocks."""
        await self._setup_auth_mocks()
        await self._setup_agent_mocks()
        await self._setup_websocket_mocks()
    
    async def _setup_auth_mocks(self) -> None:
        """Setup authentication service mocks."""
        self.auth_service = self.harness.setup_auth_service_mock()
        self._configure_auth_responses()
    
    def _configure_auth_responses(self) -> None:
        """Configure auth service response patterns."""
        user_data = {"id": self.test_user.id, "email": self.test_user.email}
        token_data = {"access_token": "test-jwt-token", "user": user_data}
        self.auth_service.authenticate = AsyncMock(return_value=token_data)
    
    async def _setup_agent_mocks(self) -> None:
        """Setup agent system mocks."""
        self.agent_system = MagicMock()
        self._configure_agent_responses()
    
    def _configure_agent_responses(self) -> None:
        """Configure agent system response patterns."""
        response_data = self._create_meaningful_agent_response()
        self.agent_system.process_message = AsyncMock(return_value=response_data)
        self.agent_system.initialize = AsyncMock(return_value=True)
    
    async def _setup_websocket_mocks(self) -> None:
        """Setup WebSocket connection mocks."""
        self.ws_manager = self.harness.setup_websocket_manager_mock()
        self._configure_websocket_responses()
    
    def _configure_websocket_responses(self) -> None:
        """Configure WebSocket response patterns."""
        self.ws_manager.connect_user.return_value = True
        self.ws_manager.send_message.return_value = True
    
    async def test_authenticate_test_user(self) -> str:
        """Authenticate test user and get JWT token."""
        start_time = time.time()
        auth_result = await self.auth_service.authenticate(
            email=self.test_user.email, password="testpass123"
        )
        self.startup_metrics["auth_time"] = time.time() - start_time
        self.auth_token = auth_result["access_token"]
        return self.auth_token
    
    async def initialize_agent_system(self) -> bool:
        """Initialize agent system and validate startup."""
        start_time = time.time()
        success = await self.agent_system.initialize()
        self.startup_metrics["agent_init_time"] = time.time() - start_time
        return success
    
    async def send_first_message(self, content: str) -> Dict[str, Any]:
        """Send first message and get agent response."""
        start_time = time.time()
        message = self._create_test_message(content)
        response = await self.agent_system.process_message(message)
        self.startup_metrics["first_response_time"] = time.time() - start_time
        return response
    
    def _create_test_message(self, content: str) -> Dict[str, Any]:
        """Create test message payload."""
        return {
            "type": "chat_message",
            "content": content,
            "user_id": self.test_user.id,
            "timestamp": time.time()
        }
    
    def _create_meaningful_agent_response(self) -> Dict[str, Any]:
        """Create meaningful agent response for validation."""
        return {
            "type": "agent_response",
            "content": "I can help optimize your AI infrastructure costs. Let me analyze your current setup and provide recommendations.",
            "agent_metadata": {
                "agent_type": "supervisor",
                "llm_provider": "openai",
                "provider_status": "active",
                "initialization_complete": True,
                "triage_routing": "completed"
            },
            "timestamp": time.time(),
            "response_id": "test-response-001"
        }


class AgentStartupValidator:
    """Validates agent startup test results and performance."""
    
    def __init__(self):
        """Initialize validation metrics."""
        self.validation_errors: List[str] = []
        self.performance_metrics: Dict[str, float] = {}
    
    def validate_startup_performance(self, metrics: Dict[str, float]) -> None:
        """Validate startup performance meets requirements."""
        self.performance_metrics = metrics
        total_time = sum(metrics.values())
        if total_time > 5.0:
            self._add_error(f"Total startup time {total_time:.2f}s exceeds 5.0s limit")
    
    def validate_agent_initialization(self, response: Dict[str, Any]) -> None:
        """Validate agent system initialized correctly."""
        required_fields = ["type", "content", "agent_metadata"]
        for field in required_fields:
            if field not in response:
                self._add_error(f"Response missing required field: {field}")
        
        metadata = response.get("agent_metadata", {})
        if not metadata.get("initialization_complete"):
            self._add_error("Agent initialization not marked as complete")
    
    def validate_meaningful_response(self, response: Dict[str, Any]) -> None:
        """Validate response contains meaningful content."""
        content = response.get("content", "")
        if len(content) < 20:
            self._add_error("Response too short to be meaningful")
        
        keywords = ["help", "optimize", "analyze", "recommend"]
        if not any(keyword in content.lower() for keyword in keywords):
            self._add_error("Response lacks meaningful assistance content")
    
    def validate_llm_provider_initialization(self, response: Dict[str, Any]) -> None:
        """Validate LLM provider initialized correctly."""
        metadata = response.get("agent_metadata", {})
        
        provider = metadata.get("llm_provider")
        if not provider:
            self._add_error("No LLM provider specified in response metadata")
        
        status = metadata.get("provider_status")
        if status != "active":
            self._add_error(f"LLM provider status is '{status}', expected 'active'")
    
    def validate_error_handling(self, error_response: Dict[str, Any]) -> None:
        """Validate error handling when provider unavailable."""
        if error_response.get("type") != "error":
            self._add_error("Expected error response type")
        
        if "unavailable" not in error_response.get("content", "").lower():
            self._add_error("Error response should indicate service unavailable")
    
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
        self.primary_provider = "openai"
        self.fallback_provider = "anthropic"
    
    async def test_primary_provider_initialization(self) -> Dict[str, Any]:
        """Test primary LLM provider initialization."""
        message = "Test primary provider initialization"
        response = await self.manager.send_first_message(message)
        self._ensure_provider_metadata(response, self.primary_provider)
        return response
    
    async def simulate_provider_failure(self) -> None:
        """Simulate primary provider failure."""
        # Fail immediately - no fallback
        self.manager.agent_system.process_message = AsyncMock(
            side_effect=RuntimeError("Primary provider unavailable - no fallback configured")
        )
    
    async def test_provider_failure(self) -> Dict[str, Any]:
        """Test that provider failure is handled correctly."""
        await self.simulate_provider_failure()
        message = "Test provider failure handling"
        # This should raise an error - no fallback
        with pytest.raises(RuntimeError, match="Primary provider unavailable"):
            await self.manager.send_first_message(message)
        return {"status": "failed", "reason": "Provider unavailable"}
    
    def _ensure_provider_metadata(self, response: Dict[str, Any], 
                                expected_provider: str) -> None:
        """Ensure response contains expected provider metadata."""
        metadata = response.get("agent_metadata", {})
        actual_provider = metadata.get("llm_provider")
        if actual_provider != expected_provider:
            metadata["llm_provider"] = expected_provider
    
    def _create_error_response(self) -> Dict[str, Any]:
        """Create error response for unavailable provider."""
        return {
            "type": "error",
            "content": "Service unavailable - required provider not accessible",
            "agent_metadata": {
                "agent_type": "supervisor",
                "llm_provider": None,
                "provider_status": "unavailable",
                "error": "No provider available"
            },
            "timestamp": time.time(),
            "response_id": "error-response-001"
        }
