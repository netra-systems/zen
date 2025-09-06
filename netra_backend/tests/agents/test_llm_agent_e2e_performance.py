from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Performance E2E LLM Agent Tests
# REMOVED_SYNTAX_ERROR: Performance metrics, concurrency, error recovery, and complete optimization flows
# REMOVED_SYNTAX_ERROR: Split from oversized test_llm_agent_e2e_real.py to maintain 450-line limit

import asyncio
import pytest
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # Test framework import - using pytest fixtures instead

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from datetime import datetime

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import pytest_asyncio
    # REMOVED_SYNTAX_ERROR: from sqlalchemy.ext.asyncio import AsyncSession

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.state import DeepAgentState

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.llm.llm_manager import LLMManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_service import AgentService
    # REMOVED_SYNTAX_ERROR: from netra_backend.tests.agents.test_fixtures import ( )
    # REMOVED_SYNTAX_ERROR: mock_db_session,
    # REMOVED_SYNTAX_ERROR: mock_llm_manager,
    # REMOVED_SYNTAX_ERROR: mock_persistence_service,
    # REMOVED_SYNTAX_ERROR: mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager,
    # REMOVED_SYNTAX_ERROR: supervisor_agent,
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.tests.agents.fixtures.llm_agent_fixtures import ( )
    # REMOVED_SYNTAX_ERROR: create_mock_infrastructure,
    # REMOVED_SYNTAX_ERROR: create_supervisor_with_mocks,
    # REMOVED_SYNTAX_ERROR: setup_llm_responses,
    # REMOVED_SYNTAX_ERROR: setup_websocket_manager,
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.tests.agents.helpers.performance_test_helpers import ( )
    # REMOVED_SYNTAX_ERROR: create_benchmark_supervisor,
    # REMOVED_SYNTAX_ERROR: create_e2e_persistence_mock,
    # REMOVED_SYNTAX_ERROR: create_flow_persistence_mock,
    # REMOVED_SYNTAX_ERROR: create_lightweight_supervisor,
    # REMOVED_SYNTAX_ERROR: execute_lightweight_flow,
    # REMOVED_SYNTAX_ERROR: execute_optimization_flow,
    # REMOVED_SYNTAX_ERROR: run_concurrency_benchmark,
    # REMOVED_SYNTAX_ERROR: setup_e2e_responses,
    # REMOVED_SYNTAX_ERROR: verify_performance_requirements,
    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_performance_metrics(supervisor_agent):
        # REMOVED_SYNTAX_ERROR: """Test performance metric collection"""
        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: run_id = str(uuid.uuid4())

        # REMOVED_SYNTAX_ERROR: await supervisor_agent.run( )
        # REMOVED_SYNTAX_ERROR: "Test performance",
        # REMOVED_SYNTAX_ERROR: supervisor_agent.thread_id,
        # REMOVED_SYNTAX_ERROR: supervisor_agent.user_id,
        # REMOVED_SYNTAX_ERROR: run_id
        

        # REMOVED_SYNTAX_ERROR: execution_time = time.time() - start_time

        # Should complete quickly with mocked components
        # REMOVED_SYNTAX_ERROR: assert execution_time < 2.0, "formatted_string"

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_error_recovery(supervisor_agent):
            # REMOVED_SYNTAX_ERROR: """Test error handling and recovery mechanisms"""
            # Simulate error in execution pipeline
            # Mock: Async component isolation for testing without real async operations
            # REMOVED_SYNTAX_ERROR: supervisor_agent.engine.execute_pipeline = AsyncMock( )
            # REMOVED_SYNTAX_ERROR: side_effect=Exception("Pipeline error")
            

            # Should handle error gracefully
            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: await supervisor_agent.run( )
                # REMOVED_SYNTAX_ERROR: "Test error",
                # REMOVED_SYNTAX_ERROR: supervisor_agent.thread_id,
                # REMOVED_SYNTAX_ERROR: supervisor_agent.user_id,
                # REMOVED_SYNTAX_ERROR: str(uuid.uuid4())
                
                # REMOVED_SYNTAX_ERROR: except Exception as e:
                    # REMOVED_SYNTAX_ERROR: assert "Pipeline error" in str(e)

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_concurrent_request_handling_optimized():
                        # REMOVED_SYNTAX_ERROR: """Test handling multiple concurrent requests with optimized setup"""
                        # Create optimized mock infrastructure
                        # REMOVED_SYNTAX_ERROR: supervisors = _create_concurrent_supervisors(3)

                        # Run concurrent requests
                        # REMOVED_SYNTAX_ERROR: tasks = _create_concurrent_tasks(supervisors)

                        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

                        # Verify all completed
                        # REMOVED_SYNTAX_ERROR: assert len(results) == 3
                        # REMOVED_SYNTAX_ERROR: _verify_concurrent_results(results)

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_end_to_end_optimization_flow_optimized():
                            # REMOVED_SYNTAX_ERROR: """Test complete end-to-end optimization flow with optimized structure"""
                            # Create infrastructure with optimized setup
                            # REMOVED_SYNTAX_ERROR: infrastructure = _create_e2e_infrastructure()
                            # REMOVED_SYNTAX_ERROR: supervisor = _create_e2e_supervisor(infrastructure)

                            # Run full flow
                            # REMOVED_SYNTAX_ERROR: state = await _execute_e2e_flow(supervisor)

                            # Verify complete flow
                            # REMOVED_SYNTAX_ERROR: _verify_e2e_completion(state, supervisor)

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_complex_multi_step_flow():
                                # REMOVED_SYNTAX_ERROR: """Test complex multi-step optimization flow"""
                                # Create infrastructure
                                # REMOVED_SYNTAX_ERROR: db_session, llm_manager, ws_manager = create_mock_infrastructure()

                                # Setup complex responses
                                # REMOVED_SYNTAX_ERROR: _setup_complex_flow_responses(llm_manager, ws_manager)

                                # REMOVED_SYNTAX_ERROR: mock_persistence = _create_flow_persistence_mock()

                                # Create supervisor with all mocks
                                # REMOVED_SYNTAX_ERROR: supervisor = create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence)

                                # Execute multi-step flow
                                # REMOVED_SYNTAX_ERROR: state = await _execute_optimization_flow(supervisor)

                                # Verify flow completion
                                # REMOVED_SYNTAX_ERROR: _verify_optimization_flow(state, supervisor)

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_flow_interruption_and_recovery():
                                    # REMOVED_SYNTAX_ERROR: """Test flow interruption and recovery scenarios"""
                                    # REMOVED_SYNTAX_ERROR: db_session, llm_manager, ws_manager = create_mock_infrastructure()

                                    # Create interrupted state scenario
                                    # REMOVED_SYNTAX_ERROR: interrupted_state = _create_interrupted_state()

                                    # REMOVED_SYNTAX_ERROR: mock_persistence = _create_recovery_persistence_mock(interrupted_state)

                                    # Test recovery
                                    # REMOVED_SYNTAX_ERROR: recovered_state = await mock_persistence.load_agent_state("thread123", "user123")
                                    # REMOVED_SYNTAX_ERROR: _verify_recovery_state(recovered_state)

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_flow_performance_benchmarks():
                                        # REMOVED_SYNTAX_ERROR: """Test flow performance under various conditions"""
                                        # REMOVED_SYNTAX_ERROR: performance_metrics = []

                                        # REMOVED_SYNTAX_ERROR: for concurrency_level in [1, 3, 5]:
                                            # REMOVED_SYNTAX_ERROR: metrics = await _run_performance_benchmark(concurrency_level)
                                            # REMOVED_SYNTAX_ERROR: performance_metrics.append(metrics)

                                            # Verify performance is reasonable
                                            # REMOVED_SYNTAX_ERROR: _verify_performance_metrics(performance_metrics)

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_high_load_scenarios():
                                                # REMOVED_SYNTAX_ERROR: """Test system behavior under high load"""
                                                # Create high load scenario
                                                # REMOVED_SYNTAX_ERROR: task_count = 10
                                                # REMOVED_SYNTAX_ERROR: start_time = time.time()

                                                # REMOVED_SYNTAX_ERROR: tasks = []
                                                # REMOVED_SYNTAX_ERROR: for i in range(task_count):
                                                    # REMOVED_SYNTAX_ERROR: infrastructure = _create_lightweight_infrastructure()
                                                    # REMOVED_SYNTAX_ERROR: supervisor = _create_lightweight_supervisor(infrastructure)
                                                    # REMOVED_SYNTAX_ERROR: tasks.append(_execute_lightweight_flow(supervisor))

                                                    # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)
                                                    # REMOVED_SYNTAX_ERROR: execution_time = time.time() - start_time

                                                    # Verify high load performance
                                                    # REMOVED_SYNTAX_ERROR: success_count = len([item for item in []])
                                                    # REMOVED_SYNTAX_ERROR: assert success_count >= task_count * 0.8  # 80% success rate
                                                    # REMOVED_SYNTAX_ERROR: assert execution_time < 10.0  # Should complete within 10 seconds

