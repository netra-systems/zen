"""
MISSION CRITICAL: WebSocket JSON Requirements Test Suite

This test suite validates all specific requirements that the unified JSON handler
must support for WebSocket functionality. These are the requirements that MUST
work or chat functionality will be broken.

CRITICAL REQUIREMENTS:
1. All 5 critical WebSocket events must serialize correctly
2. Message type conversion for frontend compatibility
3. DeepAgentState serialization must work reliably
4. Async serialization must not block event loop
5. Error recovery must provide fallback serialization
6. Performance must meet real-time requirements

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Reliability (unified JSON handling requirements)
- Value Impact: Defines requirements that unified handler must meet
- Strategic Impact: Requirements validation prevents regressions
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.state import DeepAgentState, OptimizationsResult, ActionPlanResult
from netra_backend.app.schemas.registry import WebSocketMessage, ServerMessage
from netra_backend.app.schemas.websocket_models import BaseWebSocketPayload
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.websocket_core.types import get_frontend_message_type
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestWebSocketJSONRequirements:
    """Test specific requirements for WebSocket JSON handling."""

    @pytest.fixture
    def websocket_manager(self):
        """Create WebSocket manager for requirements testing."""
        return WebSocketManager()

    def test_requirement_1_critical_event_types_serialization(self, websocket_manager):
        """REQUIREMENT 1: All 5 critical WebSocket events must serialize correctly."""
        
        # The 5 critical events that MUST work
        critical_events = {
            "agent_started": {
                "type": "agent_started",
                "payload": {
                    "agent_name": "test_agent",
                    "run_id": "run_123",
                    "timestamp": datetime.now(timezone.utc).timestamp()
                }
            },
            "agent_thinking": {
                "type": "agent_thinking", 
                "payload": {
                    "thought": "Analyzing the user's request...",
                    "agent_name": "test_agent",
                    "step_number": 1,
                    "timestamp": datetime.now(timezone.utc).timestamp()
                }
            },
            "tool_executing": {
                "type": "tool_executing",
                "payload": {
                    "tool_name": "data_analyzer",
                    "agent_name": "test_agent",
                    "timestamp": datetime.now(timezone.utc).timestamp()
                }
            },
            "tool_completed": {
                "type": "tool_completed",
                "payload": {
                    "tool_name": "data_analyzer",
                    "agent_name": "test_agent",
                    "result": {"status": "success", "data": [1, 2, 3]},
                    "timestamp": datetime.now(timezone.utc).timestamp()
                }
            },
            "agent_completed": {
                "type": "agent_completed",
                "payload": {
                    "agent_name": "test_agent",
                    "run_id": "run_123", 
                    "result": {"summary": "Analysis complete", "confidence": 0.95},
                    "duration_ms": 5000.0,
                    "timestamp": datetime.now(timezone.utc).timestamp()
                }
            }
        }
        
        for event_name, event_data in critical_events.items():
            # REQUIREMENT: Must serialize without errors
            result = websocket_manager._serialize_message_safely(event_data)
            assert isinstance(result, dict), f"{event_name} did not serialize to dict"
            
            # REQUIREMENT: Must be JSON serializable
            try:
                json_str = json.dumps(result)
                assert len(json_str) > 0, f"{event_name} produced empty JSON"
            except (TypeError, ValueError) as e:
                pytest.fail(f"CRITICAL FAILURE: {event_name} is not JSON serializable: {e}")
            
            # REQUIREMENT: Must preserve event type
            assert result["type"] == event_name, f"{event_name} type was not preserved"
            
            # REQUIREMENT: Must preserve payload structure
            assert "payload" in result, f"{event_name} payload was lost"
            assert isinstance(result["payload"], dict), f"{event_name} payload is not dict"

    def test_requirement_2_message_type_conversion(self, websocket_manager):
        """REQUIREMENT 2: Message type conversion for frontend compatibility."""
        
        # Backend message types that need conversion
        backend_to_frontend_mappings = [
            ("agent_status_update", get_frontend_message_type("agent_status_update")),
            ("tool_execution_started", get_frontend_message_type("tool_execution_started")),
            ("sub_agent_completed", get_frontend_message_type("sub_agent_completed")),
            ("optimization_result_ready", get_frontend_message_type("optimization_result_ready"))
        ]
        
        for backend_type, expected_frontend_type in backend_to_frontend_mappings:
            message = {"type": backend_type, "payload": {"test": "data"}}
            
            # REQUIREMENT: Backend types must be converted to frontend types
            result = websocket_manager._serialize_message_safely(message)
            assert result["type"] == expected_frontend_type, \
                f"Backend type {backend_type} was not converted to {expected_frontend_type}, got {result['type']}"

    def test_requirement_3_deep_agent_state_serialization(self, websocket_manager):
        """REQUIREMENT 3: DeepAgentState serialization must work reliably."""
        
        # Create comprehensive DeepAgentState with all possible fields
        deep_state = DeepAgentState(
            user_request="Comprehensive optimization analysis",
            chat_thread_id="thread_abc",
            user_id="user_123",
            run_id="run_456",
            optimizations_result=OptimizationsResult(
                optimization_type="cost_optimization",
                recommendations=["Use reserved instances", "Implement auto-scaling"],
                cost_savings=1500.0,
                performance_improvement=25.0,
                confidence_score=0.9
            ),
            action_plan_result=ActionPlanResult(
                action_plan_summary="Implementation plan for optimizations",
                total_estimated_time="4 weeks",
                required_approvals=["Manager", "Finance"],
                actions=[{"id": 1, "action": "Phase 1", "priority": "high"}]
            ),
            final_report="Analysis complete with recommendations",
            step_count=10,
            messages=[
                {"role": "user", "content": "Please analyze costs"},
                {"role": "assistant", "content": "I'll analyze your cost structure"}
            ]
        )
        
        # REQUIREMENT: DeepAgentState must serialize completely
        result = websocket_manager._serialize_message_safely(deep_state)
        assert isinstance(result, dict), "DeepAgentState did not serialize to dict"
        
        # REQUIREMENT: Must be JSON serializable
        json_str = json.dumps(result)
        deserialized = json.loads(json_str)
        
        # REQUIREMENT: All critical fields must be preserved
        assert deserialized["user_request"] == "Comprehensive optimization analysis"
        assert deserialized["run_id"] == "run_456"
        assert deserialized["step_count"] == 10
        
        # REQUIREMENT: Complex nested objects must be preserved
        assert "optimizations_result" in deserialized
        assert deserialized["optimizations_result"]["cost_savings"] == 1500.0
        assert "action_plan_result" in deserialized
        assert len(deserialized["messages"]) == 2

    @pytest.mark.asyncio
    async def test_requirement_4_async_serialization_no_blocking(self, websocket_manager):
        """REQUIREMENT 4: Async serialization must not block event loop."""
        
        # Create a moderately complex message
        complex_message = DeepAgentState(
            user_request="Test async serialization",
            run_id="async_test",
            optimizations_result=OptimizationsResult(
                optimization_type="test",
                recommendations=[f"Recommendation {i}" for i in range(100)],
                cost_savings=1000.0
            ),
            messages=[{"role": "user", "content": f"Message {i}"} for i in range(100)]
        )
        
        # REQUIREMENT: Async operation must not block
        start_time = time.time()
        
        # Run async serialization alongside other async work
        async def other_async_work():
            for _ in range(10):
                await asyncio.sleep(0.01)  # Simulate other async work
            return "other_work_complete"
        
        # Both should run concurrently
        serialization_task = websocket_manager._serialize_message_safely_async(complex_message)
        other_work_task = other_async_work()
        
        results = await asyncio.gather(serialization_task, other_work_task)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # REQUIREMENT: Should complete quickly without blocking
        assert duration < 2.0, f"Async serialization blocked for {duration:.2f}s"
        
        # REQUIREMENT: Both tasks should complete
        serialization_result, other_work_result = results
        assert isinstance(serialization_result, dict)
        assert other_work_result == "other_work_complete"

    def test_requirement_5_error_recovery_fallback_serialization(self, websocket_manager):
        """REQUIREMENT 5: Error recovery must provide fallback serialization."""
        
        # Create objects that will fail serialization
        class FailingPydanticModel:
            def model_dump(self, **kwargs):
                raise ValueError("model_dump failed")
            
            def to_dict(self):
                raise RuntimeError("to_dict failed")
            
            def dict(self):
                raise TypeError("dict failed")
            
            def __str__(self):
                return "FailingPydanticModel instance"
        
        class UnserializableObject:
            def __init__(self):
                # This will cause JSON serialization to fail
                self.circular_ref = self
            
            def __str__(self):
                return "UnserializableObject"
        
        failing_objects = [
            FailingPydanticModel(),
            UnserializableObject(),
            lambda x: x,  # Function (not JSON serializable)
            type("DynamicClass", (), {})(),  # Dynamic class instance
        ]
        
        for failing_obj in failing_objects:
            # REQUIREMENT: Must not crash, must provide fallback
            result = websocket_manager._serialize_message_safely(failing_obj)
            
            # REQUIREMENT: Must return a dict
            assert isinstance(result, dict), f"Fallback did not return dict for {type(failing_obj)}"
            
            # REQUIREMENT: Must be JSON serializable
            json_str = json.dumps(result)
            assert len(json_str) > 0
            
            # REQUIREMENT: Must indicate serialization error
            assert "serialization_error" in result or "payload" in result

    @pytest.mark.asyncio
    async def test_requirement_6_performance_real_time_requirements(self, websocket_manager):
        """REQUIREMENT 6: Performance must meet real-time requirements."""
        
        # Real-time chat requires fast serialization
        chat_messages = [
            {"type": "agent_thinking", "payload": {"thought": f"Thinking about step {i}"}},
            {"type": "tool_executing", "payload": {"tool_name": f"tool_{i}"}},
            {"type": "agent_update", "payload": {"progress": i / 100}},
        ] * 10  # 30 messages total
        
        # REQUIREMENT: Batch serialization must complete quickly
        start_time = time.time()
        
        # Serialize all messages
        results = []
        for msg in chat_messages:
            result = websocket_manager._serialize_message_safely(msg)
            results.append(result)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # REQUIREMENT: Must serialize 30 messages in under 1 second
        assert duration < 1.0, f"Batch serialization took {duration:.2f}s, should be < 1s"
        
        # REQUIREMENT: All messages must serialize successfully
        assert len(results) == 30
        
        # REQUIREMENT: All results must be JSON serializable
        for i, result in enumerate(results):
            json.dumps(result)  # Should not raise
            assert isinstance(result, dict)

    def test_requirement_7_websocket_message_model_compatibility(self, websocket_manager):
        """REQUIREMENT 7: Must work with existing WebSocket message models."""
        
        # Test with actual WebSocket message models
        websocket_messages = [
            WebSocketMessage(
                type="agent_update",
                payload={"agent_name": "test", "status": "running"}
            ),
            ServerMessage(
                type="server_notification",
                payload={"message": "System maintenance scheduled"}
            ),
            BaseWebSocketPayload()
        ]
        
        for msg in websocket_messages:
            # REQUIREMENT: Must serialize Pydantic models correctly
            result = websocket_manager._serialize_message_safely(msg)
            
            # REQUIREMENT: Must be dict
            assert isinstance(result, dict), f"Failed to serialize {type(msg)} to dict"
            
            # REQUIREMENT: Must be JSON serializable
            json_str = json.dumps(result)
            deserialized = json.loads(json_str)
            
            # REQUIREMENT: Must preserve structure
            if hasattr(msg, 'type'):
                assert "type" in deserialized
            if hasattr(msg, 'payload'):
                assert "payload" in deserialized

    def test_requirement_8_unicode_and_special_characters(self, websocket_manager):
        """REQUIREMENT 8: Must handle unicode and special characters correctly."""
        
        # Messages with various international characters and emojis
        unicode_messages = [
            {
                "type": "agent_message",
                "payload": {
                    "content": "Analysis complete!  CELEBRATION:  Results: [U+00E1][U+00E9][U+00ED][U+00F3][U+00FA] [U+00F1] [U+00E7][U+00C7]",
                    "languages": ["English", "Espa[U+00F1]ol", "Fran[U+00E7]ais", "Deutsch", "[U+4E2D][U+6587]", "[U+65E5][U+672C][U+8A9E]", "[U+0627][U+0644][U+0639][U+0631][U+0628][U+064A][U+0629]", "Pucck[U+0438][U+0439]"],
                    "emojis": ["[U+1F680]", " IDEA: ", " LIGHTNING: ", "[U+1F31F]", "[U+1F527]", " CHART: "],
                    "special_chars": ["@", "#", "$", "%", "^", "&", "*", "(", ")", "[", "]", "{", "}"]
                }
            },
            {
                "type": "multilingual_response",
                "payload": {
                    "messages": {
                        "en": "Hello World",
                        "es": "Hola Mundo", 
                        "fr": "Bonjour le Monde",
                        "zh": "[U+4F60][U+597D][U+4E16][U+754C]",
                        "ja": "[U+3053][U+3093][U+306B][U+3061][U+306F][U+4E16][U+754C]",
                        "ar": "[U+0645][U+0631][U+062D][U+0628][U+0627] [U+0628][U+0627][U+0644][U+0639][U+0627][U+0644][U+0645]",
                        "ru": "[U+041F]p[U+0438]vet m[U+0438]p"
                    }
                }
            }
        ]
        
        for msg in unicode_messages:
            # REQUIREMENT: Must handle unicode correctly
            result = websocket_manager._serialize_message_safely(msg)
            
            # REQUIREMENT: Must be JSON serializable with unicode
            json_str = json.dumps(result, ensure_ascii=False)
            deserialized = json.loads(json_str)
            
            # REQUIREMENT: Unicode characters must be preserved
            if "content" in deserialized.get("payload", {}):
                assert " CELEBRATION: " in deserialized["payload"]["content"]
                assert "[U+00E1][U+00E9][U+00ED][U+00F3][U+00FA]" in deserialized["payload"]["content"]

    def test_requirement_9_datetime_serialization_consistency(self, websocket_manager):
        """REQUIREMENT 9: DateTime serialization must be consistent."""
        
        now = datetime.now(timezone.utc)
        messages_with_dates = [
            {
                "type": "timestamped_event",
                "payload": {
                    "timestamp": now,
                    "created_at": now.isoformat(),
                    "unix_timestamp": now.timestamp(),
                    "date_array": [now, datetime(2024, 1, 1, tzinfo=timezone.utc)]
                }
            }
        ]
        
        for msg in messages_with_dates:
            # REQUIREMENT: Must serialize datetime objects
            result = websocket_manager._serialize_message_safely(msg)
            
            # REQUIREMENT: Must be JSON serializable
            json_str = json.dumps(result)
            deserialized = json.loads(json_str)
            
            # REQUIREMENT: Timestamps must be preserved in some form
            payload = deserialized["payload"]
            assert "timestamp" in payload
            assert "created_at" in payload
            assert isinstance(payload["unix_timestamp"], (int, float))

    def test_requirement_10_large_message_handling(self, websocket_manager):
        """REQUIREMENT 10: Must handle large messages gracefully."""
        
        # Create large message (100KB content)
        large_content = "x" * 100000
        large_message = {
            "type": "large_data_transfer",
            "payload": {
                "large_content": large_content,
                "metadata": {
                    "size": len(large_content),
                    "type": "bulk_data",
                    "compression": "none"
                }
            }
        }
        
        # REQUIREMENT: Must handle large messages
        result = websocket_manager._serialize_message_safely(large_message)
        
        # REQUIREMENT: Must be JSON serializable
        json_str = json.dumps(result)
        
        # REQUIREMENT: Content must be preserved
        deserialized = json.loads(json_str)
        assert len(deserialized["payload"]["large_content"]) == 100000

    @pytest.mark.asyncio
    async def test_requirement_11_concurrent_serialization_safety(self, websocket_manager):
        """REQUIREMENT 11: Must be thread-safe for concurrent serialization."""
        
        # Create multiple different messages
        different_messages = [
            {"type": "message_1", "payload": {"data": i}} for i in range(20)
        ]
        
        # REQUIREMENT: Concurrent async serialization must be safe
        tasks = [
            websocket_manager._serialize_message_safely_async(msg)
            for msg in different_messages
        ]
        
        results = await asyncio.gather(*tasks)
        
        # REQUIREMENT: All must succeed
        assert len(results) == 20
        
        # REQUIREMENT: Results must be correct and not mixed up
        for i, result in enumerate(results):
            assert result["payload"]["data"] == i

    def test_requirement_12_error_information_preservation(self, websocket_manager):
        """REQUIREMENT 12: Error information must be preserved for debugging."""
        
        class DetailedFailureObject:
            def model_dump(self, **kwargs):
                raise ValueError("Specific serialization failure with context")
            
            def __str__(self):
                return "DetailedFailureObject with important context"
        
        failing_obj = DetailedFailureObject()
        
        # REQUIREMENT: Error details must be preserved
        result = websocket_manager._serialize_message_safely(failing_obj)
        
        # REQUIREMENT: Must include error information
        assert "serialization_error" in result or "error" in str(result)
        
        # REQUIREMENT: Must be JSON serializable for error reporting
        json.dumps(result)
        
        # REQUIREMENT: Original object information should be preserved
        result_str = str(result)
        assert "DetailedFailureObject" in result_str or "important context" in result_str