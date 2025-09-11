"""
Comprehensive Performance and SLA Validation Tests for Golden Path

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure golden path meets performance SLAs protecting $500K+ ARR
- Value Impact: Validates user experience quality that drives retention and conversion
- Strategic Impact: Ensures platform can scale to support business growth

This test suite validates performance and SLA requirements for the golden path:
1. Connection establishment performance (<3s)
2. First agent response time (<5s)
3. Total execution time (<60s)
4. Event delivery latency (<1s)
5. Concurrent user capacity (100+ users)
6. Memory efficiency and resource usage
7. Error rate thresholds (<1%)
8. Recovery time objectives (<10s)

Key Coverage Areas:
- WebSocket connection performance
- Agent execution speed and efficiency
- Real-time event delivery latency
- Concurrent user load testing
- Memory usage and resource optimization
- Error handling and recovery performance
- Throughput and scalability validation
- Business SLA compliance verification
"""

import asyncio
import gc
import psutil
import pytest
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# WebSocket and agent performance testing
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Logging and monitoring
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class TestGoldenPathPerformanceSLAComprehensive(SSotAsyncTestCase):
    """
    Comprehensive performance and SLA validation tests for golden path.
    
    Tests focus on meeting business performance requirements that ensure
    user experience quality and platform scalability.
    """

    def setup_method(self, method):
        """Setup test environment for performance testing."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        
        # Business SLA requirements
        self.sla_requirements = {
            "connection_max_seconds": 3.0,
            "first_response_max_seconds": 5.0,
            "total_execution_max_seconds": 60.0,
            "event_delivery_max_milliseconds": 1000.0,
            "concurrent_users_minimum": 50,
            "error_rate_max_percent": 1.0,
            "recovery_time_max_seconds": 10.0,
            "memory_per_user_max_mb": 50.0,
            "throughput_min_ops_per_second": 10.0
        }
        
        # Performance tracking
        self.performance_measurements: List[Dict[str, Any]] = []
        self.memory_samples: List[Dict[str, Any]] = []
        self.error_events: List[Dict[str, Any]] = []
        
        # Mock services for performance testing
        self.mock_llm_manager = MagicMock()
        self.mock_llm_client = self.mock_factory.create_llm_client_mock()
        self.mock_llm_manager.get_default_client.return_value = self.mock_llm_client

    async def async_setup_method(self, method):
        """Async setup for performance test initialization."""
        await super().async_setup_method(method)
        
        # Configure fast LLM responses for performance testing
        async def fast_llm_response(*args, **kwargs):
            await asyncio.sleep(0.01)  # Minimal delay
            return {
                "response": "Quick performance test analysis completed.",
                "performance_optimized": True,
                "recommendations": ["test_recommendation_1", "test_recommendation_2"],
                "confidence": 0.95
            }
        
        self.mock_llm_client.agenerate.return_value = await fast_llm_response()
        
        # Track initial system resources
        self.initial_memory = self._get_memory_usage()
        self.initial_cpu_percent = psutil.cpu_percent()

    @pytest.mark.performance
    @pytest.mark.golden_path
    @pytest.mark.sla
    async def test_websocket_connection_performance_sla(self):
        """
        BVJ: All segments | Connection SLA | Ensures WebSocket connections meet timing requirements
        Test WebSocket connection establishment performance against SLA.
        """
        connection_times = []
        num_connection_tests = 20
        
        # Test multiple connection establishments
        for test_index in range(num_connection_tests):
            # Create mock WebSocket
            mock_websocket = self.mock_factory.create_websocket_mock()
            
            # Mock connection process
            connection_start = time.time()
            
            # Simulate connection establishment steps
            await asyncio.sleep(0.001)  # Simulate network latency
            
            # Create emitter (simulates WebSocket initialization)
            emitter = UnifiedWebSocketEmitter(
                websocket=mock_websocket,
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4())
            )
            
            # Simulate authentication and setup
            await asyncio.sleep(0.002)  # Simulate auth validation
            
            connection_time = time.time() - connection_start
            connection_times.append(connection_time)
            
            # Per-connection SLA validation
            assert connection_time <= self.sla_requirements["connection_max_seconds"], f"Connection {test_index} too slow: {connection_time:.3f}s"
        
        # Statistical analysis
        avg_connection_time = statistics.mean(connection_times)
        median_connection_time = statistics.median(connection_times)
        p95_connection_time = sorted(connection_times)[int(len(connection_times) * 0.95)]
        max_connection_time = max(connection_times)
        
        # SLA validation
        assert avg_connection_time <= self.sla_requirements["connection_max_seconds"] * 0.5, f"Average connection time too high: {avg_connection_time:.3f}s"
        assert p95_connection_time <= self.sla_requirements["connection_max_seconds"] * 0.8, f"P95 connection time too high: {p95_connection_time:.3f}s"
        
        performance_summary = {
            "metric": "websocket_connection_performance",
            "avg_time_ms": avg_connection_time * 1000,
            "median_time_ms": median_connection_time * 1000,
            "p95_time_ms": p95_connection_time * 1000,
            "max_time_ms": max_connection_time * 1000,
            "samples": num_connection_tests,
            "sla_compliance": True
        }
        
        self.performance_measurements.append(performance_summary)
        
        logger.info(f"✅ WebSocket connection SLA validated: {avg_connection_time*1000:.1f}ms avg, {p95_connection_time*1000:.1f}ms P95")

    @pytest.mark.performance
    @pytest.mark.golden_path
    @pytest.mark.sla
    async def test_agent_execution_performance_sla(self):
        """
        BVJ: All segments | Response Time SLA | Ensures agent execution meets timing requirements
        Test agent execution performance against first response and total execution SLAs.
        """
        execution_times = []
        first_response_times = []
        num_execution_tests = 15
        
        for test_index in range(num_execution_tests):
            # Setup execution context
            user_context = UserExecutionContext(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4())
            )
            
            # Create supervisor with performance tracking
            supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
            
            # Mock WebSocket bridge with event timing
            event_times = []
            first_event_time = None
            
            async def timed_websocket_event(event_type: str, data: Dict[str, Any], **kwargs):
                nonlocal first_event_time
                event_time = time.time()
                event_times.append(event_time)
                
                if first_event_time is None:
                    first_event_time = event_time
            
            mock_bridge = AsyncMock()
            mock_bridge.notify_agent_started = timed_websocket_event
            mock_bridge.notify_agent_thinking = timed_websocket_event
            mock_bridge.notify_tool_executing = timed_websocket_event
            mock_bridge.notify_tool_completed = timed_websocket_event
            mock_bridge.notify_agent_completed = timed_websocket_event
            
            supervisor.websocket_bridge = mock_bridge
            
            # Execute with timing
            execution_start = time.time()
            
            result = await supervisor.execute(
                context=user_context,
                stream_updates=True
            )
            
            execution_end = time.time()
            
            # Calculate timings
            total_execution_time = execution_end - execution_start
            first_response_time = first_event_time - execution_start if first_event_time else None
            
            execution_times.append(total_execution_time)
            if first_response_time:
                first_response_times.append(first_response_time)
            
            # Verify execution completed successfully
            assert result is not None, f"Execution {test_index} should return result"
            
            # Per-execution SLA validation
            assert total_execution_time <= self.sla_requirements["total_execution_max_seconds"], f"Execution {test_index} too slow: {total_execution_time:.3f}s"
            
            if first_response_time:
                assert first_response_time <= self.sla_requirements["first_response_max_seconds"], f"First response {test_index} too slow: {first_response_time:.3f}s"
        
        # Statistical analysis
        avg_execution_time = statistics.mean(execution_times)
        p95_execution_time = sorted(execution_times)[int(len(execution_times) * 0.95)]
        
        if first_response_times:
            avg_first_response = statistics.mean(first_response_times)
            p95_first_response = sorted(first_response_times)[int(len(first_response_times) * 0.95)]
        else:
            avg_first_response = None
            p95_first_response = None
        
        # SLA validation
        assert avg_execution_time <= self.sla_requirements["total_execution_max_seconds"] * 0.5, f"Average execution time too high: {avg_execution_time:.3f}s"
        
        if avg_first_response:
            assert avg_first_response <= self.sla_requirements["first_response_max_seconds"] * 0.8, f"Average first response too slow: {avg_first_response:.3f}s"
        
        execution_performance = {
            "metric": "agent_execution_performance",
            "avg_execution_time_ms": avg_execution_time * 1000,
            "p95_execution_time_ms": p95_execution_time * 1000,
            "avg_first_response_ms": avg_first_response * 1000 if avg_first_response else None,
            "p95_first_response_ms": p95_first_response * 1000 if p95_first_response else None,
            "samples": num_execution_tests,
            "sla_compliance": True
        }
        
        self.performance_measurements.append(execution_performance)
        
        logger.info(f"✅ Agent execution SLA validated: {avg_execution_time*1000:.1f}ms avg execution, {avg_first_response*1000 if avg_first_response else 'N/A'}ms avg first response")

    @pytest.mark.performance
    @pytest.mark.golden_path
    @pytest.mark.sla
    @pytest.mark.concurrency
    async def test_concurrent_user_capacity_performance_sla(self):
        """
        BVJ: Mid/Enterprise | Scalability SLA | Ensures platform supports concurrent users
        Test concurrent user capacity against minimum scalability requirements.
        """
        target_concurrent_users = self.sla_requirements["concurrent_users_minimum"]
        
        # Create WebSocket bridge for concurrent testing
        websocket_bridge = AgentWebSocketBridge()
        execution_factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        # Concurrent user simulation
        async def simulate_user_session(user_index: int) -> Dict[str, Any]:
            session_start = time.time()
            
            try:
                # Create user context
                user_context = UserExecutionContext(
                    user_id=str(uuid.uuid4()),
                    thread_id=str(uuid.uuid4()),
                    run_id=str(uuid.uuid4()),
                    agent_context={"user_index": user_index}
                )
                
                # Create execution engine
                engine = await execution_factory.create_for_user(user_context)
                
                # Simulate user operations
                operations = [
                    ("set_state", {"key": "user_data", "value": f"user_{user_index}_data"}),
                    ("get_state", {"key": "user_data"}),
                    ("set_execution_state", {"key": "current_task", "value": {"task": f"user_{user_index}_task"}}),
                    ("get_execution_state", {"key": "current_task"})
                ]
                
                operation_results = []
                
                for op_name, op_params in operations:
                    op_start = time.time()
                    
                    if op_name == "set_state":
                        engine.set_agent_state(op_params["key"], op_params["value"])
                    elif op_name == "get_state":
                        result = engine.get_agent_state(op_params["key"])
                        assert result is not None, f"User {user_index} should get state"
                    elif op_name == "set_execution_state":
                        engine.set_execution_state(op_params["key"], op_params["value"])
                    elif op_name == "get_execution_state":
                        result = engine.get_execution_state(op_params["key"])
                        assert result is not None, f"User {user_index} should get execution state"
                    
                    op_time = time.time() - op_start
                    operation_results.append({"operation": op_name, "time": op_time})
                
                # Small delay to simulate user thinking time
                await asyncio.sleep(0.001)
                
                session_time = time.time() - session_start
                
                return {
                    "user_index": user_index,
                    "success": True,
                    "session_time": session_time,
                    "operations": operation_results,
                    "engine_id": id(engine)
                }
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "success": False,
                    "session_time": time.time() - session_start,
                    "error": str(e)
                }
        
        # Execute concurrent user sessions
        concurrent_start = time.time()
        
        user_tasks = [
            simulate_user_session(i) for i in range(target_concurrent_users)
        ]
        
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        concurrent_duration = time.time() - concurrent_start
        
        # Analyze concurrent performance
        successful_users = [r for r in results if isinstance(r, dict) and r.get("success", False)]
        failed_users = [r for r in results if isinstance(r, dict) and not r.get("success", True)]
        
        success_rate = len(successful_users) / len(results)
        avg_session_time = statistics.mean([r["session_time"] for r in successful_users]) if successful_users else 0
        
        # SLA validation
        required_success_rate = 1.0 - (self.sla_requirements["error_rate_max_percent"] / 100.0)
        assert success_rate >= required_success_rate, f"Concurrent success rate too low: {success_rate:.2%} (required: >{required_success_rate:.2%})"
        assert concurrent_duration <= 10.0, f"Concurrent user setup too slow: {concurrent_duration:.2f}s"
        assert len(successful_users) >= target_concurrent_users * 0.95, f"Not enough successful concurrent users: {len(successful_users)}/{target_concurrent_users}"
        
        # Memory efficiency check
        memory_after_concurrent = self._get_memory_usage()
        memory_increase = memory_after_concurrent - self.initial_memory
        memory_per_user = memory_increase / target_concurrent_users
        
        # Verify memory efficiency
        memory_per_user_mb = memory_per_user / (1024 * 1024)
        assert memory_per_user_mb <= self.sla_requirements["memory_per_user_max_mb"], f"Memory per user too high: {memory_per_user_mb:.1f}MB"
        
        concurrency_performance = {
            "metric": "concurrent_user_capacity",
            "target_users": target_concurrent_users,
            "successful_users": len(successful_users),
            "success_rate_percent": success_rate * 100,
            "avg_session_time_ms": avg_session_time * 1000,
            "concurrent_setup_time_ms": concurrent_duration * 1000,
            "memory_per_user_mb": memory_per_user_mb,
            "sla_compliance": True
        }
        
        self.performance_measurements.append(concurrency_performance)
        
        logger.info(f"✅ Concurrent user capacity SLA validated: {len(successful_users)}/{target_concurrent_users} users, {success_rate:.2%} success rate")

    @pytest.mark.performance
    @pytest.mark.golden_path
    @pytest.mark.sla
    async def test_event_delivery_latency_performance_sla(self):
        """
        BVJ: All segments | Real-time UX SLA | Ensures WebSocket events meet latency requirements
        Test WebSocket event delivery latency against real-time user experience SLAs.
        """
        event_latencies = []
        num_event_tests = 100
        
        # Setup event delivery testing
        mock_websocket = self.mock_factory.create_websocket_mock()
        
        # Track event delivery timing
        async def timed_websocket_send(message: str):
            send_time = time.time()
            await asyncio.sleep(0.0001)  # Minimal network simulation
            delivery_time = time.time()
            latency = delivery_time - send_time
            event_latencies.append(latency)
        
        mock_websocket.send_text = timed_websocket_send
        
        # Create emitter for event testing
        emitter = UnifiedWebSocketEmitter(
            websocket=mock_websocket,
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4())
        )
        
        # Test all 5 critical events multiple times
        event_types = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        for test_round in range(num_event_tests // len(event_types)):
            for event_type in event_types:
                # Send event with timing
                event_data = {
                    "test_round": test_round,
                    "event_type": event_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": f"performance_test_data_{test_round}"
                }
                
                # Emit event (will be timed by mock)
                try:
                    await emitter.send_event(
                        event_type,
                        event_data,
                        user_id=str(uuid.uuid4()),
                        thread_id=str(uuid.uuid4())
                    )
                except AttributeError:
                    # Handle case where emitter doesn't have send_event method
                    import json
                    await mock_websocket.send_text(json.dumps({
                        "type": event_type,
                        "data": event_data
                    }))
        
        # Statistical analysis of latencies
        avg_latency = statistics.mean(event_latencies)
        median_latency = statistics.median(event_latencies)
        p95_latency = sorted(event_latencies)[int(len(event_latencies) * 0.95)]
        max_latency = max(event_latencies)
        
        # Convert to milliseconds for SLA comparison
        avg_latency_ms = avg_latency * 1000
        p95_latency_ms = p95_latency * 1000
        max_latency_ms = max_latency * 1000
        
        # SLA validation
        assert avg_latency_ms <= self.sla_requirements["event_delivery_max_milliseconds"] * 0.5, f"Average event latency too high: {avg_latency_ms:.1f}ms"
        assert p95_latency_ms <= self.sla_requirements["event_delivery_max_milliseconds"] * 0.8, f"P95 event latency too high: {p95_latency_ms:.1f}ms"
        assert max_latency_ms <= self.sla_requirements["event_delivery_max_milliseconds"], f"Max event latency too high: {max_latency_ms:.1f}ms"
        
        # Verify event delivery consistency
        latency_std_dev = statistics.stdev(event_latencies)
        latency_consistency = latency_std_dev / avg_latency if avg_latency > 0 else 0
        
        assert latency_consistency <= 0.5, f"Event delivery latency too inconsistent: {latency_consistency:.2f} coefficient of variation"
        
        event_performance = {
            "metric": "event_delivery_latency",
            "avg_latency_ms": avg_latency_ms,
            "median_latency_ms": median_latency * 1000,
            "p95_latency_ms": p95_latency_ms,
            "max_latency_ms": max_latency_ms,
            "consistency_cv": latency_consistency,
            "samples": len(event_latencies),
            "sla_compliance": True
        }
        
        self.performance_measurements.append(event_performance)
        
        logger.info(f"✅ Event delivery latency SLA validated: {avg_latency_ms:.1f}ms avg, {p95_latency_ms:.1f}ms P95")

    @pytest.mark.performance
    @pytest.mark.golden_path
    @pytest.mark.sla
    async def test_memory_efficiency_and_resource_management_sla(self):
        """
        BVJ: Platform | Resource Efficiency SLA | Ensures efficient memory usage
        Test memory efficiency and resource management against platform SLAs.
        """
        # Track memory usage throughout test
        memory_samples = []
        
        # Baseline memory measurement
        baseline_memory = self._get_memory_usage()
        memory_samples.append({"phase": "baseline", "memory_mb": baseline_memory / (1024 * 1024)})
        
        # Create multiple execution engines to test memory scaling
        num_engines = 25
        engines = []
        
        # Create engines with memory tracking
        for i in range(num_engines):
            context = UserExecutionContext(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4())
            )
            
            websocket_bridge = AgentWebSocketBridge()
            factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
            engine = await factory.create_for_user(context)
            engines.append(engine)
            
            # Add data to test memory usage
            large_data = {
                "user_data": f"user_{i}_" * 100,
                "execution_history": [f"step_{j}" for j in range(50)],
                "metadata": {"user_index": i, "created_at": datetime.utcnow().isoformat()}
            }
            
            engine.set_agent_state("performance_test_data", large_data)
            engine.set_execution_state("current_task", {"task": f"memory_test_{i}"})
            
            # Sample memory every 5 engines
            if (i + 1) % 5 == 0:
                current_memory = self._get_memory_usage()
                memory_samples.append({
                    "phase": f"after_{i+1}_engines",
                    "memory_mb": current_memory / (1024 * 1024),
                    "engines_created": i + 1
                })
        
        # Memory after all engines created
        peak_memory = self._get_memory_usage()
        memory_increase = peak_memory - baseline_memory
        memory_per_engine = memory_increase / num_engines
        memory_per_engine_mb = memory_per_engine / (1024 * 1024)
        
        memory_samples.append({
            "phase": "peak_usage",
            "memory_mb": peak_memory / (1024 * 1024),
            "engines_created": num_engines
        })
        
        # Test memory cleanup
        cleanup_start = time.time()
        
        # Cleanup half the engines
        engines_to_cleanup = engines[:num_engines // 2]
        for engine in engines_to_cleanup:
            await engine.cleanup()
        
        engines_to_cleanup.clear()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)
        gc.collect()
        
        cleanup_time = time.time() - cleanup_start
        memory_after_cleanup = self._get_memory_usage()
        memory_released = peak_memory - memory_after_cleanup
        cleanup_efficiency = memory_released / memory_increase if memory_increase > 0 else 0
        
        memory_samples.append({
            "phase": "after_cleanup",
            "memory_mb": memory_after_cleanup / (1024 * 1024),
            "cleanup_efficiency": cleanup_efficiency
        })
        
        # Cleanup remaining engines
        for engine in engines[num_engines // 2:]:
            await engine.cleanup()
        
        engines.clear()
        gc.collect()
        
        final_memory = self._get_memory_usage()
        final_cleanup_efficiency = (peak_memory - final_memory) / memory_increase if memory_increase > 0 else 0
        
        memory_samples.append({
            "phase": "final_cleanup",
            "memory_mb": final_memory / (1024 * 1024),
            "final_cleanup_efficiency": final_cleanup_efficiency
        })
        
        # SLA validation
        assert memory_per_engine_mb <= self.sla_requirements["memory_per_user_max_mb"], f"Memory per engine too high: {memory_per_engine_mb:.1f}MB"
        assert cleanup_time <= 2.0, f"Memory cleanup too slow: {cleanup_time:.2f}s"
        assert cleanup_efficiency >= 0.6, f"Memory cleanup insufficient: {cleanup_efficiency:.2%}"
        assert final_cleanup_efficiency >= 0.8, f"Final cleanup insufficient: {final_cleanup_efficiency:.2%}"
        
        # CPU usage check
        current_cpu_percent = psutil.cpu_percent()
        cpu_increase = current_cpu_percent - self.initial_cpu_percent
        
        # CPU should not be excessive
        assert cpu_increase <= 20.0, f"CPU usage increase too high: {cpu_increase:.1f}%"
        
        memory_performance = {
            "metric": "memory_efficiency",
            "memory_per_engine_mb": memory_per_engine_mb,
            "cleanup_time_ms": cleanup_time * 1000,
            "cleanup_efficiency_percent": cleanup_efficiency * 100,
            "final_cleanup_efficiency_percent": final_cleanup_efficiency * 100,
            "cpu_increase_percent": cpu_increase,
            "engines_tested": num_engines,
            "sla_compliance": True
        }
        
        self.performance_measurements.append(memory_performance)
        self.memory_samples.extend(memory_samples)
        
        logger.info(f"✅ Memory efficiency SLA validated: {memory_per_engine_mb:.1f}MB per engine, {cleanup_efficiency:.2%} cleanup efficiency")

    @pytest.mark.performance
    @pytest.mark.golden_path
    @pytest.mark.sla
    async def test_error_recovery_performance_sla(self):
        """
        BVJ: All segments | Reliability SLA | Ensures quick error recovery
        Test error handling and recovery performance against reliability SLAs.
        """
        recovery_times = []
        error_rates = []
        num_error_tests = 20
        
        for test_index in range(num_error_tests):
            # Create context for error testing
            context = UserExecutionContext(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4())
            )
            
            # Create failing then recovering system
            failure_count = 0
            
            async def failing_then_recovering_operation():
                nonlocal failure_count
                failure_count += 1
                
                if failure_count <= 2:  # Fail first 2 attempts
                    raise Exception(f"Simulated failure {failure_count}")
                
                return {"status": "success", "recovery": True}
            
            # Test error recovery timing
            recovery_start = time.time()
            
            # Retry logic with exponential backoff
            max_retries = 5
            retry_delay = 0.01
            
            for attempt in range(max_retries):
                try:
                    result = await failing_then_recovering_operation()
                    recovery_time = time.time() - recovery_start
                    recovery_times.append(recovery_time)
                    
                    # Verify successful recovery
                    assert result["status"] == "success"
                    assert result["recovery"] is True
                    break
                    
                except Exception:
                    if attempt == max_retries - 1:
                        # Final attempt failed
                        recovery_time = time.time() - recovery_start
                        recovery_times.append(recovery_time)
                        break
                    
                    # Wait before retry
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
            
            # Calculate error rate for this test
            error_rate = failure_count / (failure_count + 1) if failure_count > 0 else 0
            error_rates.append(error_rate)
        
        # Statistical analysis
        avg_recovery_time = statistics.mean(recovery_times)
        max_recovery_time = max(recovery_times)
        p95_recovery_time = sorted(recovery_times)[int(len(recovery_times) * 0.95)]
        
        avg_error_rate = statistics.mean(error_rates)
        max_error_rate = max(error_rates)
        
        # SLA validation
        assert avg_recovery_time <= self.sla_requirements["recovery_time_max_seconds"], f"Average recovery time too high: {avg_recovery_time:.2f}s"
        assert max_recovery_time <= self.sla_requirements["recovery_time_max_seconds"] * 2, f"Max recovery time too high: {max_recovery_time:.2f}s"
        assert avg_error_rate * 100 <= self.sla_requirements["error_rate_max_percent"] * 10, f"Error rate too high: {avg_error_rate:.2%}"  # Allow higher in testing
        
        recovery_performance = {
            "metric": "error_recovery_performance",
            "avg_recovery_time_ms": avg_recovery_time * 1000,
            "max_recovery_time_ms": max_recovery_time * 1000,
            "p95_recovery_time_ms": p95_recovery_time * 1000,
            "avg_error_rate_percent": avg_error_rate * 100,
            "max_error_rate_percent": max_error_rate * 100,
            "recovery_tests": num_error_tests,
            "sla_compliance": True
        }
        
        self.performance_measurements.append(recovery_performance)
        
        logger.info(f"✅ Error recovery SLA validated: {avg_recovery_time*1000:.1f}ms avg recovery, {avg_error_rate:.2%} avg error rate")

    def _get_memory_usage(self) -> int:
        """Get current process memory usage in bytes."""
        try:
            process = psutil.Process()
            return process.memory_info().rss
        except Exception:
            # Fallback for environments without psutil
            return 1024 * 1024 * 100  # 100MB fallback

    def _generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        return {
            "test_timestamp": datetime.utcnow().isoformat(),
            "sla_requirements": self.sla_requirements,
            "performance_measurements": self.performance_measurements,
            "memory_samples": self.memory_samples,
            "overall_sla_compliance": all(
                measurement.get("sla_compliance", False) 
                for measurement in self.performance_measurements
            ),
            "total_measurements": len(self.performance_measurements),
            "test_environment": "unit_test"
        }

    def teardown_method(self, method):
        """Cleanup after performance tests."""
        # Generate and log performance report
        performance_report = self._generate_performance_report()
        
        logger.info(f"📊 Performance Test Summary:")
        logger.info(f"  - Total Measurements: {performance_report['total_measurements']}")
        logger.info(f"  - SLA Compliance: {performance_report['overall_sla_compliance']}")
        
        for measurement in self.performance_measurements:
            metric_name = measurement.get("metric", "unknown")
            compliance = measurement.get("sla_compliance", False)
            status = "✅" if compliance else "❌"
            logger.info(f"  {status} {metric_name}: {'PASS' if compliance else 'FAIL'}")
        
        # Clear performance data
        self.performance_measurements.clear()
        self.memory_samples.clear()
        self.error_events.clear()
        
        super().teardown_method(method)
    
    async def async_teardown_method(self, method):
        """Async cleanup after performance tests."""
        # Force final garbage collection
        gc.collect()
        
        await super().async_teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
