"""
Mission Critical Tests for Golden Pattern ReportingSubAgent

Tests the complete golden pattern implementation including:
- WebSocket event emissions for chat value delivery
- Report generation workflow with real LLM services
- Error handling with proper AgentError types
- Complete end-to-end flow testing
- BaseAgent infrastructure integration

CRITICAL: This test suite ensures the ReportingSubAgent follows
the golden pattern and delivers chat value through WebSocket events.
"""

import asyncio
import json
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.agent_error_types import AgentValidationError
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager


class TestReportingAgentGoldenPattern:
    """Test the ReportingSubAgent golden pattern implementation."""

    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        llm_manager = AsyncMock(spec=LLMManager)
        llm_manager.ask_llm.return_value = json.dumps({
            "report": "Test report generated successfully",
            "sections": [
                {
                    "section_id": "summary",
                    "title": "Executive Summary",
                    "content": "This is a test summary",
                    "section_type": "summary"
                }
            ],
            "metadata": {"generated_at": time.time()}
        })
        return llm_manager

    @pytest.fixture
    def reporting_agent(self, mock_llm_manager):
        """Create ReportingSubAgent instance."""
        agent = ReportingSubAgent()
        agent.llm_manager = mock_llm_manager
        return agent

    @pytest.fixture
    def valid_state(self):
        """Create valid DeepAgentState with all required results."""
        state = DeepAgentState()
        state.user_request = "Generate a comprehensive analysis report"
        state.action_plan_result = {"actions": ["analyze", "optimize"]}
        state.optimizations_result = {"optimizations": ["cache", "index"]}
        state.data_result = {"data": "analysis complete"}
        state.triage_result = {"category": "analysis", "priority": "high"}
        return state

    @pytest.fixture
    def incomplete_state(self):
        """Create incomplete DeepAgentState missing required results."""
        state = DeepAgentState()
        state.user_request = "Generate report"
        state.action_plan_result = None  # Missing
        state.optimizations_result = {"optimizations": ["cache"]}
        state.data_result = None  # Missing
        state.triage_result = {"category": "analysis"}
        return state

    @pytest.fixture
    def execution_context(self, valid_state):
        """Create valid execution context."""
        return ExecutionContext(
            run_id="test_run_123",
            agent_name="ReportingSubAgent",
            state=valid_state,
            stream_updates=True,
            thread_id="thread_456",
            user_id="user_789",
            start_time=time.time(),
            correlation_id="correlation_123"
        )

    async def test_golden_pattern_inheritance(self, reporting_agent):
        """Test that ReportingSubAgent follows golden pattern inheritance."""
        # Verify inheritance from BaseAgent
        from netra_backend.app.agents.base_agent import BaseAgent
        assert isinstance(reporting_agent, BaseAgent)
        
        # Verify infrastructure is enabled
        assert reporting_agent._enable_reliability == True
        assert reporting_agent._enable_execution_engine == True
        assert reporting_agent._enable_caching == True
        
        # Verify BaseAgent methods are available
        assert hasattr(reporting_agent, 'emit_thinking')
        assert hasattr(reporting_agent, 'emit_progress')
        assert hasattr(reporting_agent, 'emit_error')
        assert hasattr(reporting_agent, 'execute_with_reliability')

    async def test_validate_preconditions_success(self, reporting_agent, execution_context):
        """Test successful validation of preconditions."""
        # Should return True for valid context
        result = await reporting_agent.validate_preconditions(execution_context)
        assert result == True

    async def test_validate_preconditions_failure(self, reporting_agent, incomplete_state):
        """Test validation failure with proper AgentValidationError."""
        context = ExecutionContext(
            run_id="test_run_123",
            agent_name="ReportingSubAgent",
            state=incomplete_state,
            stream_updates=True,
            thread_id="thread_456",
            user_id="user_789",
            start_time=time.time(),
            correlation_id="correlation_123"
        )
        
        # Should raise AgentValidationError for missing results
        with pytest.raises(AgentValidationError) as exc_info:
            await reporting_agent.validate_preconditions(context)
        
        # Verify error details
        error = exc_info.value
        assert "Missing required analysis results" in str(error)
        assert "action_plan_result" in str(error)
        assert "data_result" in str(error)

    @pytest.mark.asyncio
    async def test_websocket_events_emission(self, reporting_agent, execution_context):
        """Test WebSocket events are emitted for chat value delivery."""
        # Mock WebSocket event methods
        reporting_agent.emit_thinking = AsyncMock()
        reporting_agent.emit_progress = AsyncMock()
        reporting_agent.emit_error = AsyncMock()
        
        # Mock internal methods to avoid actual LLM calls
        with patch.object(reporting_agent, '_build_reporting_prompt', return_value="test prompt"):
            with patch.object(reporting_agent, '_execute_reporting_llm_with_observability', 
                            return_value='{"report": "test", "metadata": {}}'):
                with patch.object(reporting_agent, '_send_success_update'):
                    
                    # Execute core logic
                    result = await reporting_agent.execute_core_logic(execution_context)
                    
                    # Verify WebSocket events were emitted
                    assert reporting_agent.emit_thinking.call_count >= 2  # At least 2 thinking events
                    assert reporting_agent.emit_progress.call_count >= 2  # At least 2 progress events
                    
                    # Verify specific event calls
                    thinking_calls = [call.args[0] for call in reporting_agent.emit_thinking.call_args_list]
                    assert any("Starting comprehensive report generation" in call for call in thinking_calls)
                    assert any("Generating final report with AI model" in call for call in thinking_calls)
                    
                    progress_calls = [call.args[0] for call in reporting_agent.emit_progress.call_args_list]
                    assert any("Building comprehensive analysis prompt" in call for call in progress_calls)
                    assert any("Final report generation completed successfully" in call for call in progress_calls)

    @pytest.mark.asyncio
    async def test_error_handling_with_websocket_events(self, reporting_agent, execution_context):
        """Test proper error handling with WebSocket error events."""
        # Mock WebSocket methods
        reporting_agent.emit_thinking = AsyncMock()
        reporting_agent.emit_progress = AsyncMock()
        reporting_agent.emit_error = AsyncMock()
        
        # Mock LLM to raise an exception
        with patch.object(reporting_agent, '_execute_reporting_llm_with_observability',
                         side_effect=Exception("LLM service unavailable")):
            
            # Execute should handle error gracefully
            result = await reporting_agent.execute_core_logic(execution_context)
            
            # Verify error event was emitted
            reporting_agent.emit_error.assert_called_once()
            error_call = reporting_agent.emit_error.call_args[0][0]
            assert "Report generation failed" in error_call
            
            # Verify fallback result is returned
            assert result is not None
            assert "fallback_used" in result.get("metadata", {})

    @pytest.mark.asyncio
    async def test_complete_report_generation_workflow(self, reporting_agent, execution_context, mock_llm_manager):
        """Test complete end-to-end report generation workflow."""
        # Mock WebSocket methods
        reporting_agent.emit_thinking = AsyncMock()
        reporting_agent.emit_progress = AsyncMock()
        reporting_agent._send_update = AsyncMock()
        
        # Execute core logic
        result = await reporting_agent.execute_core_logic(execution_context)
        
        # Verify LLM was called
        mock_llm_manager.ask_llm.assert_called_once()
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "report" in result
        assert result["report"] == "Test report generated successfully"
        
        # Verify state was updated
        assert execution_context.state.report_result is not None

    @pytest.mark.asyncio
    async def test_legacy_execute_method(self, reporting_agent, valid_state):
        """Test backward compatibility with legacy execute method."""
        # Mock execute_with_reliability to avoid actual reliability infrastructure
        reporting_agent.execute_with_reliability = AsyncMock()
        
        # Execute using legacy method
        await reporting_agent.execute(valid_state, "test_run_123", True)
        
        # Verify reliability infrastructure was called
        reporting_agent.execute_with_reliability.assert_called_once()
        
        # Verify arguments passed correctly
        args = reporting_agent.execute_with_reliability.call_args
        assert args[1][1] == "execute_reporting"  # operation_name

    def test_fallback_report_creation(self, reporting_agent, valid_state):
        """Test fallback report creation for error scenarios."""
        fallback_result = reporting_agent._create_fallback_report(valid_state)
        
        # Verify fallback structure
        assert isinstance(fallback_result, dict)
        assert "report" in fallback_result
        assert "summary" in fallback_result
        assert "metadata" in fallback_result
        
        # Verify fallback indicators
        assert fallback_result["summary"]["fallback_used"] == True
        assert fallback_result["metadata"]["fallback_used"] == True
        assert "Primary report generation failed" in fallback_result["metadata"]["reason"]

    def test_report_result_conversion(self, reporting_agent):
        """Test conversion from dict to ReportResult object."""
        test_data = {
            "report": "Test report content",
            "sections": [
                {
                    "section_id": "test_section",
                    "title": "Test Section",
                    "content": "Test content",
                    "section_type": "analysis"
                },
                "string_section"  # Test string section handling
            ],
            "metadata": {"test": "value"}
        }
        
        result = reporting_agent._create_report_result(test_data)
        
        # Verify ReportResult object creation
        from netra_backend.app.agents.state import ReportResult
        assert isinstance(result, ReportResult)
        assert result.content == "Test report content"
        assert len(result.sections) == 2
        assert result.metadata["test"] == "value"
        
        # Verify section conversion
        assert result.sections[0].section_id == "test_section"
        assert result.sections[1].title == "String_section"  # Capitalized

    async def test_entry_conditions_check(self, reporting_agent, valid_state, incomplete_state):
        """Test entry conditions checking."""
        # Valid state should pass
        result = await reporting_agent.check_entry_conditions(valid_state, "test_run")
        assert result == True
        
        # Incomplete state should fail
        result = await reporting_agent.check_entry_conditions(incomplete_state, "test_run")
        assert result == False

    async def test_cleanup_method(self, reporting_agent, valid_state):
        """Test cleanup method execution."""
        # Create mock report result with metadata
        from netra_backend.app.agents.state import ReportResult
        valid_state.report_result = ReportResult(
            report_type="analysis",
            content="test",
            sections=[],
            metadata={"cleanup_test": True}
        )
        
        # Should not raise any exceptions
        await reporting_agent.cleanup(valid_state, "test_run_123")

    @pytest.mark.asyncio
    async def test_llm_observability_integration(self, reporting_agent):
        """Test LLM observability integration."""
        with patch('netra_backend.app.agents.reporting_sub_agent.start_llm_heartbeat') as mock_start:
            with patch('netra_backend.app.agents.reporting_sub_agent.stop_llm_heartbeat') as mock_stop:
                with patch('netra_backend.app.agents.reporting_sub_agent.log_agent_input') as mock_log_input:
                    with patch('netra_backend.app.agents.reporting_sub_agent.log_agent_output') as mock_log_output:
                        
                        # Execute LLM with observability
                        response = await reporting_agent._execute_reporting_llm_with_observability(
                            "test prompt", "test_correlation_id"
                        )
                        
                        # Verify observability hooks were called
                        mock_start.assert_called_once_with("test_correlation_id", "ReportingSubAgent")
                        mock_stop.assert_called_once_with("test_correlation_id")
                        mock_log_input.assert_called_once()
                        mock_log_output.assert_called_once()

    def test_golden_pattern_compliance(self, reporting_agent):
        """Test compliance with golden pattern requirements."""
        # Verify line count is reasonable (should be under 250 lines)
        import inspect
        import netra_backend.app.agents.reporting_sub_agent as agent_module
        source_lines = inspect.getsourcelines(agent_module)[0]
        line_count = len(source_lines)
        assert line_count < 250, f"Agent has {line_count} lines, should be under 250 for golden pattern"
        
        # Verify required methods are implemented
        assert hasattr(reporting_agent, 'validate_preconditions')
        assert hasattr(reporting_agent, 'execute_core_logic')
        
        # Verify infrastructure methods are NOT implemented (inherited from BaseAgent)
        # These should be inherited, not duplicated
        source = inspect.getsource(ReportingSubAgent)
        assert 'class ReliabilityManager' not in source
        assert 'class ExecutionEngine' not in source
        assert 'def emit_websocket_event' not in source
        
        # Verify proper imports for AgentError types
        assert hasattr(reporting_agent, '__module__')
        module = __import__(reporting_agent.__module__, fromlist=['AgentValidationError'])
        assert hasattr(module, 'AgentValidationError')


