"""
Critical regression tests for DeepAgentState JSON serialization.

This test suite ensures that DeepAgentState objects can be properly serialized
to JSON for WebSocket transmission, preventing the error:
"Object of type DeepAgentState is not JSON serializable"

Issue fixed: 2025-08-27
Error location: netra_backend.app.websocket_core.manager:_send_to_connection:337
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
from pydantic import BaseModel

from netra_backend.app.agents.state import (
    ActionPlanResult,
    AgentMetadata,
    DeepAgentState,
    OptimizationsResult,
    ReportResult,
    ReportSection,
    SupplyResearchResult,
    SyntheticDataResult,
)
from netra_backend.app.schemas.agent_models import AgentResult
from netra_backend.app.schemas.agent_models import DeepAgentState as SchemaDeepAgentState


class TestDeepAgentStateSerialization:
    """Test suite for DeepAgentState JSON serialization."""

    def test_basic_deep_agent_state_serialization(self):
        """Test that a basic DeepAgentState can be JSON serialized."""
        state = DeepAgentState(
            user_request="Test serialization",
            chat_thread_id="thread-123",
            user_id="user-456"
        )
        
        # The to_dict() method should return a JSON-serializable dict
        state_dict = state.to_dict()
        
        # This should not raise TypeError
        json_str = json.dumps(state_dict)
        
        # Verify we can parse it back
        parsed = json.loads(json_str)
        assert parsed["user_request"] == "Test serialization"
        assert parsed["chat_thread_id"] == "thread-123"
        assert parsed["user_id"] == "user-456"

    def test_deep_agent_state_with_datetime_metadata(self):
        """Test that DeepAgentState with datetime in metadata serializes correctly."""
        state = DeepAgentState(user_request="Test with datetime")
        
        # Access datetime fields to ensure they're populated
        assert state.metadata.created_at is not None
        assert state.metadata.last_updated is not None
        assert isinstance(state.metadata.created_at, datetime)
        assert isinstance(state.metadata.last_updated, datetime)
        
        # Serialize to dict
        state_dict = state.to_dict()
        
        # Should not raise TypeError
        json_str = json.dumps(state_dict)
        
        # Parse back and verify datetime fields are strings
        parsed = json.loads(json_str)
        assert "metadata" in parsed
        assert "created_at" in parsed["metadata"]
        assert "last_updated" in parsed["metadata"]
        assert isinstance(parsed["metadata"]["created_at"], str)
        assert isinstance(parsed["metadata"]["last_updated"], str)

    def test_deep_agent_state_with_report_result(self):
        """Test serialization with ReportResult containing datetime."""
        report = ReportResult(
            report_type="analysis",
            content="Test report content",
            sections=[
                ReportSection(
                    section_id="section-1",
                    title="Section 1",
                    content="Content"
                )
            ]
        )
        
        state = DeepAgentState(
            user_request="Test with report",
            report_result=report
        )
        
        # The report has a generated_at datetime field
        assert report.generated_at is not None
        assert isinstance(report.generated_at, datetime)
        
        # Serialize
        state_dict = state.to_dict()
        json_str = json.dumps(state_dict)
        
        # Verify
        parsed = json.loads(json_str)
        assert "report_result" in parsed
        assert "generated_at" in parsed["report_result"]
        assert isinstance(parsed["report_result"]["generated_at"], str)

    def test_deep_agent_state_with_all_result_types(self):
        """Test serialization with all possible result types populated."""
        state = DeepAgentState(
            user_request="Full test",
            optimizations_result=OptimizationsResult(
                optimization_type="cost",
                recommendations=["rec1"],
                cost_savings=100.0,
                performance_improvement=10.0
            ),
            action_plan_result=ActionPlanResult(
                action_plan_summary="Test action plan",
                total_estimated_time="1h",
                actions=[{"step": "action1", "description": "Do something"}]
            ),
            report_result=ReportResult(
                report_type="summary",
                content="Report content"
            ),
            synthetic_data_result=SyntheticDataResult(
                data_type="test",
                generation_method="random",
                sample_count=10
            ),
            supply_research_result=SupplyResearchResult(
                research_scope="test scope",
                findings=["finding1"],
                confidence_level=0.9
            )
        )
        
        # All fields should serialize
        state_dict = state.to_dict()
        json_str = json.dumps(state_dict)
        
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["optimizations_result"]["cost_savings"] == 100.0
        assert parsed["action_plan_result"]["total_estimated_time"] == "1h"
        assert parsed["report_result"]["report_type"] == "summary"
        assert parsed["synthetic_data_result"]["sample_count"] == 10
        assert parsed["supply_research_result"]["confidence_level"] == 0.9

    def test_schema_deep_agent_state_serialization(self):
        """Test that the schema version of DeepAgentState also serializes correctly."""
        state = SchemaDeepAgentState(
            user_request="Schema test",
            chat_thread_id="thread-789"
        )
        
        # Should have datetime metadata
        assert state.metadata.created_at is not None
        
        # Serialize
        state_dict = state.to_dict()
        json_str = json.dumps(state_dict)
        
        # Verify
        parsed = json.loads(json_str)
        assert parsed["user_request"] == "Schema test"
        assert isinstance(parsed["metadata"]["created_at"], str)

    def test_agent_result_with_deep_agent_state(self):
        """Test the pipeline executor flow: AgentResult containing DeepAgentState dict."""
        state = DeepAgentState(
            user_request="Pipeline test",
            user_id="user-123"
        )
        
        # Simulate pipeline executor flow
        result = AgentResult(
            success=True,
            output=state.to_dict()  # This is how pipeline_executor uses it
        )
        
        # Get the dict for WebSocket transmission
        result_dict = result.model_dump()
        
        # Should serialize without errors
        json_str = json.dumps(result_dict)
        
        # Verify
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["output"]["user_request"] == "Pipeline test"

    @pytest.mark.asyncio
    async def test_websocket_message_flow(self):
        """Test the complete WebSocket message flow with DeepAgentState."""
        from netra_backend.app.schemas.websocket_models import WebSocketMessage
        
        state = DeepAgentState(
            user_request="WebSocket test",
            chat_thread_id="ws-thread-123"
        )
        
        # Create completion message as in pipeline_executor
        from netra_backend.app.schemas.agent import AgentCompleted
        
        result = AgentResult(success=True, output=state.to_dict())
        content = AgentCompleted(
            run_id="run-123",
            result=result,
            execution_time_ms=100.0
        )
        
        # Create WebSocket message
        ws_message = WebSocketMessage(
            type="agent_completed",
            payload=content.model_dump(mode='json')  # Use mode='json' for datetime conversion
        )
        
        # This is what gets sent through WebSocket
        message_dict = ws_message.model_dump(mode='json')  # Use mode='json' here too
        
        # Should serialize without errors
        json_str = json.dumps(message_dict)
        
        # Verify the structure
        parsed = json.loads(json_str)
        assert parsed["type"] == "agent_completed"
        assert parsed["payload"]["run_id"] == "run-123"
        assert parsed["payload"]["result"]["success"] is True
        assert parsed["payload"]["result"]["output"]["user_request"] == "WebSocket test"

    def test_nested_metadata_serialization(self):
        """Test that nested metadata with datetime fields serializes correctly."""
        metadata = AgentMetadata(
            execution_context={"test": "context"},
            custom_fields={"field": "value"},
            priority=5,
            retry_count=2,
            parent_agent_id="parent-123",
            tags=["tag1", "tag2"]
        )
        
        state = DeepAgentState(
            user_request="Metadata test",
            metadata=metadata
        )
        
        # Verify datetime fields exist
        assert metadata.created_at is not None
        assert metadata.last_updated is not None
        
        # Serialize
        state_dict = state.to_dict()
        json_str = json.dumps(state_dict)
        
        # Parse and verify
        parsed = json.loads(json_str)
        assert parsed["metadata"]["priority"] == 5
        assert parsed["metadata"]["retry_count"] == 2
        assert parsed["metadata"]["tags"] == ["tag1", "tag2"]
        assert isinstance(parsed["metadata"]["created_at"], str)
        assert isinstance(parsed["metadata"]["last_updated"], str)

    def test_empty_state_serialization(self):
        """Test that even an empty/minimal DeepAgentState serializes correctly."""
        # Use default values
        state = DeepAgentState()
        
        # Should still serialize
        state_dict = state.to_dict()
        json_str = json.dumps(state_dict)
        
        # Verify defaults
        parsed = json.loads(json_str)
        assert parsed["user_request"] == "default_request"
        assert parsed["step_count"] == 0
        assert parsed["messages"] == []

    def test_model_dump_mode_json_behavior(self):
        """Test that model_dump with mode='json' properly converts datetime."""
        state = DeepAgentState(user_request="mode test")
        
        # Without mode='json' (this would fail in real WebSocket transmission)
        dict_without_mode = state.model_dump(exclude_none=True)
        
        # With mode='json' (our fix)
        dict_with_mode = state.model_dump(exclude_none=True, mode='json')
        
        # The one without mode has datetime objects
        assert isinstance(dict_without_mode["metadata"]["created_at"], datetime)
        
        # The one with mode='json' has strings
        assert isinstance(dict_with_mode["metadata"]["created_at"], str)
        
        # Only the one with mode='json' should be JSON serializable
        json.dumps(dict_with_mode)  # Should work
        
        with pytest.raises(TypeError, match="Object of type datetime is not JSON serializable"):
            json.dumps(dict_without_mode)  # Should fail

    def test_copy_with_updates_preserves_serializability(self):
        """Test that copy_with_updates maintains JSON serializability."""
        original = DeepAgentState(user_request="original")
        
        # Create a copy with updates
        updated = original.copy_with_updates(
            user_request="updated",
            chat_thread_id="new-thread"
        )
        
        # Should still be serializable
        updated_dict = updated.to_dict()
        json_str = json.dumps(updated_dict)
        
        # Verify updates
        parsed = json.loads(json_str)
        assert parsed["user_request"] == "updated"
        assert parsed["chat_thread_id"] == "new-thread"

    @pytest.mark.parametrize("state_class", [DeepAgentState, SchemaDeepAgentState])
    def test_both_deep_agent_state_classes(self, state_class):
        """Test that both versions of DeepAgentState serialize correctly."""
        state = state_class(
            user_request="Parameterized test",
            user_id="user-999"
        )
        
        # Both should have to_dict() that returns JSON-serializable data
        state_dict = state.to_dict()
        json_str = json.dumps(state_dict)
        
        # Verify
        parsed = json.loads(json_str)
        assert parsed["user_request"] == "Parameterized test"
        assert parsed["user_id"] == "user-999"

    def test_regression_prevention_for_websocket_error(self):
        """
        Regression test for the specific error:
        2025-08-27 22:45:47.043 | ERROR | netra_backend.app.websocket_core.manager:_send_to_connection:337
        Error sending to connection conn_dev-temp-df9fae96_e3398d5d: Object of type DeepAgentState is not JSON serializable
        """
        # Create state that would have caused the error
        state = DeepAgentState(
            user_request="Regression test for WebSocket error",
            chat_thread_id="thread-regression",
            user_id="user-regression"
        )
        
        # Add metadata with datetime
        state.metadata = AgentMetadata(
            created_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
            execution_context={"test": "regression"}
        )
        
        # The fix ensures to_dict() returns JSON-serializable data
        state_dict = state.to_dict()
        
        # This should NOT raise: "Object of type DeepAgentState is not JSON serializable"
        try:
            json_str = json.dumps(state_dict)
            success = True
        except TypeError as e:
            if "DeepAgentState" in str(e) and "not JSON serializable" in str(e):
                success = False
                raise AssertionError(f"Regression detected: {e}")
            raise
        
        assert success, "DeepAgentState should be JSON serializable after fix"
        
        # Verify the serialized data is valid
        parsed = json.loads(json_str)
        assert parsed["user_request"] == "Regression test for WebSocket error"