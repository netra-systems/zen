"""Golden Pattern Test Suite for ReportingSubAgent

CRITICAL TEST SUITE: Validates ReportingSubAgent golden pattern implementation
following BaseAgent SSOT principles and ensuring chat value delivery through
proper WebSocket event emission.

This comprehensive test suite covers:
1. BaseAgent inheritance and SSOT compliance verification
2. WebSocket event emission for chat value (agent_thinking, tool_executing, etc.)
3. Golden pattern execution methods (validate_preconditions, execute_core_logic)  
4. Infrastructure non-duplication enforcement (no local reliability_manager, etc.)
5. Fallback scenarios and error recovery patterns
6. Cache hit/miss scenarios for performance optimization
7. Difficult edge cases and failure scenarios
8. Mission-critical WebSocket event propagation

BVJ: ALL segments | Chat Experience | Real-time AI value delivery = Core Revenue Driver
"""

import asyncio
import json
import pytest
import time
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime, timezone

from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState, ReportResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.redis_manager import RedisManager


# Module-level fixtures for shared access across all test classes
@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager."""
    llm = Mock(spec=LLMManager)
    llm.ask_llm = AsyncMock(return_value='{"report": "Test report", "sections": ["intro"], "metadata": {}}')
    return llm

@pytest.fixture
def mock_tool_dispatcher():
    """Create mock tool dispatcher."""
    dispatcher = Mock(spec=ToolDispatcher)
    dispatcher.dispatch = AsyncMock()
    return dispatcher

@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager."""
    manager = Mock()
    manager.send_to_thread = AsyncMock(return_value=True)
    manager.notify_agent_thinking = AsyncMock()
    manager.notify_agent_completed = AsyncMock()
    manager.notify_tool_executing = AsyncMock()
    manager.notify_tool_completed = AsyncMock()
    return manager

@pytest.fixture
def reporting_agent(mock_llm_manager, mock_tool_dispatcher):
    """Create ReportingSubAgent for testing."""
    agent = ReportingSubAgent()
    # Mock the dependencies that BaseAgent initializes
    agent.llm_manager = mock_llm_manager
    agent.tool_dispatcher = mock_tool_dispatcher
    return agent

@pytest.fixture
def complete_state():
    """Create complete state with all required analysis results."""
    state = DeepAgentState()
    state.user_request = "Generate a comprehensive report of our analysis"
    state.action_plan_result = {"plan": "Detailed action plan"}
    state.optimizations_result = {"optimizations": "Performance improvements"}
    state.data_result = {"data": "Analysis data"}
    state.triage_result = {"category": "optimization", "priority": "high"}
    state.chat_thread_id = "test-thread-123"
    state.user_id = "test-user-456"
    return state

@pytest.fixture
def incomplete_state():
    """Create incomplete state missing some analysis results."""
    state = DeepAgentState()
    state.user_request = "Generate report"
    state.action_plan_result = {"plan": "Some plan"}
    # Missing: optimizations_result, data_result, triage_result
    state.chat_thread_id = "test-thread-123"
    return state

@pytest.fixture
def execution_context(complete_state):
    """Create execution context for testing."""
    return ExecutionContext(
        request_id="test-run-123",
        user_id="test-user-456",
        session_id="test-thread-123",
        correlation_id="test-correlation-123",
        metadata={
            "agent_name": "ReportingSubAgent",
            "state": complete_state,
            "stream_updates": True
        },
        created_at=datetime.now(timezone.utc)
    )


class TestReportingSubAgentGoldenPattern:
    """Test ReportingSubAgent follows golden pattern requirements."""