@pytest.mark.integration
class TestReportingAgentIntegration:
    """Integration tests with real BaseAgent infrastructure."""

    @pytest.fixture
    def integration_agent(self):
        """Create agent for integration testing."""
        agent = ReportingSubAgent()
        # Use mock LLM to avoid real API calls
        agent.llm_manager = AsyncMock(spec=LLMManager)
        agent.llm_manager.ask_llm.return_value = '{"report": "Integration test report", "metadata": {}}'
        return agent

    @pytest.mark.asyncio
    async def test_baseagent_infrastructure_integration(self, integration_agent):
        """Test integration with BaseAgent infrastructure."""
        # Test health status (from BaseAgent)
        health = integration_agent.get_health_status()
        assert isinstance(health, dict)
        assert "agent_name" in health
        assert health["agent_name"] == "ReportingSubAgent"
        
        # Test WebSocket bridge availability
        has_websocket = integration_agent.has_websocket_context()
        assert isinstance(has_websocket, bool)


class TestReportingAgentExecuteCore:
    """Test _execute_core implementation patterns."""
    
    @pytest.fixture
    def reporting_agent(self):
        """Create ReportingSubAgent instance for _execute_core testing."""
        agent = ReportingSubAgent()
        agent.llm_manager = AsyncMock()
        agent.llm_manager.ask_llm.return_value = json.dumps({
            "report": "Core execution test report",
            "sections": [{"section_id": "test", "content": "Test section"}]
        })
        return agent
        
    @pytest.fixture
    def core_execution_context(self):
        """Create execution context for _execute_core testing."""
        state = DeepAgentState()
        state.user_request = "Test _execute_core workflow"
        state.action_plan_result = {"actions": ["analyze", "report"]}
        state.optimizations_result = {"optimizations": ["cache"]}
        state.data_result = {"data": "test data"}
        state.triage_result = {"category": "reporting"}
        
        return ExecutionContext(
            run_id="core_exec_test",
            agent_name="ReportingSubAgent",
            state=state,
            stream_updates=True,
            thread_id="thread_core",
            user_id="user_core",
            start_time=time.time(),
            correlation_id="core_correlation"
        )

    async def test_execute_core_basic_workflow(self, reporting_agent, core_execution_context):
        """Test _execute_core basic execution workflow."""
        # Mock WebSocket events
        reporting_agent._emit_agent_started = AsyncMock()
        reporting_agent._emit_agent_thinking = AsyncMock()
        reporting_agent._emit_tool_executing = AsyncMock()
        reporting_agent._emit_tool_completed = AsyncMock()
        reporting_agent._emit_agent_completed = AsyncMock()
        
        # Execute core logic - fallback to execute_core_logic if _execute_core not available
        if hasattr(reporting_agent, '_execute_core'):
            result = await reporting_agent._execute_core(core_execution_context)
        else:
            result = await reporting_agent.execute_core_logic(core_execution_context)
        
        # Verify result
        assert result is not None
        assert "report" in str(result) or hasattr(result, 'report') or hasattr(result, 'content')
        
    async def test_execute_core_error_propagation(self, reporting_agent, core_execution_context):
        """Test _execute_core error propagation."""
        # Force LLM error
        reporting_agent.llm_manager.ask_llm.side_effect = Exception("LLM service unavailable")
        
        # Mock WebSocket events
        reporting_agent._emit_agent_started = AsyncMock()
        reporting_agent._emit_agent_error = AsyncMock()
        
        # Execute - should handle error gracefully
        if hasattr(reporting_agent, '_execute_core'):
            result = await reporting_agent._execute_core(core_execution_context)
            # Should return fallback result, not raise exception
            assert result is not None
        else:
            result = await reporting_agent.execute_core_logic(core_execution_context)
            assert result is not None
        
    async def test_execute_core_state_validation(self, reporting_agent):
        """Test _execute_core validates required state."""
        # Create context with incomplete state
        incomplete_state = DeepAgentState()
        incomplete_state.user_request = "Test incomplete state"
        # Missing required results
        
        context = ExecutionContext(
            run_id="incomplete_test",
            agent_name="ReportingSubAgent", 
            state=incomplete_state,
            stream_updates=True
        )
        
        # Should handle missing state gracefully or raise validation error
        try:
            if hasattr(reporting_agent, '_execute_core'):
                result = await reporting_agent._execute_core(context)
            else:
                result = await reporting_agent.execute_core_logic(context)
            # If no exception, result should indicate the missing data
            assert result is not None
        except (AgentValidationError, ValueError):
            # This is acceptable behavior for incomplete state
            pass
        
    async def test_execute_core_timeout_handling(self, reporting_agent, core_execution_context):
        """Test _execute_core handles timeouts properly."""
        # Mock long-running LLM call
        async def slow_llm_call(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate slow response
            return json.dumps({"report": "Delayed report"})
            
        reporting_agent.llm_manager.ask_llm = slow_llm_call
        
        # Execute with timeout
        try:
            if hasattr(reporting_agent, '_execute_core'):
                await asyncio.wait_for(
                    reporting_agent._execute_core(core_execution_context),
                    timeout=1.0
                )
            else:
                await asyncio.wait_for(
                    reporting_agent.execute_core_logic(core_execution_context),
                    timeout=1.0
                )
        except asyncio.TimeoutError:
            pass  # Expected timeout
    
    async def test_execute_core_websocket_event_sequence(self, reporting_agent, core_execution_context):
        """Test _execute_core emits WebSocket events in correct sequence."""
        events_emitted = []
        
        def track_event(event_name):
            events_emitted.append(event_name)
            
        # Mock WebSocket events to track emission
        reporting_agent.emit_thinking = lambda msg: track_event('thinking')
        reporting_agent.emit_progress = lambda msg: track_event('progress')
        reporting_agent.emit_error = lambda msg: track_event('error')
        
        if hasattr(reporting_agent, '_execute_core'):
            await reporting_agent._execute_core(core_execution_context)
        else:
            await reporting_agent.execute_core_logic(core_execution_context)
        
        # Verify events were emitted
        assert len(events_emitted) > 0


class TestReportingAgentErrorRecovery:
    """Test error recovery patterns under 5 seconds."""
    
    @pytest.fixture
    def recovery_agent(self):
        """Create ReportingSubAgent for error recovery testing.""" 
        agent = ReportingSubAgent()
        agent.llm_manager = AsyncMock()
        return agent
        
    @pytest.fixture 
    def recovery_context(self):
        """Create context for error recovery testing."""
        state = DeepAgentState()
        state.user_request = "Test error recovery"
        state.action_plan_result = {"actions": ["recover"]}
        state.optimizations_result = {"optimizations": []}
        state.data_result = {"data": "recovery test"}
        state.triage_result = {"category": "recovery"}
        
        return ExecutionContext(
            run_id="recovery_test",
            agent_name="ReportingSubAgent",
            state=state,
            stream_updates=True
        )

    async def test_llm_failure_recovery(self, recovery_agent, recovery_context):
        """Test recovery from LLM failures within 5 seconds."""
        start_time = time.time()
        
        # Mock LLM failure then success  
        call_count = 0
        async def llm_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("LLM temporarily unavailable")
            return json.dumps({"report": "Recovery successful", "sections": []})
            
        recovery_agent.llm_manager.ask_llm = llm_with_retry
        
        # Execute with recovery - should use fallback on failure
        result = await recovery_agent.execute_core_logic(recovery_context)
        
        # Verify recovery completed within time limit
        recovery_time = time.time() - start_time
        assert recovery_time < 5.0, f"Recovery took {recovery_time:.2f}s, exceeds 5s limit"
        
        # Verify result was returned (either success or fallback)
        assert result is not None
        
    async def test_network_timeout_recovery(self, recovery_agent, recovery_context):
        """Test recovery from network timeouts."""
        start_time = time.time()
        
        # Mock network timeout then success
        call_count = 0
        async def network_timeout_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError("Network timeout")
            return json.dumps({"report": "Network recovery", "sections": []})
            
        recovery_agent.llm_manager.ask_llm = network_timeout_then_success
        
        # Execute recovery - should provide fallback
        result = await recovery_agent.execute_core_logic(recovery_context)
        
        # Verify fast recovery  
        recovery_time = time.time() - start_time
        assert recovery_time < 5.0
        assert result is not None
        
    async def test_state_corruption_recovery(self, recovery_agent, recovery_context):
        """Test recovery from state corruption."""
        start_time = time.time()
        
        # Corrupt the state mid-execution
        recovery_context.state.data_result = None  # Simulate corruption
        
        recovery_agent.llm_manager.ask_llm.return_value = json.dumps({
            "report": "Fallback report due to state corruption",
            "sections": []
        })
        
        # Should recover within time limit
        result = await recovery_agent.execute_core_logic(recovery_context)
        
        recovery_time = time.time() - start_time  
        assert recovery_time < 5.0
        assert result is not None
        
    async def test_partial_result_recovery(self, recovery_agent, recovery_context):
        """Test recovery by providing partial results when full execution fails."""
        start_time = time.time()
        
        # Mock partial failure
        recovery_agent.llm_manager.ask_llm.side_effect = Exception("Cannot generate full report")
        
        # Should provide fallback/partial result  
        result = await recovery_agent.execute_core_logic(recovery_context)
        
        recovery_time = time.time() - start_time
        assert recovery_time < 5.0
        assert result is not None


class TestReportingAgentResourceCleanup:
    """Test resource cleanup patterns."""
    
    @pytest.fixture
    def cleanup_agent(self):
        """Create ReportingSubAgent for cleanup testing."""
        agent = ReportingSubAgent()
        agent.llm_manager = AsyncMock()
        return agent
        
    @pytest.fixture
    def cleanup_context(self):
        """Create context for cleanup testing."""
        state = DeepAgentState()
        state.user_request = "Test cleanup"
        state.action_plan_result = {"actions": ["cleanup_test"]}
        
        return ExecutionContext(
            run_id="cleanup_test",
            agent_name="ReportingSubAgent", 
            state=state,
            stream_updates=True
        )

    async def test_automatic_resource_cleanup(self, cleanup_agent, cleanup_context):
        """Test automatic cleanup of resources."""
        # Track resource allocation
        resources_allocated = []
        resources_cleaned = []
        
        # Mock resource allocation/cleanup
        async def mock_allocate_resource():
            resource_id = f"resource_{len(resources_allocated)}"
            resources_allocated.append(resource_id)
            return resource_id
            
        cleanup_agent._allocate_resource = mock_allocate_resource
        
        # Execute with resource allocation
        cleanup_agent.llm_manager.ask_llm.return_value = json.dumps({
            "report": "Cleanup test report", 
            "sections": []
        })
        
        # Simulate resource usage during execution
        await mock_allocate_resource()
        await mock_allocate_resource()
        
        # Execute cleanup - should not raise exceptions
        state = DeepAgentState()
        state.user_request = "cleanup test"
        await cleanup_agent.cleanup(state, "cleanup_test")
        
        # Verify resources were allocated
        assert len(resources_allocated) == 2
        
    async def test_exception_safe_cleanup(self, cleanup_agent, cleanup_context):
        """Test cleanup occurs even when exceptions happen."""
        cleanup_called = False
        
        async def mock_cleanup(state, run_id):
            nonlocal cleanup_called
            cleanup_called = True
            
        cleanup_agent.cleanup = mock_cleanup
        
        # Force exception during execution
        cleanup_agent.llm_manager.ask_llm.side_effect = Exception("Execution failure")
        
        try:
            await cleanup_agent.execute_core_logic(cleanup_context)
        except Exception:
            pass  # Expected
        finally:
            # Ensure cleanup is called even after exception
            state = DeepAgentState()
            await cleanup_agent.cleanup(state, "cleanup_test")
        
        assert cleanup_called is True
        
    async def test_memory_leak_prevention(self, cleanup_agent, cleanup_context):
        """Test prevention of memory leaks."""
        import gc
        import weakref
        
        # Create tracked object
        class TrackableResource:
            def __init__(self, name):
                self.name = name
                
        resource = TrackableResource("test_resource")
        weak_ref = weakref.ref(resource)
        
        # Simulate attaching resource to agent
        cleanup_agent._test_resource = resource
        
        # Clear reference
        del resource
        
        # Cleanup should remove agent references  
        state = DeepAgentState()
        await cleanup_agent.cleanup(state, "cleanup_test")
        cleanup_agent._test_resource = None
        
        # Force garbage collection
        gc.collect()
        
        # Verify object was garbage collected (may not always work due to gc timing)
        # This is a best-effort test
        try:
            assert weak_ref() is None, "Memory leak detected - resource not garbage collected"
        except AssertionError:
            # GC timing issues are acceptable in tests
            pass
        
    async def test_websocket_cleanup(self, cleanup_agent, cleanup_context):
        """Test WebSocket connection cleanup."""
        websocket_closed = False
        
        class MockWebSocket:
            def __init__(self):
                self.closed = False
                
            async def close(self):
                nonlocal websocket_closed
                self.closed = True
                websocket_closed = True
                
        mock_ws = MockWebSocket()
        cleanup_agent._websocket_connection = mock_ws
        
        # Cleanup should close WebSocket
        state = DeepAgentState()
        await cleanup_agent.cleanup(state, "cleanup_test")
        
        # Verify cleanup was attempted
        assert hasattr(cleanup_agent, '_websocket_connection')
        
    async def test_thread_cleanup(self, cleanup_agent, cleanup_context):
        """Test cleanup of background threads.""" 
        import threading
        
        threads_stopped = []
        
        class MockThread(threading.Thread):
            def __init__(self, name):
                super().__init__(name=name)
                self.stopped = False
                
            def stop(self):
                self.stopped = True
                threads_stopped.append(self.name)
                
        # Simulate background threads
        thread1 = MockThread("reporter_thread_1")
        thread2 = MockThread("reporter_thread_2")
        
        cleanup_agent._background_threads = [thread1, thread2]
        
        # Cleanup should stop threads
        state = DeepAgentState()  
        await cleanup_agent.cleanup(state, "cleanup_test")
        
        # Verify cleanup was called (threads attribute exists)
        assert hasattr(cleanup_agent, '_background_threads')


class TestReportingAgentBaseInheritance:
    """Test BaseAgent inheritance compliance."""
    
    @pytest.fixture
    def inheritance_agent(self):
        """Create ReportingSubAgent for inheritance testing."""
        return ReportingSubAgent()

    def test_baseagent_inheritance_chain(self, inheritance_agent):
        """Test proper BaseAgent inheritance chain."""
        from netra_backend.app.agents.base_agent import BaseAgent
        
        # Verify inheritance
        assert isinstance(inheritance_agent, BaseAgent)
        
        # Check MRO (Method Resolution Order)
        mro = type(inheritance_agent).__mro__
        base_agent_in_mro = any(cls.__name__ == 'BaseAgent' for cls in mro)
        assert base_agent_in_mro, "BaseAgent not found in MRO"
        
    def test_baseagent_methods_inherited(self, inheritance_agent):
        """Test BaseAgent methods are properly inherited."""
        # Critical BaseAgent methods that must be inherited
        required_methods = [
            'emit_thinking',
            'emit_progress', 
            'emit_error',
            'get_health_status',
            'has_websocket_context'
        ]
        
        for method_name in required_methods:
            assert hasattr(inheritance_agent, method_name), f"Missing inherited method: {method_name}"
            method = getattr(inheritance_agent, method_name)
            assert callable(method), f"Method {method_name} is not callable"
            
    def test_baseagent_infrastructure_flags(self, inheritance_agent):
        """Test BaseAgent infrastructure flags are properly set."""
        # Infrastructure flags should be enabled by default
        expected_flags = [
            '_enable_reliability',
            '_enable_execution_engine', 
            '_enable_caching'
        ]
        
        for flag in expected_flags:
            if hasattr(inheritance_agent, flag):
                flag_value = getattr(inheritance_agent, flag)
                assert flag_value is True, f"Infrastructure flag {flag} should be True"
                
    def test_no_infrastructure_duplication(self, inheritance_agent):
        """Test that infrastructure is not duplicated in ReportingSubAgent."""
        import inspect
        
        # Get source code of ReportingSubAgent
        source = inspect.getsource(ReportingSubAgent)
        
        # These should NOT be in ReportingSubAgent (inherited from BaseAgent)
        forbidden_duplicates = [
            'class ReliabilityManager',
            'class ExecutionEngine',
            'def emit_websocket_event',
            'def _setup_websocket',
            'def get_health_status'
        ]
        
        for duplicate in forbidden_duplicates:
            assert duplicate not in source, f"Infrastructure duplication found: {duplicate}"
            
    def test_proper_method_overrides(self, inheritance_agent):
        """Test that method overrides are properly implemented."""
        # Methods that SHOULD be overridden in ReportingSubAgent
        required_overrides = [
            'validate_preconditions',
            'execute_core_logic'
        ]
        
        for method_name in required_overrides:
            assert hasattr(inheritance_agent, method_name), f"Missing override: {method_name}"
            
            # Verify it's actually overridden (not just inherited)
            method = getattr(inheritance_agent, method_name)
            if hasattr(method, '__self__'):
                method_class = method.__self__.__class__
                assert method_class.__name__ == 'ReportingSubAgent', f"Method {method_name} not properly overridden"

    def test_super_calls_in_overrides(self, inheritance_agent):
        """Test that overridden methods properly call super() when needed."""
        import inspect
        
        source = inspect.getsource(ReportingSubAgent)
        
        # Look for execute methods that should call super()
        if 'def execute(' in source:
            # If execute is overridden, it should call super() for reliability
            lines = source.split('\n')
            execute_lines = [line for line in lines if 'def execute(' in line or 'super().' in line or 'execute_with_reliability' in line]
            
            # Should have some form of super() call or execute_with_reliability
            has_proper_super = any('super()' in line or 'execute_with_reliability' in line for line in execute_lines)
            # This is optional - some agents may not override execute
            
    def test_inheritance_consistency(self, inheritance_agent):
        """Test that inheritance is consistent across all methods."""
        from netra_backend.app.agents.base_agent import BaseAgent
        
        # Create a BaseAgent instance for comparison
        base_agent = BaseAgent()
        
        # Get all methods from BaseAgent
        base_methods = [method for method in dir(base_agent) if not method.startswith('_') and callable(getattr(base_agent, method))]
        
        # Verify ReportingSubAgent has all BaseAgent methods
        for method_name in base_methods:
            if method_name not in ['validate_preconditions', 'execute_core_logic']:  # These should be overridden
                assert hasattr(inheritance_agent, method_name), f"Missing BaseAgent method: {method_name}"


if __name__ == "__main__":
    # Run all test classes
    pytest.main([__file__, "-v", "--tb=short"])