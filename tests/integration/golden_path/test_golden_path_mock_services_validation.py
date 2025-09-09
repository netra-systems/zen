#!/usr/bin/env python3
"""
Golden Path Mock Services Validation Test
==========================================

This test validates that the Golden Path mock services work correctly
when Docker is not available, ensuring business logic validation
without external dependencies.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity
- Business Goal: Enable Golden Path test execution in no-Docker environments
- Value Impact: Faster development cycles and CI/CD reliability
- Strategic Impact: Reduced infrastructure dependencies for testing
"""

import asyncio
import pytest
from loguru import logger

# SSOT Test Framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.fixtures.no_docker_golden_path_fixtures import (
    golden_path_services,
    mock_authenticated_user
)


class TestGoldenPathMockServicesValidation(SSotAsyncTestCase):
    """Validate Golden Path mock services work correctly without Docker."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mock_services_availability(self, golden_path_services):
        """Test that mock services are available and properly configured."""
        
        # Validate service availability
        assert golden_path_services is not None, "Golden Path services must be available"
        assert golden_path_services.get("available") is True, "Services must be marked as available"
        
        # Validate service type
        service_type = golden_path_services.get("service_type")
        assert service_type == "mock", f"Expected mock services, got: {service_type}"
        
        # Validate required service components
        required_services = [
            "websocket_manager",
            "database_manager", 
            "redis_manager",
            "agent_engine",
            "mock_state"
        ]
        
        for service_name in required_services:
            assert service_name in golden_path_services, f"Missing required service: {service_name}"
            assert golden_path_services[service_name] is not None, f"Service {service_name} is None"
        
        logger.success("✅ Mock services validation passed")
    
    @pytest.mark.integration
    @pytest.mark.asyncio  
    async def test_mock_websocket_connection(self, golden_path_services, mock_authenticated_user):
        """Test mock WebSocket connection and basic functionality."""
        
        websocket_manager = golden_path_services["websocket_manager"]
        
        # Test connection
        user_context = {
            "user_id": mock_authenticated_user["user_id"],
            "email": mock_authenticated_user["email"]
        }
        
        success = await websocket_manager.connect(
            mock_authenticated_user["websocket_client_id"],
            user_context
        )
        
        assert success is True, "Mock WebSocket connection must succeed"
        
        # Test event emission
        test_event = {
            "test_data": "mock_event",
            "user_id": mock_authenticated_user["user_id"]
        }
        
        event_success = await websocket_manager.emit_agent_event(
            "agent_started", 
            test_event,
            mock_authenticated_user["websocket_client_id"]
        )
        
        assert event_success is True, "Mock WebSocket event emission must succeed"
        
        # Validate event was recorded
        events = websocket_manager.get_events_sent()
        assert len(events) > 0, "At least one event should be recorded"
        assert events[0]["event_type"] == "agent_started", "Event type must be correct"
        
        logger.success("✅ Mock WebSocket validation passed")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mock_agent_execution(self, golden_path_services, mock_authenticated_user):
        """Test mock agent execution with WebSocket events."""
        
        agent_engine = golden_path_services["agent_engine"]
        websocket_manager = golden_path_services["websocket_manager"]
        
        # Execute mock agent pipeline
        user_context = {
            "user_id": mock_authenticated_user["user_id"],
            "email": mock_authenticated_user["email"]
        }
        
        result = await agent_engine.execute_agent_pipeline(
            user_context,
            "Test optimization request for mock execution"
        )
        
        # Validate execution result
        assert result is not None, "Agent execution must return result"
        assert result.get("status") == "completed", "Execution must complete successfully"
        assert result.get("execution_id") is not None, "Execution ID must be provided"
        
        # Validate WebSocket events were emitted
        events = websocket_manager.get_events_sent()
        critical_events = websocket_manager.get_critical_events_count()
        
        assert len(events) >= 5, "At least 5 WebSocket events should be emitted"
        assert critical_events >= 5, "All 5 critical events should be emitted"
        
        # Check for specific event types
        event_types = [event["event_type"] for event in events]
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for expected_event in expected_events:
            assert expected_event in event_types, f"Missing critical event: {expected_event}"
        
        logger.success("✅ Mock agent execution validation passed")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mock_data_persistence(self, golden_path_services, mock_authenticated_user):
        """Test mock database and Redis operations."""
        
        database_manager = golden_path_services["database_manager"]
        redis_manager = golden_path_services["redis_manager"]
        
        # Test database operations
        test_message = {
            "content": "Test message for mock validation",
            "user_id": mock_authenticated_user["user_id"],
            "message_type": "optimization_request"
        }
        
        success = await database_manager.save_message("test_thread_123", test_message)
        assert success is True, "Mock database save must succeed"
        
        # Test Redis operations
        cache_key = f"test_key_{mock_authenticated_user['user_id']}"
        cache_value = "test_cache_value"
        
        set_success = await redis_manager.set(cache_key, cache_value, expire=60)
        assert set_success is True, "Mock Redis set must succeed"
        
        cached_value = await redis_manager.get(cache_key)
        assert cached_value is not None, "Cached value must be retrievable"
        
        key_exists = await redis_manager.exists(cache_key)
        assert key_exists is True, "Cache key must exist"
        
        logger.success("✅ Mock data persistence validation passed")
    
    @pytest.mark.integration  
    @pytest.mark.asyncio
    async def test_complete_mock_golden_path_flow(self, golden_path_services, mock_authenticated_user):
        """Test complete Golden Path flow using mock services."""
        
        websocket_manager = golden_path_services["websocket_manager"]
        agent_engine = golden_path_services["agent_engine"]
        mock_state = golden_path_services["mock_state"]
        
        # Clear any previous state
        mock_state.reset()
        
        # Step 1: Connect WebSocket
        user_context = {
            "user_id": mock_authenticated_user["user_id"],
            "email": mock_authenticated_user["email"]
        }
        
        connection_success = await websocket_manager.connect(
            mock_authenticated_user["websocket_client_id"],
            user_context
        )
        assert connection_success, "WebSocket connection must succeed"
        
        # Step 2: Execute agent pipeline
        optimization_request = (
            "Analyze my AI costs: $50K/month on OpenAI, $30K on custom models. "
            "Identify optimization opportunities for 20% cost reduction."
        )
        
        execution_result = await agent_engine.execute_agent_pipeline(
            user_context,
            optimization_request
        )
        
        # Step 3: Validate complete flow
        assert execution_result["status"] == "completed", "Agent execution must complete"
        assert execution_result.get("tools_executed", 0) > 0, "Tools must be executed"
        
        # Validate WebSocket events
        events = websocket_manager.get_events_sent()
        critical_events = websocket_manager.get_critical_events_count()
        
        assert critical_events >= 5, "At least 5 critical events must be emitted"
        
        # Validate state tracking
        assert len(mock_state.agent_executions) > 0, "Agent execution must be tracked"
        assert len(mock_state.tool_executions) > 0, "Tool executions must be tracked"
        assert len(mock_state.websocket_events_sent) > 0, "WebSocket events must be tracked"
        
        # Business value validation
        execution_time = execution_result.get("execution_time", 0)
        assert execution_time > 0, "Execution time must be measured"
        assert execution_time < 5.0, "Mock execution should complete quickly"
        
        logger.success("✅ Complete mock Golden Path flow validation passed")
        
        # Provide business value summary
        logger.success(f"🎯 Business Value Delivered:")
        logger.success(f"   Mock services functional: ✅")
        logger.success(f"   WebSocket events validated: {critical_events}")
        logger.success(f"   Execution completed: ✅")
        logger.success(f"   Performance acceptable: {execution_time:.2f}s < 5.0s")
        logger.success(f"   No Docker dependency: ✅")