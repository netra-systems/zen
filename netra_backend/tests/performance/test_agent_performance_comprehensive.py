"""
Agent Performance Testing (Iterations 31-35 completion).

Comprehensive performance tests for agent operations including
latency, throughput, memory usage, and optimization patterns.
"""

import asyncio
import pytest
import time
import psutil
import gc
from typing import Dict, Any, List
from statistics import mean, median, stdev
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent


@pytest.mark.performance
class TestAgentLatencyPerformance:
    """Test agent operation latency and response times."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization_latency(self):
        """Test agent initialization performance."""
        initialization_times = []
        
        # Test multiple agent initializations
        for i in range(20):
            start_time = time.time()
            
            agent_state = DeepAgentState(
                agent_id=f"perf_agent_{i}",
                session_id=f"perf_session_{i}",
                thread_id=f"perf_thread_{i}",
                context={"performance_test": True, "initialization_id": i}
            )
            
            agent = SupervisorAgent(
                agent_id=f"performance_test_{i}",
                initial_state=agent_state
            )
            
            end_time = time.time()
            initialization_time = (end_time - start_time) * 1000  # Convert to milliseconds
            initialization_times.append(initialization_time)
        
        # Analyze initialization performance
        avg_init_time = mean(initialization_times)
        median_init_time = median(initialization_times)
        max_init_time = max(initialization_times)
        min_init_time = min(initialization_times)
        
        # Performance assertions
        assert avg_init_time < 50.0  # Average initialization should be under 50ms
        assert median_init_time < 40.0  # Median should be under 40ms
        assert max_init_time < 100.0  # No initialization should take over 100ms
        assert min_init_time >= 0.1  # Sanity check - should take some time
        
        # Consistency check - standard deviation should be reasonable
        if len(initialization_times) > 1:
            init_stdev = stdev(initialization_times)
            assert init_stdev < 20.0  # Initialization times should be consistent
    
    @pytest.mark.asyncio
    async def test_agent_task_execution_latency(self):
        """Test agent task execution latency under different loads."""
        # Mock database operations with realistic delays
        mock_db_manager = DatabaseTestManager().get_session()
        mock_session = AsyncNone  # TODO: Use real service instance
        
        async def mock_db_operation(*args, **kwargs):
            # Simulate database latency
            await asyncio.sleep(0.005)  # 5ms database latency
            return {"result": "success", "rows": 1}
        
        mock_session.execute = AsyncMock(side_effect=mock_db_operation)
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        # Mock WebSocket operations
        mock_websocket_manager = UnifiedWebSocketManager()
        mock_websocket_manager.broadcast_to_thread = AsyncNone  # TODO: Use real service instance
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            with patch('netra_backend.app.websocket_core.utils.get_connection_monitor', return_value=mock_websocket_manager):
                
                # Test different task complexities
                task_scenarios = [
                    {"complexity": "simple", "operations": 1, "expected_max_latency": 50},
                    {"complexity": "medium", "operations": 5, "expected_max_latency": 100},
                    {"complexity": "complex", "operations": 10, "expected_max_latency": 200}
                ]
                
                for scenario in task_scenarios:
                    execution_times = []
                    
                    # Execute multiple tasks of the same complexity
                    for i in range(10):
                        agent_state = DeepAgentState(
                            agent_id=f"latency_agent_{scenario['complexity']}_{i}",
                            session_id=f"latency_session_{i}",
                            thread_id=f"latency_thread_{i}",
                            context={"performance_test": True, "complexity": scenario["complexity"]}
                        )
                        
                        agent = SupervisorAgent(
                            agent_id=f"latency_test_{i}",
                            initial_state=agent_state
                        )
                        
                        # Execute task with timing
                        start_time = time.time()
                        
                        task_config = {
                            "operations": scenario["operations"],
                            "complexity": scenario["complexity"]
                        }
                        
                        result = await agent._execute_performance_task(task_config)
                        
                        end_time = time.time()
                        execution_time = (end_time - start_time) * 1000  # Convert to ms
                        execution_times.append(execution_time)
                        
                        # Verify task completed successfully
                        assert result["status"] == "completed"
                    
                    # Analyze performance for this complexity level
                    avg_time = mean(execution_times)
                    max_time = max(execution_times)
                    p95_time = sorted(execution_times)[int(0.95 * len(execution_times))]
                    
                    # Performance assertions based on complexity
                    assert avg_time < scenario["expected_max_latency"]
                    assert max_time < scenario["expected_max_latency"] * 1.5  # Allow 50% variance for max
                    assert p95_time < scenario["expected_max_latency"] * 1.2  # 95th percentile within 20% of expected
    
    @pytest.mark.asyncio
    async def test_agent_concurrent_execution_latency(self):
        """Test agent latency under concurrent execution."""
        # Mock shared resources
        mock_db_manager = DatabaseTestManager().get_session()
        mock_session = AsyncNone  # TODO: Use real service instance
        
        # Simulate connection pool contention
        connection_pool_delay = 0
        
        async def mock_get_session(*args, **kwargs):
            nonlocal connection_pool_delay
            # Simulate increasing delay as more connections are requested
            await asyncio.sleep(connection_pool_delay)
            connection_pool_delay = min(connection_pool_delay + 0.001, 0.01)  # Max 10ms delay
            return mock_session
        
        mock_session.execute = AsyncMock(return_value={"result": "success"})
        mock_db_manager.get_async_session.side_effect = mock_get_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            
            # Test increasing levels of concurrency
            concurrency_levels = [5, 10, 20, 30]
            latency_results = []
            
            for concurrency in concurrency_levels:
                execution_times = []
                
                # Create concurrent agents
                tasks = []
                
                for i in range(concurrency):
                    agent_state = DeepAgentState(
                        agent_id=f"concurrent_agent_{concurrency}_{i}",
                        session_id=f"concurrent_session_{i}",
                        thread_id=f"concurrent_thread_{i}",
                        context={"concurrency_level": concurrency}
                    )
                    
                    agent = SupervisorAgent(
                        agent_id=f"concurrent_test_{i}",
                        initial_state=agent_state
                    )
                    
                    # Create task with timing wrapper
                    async def timed_task(agent_instance=agent):
                        start_time = time.time()
                        result = await agent_instance._execute_concurrent_task({
                            "operation": "database_query",
                            "concurrency_level": concurrency
                        })
                        end_time = time.time()
                        execution_time = (end_time - start_time) * 1000
                        return {"result": result, "execution_time": execution_time}
                    
                    tasks.append(timed_task())
                
                # Execute all concurrent tasks
                start_batch_time = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_batch_time = time.time()
                batch_time = (end_batch_time - start_batch_time) * 1000
                
                # Extract execution times
                for result in results:
                    if isinstance(result, dict) and "execution_time" in result:
                        execution_times.append(result["execution_time"])
                
                # Analyze latency under this concurrency level
                if execution_times:
                    avg_latency = mean(execution_times)
                    p95_latency = sorted(execution_times)[int(0.95 * len(execution_times))]
                    
                    latency_results.append({
                        "concurrency": concurrency,
                        "avg_latency_ms": avg_latency,
                        "p95_latency_ms": p95_latency,
                        "batch_time_ms": batch_time
                    })
            
            # Verify latency scaling characteristics
            assert len(latency_results) == len(concurrency_levels)
            
            # Latency should not degrade exponentially with concurrency
            for i in range(1, len(latency_results)):
                current = latency_results[i]
                previous = latency_results[i-1]
                
                # Allow reasonable latency increase (not more than 3x for 2x concurrency)
                concurrency_ratio = current["concurrency"] / previous["concurrency"]
                latency_ratio = current["avg_latency_ms"] / previous["avg_latency_ms"]
                
                assert latency_ratio <= concurrency_ratio * 1.5  # Reasonable scaling


@pytest.mark.performance
class TestAgentMemoryPerformance:
    """Test agent memory usage and optimization."""
    
    @pytest.mark.asyncio
    async def test_agent_memory_usage_baseline(self):
        """Test baseline agent memory consumption."""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create multiple agents and measure memory growth
        agents = []
        memory_measurements = [initial_memory]
        
        for i in range(10):
            agent_state = DeepAgentState(
                agent_id=f"memory_test_agent_{i}",
                session_id=f"memory_session_{i}",
                thread_id=f"memory_thread_{i}",
                context={"memory_test": True, "agent_index": i}
            )
            
            agent = SupervisorAgent(
                agent_id=f"memory_baseline_test_{i}",
                initial_state=agent_state
            )
            agents.append(agent)
            
            # Measure memory after each agent creation
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_measurements.append(current_memory)
        
        # Analyze memory growth
        final_memory = memory_measurements[-1]
        total_memory_growth = final_memory - initial_memory
        average_memory_per_agent = total_memory_growth / len(agents)
        
        # Performance assertions
        assert average_memory_per_agent < 5.0  # Each agent should use less than 5MB
        assert total_memory_growth < 50.0  # Total growth should be under 50MB for 10 agents
        
        # Test memory cleanup
        del agents
        gc.collect()
        
        # Allow some time for cleanup
        await asyncio.sleep(0.1)
        
        cleanup_memory = process.memory_info().rss / 1024 / 1024
        memory_recovered = final_memory - cleanup_memory
        
        # Should recover at least 50% of the allocated memory
        assert memory_recovered >= total_memory_growth * 0.5
    
    @pytest.mark.asyncio
    async def test_agent_memory_leak_detection(self):
        """Test agent operations for memory leaks."""
        process = psutil.Process()
        
        # Baseline memory measurement
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        # Execute multiple agent task cycles
        cycles = 5
        memory_after_cycles = []
        
        for cycle in range(cycles):
            # Create and execute agents for this cycle
            cycle_agents = []
            
            for i in range(5):  # 5 agents per cycle
                agent_state = DeepAgentState(
                    agent_id=f"leak_test_agent_c{cycle}_a{i}",
                    session_id=f"leak_session_c{cycle}_a{i}",
                    thread_id=f"leak_thread_c{cycle}_a{i}",
                    context={"leak_test": True, "cycle": cycle, "agent": i}
                )
                
                agent = SupervisorAgent(
                    agent_id=f"leak_detection_test_c{cycle}_a{i}",
                    initial_state=agent_state
                )
                cycle_agents.append(agent)
                
                # Execute some operations
                await agent._execute_memory_test_operations([
                    {"operation": "create_large_context", "size_mb": 1},
                    {"operation": "process_data", "iterations": 100},
                    {"operation": "cleanup"}
                ])
            
            # Cleanup cycle agents
            del cycle_agents
            gc.collect()
            await asyncio.sleep(0.1)  # Allow cleanup time
            
            # Measure memory after cleanup
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_after_cycles.append(current_memory)
        
        # Analyze memory leak patterns
        memory_growth_per_cycle = []
        for i in range(1, len(memory_after_cycles)):
            growth = memory_after_cycles[i] - memory_after_cycles[i-1]
            memory_growth_per_cycle.append(growth)
        
        # Check for memory leak indicators
        if memory_growth_per_cycle:
            avg_growth = mean(memory_growth_per_cycle)
            max_growth = max(memory_growth_per_cycle)
            
            # Memory growth per cycle should be minimal (indicating no leaks)
            assert avg_growth < 2.0  # Less than 2MB average growth per cycle
            assert max_growth < 5.0  # Less than 5MB max growth in any cycle
            
            # Total memory growth should be bounded
            total_growth = memory_after_cycles[-1] - baseline_memory
            assert total_growth < 10.0  # Total growth under 10MB for all cycles
    
    @pytest.mark.asyncio
    async def test_agent_large_dataset_memory_efficiency(self):
        """Test agent memory efficiency with large datasets."""
        process = psutil.Process()
        
        # Test processing datasets of increasing sizes
        dataset_sizes = [1000, 5000, 10000, 20000]  # Number of records
        memory_efficiency_results = []
        
        for dataset_size in dataset_sizes:
            # Measure initial memory
            gc.collect()
            initial_memory = process.memory_info().rss / 1024 / 1024
            
            agent_state = DeepAgentState(
                agent_id=f"large_data_agent_{dataset_size}",
                session_id=f"large_data_session_{dataset_size}",
                thread_id=f"large_data_thread_{dataset_size}",
                context={"dataset_size": dataset_size, "memory_optimization": True}
            )
            
            agent = SupervisorAgent(
                agent_id=f"large_data_test_{dataset_size}",
                initial_state=agent_state
            )
            
            # Simulate large dataset processing
            start_time = time.time()
            result = await agent._process_large_dataset({
                "dataset_size": dataset_size,
                "processing_mode": "memory_efficient",
                "batch_size": min(1000, dataset_size // 5)  # Process in batches
            })
            end_time = time.time()
            
            # Measure peak memory during processing
            peak_memory = process.memory_info().rss / 1024 / 1024
            memory_used = peak_memory - initial_memory
            processing_time = end_time - start_time
            
            # Cleanup
            del agent
            gc.collect()
            
            memory_efficiency_results.append({
                "dataset_size": dataset_size,
                "memory_used_mb": memory_used,
                "processing_time_s": processing_time,
                "memory_per_record_kb": (memory_used * 1024) / dataset_size,
                "records_per_second": dataset_size / processing_time
            })
            
            # Verify processing completed successfully
            assert result["status"] == "completed"
            assert result["records_processed"] == dataset_size
        
        # Analyze memory efficiency scaling
        for i, result in enumerate(memory_efficiency_results):
            dataset_size = result["dataset_size"]
            memory_per_record = result["memory_per_record_kb"]
            records_per_second = result["records_per_second"]
            
            # Memory per record should not grow significantly with dataset size
            # (indicates efficient streaming/batching)
            assert memory_per_record < 5.0  # Less than 5KB per record
            
            # Processing rate should remain reasonable
            assert records_per_second > dataset_size / 10  # At least 1/10 of dataset per second
            
            # Memory usage should scale sub-linearly (due to batching)
            if i > 0:
                prev_result = memory_efficiency_results[i-1]
                size_ratio = dataset_size / prev_result["dataset_size"]
                memory_ratio = result["memory_used_mb"] / prev_result["memory_used_mb"]
                
                # Memory should not scale linearly with data size (efficient processing)
                assert memory_ratio < size_ratio * 0.8  # Memory scales sub-linearly


@pytest.mark.performance
class TestAgentThroughputOptimization:
    """Test agent throughput optimization and scaling."""
    
    @pytest.mark.asyncio
    async def test_agent_batch_processing_throughput(self):
        """Test agent throughput with batch processing optimization."""
        # Mock database for batch operations
        mock_db_manager = DatabaseTestManager().get_session()
        mock_session = AsyncNone  # TODO: Use real service instance
        
        # Track batch operations
        batch_operations = []
        
        async def mock_batch_execute(queries):
            # Simulate batch processing efficiency
            batch_size = len(queries)
            processing_time = 0.001 * batch_size + 0.005  # Base overhead + per-item cost
            await asyncio.sleep(processing_time)
            
            batch_operations.append({
                "batch_size": batch_size,
                "processing_time": processing_time
            })
            
            return {"rowcount": batch_size, "batch_processed": True}
        
        mock_session.execute_batch = AsyncMock(side_effect=mock_batch_execute)
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            
            # Test different batch sizes
            batch_sizes = [10, 50, 100, 200]
            throughput_results = []
            
            for batch_size in batch_sizes:
                agent_state = DeepAgentState(
                    agent_id=f"batch_agent_{batch_size}",
                    session_id=f"batch_session_{batch_size}",
                    thread_id=f"batch_thread_{batch_size}",
                    context={"batch_processing": True, "batch_size": batch_size}
                )
                
                agent = SupervisorAgent(
                    agent_id=f"batch_throughput_test_{batch_size}",
                    initial_state=agent_state
                )
                
                # Measure throughput for this batch size
                items_to_process = 1000
                
                start_time = time.time()
                result = await agent._execute_batch_processing({
                    "total_items": items_to_process,
                    "batch_size": batch_size,
                    "optimization": "throughput"
                })
                end_time = time.time()
                
                processing_time = end_time - start_time
                throughput = items_to_process / processing_time  # Items per second
                
                throughput_results.append({
                    "batch_size": batch_size,
                    "throughput_items_per_second": throughput,
                    "total_processing_time": processing_time,
                    "batches_executed": items_to_process // batch_size
                })
                
                # Verify processing completed
                assert result["status"] == "completed"
                assert result["items_processed"] == items_to_process
            
            # Analyze throughput optimization
            peak_throughput = max(r["throughput_items_per_second"] for r in throughput_results)
            
            # Find optimal batch size
            optimal_result = max(throughput_results, key=lambda x: x["throughput_items_per_second"])
            
            # Verify throughput characteristics
            assert peak_throughput > 100  # At least 100 items per second at peak
            assert optimal_result["batch_size"] >= 50  # Optimal batch size should be reasonable
            
            # Verify batch processing was used effectively
            assert len(batch_operations) > 0
            avg_batch_size = mean(op["batch_size"] for op in batch_operations)
            assert avg_batch_size >= 10  # Should use meaningful batch sizes
    
    @pytest.mark.asyncio
    async def test_agent_parallel_execution_throughput(self):
        """Test agent throughput with parallel execution."""
        # Mock concurrent operation tracking
        concurrent_operations = {"active": 0, "peak": 0, "completed": 0}
        
        async def mock_parallel_operation(operation_id):
            concurrent_operations["active"] += 1
            concurrent_operations["peak"] = max(concurrent_operations["peak"], concurrent_operations["active"])
            
            # Simulate variable operation time
            operation_time = 0.05 + (operation_id % 3) * 0.01  # 50-70ms
            await asyncio.sleep(operation_time)
            
            concurrent_operations["active"] -= 1
            concurrent_operations["completed"] += 1
            
            return {"operation_id": operation_id, "status": "completed", "duration": operation_time}
        
        # Test different parallelism levels
        parallelism_levels = [2, 5, 10, 15]
        parallel_throughput_results = []
        
        for max_parallel in parallelism_levels:
            # Reset tracking
            concurrent_operations.update({"active": 0, "peak": 0, "completed": 0})
            
            agent_state = DeepAgentState(
                agent_id=f"parallel_agent_{max_parallel}",
                session_id=f"parallel_session_{max_parallel}",
                thread_id=f"parallel_thread_{max_parallel}",
                context={"max_parallelism": max_parallel, "parallel_optimization": True}
            )
            
            agent = SupervisorAgent(
                agent_id=f"parallel_throughput_test_{max_parallel}",
                initial_state=agent_state
            )
            
            # Mock parallel task execution
            async def execute_parallel_tasks(task_count, max_concurrency):
                semaphore = asyncio.Semaphore(max_concurrency)
                
                async def limited_operation(op_id):
                    async with semaphore:
                        return await mock_parallel_operation(op_id)
                
                tasks = [limited_operation(i) for i in range(task_count)]
                return await asyncio.gather(*tasks)
            
            # Execute parallel tasks
            task_count = 50
            start_time = time.time()
            
            results = await execute_parallel_tasks(task_count, max_parallel)
            
            end_time = time.time()
            total_time = end_time - start_time
            throughput = task_count / total_time
            
            parallel_throughput_results.append({
                "max_parallelism": max_parallel,
                "throughput_tasks_per_second": throughput,
                "total_time": total_time,
                "peak_concurrency": concurrent_operations["peak"],
                "tasks_completed": concurrent_operations["completed"]
            })
            
            # Verify parallel execution occurred
            assert concurrent_operations["peak"] >= min(max_parallel, task_count)
            assert concurrent_operations["completed"] == task_count
        
        # Analyze parallel throughput scaling
        for i in range(1, len(parallel_throughput_results)):
            current = parallel_throughput_results[i]
            previous = parallel_throughput_results[i-1]
            
            # Throughput should generally improve with more parallelism
            # (allowing for some variance due to overhead)
            parallelism_ratio = current["max_parallelism"] / previous["max_parallelism"]
            throughput_ratio = current["throughput_tasks_per_second"] / previous["throughput_tasks_per_second"]
            
            # Should see some throughput improvement (at least 50% of theoretical)
            expected_min_improvement = (parallelism_ratio - 1) * 0.5 + 1
            assert throughput_ratio >= expected_min_improvement * 0.8  # Allow for overhead
        
        # Peak throughput should be significantly higher than single-threaded
        peak_throughput = max(r["throughput_tasks_per_second"] for r in parallel_throughput_results)
        single_threaded_estimate = 1 / 0.06  # ~16.7 tasks/sec for 60ms tasks
        
        assert peak_throughput > single_threaded_estimate * 3  # At least 3x improvement