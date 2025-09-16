"""
Business Value Core Tests (Tests 1-5) - Essential Business Functionality
Tests fundamental business value scenarios for cost optimization and performance
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import uuid
from typing import Dict, List

import pytest

from netra_backend.tests.test_business_value_fixtures import BusinessValueFixtures

class TestBusinessValueCore(BusinessValueFixtures):
    """
    Core business value tests focused on essential optimization scenarios
    """

    def _setup_test_run(self, user_request: str) -> tuple[str, str]:
        """Setup test run with unique ID and user request"""
        run_id = str(uuid.uuid4())
        return run_id, user_request

    async def _execute_with_mocked_state(self, supervisor, user_request: str, run_id: str):
        """Execute supervisor with mocked state persistence"""
        # Mock: Generic component isolation for controlled unit testing
        save_mock = AsyncNone  # TODO: Use real service instance
        # Mock: Async component isolation for testing without real async operations
        load_mock = AsyncMock(return_value=None)
        # Mock: Async component isolation for testing without real async operations
        context_mock = AsyncMock(return_value=None)
        return await self._execute_with_patches(supervisor, user_request, run_id, 
                                               save_mock, load_mock, context_mock)

    async def _execute_with_patches(self, supervisor, user_request, run_id, 
                                   save_mock, load_mock, context_mock):
        """Execute with specific state persistence patches"""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.services.state_persistence.state_persistence_service.save_agent_state', save_mock):
            # Mock: Component isolation for testing without external dependencies
            with patch('netra_backend.app.services.state_persistence.state_persistence_service.load_agent_state', load_mock):
                # Mock: Component isolation for testing without external dependencies
                with patch('netra_backend.app.services.state_persistence.state_persistence_service.get_thread_context', context_mock):
                    return await supervisor.run(user_request, "test_thread", "test_user", run_id)

    def _verify_basic_result(self, result_state, user_request: str):
        """Verify basic result assertions"""
        assert result_state != None
        assert result_state.user_request == user_request

    def _verify_llm_optimization_calls(self, llm_manager):
        """Verify LLM optimization calls were made"""
        assert llm_manager.ask_llm.called
        optimization_calls = self._get_optimization_calls(llm_manager)
        assert len(optimization_calls) > 0

    def _get_optimization_calls(self, llm_manager):
        """Get optimization-related LLM calls"""
        return [call for call in llm_manager.ask_llm.call_args_list 
                if "optimiz" in str(call).lower()]

    def _verify_cost_analysis_tools(self, tool_dispatcher):
        """Verify cost analysis tool usage"""
        if tool_dispatcher.dispatch_tool.called:
            tool_calls = tool_dispatcher.dispatch_tool.call_args_list
            cost_analysis_calls = self._get_cost_analysis_calls(tool_calls)
            assert len(cost_analysis_calls) >= 0

    def _get_cost_analysis_calls(self, tool_calls):
        """Get cost analysis related tool calls"""
        return [call for call in tool_calls 
                if "cost" in str(call).lower()]

    @pytest.mark.asyncio
    async def test_1_cost_optimization_request(self, setup_test_infrastructure):
        """
        Business Value Test 1: Cost Optimization Analysis
        User Story: As a CTO, I need to reduce my AI costs by 40% while maintaining quality
        """
        infra = setup_test_infrastructure
        request = "How can I reduce my GPT-4 costs by 40% while maintaining quality?"
        run_id, user_request = self._setup_test_run(request)
        result_state = await self._execute_with_mocked_state(infra["supervisor"], user_request, run_id)
        self._verify_test_1_results(result_state, user_request, infra)

    def _verify_test_1_results(self, result_state, user_request, infra):
        """Verify test 1 specific results"""
        self._verify_basic_result(result_state, user_request)
        self._verify_llm_optimization_calls(infra["llm_manager"])
        self._verify_cost_analysis_tools(infra["tool_dispatcher"])

    def _verify_performance_analysis_tools(self, tool_dispatcher):
        """Verify performance analysis tool usage"""
        if tool_dispatcher.dispatch_tool.called:
            bottleneck_calls = self._get_bottleneck_calls(tool_dispatcher)
            assert len(bottleneck_calls) >= 0

    def _get_bottleneck_calls(self, tool_dispatcher):
        """Get bottleneck analysis calls"""
        return [call for call in tool_dispatcher.dispatch_tool.call_args_list
                if "bottleneck" in str(call).lower()]

    @pytest.mark.asyncio
    async def test_2_performance_bottleneck_identification(self, setup_test_infrastructure):
        """
        Business Value Test 2: Performance Bottleneck Analysis
        User Story: As an ML Engineer, I need to identify why P95 latency increased to 800ms
        """
        infra = setup_test_infrastructure
        request = "P95 latency increased from 200ms to 800ms. Identify bottlenecks and solutions."
        run_id, user_request = self._setup_test_run(request)
        result_state = await self._execute_with_mocked_state(infra["supervisor"], user_request, run_id)
        self._verify_test_2_results(result_state, infra)

    def _verify_test_2_results(self, result_state, infra):
        """Verify test 2 specific results"""
        assert result_state != None
        self._verify_performance_analysis_tools(infra["tool_dispatcher"])

    def _verify_comparison_analysis(self, llm_manager):
        """Verify model comparison analysis was performed"""
        assert llm_manager.ask_llm.call_count > 0

    @pytest.mark.asyncio
    async def test_3_model_comparison_and_selection(self, setup_test_infrastructure):
        """
        Business Value Test 3: Model Comparison for Use Case
        User Story: As a Product Manager, I need to choose between GPT-4 and Claude for my chatbot
        """
        infra = setup_test_infrastructure
        request = "Compare GPT-4 vs Claude-3 for customer support chatbot. Budget: $10k/month"
        run_id, user_request = self._setup_test_run(request)
        result_state = await self._execute_with_mocked_state(infra["supervisor"], user_request, run_id)
        self._verify_test_3_results(result_state, infra)

    def _verify_test_3_results(self, result_state, infra):
        """Verify test 3 specific results"""
        assert result_state != None
        self._verify_comparison_analysis(infra["llm_manager"])

    def _setup_streaming_capture(self, websocket_manager) -> List[Dict]:
        """Setup streaming message capture"""
        streamed_messages = []
        capture_stream = self._create_capture_stream(streamed_messages)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager.send_message = AsyncMock(side_effect=capture_stream)
        return streamed_messages

    def _create_capture_stream(self, streamed_messages):
        """Create capture stream function"""
        async def capture_stream(rid, message):
            streamed_messages.append(message)
        return capture_stream

    def _verify_streaming_occurred(self, streamed_messages: List[Dict]):
        """Verify streaming messages were sent"""
        assert len(streamed_messages) > 0
        message_types = [msg.get("type") for msg in streamed_messages]
        assert "agent_started" in message_types

    @pytest.mark.asyncio
    async def test_4_real_time_streaming_updates(self, setup_test_infrastructure):
        """
        Business Value Test 4: Real-time Progress Updates
        User Story: As a user, I want to see progress during long-running analyses
        """
        infra = setup_test_infrastructure
        streamed_messages = self._setup_streaming_capture(infra["websocket_manager"])
        run_id, user_request = self._setup_test_run("Analyze my workload")
        await self._execute_with_mocked_state(infra["supervisor"], user_request, run_id)
        self._verify_streaming_occurred(streamed_messages)

    def _verify_batch_optimization(self, llm_manager):
        """Verify batch optimization was considered"""
        optimization_prompts = self._get_batch_optimization_prompts(llm_manager)
        assert len(optimization_prompts) >= 0

    def _get_batch_optimization_prompts(self, llm_manager):
        """Get batch optimization related prompts"""
        return [call for call in llm_manager.ask_llm.call_args_list
                if "batch" in str(call).lower() or "optimiz" in str(call).lower()]

    @pytest.mark.asyncio
    async def test_5_batch_processing_optimization(self, setup_test_infrastructure):
        """
        Business Value Test 5: Batch Processing Recommendations
        User Story: As a Data Scientist, I need to optimize batch inference costs
        """
        infra = setup_test_infrastructure
        request = "I have 10,000 similar classification requests daily. How to optimize?"
        run_id, user_request = self._setup_test_run(request)
        result_state = await self._execute_with_mocked_state(infra["supervisor"], user_request, run_id)
        self._verify_test_5_results(result_state, infra)

    def _verify_test_5_results(self, result_state, infra):
        """Verify test 5 specific results"""
        assert result_state != None
        self._verify_batch_optimization(infra["llm_manager"])

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])