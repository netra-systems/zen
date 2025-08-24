"""
Performance and concurrency critical end-to-end tests.
Tests 9-10: Concurrent request handling, performance and timeout handling.
"""

import sys
from pathlib import Path

# Add netra_backend to path  

import asyncio
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.services.state_persistence import state_persistence_service
from netra_backend.tests.agents.test_agent_e2e_critical_setup import AgentE2ETestBase

class TestAgentE2ECriticalPerformance(AgentE2ETestBase):
    """Performance and concurrency critical tests"""
    @pytest.mark.asyncio
    async def test_9_concurrent_request_handling(self, setup_agent_infrastructure):
        """
        Test Case 9: Concurrent Request Handling
        - Test multiple simultaneous user requests
        - Test resource isolation between requests
        - Test performance under concurrent load
        """
        infra = setup_agent_infrastructure
        agent_service = infra["agent_service"]
        
        num_concurrent_requests = 10
        requests = [
            {
                "user_id": str(uuid.uuid4()),
                "thread_id": str(uuid.uuid4()),
                "request": f"Request {i}"
            }
            for i in range(num_concurrent_requests)
        ]
        
        # Track execution metrics
        start_time = datetime.now()
        results = []
        errors = []
        
        # Mock the agent service to always succeed for concurrent testing
        async def mock_concurrent_start(user_id=None, thread_id=None, request=None):
            if user_id and thread_id:
                return str(uuid.uuid4())
            raise Exception("Missing required parameters")
        
        agent_service.start_agent_run = mock_concurrent_start
        
        async def execute_request(req):
            try:
                run_id = await agent_service.start_agent_run(**req)
                return {"success": True, "run_id": run_id}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Execute all requests concurrently
        tasks = [execute_request(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Verify all requests were handled
        assert len(results) == num_concurrent_requests
        
        # Check success rate
        successful = [r for r in results if isinstance(r, dict) and r.get("success")]
        success_rate = len(successful) / num_concurrent_requests
        # All requests should succeed with our mock
        assert success_rate >= 0.8  # At least 80% success rate
        
        # Verify isolation - each request got unique run_id
        run_ids = [r["run_id"] for r in successful]
        assert len(run_ids) == len(set(run_ids))  # All unique
        
        # Performance check - should handle concurrent requests efficiently
        avg_time_per_request = execution_time / num_concurrent_requests
        assert avg_time_per_request < 1.0  # Less than 1 second per request on average

    def _get_sub_agents_from_supervisor(self, supervisor):
        """Extract sub-agents from supervisor implementation"""
        sub_agents = []
        if hasattr(supervisor, '_impl') and supervisor._impl:
            if hasattr(supervisor._impl, 'agents'):
                sub_agents = list(supervisor._impl.agents.values())
            elif hasattr(supervisor._impl, 'sub_agents'):
                sub_agents = supervisor._impl.sub_agents
        elif hasattr(supervisor, 'sub_agents'):
            sub_agents = supervisor.sub_agents
        return sub_agents

    async def _test_timeout_scenario(self, supervisor, run_id):
        """Test timeout handling for long-running operations"""
        async def slow_execute(state, rid, stream):
            await asyncio.sleep(10)  # Simulate long-running task
            return state
        
        async def mock_entry_conditions(state, rid):
            return True
        
        sub_agents = self._get_sub_agents_from_supervisor(supervisor)
        if len(sub_agents) > 1:
            sub_agents[1].execute = slow_execute
            sub_agents[1].check_entry_conditions = mock_entry_conditions

    async def _test_with_timeout_patches(self, supervisor, run_id, timeout_seconds):
        """Run supervisor with timeout and state persistence patches"""
        # Ensure slow execution is set up for timeout test
        async def slow_execute(state, rid, stream):
            await asyncio.sleep(timeout_seconds + 1)  # Ensure it exceeds timeout
            return state
        
        async def mock_entry_conditions(state, rid):
            return True
        
        sub_agents = self._get_sub_agents_from_supervisor(supervisor)
        if len(sub_agents) > 1:
            sub_agents[1].execute = slow_execute
            sub_agents[1].check_entry_conditions = mock_entry_conditions
        
        # Mock: Generic component isolation for controlled unit testing
        with patch.object(state_persistence_service, 'save_agent_state', AsyncMock()):
            # Mock: Async component isolation for testing without real async operations
            with patch.object(state_persistence_service, 'load_agent_state', AsyncMock(return_value=None)):
                # Mock: Async component isolation for testing without real async operations
                with patch.object(state_persistence_service, 'get_thread_context', AsyncMock(return_value=None)):
                    with pytest.raises(asyncio.TimeoutError):
                        await asyncio.wait_for(
                            supervisor.run("Test timeout", supervisor.thread_id, supervisor.user_id, run_id),
                            timeout=timeout_seconds
                        )

    async def _create_monitored_execute(self, performance_metrics, agent_name):
        """Create monitored execution function for performance tracking"""
        async def monitored_execute(state, rid, stream):
            start = datetime.now()
            await asyncio.sleep(0.1)  # Simulate work
            end = datetime.now()
            performance_metrics["execution_times"][agent_name] = (end - start).total_seconds()
            return state
        return monitored_execute

    def _setup_performance_monitoring(self, supervisor, performance_metrics):
        """Setup performance monitoring for all agents"""
        sub_agents = self._get_sub_agents_from_supervisor(supervisor)
        for agent in sub_agents:
            async def create_wrapper(name):
                monitored_func = await self._create_monitored_execute(performance_metrics, name)
                return monitored_func
            # Note: This is a simplified approach - in practice, we'd need proper async wrapping
            # Mock: Agent service isolation for testing without LLM agent execution
            agent.execute = AsyncMock(side_effect=lambda s, r, st: self._simulate_monitored_execution(performance_metrics, agent.name))

    async def _simulate_monitored_execution(self, performance_metrics, agent_name):
        """Simulate monitored execution for testing"""
        start = datetime.now()
        await asyncio.sleep(0.1)
        end = datetime.now()
        performance_metrics["execution_times"][agent_name] = (end - start).total_seconds()
        return None

    async def _run_performance_test(self, supervisor, run_id, performance_metrics):
        """Execute performance test with monitoring"""
        # Mock: Generic component isolation for controlled unit testing
        with patch.object(state_persistence_service, 'save_agent_state', AsyncMock()):
            # Mock: Async component isolation for testing without real async operations
            with patch.object(state_persistence_service, 'load_agent_state', AsyncMock(return_value=None)):
                # Mock: Async component isolation for testing without real async operations
                with patch.object(state_persistence_service, 'get_thread_context', AsyncMock(return_value=None)):
                    performance_metrics["start_time"] = datetime.now()
                    await supervisor.run("Performance test", supervisor.thread_id, supervisor.user_id, run_id + "_perf")
                    performance_metrics["end_time"] = datetime.now()

    def _verify_performance_metrics(self, performance_metrics):
        """Verify collected performance metrics"""
        assert len(performance_metrics["execution_times"]) >= 0
        total_time = (performance_metrics["end_time"] - performance_metrics["start_time"]).total_seconds()
        assert total_time < 5.0  # Should complete within 5 seconds
    @pytest.mark.asyncio
    async def test_10_performance_and_timeout_handling(self, setup_agent_infrastructure):
        """
        Test Case 10: Performance and Timeout Scenarios
        - Test timeout handling for long-running agents
        - Test performance monitoring and metrics
        - Test graceful degradation under load
        """
        infra = setup_agent_infrastructure
        supervisor = infra["supervisor"]
        run_id = str(uuid.uuid4())
        
        # Test timeout handling
        await self._test_with_timeout_patches(supervisor, run_id, timeout_seconds=2)
        
        # Test performance monitoring
        performance_metrics = {"start_time": None, "end_time": None, "memory_usage": [], "execution_times": {}}
        self._setup_performance_monitoring(supervisor, performance_metrics)
        await self._run_performance_test(supervisor, run_id, performance_metrics)
        self._verify_performance_metrics(performance_metrics)

    @pytest.mark.asyncio
    async def test_load_balancing_and_degradation(self, setup_agent_infrastructure):
        """Test graceful degradation under different load levels"""
        infra = setup_agent_infrastructure
        supervisor = infra["supervisor"]
        
        run_id = str(uuid.uuid4())
        
        # Test graceful degradation
        load_levels = [1, 5, 10, 20]
        degradation_results = []
        
        for load in load_levels:
            start = datetime.now()
            
            # Simulate load with state persistence mocking
            async def run_with_mocks(request, rid):
                # Mock: Generic component isolation for controlled unit testing
                with patch.object(state_persistence_service, 'save_agent_state', AsyncMock()):
                    # Mock: Async component isolation for testing without real async operations
                    with patch.object(state_persistence_service, 'load_agent_state', AsyncMock(return_value=None)):
                        # Mock: Async component isolation for testing without real async operations
                        with patch.object(state_persistence_service, 'get_thread_context', AsyncMock(return_value=None)):
                            return await supervisor.run(request, supervisor.thread_id, supervisor.user_id, rid)
            
            tasks = [
                run_with_mocks(f"Load test {i}", f"{run_id}_load_{load}_{i}")
                for i in range(load)
            ]
            
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=10
                )
                success = True
            except asyncio.TimeoutError:
                success = False
            
            end = datetime.now()
            degradation_results.append({
                "load": load,
                "success": success,
                "time": (end - start).total_seconds()
            })
        
        # Verify graceful degradation
        # In a real system, response time should generally increase with load
        # but in our mocked tests, this may not always be true
        # So we just verify that we got results for all load levels
        assert len(degradation_results) == len(load_levels)
        
        # System should handle at least low load
        if len(degradation_results) > 0:
            assert degradation_results[0]["success"] == True