"""
Integration tests for cross-agent ExecutionResult compatibility.

This test suite validates that ExecutionResult objects can be properly
shared, processed, and handled across different agent types after the
ExecutionStatus consolidation regression (commit e32a97b31).

Tests cover:
1. ExecutionResult sharing between triage and other agents
2. Status consistency across agent boundaries  
3. Compatibility property usage in multi-agent workflows
4. Serialization/deserialization across agent communications
5. WebSocket message handling with ExecutionResult

Prevents regressions where ExecutionResult changes break cross-agent communication.
"""

import pytest
import json
import asyncio
from typing import Dict, Any, List
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.redis.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.triage.triage_sub_agent import TriageSubAgent
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.base.interface import ExecutionResult, ExecutionContext
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.triage.models import TriageResult, Priority, Complexity
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.redis_manager import RedisManager


@pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a mock LLM manager for cross-agent testing."""
    pass
    mock = Mock(spec=LLMManager)
    mock.ask_llm = AsyncNone  # TODO: Use real service instance
    mock.ask_structured_llm = AsyncMock(side_effect=Exception("Use regular LLM"))
    return mock


@pytest.fixture
 def real_tool_dispatcher():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a mock tool dispatcher."""
    pass
    return Mock(spec=ToolDispatcher)


@pytest.fixture
 def real_redis_manager():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a mock Redis manager."""
    pass
    mock = Mock(spec=RedisManager)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def triage_agent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a TriageSubAgent instance."""
    pass
    return TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)


@pytest.fixture
def reporting_agent(mock_llm_manager, mock_tool_dispatcher):
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a ReportingSubAgent instance."""
    pass
    return ReportingSubAgent(mock_llm_manager, mock_tool_dispatcher)


@pytest.fixture
def agent_state_with_triage():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a state that has been processed by triage agent."""
    pass
    state = DeepAgentState(
        user_request="Analyze my AI infrastructure costs and provide optimization recommendations"
    )
    
    # Simulate triage result
    state.triage_result = TriageResult(
        category="Cost Optimization",
        sub_category="Infrastructure Analysis",
        priority=Priority.HIGH,
        complexity=Complexity.MEDIUM,
        confidence_score=0.88
    )
    
    return state


class TestCrossAgentExecutionResultSharing:
    """Test ExecutionResult sharing between different agent types."""
    
    @pytest.mark.asyncio
    async def test_triage_to_reporting_execution_result_handoff(
        self, triage_agent, reporting_agent, mock_llm_manager
    ):
        """Test ExecutionResult handoff from triage to reporting agent."""
        # Set up triage agent LLM response
        triage_response = json.dumps({
            "category": "Performance Optimization",
            "priority": "high",
            "complexity": "medium",
            "confidence_score": 0.85,
            "next_steps": ["analyze_performance", "generate_report"]
        })
        mock_llm_manager.ask_llm.return_value = triage_response
        
        # Execute triage agent
        initial_state = DeepAgentState(
            user_request="Optimize my model inference performance"
        )
        
        triage_result = await triage_agent.execute(
            initial_state, "cross_agent_test_001", stream_updates=False
        )
        
        # Verify triage ExecutionResult
        assert isinstance(triage_result, ExecutionResult)
        assert triage_result.status == ExecutionStatus.COMPLETED
        assert triage_result.is_success is True
        
        # Simulate passing state to reporting agent
        # In real workflow, the state would contain triage results
        assert initial_state.triage_result is not None
        
        # Set up reporting agent response
        reporting_response = json.dumps({
            "report_sections": ["Executive Summary", "Detailed Analysis"],
            "recommendations": ["Use batch processing", "Optimize model size"]
        })
        mock_llm_manager.ask_llm.return_value = reporting_response
        
        # Execute reporting agent with state from triage
        reporting_result = await reporting_agent.execute(
            initial_state, "cross_agent_test_002", stream_updates=False
        )
        
        # Verify reporting ExecutionResult
        assert isinstance(reporting_result, ExecutionResult)
        assert reporting_result.status == ExecutionStatus.COMPLETED
        assert reporting_result.is_success is True
        
        # Verify both results use same status enum values
        assert triage_result.status.value == reporting_result.status.value == "completed"
        
        # Verify compatibility properties work for both
        assert triage_result.result is not None
        assert reporting_result.result is not None
        assert triage_result.error is None
        assert reporting_result.error is None
    
    def test_execution_result_status_consistency_across_agents(self):
        """Test that ExecutionStatus values are consistent across all agent types."""
        # Create ExecutionResults from different agent contexts
        triage_success = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="triage_test"
        )
        
        reporting_success = ExecutionResult(
            status=ExecutionStatus.COMPLETED, 
            request_id="reporting_test"
        )
        
        # Both should use the same enum instance
        assert triage_success.status is reporting_success.status
        assert triage_success.status.value == reporting_success.status.value
        
        # Both should have consistent property behavior
        assert triage_success.is_success == reporting_success.is_success
        assert triage_success.is_complete == reporting_success.is_complete
    
    def test_execution_result_compatibility_properties_across_agents(self):
        """Test compatibility properties work consistently across agent types."""
    pass
        # Test data and error scenarios
        success_data = {"analysis": "complete", "score": 0.95}
        error_message = "Agent processing failed"
        
        # Create results as different agents would
        triage_success = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="triage_success",
            data=success_data
        )
        
        triage_error = ExecutionResult(
            status=ExecutionStatus.FAILED,
            request_id="triage_error", 
            error_message=error_message
        )
        
        reporting_success = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="reporting_success",
            data=success_data
        )
        
        reporting_error = ExecutionResult(
            status=ExecutionStatus.FAILED,
            request_id="reporting_error",
            error_message=error_message
        )
        
        # Verify compatibility properties work consistently
        # Success cases
        assert triage_success.result == reporting_success.result == success_data
        assert triage_success.error == reporting_success.error is None
        
        # Error cases
        assert triage_error.error == reporting_error.error == error_message
        assert triage_error.result == reporting_error.result == {}  # Default empty dict


