"""Fixtures for first_time_user E2E tests."""

import pytest
from unittest.mock import AsyncMock, Mock


@pytest.fixture
async def conversion_environment():
    """Mock conversion environment for E2E testing."""
    metrics_tracker = Mock()
    metrics_tracker.upgrade_prompt_time = None
    
    # Create comprehensive websocket manager with all needed async methods
    websocket_manager = AsyncMock()
    websocket_manager.send_upgrade_prompt = AsyncMock()
    websocket_manager.send_tier_limits_warning = AsyncMock()
    websocket_manager.send_security_confirmation = AsyncMock()
    websocket_manager.send_dashboard_update = AsyncMock()
    websocket_manager.send_onboarding_update = AsyncMock()
    websocket_manager.send_optimization_results = AsyncMock()
    websocket_manager.send_optimization_result = AsyncMock()
    websocket_manager.send_dashboard_ready = AsyncMock()
    websocket_manager.send_team_upgrade_offer = AsyncMock()
    websocket_manager.send_purchase_confirmation = AsyncMock()
    websocket_manager.send_sharing_ready = AsyncMock()
    websocket_manager.send_message = AsyncMock()
    
    # Create auth client mock
    auth_client = AsyncMock()
    auth_client.signup = AsyncMock(return_value={"user_id": "test_user_123", "email": "newuser@test.com", "plan": "free"})
    auth_client.validate_token = AsyncMock(return_value={"valid": True, "user_id": "test_user_123"})
    auth_client.initiate_oauth = AsyncMock(return_value={"oauth_url": "https://auth.example.com", "state": "test_state"})
    
    # Create demo service mock
    demo_service = AsyncMock()
    demo_service.calculate_roi = AsyncMock(return_value={"roi_percentage": 300, "monthly_savings": 2400})
    demo_service.get_optimization_preview = AsyncMock(return_value={"preview_data": "sample"})
    demo_service.run_scenario = AsyncMock(return_value={"scenario_result": "success", "savings": 1200})
    
    return {
        "user_id": "test_user_123",
        "thread_id": "test_thread_456", 
        "run_id": "test_run_789",
        "tier": "free",
        "usage_stats": {
            "api_calls": 150,
            "data_analyzed": "2.5GB",
            "monthly_savings": 0
        },
        "metrics_tracker": metrics_tracker,
        "websocket_manager": websocket_manager,
        "auth_client": auth_client,
        "demo_service": demo_service
    }


@pytest.fixture  
async def cost_savings_calculator():
    """Mock cost savings calculator."""
    calculator = Mock()
    calculator.calculate_savings = AsyncMock(return_value={
        "current_monthly_cost": 2500.0,
        "netra_monthly_cost": 1800.0,
        "monthly_savings": 700.0,
        "annual_savings": 8400.0,
        "roi_percentage": 28.0
    })
    calculator.preview_optimization_value = Mock(return_value={
        "monthly_savings": 2400.0,
        "annual_savings": 28800.0,
        "roi_percentage": 300.0,
        "optimization_score": 85
    })
    return calculator


@pytest.fixture
async def permission_system():
    """Mock permission system for tier limitations."""
    system = Mock()
    system.check_tier_limits = AsyncMock(return_value={
        "tier": "free",
        "limits_reached": ["api_calls", "data_storage"],
        "upgrade_required": True,
        "remaining_usage": 0
    })
    return system


@pytest.fixture
async def upgrade_flow_manager():
    """Mock upgrade flow manager."""
    manager = Mock()
    manager.initiate_upgrade = AsyncMock(return_value={
        "upgrade_url": "https://netra.ai/upgrade",
        "discount_code": "FIRST20",
        "expires_at": "2024-01-01T00:00:00Z"
    })
    return manager


@pytest.fixture
async def pricing_engine():
    """Mock pricing engine for tier comparisons."""
    engine = Mock()
    engine.get_tier_comparison = AsyncMock(return_value={
        "free": {"api_calls": 1000, "storage": "1GB", "support": "community"},
        "pro": {"api_calls": 10000, "storage": "100GB", "support": "email"},
        "enterprise": {"api_calls": "unlimited", "storage": "unlimited", "support": "priority"}
    })
    return engine


@pytest.fixture
async def ai_provider_simulator():
    """Mock AI provider simulator for API key testing."""
    simulator = AsyncMock()
    simulator.validate_api_key = AsyncMock(return_value={
        "valid": True,
        "provider": "openai",
        "balance": 100.0,
        "rate_limits": {"requests_per_minute": 1000}
    })
    simulator.test_connection = AsyncMock(return_value={
        "connected": True,
        "latency_ms": 45,
        "model_access": ["gpt-4", "gpt-3.5-turbo"]
    })
    simulator.connect_openai = AsyncMock(return_value={
        "provider": "openai",
        "api_key_status": "valid",
        "connection_id": "conn_123"
    })
    simulator.analyze_current_usage = AsyncMock(return_value={
        "monthly_cost": 2500,
        "requests": 15000,
        "tokens_used": 500000
    })
    return simulator


@pytest.fixture
async def enterprise_security_checker():
    """Mock enterprise security checker."""
    checker = Mock()
    checker.validate_compliance = AsyncMock(return_value={
        "gdpr_compliant": True,
        "soc2_compliant": True,
        "encryption": "AES-256",
        "data_residency": "US"
    })
    return checker


@pytest.fixture
async def onboarding_flow_manager():
    """Mock onboarding flow manager."""
    manager = Mock()
    manager.initialize_onboarding = AsyncMock(return_value={
        "session_id": "onboard_123",
        "steps": ["welcome", "api_setup", "optimization", "verification"],
        "current_step": "welcome"
    })
    manager.complete_step = AsyncMock(return_value={"next_step": "api_setup"})
    return manager


@pytest.fixture
async def real_llm_manager():
    """Mock real LLM manager for testing with actual LLM interactions."""
    manager = AsyncMock()
    
    # Configure the generate_response method properly
    manager.generate_response = AsyncMock()
    manager.generate_response.return_value = {
        "content": "This is a sample AI response for testing",
        "model": "gpt-3.5-turbo",
        "tokens_used": 45,
        "cost": 0.0012
    }
    
    manager.analyze_optimization = AsyncMock(return_value={
        "optimization_suggestions": ["Use batch processing", "Implement caching"],
        "confidence": 0.85,
        "potential_savings": 1200
    })
    return manager


@pytest.fixture
async def real_websocket_manager():
    """Mock real websocket manager for testing websocket functionality."""
    manager = AsyncMock()
    manager.connect = AsyncMock(return_value={"connection_id": "ws_123", "status": "connected"})
    manager.send_message = AsyncMock()
    manager.send_optimization_result = AsyncMock()
    manager.send_upgrade_prompt = AsyncMock()
    manager.broadcast = AsyncMock()
    manager.disconnect = AsyncMock()
    return manager