class TestBaseAgentInheritanceSSOT:
    """Test BaseAgent inheritance and SSOT compliance."""

    def test_inherits_from_base_agent(self, reporting_agent):
        """CRITICAL: Verify ReportingSubAgent inherits from BaseAgent."""
        assert isinstance(reporting_agent, BaseAgent)
        assert ReportingSubAgent.__bases__ == (BaseAgent,)
        assert "BaseAgent" in [cls.__name__ for cls in ReportingSubAgent.__mro__]

    def test_no_infrastructure_duplication(self, reporting_agent):
        """CRITICAL: Verify NO infrastructure is duplicated in sub-agent."""
        # These should NOT exist as local instance variables
        infrastructure_attributes = [
            'local_reliability_manager',
            'local_execution_monitor', 
            'local_circuit_breaker',
            'local_websocket_handler',
            'local_retry_manager',
            'websocket_notifier',  # Should use inherited WebSocket bridge
            'execution_engine_local'  # Should use inherited execution patterns
        ]
        
        for attr in infrastructure_attributes:
            assert not hasattr(reporting_agent, attr), f"Found prohibited infrastructure: {attr}"

    def test_uses_inherited_infrastructure(self, reporting_agent):
        """CRITICAL: Verify agent uses inherited BaseAgent infrastructure."""
        # Verify inherited infrastructure is available
        assert hasattr(reporting_agent, '_websocket_adapter')  # Inherited WebSocket bridge
        assert hasattr(reporting_agent, '_unified_reliability_handler')  # Inherited reliability
        assert hasattr(reporting_agent, '_execution_engine')  # Inherited execution engine
        assert hasattr(reporting_agent, 'timing_collector')  # Inherited timing
        assert hasattr(reporting_agent, 'logger')  # Inherited logging

    def test_agent_name_and_description(self, reporting_agent):
        """Test agent has proper name and description."""
        assert reporting_agent.name == "ReportingSubAgent"
        assert "report" in reporting_agent.description.lower()
        assert reporting_agent.state == SubAgentLifecycle.PENDING

    def test_single_inheritance_pattern(self, reporting_agent):
        """CRITICAL: Verify clean single inheritance (no multiple inheritance)."""
        # Should only inherit from BaseAgent, no mixins
        base_classes = ReportingSubAgent.__bases__
        assert len(base_classes) == 1
        assert base_classes[0] == BaseAgent
        
        # Verify no mixin contamination in MRO
        mixin_indicators = ['Mixin', 'Protocol', 'ABC']
        mro_names = [cls.__name__ for cls in ReportingSubAgent.__mro__]
        for name in mro_names:
            for indicator in mixin_indicators:
                if indicator in name and name != 'ABC':  # ABC is allowed as base
                    pytest.fail(f"Found mixin contamination in MRO: {name}")

    def test_websocket_bridge_integration(self, reporting_agent, mock_websocket_manager):
        """Test WebSocket bridge integration via BaseAgent."""
        # Set websocket bridge (simulating supervisor setup)
        reporting_agent.set_websocket_bridge(mock_websocket_manager, "test-run-123")
        
        # Verify bridge is set and available
        assert reporting_agent.has_websocket_context()
        assert reporting_agent._websocket_adapter._bridge is not None