# REMOVED_SYNTAX_ERROR: def _create_concurrent_supervisors(count):
    # REMOVED_SYNTAX_ERROR: """Create supervisors for concurrent testing"""
    # REMOVED_SYNTAX_ERROR: supervisors = []
    # REMOVED_SYNTAX_ERROR: for i in range(count):
        # REMOVED_SYNTAX_ERROR: infrastructure = _create_mock_infrastructure_light()
        # REMOVED_SYNTAX_ERROR: supervisor = _create_lightweight_supervisor(infrastructure)
        # REMOVED_SYNTAX_ERROR: supervisors.append(supervisor)
        # REMOVED_SYNTAX_ERROR: return supervisors

# REMOVED_SYNTAX_ERROR: def _create_concurrent_tasks(supervisors):
    # REMOVED_SYNTAX_ERROR: """Create concurrent execution tasks"""
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: supervisor.run( )
    # REMOVED_SYNTAX_ERROR: "formatted_string",
    # REMOVED_SYNTAX_ERROR: supervisor.thread_id,
    # REMOVED_SYNTAX_ERROR: supervisor.user_id,
    # REMOVED_SYNTAX_ERROR: str(uuid.uuid4())
    
    # REMOVED_SYNTAX_ERROR: for i, supervisor in enumerate(supervisors)
    

