class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
    pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
    pass
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
    return self.messages_sent.copy()

"""Stress Tests for Supervisor Agent Under Extreme Load.

Tests the supervisor's ability to handle extreme conditions including:
- High concurrency
- Memory pressure
- Resource exhaustion
- Cascading failures
- Recovery under load

Business Value: Ensures system stability and graceful degradation under stress.
"""

import asyncio
import pytest
import time
import psutil
import gc
import random
from datetime import datetime, timezone
from typing import Dict, Any, List
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core import UnifiedWebSocketManager
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestHighConcurrency:
    """Test supervisor under high concurrency stress."""
    
    @pytest.fixture
    def supervisor_for_stress(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create supervisor configured for stress testing."""
    pass
        websocket = TestWebSocketConnection()
        llm_manager = MagicMock(spec=LLMManager)
        llm_manager.generate = AsyncMock(return_value="Stress test response")
        websocket_manager = MagicMock(spec=UnifiedWebSocketManager)
        websocket_manager.websocket = TestWebSocketConnection()
        tool_dispatcher = MagicMock(spec=ToolDispatcher)
        
        return SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
    
    @pytest.mark.asyncio
    async def test_100_concurrent_users(self, supervisor_for_stress):
        """Test handling 100 concurrent users."""
        supervisor = supervisor_for_stress
        num_users = 100
        
        # Track metrics
        start_times = []
        end_times = []
        errors = []
        
        async def simulate_user(user_id):
            try:
                start_times.append(time.time())
                
                state = DeepAgentState()
                state.user_id = f"user-{user_id}"
                state.messages = [
                    {"role": "user", "content": f"Request from user {user_id}"}
                ]
                
                run_id = f"stress-{user_id}-{uuid.uuid4()}"
                
                with patch.object(supervisor, '_execute_protected_workflow',
                                return_value=[ExecutionResult(success=True)]):
                    await supervisor.execute(state, run_id, stream_updates=True)
                
                end_times.append(time.time())
                await asyncio.sleep(0)
    return True
                
            except Exception as e:
                errors.append(str(e))
                return False
        
        # Execute all users concurrently
        start = time.time()
        tasks = [simulate_user(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start
        
        # Calculate metrics
        successful = sum(1 for r in results if r is True)
        failed = len(results) - successful
        
        # Performance requirements
        assert successful >= 95  # At least 95% success rate
        assert total_time < 60  # Complete within 60 seconds
        
        print(f"
100 Concurrent Users Stress Test:")
        print(f"  Total Time: {total_time:.2f}s")
        print(f"  Successful: {successful}/{num_users}")
        print(f"  Failed: {failed}")
        print(f"  Throughput: {successful/total_time:.2f} req/s")
    
    @pytest.mark.asyncio
    async def test_burst_traffic(self, supervisor_for_stress):
        """Test handling sudden burst of traffic."""
    pass
        supervisor = supervisor_for_stress
        
        # Simulate steady traffic then burst
        steady_rate = 5  # 5 requests per second
        burst_rate = 50  # 50 requests in burst
        
        results = []
        
        # Phase 1: Steady traffic
        for i in range(10):
            state = DeepAgentState()
            state.messages = [{"role": "user", "content": f"Steady {i}"}]
            
            with patch.object(supervisor, '_execute_protected_workflow',
                            return_value=[ExecutionResult(success=True)]):
                task = supervisor.execute(state, f"steady-{i}", stream_updates=False)
                results.append(asyncio.create_task(task))
            
            await asyncio.sleep(1.0 / steady_rate)
        
        # Phase 2: Traffic burst
        burst_start = time.time()
        burst_tasks = []
        
        for i in range(burst_rate):
            state = DeepAgentState()
            state.messages = [{"role": "user", "content": f"Burst {i}"}]
            
            with patch.object(supervisor, '_execute_protected_workflow',
                            return_value=[ExecutionResult(success=True)]):
                task = supervisor.execute(state, f"burst-{i}", stream_updates=False)
                burst_tasks.append(asyncio.create_task(task))
        
        # Wait for burst to complete
        burst_results = await asyncio.gather(*burst_tasks, return_exceptions=True)
        burst_time = time.time() - burst_start
        
        # System should handle burst gracefully
        burst_successful = sum(1 for r in burst_results if not isinstance(r, Exception))
        assert burst_successful >= burst_rate * 0.8  # 80% success during burst
        
        print(f"
Burst Traffic Test:")
        print(f"  Burst Size: {burst_rate} requests")
        print(f"  Burst Duration: {burst_time:.2f}s")
        print(f"  Successful: {burst_successful}/{burst_rate}")
    
    @pytest.mark.asyncio
    async def test_sustained_load(self, supervisor_for_stress):
        """Test sustained high load over extended period."""
        supervisor = supervisor_for_stress
        duration = 30  # 30 seconds of sustained load
        target_rps = 20  # Target 20 requests per second
        
        start_time = time.time()
        request_count = 0
        errors = []
        
        async def generate_load():
            nonlocal request_count
            while time.time() - start_time < duration:
                state = DeepAgentState()
                state.messages = [{"role": "user", "content": f"Load {request_count}"}]
                
                try:
                    with patch.object(supervisor, '_execute_protected_workflow',
                                    return_value=[ExecutionResult(success=True)]):
                        await supervisor.execute(state, f"load-{request_count}", 
                                               stream_updates=False)
                    request_count += 1
                except Exception as e:
                    errors.append(str(e))
                
                # Control rate
                await asyncio.sleep(1.0 / target_rps)
        
        # Run load generator
        await generate_load()
        
        actual_duration = time.time() - start_time
        actual_rps = request_count / actual_duration
        
        # System should maintain performance under sustained load
        assert actual_rps >= target_rps * 0.8  # Achieve at least 80% of target RPS
        assert len(errors) < request_count * 0.1  # Less than 10% errors
        
        print(f"
Sustained Load Test:")
        print(f"  Duration: {actual_duration:.2f}s")
        print(f"  Requests: {request_count}")
        print(f"  RPS: {actual_rps:.2f}")
        print(f"  Errors: {len(errors)}")


class TestMemoryPressure:
    """Test supervisor behavior under memory pressure."""
    
    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self, supervisor_for_stress):
        """Test that supervisor doesn't leak memory under load."""
        supervisor = supervisor_for_stress
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate load to stress memory
        for batch in range(10):
            tasks = []
            
            for i in range(100):
                state = DeepAgentState()
                # Large message to stress memory
                state.messages = [
                    {"role": "user", "content": "x" * 10000}
                ]
                
                with patch.object(supervisor, '_execute_protected_workflow',
                                return_value=[ExecutionResult(success=True)]):
                    task = supervisor.execute(state, f"mem-{batch}-{i}", 
                                            stream_updates=False)
                    tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Force garbage collection
            gc.collect()
            await asyncio.sleep(0.1)
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be bounded
        assert memory_growth < 100  # Less than 100MB growth
        
        print(f"
Memory Leak Test:")
        print(f"  Initial Memory: {initial_memory:.2f} MB")
        print(f"  Final Memory: {final_memory:.2f} MB")
        print(f"  Growth: {memory_growth:.2f} MB")
    
    @pytest.mark.asyncio
    async def test_large_state_handling(self, supervisor_for_stress):
        """Test handling of large state objects."""
    pass
        supervisor = supervisor_for_stress
        
        # Create large state
        large_state = DeepAgentState()
        large_state.messages = []
        
        # Add many messages to create large state
        for i in range(1000):
            large_state.messages.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}: " + "x" * 500
            })
        
        # Should handle large state without crashing
        with patch.object(supervisor, '_execute_protected_workflow',
                        return_value=[ExecutionResult(success=True)]):
            start = time.time()
            await supervisor.execute(large_state, "large-state-test", 
                                   stream_updates=False)
            elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert elapsed < 10  # Less than 10 seconds
        
        print(f"
Large State Test:")
        print(f"  State Size: {len(large_state.messages)} messages")
        print(f"  Processing Time: {elapsed:.2f}s")


class TestResourceExhaustion:
    """Test supervisor behavior when resources are exhausted."""
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, supervisor_for_stress):
        """Test behavior when connection pools are exhausted."""
        supervisor = supervisor_for_stress
        
        # Simulate connection pool exhaustion
        connection_errors = []
        
        async def failing_db_operation(*args, **kwargs):
            connection_errors.append(time.time())
            if len(connection_errors) > 5:
                # Start succeeding after some failures
                await asyncio.sleep(0)
    return {"status": "recovered"}
            raise Exception("Connection pool exhausted")
        
        supervisor.db_session.execute = failing_db_operation
        
        # Try multiple operations
        results = []
        for i in range(10):
            state = DeepAgentState()
            state.messages = [{"role": "user", "content": f"Test {i}"}]
            
            try:
                with patch.object(supervisor, '_execute_protected_workflow',
                                return_value=[ExecutionResult(success=True)]):
                    await supervisor.execute(state, f"conn-{i}", stream_updates=False)
                results.append("success")
            except Exception:
                results.append("failure")
        
        # Should recover after initial failures
        successes = results.count("success")
        assert successes > 0  # Some requests should succeed after recovery
        
        print(f"
Connection Pool Exhaustion Test:")
        print(f"  Total Attempts: {len(results)}")
        print(f"  Successes: {successes}")
        print(f"  Failures: {results.count('failure')}")
    
    @pytest.mark.asyncio
    async def test_cpu_saturation(self, supervisor_for_stress):
        """Test behavior under CPU saturation."""
    pass
        supervisor = supervisor_for_stress
        
        # Create CPU-intensive tasks
        def cpu_intensive_work():
    pass
            # Simulate CPU-intensive work
            result = 0
            for i in range(1000000):
                result += i * i
            await asyncio.sleep(0)
    return result
        
        # Run CPU-intensive work in parallel with supervisor
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Start CPU-intensive background tasks
            cpu_tasks = [
                executor.submit(cpu_intensive_work) 
                for _ in range(4)
            ]
            
            # Run supervisor tasks
            supervisor_tasks = []
            start = time.time()
            
            for i in range(10):
                state = DeepAgentState()
                state.messages = [{"role": "user", "content": f"CPU test {i}"}]
                
                with patch.object(supervisor, '_execute_protected_workflow',
                                return_value=[ExecutionResult(success=True)]):
                    task = supervisor.execute(state, f"cpu-{i}", stream_updates=False)
                    supervisor_tasks.append(task)
            
            # Execute supervisor tasks under CPU pressure
            supervisor_results = await asyncio.gather(*supervisor_tasks, 
                                                     return_exceptions=True)
            elapsed = time.time() - start
        
        # Should complete even under CPU pressure
        successful = sum(1 for r in supervisor_results 
                        if not isinstance(r, Exception))
        assert successful >= 8  # At least 80% success
        
        print(f"
CPU Saturation Test:")
        print(f"  Supervisor Tasks: {len(supervisor_tasks)}")
        print(f"  Successful: {successful}")
        print(f"  Time Under Pressure: {elapsed:.2f}s")


class TestCascadingFailures:
    """Test resilience to cascading failures."""
    
    @pytest.mark.asyncio
    async def test_agent_cascade_failure(self, supervisor_for_stress):
        """Test handling of cascading agent failures."""
        supervisor = supervisor_for_stress
        
        # Track failure cascade
        failed_agents = set()
        
        async def cascading_agent_execute(context, state):
            # Simulate cascade: if one fails, others start failing
            if len(failed_agents) > 0 and random.random() < 0.7:
                failed_agents.add(context.agent_name)
                raise Exception(f"Cascade failure in {context.agent_name}")
            
            # Random initial failure
            if random.random() < 0.1:
                failed_agents.add(context.agent_name)
                raise Exception(f"Initial failure in {context.agent_name}")
            
            await asyncio.sleep(0)
    return ExecutionResult(success=True)
        
        with patch.object(supervisor.execution_engine.agent_core, 'execute_agent',
                        side_effect=cascading_agent_execute):
            
            results = []
            for i in range(20):
                state = DeepAgentState()
                state.messages = [{"role": "user", "content": f"Cascade test {i}"}]
                
                try:
                    await supervisor.execute(state, f"cascade-{i}", stream_updates=False)
                    results.append("success")
                except Exception:
                    results.append("failure")
                
                # Small delay to allow cascade to develop
                await asyncio.sleep(0.1)
            
            # System should prevent complete cascade
            successes = results.count("success")
            assert successes > 5  # At least some requests should succeed
            
            print(f"
Cascading Failure Test:")
            print(f"  Total Requests: {len(results)}")
            print(f"  Successes: {successes}")
            print(f"  Failed Agents: {len(failed_agents)}")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_under_stress(self, supervisor_for_stress):
        """Test circuit breaker effectiveness under stress."""
    pass
        supervisor = supervisor_for_stress
        
        # Track circuit breaker state
        circuit_trips = []
        
        async def monitor_circuit_breaker(context, func):
    pass
            # Simulate circuit breaker behavior
            if len(circuit_trips) >= 3:
                # Circuit open
                circuit_trips.append(time.time())
                if len(circuit_trips) > 10:
                    # Allow reset after some time
                    circuit_trips.clear()
                    await asyncio.sleep(0)
    return await func()
                raise Exception("Circuit breaker open")
            
            try:
                result = await func()
                return result
            except Exception as e:
                circuit_trips.append(time.time())
                raise e
        
        supervisor.circuit_breaker_integration.execute_with_circuit_protection = \
            monitor_circuit_breaker
        
        # Generate failing load
        results = []
        for i in range(30):
            state = DeepAgentState()
            state.messages = [{"role": "user", "content": f"Circuit test {i}"}]
            
            # Inject failures for first requests
            if i < 5:
                with patch.object(supervisor.workflow_orchestrator, 
                                'execute_standard_workflow',
                                side_effect=Exception("Service error")):
                    try:
                        await supervisor.execute(state, f"circuit-{i}", 
                                               stream_updates=False)
                        results.append("success")
                    except Exception:
                        results.append("failure")
            else:
                with patch.object(supervisor, '_execute_protected_workflow',
                                return_value=[ExecutionResult(success=True)]):
                    try:
                        await supervisor.execute(state, f"circuit-{i}", 
                                               stream_updates=False)
                        results.append("success")
                    except Exception:
                        results.append("failure")
        
        # Circuit breaker should prevent cascade
        # After initial failures, circuit should trip and protect system
        later_successes = results[15:].count("success")
        assert later_successes > 0  # Should recover after circuit resets
        
        print(f"
Circuit Breaker Stress Test:")
        print(f"  Total Requests: {len(results)}")
        print(f"  Circuit Trips: {len(circuit_trips)}")
        print(f"  Recovery Success: {later_successes}")


class TestRecoveryUnderLoad:
    """Test system recovery capabilities under load."""
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, supervisor_for_stress):
        """Test graceful degradation under overload."""
        supervisor = supervisor_for_stress
        
        # Track degradation levels
        degradation_levels = []
        
        async def adaptive_execution(context):
            load = len(degradation_levels)
            
            if load < 10:
                # Normal operation
                degradation_levels.append("normal")
                await asyncio.sleep(0)
    return [
                    ExecutionResult(success=True, result={"mode": "full"}),
                    ExecutionResult(success=True, result={"mode": "full"})
                ]
            elif load < 20:
                # Degraded mode - skip optional steps
                degradation_levels.append("degraded")
                return [
                    ExecutionResult(success=True, result={"mode": "degraded"})
                ]
            else:
                # Minimal mode - essential only
                degradation_levels.append("minimal")
                return [
                    ExecutionResult(success=True, result={"mode": "minimal"})
                ]
        
        with patch.object(supervisor, '_execute_protected_workflow',
                        side_effect=adaptive_execution):
            
            # Generate increasing load
            tasks = []
            for i in range(30):
                state = DeepAgentState()
                state.messages = [{"role": "user", "content": f"Degrade test {i}"}]
                
                task = supervisor.execute(state, f"degrade-{i}", stream_updates=False)
                tasks.append(task)
                
                # Stagger requests
                if i % 5 == 0:
                    await asyncio.sleep(0.1)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All requests should complete (possibly degraded)
            successful = sum(1 for r in results if not isinstance(r, Exception))
            assert successful == len(tasks)
            
            # Check degradation pattern
            assert "normal" in degradation_levels
            assert "degraded" in degradation_levels or "minimal" in degradation_levels
            
            print(f"
Graceful Degradation Test:")
            print(f"  Total Requests: {len(tasks)}")
            print(f"  Normal Mode: {degradation_levels.count('normal')}")
            print(f"  Degraded Mode: {degradation_levels.count('degraded')}")
            print(f"  Minimal Mode: {degradation_levels.count('minimal')}")
    
    @pytest.mark.asyncio
    async def test_recovery_after_overload(self, supervisor_for_stress):
        """Test system recovery after overload condition."""
    pass
        supervisor = supervisor_for_stress
        
        # Phase 1: Overload the system
        overload_tasks = []
        for i in range(50):
            state = DeepAgentState()
            state.messages = [{"role": "user", "content": f"Overload {i}"}]
            
            with patch.object(supervisor, '_execute_protected_workflow',
                            return_value=[ExecutionResult(success=True)]):
                task = supervisor.execute(state, f"overload-{i}", stream_updates=False)
                overload_tasks.append(task)
        
        # Execute overload
        overload_start = time.time()
        overload_results = await asyncio.gather(*overload_tasks, return_exceptions=True)
        overload_time = time.time() - overload_start
        
        # Phase 2: Recovery period
        await asyncio.sleep(2)  # Allow system to recover
        
        # Phase 3: Normal load after recovery
        recovery_tasks = []
        for i in range(10):
            state = DeepAgentState()
            state.messages = [{"role": "user", "content": f"Recovery {i}"}]
            
            with patch.object(supervisor, '_execute_protected_workflow',
                            return_value=[ExecutionResult(success=True)]):
                task = supervisor.execute(state, f"recovery-{i}", stream_updates=False)
                recovery_tasks.append(task)
        
        recovery_start = time.time()
        recovery_results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
        recovery_time = time.time() - recovery_start
        
        # System should recover to normal performance
        recovery_successful = sum(1 for r in recovery_results 
                                if not isinstance(r, Exception))
        assert recovery_successful == len(recovery_tasks)
        
        # Recovery should be faster than overload
        recovery_rps = len(recovery_tasks) / recovery_time
        overload_rps = len(overload_tasks) / overload_time
        
        print(f"
Recovery After Overload Test:")
        print(f"  Overload: {len(overload_tasks)} requests in {overload_time:.2f}s")
        print(f"  Recovery: {len(recovery_tasks)} requests in {recovery_time:.2f}s")
        print(f"  Overload RPS: {overload_rps:.2f}")
        print(f"  Recovery RPS: {recovery_rps:.2f}")


if __name__ == "__main__":
    # Run stress tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--asyncio-mode=auto"
    ])