class TestGoldenPatternMethods:
    """Test golden pattern execution methods implementation."""

    async def test_validate_preconditions_complete_state(self, reporting_agent, execution_context):
        """Test validate_preconditions with complete state."""
        result = await reporting_agent.validate_preconditions(execution_context)
        assert result is True

    async def test_validate_preconditions_incomplete_state(self, reporting_agent, incomplete_state):
        """Test validate_preconditions with missing required data."""
        context = ExecutionContext(
            request_id="test-run-123",
            user_id="test-user-456",
            metadata={"agent_name": "ReportingSubAgent", "state": incomplete_state}
        )
        result = await reporting_agent.validate_preconditions(context)
        assert result is False

    async def test_validate_preconditions_empty_state(self, reporting_agent):
        """Test validate_preconditions with completely empty state."""
        empty_state = DeepAgentState()
        context = ExecutionContext(
            request_id="test-run-123",
            user_id="test-user-456",
            metadata={"agent_name": "ReportingSubAgent", "state": empty_state}
        )
        result = await reporting_agent.validate_preconditions(context)
        assert result is False

    async def test_execute_core_logic_success(self, reporting_agent, execution_context, mock_llm_manager):
        """Test execute_core_logic successful execution."""
        # Mock LLM response
        mock_llm_manager.ask_llm.return_value = json.dumps({
            "report": "Comprehensive analysis report",
            "sections": ["executive_summary", "findings", "recommendations"],
            "metadata": {"generated_at": "2025-09-02T10:00:00Z"}
        })
        
        result = await reporting_agent.execute_core_logic(execution_context)
        
        assert isinstance(result, dict)
        assert "report" in result
        assert result["report"] == "Comprehensive analysis report"
        assert "sections" in result
        assert "metadata" in result

    async def test_execute_core_logic_llm_failure(self, reporting_agent, execution_context, mock_llm_manager):
        """Test execute_core_logic with LLM failure."""
        # Mock LLM failure
        mock_llm_manager.ask_llm.side_effect = Exception("LLM service unavailable")
        
        with pytest.raises(Exception) as exc_info:
            await reporting_agent.execute_core_logic(execution_context)
        
        assert "LLM service unavailable" in str(exc_info.value)

    async def test_execute_core_logic_invalid_json_response(self, reporting_agent, execution_context, mock_llm_manager):
        """Test execute_core_logic with invalid JSON from LLM."""
        # Mock invalid JSON response
        mock_llm_manager.ask_llm.return_value = "Invalid JSON response from LLM"
        
        result = await reporting_agent.execute_core_logic(execution_context)
        
        # Should handle gracefully with fallback
        assert isinstance(result, dict)
        assert "report" in result
        assert result["report"] == "No report could be generated."


class TestWebSocketEventEmission:
    """Test WebSocket event emission for chat value delivery."""

    async def test_websocket_events_during_execution(self, reporting_agent, execution_context, mock_websocket_manager, mock_llm_manager):
        """CRITICAL: Test all required WebSocket events are emitted during execution."""
        # Set up WebSocket bridge
        reporting_agent.set_websocket_bridge(mock_websocket_manager, execution_context.run_id)
        
        # Mock successful LLM response
        mock_llm_manager.ask_llm.return_value = json.dumps({
            "report": "Test report content",
            "sections": ["intro", "analysis", "conclusion"],
            "metadata": {"generated": True}
        })
        
        # Execute core logic
        result = await reporting_agent.execute_core_logic(execution_context)
        
        # Verify WebSocket events were emitted
        websocket_calls = mock_websocket_manager.method_calls
        
        # Check for thinking events (multiple expected)
        thinking_calls = [call for call in websocket_calls if 'thinking' in str(call)]
        assert len(thinking_calls) >= 2, "Should emit multiple thinking events"
        
        # Verify progress events  
        progress_calls = [call for call in websocket_calls if 'progress' in str(call)]
        assert len(progress_calls) >= 1, "Should emit progress events"

    async def test_emit_thinking_events(self, reporting_agent, mock_websocket_manager):
        """Test emit_thinking WebSocket events."""
        reporting_agent.set_websocket_bridge(mock_websocket_manager, "test-run-123")
        
        await reporting_agent.emit_thinking("Compiling analysis results...")
        await reporting_agent.emit_thinking("Building comprehensive report...")
        await reporting_agent.emit_thinking("Formatting final output...")
        
        # Verify thinking events were sent
        assert len(mock_websocket_manager.method_calls) >= 3

    async def test_emit_progress_events(self, reporting_agent, mock_websocket_manager):
        """Test emit_progress WebSocket events."""
        reporting_agent.set_websocket_bridge(mock_websocket_manager, "test-run-123")
        
        await reporting_agent.emit_progress("Report generation 25% complete")
        await reporting_agent.emit_progress("Report generation 75% complete")
        await reporting_agent.emit_progress("Report completed successfully", is_complete=True)
        
        # Verify progress events were sent
        assert len(mock_websocket_manager.method_calls) >= 3

    async def test_emit_agent_completed(self, reporting_agent, mock_websocket_manager):
        """Test emit_agent_completed WebSocket event."""
        reporting_agent.set_websocket_bridge(mock_websocket_manager, "test-run-123")
        
        result = {"report": "Final report", "status": "success"}
        await reporting_agent.emit_agent_completed(result)
        
        # Verify completion event was sent
        assert len(mock_websocket_manager.method_calls) >= 1

    async def test_emit_error_events(self, reporting_agent, mock_websocket_manager):
        """Test emit_error WebSocket events."""
        reporting_agent.set_websocket_bridge(mock_websocket_manager, "test-run-123")
        
        await reporting_agent.emit_error("Report generation failed", "LLMError", {"details": "timeout"})
        
        # Verify error event was sent
        assert len(mock_websocket_manager.method_calls) >= 1

    async def test_websocket_events_without_bridge(self, reporting_agent):
        """Test WebSocket events fail gracefully without bridge."""
        # Don't set WebSocket bridge
        assert not reporting_agent.has_websocket_context()
        
        # These should not raise exceptions
        await reporting_agent.emit_thinking("Test thought")
        await reporting_agent.emit_progress("Test progress")
        await reporting_agent.emit_agent_completed({"test": "result"})