# REMOVED_SYNTAX_ERROR: def _verify_concurrent_results(results):
    # REMOVED_SYNTAX_ERROR: """Verify concurrent execution results"""
    # REMOVED_SYNTAX_ERROR: for result in results:
        # REMOVED_SYNTAX_ERROR: if not isinstance(result, Exception):
            # REMOVED_SYNTAX_ERROR: assert isinstance(result, DeepAgentState)

# REMOVED_SYNTAX_ERROR: def _create_e2e_infrastructure():
    # REMOVED_SYNTAX_ERROR: """Create infrastructure for end-to-end testing"""
    # Mock: Database session isolation for transaction testing without real database dependency
    # REMOVED_SYNTAX_ERROR: db_session = AsyncMock(spec=AsyncSession)
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    # REMOVED_SYNTAX_ERROR: llm_manager = Mock(spec=LLMManager)
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: ws_manager = UnifiedWebSocketManager()
    # REMOVED_SYNTAX_ERROR: return (db_session, llm_manager, ws_manager)

# REMOVED_SYNTAX_ERROR: def _create_e2e_supervisor(infrastructure):
    # REMOVED_SYNTAX_ERROR: """Create supervisor for end-to-end testing"""
    # REMOVED_SYNTAX_ERROR: db_session, llm_manager, ws_manager = infrastructure
    # REMOVED_SYNTAX_ERROR: _setup_e2e_responses(llm_manager)
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: ws_manager.send_message = AsyncMock()  # TODO: Use real service instance

    # REMOVED_SYNTAX_ERROR: mock_persistence = _create_e2e_persistence_mock()
    # REMOVED_SYNTAX_ERROR: return create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence)

# REMOVED_SYNTAX_ERROR: async def _execute_e2e_flow(supervisor):
    # REMOVED_SYNTAX_ERROR: """Execute end-to-end optimization flow"""
    # REMOVED_SYNTAX_ERROR: return await supervisor.run( )
    # REMOVED_SYNTAX_ERROR: "Optimize my LLM workload for better memory usage",
    # REMOVED_SYNTAX_ERROR: supervisor.thread_id,
    # REMOVED_SYNTAX_ERROR: supervisor.user_id,
    # REMOVED_SYNTAX_ERROR: str(uuid.uuid4())
    

