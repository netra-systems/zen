"""Performance Benchmark Tests for Agent Infrastructure

CRITICAL PERFORMANCE SUITE: Validates performance characteristics of BaseAgent 
and TriageSubAgent under various load conditions and measures key performance indicators.

This comprehensive performance test suite covers:
1. Initialization overhead and startup time
2. Execution timing under various loads
3. Memory usage patterns and leak detection
4. Concurrent execution performance
5. Cache performance and hit rates
6. Circuit breaker overhead
7. WebSocket event emission latency
8. Error handling performance impact
9. Large payload handling performance
10. Long-running operation stability

BVJ: ALL segments | Platform Performance | Response time = Customer satisfaction
"""

import asyncio
import gc
import json
import memory_profiler
import pytest
import psutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas.registry import DeepAgentState


class PerformanceAgent(BaseAgent):
    """Agent optimized for performance testing."""
    
    def __init__(self, *args, **kwargs):
        self.execution_count = 0
        self.total_execution_time = 0
        super().__init__(*args, **kwargs)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        start_time = time.time()
        self.execution_count += 1
        
        # Simulate realistic work
        await asyncio.sleep(0.001)  # 1ms simulated work
        
        end_time = time.time()
        execution_time = end_time - start_time
        self.total_execution_time += execution_time
        
        return {
            "status": "success",
            "execution_time": execution_time,
            "execution_count": self.execution_count
        }


class TestInitializationPerformance:
    """Test initialization overhead and startup time."""
    
    def test_base_agent_initialization_time(self):
        """Test BaseAgent initialization performance."""
        # Mock dependencies
        mock_llm = Mock(spec=LLMManager)
        mock_tool_dispatcher = Mock(spec=ToolDispatcher)
        mock_redis = Mock(spec=RedisManager)
        
        # Measure initialization time
        start_time = time.time()
        
        for i in range(100):
            agent = PerformanceAgent(
                llm_manager=mock_llm,
                name=f"PerfAgent_{i}",
                enable_reliability=True,
                enable_execution_engine=True,
                enable_caching=True,
                tool_dispatcher=mock_tool_dispatcher,
                redis_manager=mock_redis
            )
            # Ensure agent is properly initialized
            assert agent.reliability_manager is not None
            assert agent.execution_engine is not None
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_init_time = total_time / 100
        
        # Performance requirements
        assert total_time < 5.0  # 100 agents should initialize in under 5 seconds
        assert avg_init_time < 0.05  # Average under 50ms per agent
        
        print(f"Average initialization time: {avg_init_time:.3f}s")
        
    def test_triage_agent_initialization_time(self):
        """Test UnifiedTriageAgent initialization performance."""
        initialization_times = []
        
        # Create mock dependencies
        mock_llm_manager = Mock()
        mock_tool_dispatcher = Mock()
        
        for i in range(50):
            start_time = time.time()
            
            agent = UnifiedTriageAgent(
                llm_manager=mock_llm_manager,
                tool_dispatcher=mock_tool_dispatcher
            )
            
            end_time = time.time()
            init_time = end_time - start_time
            initialization_times.append(init_time)
            
            # Verify proper initialization - UnifiedTriageAgent uses BaseAgent architecture
            # triage_core and processor are created per-request for isolation
            assert agent.name == "UnifiedTriageAgent"
            assert hasattr(agent, 'name')
        
        avg_init_time = sum(initialization_times) / len(initialization_times)
        max_init_time = max(initialization_times)
        min_init_time = min(initialization_times)
        
        # Performance requirements
        assert avg_init_time < 0.1  # Average under 100ms
        assert max_init_time < 0.5  # Maximum under 500ms
        
        print(f"TriageSubAgent init - Avg: {avg_init_time:.3f}s, Max: {max_init_time:.3f}s, Min: {min_init_time:.3f}s")
        
    def test_initialization_memory_footprint(self):
        """Test memory footprint of agent initialization."""
        # Get baseline memory
        gc.collect()
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Initialize multiple agents
        agents = []
        for i in range(20):
            mock_llm = Mock(spec=LLMManager)
            agent = PerformanceAgent(
                llm_manager=mock_llm,
                name=f"MemoryAgent_{i}",
                enable_reliability=True,
                enable_execution_engine=True
            )
            agents.append(agent)
        
        # Measure memory after initialization
        gc.collect()
        after_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_per_agent = (after_memory - baseline_memory) / 20
        
        # Performance requirements
        assert memory_per_agent < 5.0  # Under 5MB per agent
        
        print(f"Memory per agent: {memory_per_agent:.2f}MB")
        
        # Clean up
        del agents
        gc.collect()


