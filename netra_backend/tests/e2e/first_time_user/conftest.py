from unittest.mock import Mock, patch, MagicMock, AsyncMock
"""Fixtures for first_time_user E2E tests."""

import pytest
from unittest.mock import AsyncMock, Mock
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig



@pytest.fixture
async def conversion_environment():
    """Mock conversion environment for E2E testing."""
    # Mock: Generic component isolation for controlled unit testing
    metrics_tracker = Mock()
    metrics_tracker.upgrade_prompt_time = None
    
    # Create comprehensive websocket manager with all needed async methods
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager = AsyncMock()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_upgrade_prompt = AsyncMock()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_tier_limits_warning = AsyncMock()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_security_confirmation = AsyncMock()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_dashboard_update = AsyncMock()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_onboarding_update = AsyncMock()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_optimization_results = AsyncMock()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_optimization_result = AsyncMock()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_dashboard_ready = AsyncMock()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_team_upgrade_offer = AsyncMock()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_purchase_confirmation = AsyncMock()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_sharing_ready = AsyncMock()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_message = AsyncMock()
    
    # Create auth client mock
    # Mock: Generic component isolation for controlled unit testing
    auth_client = AsyncMock()
    # Mock: Async component isolation for testing without real async operations
    auth_client.signup = AsyncMock(return_value = {"user_id": "test_user_123", "email": "newuser@test.com", "plan": "free"})
    # Mock: Async component isolation for testing without real async operations
    auth_client.validate_token = AsyncMock(return_value = {"valid": True, "user_id": "test_user_123"})
    # Mock: OAuth external provider isolation for network-independent testing
    auth_client.initiate_oauth = AsyncMock(return_value = {"oauth_url": "https://auth.example.com", "state": "test_state"})
    
    
    yield {
        "user_id": "test_user_123",
        "thread_id": "test_thread_456", 
        "run_id": "test_run_789",
        "tier": "free",
        "usage_stats": {
            "api_calls": 150,
            "data_analyzed": "2.5GB",
            "monthly_savings": 0,
},
        "metrics_tracker": metrics_tracker,
        "websocket_manager": websocket_manager,
        "auth_client": auth_client,
}


@pytest.fixture  
async def cost_savings_calculator():
    """Mock cost savings calculator."""
    # Mock: Generic component isolation for controlled unit testing
    calculator = Mock()
    # Mock: Async component isolation for testing without real async operations
    calculator.calculate_savings = AsyncMock(return_value = {
        "current_monthly_cost": 2500.0,
        "netra_monthly_cost": 1800.0,
        "monthly_savings": 700.0,
        "annual_savings": 8400.0,
        "roi_percentage": 28.0,
})
    # Mock: Component isolation for controlled unit testing
    calculator.preview_optimization_value = Mock(return_value = {
        "monthly_savings": 2400.0,
        "annual_savings": 28800.0,
        "roi_percentage": 300.0,
        "optimization_score": 85,
})
    yield calculator


@pytest.fixture
async def permission_system():
    """Mock permission system for tier limitations."""
    # Mock: Generic component isolation for controlled unit testing
    system = Mock()
    # Mock: Async component isolation for testing without real async operations
    system.check_tier_limits = AsyncMock(return_value = {
        "tier": "free",
        "limits_reached": ["api_calls", "data_storage"],
        "upgrade_required": True,
        "remaining_usage": 0,
})
    yield system


@pytest.fixture
async def upgrade_flow_manager():
    """Mock upgrade flow manager."""
    # Mock: Generic component isolation for controlled unit testing
    manager = Mock()
    # Mock: Async component isolation for testing without real async operations
    manager.initiate_upgrade = AsyncMock(return_value = {
        "upgrade_url": "https://netra.ai/upgrade",
        "discount_code": "FIRST20",
        "expires_at": "2024-01-01T00:00:00Z",
})
    yield manager


