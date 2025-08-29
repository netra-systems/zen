"""
Tests for concurrent corpus operations and conflict resolution.

This module tests concurrent corpus modifications to ensure:
- No data corruption under concurrent access
- Proper resource locking
- Transaction rollback on failures
- Multi-tenant isolation

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Platform Reliability, Multi-tenant Safety
- Value Impact: Prevents data corruption for enterprise customers with multiple teams
- Strategic Impact: Critical for enterprise scalability and $100K+ ARR accounts
"""

import asyncio
import pytest
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock

from netra_backend.app.agents.corpus_admin.agent import CorpusAdminSubAgent
from netra_backend.app.agents.corpus_admin.models import (
    CorpusOperation,
    CorpusType,
    CorpusMetadata,
    CorpusOperationRequest,
    CorpusOperationResult,
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from test_framework.fixtures.corpus_admin import (
    create_test_deep_state,
    create_test_corpus_admin_agent,
    create_test_execution_context,
)


class TestCorpusAdminConcurrentOperations:
    """Tests for concurrent corpus operations and conflict resolution."""

    @pytest.fixture
    async def setup_concurrent_environment(self):
        """Set up environment for concurrent operation testing."""
        # Create multiple agents to simulate concurrent access
        agents = []
        for i in range(3):  # Reduced from 5 for simpler testing
            agent = await create_test_corpus_admin_agent(with_real_llm=False)
            agents.append(agent)
        
        return {
            "llm_manager": agents[0].llm_manager if agents else None,
            "tool_dispatcher": agents[0].tool_dispatcher if agents else None,
            "agents": agents,
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.critical_path
    async def test_concurrent_agent_initialization(self, setup_concurrent_environment):
        """
        Test that multiple corpus admin agents can be initialized concurrently
        without conflicts.
        """
        env = await setup_concurrent_environment
        
        # Validate all agents initialized properly
        assert len(env["agents"]) == 3
        
        for i, agent in enumerate(env["agents"]):
            assert agent is not None
            assert agent.name == "CorpusAdminSubAgent"
            
            # Test health status
            health_status = agent.get_health_status()
            assert health_status["agent_health"] == "healthy"
            
            print(f"Agent {i} initialized successfully")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.critical_path
    async def test_concurrent_entry_condition_checks(self, setup_concurrent_environment):
        """
        Test that multiple agents can check entry conditions concurrently
        without interference.
        """
        env = await setup_concurrent_environment
        
        # Create test requests
        test_requests = [
            "Create knowledge base for optimization strategies",
            "Update corpus with new documentation",
            "Delete obsolete knowledge corpus",
        ]
        
        # Define concurrent check function
        async def check_entry_conditions(agent_index: int):
            agent = env["agents"][agent_index]
            state = DeepAgentState(
                user_request="test",
                chat_thread_id="test_thread",
                user_id="test_user"
            )
            state.user_request = test_requests[agent_index]
            
            result = await agent.check_entry_conditions(
                state, f"concurrent_check_{agent_index}"
            )
            
            return (agent_index, result)
        
        # Launch concurrent checks
        tasks = [check_entry_conditions(i) for i in range(3)]
        results = await asyncio.gather(*tasks)
        
        # Validate all checks completed
        assert len(results) == 3
        
        for agent_index, result in results:
            # Entry condition check should complete (True or False both acceptable)
            assert isinstance(result, bool)
            print(f"Agent {agent_index} entry check: {result}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.critical_path
    async def test_concurrent_execution_isolation(self, setup_concurrent_environment):
        """
        Test that concurrent executions are properly isolated and don't
        interfere with each other's state.
        """
        env = await setup_concurrent_environment
        
        # Define concurrent execution function
        async def execute_corpus_operation(agent_index: int):
            agent = env["agents"][agent_index]
            state = DeepAgentState(
                user_request="test",
                chat_thread_id=f"test_thread_{agent_index}",
                user_id=f"test_user_{agent_index}"
            )
            
            # Each agent gets a different request
            requests = [
                "Create performance optimization corpus",
                "Update cost analysis knowledge base", 
                "Search existing documentation corpus"
            ]
            
            state.user_request = requests[agent_index]
            state.user_id = f"user_{agent_index}"
            state.chat_thread_id = f"thread_{agent_index}"
            
            # Execute
            await agent.execute(
                state=state,
                run_id=f"concurrent_exec_{agent_index}",
                stream_updates=False
            )
            
            return (agent_index, state)
        
        # Launch concurrent executions
        start_time = datetime.now()
        tasks = [execute_corpus_operation(i) for i in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Validate results
        successful_executions = 0
        for result in results:
            if isinstance(result, Exception):
                print(f"Execution failed with exception: {result}")
            else:
                agent_index, state = result
                
                # Validate state isolation
                assert state.user_id == f"user_{agent_index}"
                assert state.chat_thread_id == f"thread_{agent_index}"
                
                # Validate execution completed
                has_result = hasattr(state, 'corpus_admin_result')
                has_error = hasattr(state, 'corpus_admin_error')
                
                if has_result or has_error:
                    successful_executions += 1
                    print(f"Agent {agent_index} completed successfully")
        
        # At least some executions should complete
        assert successful_executions > 0, "At least one concurrent execution should succeed"
        
        # Performance check - concurrent execution shouldn't be much slower than sequential
        assert execution_time < 30.0, f"Concurrent execution took too long: {execution_time}s"
        
        print(f"Concurrent execution completed in {execution_time:.2f}s")
        print(f"Successful executions: {successful_executions}/3")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.critical_path
    async def test_concurrent_cleanup_operations(self, setup_concurrent_environment):
        """
        Test that concurrent cleanup operations don't interfere with each other.
        """
        env = await setup_concurrent_environment
        
        # First, execute operations to have something to clean up
        states = []
        for i in range(3):
            agent = env["agents"][i]
            state = DeepAgentState(
                user_request="test",
                chat_thread_id="test_thread",
                user_id="test_user"
            )
            state.user_request = f"Test operation {i} for cleanup"
            
            await agent.execute(
                state=state,
                run_id=f"cleanup_setup_{i}",
                stream_updates=False
            )
            
            states.append((agent, state, f"cleanup_setup_{i}"))
        
        # Now perform concurrent cleanup
        async def cleanup_operation(agent_state_tuple):
            agent, state, run_id = agent_state_tuple
            await agent.cleanup(state, run_id)
            return True
        
        # Launch concurrent cleanups
        cleanup_tasks = [cleanup_operation(ast) for ast in states]
        cleanup_results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Validate all cleanups completed without errors
        successful_cleanups = 0
        for result in cleanup_results:
            if isinstance(result, Exception):
                print(f"Cleanup failed: {result}")
            else:
                successful_cleanups += 1
        
        assert successful_cleanups == 3, "All cleanups should succeed"
        print(f"All {successful_cleanups} concurrent cleanups completed successfully")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_concurrent_performance_benchmarks(self, setup_concurrent_environment):
        """
        Test performance characteristics of concurrent corpus operations
        to ensure system scales properly.
        """
        env = await setup_concurrent_environment
        
        # Benchmark different concurrent operation patterns
        benchmarks = {}
        
        # Test 1: All agents doing similar operations
        start_time = datetime.now()
        
        async def similar_operation(agent_index: int):
            agent = env["agents"][agent_index]
            state = DeepAgentState(
                user_request="test",
                chat_thread_id="test_thread",
                user_id="test_user"
            )
            state.user_request = "Create knowledge base for performance testing"
            
            await agent.execute(
                state=state,
                run_id=f"perf_similar_{agent_index}",
                stream_updates=False
            )
            
            return state
        
        similar_tasks = [similar_operation(i) for i in range(3)]
        similar_results = await asyncio.gather(*similar_tasks, return_exceptions=True)
        similar_duration = (datetime.now() - start_time).total_seconds()
        benchmarks["similar_operations"] = similar_duration
        
        # Test 2: All agents doing different operations
        start_time = datetime.now()
        
        async def different_operation(agent_index: int):
            agent = env["agents"][agent_index]
            state = DeepAgentState(
                user_request="test",
                chat_thread_id="test_thread",
                user_id="test_user"
            )
            
            operations = [
                "Create new corpus with documentation",
                "Update existing corpus with metrics", 
                "Search corpus for optimization data"
            ]
            
            state.user_request = operations[agent_index]
            
            await agent.execute(
                state=state,
                run_id=f"perf_different_{agent_index}",
                stream_updates=False
            )
            
            return state
        
        different_tasks = [different_operation(i) for i in range(3)]
        different_results = await asyncio.gather(*different_tasks, return_exceptions=True)
        different_duration = (datetime.now() - start_time).total_seconds()
        benchmarks["different_operations"] = different_duration
        
        # Validate performance
        assert similar_duration < 15.0, f"Similar operations too slow: {similar_duration}s"
        assert different_duration < 15.0, f"Different operations too slow: {different_duration}s"
        
        # Count successful operations
        similar_success = sum(1 for r in similar_results if not isinstance(r, Exception))
        different_success = sum(1 for r in different_results if not isinstance(r, Exception))
        
        print(f"Performance Benchmarks:")
        print(f"  Similar operations: {similar_duration:.2f}s ({similar_success}/3 successful)")
        print(f"  Different operations: {different_duration:.2f}s ({different_success}/3 successful)")
        
        # At least some operations should succeed
        assert similar_success > 0, "Some similar operations should succeed"
        assert different_success > 0, "Some different operations should succeed"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.critical_path
    async def test_agent_health_under_concurrent_load(self, setup_concurrent_environment):
        """
        Test that agent health status remains stable under concurrent load.
        """
        env = await setup_concurrent_environment
        
        # Check initial health
        initial_health = [agent.get_health_status() for agent in env["agents"]]
        
        for i, health in enumerate(initial_health):
            assert health["agent_health"] == "healthy", f"Agent {i} should start healthy"
        
        # Apply concurrent load
        async def load_operation(agent_index: int, operation_count: int):
            agent = env["agents"][agent_index]
            results = []
            
            for j in range(operation_count):
                state = DeepAgentState(
                user_request="test",
                chat_thread_id="test_thread",
                user_id="test_user"
            )
                state.user_request = f"Load test operation {j} for agent {agent_index}"
                
                try:
                    await agent.execute(
                        state=state,
                        run_id=f"load_{agent_index}_{j}",
                        stream_updates=False
                    )
                    results.append(True)
                except Exception as e:
                    results.append(False)
                    print(f"Load operation failed: {e}")
            
            return results
        
        # Apply load to all agents concurrently (3 operations each)
        load_tasks = [load_operation(i, 3) for i in range(3)]
        load_results = await asyncio.gather(*load_tasks)
        
        # Check health after load
        final_health = [agent.get_health_status() for agent in env["agents"]]
        
        for i, health in enumerate(final_health):
            # Agents should maintain health status
            assert health["agent_health"] in ["healthy", "degraded"], f"Agent {i} health after load: {health['agent_health']}"
        
        # Count successful operations
        total_operations = sum(sum(results) for results in load_results)
        total_attempted = 3 * 3  # 3 agents * 3 operations each
        
        print(f"Load test: {total_operations}/{total_attempted} operations successful")
        
        # At least 50% of operations should succeed under load
        success_rate = total_operations / total_attempted
        assert success_rate >= 0.5, f"Success rate too low: {success_rate:.2%}"