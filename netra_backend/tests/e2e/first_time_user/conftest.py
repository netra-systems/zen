"""Fixtures for first_time_user E2E tests."""

import pytest
from unittest.mock import AsyncMock, Mock


@pytest.fixture
async def conversion_environment():
    """Mock conversion environment for E2E testing."""
    metrics_tracker = Mock()
    metrics_tracker.upgrade_prompt_time = None
    
    websocket_manager = Mock()
    websocket_manager.send_upgrade_prompt = AsyncMock()
    websocket_manager.send_tier_limits_warning = AsyncMock()
    
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
        "websocket_manager": websocket_manager
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