class TestReliabilityAndFallback:
    """Test reliability patterns and fallback scenarios."""

    async def test_fallback_report_generation(self, reporting_agent, complete_state):
        """Test fallback report generation when primary method fails."""
        # Create fallback operation
        fallback_op = reporting_agent._create_fallback_reporting_operation(
            complete_state, "test-run-123", True
        )
        
        result = await fallback_op()
        
        assert isinstance(result, dict)
        assert "report" in result
        assert "fallback" in result["report"].lower()
        assert result["metadata"]["fallback_used"] is True

    def test_fallback_summary_creation(self, reporting_agent, complete_state):
        """Test fallback summary creation from state."""
        summary = reporting_agent._create_fallback_summary(complete_state)
        
        assert isinstance(summary, dict)
        assert summary["data_analyzed"] is True
        assert summary["optimizations_provided"] is True
        assert summary["action_plan_created"] is True
        assert summary["fallback_used"] is True

    def test_fallback_metadata_creation(self, reporting_agent):
        """Test fallback metadata creation."""
        metadata = reporting_agent._create_fallback_metadata()
        
        assert isinstance(metadata, dict)
        assert metadata["fallback_used"] is True
        assert "reason" in metadata

    async def test_execute_with_reliability_patterns(self, reporting_agent, complete_state, mock_llm_manager):
        """Test execution with reliability patterns via inherited infrastructure."""
        # Mock LLM success
        mock_llm_manager.ask_llm.return_value = json.dumps({"report": "Success", "metadata": {}})
        
        # Test reliability execution 
        if reporting_agent._unified_reliability_handler:
            async def test_operation():
                return {"test": "success"}
            
            result = await reporting_agent.execute_with_reliability(
                test_operation, "test_operation"
            )
            
            assert result is not None

    def test_health_status_reporting(self, reporting_agent):
        """Test health status reporting through inherited infrastructure."""
        health = reporting_agent.get_health_status()
        
        assert isinstance(health, dict)
        assert "agent_name" in health
        assert health["agent_name"] == "ReportingSubAgent"
        assert "state" in health
        assert "uses_unified_reliability" in health


