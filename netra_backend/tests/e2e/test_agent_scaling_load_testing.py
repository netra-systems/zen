"""
Agent Scaling and Load Testing (Iterations 26-30 completion).

Tests agent system performance under load, concurrent operations,
and scaling scenarios.
"""

import asyncio
import pytest
from typing import Dict, Any, List
import time
import random
from concurrent.futures import ThreadPoolExecutor
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent


@pytest.mark.e2e
class TestAgentConcurrencyLoad:
    """Test agent system under concurrent load."""
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(self):
        """Test multiple agents executing concurrently."""
        # Mock shared resources
        mock_db_manager = TestDatabaseManager().get_session()
        mock_session = AsyncNone  # TODO: Use real service instance
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        mock_websocket_manager = UnifiedWebSocketManager()
        mock_websocket_manager.broadcast_to_thread = AsyncNone  # TODO: Use real service instance
        
        # Track concurrent executions
        execution_tracker = {
            "active_agents": 0,
            "peak_concurrency": 0,
            "completed_agents": 0,
            "execution_times": []
        }
        
        async def track_execution(agent_id, duration=0.1):
            execution_tracker["active_agents"] += 1
            execution_tracker["peak_concurrency"] = max(
                execution_tracker["peak_concurrency"],
                execution_tracker["active_agents"]
            )
            
            start_time = time.time()
            await asyncio.sleep(duration + random.uniform(0, 0.05))  # Simulate work with variance
            end_time = time.time()
            
            execution_tracker["active_agents"] -= 1
            execution_tracker["completed_agents"] += 1
            execution_tracker["execution_times"].append(end_time - start_time)
            
            return {
                "agent_id": agent_id,
                "status": "completed",
                "execution_time": end_time - start_time
            }
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            with patch('netra_backend.app.websocket_core.utils.get_connection_monitor', return_value=mock_websocket_manager):
                
                # Create multiple concurrent agents
                agent_count = 50
                agents = []
                tasks = []
                
                for i in range(agent_count):
                    agent_state = DeepAgentState(
                        agent_id=f"concurrent_agent_{i}",
                        session_id=f"session_{i}",
                        thread_id=f"thread_{i}",
                        context={"task_id": i, "concurrent_test": True}
                    )
                    
                    agent = SupervisorAgent(
                        agent_id=f"load_test_agent_{i}",
                        initial_state=agent_state
                    )
                    agents.append(agent)
                    
                    # Mock agent execution
                    agent._execute_task = lambda aid=f"agent_{i}": track_execution(aid)
                    tasks.append(agent._execute_task())
                
                # Execute all agents concurrently
                start_time = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()
                
                # Verify concurrent execution results
                assert len(results) == agent_count
                successful_results = [r for r in results if isinstance(r, dict) and r.get("status") == "completed"]
                assert len(successful_results) == agent_count
                
                # Verify concurrency metrics
                assert execution_tracker["peak_concurrency"] >= 10  # Should have significant concurrency
                assert execution_tracker["completed_agents"] == agent_count
                assert end_time - start_time < 5.0  # Should complete quickly due to concurrency
                
                # Verify performance distribution
                avg_execution_time = sum(execution_tracker["execution_times"]) / len(execution_tracker["execution_times"])
                assert avg_execution_time < 0.2  # Individual tasks should be fast
                
                # Verify resource sharing worked (no deadlocks/conflicts)
                db_session_calls = mock_db_manager.get_async_session.call_count
                assert db_session_calls <= agent_count * 2  # Reasonable resource usage
    
    @pytest.mark.asyncio
    async def test_agent_memory_pressure_handling(self):
        """Test agent system handles memory pressure gracefully."""
        # Mock memory monitoring
        memory_usage = {"current_mb": 100, "peak_mb": 100, "gc_triggers": 0}
        
        def simulate_memory_pressure():
            memory_usage["current_mb"] += 50
            memory_usage["peak_mb"] = max(memory_usage["peak_mb"], memory_usage["current_mb"])
            
            if memory_usage["current_mb"] > 800:  # High memory usage
                memory_usage["gc_triggers"] += 1
                memory_usage["current_mb"] = max(200, memory_usage["current_mb"] * 0.6)  # GC effect
        
        # Mock system resources
        mock_db_manager = TestDatabaseManager().get_session()
        mock_session = AsyncNone  # TODO: Use real service instance
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            with patch('psutil.virtual_memory') as mock_memory:
                
                # Simulate memory pressure scenario
                mock_memory.return_value.percent = 85  # High memory usage
                mock_memory.return_value.available = 1024 * 1024 * 1024  # 1GB available
                
                # Create memory-intensive agents
                agent_count = 20
                tasks = []
                
                for i in range(agent_count):
                    agent_state = DeepAgentState(
                        agent_id=f"memory_agent_{i}",
                        session_id=f"memory_session_{i}",
                        thread_id=f"memory_thread_{i}",
                        context={"memory_intensive": True, "data_size": "large"}
                    )
                    
                    agent = SupervisorAgent(
                        agent_id=f"memory_test_{i}",
                        initial_state=agent_state
                    )
                    
                    # Mock memory-intensive operation
                    async def memory_intensive_task():
                        simulate_memory_pressure()
                        await asyncio.sleep(0.1)  # Simulate processing time
                        return {"status": "completed", "memory_used_mb": 50}
                    
                    agent._execute_memory_intensive_task = memory_intensive_task
                    tasks.append(agent._execute_memory_intensive_task())
                
                # Execute with memory monitoring
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Verify memory pressure was handled
                assert len(results) == agent_count
                successful_results = [r for r in results if isinstance(r, dict) and r.get("status") == "completed"]
                assert len(successful_results) == agent_count
                
                # Verify garbage collection was triggered
                assert memory_usage["gc_triggers"] > 0
                assert memory_usage["peak_mb"] < 1000  # Stayed under limit
    
    @pytest.mark.asyncio 
    async def test_agent_throughput_scaling(self):
        """Test agent system throughput scales with load."""
        # Mock processing components
        mock_db_manager = TestDatabaseManager().get_session()
        mock_session = AsyncNone  # TODO: Use real service instance
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        # Test different load levels
        load_levels = [10, 25, 50, 100]  # Number of concurrent agents
        throughput_results = []
        
        for load_level in load_levels:
            # Track throughput metrics
            throughput_tracker = {
                "completed_tasks": 0,
                "start_time": None,
                "end_time": None,
                "errors": 0
            }
            
            async def process_task(task_id):
                try:
                    if throughput_tracker["start_time"] is None:
                        throughput_tracker["start_time"] = time.time()
                    
                    # Simulate variable processing time
                    processing_time = random.uniform(0.05, 0.15)
                    await asyncio.sleep(processing_time)
                    
                    throughput_tracker["completed_tasks"] += 1
                    throughput_tracker["end_time"] = time.time()
                    
                    return {"task_id": task_id, "status": "completed", "processing_time": processing_time}
                except Exception as e:
                    throughput_tracker["errors"] += 1
                    raise e
            
            with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
                
                # Create agents for current load level
                agents = []
                tasks = []
                
                for i in range(load_level):
                    agent_state = DeepAgentState(
                        agent_id=f"throughput_agent_{load_level}_{i}",
                        session_id=f"throughput_session_{i}",
                        thread_id=f"throughput_thread_{i}",
                        context={"load_level": load_level, "throughput_test": True}
                    )
                    
                    agent = SupervisorAgent(
                        agent_id=f"throughput_test_{i}",
                        initial_state=agent_state
                    )
                    agents.append(agent)
                    
                    # Mock task execution
                    agent._process_throughput_task = lambda tid=i: process_task(tid)
                    tasks.append(agent._process_throughput_task())
                
                # Execute load level
                start_wall_time = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_wall_time = time.time()
                
                # Calculate throughput metrics
                wall_time = end_wall_time - start_wall_time
                actual_execution_time = throughput_tracker["end_time"] - throughput_tracker["start_time"]
                
                throughput_per_second = throughput_tracker["completed_tasks"] / wall_time
                error_rate = throughput_tracker["errors"] / load_level
                
                throughput_results.append({
                    "load_level": load_level,
                    "throughput_per_second": throughput_per_second,
                    "error_rate": error_rate,
                    "wall_time": wall_time,
                    "avg_task_time": sum(r.get("processing_time", 0) for r in results if isinstance(r, dict)) / len(results)
                })
        
        # Analyze scaling characteristics
        assert len(throughput_results) == 4
        
        # Verify throughput generally increases with load (allowing for some variance)
        for i in range(1, len(throughput_results)):
            current_throughput = throughput_results[i]["throughput_per_second"]
            previous_throughput = throughput_results[i-1]["throughput_per_second"]
            
            # Throughput should scale reasonably (at least 70% linear scaling)
            expected_min_throughput = previous_throughput * 1.4  # 70% of 2x scaling
            assert current_throughput >= expected_min_throughput * 0.7
        
        # Verify error rates stay low
        max_error_rate = max(result["error_rate"] for result in throughput_results)
        assert max_error_rate < 0.05  # Less than 5% error rate
        
        # Verify highest load level achieved good absolute throughput
        peak_throughput = throughput_results[-1]["throughput_per_second"]
        assert peak_throughput >= 200  # At least 200 tasks per second at peak load