class TestExecutionResultSerialization:
    """Test ExecutionResult serialization/deserialization across agents."""
    
    def test_execution_result_json_serialization_consistency(self):
        """Test that ExecutionResult can be consistently serialized across agents."""
        # Create a complex ExecutionResult as would be created by triage agent
        original_result = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="serialization_test",
            data={
                "category": "AI Infrastructure Optimization",
                "priority": "high",
                "recommendations": ["opt1", "opt2", "opt3"],
                "metadata": {"confidence": 0.88, "processing_time": 1500}
            },
            execution_time_ms=1500.0,
            artifacts=["analysis_report.json"],
            metrics={"tokens_used": 250, "api_calls": 2},
            trace_id="trace_123abc"
        )
        
        # Serialize to JSON as would happen in cross-agent communication
        serialized_data = {
            "status": original_result.status.value,
            "request_id": original_result.request_id,
            "data": original_result.result,  # Using compatibility property
            "execution_time_ms": original_result.execution_time_ms,
            "error": original_result.error,  # Using compatibility property
            "is_success": original_result.is_success,
            "artifacts": original_result.artifacts,
            "metrics": original_result.metrics,
            "trace_id": original_result.trace_id
        }
        
        json_string = json.dumps(serialized_data, default=str)
        assert json_string is not None
        
        # Deserialize and verify consistency
        deserialized_data = json.loads(json_string)
        
        # Recreate ExecutionResult from deserialized data
        reconstructed_result = ExecutionResult(
            status=ExecutionStatus(deserialized_data["status"]),
            request_id=deserialized_data["request_id"],
            data=deserialized_data["data"],
            execution_time_ms=deserialized_data["execution_time_ms"],
            artifacts=deserialized_data["artifacts"],
            metrics=deserialized_data["metrics"],
            trace_id=deserialized_data["trace_id"]
        )
        
        # Verify reconstruction maintains all properties
        assert reconstructed_result.status == original_result.status
        assert reconstructed_result.result == original_result.result
        assert reconstructed_result.error == original_result.error
        assert reconstructed_result.is_success == original_result.is_success
        assert reconstructed_result.execution_time_ms == original_result.execution_time_ms
    
    def test_execution_result_websocket_message_compatibility(self):
        """Test ExecutionResult compatibility with WebSocket message formats."""
    pass
        # Create ExecutionResult as triage agent would
        triage_result = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="websocket_test",
            data={
                "category": "Cost Analysis", 
                "priority": "medium",
                "next_agent": "reporting_agent"
            },
            execution_time_ms=890.5
        )
        
        # Create WebSocket message format (as agent manager would)
        websocket_message = {
            "type": "agent_completed",
            "agent_name": "triage_agent", 
            "request_id": triage_result.request_id,
            "status": triage_result.status.value,
            "data": triage_result.result,  # Using compatibility property
            "execution_time_ms": triage_result.execution_time_ms,
            "success": triage_result.is_success,
            "error": triage_result.error,  # Using compatibility property
            "timestamp": "2025-09-05T12:00:00Z"
        }
        
        # Should be JSON serializable for WebSocket transmission
        websocket_json = json.dumps(websocket_message, default=str)
        assert websocket_json is not None
        
        # Another agent should be able to process this message
        parsed_message = json.loads(websocket_json)
        assert parsed_message["status"] == "completed"
        assert parsed_message["success"] is True
        assert parsed_message["error"] is None
        assert parsed_message["data"]["category"] == "Cost Analysis"