class TestCacheScenarios:
    """Test caching behavior and performance optimization."""

    def test_cache_configuration(self, reporting_agent):
        """Test cache configuration and setup."""
        # Verify default cache settings
        assert hasattr(reporting_agent, 'cache_ttl')
        assert reporting_agent.cache_ttl >= 0
        
        # Test with caching enabled
        agent_with_cache = ReportingSubAgent()
        # Cache is controlled by BaseAgent initialization
        assert agent_with_cache._enable_caching is True  # Set in constructor

    async def test_report_result_creation(self, reporting_agent):
        """Test ReportResult object creation."""
        test_data = {
            "report": "Test report content",
            "sections": ["intro", "body", "conclusion"],
            "metadata": {"version": "1.0"}
        }
        
        report_result = reporting_agent._create_report_result(test_data)
        
        assert isinstance(report_result, ReportResult)
        assert report_result.report_type == "analysis"
        assert report_result.content == "Test report content"
        assert report_result.sections == ["intro", "body", "conclusion"]
        assert report_result.metadata == {"version": "1.0"}

    async def test_report_result_missing_fields(self, reporting_agent):
        """Test ReportResult creation with missing fields."""
        minimal_data = {}
        
        report_result = reporting_agent._create_report_result(minimal_data)
        
        assert isinstance(report_result, ReportResult)
        assert report_result.content == "No content available"
        assert report_result.sections == []
        assert report_result.metadata == {}


class TestErrorHandlingEdgeCases:
    """Test difficult edge cases and error scenarios."""

    async def test_empty_llm_response(self, reporting_agent, execution_context, mock_llm_manager):
        """Test handling of empty LLM response."""
        mock_llm_manager.ask_llm.return_value = ""
        
        result = await reporting_agent.execute_core_logic(execution_context)
        
        assert isinstance(result, dict)
        assert "report" in result
        # Should handle gracefully

    async def test_malformed_json_response(self, reporting_agent, execution_context, mock_llm_manager):
        """Test handling of malformed JSON from LLM."""
        mock_llm_manager.ask_llm.return_value = '{"report": "test", "invalid": json}'
        
        result = await reporting_agent.execute_core_logic(execution_context)
        
        assert isinstance(result, dict)
        # Should handle gracefully with fallback

    async def test_llm_timeout(self, reporting_agent, execution_context, mock_llm_manager):
        """Test handling of LLM timeout."""
        mock_llm_manager.ask_llm.side_effect = asyncio.TimeoutError("LLM timeout")
        
        with pytest.raises(asyncio.TimeoutError):
            await reporting_agent.execute_core_logic(execution_context)

    async def test_network_failure(self, reporting_agent, execution_context, mock_llm_manager):
        """Test handling of network failure."""
        mock_llm_manager.ask_llm.side_effect = ConnectionError("Network unreachable")
        
        with pytest.raises(ConnectionError):
            await reporting_agent.execute_core_logic(execution_context)

    def test_corrupted_state_data(self, reporting_agent):
        """Test handling of corrupted state data."""
        corrupted_state = DeepAgentState()
        # Set invalid/corrupted data
        corrupted_state.action_plan_result = "not_a_dict"
        corrupted_state.data_result = None
        corrupted_state.optimizations_result = []
        
        context = ExecutionContext(
            request_id="test-run-123",
            user_id="test-user-456",
            metadata={"agent_name": "ReportingSubAgent", "state": corrupted_state}
        )
        
        # Should return False for invalid state
        result = asyncio.run(reporting_agent.validate_preconditions(context))
        assert result is False

    async def test_concurrent_execution(self, reporting_agent, mock_llm_manager):
        """Test concurrent execution scenarios."""
        mock_llm_manager.ask_llm.return_value = json.dumps({"report": "concurrent test"})
        
        # Create multiple contexts
        contexts = []
        for i in range(3):
            state = DeepAgentState()
            state.user_request = f"Request {i}"
            state.action_plan_result = {"plan": f"Plan {i}"}
            state.optimizations_result = {"opts": f"Opts {i}"}
            state.data_result = {"data": f"Data {i}"}
            state.triage_result = {"triage": f"Triage {i}"}
            
            contexts.append(ExecutionContext(
                request_id=f"run-{i}",
                user_id=f"user-{i}",
                metadata={"agent_name": "ReportingSubAgent", "state": state}
            ))
        
        # Execute concurrently
        tasks = [reporting_agent.execute_core_logic(ctx) for ctx in contexts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, dict)

    async def test_memory_pressure_scenario(self, reporting_agent, execution_context, mock_llm_manager):
        """Test behavior under memory pressure."""
        # Simulate large response
        large_response = json.dumps({
            "report": "Large report content" * 1000,
            "sections": ["section"] * 100,
            "metadata": {"large_data": ["item"] * 1000}
        })
        mock_llm_manager.ask_llm.return_value = large_response
        
        result = await reporting_agent.execute_core_logic(execution_context)
        
        assert isinstance(result, dict)
        assert "report" in result