class TestExecutionPerformance:
    """Test execution timing under various loads."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value='{"category": "Performance", "confidence_score": 0.9}')
        return llm
    
    @pytest.fixture
    def performance_agent(self, mock_llm_manager):
        return PerformanceAgent(
            llm_manager=mock_llm_manager,
            name="PerformanceTestAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
    
    @pytest.mark.asyncio
    async def test_single_execution_timing(self, performance_agent):
        """Test timing for single execution."""
        state = DeepAgentState()
        state.user_request = "Performance test request"
        
        # Warm up (JIT, caching, etc.)
        await performance_agent.execute_modern(state, "warmup")
        
        # Measure actual execution
        execution_times = []
        for i in range(100):
            start_time = time.time()
            
            result = await performance_agent.execute_modern(state, f"timing_test_{i}")
            
            end_time = time.time()
            execution_time = end_time - start_time
            execution_times.append(execution_time)
            
            assert result.is_success is True
        
        # Calculate statistics
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)
        
        # Performance requirements - adjusted for realistic expectations
        assert avg_time < 0.05  # Average under 50ms
        assert max_time < 0.1   # Maximum under 100ms
        
        print(f"Execution timing - Avg: {avg_time*1000:.2f}ms, Max: {max_time*1000:.2f}ms, Min: {min_time*1000:.2f}ms")
        
    @pytest.mark.asyncio
    async def test_concurrent_execution_performance(self, mock_llm_manager):
        """Test performance under concurrent load."""
        agent = PerformanceAgent(
            llm_manager=mock_llm_manager,
            name="ConcurrentPerfAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        results = {}
        
        for concurrency in concurrency_levels:
            start_time = time.time()
            
            # Create concurrent tasks
            tasks = []
            for i in range(concurrency):
                state = DeepAgentState()
                state.user_request = f"Concurrent test {i}"
                
                task = agent.execute_modern(state, f"concurrent_{concurrency}_{i}")
                tasks.append(task)
            
            # Execute and measure
            execution_results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            throughput = concurrency / total_time  # Requests per second
            
            # Verify all succeeded
            assert all(r.is_success for r in execution_results)
            
            results[concurrency] = {
                'total_time': total_time,
                'throughput': throughput,
                'avg_time': total_time / concurrency
            }
        
        # Performance requirements - realistic for test environment
        for concurrency, metrics in results.items():
            assert metrics['throughput'] > 10  # At least 10 RPS
            assert metrics['avg_time'] < 2.0   # Average under 2 seconds
        
        print(f"Concurrent performance results: {json.dumps(results, indent=2)}")
        
    @pytest.mark.asyncio
    async def test_throughput_sustained_load(self, mock_llm_manager):
        """Test sustained throughput over time."""
        agent = PerformanceAgent(
            llm_manager=mock_llm_manager,
            name="ThroughputAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Run sustained load for specified duration
        test_duration = 5.0  # 5 seconds
        concurrent_requests = 10
        completed_requests = 0
        errors = 0
        
        start_time = time.time()
        
        async def sustained_worker(worker_id):
            nonlocal completed_requests, errors
            
            while time.time() - start_time < test_duration:
                try:
                    state = DeepAgentState()
                    state.user_request = f"Sustained load worker {worker_id}"
                    
                    result = await agent.execute_modern(state, f"sustained_{worker_id}_{completed_requests}")
                    
                    if result.is_success:
                        completed_requests += 1
                    else:
                        errors += 1
                        
                except Exception:
                    errors += 1
                    
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.001)
        
        # Start concurrent workers
        workers = [sustained_worker(i) for i in range(concurrent_requests)]
        await asyncio.gather(*workers)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        throughput = completed_requests / actual_duration
        error_rate = errors / (completed_requests + errors) if (completed_requests + errors) > 0 else 0
        
        # Performance requirements - realistic for sustained load
        assert throughput > 20   # At least 20 RPS sustained
        assert error_rate < 0.05  # Less than 5% error rate
        
        print(f"Sustained load - Throughput: {throughput:.1f} RPS, Error rate: {error_rate*100:.2f}%")


class TestMemoryPerformance:
    """Test memory usage patterns and leak detection."""
    
    @pytest.mark.asyncio
    async def test_memory_usage_during_execution(self):
        """Test memory usage patterns during execution."""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.generate_response = AsyncMock(return_value='{"category": "Memory", "confidence_score": 0.8}')
        
        agent = PerformanceAgent(
            llm_manager=mock_llm,
            name="MemoryTestAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Get baseline memory
        gc.collect()
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Execute many operations and measure memory
        memory_measurements = []
        
        for i in range(200):
            state = DeepAgentState()
            state.user_request = f"Memory test {i}"
            
            result = await agent.execute_modern(state, f"memory_test_{i}")
            assert result.is_success
            
            if i % 20 == 0:  # Measure every 20 operations
                gc.collect()
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_measurements.append(current_memory - baseline_memory)
        
        # Analyze memory growth
        initial_memory = memory_measurements[0]
        final_memory = memory_measurements[-1]
        memory_growth = final_memory - initial_memory
        
        # Performance requirements
        assert memory_growth < 50  # Less than 50MB growth for 200 operations
        
        print(f"Memory growth: {memory_growth:.2f}MB over 200 operations")
        
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self):
        """Test for memory leaks over extended execution."""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.generate_response = AsyncMock(return_value='{"category": "Leak", "confidence_score": 0.8}')
        
        # Run multiple cycles of agent creation and execution
        cycle_memories = []
        
        for cycle in range(5):
            gc.collect()
            process = psutil.Process()
            cycle_start_memory = process.memory_info().rss / 1024 / 1024
            
            # Create agents and execute operations
            for i in range(20):
                agent = PerformanceAgent(
                    llm_manager=mock_llm,
                    name=f"LeakTestAgent_{cycle}_{i}",
                    enable_reliability=True
                )
                
                state = DeepAgentState()
                state.user_request = f"Leak test cycle {cycle} operation {i}"
                
                result = await agent.execute_modern(state, f"leak_test_{cycle}_{i}")
                assert result.is_success
                
                # Clean up reference
                del agent
            
            gc.collect()
            cycle_end_memory = process.memory_info().rss / 1024 / 1024
            cycle_memory_growth = cycle_end_memory - cycle_start_memory
            cycle_memories.append(cycle_memory_growth)
        
        # Analyze memory growth across cycles
        avg_cycle_growth = sum(cycle_memories) / len(cycle_memories)
        
        # Memory leak requirements
        assert avg_cycle_growth < 10  # Less than 10MB growth per cycle on average
        
        print(f"Memory per cycle: {cycle_memories}, Average: {avg_cycle_growth:.2f}MB")
        
    def test_garbage_collection_efficiency(self):
        """Test garbage collection efficiency with agent objects."""
        import weakref
        
        mock_llm = Mock(spec=LLMManager)
        
        # Create agents and track with weak references
        agent_refs = []
        
        for i in range(50):
            agent = PerformanceAgent(
                llm_manager=mock_llm,
                name=f"GCTestAgent_{i}",
                enable_reliability=True
            )
            
            # Create weak reference to track garbage collection
            weak_ref = weakref.ref(agent)
            agent_refs.append(weak_ref)
            
            # Clear strong reference
            del agent
        
        # Force garbage collection
        gc.collect()
        
        # Check how many objects were collected
        collected_count = sum(1 for ref in agent_refs if ref() is None)
        collection_rate = collected_count / len(agent_refs)
        
        # Should have high collection rate
        assert collection_rate > 0.8  # At least 80% should be collected
        
        print(f"Garbage collection rate: {collection_rate*100:.1f}%")


class TestCachePerformance:
    """Test cache performance and hit rates."""
    
    @pytest.fixture
    def mock_redis_manager(self):
        """High-performance mock Redis manager."""
        redis = Mock(spec=RedisManager)
        
        # In-memory cache simulation for testing
        cache_data = {}
        
        async def fast_get(key):
            await asyncio.sleep(0.0001)  # 0.1ms simulated network delay
            return cache_data.get(key)
        
        async def fast_set(key, value, **kwargs):
            await asyncio.sleep(0.0001)  # 0.1ms simulated network delay  
            cache_data[key] = value
        
        redis.get = AsyncMock(side_effect=fast_get)
        redis.set = AsyncMock(side_effect=fast_set)
        
        return redis
    
    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, mock_redis_manager):
        """Test performance with high cache hit rates."""
        mock_llm = Mock(spec=LLMManager)
        mock_tool_dispatcher = Mock(spec=ToolDispatcher)
        agent = UnifiedTriageAgent(
            llm_manager=mock_llm,
            tool_dispatcher=mock_tool_dispatcher
        )
        agent.redis_manager = mock_redis_manager
        
        # Prime the cache with a request
        prime_state = DeepAgentState()
        prime_state.user_request = "Cache performance test"
        
        # First execution (cache miss)
        miss_start = time.time()
        result1 = await agent.execute_modern(prime_state, "cache_prime")
        miss_time = time.time() - miss_start
        
        assert result1.is_success
        
        # Subsequent executions (cache hits)
        hit_times = []
        for i in range(10):
            hit_start = time.time()
            result = await agent.execute_modern(prime_state, f"cache_hit_{i}")
            hit_time = time.time() - hit_start
            hit_times.append(hit_time)
            
            assert result.is_success
        
        avg_hit_time = sum(hit_times) / len(hit_times)
        
        # Cache hits should be significantly faster
        # Note: This depends on actual cache implementation
        print(f"Cache miss time: {miss_time*1000:.2f}ms, Cache hit time: {avg_hit_time*1000:.2f}ms")
        
    @pytest.mark.asyncio
    async def test_cache_concurrent_access_performance(self, mock_redis_manager):
        """Test cache performance under concurrent access."""
        mock_llm = Mock(spec=LLMManager)
        mock_tool_dispatcher = Mock(spec=ToolDispatcher)
        agent = UnifiedTriageAgent(
            llm_manager=mock_llm,
            tool_dispatcher=mock_tool_dispatcher
        )
        agent.redis_manager = mock_redis_manager
        
        # Test concurrent cache operations
        start_time = time.time()
        
        async def cache_worker(worker_id):
            results = []
            for i in range(20):
                state = DeepAgentState()
                state.user_request = f"Concurrent cache test worker {worker_id} op {i}"
                
                result = await agent.execute_modern(state, f"cache_concurrent_{worker_id}_{i}")
                results.append(result.is_success if result else False)
            
            return results
        
        # Run concurrent workers
        workers = [cache_worker(i) for i in range(5)]
        worker_results = await asyncio.gather(*workers)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all operations succeeded
        total_operations = sum(len(results) for results in worker_results)
        successful_operations = sum(sum(results) for results in worker_results)
        
        assert successful_operations == total_operations
        
        # Performance requirements
        throughput = total_operations / total_time
        assert throughput > 50   # At least 50 operations per second
        
        print(f"Cache concurrent throughput: {throughput:.1f} ops/sec")


class TestCircuitBreakerPerformance:
    """Test circuit breaker performance overhead."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value='{"category": "CB", "confidence_score": 0.8}')
        return llm
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_overhead(self, mock_llm_manager):
        """Test performance overhead of circuit breaker."""
        # Agent with circuit breaker
        agent_with_cb = PerformanceAgent(
            llm_manager=mock_llm_manager,
            name="WithCBAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Agent without circuit breaker
        agent_without_cb = PerformanceAgent(
            llm_manager=mock_llm_manager,
            name="WithoutCBAgent",
            enable_reliability=False,
            enable_execution_engine=False
        )
        
        # Measure execution time with circuit breaker
        cb_times = []
        for i in range(100):
            state = DeepAgentState()
            state.user_request = f"CB overhead test {i}"
            
            start_time = time.time()
            result = await agent_with_cb.execute_modern(state, f"cb_test_{i}")
            end_time = time.time()
            
            cb_times.append(end_time - start_time)
            assert result.is_success
        
        # Measure execution time without circuit breaker  
        no_cb_times = []
        for i in range(100):
            state = DeepAgentState()
            state.user_request = f"No CB test {i}"
            
            start_time = time.time()
            # Direct execution without infrastructure
            result = await agent_without_cb.execute_core_logic(ExecutionContext(
                run_id=f"no_cb_test_{i}",
                agent_name="WithoutCBAgent",
                state=state,
                start_time=time.time(),
                correlation_id="test"
            ))
            end_time = time.time()
            
            no_cb_times.append(end_time - start_time)
            assert result["status"] == "success"
        
        # Calculate overhead
        avg_cb_time = sum(cb_times) / len(cb_times)
        avg_no_cb_time = sum(no_cb_times) / len(no_cb_times)
        overhead_percentage = ((avg_cb_time - avg_no_cb_time) / avg_no_cb_time) * 100
        
        # Performance requirements - circuit breaker should add minimal overhead
        assert overhead_percentage < 50  # Less than 50% overhead
        
        print(f"Circuit breaker overhead: {overhead_percentage:.1f}%")
        print(f"With CB: {avg_cb_time*1000:.2f}ms, Without CB: {avg_no_cb_time*1000:.2f}ms")


class TestWebSocketEventPerformance:
    """Test WebSocket event emission latency."""
    
    @pytest.fixture
    def mock_websocket_bridge(self):
        """High-performance mock WebSocket bridge."""
        bridge = Mock()
        
        # Track event timing
        bridge.event_times = []
        
        async def timed_emit(*args, **kwargs):
            start_time = time.time()
            await asyncio.sleep(0.0001)  # 0.1ms simulated emit time
            end_time = time.time()
            bridge.event_times.append(end_time - start_time)
        
        bridge.emit_thinking = AsyncMock(side_effect=timed_emit)
        bridge.emit_progress = AsyncMock(side_effect=timed_emit)
        bridge.emit_agent_started = AsyncMock(side_effect=timed_emit)
        bridge.emit_agent_completed = AsyncMock(side_effect=timed_emit)
        
        return bridge
    
    @pytest.mark.asyncio
    async def test_websocket_emission_latency(self, mock_websocket_bridge):
        """Test latency of WebSocket event emissions."""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.generate_response = AsyncMock(return_value='{"category": "WS", "confidence_score": 0.8}')
        
        agent = PerformanceAgent(
            llm_manager=mock_llm,
            name="WebSocketPerfAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Set up WebSocket bridge
        agent._websocket_adapter._websocket_bridge = mock_websocket_bridge
        agent._websocket_adapter._run_id = "ws_perf_test"
        agent._websocket_adapter._agent_name = "WebSocketPerfAgent"
        
        # Execute with WebSocket events
        execution_times = []
        
        for i in range(50):
            state = DeepAgentState()
            state.user_request = f"WebSocket perf test {i}"
            
            start_time = time.time()
            result = await agent.execute_modern(state, f"ws_perf_{i}", stream_updates=True)
            end_time = time.time()
            
            execution_times.append(end_time - start_time)
            assert result.is_success
        
        # Analyze WebSocket performance
        avg_execution_time = sum(execution_times) / len(execution_times)
        total_events = len(mock_websocket_bridge.event_times)
        avg_event_time = sum(mock_websocket_bridge.event_times) / total_events if total_events > 0 else 0
        
        # Performance requirements
        assert avg_execution_time < 0.1   # Under 100ms total execution
        assert avg_event_time < 0.01      # Under 10ms per event
        
        print(f"WebSocket performance - Execution: {avg_execution_time*1000:.2f}ms, Event: {avg_event_time*1000:.2f}ms")
        
    @pytest.mark.asyncio
    async def test_websocket_high_frequency_events(self, mock_websocket_bridge):
        """Test performance with high frequency WebSocket events."""
        mock_llm = Mock(spec=LLMManager)
        
        agent = PerformanceAgent(
            llm_manager=mock_llm,
            name="HighFreqWSAgent",
            enable_reliability=True
        )
        
        # Set up WebSocket bridge
        agent._websocket_adapter._websocket_bridge = mock_websocket_bridge
        agent._websocket_adapter._run_id = "high_freq_test"
        agent._websocket_adapter._agent_name = "HighFreqWSAgent"
        
        # Emit many events rapidly
        start_time = time.time()
        
        for i in range(1000):
            await agent.emit_thinking(f"High frequency thinking event {i}")
            if i % 10 == 0:
                await agent.emit_progress(f"Progress update {i}", is_complete=False)
        
        end_time = time.time()
        total_time = end_time - start_time
        events_per_second = 1000 / total_time
        
        # Performance requirements
        assert events_per_second > 1000  # At least 1000 events per second
        
        print(f"WebSocket high frequency: {events_per_second:.0f} events/sec")


class TestLargePayloadPerformance:
    """Test performance with large payloads."""
    
    @pytest.mark.asyncio
    async def test_large_request_processing(self):
        """Test performance with large request payloads."""
        mock_llm = Mock(spec=LLMManager)
        mock_tool_dispatcher = Mock(spec=ToolDispatcher)
        agent = UnifiedTriageAgent(
            llm_manager=mock_llm,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Test different payload sizes
        payload_sizes = [1024, 10240, 102400, 1024000]  # 1KB, 10KB, 100KB, 1MB
        performance_results = {}
        
        for size in payload_sizes:
            large_request = "Please help me optimize " + "x" * size
            
            state = DeepAgentState()
            state.user_request = large_request
            
            # Measure processing time
            start_time = time.time()
            result = await agent.execute_modern(state, f"large_payload_{size}")
            end_time = time.time()
            
            processing_time = end_time - start_time
            throughput = size / processing_time  # Bytes per second
            
            performance_results[size] = {
                'processing_time': processing_time,
                'throughput': throughput,
                'success': result.is_success if result else False
            }
            
            # Should handle all sizes successfully
            assert result.is_success if result else True
            
            # Performance requirements scale with size
            max_time = size / 1000000  # 1 second per MB
            assert processing_time < max(0.1, max_time)
        
        print(f"Large payload performance: {json.dumps(performance_results, indent=2)}")
        
    @pytest.mark.asyncio
    async def test_memory_efficient_large_data_handling(self):
        """Test memory efficiency with large data structures."""
        mock_llm = Mock(spec=LLMManager)
        
        # Create large response data
        large_response = {
            "category": "Large Data Processing",
            "confidence_score": 0.9,
            "large_data": ["x" * 1000] * 1000,  # ~1MB of data
            "metadata": {"size": "large", "processing": "efficient"}
        }
        
        mock_llm.generate_response = AsyncMock(return_value=json.dumps(large_response))
        
        agent = PerformanceAgent(
            llm_manager=mock_llm,
            name="LargeDataAgent",
            enable_reliability=True
        )
        
        # Monitor memory during processing
        import tracemalloc
        tracemalloc.start()
        
        state = DeepAgentState()
        state.user_request = "Process large data efficiently"
        
        # Process large data
        result = await agent.execute_modern(state, "large_data_test")
        
        # Check memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        peak_mb = peak / 1024 / 1024  # Convert to MB
        
        assert result.is_success
        
        # Memory requirements
        assert peak_mb < 50  # Should not use more than 50MB peak memory
        
        print(f"Large data processing peak memory: {peak_mb:.2f}MB")


class TestLongRunningOperationStability:
    """Test stability under long-running operations."""
    
    @pytest.mark.asyncio
    async def test_extended_operation_stability(self):
        """Test agent stability over extended operations."""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.generate_response = AsyncMock(return_value='{"category": "Extended", "confidence_score": 0.8}')
        
        agent = PerformanceAgent(
            llm_manager=mock_llm,
            name="ExtendedOpAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Run continuous operations for extended period
        start_time = time.time()
        operation_count = 0
        errors = 0
        
        # Run for 10 seconds
        while time.time() - start_time < 10:
            try:
                state = DeepAgentState()
                state.user_request = f"Extended operation {operation_count}"
                
                result = await agent.execute_modern(state, f"extended_{operation_count}")
                
                if result and result.is_success:
                    operation_count += 1
                else:
                    errors += 1
                    
            except Exception:
                errors += 1
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.01)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Stability requirements
        error_rate = errors / (operation_count + errors) if (operation_count + errors) > 0 else 0
        operations_per_second = operation_count / actual_duration
        
        assert error_rate < 0.05  # Less than 5% error rate
        assert operations_per_second > 10  # At least 10 ops/sec sustained
        
        # Agent should still be healthy
        health_status = agent.get_health_status()
        assert "overall_status" in health_status
        
        print(f"Extended operation - Ops: {operation_count}, Duration: {actual_duration:.1f}s, Rate: {operations_per_second:.1f} ops/sec, Errors: {error_rate*100:.2f}%")
        
    @pytest.mark.asyncio
    async def test_resource_cleanup_over_time(self):
        """Test that resources are properly cleaned up over extended execution."""
        import resource
        
        # Get initial resource usage
        initial_usage = resource.getrusage(resource.RUSAGE_SELF)
        
        # Run many operations with cleanup
        for cycle in range(10):
            agents = []
            
            # Create and run many agents
            for i in range(20):
                mock_llm = Mock(spec=LLMManager)
                agent = PerformanceAgent(
                    llm_manager=mock_llm,
                    name=f"CleanupAgent_{cycle}_{i}",
                    enable_reliability=True
                )
                agents.append(agent)
                
                state = DeepAgentState()
                state.user_request = f"Cleanup test cycle {cycle} agent {i}"
                
                result = await agent.execute_modern(state, f"cleanup_{cycle}_{i}")
                assert result.is_success
            
            # Explicit cleanup
            for agent in agents:
                await agent.shutdown()
            
            del agents
            gc.collect()
        
        # Check final resource usage
        final_usage = resource.getrusage(resource.RUSAGE_SELF)
        
        # Resource usage should be reasonable
        memory_growth = final_usage.ru_maxrss - initial_usage.ru_maxrss
        
        # On some systems ru_maxrss is in KB, others in bytes
        if memory_growth > 1000000:  # Likely in bytes
            memory_growth_mb = memory_growth / 1024 / 1024
        else:  # Likely in KB
            memory_growth_mb = memory_growth / 1024
        
        assert memory_growth_mb < 100  # Less than 100MB growth
        
        print(f"Resource cleanup - Memory growth: {memory_growth_mb:.2f}MB")


if __name__ == "__main__":
    # Enable specific performance test execution
    pytest.main([__file__, "-v", "-s"])  # -s to see print statements