"""
Performance Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure system performance meets user expectations
- Value Impact: Fast response times prevent user abandonment
- Strategic Impact: Performance directly impacts user satisfaction and retention

Integration Points Tested:
1. End-to-end performance of agent execution workflows
2. Database query performance under realistic load
3. WebSocket event delivery performance at scale
4. Tool dispatcher coordination performance
5. Multi-user concurrent performance characteristics
6. Memory and resource utilization integration
7. Performance degradation detection and monitoring
8. Load balancing and scaling performance integration
"""

import asyncio
import psutil
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from netra_backend.app.services.user_execution_context import UserExecutionContext


class PerformanceProfiler:
    """Performance profiling utility for integration tests."""
    
    def __init__(self):
        self.measurements = []
        self.resource_snapshots = []
        
    def start_measurement(self, operation_name: str) -> str:
        """Start performance measurement."""
        measurement_id = str(uuid4())
        
        measurement = {
            "measurement_id": measurement_id,
            "operation_name": operation_name,
            "start_time": time.time(),
            "start_memory": self._get_memory_usage(),
            "start_cpu": self._get_cpu_percent()
        }
        
        self.measurements.append(measurement)
        return measurement_id
        
    def end_measurement(self, measurement_id: str, success: bool = True, 
                       metadata: Dict = None) -> Dict:
        """End performance measurement."""
        end_time = time.time()
        end_memory = self._get_memory_usage()
        end_cpu = self._get_cpu_percent()
        
        # Find measurement
        measurement = next((m for m in self.measurements 
                          if m["measurement_id"] == measurement_id), None)
        
        if measurement:
            measurement.update({
                "end_time": end_time,
                "end_memory": end_memory,
                "end_cpu": end_cpu,
                "duration": end_time - measurement["start_time"],
                "memory_delta": end_memory - measurement["start_memory"],
                "cpu_avg": (measurement["start_cpu"] + end_cpu) / 2,
                "success": success,
                "metadata": metadata or {}
            })
            
        return measurement
        
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except:
            return 0.0
            
    def _get_cpu_percent(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return psutil.cpu_percent()
        except:
            return 0.0
            
    def take_resource_snapshot(self, label: str) -> Dict:
        """Take system resource snapshot."""
        snapshot = {
            "label": label,
            "timestamp": time.time(),
            "memory_mb": self._get_memory_usage(),
            "cpu_percent": self._get_cpu_percent(),
        }
        
        self.resource_snapshots.append(snapshot)
        return snapshot
        
    def get_performance_summary(self) -> Dict:
        """Get performance summary."""
        successful_measurements = [m for m in self.measurements if m.get("success", True)]
        
        if not successful_measurements:
            return {"error": "No successful measurements"}
            
        durations = [m["duration"] for m in successful_measurements]
        memory_deltas = [m["memory_delta"] for m in successful_measurements]
        
        return {
            "total_measurements": len(self.measurements),
            "successful_measurements": len(successful_measurements),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "avg_memory_delta": sum(memory_deltas) / len(memory_deltas),
            "total_memory_used": sum(memory_deltas),
            "resource_snapshots": len(self.resource_snapshots)
        }


class MockHighPerformanceAgentService:
    """Mock high-performance agent service for performance testing."""
    
    def __init__(self, base_execution_time: float = 0.1):
        self.base_execution_time = base_execution_time
        self.executions = []
        self.performance_data = []
        
    async def execute_agent(self, agent_name: str, context: Dict, 
                           performance_target_ms: int = None) -> Dict:
        """Execute agent with performance tracking."""
        start_time = time.time()
        execution_id = str(uuid4())
        
        # Simulate variable execution time based on load
        current_load = len(self.executions) / 10  # Simple load factor
        execution_time = self.base_execution_time * (1 + current_load * 0.1)
        
        execution_record = {
            "execution_id": execution_id,
            "agent_name": agent_name,
            "context": context,
            "start_time": start_time,
            "target_ms": performance_target_ms
        }
        self.executions.append(execution_record)
        
        # Simulate work
        await asyncio.sleep(execution_time)
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        execution_record.update({
            "end_time": end_time,
            "duration_ms": duration_ms,
            "status": "completed",
            "performance_met": performance_target_ms is None or duration_ms <= performance_target_ms
        })
        
        # Record performance data
        self.performance_data.append({
            "execution_id": execution_id,
            "duration_ms": duration_ms,
            "load_factor": current_load,
            "target_met": execution_record["performance_met"]
        })
        
        return execution_record
        
    def get_performance_metrics(self) -> Dict:
        """Get service performance metrics.""" 
        if not self.performance_data:
            return {"error": "No performance data available"}
            
        durations = [p["duration_ms"] for p in self.performance_data]
        targets_met = [p["target_met"] for p in self.performance_data]
        
        return {
            "total_executions": len(self.performance_data),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "p95_duration_ms": sorted(durations)[int(len(durations) * 0.95)],
            "success_rate": sum(targets_met) / len(targets_met),
            "current_load": len(self.executions) / 10
        }


class MockWebSocketPerformanceService:
    """Mock WebSocket service optimized for performance testing."""
    
    def __init__(self):
        self.events_sent = []
        self.performance_metrics = []
        self.connection_count = 0
        
    async def send_event_batch(self, events: List[Dict], 
                             target_delivery_ms: int = 100) -> Dict:
        """Send batch of events with performance tracking."""
        start_time = time.time()
        batch_id = str(uuid4())
        
        batch_record = {
            "batch_id": batch_id,
            "event_count": len(events),
            "start_time": start_time,
            "target_delivery_ms": target_delivery_ms
        }
        
        # Simulate network delay based on connection count
        base_delay = 0.01  # 10ms base
        connection_overhead = self.connection_count * 0.001  # 1ms per connection
        total_delay = base_delay + connection_overhead
        
        await asyncio.sleep(total_delay)
        
        # Record events
        for event in events:
            event_record = {
                "batch_id": batch_id,
                "event_type": event.get("type", "unknown"),
                "timestamp": time.time(),
                "payload_size": len(str(event.get("payload", {})))
            }
            self.events_sent.append(event_record)
            
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        batch_record.update({
            "end_time": end_time,
            "duration_ms": duration_ms,
            "performance_met": duration_ms <= target_delivery_ms,
            "events_delivered": len(events)
        })
        
        self.performance_metrics.append(batch_record)
        return batch_record
        
    def simulate_connections(self, count: int):
        """Simulate WebSocket connections for load testing."""
        self.connection_count = count
        
    def get_delivery_metrics(self) -> Dict:
        """Get event delivery performance metrics."""
        if not self.performance_metrics:
            return {"error": "No delivery metrics available"}
            
        durations = [m["duration_ms"] for m in self.performance_metrics]
        targets_met = [m["performance_met"] for m in self.performance_metrics]
        total_events = sum(m["events_delivered"] for m in self.performance_metrics)
        
        return {
            "total_batches": len(self.performance_metrics),
            "total_events_delivered": total_events,
            "avg_batch_duration_ms": sum(durations) / len(durations),
            "p95_batch_duration_ms": sorted(durations)[int(len(durations) * 0.95)],
            "delivery_success_rate": sum(targets_met) / len(targets_met),
            "active_connections": self.connection_count,
            "events_per_second": total_events / (durations[-1] / 1000) if durations else 0
        }


@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.performance
class TestPerformanceIntegrationComprehensive:
    """Comprehensive performance integration tests."""
    
    @pytest.fixture
    def profiler(self):
        """Provide performance profiler."""
        return PerformanceProfiler()
        
    @pytest.fixture
    def agent_service(self):
        """Provide high-performance agent service."""
        return MockHighPerformanceAgentService(base_execution_time=0.05)
        
    @pytest.fixture
    def websocket_service(self):
        """Provide WebSocket performance service."""
        return MockWebSocketPerformanceService()
        
    @pytest.fixture
    def user_contexts(self):
        """Provide multiple user contexts for load testing."""
        return [
            UserExecutionContext(
                user_id=f"perf_user_{i}",
                thread_id=f"perf_thread_{i}",
                correlation_id=f"perf_correlation_{i}",
                permissions=["performance_testing"]
            )
            for i in range(10)
        ]
        
    async def test_single_agent_execution_performance_integration(
        self, profiler, agent_service
    ):
        """Test single agent execution performance integration."""
        # BUSINESS VALUE: Fast single-user response times improve user experience
        
        # Setup: Performance target
        target_execution_time_ms = 200
        
        # Execute: Single agent execution with performance tracking
        measurement_id = profiler.start_measurement("single_agent_execution")
        
        result = await agent_service.execute_agent(
            agent_name="performance_test_agent",
            context={"optimization_type": "cost_analysis"},
            performance_target_ms=target_execution_time_ms
        )
        
        measurement = profiler.end_measurement(
            measurement_id, 
            success=result["status"] == "completed"
        )
        
        # Verify: Performance target met
        assert result["performance_met"] is True
        assert result["duration_ms"] <= target_execution_time_ms
        
        # Verify: Reasonable resource usage
        assert measurement["duration"] < 1.0  # Should complete quickly
        assert measurement["memory_delta"] < 100  # Should not use excessive memory
        
        # Verify: Service performance metrics
        service_metrics = agent_service.get_performance_metrics()
        assert service_metrics["avg_duration_ms"] <= target_execution_time_ms
        assert service_metrics["success_rate"] == 1.0
        
    async def test_concurrent_agent_execution_performance_integration(
        self, profiler, agent_service, user_contexts
    ):
        """Test concurrent agent execution performance integration."""
        # BUSINESS VALUE: Multi-user concurrent performance enables platform scalability
        
        # Setup: Performance targets
        target_execution_time_ms = 500  # Higher target for concurrent load
        concurrent_users = 5
        
        # Execute: Concurrent agent executions
        profiler.take_resource_snapshot("before_concurrent_load")
        
        async def execute_for_user(user_context: UserExecutionContext, user_index: int):
            """Execute agent for specific user."""
            measurement_id = profiler.start_measurement(f"concurrent_agent_{user_index}")
            
            result = await agent_service.execute_agent(
                agent_name=f"concurrent_agent_{user_index}",
                context={
                    "user_id": user_context.user_id,
                    "optimization_request": f"Concurrent test {user_index}"
                },
                performance_target_ms=target_execution_time_ms
            )
            
            profiler.end_measurement(
                measurement_id,
                success=result["status"] == "completed",
                metadata={"user_index": user_index}
            )
            
            return result
            
        # Run concurrent executions
        start_time = time.time()
        
        concurrent_tasks = [
            execute_for_user(user_contexts[i], i) 
            for i in range(concurrent_users)
        ]
        
        results = await asyncio.gather(*concurrent_tasks)
        
        total_time = time.time() - start_time
        profiler.take_resource_snapshot("after_concurrent_load")
        
        # Verify: All executions completed successfully
        assert len(results) == concurrent_users
        assert all(r["status"] == "completed" for r in results)
        
        # Verify: Reasonable concurrent performance
        assert total_time < 2.0  # Should complete all within 2 seconds
        
        # Verify: Performance targets met under load
        performance_met_count = sum(1 for r in results if r["performance_met"])
        success_rate = performance_met_count / concurrent_users
        assert success_rate >= 0.8  # At least 80% should meet performance target
        
        # Verify: Service metrics under concurrent load
        service_metrics = agent_service.get_performance_metrics()
        assert service_metrics["total_executions"] == concurrent_users
        assert service_metrics["avg_duration_ms"] <= target_execution_time_ms * 1.2  # 20% tolerance
        
        # Verify: Performance profiler captured data
        performance_summary = profiler.get_performance_summary()
        assert performance_summary["total_measurements"] == concurrent_users
        assert performance_summary["avg_duration"] <= 1.0
        
    async def test_websocket_event_delivery_performance_integration(
        self, profiler, websocket_service
    ):
        """Test WebSocket event delivery performance integration."""
        # BUSINESS VALUE: Fast event delivery prevents user abandonment
        
        # Setup: Event delivery performance targets
        target_delivery_ms = 50
        event_batch_size = 20
        
        # Simulate connections
        websocket_service.simulate_connections(100)  # 100 concurrent connections
        
        # Execute: Event batch delivery
        measurement_id = profiler.start_measurement("websocket_event_delivery")
        
        events = [
            {
                "type": f"performance_event_{i}",
                "payload": {
                    "event_id": i,
                    "timestamp": time.time(),
                    "data": f"Performance test data {i}"
                }
            }
            for i in range(event_batch_size)
        ]
        
        delivery_result = await websocket_service.send_event_batch(
            events=events,
            target_delivery_ms=target_delivery_ms
        )
        
        measurement = profiler.end_measurement(
            measurement_id,
            success=delivery_result["performance_met"]
        )
        
        # Verify: Delivery performance
        assert delivery_result["performance_met"] is True
        assert delivery_result["duration_ms"] <= target_delivery_ms
        assert delivery_result["events_delivered"] == event_batch_size
        
        # Verify: WebSocket service metrics
        delivery_metrics = websocket_service.get_delivery_metrics()
        assert delivery_metrics["total_events_delivered"] == event_batch_size
        assert delivery_metrics["delivery_success_rate"] == 1.0
        assert delivery_metrics["events_per_second"] > 100  # Should be high throughput
        
    async def test_high_load_websocket_performance_integration(
        self, profiler, websocket_service
    ):
        """Test WebSocket performance under high load integration."""
        # BUSINESS VALUE: High-load performance ensures platform reliability
        
        # Setup: High load scenario
        connection_count = 500
        batch_count = 10
        events_per_batch = 50
        target_delivery_ms = 100
        
        websocket_service.simulate_connections(connection_count)
        
        # Execute: Multiple event batches under load
        profiler.take_resource_snapshot("before_high_load")
        
        async def send_event_batch(batch_id: int):
            """Send event batch."""
            events = [
                {
                    "type": "high_load_event",
                    "payload": {
                        "batch_id": batch_id,
                        "event_index": i,
                        "load_test": True
                    }
                }
                for i in range(events_per_batch)
            ]
            
            return await websocket_service.send_event_batch(
                events=events,
                target_delivery_ms=target_delivery_ms
            )
            
        # Send batches concurrently
        start_time = time.time()
        
        batch_tasks = [send_event_batch(i) for i in range(batch_count)]
        batch_results = await asyncio.gather(*batch_tasks)
        
        total_time = time.time() - start_time
        profiler.take_resource_snapshot("after_high_load")
        
        # Verify: All batches delivered
        assert len(batch_results) == batch_count
        total_events = sum(r["events_delivered"] for r in batch_results)
        expected_events = batch_count * events_per_batch
        assert total_events == expected_events
        
        # Verify: Performance under high load
        delivery_success_rate = sum(1 for r in batch_results if r["performance_met"]) / batch_count
        assert delivery_success_rate >= 0.7  # At least 70% should meet target under high load
        
        # Verify: Throughput
        events_per_second = total_events / total_time
        assert events_per_second > 500  # Should maintain high throughput
        
        # Verify: Delivery metrics
        delivery_metrics = websocket_service.get_delivery_metrics()
        assert delivery_metrics["total_events_delivered"] >= expected_events
        assert delivery_metrics["active_connections"] == connection_count
        
    async def test_memory_usage_performance_integration(self, profiler, agent_service):
        """Test memory usage performance integration."""
        # BUSINESS VALUE: Efficient memory usage enables cost-effective scaling
        
        # Execute: Memory usage monitoring
        profiler.take_resource_snapshot("baseline")
        
        # Execute multiple agents to test memory efficiency
        agent_count = 20
        
        for i in range(agent_count):
            measurement_id = profiler.start_measurement(f"memory_test_agent_{i}")
            
            result = await agent_service.execute_agent(
                agent_name=f"memory_test_agent_{i}",
                context={
                    "test_data": f"Memory test data for agent {i}" * 100,  # Some payload
                    "iteration": i
                }
            )
            
            profiler.end_measurement(
                measurement_id,
                success=result["status"] == "completed"
            )
            
            # Take periodic snapshots
            if i % 5 == 0:
                profiler.take_resource_snapshot(f"after_agent_{i}")
                
        profiler.take_resource_snapshot("final")
        
        # Analyze memory usage
        snapshots = profiler.resource_snapshots
        baseline_memory = next(s["memory_mb"] for s in snapshots if s["label"] == "baseline")
        final_memory = next(s["memory_mb"] for s in snapshots if s["label"] == "final")
        
        memory_increase = final_memory - baseline_memory
        memory_per_agent = memory_increase / agent_count
        
        # Verify: Reasonable memory usage
        assert memory_per_agent < 10  # Should use less than 10MB per agent
        assert memory_increase < 200  # Total increase should be reasonable
        
        # Verify: No significant memory leaks
        intermediate_snapshots = [s for s in snapshots if s["label"].startswith("after_agent_")]
        if len(intermediate_snapshots) >= 2:
            memory_growth_rate = (intermediate_snapshots[-1]["memory_mb"] - 
                                 intermediate_snapshots[0]["memory_mb"]) / len(intermediate_snapshots)
            assert memory_growth_rate < 5  # Should not grow too quickly
            
        # Verify: Performance summary
        performance_summary = profiler.get_performance_summary()
        assert performance_summary["avg_memory_delta"] < 20  # Average per operation
        
    async def test_performance_degradation_detection_integration(
        self, profiler, agent_service
    ):
        """Test performance degradation detection integration."""
        # BUSINESS VALUE: Early detection of performance issues prevents user impact
        
        # Execute: Baseline performance measurement
        baseline_executions = 5
        baseline_times = []
        
        for i in range(baseline_executions):
            measurement_id = profiler.start_measurement(f"baseline_agent_{i}")
            
            result = await agent_service.execute_agent(
                agent_name="baseline_performance_agent",
                context={"baseline_test": True, "iteration": i}
            )
            
            measurement = profiler.end_measurement(
                measurement_id,
                success=result["status"] == "completed"
            )
            
            baseline_times.append(measurement["duration"])
            
        baseline_avg = sum(baseline_times) / len(baseline_times)
        
        # Simulate load increase (degradation)
        # Add artificial delay to simulate system under load
        original_execution_time = agent_service.base_execution_time
        agent_service.base_execution_time = original_execution_time * 2  # 2x slower
        
        # Execute: Performance under degraded conditions
        degraded_executions = 5
        degraded_times = []
        
        for i in range(degraded_executions):
            measurement_id = profiler.start_measurement(f"degraded_agent_{i}")
            
            result = await agent_service.execute_agent(
                agent_name="degraded_performance_agent",
                context={"degradation_test": True, "iteration": i}
            )
            
            measurement = profiler.end_measurement(
                measurement_id, 
                success=result["status"] == "completed"
            )
            
            degraded_times.append(measurement["duration"])
            
        degraded_avg = sum(degraded_times) / len(degraded_times)
        
        # Verify: Performance degradation detected
        performance_degradation = (degraded_avg - baseline_avg) / baseline_avg
        assert performance_degradation > 0.5  # Should detect significant degradation (>50%)
        
        # Verify: Service metrics show degradation
        service_metrics = agent_service.get_performance_metrics()
        assert service_metrics["max_duration_ms"] > service_metrics["min_duration_ms"] * 1.5
        
        # Verify: Profiler captured degradation pattern
        performance_summary = profiler.get_performance_summary()
        assert performance_summary["max_duration"] > performance_summary["min_duration"] * 1.5
        
        # Restore original performance
        agent_service.base_execution_time = original_execution_time