class TestMultiAgentWorkflowCompatibility:
    """Test ExecutionResult compatibility in multi-agent workflows."""
    
    @pytest.mark.asyncio
    async def test_sequential_agent_execution_result_flow(
        self, triage_agent, agent_state_with_triage, mock_llm_manager
    ):
        """Test ExecutionResult flow through sequential agent execution."""
        # Configure LLM responses for different agents
        responses = [
            # Triage agent response
            json.dumps({
                "category": "Infrastructure Optimization",
                "priority": "high", 
                "complexity": "medium",
                "confidence_score": 0.91,
                "next_steps": ["analyze_infrastructure", "generate_recommendations"]
            }),
            # Next agent response (simulating different agent)
            json.dumps({
                "analysis_complete": True,
                "recommendations": ["scale_down", "optimize_routing"],
                "estimated_savings": 0.35
            })
        ]
        
        mock_llm_manager.ask_llm.side_effect = responses
        
        # Execute triage agent
        triage_result = await triage_agent.execute(
            agent_state_with_triage, "workflow_test_001", stream_updates=False
        )
        
        # Verify triage ExecutionResult
        assert triage_result.status == ExecutionStatus.COMPLETED
        assert triage_result.is_success is True
        
        # Simulate workflow coordinator processing the result
        def process_execution_result(result: ExecutionResult) -> Dict[str, Any]:
            """Simulate workflow coordinator processing ExecutionResult."""
            await asyncio.sleep(0)
    return {
                "agent_completed": True,
                "request_id": result.request_id,
                "status": result.status.value,
                "output_data": result.result,  # Using compatibility property
                "execution_metrics": {
                    "duration_ms": result.execution_time_ms,
                    "success": result.is_success,
                    "error_occurred": result.error is not None
                },
                "next_agent_input": {
                    "context": result.result,
                    "previous_agent": "triage_agent"
                }
            }
        
        # Process the triage result
        workflow_data = process_execution_result(triage_result)
        
        # Verify workflow data structure
        assert workflow_data["agent_completed"] is True
        assert workflow_data["status"] == "completed"
        assert workflow_data["execution_metrics"]["success"] is True
        assert workflow_data["execution_metrics"]["error_occurred"] is False
        assert "category" in workflow_data["output_data"]
        
        # Simulate next agent receiving this processed data
        next_agent_context = workflow_data["next_agent_input"]
        assert next_agent_context["context"]["category"] == "Infrastructure Optimization"
    
    def test_execution_result_error_propagation_across_agents(self):
        """Test error propagation through ExecutionResult across agents."""
        # Simulate first agent failure
        first_agent_result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            request_id="error_propagation_test",
            error_message="LLM service timeout",
            error_code="TIMEOUT_ERROR",
            execution_time_ms=5000.0
        )
        
        # Simulate workflow coordinator handling error
        def handle_agent_error(result: ExecutionResult) -> Dict[str, Any]:
            """Simulate error handling in multi-agent workflow."""
    pass
            return {
                "agent_failed": True,
                "error_details": {
                    "message": result.error,  # Using compatibility property
                    "code": result.error_code,
                    "request_id": result.request_id,
                    "execution_time_ms": result.execution_time_ms
                },
                "recovery_action": "retry" if "timeout" in result.error.lower() else "abort",
                "next_step": "fallback_agent" if result.error_code == "TIMEOUT_ERROR" else None
            }
        
        # Process the error
        error_handling = handle_agent_error(first_agent_result)
        
        # Verify error information is properly extracted
        assert error_handling["agent_failed"] is True
        assert error_handling["error_details"]["message"] == "LLM service timeout"
        assert error_handling["error_details"]["code"] == "TIMEOUT_ERROR"
        assert error_handling["recovery_action"] == "retry"
        assert error_handling["next_step"] == "fallback_agent"
    
    @pytest.mark.asyncio
    async def test_execution_result_metrics_aggregation(
        self, triage_agent, mock_llm_manager
    ):
        """Test aggregation of ExecutionResult metrics across multiple agents."""
        # Configure LLM response
        llm_response = json.dumps({
            "category": "Model Performance Analysis",
            "priority": "high",
            "confidence_score": 0.87
        })
        mock_llm_manager.ask_llm.return_value = llm_response
        
        # Execute agent with metrics
        state = DeepAgentState(user_request="Analyze model performance metrics")
        result = await triage_agent.execute(state, "metrics_test_001", stream_updates=False)
        
        # Simulate metrics aggregation across multiple agents
        def aggregate_agent_metrics(results: List[ExecutionResult]) -> Dict[str, Any]:
            """Simulate metrics aggregation across agent executions."""
            total_time = sum(r.execution_time_ms or 0 for r in results)
            success_count = sum(1 for r in results if r.is_success)
            error_count = sum(1 for r in results if r.error is not None)
            
            await asyncio.sleep(0)
    return {
                "total_execution_time_ms": total_time,
                "total_agents_executed": len(results),
                "successful_agents": success_count,
                "failed_agents": error_count,
                "overall_success_rate": success_count / len(results) if results else 0,
                "agent_details": [
                    {
                        "request_id": r.request_id,
                        "status": r.status.value,
                        "duration_ms": r.execution_time_ms,
                        "success": r.is_success,
                        "has_error": r.error is not None
                    }
                    for r in results
                ]
            }
        
        # Test with single result
        metrics = aggregate_agent_metrics([result])
        
        assert metrics["total_agents_executed"] == 1
        assert metrics["successful_agents"] == 1
        assert metrics["failed_agents"] == 0
        assert metrics["overall_success_rate"] == 1.0
        assert len(metrics["agent_details"]) == 1
        assert metrics["agent_details"][0]["status"] == "completed"
        assert metrics["agent_details"][0]["success"] is True
        
        # Simulate additional failed agent
        failed_result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            request_id="failed_agent_test",
            error_message="Processing error",
            execution_time_ms=1200.0
        )
        
        # Test aggregation with mixed results
        mixed_metrics = aggregate_agent_metrics([result, failed_result])
        
        assert mixed_metrics["total_agents_executed"] == 2
        assert mixed_metrics["successful_agents"] == 1
        assert mixed_metrics["failed_agents"] == 1
        assert mixed_metrics["overall_success_rate"] == 0.5


