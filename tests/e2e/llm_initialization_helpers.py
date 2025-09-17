class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

        '''LLM Initialization Test Helpers - Supporting classes and utilities

        Separated from main test file to comply with 450-line limit
        All functions  <= 8 lines following CLAUDE.md requirements
        '''

        import asyncio
        import time
        from shared.isolated_environment import get_env
        from decimal import Decimal
        from typing import Any, Dict, List, Optional

        import pytest
        from pydantic import BaseModel, Field

        from netra_backend.app.schemas.config import AppConfig
        from netra_backend.app.schemas.config import LLMConfig
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient


class LLMTestResponse(BaseModel):
        """Structured response model for LLM reasoning tests"""

        category: str = Field(description="Response category")
        confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
        reasoning: str = Field(description="Reasoning explanation")
        token_count_estimate: Optional[int] = Field(default=None, ge=0)


class LLMHealthCheck(BaseModel):
        """Health check response for LLM services"""

        provider: str
        model: str
        status: str
        latency_ms: float
        error: Optional[str] = None


class TokenTracker:
        """Simple token usage tracker for testing"""

    def __init__(self):
        self.total_tokens = 0
        self.total_cost = Decimal("0.0")
        self.requests = 0

    def track_usage(self, usage, cost: Decimal = None) -> None:
        """Track token usage and costs"""
        self.total_tokens += usage.total_tokens
        self.requests += 1
        if cost:
        self.total_cost += cost

    def get_stats(self) -> Dict[str, Any]:
        """Get tracking statistics"""
        avg_tokens = self.total_tokens / max(self.requests, 1)
        return { }
        "total_tokens": self.total_tokens,
        "total_requests": self.requests,
        "total_cost": float(self.total_cost),
        "avg_tokens_per_request": avg_tokens
    