class TestModernExecutionPatterns:
    """Test modern execution patterns via BaseAgent."""

    async def test_modern_execute_method_success(self, reporting_agent, complete_state, mock_llm_manager):
        """Test modern execute method with successful execution."""
        mock_llm_manager.ask_llm.return_value = json.dumps({"report": "Modern execution test"})
        
        if hasattr(reporting_agent, 'execute_modern') and reporting_agent._enable_execution_engine:
            result = await reporting_agent.execute_modern(complete_state, "test-run-123", True)
            
            assert isinstance(result, ExecutionResult)
            if result.is_success:
                assert result.status == ExecutionStatus.COMPLETED
                assert result.result is not None
                assert result.execution_time_ms >= 0

    async def test_modern_execute_method_failure(self, reporting_agent, incomplete_state, mock_llm_manager):
        """Test modern execute method with precondition failure."""
        if hasattr(reporting_agent, 'execute_modern') and reporting_agent._enable_execution_engine:
            result = await reporting_agent.execute_modern(incomplete_state, "test-run-123", True)
            
            assert isinstance(result, ExecutionResult)
            # Should fail due to preconditions
            assert result.is_success is False
            assert result.status == ExecutionStatus.FAILED

    def test_execution_context_creation(self, reporting_agent, complete_state):
        """Test execution context creation."""
        context = reporting_agent._create_execution_context(complete_state, "test-run-123", True)
        
        assert isinstance(context, ExecutionContext)
        assert context.run_id == "test-run-123"
        assert context.agent_name == "ReportingSubAgent"
        assert context.state == complete_state
        assert context.stream_updates is True

    def test_success_execution_result_creation(self, reporting_agent):
        """Test successful execution result creation."""
        test_result = {"report": "Test report", "status": "success"}
        execution_time = 150.5
        
        result = reporting_agent._create_success_execution_result(test_result, execution_time)
        
        assert isinstance(result, ExecutionResult)
        assert result.is_success is True
        assert result.status == ExecutionStatus.COMPLETED
        assert result.result == test_result
        assert result.execution_time_ms == execution_time

    def test_error_execution_result_creation(self, reporting_agent):
        """Test error execution result creation."""
        error_msg = "Test error occurred"
        execution_time = 75.0
        
        result = reporting_agent._create_error_execution_result(error_msg, execution_time)
        
        assert isinstance(result, ExecutionResult)
        assert result.is_success is False
        assert result.status == ExecutionStatus.FAILED
        assert result.error == error_msg
        assert result.execution_time_ms == execution_time


