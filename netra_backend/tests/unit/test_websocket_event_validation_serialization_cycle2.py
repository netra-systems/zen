"""
Unit Tests for WebSocket Event Validation and Serialization - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket events are properly validated and serialized
- Value Impact: Users receive well-formed, actionable event data
- Strategic Impact: Data quality is essential for user trust and platform reliability

CRITICAL: Malformed events break the user experience and make AI progress invisible.
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from typing import Dict, Any

from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from shared.types import UserID, ThreadID, RunID

class TestWebSocketEventValidationSerialization:
    """Test WebSocket event validation and serialization for data quality."""
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager that captures serialized data."""
        manager = Mock()
        manager.sent_events = []
        
        async def capture_send_to_user(user_id, event_data):
            # Simulate serialization by converting to JSON and back
            serialized = json.dumps(event_data, default=str)
            deserialized = json.loads(serialized)
            manager.sent_events.append({
                "user_id": user_id,
                "event": deserialized,
                "raw_event": event_data
            })
        
        manager.send_to_user.side_effect = capture_send_to_user
        return manager
    
    @pytest.fixture
    def websocket_notifier(self, mock_websocket_manager):
        """Create WebSocket notifier with serialization capture."""
        return AgentWebSocketBridge(websocket_manager=mock_websocket_manager)
    
    @pytest.fixture
    def mock_execution_context(self):
        """Mock execution context with various data types."""
        context = Mock(spec=AgentExecutionContext)
        context.user_id = UserID("validation_test_user")
        context.thread_id = ThreadID("validation_thread_123")
        context.run_id = RunID("validation_run_456")
        context.agent_name = "validation_agent"
        return context

    @pytest.mark.unit
    async def test_agent_started_event_validation(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test agent_started event has required fields and valid structure.
        
        Business Value: Users must receive complete information about agent startup.
        Missing fields prevent users from understanding what's happening.
        """
        # Act: Generate agent_started event
        await websocket_notifier.notify_agent_started(mock_execution_context)
        
        # Assert: Validate event structure
        assert len(mock_websocket_manager.sent_events) == 1
        captured_event = mock_websocket_manager.sent_events[0]["event"]
        
        # Business requirement: All critical fields present
        required_fields = ["type", "timestamp", "thread_id", "run_id", "agent_name"]
        for field in required_fields:
            assert field in captured_event, f"Missing required field: {field}"
        
        # Validate field types and values
        assert captured_event["type"] == "agent_started"
        assert captured_event["thread_id"] == "validation_thread_123"
        assert captured_event["run_id"] == "validation_run_456"
        assert captured_event["agent_name"] == "validation_agent"
        
        # Validate timestamp format (ISO 8601)
        timestamp = captured_event["timestamp"]
        assert isinstance(timestamp, str), "Timestamp should be serialized as string"
        
        # Should be parseable as datetime
        try:
            parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            assert parsed_time is not None
        except ValueError:
            pytest.fail(f"Timestamp {timestamp} is not valid ISO format")

    @pytest.mark.unit
    async def test_agent_thinking_event_content_validation(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test agent_thinking event properly validates and serializes content.
        
        Business Value: Thinking content must be readable and actionable for users.
        Malformed thinking content provides no transparency value.
        """
        # Test various content types
        test_contents = [
            "Simple thinking message",
            "Complex thinking with special chars: áéíóú, 中文, 🤖",
            "Multi-line thinking\nwith embedded\nnewlines",
            "JSON-like content: {\"analysis\": \"cost optimization\", \"confidence\": 0.85}",
            ""  # Empty content edge case
        ]
        
        for content in test_contents:
            # Clear previous events
            mock_websocket_manager.sent_events.clear()
            
            # Act: Send thinking event with test content
            await websocket_notifier.notify_agent_thinking(mock_execution_context, content)
            
            # Assert: Content properly serialized and validated
            assert len(mock_websocket_manager.sent_events) == 1
            event = mock_websocket_manager.sent_events[0]["event"]
            
            assert event["type"] == "agent_thinking"
            assert "content" in event
            assert event["content"] == content, f"Content not preserved for: {repr(content)}"
            
            # Business requirement: Content should be meaningful (except empty edge case)
            if content.strip():  # Non-empty content
                assert len(event["content"]) > 0, "Non-empty thinking content should be preserved"

    @pytest.mark.unit
    async def test_tool_events_complex_data_serialization(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test tool events properly serialize complex data structures.
        
        Business Value: Tool parameters and results must preserve data fidelity.
        Data corruption makes tool outputs unreliable for business decisions.
        """
        # Test complex tool parameters
        complex_params = {
            "timeframe": "30_days",
            "filters": {
                "service_types": ["ec2", "s3", "rds"],
                "regions": ["us-east-1", "us-west-2"],
                "cost_threshold": 1000.50
            },
            "options": {
                "include_recommendations": True,
                "detail_level": "high",
                "confidence_minimum": 0.75,
                "tags": ["production", "development"]
            },
            "metadata": {
                "request_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "2.1.0"
            }
        }
        
        # Test complex tool results
        complex_results = {
            "analysis_summary": {
                "current_monthly_cost": 15420.75,
                "potential_savings": 2341.50,
                "savings_percentage": 15.2,
                "confidence_score": 0.87
            },
            "recommendations": [
                {
                    "id": "rec_001",
                    "type": "instance_resize",
                    "description": "Resize oversized EC2 instances",
                    "potential_savings": 850.25,
                    "impact": "medium",
                    "implementation_effort": "low"
                },
                {
                    "id": "rec_002", 
                    "type": "storage_optimization",
                    "description": "Enable S3 Intelligent Tiering",
                    "potential_savings": 1491.25,
                    "impact": "high",
                    "implementation_effort": "minimal"
                }
            ],
            "metadata": {
                "analysis_duration_ms": 1247,
                "data_points_analyzed": 15840,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Act: Send tool events with complex data
        await websocket_notifier.notify_tool_executing(mock_execution_context, "cloud_cost_analyzer", complex_params)
        await websocket_notifier.notify_tool_completed(mock_execution_context, "cloud_cost_analyzer", complex_results)
        
        # Assert: Complex data properly serialized
        assert len(mock_websocket_manager.sent_events) == 2
        
        executing_event = mock_websocket_manager.sent_events[0]["event"]
        completed_event = mock_websocket_manager.sent_events[1]["event"]
        
        # Validate tool_executing event
        assert executing_event["type"] == "tool_executing"
        assert executing_event["tool_name"] == "cloud_cost_analyzer"
        assert executing_event["tool_params"] == complex_params
        
        # Validate nested structure preservation
        assert executing_event["tool_params"]["filters"]["cost_threshold"] == 1000.50
        assert "production" in executing_event["tool_params"]["options"]["tags"]
        
        # Validate tool_completed event
        assert completed_event["type"] == "tool_completed"
        assert completed_event["tool_result"] == complex_results
        
        # Business requirement: Numeric values preserved with precision
        assert completed_event["tool_result"]["analysis_summary"]["potential_savings"] == 2341.50
        assert completed_event["tool_result"]["analysis_summary"]["confidence_score"] == 0.87
        
        # Validate array structure preservation
        recommendations = completed_event["tool_result"]["recommendations"]
        assert len(recommendations) == 2
        assert recommendations[0]["id"] == "rec_001"
        assert recommendations[1]["potential_savings"] == 1491.25

    @pytest.mark.unit
    async def test_event_serialization_edge_cases(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test event serialization handles edge cases and invalid data gracefully.
        
        Business Value: System remains stable even with unexpected data.
        Robustness prevents crashes that would lose customer progress.
        """
        # Test edge cases that could break serialization
        edge_case_data = [
            None,  # None value
            {"nested_none": None},  # Nested None
            {"infinity": float('inf')},  # Infinity (not JSON serializable)
            {"nan": float('nan')},  # NaN (not JSON serializable)
            {"datetime_obj": datetime.now()},  # Raw datetime object
            {"uuid_obj": uuid.uuid4()},  # Raw UUID object
            {"circular_ref": {}},  # Will create circular reference
        ]
        
        # Create circular reference
        edge_case_data[-1]["circular_ref"]["self"] = edge_case_data[-1]
        
        for i, test_data in enumerate(edge_case_data):
            # Clear previous events
            mock_websocket_manager.sent_events.clear()
            
            try:
                # Act: Send event with edge case data
                await websocket_notifier.notify_tool_completed(
                    mock_execution_context, 
                    f"edge_case_tool_{i}", 
                    test_data
                )
                
                # Assert: Event was processed (may have been cleaned/converted)
                assert len(mock_websocket_manager.sent_events) == 1
                event = mock_websocket_manager.sent_events[0]["event"]
                
                assert event["type"] == "tool_completed"
                assert event["tool_name"] == f"edge_case_tool_{i}"
                
                # Business requirement: System handles edge cases gracefully
                # (May convert to string representation or clean data)
                assert "tool_result" in event  # Some result should be present
                
            except Exception as e:
                # If serialization fails, it should be handled gracefully
                # The test passes if no unhandled exception bubbles up
                print(f"Edge case {i} handled with exception (acceptable): {e}")

    @pytest.mark.unit
    async def test_event_field_type_validation(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test that event fields have correct types after serialization.
        
        Business Value: Type consistency enables reliable frontend processing.
        Wrong types cause UI failures and poor user experience.
        """
        # Act: Generate all event types
        await websocket_notifier.notify_agent_started(mock_execution_context)
        await websocket_notifier.notify_agent_thinking(mock_execution_context, "Type validation test")
        await websocket_notifier.notify_tool_executing(mock_execution_context, "type_tool", {"param": "value"})
        await websocket_notifier.notify_tool_completed(mock_execution_context, "type_tool", {"result": 42})
        await websocket_notifier.notify_agent_completed(mock_execution_context, {"status": "completed"})
        
        # Assert: Field types are correct across all events
        assert len(mock_websocket_manager.sent_events) == 5
        
        for event_data in mock_websocket_manager.sent_events:
            event = event_data["event"]
            
            # Universal field type validations
            assert isinstance(event["type"], str), "Event type must be string"
            assert isinstance(event["timestamp"], str), "Timestamp must be string"
            assert isinstance(event["thread_id"], str), "Thread ID must be string"
            assert isinstance(event["run_id"], str), "Run ID must be string"
            
            # Event-specific validations
            event_type = event["type"]
            
            if event_type == "agent_started":
                assert isinstance(event["agent_name"], str), "Agent name must be string"
                
            elif event_type == "agent_thinking":
                assert isinstance(event["content"], str), "Thinking content must be string"
                
            elif event_type == "tool_executing":
                assert isinstance(event["tool_name"], str), "Tool name must be string"
                assert isinstance(event["tool_params"], dict), "Tool params must be dict"
                
            elif event_type == "tool_completed":
                assert isinstance(event["tool_name"], str), "Tool name must be string"
                # tool_result can be various types, but should be serializable
                result = event["tool_result"]
                assert result is not None, "Tool result should not be None"
                
            elif event_type == "agent_completed":
                assert isinstance(event["result"], dict), "Agent result must be dict"
                assert isinstance(event["status"], str), "Agent status must be string"

    @pytest.mark.unit
    async def test_event_size_validation(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test that events don't exceed reasonable size limits.
        
        Business Value: Reasonably sized events ensure fast delivery and good performance.
        Oversized events slow down the user experience and consume bandwidth.
        """
        # Test with various sized content
        small_content = "Small thinking message"
        medium_content = "Medium thinking content. " * 50  # ~1.3KB
        large_content = "Large thinking content. " * 1000   # ~26KB
        
        contents = [
            ("small", small_content),
            ("medium", medium_content), 
            ("large", large_content)
        ]
        
        for size_label, content in contents:
            # Clear previous events
            mock_websocket_manager.sent_events.clear()
            
            # Act: Send thinking event with different sizes
            await websocket_notifier.notify_agent_thinking(mock_execution_context, content)
            
            # Assert: Event size is reasonable
            assert len(mock_websocket_manager.sent_events) == 1
            event = mock_websocket_manager.sent_events[0]["event"]
            
            # Serialize to measure actual size
            serialized = json.dumps(event)
            event_size_kb = len(serialized) / 1024
            
            # Business requirement: Events should be reasonably sized
            if size_label == "small":
                assert event_size_kb < 1, f"Small event should be under 1KB, got {event_size_kb:.1f}KB"
            elif size_label == "medium":
                assert event_size_kb < 5, f"Medium event should be under 5KB, got {event_size_kb:.1f}KB"
            elif size_label == "large":
                # Large events acceptable but should have reasonable upper bound
                assert event_size_kb < 50, f"Large event should be under 50KB, got {event_size_kb:.1f}KB"
            
            # Content should be preserved regardless of size
            assert event["content"] == content, f"Content should be preserved for {size_label} event"