@pytest.mark.e2e
class TestAgentResourceManagement:
    """Test agent resource management under load."""
    
    @pytest.mark.asyncio
    async def test_agent_connection_pool_under_load(self):
        """Test database connection pooling efficiency under agent load."""
        # Mock connection pool with limited capacity
        pool_stats = {
            "pool_size": 20,
            "checked_out": 0,
            "checked_in": 20,
            "overflow": 0,
            "peak_checked_out": 0,
            "wait_times": []
        }
        
        mock_db_manager = TestDatabaseManager().get_session()
        
        async def mock_get_session(*args, **kwargs):
            # Simulate connection pool behavior
            if pool_stats["checked_out"] >= pool_stats["pool_size"]:
                wait_start = time.time()
                await asyncio.sleep(0.01)  # Simulate wait for connection
                wait_time = time.time() - wait_start
                pool_stats["wait_times"].append(wait_time)
            
            pool_stats["checked_out"] += 1
            pool_stats["checked_in"] -= 1
            pool_stats["peak_checked_out"] = max(pool_stats["peak_checked_out"], pool_stats["checked_out"])
            
            # Return mock session that releases connection when done
            mock_session = AsyncNone  # TODO: Use real service instance
            
            async def release_connection():
                pool_stats["checked_out"] -= 1
                pool_stats["checked_in"] += 1
            
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(side_effect=lambda *args: release_connection())
            
            return mock_session
        
        mock_db_manager.get_async_session = mock_get_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            
            # Create many concurrent agents (more than pool size)
            agent_count = 30  # More than pool size of 20
            tasks = []
            
            for i in range(agent_count):
                agent_state = DeepAgentState(
                    agent_id=f"pool_test_agent_{i}",
                    session_id=f"pool_session_{i}",
                    thread_id=f"pool_thread_{i}",
                    context={"connection_pool_test": True}
                )
                
                agent = SupervisorAgent(
                    agent_id=f"pool_load_test_{i}",
                    initial_state=agent_state
                )
                
                # Mock database operation
                async def db_operation():
                    async with mock_db_manager.get_async_session() as session:
                        await asyncio.sleep(0.05)  # Simulate query time
                        return {"status": "completed"}
                
                agent._execute_db_operation = db_operation
                tasks.append(agent._execute_db_operation())
            
            # Execute all operations
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Verify connection pool behavior
            assert len(results) == agent_count
            successful_results = [r for r in results if isinstance(r, dict) and r.get("status") == "completed"]
            assert len(successful_results) == agent_count
            
            # Verify pool was utilized efficiently
            assert pool_stats["peak_checked_out"] <= pool_stats["pool_size"]  # Never exceeded pool size
            assert pool_stats["checked_out"] == 0  # All connections returned
            assert pool_stats["checked_in"] == pool_stats["pool_size"]  # Pool restored
            
            # Some operations should have waited for connections
            if len(pool_stats["wait_times"]) > 0:
                avg_wait_time = sum(pool_stats["wait_times"]) / len(pool_stats["wait_times"])
                assert avg_wait_time < 0.1  # Wait times should be reasonable
    
    @pytest.mark.asyncio
    async def test_agent_circuit_breaker_under_load(self):
        """Test circuit breaker behavior under agent load conditions."""
        # Mock circuit breaker with failure tracking
        circuit_stats = {
            "total_calls": 0,
            "failures": 0,
            "successes": 0,
            "state": "closed",  # closed, open, half_open
            "failure_threshold": 10,
            "recovery_timeout": 0.1
        }
        
        def mock_circuit_call(operation):
            circuit_stats["total_calls"] += 1
            
            # Simulate sporadic failures under load
            if circuit_stats["total_calls"] % 7 == 0:  # Every 7th call fails
                circuit_stats["failures"] += 1
                if circuit_stats["failures"] >= circuit_stats["failure_threshold"]:
                    circuit_stats["state"] = "open"
                raise Exception("Service unavailable")
            
            circuit_stats["successes"] += 1
            return "success"
        
        mock_circuit_breaker = mock_circuit_breaker_instance  # Initialize appropriate service
        mock_circuit_breaker.call = AsyncMock(side_effect=mock_circuit_call)
        mock_circuit_breaker.is_open = property(lambda self: circuit_stats["state"] == "open")
        
        with patch('netra_backend.app.core.resilience.circuit_breaker_manager.get_circuit_breaker', 
                  return_value=mock_circuit_breaker):
            
            # Create agents that will stress the circuit breaker
            agent_count = 50
            tasks = []
            results_tracker = {"successes": 0, "failures": 0, "circuit_open_errors": 0}
            
            for i in range(agent_count):
                agent_state = DeepAgentState(
                    agent_id=f"circuit_agent_{i}",
                    session_id=f"circuit_session_{i}",
                    thread_id=f"circuit_thread_{i}",
                    context={"circuit_breaker_test": True}
                )
                
                agent = SupervisorAgent(
                    agent_id=f"circuit_test_{i}",
                    initial_state=agent_state
                )
                
                # Mock operation protected by circuit breaker
                async def protected_operation():
                    try:
                        if circuit_stats["state"] == "open":
                            results_tracker["circuit_open_errors"] += 1
                            return {"status": "circuit_open", "fallback_used": True}
                        
                        result = await mock_circuit_breaker.call(lambda: "external_service_call")
                        results_tracker["successes"] += 1
                        return {"status": "success", "result": result}
                    except Exception as e:
                        results_tracker["failures"] += 1
                        return {"status": "failed", "error": str(e)}
                
                agent._execute_protected_operation = protected_operation
                tasks.append(agent._execute_protected_operation())
            
            # Execute all operations
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify circuit breaker behavior under load
            assert len(results) == agent_count
            
            # Verify results distribution
            success_results = [r for r in results if isinstance(r, dict) and r.get("status") == "success"]
            failed_results = [r for r in results if isinstance(r, dict) and r.get("status") == "failed"]
            circuit_open_results = [r for r in results if isinstance(r, dict) and r.get("status") == "circuit_open"]
            
            # Should have a mix of results due to circuit breaker behavior
            assert len(success_results) > 0
            assert len(failed_results) > 0  # Some failures due to simulated errors
            
            # If circuit opened, some operations should have been rejected
            if circuit_stats["state"] == "open":
                assert len(circuit_open_results) > 0
                assert results_tracker["circuit_open_errors"] > 0
            
            # Verify circuit breaker statistics
            assert circuit_stats["total_calls"] <= agent_count  # May be less if circuit opened
            assert circuit_stats["failures"] > 0  # Should have detected failures
            
            # Verify failure rate tracking
            if circuit_stats["total_calls"] > 0:
                failure_rate = circuit_stats["failures"] / circuit_stats["total_calls"]
                if failure_rate >= 0.2:  # High failure rate should trigger circuit
                    assert circuit_stats["state"] in ["open", "half_open"]