class TestExecutionResultBackwardCompatibility:
    """Test backward compatibility scenarios that could break cross-agent communication."""
    
    def test_legacy_execution_result_processing(self):
        """Test that legacy code patterns still work with new ExecutionResult."""
        # Create ExecutionResult using the new COMPLETED status
        result = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="legacy_test",
            data={"processed": True, "value": 42}
        )
        
        # Simulate legacy code patterns that might exist
        def legacy_result_processor(agent_result):
            """Simulate legacy code that processes agent results."""
    pass
            # Legacy pattern 1: Check success by status value
            is_successful = str(agent_result.status) == "completed"
            
            # Legacy pattern 2: Access data via result property
            output_data = agent_result.result if hasattr(agent_result, 'result') else agent_result.data
            
            # Legacy pattern 3: Check for errors via error property
            has_error = (hasattr(agent_result, 'error') and agent_result.error is not None)
            
            return {
                "success": is_successful,
                "data": output_data, 
                "error": has_error
            }
        
        # Process with legacy code
        processed = legacy_result_processor(result)
        
        # Verify legacy patterns work
        assert processed["success"] is True
        assert processed["data"]["processed"] is True
        assert processed["data"]["value"] == 42
        assert processed["error"] is False
    
    def test_execution_status_alias_compatibility(self):
        """Test that SUCCESS alias still works for backward compatibility."""
        # Some legacy code might still use SUCCESS
        legacy_result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,  # Using alias
            request_id="alias_test"
        )
        
        # Should work exactly like COMPLETED
        assert legacy_result.status == ExecutionStatus.COMPLETED
        assert legacy_result.status.value == "completed"
        assert legacy_result.is_success is True
        
        # Cross-agent comparison should work
        new_result = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="new_test"
        )
        
        assert legacy_result.status == new_result.status
        assert legacy_result.is_success == new_result.is_success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
    pass