@pytest.fixture
async def pricing_engine():
    """Mock pricing engine for tier comparisons."""
    # Mock: Generic component isolation for controlled unit testing
    engine = Mock()
    # Mock: Async component isolation for testing without real async operations
    engine.get_tier_comparison = AsyncMock(return_value = {
        "free": {"api_calls": 1000, "storage": "1GB", "support": "community"},
        "pro": {"api_calls": 10000, "storage": "100GB", "support": "email"},
        "enterprise": {"api_calls": "unlimited", "storage": "unlimited", "support": "priority"},
})
    yield engine


@pytest.fixture
async def ai_provider_simulator():
    """Mock AI provider simulator for API key testing."""
    # Mock: Generic component isolation for controlled unit testing
    simulator = AsyncMock()
    # Mock: Async component isolation for testing without real async operations
    simulator.validate_api_key = AsyncMock(return_value = {
        "valid": True,
        "provider": "openai",
        "balance": 100.0,
        "rate_limits": {"requests_per_minute": 1000},
})
    # Mock: Async component isolation for testing without real async operations
    simulator.test_connection = AsyncMock(return_value = {
        "connected": True,
        "latency_ms": 45,
        "model_access": [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value],
})
    # Mock: OpenAI service isolation to avoid API rate limits and costs
    simulator.connect_openai = AsyncMock(return_value = {
        "provider": "openai",
        "api_key_status": "valid",
        "connection_id": "conn_123",
})
    # Mock: Async component isolation for testing without real async operations
    simulator.analyze_current_usage = AsyncMock(return_value = {
        "monthly_cost": 2500,
        "requests": 15000,
        "tokens_used": 500000,
})
    yield simulator


@pytest.fixture
async def enterprise_security_checker():
    """Mock enterprise security checker."""
    # Mock: Generic component isolation for controlled unit testing
    checker = Mock()
    # Mock: Async component isolation for testing without real async operations
    checker.validate_compliance = AsyncMock(return_value = {
        "gdpr_compliant": True,
        "soc2_compliant": True,
        "encryption": "AES-256",
        "data_residency": "US",
})
    yield checker


@pytest.fixture
async def onboarding_flow_manager():
    """Mock onboarding flow manager."""
    # Mock: Generic component isolation for controlled unit testing
    manager = Mock()
    # Mock: Async component isolation for testing without real async operations
    manager.initialize_onboarding = AsyncMock(return_value = {
        "session_id": "onboard_123",
        "steps": ["welcome", "api_setup", "optimization", "verification"],
        "current_step": "welcome",
})
    # Mock: Async component isolation for testing without real async operations
    manager.complete_step = AsyncMock(return_value = {"next_step": "api_setup"})
    yield manager


@pytest.fixture
async def real_llm_manager():
    """Mock real LLM manager for testing with actual LLM interactions."""
    # Mock: Generic component isolation for controlled unit testing
    manager = AsyncMock()
    
    # Configure the generate_response method properly
    # Mock: Generic component isolation for controlled unit testing
    manager.generate_response = AsyncMock()
    manager.generate_response.return_value = {
        "content": "This is a sample AI response for testing",
        "model": LLMModel.GEMINI_2_5_FLASH.value,
        "tokens_used": 45,
        "cost": 0.0012,
}
    
    # Mock: Async component isolation for testing without real async operations
    manager.analyze_optimization = AsyncMock(return_value = {
        "optimization_suggestions": ["Use batch processing", "Implement caching"],
        "confidence": 0.85,
        "potential_savings": 1200,
})
    yield manager


@pytest.fixture
async def real_websocket_manager():
    """Mock real websocket manager for testing websocket functionality."""
    # Mock: Generic component isolation for controlled unit testing
    manager = AsyncMock()
    # Mock: Async component isolation for testing without real async operations
    manager.connect = AsyncMock(return_value = {"connection_id": "ws_123", "status": "connected"})
    # Mock: Generic component isolation for controlled unit testing
    manager.send_message = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    manager.send_optimization_result = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    manager.send_upgrade_prompt = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    manager.broadcast = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    manager.disconnect = AsyncMock()
    yield manager