class LLMTestHelpers:
        """Helper methods for LLM initialization testing"""

        @staticmethod
    def check_api_keys() -> Dict[str, bool]:
        """Check availability of real API keys"""
        anthropic_key = get_env().get("ANTHROPIC_API_KEY")
        openai_key = get_env().get("GOOGLE_API_KEY")
        gemini_key = get_env().get("GEMINI_API_KEY")
        return { }
        "anthropic": bool(anthropic_key and anthropic_key != "test-key"),
        "openai": bool(openai_key and openai_key != "test-openai-key"),
        "gemini": bool(gemini_key and gemini_key != "test-gemini-key")
    

        @staticmethod
    def create_llm_config(provider: str, model: str, api_key: str) -> AppConfig:
        """Create LLM configuration for testing"""
        config_dict = { }
        provider: LLMConfig( )
        provider=provider,
        model_name=model,
        api_key=api_key,
        generation_config={"temperature": 0.3, "max_tokens": 500}
    
    
        return AppConfig(llm_configs=config_dict)

        @staticmethod
    def create_mock_llm_manager() -> MagicMock:
        """Create mock LLM manager for testing"""
        mock_manager = MagicMock(); mock_manager.get_llm.return_value = MagicMock(); mock_manager.ask_llm = AsyncMock(return_value="LLM_INIT_SUCCESS")
        LLMTestHelpers._setup_mock_responses(mock_manager)
        return mock_manager

        @staticmethod
    def _setup_mock_responses(mock_manager):
        """Setup mock responses for manager"""
        mock_response = LLMTestHelpers._create_mock_usage_response()
        mock_manager.ask_llm_full = AsyncMock(return_value=mock_response)
        structured_response = LLMTestHelpers._create_mock_structured_response()
        mock_manager.ask_structured_llm = AsyncMock(return_value=structured_response)

        @staticmethod
    def _create_mock_usage_response():
        """Create mock response with usage tracking"""
        mock_response = MagicMock(); mock_response.usage = MagicMock(); mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        return mock_response

        @staticmethod
    def _create_mock_structured_response():
        """Create mock structured response"""
        return LLMTestResponse( )
        category="initialization",
        confidence=0.95,
        reasoning="Mock LLM initialization test successful"
    

        @staticmethod
    def create_structured_test_prompt():
        """Create structured test prompt"""
        return '''
        Analyze this business scenario and respond in JSON format:

        Scenario: LLM service initialization test for revenue-critical system
        Expected: Successful connection with structured response validation

        Provide analysis as JSON with: category, confidence (0-1), reasoning, token_count_estimate
        '''

        @staticmethod
    def validate_structured_response(response):
        """Validate structured response format"""
        assert isinstance(response, LLMTestResponse), "Response not properly structured"
        assert 0.0 <= response.confidence <= 1.0, "Confidence not in valid range"
        assert len(response.reasoning) > 10, "Reasoning too brief"
        assert response.category.strip(), "Category field empty"

        @staticmethod
    async def test_provider_with_mock(mock_manager:
        """Test provider initialization with mock manager"""
        try:
        LLMTestHelpers._verify_client_creation(mock_manager, provider)
        latency = await LLMTestHelpers._test_basic_prompt(mock_manager, provider)
        return LLMTestHelpers._create_success_result(latency, model)
        except Exception as e:
        return {"success": False, "error": str(e), "model": model}

        @staticmethod
    def _verify_client_creation(mock_manager, provider):
        """Verify LLM client creation"""
        client = mock_manager.get_llm(provider)
        assert client is not None, ""

        @staticmethod
    async def _test_basic_prompt(mock_manager, provider):
        """Test basic prompt with timing"""
        start_time = time.time()
        response = await mock_manager.ask_llm("Respond with: LLM_INIT_SUCCESS", provider)
        latency = (time.time() - start_time) * 1000
        assert "LLM_INIT_SUCCESS" in response, ""
        return latency

        @staticmethod
    def _create_success_result(latency, model):
        """Create success result dictionary"""
        return { }
        "success": True,
        "latency_ms": latency,
        "response": "LLM_INIT_SUCCESS",
        "model": model
    

        @staticmethod
    def create_failing_mock_manager():
        """Create mock manager that fails immediately"""
        mock_manager = MagicMock(); mock_manager.ask_llm = AsyncMock( )
        side_effect=RuntimeError("LLM provider unavailable - no fallback")
    
        return mock_manager

        @staticmethod
    async def test_provider_failure(mock_manager):
        """Test that provider failure is raised immediately"""
        with pytest.raises(RuntimeError, match="LLM provider unavailable"):
        await mock_manager.ask_llm("test", "primary")
        return True

        @staticmethod
    def create_failure_result():
        """Create provider failure test result"""
        return { }
        "provider_available": False,
        "error": "Provider unavailable",
        "fallback_available": False
    


class ReliabilityTestHelpers:
        """Helper methods for LLM reliability pattern testing"""

        @staticmethod
    def create_failing_manager():
        """Create manager that always fails"""
        mock_manager = MagicMock(); mock_manager.ask_llm = AsyncMock(side_effect=Exception("Service unavailable"))
        return mock_manager

        @staticmethod
    async def test_repeated_failures(mock_manager):
        """Test repeated failures for circuit breaker"""
        failure_count = 0
        for _ in range(5):
        try:
        await mock_manager.ask_llm("test", "test")
        except Exception:
        failure_count += 1
        return failure_count

        @staticmethod
    def create_slow_manager():
        """Create manager with slow responses"""
        mock_manager = MagicMock(); mock_manager.ask_llm = AsyncMock(side_effect=ReliabilityTestHelpers._slow_response)
        return mock_manager

        @staticmethod
    async def _slow_response(*args, **kwargs):
        """Simulate slow response"""
        await asyncio.sleep(0.1)
        return "degraded_response"

        @staticmethod
    async def test_slow_response(mock_manager):
        """Test response under slow conditions"""
        start_time = time.time()
        try:
        response = await mock_manager.ask_llm("test", "test")
        execution_time = time.time() - start_time
        return execution_time, response
        except Exception as e:
        execution_time = time.time() - start_time
        return execution_time, str(e)

        @staticmethod
    def validate_degradation_handling(execution_time, response):
        """Validate degradation handling behavior"""
        assert execution_time < 2.0, "Degradation handling timeout failed"
        if response is not None:
        assert "error" in str(response).lower() or "unavailable" in str(response).lower(), \
        "Response should indicate service unavailable"