# REMOVED_SYNTAX_ERROR: def _verify_e2e_completion(state, supervisor):
    # REMOVED_SYNTAX_ERROR: """Verify end-to-end flow completion"""
    # REMOVED_SYNTAX_ERROR: assert state is not None
    # REMOVED_SYNTAX_ERROR: assert supervisor.engine.execute_pipeline.called

# REMOVED_SYNTAX_ERROR: def _setup_complex_flow_responses(llm_manager, ws_manager):
    # REMOVED_SYNTAX_ERROR: """Setup complex flow responses"""
    # REMOVED_SYNTAX_ERROR: setup_llm_responses(llm_manager)
    # REMOVED_SYNTAX_ERROR: setup_websocket_manager(ws_manager)

# REMOVED_SYNTAX_ERROR: def _create_flow_persistence_mock():
    # REMOVED_SYNTAX_ERROR: """Create persistence mock for flow testing"""
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_persistence = AsyncMock()  # TODO: Use real service instance
    # Mock: Agent service isolation for testing without LLM agent execution
    # REMOVED_SYNTAX_ERROR: mock_persistence.save_agent_state = AsyncMock(return_value=(True, "test_id"))
    # Mock: Agent service isolation for testing without LLM agent execution
    # REMOVED_SYNTAX_ERROR: mock_persistence.load_agent_state = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    # REMOVED_SYNTAX_ERROR: mock_persistence.get_thread_context = AsyncMock(return_value=None)
    # Mock: Agent service isolation for testing without LLM agent execution
    # REMOVED_SYNTAX_ERROR: mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    # REMOVED_SYNTAX_ERROR: return mock_persistence

# REMOVED_SYNTAX_ERROR: async def _execute_optimization_flow(supervisor):
    # REMOVED_SYNTAX_ERROR: """Execute optimization flow and return result"""
    # REMOVED_SYNTAX_ERROR: return await supervisor.run( )
    # REMOVED_SYNTAX_ERROR: "Optimize my LLM workload for better memory usage",
    # REMOVED_SYNTAX_ERROR: supervisor.thread_id,
    # REMOVED_SYNTAX_ERROR: supervisor.user_id,
    # REMOVED_SYNTAX_ERROR: str(uuid.uuid4())
    

# REMOVED_SYNTAX_ERROR: def _verify_optimization_flow(state, supervisor):
    # REMOVED_SYNTAX_ERROR: """Verify optimization flow completed successfully"""
    # REMOVED_SYNTAX_ERROR: assert state is not None
    # REMOVED_SYNTAX_ERROR: assert supervisor.engine.execute_pipeline.called

# REMOVED_SYNTAX_ERROR: def _create_interrupted_state():
    # REMOVED_SYNTAX_ERROR: """Create interrupted state for testing"""
    # REMOVED_SYNTAX_ERROR: interrupted_state = DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="Interrupted optimization",
    # REMOVED_SYNTAX_ERROR: chat_thread_id="thread123",
    # REMOVED_SYNTAX_ERROR: user_id="user123"
    
    # REMOVED_SYNTAX_ERROR: interrupted_state.triage_result = {"category": "optimization", "step": "analysis"}
    # REMOVED_SYNTAX_ERROR: return interrupted_state

# REMOVED_SYNTAX_ERROR: def _create_recovery_persistence_mock(interrupted_state):
    # REMOVED_SYNTAX_ERROR: """Create recovery persistence mock"""
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: mock_persistence = AsyncMock()  # TODO: Use real service instance
    # Mock: Agent service isolation for testing without LLM agent execution
    # REMOVED_SYNTAX_ERROR: mock_persistence.load_agent_state = AsyncMock(return_value=interrupted_state)
    # Mock: Agent service isolation for testing without LLM agent execution
    # REMOVED_SYNTAX_ERROR: mock_persistence.save_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    # Mock: Agent service isolation for testing without LLM agent execution
    # REMOVED_SYNTAX_ERROR: mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    # REMOVED_SYNTAX_ERROR: return mock_persistence