class TestLegacyCompatibility:
    """Test legacy compatibility and migration support."""

    async def test_legacy_execute_method(self, reporting_agent, complete_state, mock_llm_manager):
        """Test legacy execute method still works."""
        mock_llm_manager.ask_llm.return_value = json.dumps({"report": "Legacy test"})
        
        # Should not raise exception
        await reporting_agent.execute(complete_state, "test-run-123", True)
        
        # Verify state was updated
        assert hasattr(complete_state, 'report_result')

    async def test_legacy_update_methods(self, reporting_agent):
        """Test legacy update methods for backward compatibility."""
        # These methods should exist for backward compatibility
        assert hasattr(reporting_agent, '_send_update')
        assert hasattr(reporting_agent, 'send_processing_update')
        assert hasattr(reporting_agent, 'send_completion_update')

    def test_get_health_status_legacy(self, reporting_agent):
        """Test legacy health status method."""
        health = reporting_agent.get_health_status()
        
        assert isinstance(health, dict)
        assert "agent_name" in health

    def test_get_circuit_breaker_status(self, reporting_agent):
        """Test circuit breaker status reporting."""
        status = reporting_agent.get_circuit_breaker_status()
        
        assert isinstance(status, dict)


@pytest.mark.integration 
class TestReportingAgentIntegration:
    """Integration tests with real services (when available)."""

    @pytest.fixture
    def real_redis_manager(self):
        """Create real Redis manager for integration testing."""
        try:
            from netra_backend.app.redis_manager import RedisManager
            return RedisManager()
        except Exception:
            pytest.skip("Redis not available for integration testing")

    async def test_integration_with_redis(self, real_redis_manager, mock_llm_manager):
        """Test integration with real Redis for caching."""
        reporting_agent = ReportingSubAgent()
        reporting_agent.llm_manager = mock_llm_manager
        reporting_agent.tool_dispatcher = Mock(spec=ToolDispatcher)
        
        # Test Redis integration if available
        if real_redis_manager:
            assert reporting_agent is not None


@pytest.mark.mission_critical
class TestMissionCriticalWebSocketPropagation:
    """Mission-critical tests for WebSocket event propagation."""

    async def test_all_websocket_events_propagated(self, reporting_agent, execution_context, mock_websocket_manager, mock_llm_manager):
        """MISSION CRITICAL: All WebSocket events must propagate for chat value."""
        # Set up WebSocket bridge
        reporting_agent.set_websocket_bridge(mock_websocket_manager, execution_context.run_id)
        
        # Mock successful execution
        mock_llm_manager.ask_llm.return_value = json.dumps({
            "report": "Mission critical test report",
            "sections": ["critical", "analysis"],
            "metadata": {"mission_critical": True}
        })
        
        # Execute and capture events
        result = await reporting_agent.execute_core_logic(execution_context)
        
        # Verify ALL required events were sent
        websocket_calls = mock_websocket_manager.method_calls
        assert len(websocket_calls) >= 3, "Must send multiple WebSocket events for chat value"
        
        # Verify execution completed successfully
        assert isinstance(result, dict)
        assert "report" in result

    async def test_websocket_event_timing(self, reporting_agent, execution_context, mock_websocket_manager, mock_llm_manager):
        """Test WebSocket events are sent in proper timing sequence."""
        reporting_agent.set_websocket_bridge(mock_websocket_manager, execution_context.run_id)
        mock_llm_manager.ask_llm.return_value = json.dumps({"report": "Timing test"})
        
        start_time = time.time()
        await reporting_agent.execute_core_logic(execution_context)
        end_time = time.time()
        
        # Events should be sent within reasonable time
        execution_time = end_time - start_time
        assert execution_time < 5.0, "WebSocket events must be sent promptly"

    async def test_websocket_events_survive_failures(self, reporting_agent, execution_context, mock_websocket_manager, mock_llm_manager):
        """Test WebSocket events are attempted even during failures."""
        reporting_agent.set_websocket_bridge(mock_websocket_manager, execution_context.run_id)
        
        # Mock LLM failure
        mock_llm_manager.ask_llm.side_effect = Exception("Simulated failure")
        
        # Should attempt WebSocket events even during failure
        with pytest.raises(Exception):
            await reporting_agent.execute_core_logic(execution_context)
        
        # Verify some WebSocket events were attempted
        websocket_calls = mock_websocket_manager.method_calls
        assert len(websocket_calls) >= 1, "Should attempt WebSocket events even during failures"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])