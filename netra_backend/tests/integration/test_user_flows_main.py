"""
Main User Flow Integration Tests

This file serves as the main entry point for all user flow tests that were
split from test_first_time_user_flows_comprehensive.py to comply with size limits.

Business Value Justification (BVJ):
- Segment: Free → Early → Paid (Primary revenue funnel)
- Business Goal: Protect $570K MRR from first-time user journey failures  
- Value Impact: Each test prevents deployment of broken onboarding flows
- Strategic Impact: Ensures enterprise-ready user experience

The original comprehensive file was refactored into focused modules:
- test_user_registration_flow.py - Registration and email verification
- test_user_onboarding_flow.py - First chat session and profile setup
- test_user_tier_management.py - Free tier limits and paid conversion
- test_user_websocket_lifecycle.py - WebSocket connection lifecycle
- Additional modules for API management, provider integration, etc.
"""

from netra_backend.app.websocket_core.manager import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.tests.integration.helpers.user_flow_helpers import (
    MockAuthService,
    MockUsageService,
    MockWebSocketManager,
    generate_test_user_data,
    simulate_user_journey,
)

class TestCompleteUserJourney:

    """Integration tests for complete end-to-end user journeys"""
    
    @pytest.mark.asyncio
    async def test_complete_new_user_journey(self, 

                                           test_session: AsyncSession,

                                           test_redis: Redis):

        """Test complete journey from registration to first successful interaction"""

        user_data = generate_test_user_data()
        
        # Setup mock services

        mock_services = {

            "auth_service": MockAuthService(),

            "websocket_manager": MockWebSocketManager(),

            "usage_service": MockUsageService()

        }
        
        # Define complete user journey

        journey_steps = [

            {"type": "register", "data": {"user_data": user_data}},

            {"type": "verify_email", "data": {}},

            {"type": "login", "data": {}},

            {"type": "create_thread", "data": {}}

        ]
        
        # Execute complete journey

        result = await simulate_user_journey(journey_steps, mock_services)
        
        # Validate end-to-end success

        assert result["success"] is True, f"Journey failed: {result['errors']}"

        assert result["steps_completed"] == len(journey_steps)
        
        # Verify user is in good state for continued usage

        final_context = result["step_results"][-1].get("context", {})

        assert "thread" in final_context

        assert "session" in result["step_results"][2].get("context", {})
    
    @pytest.mark.asyncio
    async def test_user_journey_with_interruptions(self, test_session: AsyncSession):

        """Test user journey resilience with interruptions"""

        user_data = generate_test_user_data()

        mock_services = {

            "auth_service": MockAuthService(),

            "websocket_manager": MockWebSocketManager()

        }
        
        # Start journey

        initial_steps = [

            {"type": "register", "data": {"user_data": user_data}}

        ]
        
        initial_result = await simulate_user_journey(initial_steps, mock_services)

        assert initial_result["success"] is True
        
        # Simulate interruption and resumption

        await asyncio.sleep(0.1)  # Simulate time gap
        
        # Continue journey

        continuation_steps = [

            {"type": "verify_email", "data": {}},

            {"type": "login", "data": {}}

        ]
        
        # Update context from initial result

        user_context = initial_result["step_results"][0].get("context", {})
        
        continuation_result = await simulate_user_journey(continuation_steps, mock_services)
        
        # Should be able to complete despite interruption

        assert continuation_result["success"] is True
    
    @pytest.mark.asyncio
    async def test_multiple_user_concurrent_journeys(self, test_session: AsyncSession):

        """Test multiple users going through journeys concurrently"""

        num_users = 5

        user_data_list = [generate_test_user_data() for _ in range(num_users)]
        
        mock_services = {

            "auth_service": MockAuthService(),

            "websocket_manager": MockWebSocketManager()

        }
        
        # Define journey for each user

        async def single_user_journey(user_data):

            journey_steps = [

                {"type": "register", "data": {"user_data": user_data}},

                {"type": "verify_email", "data": {}},

                {"type": "login", "data": {}}

            ]

            return await simulate_user_journey(journey_steps, mock_services)
        
        # Execute concurrent journeys

        start_time = time.time()

        tasks = [single_user_journey(user_data) for user_data in user_data_list]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time
        
        # Validate concurrent performance

        successful_journeys = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        
        assert successful_journeys >= num_users * 0.8, f"Too many failed journeys: {successful_journeys}/{num_users}"

        assert total_time < 10.0, f"Concurrent journeys took too long: {total_time:.2f}s"
    
    @pytest.mark.asyncio
    async def test_user_journey_performance_metrics(self, test_session: AsyncSession):

        """Test user journey performance and timing metrics"""

        user_data = generate_test_user_data()

        mock_services = {

            "auth_service": MockAuthService(),

            "websocket_manager": MockWebSocketManager()

        }
        
        # Measure journey timing

        journey_steps = [

            {"type": "register", "data": {"user_data": user_data}},

            {"type": "verify_email", "data": {}},

            {"type": "login", "data": {}}

        ]
        
        start_time = time.time()

        result = await simulate_user_journey(journey_steps, mock_services)

        total_time = time.time() - start_time
        
        # Validate performance requirements

        assert result["success"] is True

        assert total_time < 5.0, f"Journey too slow: {total_time:.2f}s"
        
        # Check individual step timings if available

        step_results = result.get("step_results", [])

        assert len(step_results) == len(journey_steps)

@pytest.fixture

@pytest.mark.asyncio
async def test_user_data() -> Dict[str, Any]:

    """Fixture providing test user data"""

    return generate_test_user_data()

@pytest.fixture

async def mock_services():

    """Fixture providing mock services for testing"""

    return {

        "auth_service": MockAuthService(),

        "websocket_manager": MockWebSocketManager(),

        "usage_service": MockUsageService()

    }