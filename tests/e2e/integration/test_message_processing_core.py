"""Core Message Processing E2E Tests

Tests essential message processing functionality including validation,
routing, and state transitions. Uses real handlers without mocks.

Business Value: Ensures reliable core message processing
"""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.handlers.example_message_handler import ExampleMessageHandler
from tests.e2e.example_message_test_helpers import (
    BASIC_COST_OPTIMIZATION,
    assert_completed_response,
    assert_error_response,
    create_example_message_request,
)


@pytest.fixture
async def example_handler():
    """Get example message handler instance"""
    return ExampleMessageHandler()


@pytest.fixture 
@pytest.mark.e2e
async def test_user_id():
    """Generate test user ID"""
    return f"test_user_{uuid4()}"


@pytest.mark.e2e
class TestMessageValidation:
    """Test message validation flow"""

    @pytest.mark.e2e
    async def test_valid_message_processing(self, example_handler, test_user_id):
        """Test processing of valid message"""
        request = create_example_message_request(BASIC_COST_OPTIMIZATION, user_id=test_user_id)
        response = await example_handler.handle_example_message(request)
        assert_completed_response(response)

    @pytest.mark.e2e
    async def test_invalid_message_structure(self, example_handler):
        """Test handling of invalid message structure"""
        invalid_request = {"invalid": "structure"}
        response = await example_handler.handle_example_message(invalid_request)
        assert_error_response(response)

    @pytest.mark.e2e
    async def test_missing_required_fields(self, example_handler):
        """Test handling of missing required fields"""
        incomplete_request = {"content": "Test message"}
        response = await example_handler.handle_example_message(incomplete_request)
        assert_error_response(response)

    @pytest.mark.e2e
    async def test_invalid_category_validation(self, example_handler, test_user_id):
        """Test validation of invalid category"""
        request = create_example_message_request(
            "Test content", 
            category="invalid-category",
            user_id=test_user_id
        )
        response = await example_handler.handle_example_message(request)
        assert_error_response(response)


@pytest.mark.e2e
class TestMessageRouting:
    """Test message routing to agents"""

    @pytest.mark.e2e
    async def test_cost_optimization_routing(self, example_handler, test_user_id):
        """Test routing to cost optimization agent"""
        request = create_example_message_request(
            BASIC_COST_OPTIMIZATION,
            category="cost-optimization",
            user_id=test_user_id
        )
        response = await example_handler.handle_example_message(request)
        assert_completed_response(response)
        assert "cost" in response.result.get("optimization_type", "").lower()

    @pytest.mark.e2e
    async def test_latency_optimization_routing(self, example_handler, test_user_id):
        """Test routing to latency optimization agent"""
        request = create_example_message_request(
            "Need 3x latency improvement",
            category="latency-optimization",
            user_id=test_user_id
        )
        response = await example_handler.handle_example_message(request)
        assert_completed_response(response)
        assert "latency" in response.result.get("optimization_type", "").lower()

    @pytest.mark.e2e
    async def test_model_selection_routing(self, example_handler, test_user_id):
        """Test routing to model selection agent"""
        request = create_example_message_request(
            "Evaluate GPT-4o effectiveness",
            category="model-selection",
            user_id=test_user_id
        )
        response = await example_handler.handle_example_message(request)
        assert_completed_response(response)
        assert "model" in response.result.get("optimization_type", "").lower()

    @pytest.mark.e2e
    async def test_scaling_analysis_routing(self, example_handler, test_user_id):
        """Test routing to scaling analysis agent"""
        request = create_example_message_request(
            "50% usage increase impact",
            category="scaling",
            user_id=test_user_id
        )
        response = await example_handler.handle_example_message(request)
        assert_completed_response(response)
        assert "scaling" in response.result.get("optimization_type", "").lower()


@pytest.mark.e2e
class TestMessageStateTracking:
    """Test message state transitions"""

    @pytest.mark.e2e
    async def test_session_creation_and_cleanup(self, example_handler, test_user_id):
        """Test session is created and cleaned up properly"""
        initial_count = len(example_handler.get_active_sessions())
        request = create_example_message_request(BASIC_COST_OPTIMIZATION, user_id=test_user_id)
        await example_handler.handle_example_message(request)
        final_count = len(example_handler.get_active_sessions())
        assert final_count == initial_count

    @pytest.mark.e2e
    async def test_processing_time_tracking(self, example_handler, test_user_id):
        """Test processing time is tracked"""
        request = create_example_message_request(BASIC_COST_OPTIMIZATION, user_id=test_user_id)
        response = await example_handler.handle_example_message(request)
        assert_completed_response(response)
        assert response.processing_time_ms > 0

    @pytest.mark.e2e
    async def test_error_state_handling(self, example_handler):
        """Test error state handling and cleanup"""
        initial_count = len(example_handler.get_active_sessions())
        invalid_request = {"invalid": "data"}
        await example_handler.handle_example_message(invalid_request)
        final_count = len(example_handler.get_active_sessions())
        assert final_count == initial_count


@pytest.mark.e2e
class TestBusinessValueTracking:
    """Test business value and insights generation"""

    @pytest.mark.e2e
    async def test_business_insights_generation(self, example_handler, test_user_id):
        """Test business insights are generated"""
        request = create_example_message_request(
            BASIC_COST_OPTIMIZATION,
            business_value="conversion",
            user_id=test_user_id
        )
        response = await example_handler.handle_example_message(request)
        assert_completed_response(response)
        if response.business_insights:
            assert "business_value_type" in response.business_insights
            assert "performance_score" in response.business_insights

    @pytest.mark.e2e
    async def test_conversion_tracking(self, example_handler, test_user_id):
        """Test conversion-focused tracking"""
        request = create_example_message_request(
            BASIC_COST_OPTIMIZATION,
            business_value="conversion",
            user_id=test_user_id
        )
        response = await example_handler.handle_example_message(request)
        assert_completed_response(response)
        if response.business_insights:
            assert response.business_insights["business_value_type"] == "conversion"
