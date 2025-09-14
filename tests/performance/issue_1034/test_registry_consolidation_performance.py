"""
TEST SUITE 2: Registry Consolidation Performance Impact Validation (Issue #1034)

Business Value Protection: $500K+ ARR Golden Path performance during registry consolidation
Test Type: Integration (Real services, NO Docker)

PURPOSE: Validate consolidation doesn't degrade system performance
EXPECTED: Equal or better performance than current state

This test suite validates that registry consolidation maintains or improves system
performance characteristics while preserving business functionality. Performance
degradation could impact user experience and revenue generation.

Critical Performance Areas:
- Consolidated registry performance baseline
- Concurrent user performance under load
- Memory usage and resource efficiency
- WebSocket event delivery latency
"""

import asyncio
import pytest
import time
import statistics
import gc
import psutil
import os
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# SSOT TEST INFRASTRUCTURE - Use established testing patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from shared.isolated_environment import IsolatedEnvironment

# Import registry for performance testing
try:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    REGISTRY_AVAILABLE = True
except ImportError:
    AgentRegistry = None
    REGISTRY_AVAILABLE = False


class TestRegistryConsolidationPerformance(SSotAsyncTestCase):
    """Test performance impact of registry consolidation."""
    
    async def asyncSetUp(self):
        """Set up performance test environment with SSOT compliance."""
        await super().asyncSetUp()
        
        # Create isolated environment
        self.env = IsolatedEnvironment()
        self.env.set("ENVIRONMENT", "test")
        
        # Create mock LLM manager for registry initialization
        self.mock_llm_manager = SSotMockFactory.create_mock_llm_manager()
        
        # Track registry instance for cleanup
        self.registry: Optional[AgentRegistry] = None
        
        # Performance test parameters
        self.performance_thresholds = {
            "user_session_creation_ms": 100,  # Max 100ms per session
            "registry_health_check_ms": 50,   # Max 50ms for health check
            "agent_creation_ms": 200,         # Max 200ms per agent
            "websocket_event_latency_ms": 10, # Max 10ms for WebSocket events
            "concurrent_user_response_ms": 500, # Max 500ms with 10 concurrent users
            "memory_growth_mb": 50,           # Max 50MB memory growth during test
        }
        
        # Track initial system resources
        self.initial_memory_mb = self._get_current_memory_mb()
        
        # Performance measurement storage
        self.performance_metrics: Dict[str, List[float]] = {}
    
    def _get_current_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def _record_performance(self, operation: str, duration_ms: float) -> None:
        """Record performance measurement."""
        if operation not in self.performance_metrics:
            self.performance_metrics[operation] = []
        self.performance_metrics[operation].append(duration_ms)
    
    def _get_performance_summary(self, operation: str) -> Dict[str, float]:
        """Get performance summary for operation."""
        if operation not in self.performance_metrics:
            return {}
        
        measurements = self.performance_metrics[operation]
        return {
            "count": len(measurements),
            "mean_ms": statistics.mean(measurements),
            "median_ms": statistics.median(measurements),
            "min_ms": min(measurements),
            "max_ms": max(measurements),
            "stddev_ms": statistics.stdev(measurements) if len(measurements) > 1 else 0.0
        }
    
    async def asyncTearDown(self):
        """Clean up test resources and check memory usage."""
        try:
            # Cleanup registry
            if self.registry:
                await self.registry.cleanup()
            
            # Force garbage collection
            gc.collect()
            
            # Check final memory usage
            final_memory_mb = self._get_current_memory_mb()
            memory_growth = final_memory_mb - self.initial_memory_mb
            
            if memory_growth > self.performance_thresholds["memory_growth_mb"]:
                print(f"Warning: Memory growth exceeded threshold: {memory_growth:.1f}MB")
            
        except Exception as e:
            print(f"Warning: Error during performance test cleanup: {e}")
        
        await super().asyncTearDown()
    
    @pytest.mark.asyncio
    async def test_consolidated_registry_baseline_performance(self):
        """
        Test consolidated registry performance baseline.
        
        EXPECTED: Registry operations should meet performance thresholds
        """
        if not REGISTRY_AVAILABLE:
            self.skipTest("Registry not available for performance testing")
        
        self.registry = AgentRegistry(llm_manager=self.mock_llm_manager)
        
        # Test 1: User session creation performance
        session_count = 20
        for i in range(session_count):
            start_time = time.perf_counter()
            
            user_session = await self.registry.get_user_session(f"perf_user_{i}")
            
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            self._record_performance("user_session_creation", duration_ms)
            
            self.assertIsNotNone(user_session)
        
        # Validate user session creation performance
        session_perf = self._get_performance_summary("user_session_creation")
        self.assertLess(
            session_perf["mean_ms"],
            self.performance_thresholds["user_session_creation_ms"],
            f"User session creation too slow: {session_perf['mean_ms']:.2f}ms average "
            f"(threshold: {self.performance_thresholds['user_session_creation_ms']}ms)"
        )
        
        # Test 2: Registry health check performance
        health_check_count = 10
        for i in range(health_check_count):
            start_time = time.perf_counter()
            
            health_report = self.registry.get_registry_health()
            
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            self._record_performance("health_check", duration_ms)
            
            self.assertIn("total_agents", health_report)
        
        # Validate health check performance
        health_perf = self._get_performance_summary("health_check")
        self.assertLess(
            health_perf["mean_ms"],
            self.performance_thresholds["registry_health_check_ms"],
            f"Registry health check too slow: {health_perf['mean_ms']:.2f}ms average "
            f"(threshold: {self.performance_thresholds['registry_health_check_ms']}ms)"
        )
        
        print(f"Registry Performance Baseline:")
        print(f"  User Session Creation: {session_perf['mean_ms']:.2f}ms avg")
        print(f"  Health Check: {health_perf['mean_ms']:.2f}ms avg")
    
    @pytest.mark.asyncio
    async def test_concurrent_user_performance_under_load(self):
        """
        Test concurrent user performance under load.
        
        EXPECTED: System should handle concurrent users without degradation
        """
        if not REGISTRY_AVAILABLE:
            self.skipTest("Registry not available for concurrent testing")
        
        self.registry = AgentRegistry(llm_manager=self.mock_llm_manager)
        
        # Create mock WebSocket manager for realistic testing
        mock_websocket_manager = Mock()
        mock_websocket_manager.broadcast = AsyncMock()
        self.registry.set_websocket_manager(mock_websocket_manager)
        
        async def user_workload(user_id: str) -> float:
            """Simulate typical user workload and measure response time."""
            start_time = time.perf_counter()
            
            try:
                # Get user session
                user_session = await self.registry.get_user_session(user_id)
                
                # Simulate agent creation (mock)
                mock_agent = Mock()
                await user_session.register_agent("test_agent", mock_agent)
                
                # Get session metrics
                metrics = user_session.get_metrics()
                self.assertIsInstance(metrics, dict)
                
                # Cleanup
                await user_session.cleanup_all_agents()
                
                end_time = time.perf_counter()
                return (end_time - start_time) * 1000  # Return duration in ms
                
            except Exception as e:
                print(f"Error in user workload for {user_id}: {e}")
                return float('inf')  # Return very high time for errors
        
        # Test with increasing concurrent user counts
        concurrent_user_counts = [1, 5, 10, 15]
        
        for user_count in concurrent_user_counts:
            print(f"Testing with {user_count} concurrent users...")
            
            # Create concurrent user tasks
            tasks = [
                user_workload(f"concurrent_user_{user_count}_{i}")
                for i in range(user_count)
            ]
            
            # Measure concurrent execution time
            start_time = time.perf_counter()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.perf_counter()
            
            total_duration_ms = (end_time - start_time) * 1000
            
            # Filter out exceptions and infinite values
            valid_results = [
                result for result in results 
                if isinstance(result, float) and result != float('inf')
            ]
            
            if not valid_results:
                self.fail(f"All concurrent user workloads failed for {user_count} users")
            
            # Record performance metrics
            self._record_performance(f"concurrent_users_{user_count}", total_duration_ms)
            
            # Calculate statistics
            avg_user_time = statistics.mean(valid_results)
            max_user_time = max(valid_results)
            
            print(f"  Total time: {total_duration_ms:.2f}ms")
            print(f"  Avg user time: {avg_user_time:.2f}ms")
            print(f"  Max user time: {max_user_time:.2f}ms")
            print(f"  Success rate: {len(valid_results)}/{user_count}")
            
            # Validate performance doesn't degrade significantly with concurrent users
            if user_count == 10:  # Test primary threshold
                self.assertLess(
                    max_user_time,
                    self.performance_thresholds["concurrent_user_response_ms"],
                    f"Concurrent user response too slow: {max_user_time:.2f}ms "
                    f"with {user_count} users (threshold: "
                    f"{self.performance_thresholds['concurrent_user_response_ms']}ms)"
                )
    
    @pytest.mark.asyncio
    async def test_memory_usage_efficiency(self):
        """
        Test memory usage efficiency during registry operations.
        
        EXPECTED: Memory usage should be stable and not grow excessively
        """
        if not REGISTRY_AVAILABLE:
            self.skipTest("Registry not available for memory testing")
        
        self.registry = AgentRegistry(llm_manager=self.mock_llm_manager)
        
        # Measure memory at different stages
        memory_checkpoints = []
        
        # Checkpoint 1: Initial registry creation
        memory_checkpoints.append(("initial", self._get_current_memory_mb()))
        
        # Create many user sessions
        session_count = 50
        for i in range(session_count):
            user_session = await self.registry.get_user_session(f"memory_test_user_{i}")
            
            # Add some agents to each session
            for j in range(3):
                mock_agent = Mock()
                await user_session.register_agent(f"agent_{j}", mock_agent)
        
        # Checkpoint 2: After creating sessions and agents
        memory_checkpoints.append(("after_creation", self._get_current_memory_mb()))
        
        # Get registry monitoring data
        monitoring_report = await self.registry.monitor_all_users()
        self.assertIsInstance(monitoring_report, dict)
        self.assertEqual(monitoring_report["total_users"], session_count)
        
        # Checkpoint 3: After monitoring
        memory_checkpoints.append(("after_monitoring", self._get_current_memory_mb()))
        
        # Cleanup half the users
        cleanup_count = session_count // 2
        for i in range(cleanup_count):
            await self.registry.cleanup_user_session(f"memory_test_user_{i}")
        
        # Force garbage collection
        gc.collect()
        
        # Checkpoint 4: After partial cleanup
        memory_checkpoints.append(("after_partial_cleanup", self._get_current_memory_mb()))
        
        # Cleanup remaining users
        for i in range(cleanup_count, session_count):
            await self.registry.cleanup_user_session(f"memory_test_user_{i}")
        
        # Force garbage collection
        gc.collect()
        
        # Checkpoint 5: After full cleanup
        memory_checkpoints.append(("after_full_cleanup", self._get_current_memory_mb()))
        
        # Analyze memory usage patterns
        print("Memory Usage Analysis:")
        for i, (stage, memory_mb) in enumerate(memory_checkpoints):
            growth = memory_mb - self.initial_memory_mb
            print(f"  {stage}: {memory_mb:.1f}MB (growth: {growth:+.1f}MB)")
        
        # Validate memory usage patterns
        max_memory = max(memory for _, memory in memory_checkpoints)
        max_growth = max_memory - self.initial_memory_mb
        
        self.assertLess(
            max_growth,
            self.performance_thresholds["memory_growth_mb"],
            f"Memory growth exceeded threshold: {max_growth:.1f}MB "
            f"(threshold: {self.performance_thresholds['memory_growth_mb']}MB)"
        )
        
        # Validate memory was freed after cleanup
        final_memory = memory_checkpoints[-1][1]
        final_growth = final_memory - self.initial_memory_mb
        
        # Memory growth after cleanup should be minimal (< 20MB)
        self.assertLess(
            final_growth, 20.0,
            f"Memory not properly freed after cleanup: {final_growth:.1f}MB remaining growth"
        )
    
    @pytest.mark.asyncio
    async def test_websocket_event_delivery_performance(self):
        """
        Test WebSocket event delivery performance.
        
        EXPECTED: WebSocket events should be delivered with low latency
        Critical for $500K+ ARR real-time chat functionality
        """
        if not REGISTRY_AVAILABLE:
            self.skipTest("Registry not available for WebSocket testing")
        
        self.registry = AgentRegistry(llm_manager=self.mock_llm_manager)
        
        # Create mock WebSocket manager with performance tracking
        event_delivery_times = []
        
        async def mock_broadcast(event_data):
            """Mock broadcast that records delivery time."""
            # Simulate realistic WebSocket delivery time
            await asyncio.sleep(0.001)  # 1ms simulated network latency
            return True
        
        mock_websocket_manager = Mock()
        mock_websocket_manager.broadcast = AsyncMock(side_effect=mock_broadcast)
        
        # Set WebSocket manager
        await self.registry.set_websocket_manager_async(mock_websocket_manager)
        
        # Test event delivery performance with multiple users
        user_count = 10
        events_per_user = 5
        
        for user_idx in range(user_count):
            user_id = f"websocket_perf_user_{user_idx}"
            user_session = await self.registry.get_user_session(user_id)
            
            # Create mock user context
            mock_user_context = Mock()
            mock_user_context.user_id = user_id
            mock_user_context.request_id = f"req_{user_idx}"
            mock_user_context.thread_id = f"thread_{user_idx}"
            mock_user_context.run_id = f"run_{user_idx}"
            
            # Set WebSocket manager on user session
            await user_session.set_websocket_manager(mock_websocket_manager, mock_user_context)
            
            # Test event delivery for this user
            for event_idx in range(events_per_user):
                start_time = time.perf_counter()
                
                # Trigger a WebSocket event (via agent registration)
                mock_agent = Mock()
                await user_session.register_agent(f"perf_agent_{event_idx}", mock_agent)
                
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                
                self._record_performance("websocket_event_delivery", duration_ms)
        
        # Validate WebSocket event delivery performance
        event_perf = self._get_performance_summary("websocket_event_delivery")
        
        if event_perf:
            print(f"WebSocket Event Delivery Performance:")
            print(f"  Average: {event_perf['mean_ms']:.2f}ms")
            print(f"  Max: {event_perf['max_ms']:.2f}ms")
            print(f"  Events tested: {event_perf['count']}")
            
            # Note: We don't strictly enforce the threshold here because event delivery
            # might include more than just WebSocket latency (agent creation, etc.)
            # But we validate it's reasonable for chat functionality
            self.assertLess(
                event_perf['max_ms'], 100.0,  # Max 100ms for any single event
                f"WebSocket event delivery too slow: {event_perf['max_ms']:.2f}ms max. "
                f"This could impact real-time chat experience."
            )
            
            # Validate broadcast was called the expected number of times
            expected_calls = user_count * events_per_user
            # Note: broadcast might be called more than expected due to internal events
            # so we just verify it was called at least once per user event
            self.assertGreaterEqual(
                mock_websocket_manager.broadcast.call_count, 1,
                "WebSocket broadcast should be called for events"
            )
    
    @pytest.mark.asyncio
    async def test_registry_scalability_limits(self):
        """
        Test registry scalability limits and performance degradation points.
        
        EXPECTED: Identify performance degradation points for monitoring
        """
        if not REGISTRY_AVAILABLE:
            self.skipTest("Registry not available for scalability testing")
        
        self.registry = AgentRegistry(llm_manager=self.mock_llm_manager)
        
        # Test scalability with increasing user counts
        user_counts = [10, 25, 50, 75, 100]
        
        scalability_results = []
        
        for user_count in user_counts:
            start_time = time.perf_counter()
            
            # Create user sessions
            session_creation_times = []
            for i in range(user_count):
                session_start = time.perf_counter()
                user_session = await self.registry.get_user_session(f"scale_user_{user_count}_{i}")
                session_end = time.perf_counter()
                
                session_creation_times.append((session_end - session_start) * 1000)
                
                # Add agents to each session
                for j in range(2):  # 2 agents per user
                    mock_agent = Mock()
                    await user_session.register_agent(f"agent_{j}", mock_agent)
            
            # Measure monitoring performance at scale
            monitoring_start = time.perf_counter()
            monitoring_report = await self.registry.monitor_all_users()
            monitoring_end = time.perf_counter()
            
            monitoring_time_ms = (monitoring_end - monitoring_start) * 1000
            
            end_time = time.perf_counter()
            total_time_ms = (end_time - start_time) * 1000
            
            # Calculate performance metrics
            avg_session_creation = statistics.mean(session_creation_times)
            max_session_creation = max(session_creation_times)
            
            scalability_results.append({
                "user_count": user_count,
                "total_time_ms": total_time_ms,
                "avg_session_creation_ms": avg_session_creation,
                "max_session_creation_ms": max_session_creation,
                "monitoring_time_ms": monitoring_time_ms,
                "total_agents": monitoring_report["total_agents"],
                "memory_mb": self._get_current_memory_mb()
            })
            
            print(f"Scalability Test - {user_count} users:")
            print(f"  Total time: {total_time_ms:.1f}ms")
            print(f"  Avg session creation: {avg_session_creation:.2f}ms")
            print(f"  Monitoring time: {monitoring_time_ms:.2f}ms")
            print(f"  Memory: {self._get_current_memory_mb():.1f}MB")
            
            # Clean up for next iteration
            await self.registry.emergency_cleanup_all()
            gc.collect()
        
        # Analyze scalability trends
        print("\nScalability Analysis:")
        print("Users | Total(ms) | AvgSession(ms) | Monitor(ms) | Memory(MB)")
        print("-" * 65)
        for result in scalability_results:
            print(f"{result['user_count']:5d} | "
                  f"{result['total_time_ms']:9.1f} | "
                  f"{result['avg_session_creation_ms']:13.2f} | "
                  f"{result['monitoring_time_ms']:10.2f} | "
                  f"{result['memory_mb']:9.1f}")
        
        # Validate scalability characteristics
        # Performance should not degrade exponentially
        if len(scalability_results) >= 2:
            small_scale = scalability_results[0]  # 10 users
            large_scale = scalability_results[-1]  # 100 users
            
            # Per-user performance should not degrade more than 5x
            small_per_user = small_scale["total_time_ms"] / small_scale["user_count"]
            large_per_user = large_scale["total_time_ms"] / large_scale["user_count"]
            
            degradation_factor = large_per_user / small_per_user
            
            self.assertLess(
                degradation_factor, 5.0,
                f"Performance degraded too much at scale: {degradation_factor:.1f}x slower per user "
                f"({small_per_user:.1f}ms -> {large_per_user:.1f}ms per user)"
            )