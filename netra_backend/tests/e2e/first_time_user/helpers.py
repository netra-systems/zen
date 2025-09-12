"""
First-Time User E2E Test Helpers - Shared fixtures and utilities

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Free users  ->  Paid conversions (10,000+ potential users)
2. **Business Goal**: Increase conversion rate from 2% to 15% = 6.5x improvement
3. **Value Impact**: Each test validates $99-$999/month revenue per conversion
4. **Revenue Impact**: Optimized journey = +$1.2M ARR from improved conversions
5. **Growth Engine**: First experience determines 95% of conversion probability
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, Mock

import pytest

from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.services.cost_calculator import CostCalculatorService

@dataclass
class FirstTimeUserMetrics:
    """Track first-time user conversion metrics"""
    signup_time: datetime
    first_value_time: Optional[datetime] = None
    first_optimization_time: Optional[datetime] = None
    upgrade_prompt_time: Optional[datetime] = None
    conversion_time: Optional[datetime] = None
    abandonment_time: Optional[datetime] = None

class FirstTimeUserTestHelpers:
    """Shared helper methods for first-time user E2E tests"""
    
    @staticmethod
    async def create_conversion_environment():
        """Create comprehensive conversion test environment"""
        env = {
            "auth_client": FirstTimeUserTestHelpers._create_auth_client_mock(),
            "websocket_manager": FirstTimeUserTestHelpers._create_websocket_mock(),
            "metrics_tracker": FirstTimeUserMetrics(signup_time=datetime.now(timezone.utc))
        }
        return env

    @staticmethod
    def _create_auth_client_mock():
        """Create auth client with realistic signup/login flows"""
        auth_client = AsyncMock()
        auth_client.signup = AsyncMock(return_value={"user_id": str(uuid.uuid4()), "email": "newuser@test.com"})
        auth_client.validate_token = AsyncMock(return_value={"valid": True, "user_id": "test-user"})
        return auth_client


    @staticmethod
    def _create_websocket_mock():
        """Create WebSocket manager for real-time updates"""
        ws_manager = AsyncMock()
        ws_manager.send_optimization_result = AsyncMock()
        ws_manager.send_upgrade_prompt = AsyncMock()
        ws_manager.send_message = AsyncMock()
        return ws_manager

    @staticmethod
    def init_cost_savings_calculator():
        """Initialize cost savings calculator for immediate value demonstration"""
        calculator = Mock(spec=CostCalculatorService)
        calculator.calculate_immediate_savings = Mock(return_value={"monthly_savings": 2400, "roi_percentage": 340})
        calculator.preview_optimization_value = Mock()
        return calculator

    @staticmethod
    def init_ai_provider_simulator():
        """Initialize AI provider connection simulator"""
        simulator = Mock()
        simulator.connect_openai = AsyncMock(return_value={"connected": True, "current_cost": 1200})
        simulator.analyze_current_usage = AsyncMock()
        return simulator

# Shared fixtures
@pytest.fixture
async def conversion_environment():
    """Setup complete conversion test environment"""
    yield await FirstTimeUserTestHelpers.create_conversion_environment()

@pytest.fixture
def cost_savings_calculator():
    """Setup cost savings calculator for value demonstration"""
    return FirstTimeUserTestHelpers.init_cost_savings_calculator()

@pytest.fixture
def ai_provider_simulator():
    """Setup AI provider connection simulator"""
    return FirstTimeUserTestHelpers.init_ai_provider_simulator()