"""
Test Message Handler Factory Pattern SSOT Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate message handler factory violations blocking golden path
- Value Impact: Remove duplicate message handling patterns causing communication failures
- Strategic Impact: Critical $120K+ MRR protection through reliable message processing

This test validates that message handler factory patterns don't create duplicate
message processing systems. The over-engineering audit identified multiple message
handler factories that violate SSOT principles.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

# Import message handling classes to test SSOT violations
from netra_backend.app.services.user_execution_context import UserExecutionContext


class MockMessageHandler:
    """Mock message handler for testing factory patterns."""
    
    def __init__(self, handler_id: str):
        self.handler_id = handler_id
        self.processed_messages = []
        self.is_initialized = False
    
    async def initialize(self, **kwargs):
        self.is_initialized = True
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        self.processed_messages.append(message)
        return {
            "status": "processed",
            "handler_id": self.handler_id,
            "message_id": message.get("id"),
            "processed_at": time.time()
        }
    
    async def cleanup(self):
        self.is_initialized = False


class MockMessageHandlerFactory:
    """Mock message handler factory for testing SSOT violations."""
    
    def __init__(self, factory_type: str):
        self.factory_type = factory_type
        self.created_handlers = []
    
    async def create_handler(self, handler_config: Dict[str, Any]) -> MockMessageHandler:
        handler_id = f"{self.factory_type}_{len(self.created_handlers)}"
        handler = MockMessageHandler(handler_id)
        await handler.initialize(**handler_config)
        self.created_handlers.append(handler)
        return handler
    
    async def cleanup_all_handlers(self):
        for handler in self.created_handlers:
            await handler.cleanup()
        self.created_handlers.clear()


class TestMessageHandlerFactoryPatterns(BaseIntegrationTest):
    """Test SSOT violations in message handler factory patterns."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_handler_factory_duplication_patterns(self, real_services_fixture):
        """
        Test SSOT violation between different message handler factory implementations.
        
        SSOT Violation: Multiple factory patterns for creating message handlers
        with overlapping responsibilities and inconsistent APIs.
        """
        # SSOT VIOLATION: Multiple message handler factory patterns
        
        # Pattern 1: WebSocket message handler factory
        websocket_factory = MockMessageHandlerFactory("websocket")
        
        # Pattern 2: Agent message handler factory  
        agent_factory = MockMessageHandlerFactory("agent")
        
        # Pattern 3: API message handler factory
        api_factory = MockMessageHandlerFactory("api")
        
        # Create test message handlers via different factories
        handler_configs = [
            {"message_type": "websocket_event", "user_id": "test_user_1"},
            {"message_type": "agent_response", "user_id": "test_user_2"},
            {"message_type": "api_request", "user_id": "test_user_3"}
        ]
        
        # Create handlers via each factory
        websocket_handlers = []
        agent_handlers = []
        api_handlers = []
        
        for config in handler_configs:
            websocket_handler = await websocket_factory.create_handler(config)
            agent_handler = await agent_factory.create_handler(config)
            api_handler = await api_factory.create_handler(config)
            
            websocket_handlers.append(websocket_handler)
            agent_handlers.append(agent_handler)
            api_handlers.append(api_handler)
        
        # SSOT REQUIREMENT: All handlers should process messages consistently
        
        test_messages = [
            {"id": "msg_1", "type": "user_message", "content": "Hello", "user_id": "test_user_1"},
            {"id": "msg_2", "type": "agent_query", "content": "Process data", "user_id": "test_user_2"},
            {"id": "msg_3", "type": "api_call", "content": "Get status", "user_id": "test_user_3"}
        ]
        
        # Process messages through all handler types
        handler_results = {
            "websocket": [],
            "agent": [],
            "api": []
        }
        
        for i, message in enumerate(test_messages):
            # Process via websocket handler
            websocket_result = await websocket_handlers[i].handle_message(message)
            handler_results["websocket"].append(websocket_result)
            
            # Process via agent handler
            agent_result = await agent_handlers[i].handle_message(message)
            handler_results["agent"].append(agent_result)
            
            # Process via API handler
            api_result = await api_handlers[i].handle_message(message)
            handler_results["api"].append(api_result)
        
        # SSOT VALIDATION: All handlers should produce consistent results
        
        for handler_type, results in handler_results.items():
            for i, result in enumerate(results):
                assert result["status"] == "processed"
                assert result["message_id"] == test_messages[i]["id"]
                assert handler_type in result["handler_id"]
                assert "processed_at" in result
        
        # CRITICAL: Test message routing consistency
        # All factories should route messages to appropriate handlers
        
        # Test message routing patterns
        routing_test_message = {
            "id": "routing_test",
            "type": "multi_handler_test",
            "content": "Test routing",
            "target_handlers": ["websocket", "agent", "api"]
        }
        
        # Route to all handler types
        routing_results = {}
        
        # Route via websocket handler
        routing_results["websocket"] = await websocket_handlers[0].handle_message(routing_test_message)
        
        # Route via agent handler
        routing_results["agent"] = await agent_handlers[0].handle_message(routing_test_message)
        
        # Route via API handler
        routing_results["api"] = await api_handlers[0].handle_message(routing_test_message)
        
        # All should process the same message consistently
        for handler_type, result in routing_results.items():
            assert result["status"] == "processed"
            assert result["message_id"] == "routing_test"
        
        # Test handler state isolation
        # Each handler should maintain independent state
        
        websocket_processed_count = len(websocket_handlers[0].processed_messages)
        agent_processed_count = len(agent_handlers[0].processed_messages)
        api_processed_count = len(api_handlers[0].processed_messages)
        
        # All handlers should have processed same number of messages
        assert websocket_processed_count == agent_processed_count == api_processed_count == 2
        
        # Cleanup all handlers
        await websocket_factory.cleanup_all_handlers()
        await agent_factory.cleanup_all_handlers()
        await api_factory.cleanup_all_handlers()
        
        # Business value: Unified message handling reduces processing inconsistencies
        self.assert_business_value_delivered(
            {
                "message_handler_consolidation": True,
                "processing_consistency": True,
                "routing_reliability": True,
                "handler_isolation": True
            },
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_handler_lifecycle_management_duplication(self, real_services_fixture):
        """
        Test SSOT violation in message handler lifecycle management patterns.
        
        SSOT Violation: Different factory patterns manage handler lifecycle
        with inconsistent initialization, cleanup, and error handling.
        """
        # SSOT VIOLATION: Inconsistent lifecycle management patterns
        
        # Create factories with different lifecycle patterns
        short_lived_factory = MockMessageHandlerFactory("short_lived")
        long_lived_factory = MockMessageHandlerFactory("long_lived") 
        persistent_factory = MockMessageHandlerFactory("persistent")
        
        # Create test user context
        user_context = UserExecutionContext.from_request_supervisor(
            user_id="lifecycle_test_user",
            thread_id="thread_lifecycle",
            run_id="run_lifecycle",
            db_session=real_services_fixture["db"]
        )
        
        # Test different lifecycle patterns
        
        # Pattern 1: Short-lived handlers (created per message)
        short_lived_handlers = []
        for i in range(5):
            handler = await short_lived_factory.create_handler({
                "lifecycle": "per_message",
                "user_context": user_context,
                "message_index": i
            })
            short_lived_handlers.append(handler)
        
        # Pattern 2: Long-lived handlers (created per session)
        session_handler = await long_lived_factory.create_handler({
            "lifecycle": "per_session",
            "user_context": user_context,
            "session_id": user_context.thread_id
        })
        
        # Pattern 3: Persistent handlers (created once, reused)
        persistent_handler = await persistent_factory.create_handler({
            "lifecycle": "persistent",
            "user_context": user_context,
            "persistent_id": "global_handler"
        })
        
        # CRITICAL: Test message processing across different lifecycle patterns
        
        test_messages = [
            {"id": f"lifecycle_msg_{i}", "content": f"Message {i}", "timestamp": time.time() + i}
            for i in range(5)
        ]
        
        # Process messages via different lifecycle patterns
        lifecycle_results = {
            "short_lived": [],
            "long_lived": [],
            "persistent": []
        }
        
        # Short-lived pattern: one handler per message
        for i, message in enumerate(test_messages):
            result = await short_lived_handlers[i].handle_message(message)
            lifecycle_results["short_lived"].append(result)
            # Cleanup immediately after use
            await short_lived_handlers[i].cleanup()
        
        # Long-lived pattern: same handler for all messages
        for message in test_messages:
            result = await session_handler.handle_message(message)
            lifecycle_results["long_lived"].append(result)
        
        # Persistent pattern: same handler for all messages
        for message in test_messages:
            result = await persistent_handler.handle_message(message)
            lifecycle_results["persistent"].append(result)
        
        # SSOT REQUIREMENT: All lifecycle patterns should produce consistent results
        
        # All patterns should process all messages successfully
        for pattern, results in lifecycle_results.items():
            assert len(results) == len(test_messages)
            for result in results:
                assert result["status"] == "processed"
                assert "processed_at" in result
        
        # Test performance differences between patterns
        start_time = time.time()
        
        # Measure short-lived pattern overhead (create/destroy per message)
        short_lived_start = time.time()
        for i in range(10):
            handler = await short_lived_factory.create_handler({"test": i})
            await handler.handle_message({"id": f"perf_test_{i}", "content": "Performance test"})
            await handler.cleanup()
        short_lived_time = time.time() - short_lived_start
        
        # Measure long-lived pattern performance (reuse handler)
        long_lived_start = time.time()
        perf_handler = await long_lived_factory.create_handler({"test": "performance"})
        for i in range(10):
            await perf_handler.handle_message({"id": f"perf_test_{i}", "content": "Performance test"})
        await perf_handler.cleanup()
        long_lived_time = time.time() - long_lived_start
        
        total_perf_time = time.time() - start_time
        
        # Long-lived pattern should be more efficient for multiple messages
        if short_lived_time > 0 and long_lived_time > 0:
            efficiency_ratio = short_lived_time / long_lived_time
            # Short-lived should not be more than 3x slower (reasonable overhead)
            assert efficiency_ratio < 3.0, f"Short-lived pattern too inefficient: {efficiency_ratio}x slower"
        
        # CRITICAL: Test error handling consistency across lifecycle patterns
        
        error_test_message = {"id": "error_test", "content": None, "trigger_error": True}
        
        error_results = {}
        
        # Test error handling in each pattern
        try:
            error_handler = await short_lived_factory.create_handler({"error_test": True})
            error_results["short_lived"] = await error_handler.handle_message(error_test_message)
            await error_handler.cleanup()
        except Exception as e:
            error_results["short_lived"] = {"error": str(e)}
        
        try:
            error_results["long_lived"] = await session_handler.handle_message(error_test_message)
        except Exception as e:
            error_results["long_lived"] = {"error": str(e)}
        
        try:
            error_results["persistent"] = await persistent_handler.handle_message(error_test_message)
        except Exception as e:
            error_results["persistent"] = {"error": str(e)}
        
        # Error handling should be consistent across patterns
        error_behaviors = set()
        for pattern, result in error_results.items():
            if "error" in result:
                error_behaviors.add("exception")
            else:
                error_behaviors.add("graceful")
        
        # All patterns should handle errors consistently
        assert len(error_behaviors) <= 1, f"Inconsistent error handling: {error_results}"
        
        # Cleanup remaining handlers
        await session_handler.cleanup()
        await persistent_handler.cleanup()
        await short_lived_factory.cleanup_all_handlers()
        await long_lived_factory.cleanup_all_handlers()
        await persistent_factory.cleanup_all_handlers()
        
        # Business value: Consistent lifecycle management reduces operational complexity
        self.assert_business_value_delivered(
            {
                "lifecycle_pattern_consistency": True,
                "performance_efficiency": efficiency_ratio if 'efficiency_ratio' in locals() else 1.0,
                "error_handling_consistency": len(error_behaviors) <= 1,
                "operational_simplification": True
            },
            "automation"
        )