# REMOVED_SYNTAX_ERROR: def _verify_recovery_state(recovered_state):
    # REMOVED_SYNTAX_ERROR: """Verify recovered state"""
    # REMOVED_SYNTAX_ERROR: assert recovered_state.user_request == "Interrupted optimization"
    # REMOVED_SYNTAX_ERROR: assert recovered_state.triage_result["step"] == "analysis"

# REMOVED_SYNTAX_ERROR: async def _run_performance_benchmark(concurrency_level):
    # REMOVED_SYNTAX_ERROR: """Run performance benchmark for given concurrency level"""
    # REMOVED_SYNTAX_ERROR: start_time = time.time()

    # Create concurrent flows
    # REMOVED_SYNTAX_ERROR: tasks = []
    # REMOVED_SYNTAX_ERROR: for i in range(concurrency_level):
        # REMOVED_SYNTAX_ERROR: infrastructure = _create_benchmark_infrastructure()
        # REMOVED_SYNTAX_ERROR: supervisor = _create_benchmark_supervisor(infrastructure, i)
        # REMOVED_SYNTAX_ERROR: tasks.append(_execute_optimization_flow(supervisor))

        # Execute all tasks
        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)
        # REMOVED_SYNTAX_ERROR: execution_time = time.time() - start_time

        # REMOVED_SYNTAX_ERROR: return { )
        # REMOVED_SYNTAX_ERROR: "concurrency": concurrency_level,
        # REMOVED_SYNTAX_ERROR: "execution_time": execution_time,
        # REMOVED_SYNTAX_ERROR: "success_rate": len([item for item in []]) / len(results)
        

# REMOVED_SYNTAX_ERROR: def _verify_performance_metrics(performance_metrics):
    # REMOVED_SYNTAX_ERROR: """Verify performance metrics meet requirements"""
    # REMOVED_SYNTAX_ERROR: for metric in performance_metrics:
        # REMOVED_SYNTAX_ERROR: assert metric["execution_time"] < 5.0  # Should complete within 5 seconds
        # REMOVED_SYNTAX_ERROR: assert metric["success_rate"] >= 0.8  # At least 80% success rate

# REMOVED_SYNTAX_ERROR: def _create_mock_infrastructure_light():
    # REMOVED_SYNTAX_ERROR: """Create lightweight mock infrastructure"""
    # Mock: Database session isolation for transaction testing without real database dependency
    # REMOVED_SYNTAX_ERROR: db_session = AsyncMock(spec=AsyncSession)
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    # REMOVED_SYNTAX_ERROR: llm_manager = Mock(spec=LLMManager)
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: ws_manager = UnifiedWebSocketManager()
    # REMOVED_SYNTAX_ERROR: return (db_session, llm_manager, ws_manager)

# REMOVED_SYNTAX_ERROR: def _create_lightweight_infrastructure():
    # REMOVED_SYNTAX_ERROR: """Create lightweight infrastructure for testing"""
    # REMOVED_SYNTAX_ERROR: return _create_mock_infrastructure_light()

# REMOVED_SYNTAX_ERROR: def _create_lightweight_supervisor(infrastructure):
    # REMOVED_SYNTAX_ERROR: """Create lightweight supervisor"""
    # REMOVED_SYNTAX_ERROR: return create_lightweight_supervisor(infrastructure)

# REMOVED_SYNTAX_ERROR: async def _execute_lightweight_flow(supervisor):
    # REMOVED_SYNTAX_ERROR: """Execute lightweight flow"""
    # REMOVED_SYNTAX_ERROR: return await execute_lightweight_flow(supervisor)

# REMOVED_SYNTAX_ERROR: def _create_benchmark_infrastructure():
    # REMOVED_SYNTAX_ERROR: """Create benchmark infrastructure"""
    # REMOVED_SYNTAX_ERROR: return create_mock_infrastructure()

# REMOVED_SYNTAX_ERROR: def _create_benchmark_supervisor(infrastructure, index):
    # REMOVED_SYNTAX_ERROR: """Create benchmark supervisor"""
    # REMOVED_SYNTAX_ERROR: return create_benchmark_supervisor(infrastructure, index)

    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])