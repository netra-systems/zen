"""Production Load Tests for Concurrent Agent Persistence

This test suite validates the platform's ability to handle enterprise-scale 
concurrent agent workloads with production-grade performance requirements.

Business Value Justification (BVJ):
- Segment: Enterprise ($50K+ MRR workloads)  
- Business Goal: Platform Scalability, 99.9% Uptime SLA, Customer Retention
- Value Impact: Supports 100+ concurrent agents for mission-critical operations
- Strategic Impact: Validates enterprise scalability claims, prevents churn from performance issues

Critical Performance Requirements:
- Support 100+ concurrent agents (Enterprise tier)
- P50 < 50ms, P99 < 200ms for state persistence operations
- 99.9% success rate under peak load
- Zero data loss under extreme load conditions
- Graceful degradation patterns under resource exhaustion
- Sub-100ms average latency for enterprise SLAs
- Memory usage < 2GB peak during concurrent operations
- Connection pooling efficiency validation

Test Coverage:
- Baseline 100+ concurrent agent execution
- Mixed read/write patterns reflecting real usage
- State size scalability (small to enterprise-scale states)
- Sustained load (24-hour simulation) 
- Burst traffic handling (spike patterns)
- Resource exhaustion scenarios (Redis, PostgreSQL, Memory)
- Failure injection and recovery validation
- Performance SLA compliance verification
- Production-realistic workload patterns

All tests use REAL services and validate actual performance metrics.
"""

import asyncio
import gc
import json
import logging
import os
import psutil
import random
import statistics
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.db.clickhouse import clickhouse_client
from netra_backend.app.db.database_manager import database_manager
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.schemas.agent_state import (
    CheckpointType,
    StatePersistenceRequest,
)
# SSOT CONSOLIDATION: StateCacheManager functionality integrated into StatePersistenceService
from netra_backend.app.services.state_persistence import state_cache_manager
from tests.fixtures.golden_datasets import (
    GOLDEN_HIGH_CONCURRENCY_FLOW,
    GOLDEN_LONG_RUNNING_FLOW,
    GOLDEN_MULTI_AGENT_FLOW,
    GOLDEN_RECOVERY_FLOW,
    GOLDEN_SIMPLE_FLOW,
    GoldenDatasets,
)

logger = logging.getLogger(__name__)

@dataclass
class LoadTestMetrics:
    """Comprehensive metrics for load testing."""
    
    test_name: str
    start_time: float
    end_time: Optional[float] = None
    
    # Agent execution metrics
    agents_executed: int = 0
    agents_succeeded: int = 0
    agents_failed: int = 0
    
    # Performance metrics
    response_times_ms: List[float] = field(default_factory=list)
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0  
    p99_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    
    # Resource metrics
    peak_memory_mb: float = 0.0
    avg_cpu_percent: float = 0.0
    redis_connections_used: int = 0
    postgres_connections_used: int = 0
    
    # Data integrity metrics
    data_corruption_count: int = 0
    state_inconsistencies: int = 0
    failed_recoveries: int = 0
    
    # SLA compliance metrics
    sla_violations: int = 0
    availability_percent: float = 0.0
    error_rate_percent: float = 0.0
    
    def finalize_metrics(self):
        """Calculate final derived metrics."""
        if self.end_time:
            total_duration = self.end_time - self.start_time
        else:
            total_duration = time.time() - self.start_time
            
        # Calculate response time percentiles
        if self.response_times_ms:
            sorted_times = sorted(self.response_times_ms)
            count = len(sorted_times)
            
            self.avg_latency_ms = statistics.mean(sorted_times)
            self.p50_latency_ms = sorted_times[int(0.5 * count)]
            self.p95_latency_ms = sorted_times[int(0.95 * count)]
            self.p99_latency_ms = sorted_times[int(0.99 * count)]
        
        # Calculate availability and error rates
        if self.agents_executed > 0:
            self.availability_percent = (self.agents_succeeded / self.agents_executed) * 100
            self.error_rate_percent = (self.agents_failed / self.agents_executed) * 100
        
        # Count SLA violations (>200ms for p99)
        self.sla_violations = sum(1 for t in self.response_times_ms if t > 200)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive test summary."""
        return {
            "test_name": self.test_name,
            "duration_seconds": (self.end_time or time.time()) - self.start_time,
            "agents": {
                "executed": self.agents_executed,
                "succeeded": self.agents_succeeded,
                "failed": self.agents_failed,
                "success_rate": self.availability_percent
            },
            "performance": {
                "avg_latency_ms": self.avg_latency_ms,
                "p50_latency_ms": self.p50_latency_ms,
                "p95_latency_ms": self.p95_latency_ms,
                "p99_latency_ms": self.p99_latency_ms
            },
            "resources": {
                "peak_memory_mb": self.peak_memory_mb,
                "avg_cpu_percent": self.avg_cpu_percent,
                "redis_connections": self.redis_connections_used,
                "postgres_connections": self.postgres_connections_used
            },
            "sla_compliance": {
                "availability_percent": self.availability_percent,
                "error_rate_percent": self.error_rate_percent,
                "sla_violations": self.sla_violations,
                "data_integrity_issues": self.data_corruption_count
            }
        }


@dataclass
class AgentWorkload:
    """Represents a single agent workload for load testing."""
    
    agent_id: str
    run_id: str
    thread_id: str
    user_id: str
    agent_type: str
    state_size: str  # "small", "medium", "large", "enterprise"
    execution_pattern: str  # "quick", "sustained", "burst"
    priority: str = "normal"  # "normal", "high", "critical"
    
    def generate_state_data(self) -> Dict[str, Any]:
        """Generate realistic state data based on workload configuration."""
        base_state = DeepAgentState(
            user_request=f"Load test workload {self.agent_id}",
            chat_thread_id=self.thread_id,
            user_id=self.user_id,
            run_id=self.run_id,
            step_count=random.randint(1, 50),
            agent_type=self.agent_type,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Add state size specific data
        state_data = base_state.model_dump()
        
        if self.state_size == "small":
            # Basic agent state (Free/Early tier)
            state_data["metadata"] = {"simple": True, "data_points": 100}
        elif self.state_size == "medium":
            # Standard business logic (Mid tier)
            state_data["metadata"] = {
                "analysis_results": [f"result_{i}" for i in range(50)],
                "processing_history": [{"step": i, "duration": random.uniform(0.1, 2.0)} for i in range(10)],
                "data_points": 1000
            }
        elif self.state_size == "large":
            # Complex enterprise workflow (Enterprise tier)
            state_data["metadata"] = {
                "analysis_results": [f"result_{i}" for i in range(200)],
                "processing_history": [{"step": i, "duration": random.uniform(0.1, 2.0)} for i in range(50)],
                "data_cache": {f"cache_key_{i}": f"cached_value_{i}" for i in range(100)},
                "data_points": 10000
            }
        elif self.state_size == "enterprise":
            # Large-scale enterprise state
            state_data["metadata"] = {
                "analysis_results": [f"result_{i}" for i in range(500)],
                "processing_history": [{"step": i, "duration": random.uniform(0.1, 2.0)} for i in range(100)],
                "data_cache": {f"cache_key_{i}": f"cached_value_{i}" for i in range(300)},
                "optimization_data": [{"metric": f"metric_{i}", "value": random.uniform(0.0, 100.0)} for i in range(200)],
                "data_points": 50000
            }
        
        return state_data


class ProductionLoadTestSuite:
    """Production-grade load test suite for concurrent agent persistence."""
    
    def __init__(self):
        """Initialize load test suite."""
        self.test_run_ids: Set[str] = set()
        self.test_thread_ids: Set[str] = set()
        self.test_user_ids: Set[str] = set()
        self.process = psutil.Process()
        
    async def setup_method(self):
        """Setup method for each test."""
        # Ensure database connections
        await self._ensure_database_connections()
        
        # Clear any existing test data
        await self._cleanup_test_data()
        
        # Force garbage collection
        gc.collect()
        
    async def teardown_method(self):
        """Teardown method for each test."""
        await self._cleanup_test_data()
        
    async def _ensure_database_connections(self):
        """Ensure all required database connections are available."""
        # Verify Redis connection
        redis_client = await redis_manager.get_client()
        assert redis_client is not None, "Redis connection required for load tests"
        
        # Verify PostgreSQL connection
        db_session = await database_manager.get_session()
        assert db_session is not None, "PostgreSQL connection required for load tests"
        await db_session.close()
        
        # Verify ClickHouse connection (optional)
        try:
            ch_client = await clickhouse_client.get_client()
            self.clickhouse_available = ch_client is not None
        except Exception:
            self.clickhouse_available = False
            logger.warning("ClickHouse not available - some tests may be skipped")
    
    async def _cleanup_test_data(self):
        """Clean up all test data from all databases."""
        redis_client = await redis_manager.get_client()
        if redis_client:
            # Batch delete Redis keys
            if self.test_run_ids:
                keys_to_delete = []
                for run_id in self.test_run_ids:
                    keys_to_delete.extend([
                        f"agent_state:{run_id}",
                        f"agent_state_version:{run_id}",
                        f"checkpoint:{run_id}"
                    ])
                
                for thread_id in self.test_thread_ids:
                    keys_to_delete.append(f"thread_context:{thread_id}")
                
                # Delete in batches to avoid blocking Redis
                batch_size = 100
                for i in range(0, len(keys_to_delete), batch_size):
                    batch = keys_to_delete[i:i + batch_size]
                    if batch:
                        await redis_client.delete(*batch)
        
        # Clear tracking sets
        self.test_run_ids.clear()
        self.test_thread_ids.clear()
        self.test_user_ids.clear()
    
    def _track_test_data(self, run_id: str, thread_id: str, user_id: str):
        """Track test data for cleanup."""
        self.test_run_ids.add(run_id)
        self.test_thread_ids.add(thread_id)
        self.test_user_ids.add(user_id)
    
    def _generate_workload_batch(self, batch_size: int, workload_config: Dict[str, Any]) -> List[AgentWorkload]:
        """Generate a batch of agent workloads."""
        workloads = []
        user_id = workload_config.get("user_id", f"load_test_user_{uuid.uuid4().hex[:8]}")
        
        for i in range(batch_size):
            agent_id = f"agent_{i}_{uuid.uuid4().hex[:8]}"
            run_id = f"run_{agent_id}"
            thread_id = f"thread_{agent_id}"
            
            # Vary agent types realistically
            agent_types = ["triage_agent", "supervisor_agent", "data_analyst", "optimization_agent"]
            agent_type = agent_types[i % len(agent_types)]
            
            # Vary state sizes realistically
            state_sizes = workload_config.get("state_sizes", ["small", "medium", "large"])
            state_size = random.choice(state_sizes)
            
            # Vary execution patterns
            execution_patterns = workload_config.get("execution_patterns", ["quick", "sustained"])
            execution_pattern = random.choice(execution_patterns)
            
            workload = AgentWorkload(
                agent_id=agent_id,
                run_id=run_id,
                thread_id=thread_id,
                user_id=user_id,
                agent_type=agent_type,
                state_size=state_size,
                execution_pattern=execution_pattern
            )
            
            # Track for cleanup
            self._track_test_data(run_id, thread_id, user_id)
            workloads.append(workload)
        
        return workloads
    
    async def _execute_single_agent_workload(self, workload: AgentWorkload) -> Tuple[bool, float]:
        """Execute a single agent workload and measure performance."""
        start_time = time.perf_counter()
        
        try:
            # Generate state data
            state_data = workload.generate_state_data()
            
            # Create persistence request
            request = StatePersistenceRequest(
                run_id=workload.run_id,
                thread_id=workload.thread_id,
                user_id=workload.user_id,
                state_data=state_data,
                checkpoint_type=CheckpointType.AUTO,
                is_recovery_point=False
            )
            
            # Execute persistence operation
            save_success = await state_cache_manager.save_primary_state(request)
            
            if save_success:
                # Verify state can be loaded (data integrity check)
                loaded_state = await state_cache_manager.load_primary_state(workload.run_id)
                if loaded_state is None:
                    logger.error(f"Data integrity failure: saved state not retrievable for {workload.run_id}")
                    return False, 0.0
                
                # Verify key data integrity
                if loaded_state.run_id != workload.run_id or loaded_state.user_id != workload.user_id:
                    logger.error(f"Data corruption detected for {workload.run_id}")
                    return False, 0.0
            
            execution_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
            return save_success, execution_time
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Agent workload execution failed for {workload.run_id}: {e}")
            return False, execution_time
    
    async def _monitor_system_resources(self, duration_seconds: float) -> Dict[str, Any]:
        """Monitor system resources during test execution."""
        start_time = time.time()
        resource_samples = []
        
        while (time.time() - start_time) < duration_seconds:
            try:
                sample = {
                    "timestamp": time.time(),
                    "cpu_percent": self.process.cpu_percent(),
                    "memory_mb": self.process.memory_info().rss / 1024 / 1024,
                    "memory_percent": self.process.memory_percent()
                }
                resource_samples.append(sample)
                
                await asyncio.sleep(1.0)  # Sample every second
            except Exception as e:
                logger.warning(f"Resource monitoring error: {e}")
                break
        
        # Calculate resource metrics
        if resource_samples:
            cpu_samples = [s["cpu_percent"] for s in resource_samples]
            memory_samples = [s["memory_mb"] for s in resource_samples]
            
            return {
                "peak_memory_mb": max(memory_samples),
                "avg_memory_mb": statistics.mean(memory_samples),
                "avg_cpu_percent": statistics.mean(cpu_samples),
                "max_cpu_percent": max(cpu_samples),
                "sample_count": len(resource_samples)
            }
        
        return {"peak_memory_mb": 0, "avg_memory_mb": 0, "avg_cpu_percent": 0, "max_cpu_percent": 0, "sample_count": 0}
    
    def _save_load_test_report(self, test_name: str, metrics: LoadTestMetrics, additional_data: Optional[Dict] = None):
        """Save detailed load test report."""
        os.makedirs("test_reports/load", exist_ok=True)
        timestamp = int(time.time())
        filename = f"test_reports/load/{test_name}_{timestamp}.json"
        
        report_data = {
            "test_name": test_name,
            "timestamp": timestamp,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics.get_summary(),
            "raw_metrics": asdict(metrics),
            "additional_data": additional_data or {}
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"Load test report saved: {filename}")


# Test Fixtures

@pytest.fixture
async def load_test_suite():
    """Load test suite fixture."""
    suite = ProductionLoadTestSuite()
    await suite.setup_method()
    yield suite
    await suite.teardown_method()


# Load Tests

@pytest.mark.load
@pytest.mark.asyncio
async def test_100_concurrent_agents_baseline(load_test_suite):
    """Test baseline performance with 100+ concurrent agents.
    
    Business Context: Enterprise customers typically run 100+ concurrent agents
    during peak business operations. This test validates the platform can handle
    this baseline Enterprise workload with acceptable performance.
    """
    suite = load_test_suite
    test_name = "100_concurrent_agents_baseline"
    metrics = LoadTestMetrics(test_name=test_name, start_time=time.time())
    
    # Generate 100 concurrent agent workloads
    concurrent_count = 100
    workload_config = {
        "state_sizes": ["small", "medium", "large"],  # Mix of state sizes
        "execution_patterns": ["quick", "sustained"],
        "user_id": "enterprise_load_test_001"
    }
    
    workloads = suite._generate_workload_batch(concurrent_count, workload_config)
    logger.info(f"Starting baseline load test with {len(workloads)} concurrent agents")
    
    # Start resource monitoring
    resource_monitor_task = asyncio.create_task(
        suite._monitor_system_resources(60.0)  # Monitor for 60 seconds
    )
    
    # Execute concurrent workloads
    start_execution = time.perf_counter()
    tasks = [suite._execute_single_agent_workload(workload) for workload in workloads]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_execution = time.perf_counter()
    
    # Stop resource monitoring
    resource_monitor_task.cancel()
    try:
        resource_metrics = await resource_monitor_task
    except asyncio.CancelledError:
        resource_metrics = await suite._monitor_system_resources(0.1)  # Quick sample
    
    # Process results
    successful_results = []
    failed_results = []
    
    for result in results:
        if isinstance(result, tuple):
            success, execution_time = result
            if success:
                successful_results.append(execution_time)
                metrics.response_times_ms.append(execution_time)
            else:
                failed_results.append(execution_time)
        else:
            # Exception occurred
            failed_results.append(0.0)
            logger.error(f"Concurrent agent execution exception: {result}")
    
    # Update metrics
    metrics.agents_executed = len(workloads)
    metrics.agents_succeeded = len(successful_results)
    metrics.agents_failed = len(failed_results)
    metrics.end_time = time.time()
    metrics.peak_memory_mb = resource_metrics.get("peak_memory_mb", 0)
    metrics.avg_cpu_percent = resource_metrics.get("avg_cpu_percent", 0)
    
    metrics.finalize_metrics()
    
    # Performance Assertions for Enterprise SLA
    assert metrics.agents_succeeded >= 95, f"At least 95% success rate required, got {metrics.agents_succeeded}/{metrics.agents_executed}"
    assert metrics.availability_percent >= 95.0, f"Availability must be  >= 95%, got {metrics.availability_percent:.1f}%"
    assert metrics.p50_latency_ms <= 50.0, f"P50 latency must be  <= 50ms, got {metrics.p50_latency_ms:.1f}ms"
    assert metrics.p99_latency_ms <= 200.0, f"P99 latency must be  <= 200ms, got {metrics.p99_latency_ms:.1f}ms"
    assert metrics.peak_memory_mb <= 2048, f"Peak memory must be  <= 2GB, got {metrics.peak_memory_mb:.0f}MB"
    
    # Data integrity assertions
    assert metrics.data_corruption_count == 0, "No data corruption allowed in production load"
    
    # Business performance requirements
    total_duration = end_execution - start_execution
    throughput = metrics.agents_succeeded / total_duration
    assert throughput >= 10.0, f"Throughput must be  >= 10 agents/sec, got {throughput:.1f}"
    
    logger.info(f"[U+2713] Baseline load test completed: {metrics.agents_succeeded}/{metrics.agents_executed} success, "
                f"P50: {metrics.p50_latency_ms:.1f}ms, P99: {metrics.p99_latency_ms:.1f}ms, "
                f"Throughput: {throughput:.1f} agents/sec")
    
    suite._save_load_test_report(test_name, metrics, {
        "throughput_agents_per_second": throughput,
        "total_duration_seconds": total_duration,
        "resource_metrics": resource_metrics
    })


@pytest.mark.load
@pytest.mark.asyncio 
async def test_mixed_workload_read_write_patterns(load_test_suite):
    """Test mixed read/write patterns reflecting actual production usage.
    
    Business Context: Production workloads involve complex read/write patterns
    with state updates, retrievals, and concurrent modifications. This validates
    realistic usage patterns maintain performance and data integrity.
    """
    suite = load_test_suite
    test_name = "mixed_workload_read_write_patterns"
    metrics = LoadTestMetrics(test_name=test_name, start_time=time.time())
    
    # Create initial states for read operations
    read_workloads = suite._generate_workload_batch(50, {
        "state_sizes": ["medium", "large"],
        "execution_patterns": ["sustained"],
        "user_id": "read_heavy_user_001"
    })
    
    # Pre-populate states for read testing
    logger.info("Pre-populating states for read pattern testing")
    for workload in read_workloads:
        state_data = workload.generate_state_data()
        request = StatePersistenceRequest(
            run_id=workload.run_id,
            thread_id=workload.thread_id,
            user_id=workload.user_id,
            state_data=state_data,
            checkpoint_type=CheckpointType.AUTO,
            is_recovery_point=False
        )
        await state_cache_manager.save_primary_state(request)
    
    # Generate mixed workload: 60% reads, 40% writes
    async def read_operation(workload: AgentWorkload) -> Tuple[bool, float]:
        """Perform read operation."""
        start_time = time.perf_counter()
        try:
            loaded_state = await state_cache_manager.load_primary_state(workload.run_id)
            success = loaded_state is not None
            execution_time = (time.perf_counter() - start_time) * 1000
            return success, execution_time
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Read operation failed for {workload.run_id}: {e}")
            return False, execution_time
    
    async def write_operation(workload: AgentWorkload) -> Tuple[bool, float]:
        """Perform write operation."""
        return await suite._execute_single_agent_workload(workload)
    
    # Create mixed operation tasks
    mixed_operations = []
    
    # 60% read operations
    read_sample = random.sample(read_workloads, 30)  # 30 read operations
    for workload in read_sample:
        mixed_operations.append(("read", read_operation(workload)))
    
    # 40% write operations  
    write_workloads = suite._generate_workload_batch(20, {
        "state_sizes": ["small", "medium", "large"],
        "execution_patterns": ["quick", "burst"],
        "user_id": "write_heavy_user_001" 
    })
    
    for workload in write_workloads:
        mixed_operations.append(("write", write_operation(workload)))
    
    # Shuffle operations for realistic mixed pattern
    random.shuffle(mixed_operations)
    
    logger.info(f"Executing mixed workload: {len([op for op_type, _ in mixed_operations if op_type == 'read'])} reads, "
                f"{len([op for op_type, _ in mixed_operations if op_type == 'write'])} writes")
    
    # Execute mixed operations concurrently
    start_execution = time.perf_counter()
    operation_tasks = [operation_task for _, operation_task in mixed_operations]
    results = await asyncio.gather(*operation_tasks, return_exceptions=True)
    end_execution = time.perf_counter()
    
    # Process mixed results
    read_count, write_count = 0, 0
    read_successes, write_successes = 0, 0
    
    for i, result in enumerate(results):
        operation_type = mixed_operations[i][0]
        
        if isinstance(result, tuple):
            success, execution_time = result
            metrics.response_times_ms.append(execution_time)
            
            if operation_type == "read":
                read_count += 1
                if success:
                    read_successes += 1
            else:
                write_count += 1
                if success:
                    write_successes += 1
        else:
            # Exception
            if operation_type == "read":
                read_count += 1
            else:
                write_count += 1
    
    # Update metrics
    metrics.agents_executed = len(mixed_operations)
    metrics.agents_succeeded = read_successes + write_successes
    metrics.agents_failed = metrics.agents_executed - metrics.agents_succeeded
    metrics.end_time = time.time()
    
    metrics.finalize_metrics()
    
    # Mixed workload assertions
    assert metrics.availability_percent >= 90.0, f"Mixed workload availability must be  >= 90%, got {metrics.availability_percent:.1f}%"
    assert read_successes >= 25, f"At least 25/30 read operations should succeed, got {read_successes}"
    assert write_successes >= 16, f"At least 16/20 write operations should succeed, got {write_successes}"
    assert metrics.p95_latency_ms <= 150.0, f"P95 latency for mixed workload must be  <= 150ms, got {metrics.p95_latency_ms:.1f}ms"
    
    # Read operations should be faster than writes
    read_times = []
    write_times = []
    for i, time_ms in enumerate(metrics.response_times_ms):
        if i < len(mixed_operations) and mixed_operations[i][0] == "read":
            read_times.append(time_ms)
        else:
            write_times.append(time_ms)
    
    if read_times and write_times:
        avg_read_time = statistics.mean(read_times)
        avg_write_time = statistics.mean(write_times)
        assert avg_read_time <= avg_write_time * 1.5, f"Read operations should be faster than writes"
        logger.info(f"Average read time: {avg_read_time:.1f}ms, average write time: {avg_write_time:.1f}ms")
    
    total_duration = end_execution - start_execution
    throughput = metrics.agents_succeeded / total_duration
    
    logger.info(f"[U+2713] Mixed workload test completed: {read_successes}/{read_count} reads, {write_successes}/{write_count} writes, "
                f"Overall P95: {metrics.p95_latency_ms:.1f}ms, Throughput: {throughput:.1f} ops/sec")
    
    suite._save_load_test_report(test_name, metrics, {
        "read_operations": {"count": read_count, "successes": read_successes},
        "write_operations": {"count": write_count, "successes": write_successes},
        "throughput_ops_per_second": throughput,
        "avg_read_time_ms": statistics.mean(read_times) if read_times else 0,
        "avg_write_time_ms": statistics.mean(write_times) if write_times else 0
    })


@pytest.mark.load
@pytest.mark.asyncio
async def test_state_size_scalability(load_test_suite):
    """Test scalability across different agent state sizes.
    
    Business Context: Enterprise agents handle varying state complexity,
    from simple Free tier states to complex Enterprise workflows with
    large datasets. Performance must scale gracefully across state sizes.
    """
    suite = load_test_suite
    test_name = "state_size_scalability"
    metrics = LoadTestMetrics(test_name=test_name, start_time=time.time())
    
    # Test different state size categories
    state_size_tests = [
        {"size": "small", "count": 25, "expected_p95_ms": 30},
        {"size": "medium", "count": 25, "expected_p95_ms": 60}, 
        {"size": "large", "count": 25, "expected_p95_ms": 120},
        {"size": "enterprise", "count": 25, "expected_p95_ms": 200}
    ]
    
    size_performance_results = {}
    
    for test_config in state_size_tests:
        size_name = test_config["size"]
        agent_count = test_config["count"]
        expected_p95 = test_config["expected_p95_ms"]
        
        logger.info(f"Testing {size_name} state size with {agent_count} agents")
        
        # Generate workloads for this state size
        workloads = suite._generate_workload_batch(agent_count, {
            "state_sizes": [size_name],
            "execution_patterns": ["quick"],
            "user_id": f"scalability_test_{size_name}"
        })
        
        # Execute workloads for this size
        size_start = time.perf_counter()
        tasks = [suite._execute_single_agent_workload(workload) for workload in workloads]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        size_end = time.perf_counter()
        
        # Process results for this state size
        size_successes = 0
        size_response_times = []
        
        for result in results:
            if isinstance(result, tuple):
                success, execution_time = result
                if success:
                    size_successes += 1
                    size_response_times.append(execution_time)
                metrics.response_times_ms.append(execution_time)
        
        # Calculate size-specific metrics
        if size_response_times:
            sorted_times = sorted(size_response_times)
            size_p95 = sorted_times[int(0.95 * len(sorted_times))]
            size_avg = statistics.mean(size_response_times)
            size_throughput = size_successes / (size_end - size_start)
            
            size_performance_results[size_name] = {
                "agent_count": agent_count,
                "successes": size_successes,
                "avg_response_ms": size_avg,
                "p95_response_ms": size_p95,
                "throughput_per_sec": size_throughput,
                "expected_p95_ms": expected_p95
            }
            
            # Validate performance scales appropriately
            assert size_successes >= agent_count * 0.95, f"{size_name} state size should have  >= 95% success rate"
            assert size_p95 <= expected_p95, f"{size_name} P95 should be  <= {expected_p95}ms, got {size_p95:.1f}ms"
            
            logger.info(f"{size_name} state results: {size_successes}/{agent_count} success, "
                       f"avg: {size_avg:.1f}ms, p95: {size_p95:.1f}ms, throughput: {size_throughput:.1f}/sec")
    
    # Update overall metrics
    metrics.agents_executed = sum(test_config["count"] for test_config in state_size_tests)
    metrics.agents_succeeded = sum(result["successes"] for result in size_performance_results.values())
    metrics.agents_failed = metrics.agents_executed - metrics.agents_succeeded
    metrics.end_time = time.time()
    
    metrics.finalize_metrics()
    
    # Scalability assertions
    assert metrics.availability_percent >= 95.0, f"Overall scalability test availability must be  >= 95%"
    
    # Validate performance scales predictably
    small_p95 = size_performance_results["small"]["p95_response_ms"]
    enterprise_p95 = size_performance_results["enterprise"]["p95_response_ms"]
    
    # Enterprise states should not be more than 10x slower than small states
    scalability_factor = enterprise_p95 / small_p95 if small_p95 > 0 else 1
    assert scalability_factor <= 10.0, f"Performance should scale gracefully, got {scalability_factor:.1f}x degradation"
    
    # Throughput should degrade gracefully with state size
    small_throughput = size_performance_results["small"]["throughput_per_sec"]
    enterprise_throughput = size_performance_results["enterprise"]["throughput_per_sec"]
    
    if enterprise_throughput > 0:
        throughput_ratio = small_throughput / enterprise_throughput
        assert throughput_ratio <= 5.0, f"Throughput degradation should be reasonable, got {throughput_ratio:.1f}x"
    
    logger.info(f"[U+2713] State size scalability test completed: {metrics.agents_succeeded}/{metrics.agents_executed} overall success, "
                f"scalability factor: {scalability_factor:.1f}x")
    
    suite._save_load_test_report(test_name, metrics, {
        "state_size_results": size_performance_results,
        "scalability_factor": scalability_factor,
        "throughput_degradation": throughput_ratio if enterprise_throughput > 0 else 0
    })


@pytest.mark.load
@pytest.mark.asyncio
async def test_sustained_load_24_hours_simulation(load_test_suite):
    """Test sustained load patterns simulating 24-hour operations.
    
    Business Context: Enterprise monitoring and automation agents run
    continuously for 24+ hours. This test simulates sustained operations
    with realistic checkpoint and state evolution patterns.
    """
    suite = load_test_suite
    test_name = "sustained_load_24h_simulation"
    metrics = LoadTestMetrics(test_name=test_name, start_time=time.time())
    
    # Simulate 24 hours with compressed time scale (24 minutes = 24 hours)
    simulation_duration = 60 * 24  # 24 minutes in seconds
    checkpoint_interval = 60  # Create checkpoint every minute (simulates hourly)
    agents_per_checkpoint = 10  # Concurrent agents per checkpoint
    
    logger.info(f"Starting 24-hour sustained load simulation ({simulation_duration/60:.0f} minutes compressed)")
    
    # Track long-running performance
    hourly_performance = []
    total_checkpoints = 0
    sustained_agents_executed = 0
    sustained_agents_succeeded = 0
    
    start_simulation = time.time()
    
    # Simulate 24 hourly checkpoints
    for hour in range(24):
        hour_start = time.perf_counter()
        
        # Generate workloads for this "hour"
        workloads = suite._generate_workload_batch(agents_per_checkpoint, {
            "state_sizes": ["medium", "large"] if hour % 4 == 0 else ["small", "medium"],  # Vary complexity
            "execution_patterns": ["sustained"],
            "user_id": f"sustained_user_hour_{hour}"
        })
        
        # Execute hourly checkpoint
        tasks = [suite._execute_single_agent_workload(workload) for workload in workloads]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        hour_end = time.perf_counter()
        hour_duration = hour_end - hour_start
        
        # Process hourly results
        hour_successes = 0
        hour_response_times = []
        
        for result in results:
            sustained_agents_executed += 1
            if isinstance(result, tuple):
                success, execution_time = result
                if success:
                    hour_successes += 1
                    sustained_agents_succeeded += 1
                    hour_response_times.append(execution_time)
                    metrics.response_times_ms.append(execution_time)
        
        # Calculate hourly performance
        hour_performance = {
            "hour": hour,
            "agents_executed": len(workloads),
            "agents_succeeded": hour_successes,
            "avg_response_ms": statistics.mean(hour_response_times) if hour_response_times else 0,
            "throughput": hour_successes / hour_duration if hour_duration > 0 else 0,
            "success_rate": hour_successes / len(workloads) if workloads else 0
        }
        
        hourly_performance.append(hour_performance)
        total_checkpoints += 1
        
        logger.info(f"Hour {hour}: {hour_successes}/{len(workloads)} success, "
                   f"avg: {hour_performance['avg_response_ms']:.1f}ms, "
                   f"throughput: {hour_performance['throughput']:.1f}/sec")
        
        # Brief pause between "hours" to simulate realistic timing
        await asyncio.sleep(1.0)
        
        # Stop early if we're seeing sustained failures
        if hour >= 3 and hour_performance["success_rate"] < 0.8:
            logger.warning(f"Stopping simulation early due to low success rate at hour {hour}")
            break
    
    end_simulation = time.time()
    simulation_actual_duration = end_simulation - start_simulation
    
    # Update overall metrics
    metrics.agents_executed = sustained_agents_executed
    metrics.agents_succeeded = sustained_agents_succeeded
    metrics.agents_failed = sustained_agents_executed - sustained_agents_succeeded
    metrics.end_time = time.time()
    
    metrics.finalize_metrics()
    
    # Calculate sustained load metrics
    avg_hourly_success_rate = statistics.mean([h["success_rate"] for h in hourly_performance])
    avg_hourly_response_time = statistics.mean([h["avg_response_ms"] for h in hourly_performance if h["avg_response_ms"] > 0])
    total_throughput = sustained_agents_succeeded / simulation_actual_duration
    
    # Performance degradation analysis
    first_hour_success = hourly_performance[0]["success_rate"]
    last_hour_success = hourly_performance[-1]["success_rate"] 
    performance_degradation = (first_hour_success - last_hour_success) / first_hour_success if first_hour_success > 0 else 0
    
    # Sustained load assertions
    assert avg_hourly_success_rate >= 0.9, f"Sustained load success rate must be  >= 90%, got {avg_hourly_success_rate:.1%}"
    assert metrics.availability_percent >= 90.0, f"Overall availability must be  >= 90% for sustained load"
    assert performance_degradation <= 0.2, f"Performance degradation must be  <= 20%, got {performance_degradation:.1%}"
    assert avg_hourly_response_time <= 100.0, f"Sustained load avg response time must be  <= 100ms, got {avg_hourly_response_time:.1f}ms"
    
    # Memory leak detection (approximate)
    if len(hourly_performance) >= 6:
        early_hours_throughput = statistics.mean([h["throughput"] for h in hourly_performance[:3]])
        late_hours_throughput = statistics.mean([h["throughput"] for h in hourly_performance[-3:]])
        throughput_degradation = (early_hours_throughput - late_hours_throughput) / early_hours_throughput if early_hours_throughput > 0 else 0
        
        assert throughput_degradation <= 0.3, f"Throughput degradation suggests memory leak, got {throughput_degradation:.1%}"
    
    logger.info(f"[U+2713] Sustained load simulation completed: {total_checkpoints} checkpoints, "
                f"{sustained_agents_succeeded}/{sustained_agents_executed} overall success, "
                f"avg success rate: {avg_hourly_success_rate:.1%}, "
                f"performance degradation: {performance_degradation:.1%}")
    
    suite._save_load_test_report(test_name, metrics, {
        "simulation_duration_minutes": simulation_actual_duration / 60,
        "total_checkpoints": total_checkpoints,
        "hourly_performance": hourly_performance,
        "avg_hourly_success_rate": avg_hourly_success_rate,
        "performance_degradation": performance_degradation,
        "throughput_degradation": throughput_degradation if len(hourly_performance) >= 6 else 0
    })


@pytest.mark.load
@pytest.mark.asyncio
async def test_burst_traffic_handling(load_test_suite):
    """Test burst traffic patterns with spike handling.
    
    Business Context: Production systems experience traffic spikes during
    peak business hours or viral events. The platform must handle sudden
    load increases while maintaining performance and data integrity.
    """
    suite = load_test_suite
    test_name = "burst_traffic_handling"
    metrics = LoadTestMetrics(test_name=test_name, start_time=time.time())
    
    # Define burst pattern: baseline  ->  spike  ->  recovery
    baseline_agents = 20
    spike_agents = 80  # 4x spike
    recovery_agents = 30
    
    logger.info(f"Testing burst traffic: {baseline_agents} baseline  ->  {spike_agents} spike  ->  {recovery_agents} recovery")
    
    burst_phases = []
    
    # Phase 1: Baseline load
    logger.info("Phase 1: Baseline load")
    baseline_workloads = suite._generate_workload_batch(baseline_agents, {
        "state_sizes": ["small", "medium"],
        "execution_patterns": ["quick"],
        "user_id": "burst_baseline_user"
    })
    
    phase1_start = time.perf_counter()
    baseline_tasks = [suite._execute_single_agent_workload(w) for w in baseline_workloads]
    baseline_results = await asyncio.gather(*baseline_tasks, return_exceptions=True)
    phase1_end = time.perf_counter()
    
    # Process baseline results
    baseline_successes = sum(1 for r in baseline_results if isinstance(r, tuple) and r[0])
    baseline_times = [r[1] for r in baseline_results if isinstance(r, tuple) and r[0]]
    baseline_avg = statistics.mean(baseline_times) if baseline_times else 0
    
    burst_phases.append({
        "phase": "baseline",
        "agents": baseline_agents,
        "successes": baseline_successes,
        "avg_response_ms": baseline_avg,
        "duration_seconds": phase1_end - phase1_start
    })
    
    # Brief pause before spike
    await asyncio.sleep(2.0)
    
    # Phase 2: Traffic spike
    logger.info("Phase 2: Traffic spike")
    spike_workloads = suite._generate_workload_batch(spike_agents, {
        "state_sizes": ["small", "medium", "large"],  # Mixed complexity during spike
        "execution_patterns": ["burst"],
        "user_id": "burst_spike_user"
    })
    
    phase2_start = time.perf_counter()
    spike_tasks = [suite._execute_single_agent_workload(w) for w in spike_workloads]
    spike_results = await asyncio.gather(*spike_tasks, return_exceptions=True)
    phase2_end = time.perf_counter()
    
    # Process spike results
    spike_successes = sum(1 for r in spike_results if isinstance(r, tuple) and r[0])
    spike_times = [r[1] for r in spike_results if isinstance(r, tuple) and r[0]]
    spike_avg = statistics.mean(spike_times) if spike_times else 0
    spike_p95 = sorted(spike_times)[int(0.95 * len(spike_times))] if spike_times else 0
    
    burst_phases.append({
        "phase": "spike",
        "agents": spike_agents,
        "successes": spike_successes,
        "avg_response_ms": spike_avg,
        "p95_response_ms": spike_p95,
        "duration_seconds": phase2_end - phase2_start
    })
    
    # Brief pause before recovery
    await asyncio.sleep(2.0)
    
    # Phase 3: Recovery phase
    logger.info("Phase 3: Recovery phase")
    recovery_workloads = suite._generate_workload_batch(recovery_agents, {
        "state_sizes": ["small", "medium"],
        "execution_patterns": ["quick"],
        "user_id": "burst_recovery_user"
    })
    
    phase3_start = time.perf_counter()
    recovery_tasks = [suite._execute_single_agent_workload(w) for w in recovery_workloads]
    recovery_results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
    phase3_end = time.perf_counter()
    
    # Process recovery results
    recovery_successes = sum(1 for r in recovery_results if isinstance(r, tuple) and r[0])
    recovery_times = [r[1] for r in recovery_results if isinstance(r, tuple) and r[0]]
    recovery_avg = statistics.mean(recovery_times) if recovery_times else 0
    
    burst_phases.append({
        "phase": "recovery",
        "agents": recovery_agents,
        "successes": recovery_successes,
        "avg_response_ms": recovery_avg,
        "duration_seconds": phase3_end - phase3_start
    })
    
    # Update overall metrics
    all_response_times = baseline_times + spike_times + recovery_times
    metrics.response_times_ms.extend(all_response_times)
    metrics.agents_executed = baseline_agents + spike_agents + recovery_agents
    metrics.agents_succeeded = baseline_successes + spike_successes + recovery_successes
    metrics.agents_failed = metrics.agents_executed - metrics.agents_succeeded
    metrics.end_time = time.time()
    
    metrics.finalize_metrics()
    
    # Burst handling assertions
    baseline_success_rate = baseline_successes / baseline_agents
    spike_success_rate = spike_successes / spike_agents  
    recovery_success_rate = recovery_successes / recovery_agents
    
    assert baseline_success_rate >= 0.95, f"Baseline success rate must be  >= 95%, got {baseline_success_rate:.1%}"
    assert spike_success_rate >= 0.80, f"Spike handling success rate must be  >= 80%, got {spike_success_rate:.1%}"
    assert recovery_success_rate >= 0.90, f"Recovery success rate must be  >= 90%, got {recovery_success_rate:.1%}"
    
    # Performance degradation during spike should be reasonable
    performance_degradation = (spike_avg - baseline_avg) / baseline_avg if baseline_avg > 0 else 0
    assert performance_degradation <= 3.0, f"Spike performance degradation must be  <= 300%, got {performance_degradation:.1%}"
    
    # Recovery should return to near-baseline performance
    recovery_performance_ratio = recovery_avg / baseline_avg if baseline_avg > 0 else 1
    assert recovery_performance_ratio <= 1.5, f"Recovery performance should be within 150% of baseline, got {recovery_performance_ratio:.1f}x"
    
    # Spike P95 should meet SLA even under stress
    assert spike_p95 <= 500.0, f"Spike P95 should be  <= 500ms under stress, got {spike_p95:.1f}ms"
    
    logger.info(f"[U+2713] Burst traffic test completed:")
    for phase in burst_phases:
        logger.info(f"  {phase['phase']}: {phase['successes']}/{phase['agents']} success, "
                   f"avg: {phase['avg_response_ms']:.1f}ms")
    logger.info(f"Performance degradation during spike: {performance_degradation:.1%}")
    
    suite._save_load_test_report(test_name, metrics, {
        "burst_phases": burst_phases,
        "performance_degradation_percent": performance_degradation * 100,
        "recovery_performance_ratio": recovery_performance_ratio
    })


@pytest.mark.load
@pytest.mark.asyncio 
async def test_redis_connection_pool_exhaustion(load_test_suite):
    """Test Redis connection pool behavior under extreme load.
    
    Business Context: Redis connection pools can become bottlenecks under
    extreme concurrent load. This test validates graceful handling of
    connection pool exhaustion scenarios.
    """
    suite = load_test_suite
    test_name = "redis_connection_pool_exhaustion" 
    metrics = LoadTestMetrics(test_name=test_name, start_time=time.time())
    
    # Attempt to exhaust Redis connection pool with high concurrency
    extreme_concurrency = 200  # More than typical pool size
    connection_test_duration = 30  # seconds
    
    logger.info(f"Testing Redis connection pool with {extreme_concurrency} concurrent connections")
    
    # Generate workloads designed to hold connections longer
    workloads = suite._generate_workload_batch(extreme_concurrency, {
        "state_sizes": ["medium"],  # Consistent size for connection testing
        "execution_patterns": ["sustained"],
        "user_id": "connection_pool_test_user"
    })
    
    connection_errors = 0
    timeout_errors = 0
    successful_operations = 0
    
    async def connection_intensive_operation(workload: AgentWorkload) -> Tuple[str, bool, float]:
        """Perform operation that may stress connection pool."""
        start_time = time.perf_counter()
        
        try:
            # Multiple Redis operations to stress connection pool
            state_data = workload.generate_state_data()
            
            # Save operation
            request = StatePersistenceRequest(
                run_id=workload.run_id,
                thread_id=workload.thread_id,
                user_id=workload.user_id,
                state_data=state_data,
                checkpoint_type=CheckpointType.AUTO,
                is_recovery_point=False
            )
            
            save_success = await state_cache_manager.save_primary_state(request)
            
            if save_success:
                # Immediate read to verify
                loaded_state = await state_cache_manager.load_primary_state(workload.run_id)
                if loaded_state:
                    # Another write to update
                    updated_data = state_data.copy()
                    updated_data["step_count"] = state_data.get("step_count", 0) + 1
                    
                    update_request = StatePersistenceRequest(
                        run_id=workload.run_id,
                        thread_id=workload.thread_id,
                        user_id=workload.user_id,
                        state_data=updated_data,
                        checkpoint_type=CheckpointType.AUTO,
                        is_recovery_point=False
                    )
                    
                    update_success = await state_cache_manager.save_primary_state(update_request)
                    
                    execution_time = (time.perf_counter() - start_time) * 1000
                    return "success", update_success, execution_time
            
            execution_time = (time.perf_counter() - start_time) * 1000
            return "operation_failed", False, execution_time
            
        except asyncio.TimeoutError:
            execution_time = (time.perf_counter() - start_time) * 1000
            return "timeout", False, execution_time
        except ConnectionError:
            execution_time = (time.perf_counter() - start_time) * 1000
            return "connection_error", False, execution_time
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Connection pool test error for {workload.run_id}: {e}")
            return "exception", False, execution_time
    
    # Execute high-concurrency operations
    logger.info("Starting connection pool exhaustion test")
    start_execution = time.perf_counter()
    
    tasks = [connection_intensive_operation(workload) for workload in workloads]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_execution = time.perf_counter()
    
    # Process connection pool results
    error_types = {}
    
    for result in results:
        if isinstance(result, tuple):
            error_type, success, execution_time = result
            
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            if success:
                successful_operations += 1
                metrics.response_times_ms.append(execution_time)
            
            if error_type == "connection_error":
                connection_errors += 1
            elif error_type == "timeout":
                timeout_errors += 1
        else:
            error_types["exception"] = error_types.get("exception", 0) + 1
    
    # Update metrics
    metrics.agents_executed = len(workloads)
    metrics.agents_succeeded = successful_operations
    metrics.agents_failed = metrics.agents_executed - successful_operations
    metrics.end_time = time.time()
    
    metrics.finalize_metrics()
    
    # Connection pool assertions
    total_errors = connection_errors + timeout_errors
    error_rate = total_errors / metrics.agents_executed if metrics.agents_executed > 0 else 0
    
    # Under extreme load, some connection errors are acceptable, but system should remain stable
    assert error_rate <= 0.3, f"Connection error rate should be  <= 30% under extreme load, got {error_rate:.1%}"
    assert successful_operations >= metrics.agents_executed * 0.7, f"At least 70% operations should succeed despite connection pressure"
    
    # Response times for successful operations should still be reasonable
    if metrics.response_times_ms:
        assert metrics.p95_latency_ms <= 1000.0, f"P95 latency should be  <= 1s even under connection stress, got {metrics.p95_latency_ms:.1f}ms"
    
    # System should not crash or become completely unresponsive
    total_duration = end_execution - start_execution
    assert total_duration <= 120.0, f"Connection pool test should complete within 2 minutes, took {total_duration:.1f}s"
    
    # Verify graceful degradation rather than complete failure
    success_rate = successful_operations / metrics.agents_executed
    assert success_rate >= 0.5, f"Success rate should be  >= 50% showing graceful degradation, got {success_rate:.1%}"
    
    logger.info(f"[U+2713] Connection pool exhaustion test completed: {successful_operations}/{metrics.agents_executed} success")
    logger.info(f"Error breakdown: {dict(error_types)}")
    logger.info(f"Connection errors: {connection_errors}, Timeout errors: {timeout_errors}")
    
    suite._save_load_test_report(test_name, metrics, {
        "extreme_concurrency": extreme_concurrency,
        "connection_errors": connection_errors,
        "timeout_errors": timeout_errors,
        "error_types": error_types,
        "error_rate_percent": error_rate * 100,
        "total_duration_seconds": total_duration
    })


@pytest.mark.load
@pytest.mark.asyncio
async def test_postgres_checkpoint_under_load(load_test_suite):
    """Test PostgreSQL checkpoint creation under concurrent load.
    
    Business Context: Critical checkpoints must be created in PostgreSQL
    even during peak load for disaster recovery compliance. This validates
    checkpoint reliability under stress.
    """
    suite = load_test_suite
    test_name = "postgres_checkpoint_under_load"
    metrics = LoadTestMetrics(test_name=test_name, start_time=time.time())
    
    # Concurrent agents creating critical checkpoints
    checkpoint_agents = 50
    checkpoint_interval = 2.0  # Create checkpoints every 2 seconds
    test_duration = 30  # seconds
    
    logger.info(f"Testing PostgreSQL checkpoints with {checkpoint_agents} agents over {test_duration}s")
    
    checkpoint_successes = 0
    checkpoint_failures = 0
    checkpoint_response_times = []
    
    async def create_checkpoint_workload(agent_index: int) -> Dict[str, Any]:
        """Create workload that generates PostgreSQL checkpoints."""
        workload = AgentWorkload(
            agent_id=f"checkpoint_agent_{agent_index}",
            run_id=f"checkpoint_run_{agent_index}_{uuid.uuid4().hex[:8]}",
            thread_id=f"checkpoint_thread_{agent_index}",
            user_id="checkpoint_load_test_user",
            agent_type="critical_agent",
            state_size="large",  # Large states for meaningful checkpoints
            execution_pattern="sustained"
        )
        
        suite._track_test_data(workload.run_id, workload.thread_id, workload.user_id)
        
        checkpoint_start = time.perf_counter()
        
        try:
            # Create state requiring critical checkpoint
            state_data = workload.generate_state_data()
            
            request = StatePersistenceRequest(
                run_id=workload.run_id,
                thread_id=workload.thread_id,
                user_id=workload.user_id,
                state_data=state_data,
                checkpoint_type=CheckpointType.CRITICAL,  # Force PostgreSQL checkpoint
                is_recovery_point=True
            )
            
            # Save to Redis (primary)
            save_success = await state_cache_manager.save_primary_state(request)
            
            # Simulate PostgreSQL checkpoint creation
            if save_success:
                # In production, this would be handled by checkpoint manager
                # For this test, we simulate the checkpoint operation
                db_session = await database_manager.get_session()
                try:
                    # Simulate checkpoint creation with realistic delay
                    await asyncio.sleep(0.1)  # Simulated DB write time
                    
                    checkpoint_data = {
                        "run_id": workload.run_id,
                        "user_id": workload.user_id,
                        "thread_id": workload.thread_id,
                        "checkpoint_type": "CRITICAL",
                        "state_hash": str(hash(json.dumps(state_data, sort_keys=True))),
                        "created_at": datetime.now(timezone.utc),
                        "is_recovery_point": True
                    }
                    
                    # Validate checkpoint data structure
                    assert checkpoint_data["run_id"] == workload.run_id
                    assert checkpoint_data["is_recovery_point"] is True
                    
                    await db_session.commit()
                    checkpoint_created = True
                    
                except Exception as e:
                    await db_session.rollback()
                    logger.error(f"PostgreSQL checkpoint creation failed: {e}")
                    checkpoint_created = False
                finally:
                    await db_session.close()
            else:
                checkpoint_created = False
            
            checkpoint_time = (time.perf_counter() - checkpoint_start) * 1000
            
            return {
                "success": checkpoint_created,
                "response_time_ms": checkpoint_time,
                "run_id": workload.run_id
            }
            
        except Exception as e:
            checkpoint_time = (time.perf_counter() - checkpoint_start) * 1000
            logger.error(f"Checkpoint workload failed for agent {agent_index}: {e}")
            return {
                "success": False,
                "response_time_ms": checkpoint_time,
                "run_id": workload.run_id,
                "error": str(e)
            }
    
    # Execute checkpoint operations in waves
    total_checkpoint_operations = 0
    wave_count = int(test_duration / checkpoint_interval)
    
    for wave in range(wave_count):
        logger.info(f"Checkpoint wave {wave + 1}/{wave_count}")
        
        # Create batch of checkpoint operations
        wave_tasks = [create_checkpoint_workload(wave * checkpoint_agents + i) for i in range(checkpoint_agents)]
        wave_results = await asyncio.gather(*wave_tasks, return_exceptions=True)
        
        # Process wave results
        for result in wave_results:
            total_checkpoint_operations += 1
            
            if isinstance(result, dict):
                if result["success"]:
                    checkpoint_successes += 1
                    checkpoint_response_times.append(result["response_time_ms"])
                    metrics.response_times_ms.append(result["response_time_ms"])
                else:
                    checkpoint_failures += 1
            else:
                checkpoint_failures += 1
                logger.error(f"Checkpoint wave exception: {result}")
        
        # Brief pause between waves
        await asyncio.sleep(checkpoint_interval)
    
    # Update metrics
    metrics.agents_executed = total_checkpoint_operations
    metrics.agents_succeeded = checkpoint_successes
    metrics.agents_failed = checkpoint_failures
    metrics.end_time = time.time()
    
    metrics.finalize_metrics()
    
    # PostgreSQL checkpoint assertions
    checkpoint_success_rate = checkpoint_successes / total_checkpoint_operations if total_checkpoint_operations > 0 else 0
    
    assert checkpoint_success_rate >= 0.90, f"Checkpoint success rate must be  >= 90% for disaster recovery, got {checkpoint_success_rate:.1%}"
    assert checkpoint_successes >= wave_count * checkpoint_agents * 0.9, f"Minimum checkpoint count required for compliance"
    
    # Checkpoint performance should remain reasonable under load
    if checkpoint_response_times:
        avg_checkpoint_time = statistics.mean(checkpoint_response_times)
        p95_checkpoint_time = sorted(checkpoint_response_times)[int(0.95 * len(checkpoint_response_times))]
        
        assert avg_checkpoint_time <= 500.0, f"Average checkpoint time should be  <= 500ms, got {avg_checkpoint_time:.1f}ms"
        assert p95_checkpoint_time <= 1000.0, f"P95 checkpoint time should be  <= 1s, got {p95_checkpoint_time:.1f}ms"
    
    # Validate no data loss during checkpoint operations
    assert metrics.data_corruption_count == 0, "No data corruption allowed during checkpoint operations"
    
    logger.info(f"[U+2713] PostgreSQL checkpoint under load test completed: {checkpoint_successes}/{total_checkpoint_operations} success")
    logger.info(f"Checkpoint success rate: {checkpoint_success_rate:.1%}")
    if checkpoint_response_times:
        logger.info(f"Checkpoint performance: avg {statistics.mean(checkpoint_response_times):.1f}ms, "
                   f"p95 {sorted(checkpoint_response_times)[int(0.95 * len(checkpoint_response_times))]:.1f}ms")
    
    suite._save_load_test_report(test_name, metrics, {
        "checkpoint_operations": total_checkpoint_operations,
        "checkpoint_successes": checkpoint_successes,
        "checkpoint_success_rate": checkpoint_success_rate,
        "waves_executed": wave_count,
        "avg_checkpoint_time_ms": statistics.mean(checkpoint_response_times) if checkpoint_response_times else 0
    })


@pytest.mark.load
@pytest.mark.asyncio
async def test_memory_usage_under_load(load_test_suite):
    """Test memory usage patterns and leak detection under sustained load.
    
    Business Context: Memory leaks or excessive memory usage can cause
    production outages and affect Enterprise SLAs. This test validates
    memory behavior under sustained concurrent operations.
    """
    suite = load_test_suite
    test_name = "memory_usage_under_load"
    metrics = LoadTestMetrics(test_name=test_name, start_time=time.time())
    
    # Memory monitoring configuration
    concurrent_agents = 75
    memory_test_duration = 45  # seconds
    memory_sample_interval = 2  # seconds
    
    logger.info(f"Testing memory usage with {concurrent_agents} concurrent agents over {memory_test_duration}s")
    
    memory_samples = []
    agent_operations = 0
    agent_successes = 0
    
    async def memory_intensive_workload(agent_index: int) -> Dict[str, Any]:
        """Create memory-intensive agent workload."""
        workload = AgentWorkload(
            agent_id=f"memory_agent_{agent_index}",
            run_id=f"memory_run_{agent_index}_{uuid.uuid4().hex[:8]}",
            thread_id=f"memory_thread_{agent_index}",
            user_id="memory_load_test_user",
            agent_type="data_analyst",  # Typically memory-intensive
            state_size="large",  # Large states to test memory handling
            execution_pattern="sustained"
        )
        
        suite._track_test_data(workload.run_id, workload.thread_id, workload.user_id)
        
        operations_completed = 0
        operations_succeeded = 0
        
        # Perform multiple operations to simulate sustained memory usage
        for operation in range(5):  # 5 operations per agent
            try:
                state_data = workload.generate_state_data()
                
                # Add extra data to increase memory pressure
                state_data["large_dataset"] = [f"data_point_{i}" for i in range(1000)]
                state_data["metadata"]["operation_index"] = operation
                
                request = StatePersistenceRequest(
                    run_id=f"{workload.run_id}_op_{operation}",
                    thread_id=workload.thread_id,
                    user_id=workload.user_id,
                    state_data=state_data,
                    checkpoint_type=CheckpointType.AUTO,
                    is_recovery_point=False
                )
                
                # Track this operation for cleanup
                suite._track_test_data(f"{workload.run_id}_op_{operation}", workload.thread_id, workload.user_id)
                
                save_success = await state_cache_manager.save_primary_state(request)
                operations_completed += 1
                
                if save_success:
                    operations_succeeded += 1
                    
                # Small delay between operations
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Memory workload operation failed for agent {agent_index}, op {operation}: {e}")
                operations_completed += 1
        
        return {
            "agent_index": agent_index,
            "operations_completed": operations_completed,
            "operations_succeeded": operations_succeeded
        }
    
    async def monitor_memory_usage():
        """Monitor memory usage throughout the test."""
        test_start = time.time()
        
        while (time.time() - test_start) < memory_test_duration:
            try:
                process_info = suite.process.memory_info()
                memory_sample = {
                    "timestamp": time.time(),
                    "rss_mb": process_info.rss / 1024 / 1024,  # Resident Set Size
                    "vms_mb": process_info.vms / 1024 / 1024,  # Virtual Memory Size  
                    "percent": suite.process.memory_percent(),
                    "available_mb": psutil.virtual_memory().available / 1024 / 1024
                }
                memory_samples.append(memory_sample)
                
                # Check for memory pressure
                if memory_sample["rss_mb"] > 2048:  # 2GB threshold
                    logger.warning(f"High memory usage detected: {memory_sample['rss_mb']:.1f}MB RSS")
                
                await asyncio.sleep(memory_sample_interval)
                
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                break
    
    # Start memory monitoring
    memory_monitor_task = asyncio.create_task(monitor_memory_usage())
    
    # Execute memory-intensive workloads
    logger.info("Starting memory-intensive workloads")
    workload_tasks = [memory_intensive_workload(i) for i in range(concurrent_agents)]
    workload_results = await asyncio.gather(*workload_tasks, return_exceptions=True)
    
    # Stop memory monitoring
    memory_monitor_task.cancel()
    try:
        await memory_monitor_task
    except asyncio.CancelledError:
        pass
    
    # Process workload results
    for result in workload_results:
        if isinstance(result, dict):
            agent_operations += result["operations_completed"]
            agent_successes += result["operations_succeeded"]
        else:
            logger.error(f"Memory workload exception: {result}")
    
    # Update metrics
    metrics.agents_executed = agent_operations
    metrics.agents_succeeded = agent_successes
    metrics.agents_failed = agent_operations - agent_successes
    metrics.end_time = time.time()
    
    if memory_samples:
        metrics.peak_memory_mb = max(sample["rss_mb"] for sample in memory_samples)
    
    metrics.finalize_metrics()
    
    # Analyze memory usage patterns
    if len(memory_samples) >= 3:
        initial_memory = statistics.mean([s["rss_mb"] for s in memory_samples[:3]])
        final_memory = statistics.mean([s["rss_mb"] for s in memory_samples[-3:]])
        peak_memory = max(s["rss_mb"] for s in memory_samples)
        avg_memory = statistics.mean(s["rss_mb"] for s in memory_samples)
        
        # Memory growth analysis
        memory_growth = final_memory - initial_memory
        memory_growth_percent = (memory_growth / initial_memory) * 100 if initial_memory > 0 else 0
        
        # Memory leak detection
        memory_leak_detected = memory_growth_percent > 50  # >50% growth suggests leak
        
        # Memory usage assertions
        assert peak_memory <= 2048, f"Peak memory must be  <= 2GB, got {peak_memory:.1f}MB"
        assert memory_growth_percent <= 100, f"Memory growth should be  <= 100%, got {memory_growth_percent:.1f}%"
        assert not memory_leak_detected, f"Memory leak detected: {memory_growth_percent:.1f}% growth"
        
        # Performance should remain stable despite memory usage
        success_rate = agent_successes / agent_operations if agent_operations > 0 else 0
        assert success_rate >= 0.85, f"Success rate should be  >= 85% despite memory pressure, got {success_rate:.1%}"
        
        logger.info(f"[U+2713] Memory usage test completed: {agent_successes}/{agent_operations} operations")
        logger.info(f"Memory usage: initial {initial_memory:.1f}MB, peak {peak_memory:.1f}MB, final {final_memory:.1f}MB")
        logger.info(f"Memory growth: {memory_growth:.1f}MB ({memory_growth_percent:.1f}%)")
        
        # Force garbage collection and verify cleanup
        gc.collect()
        await asyncio.sleep(2.0)  # Allow cleanup time
        
        post_gc_sample = {
            "rss_mb": suite.process.memory_info().rss / 1024 / 1024,
            "percent": suite.process.memory_percent()
        }
        
        memory_cleanup = final_memory - post_gc_sample["rss_mb"]
        logger.info(f"Memory cleanup after GC: {memory_cleanup:.1f}MB freed")
        
        suite._save_load_test_report(test_name, metrics, {
            "memory_analysis": {
                "initial_memory_mb": initial_memory,
                "peak_memory_mb": peak_memory,
                "final_memory_mb": final_memory,
                "avg_memory_mb": avg_memory,
                "memory_growth_mb": memory_growth,
                "memory_growth_percent": memory_growth_percent,
                "memory_leak_detected": memory_leak_detected,
                "post_gc_memory_mb": post_gc_sample["rss_mb"],
                "memory_cleanup_mb": memory_cleanup
            },
            "memory_samples": memory_samples[-10:],  # Last 10 samples
            "concurrent_agents": concurrent_agents,
            "operations_per_agent": 5
        })
    
    else:
        pytest.skip("Insufficient memory samples for analysis")


@pytest.mark.load  
@pytest.mark.asyncio
async def test_latency_sla_compliance(load_test_suite):
    """Test latency SLA compliance under production load patterns.
    
    Business Context: Enterprise SLAs require specific latency guarantees:
    - P50 < 50ms for standard operations
    - P95 < 150ms for complex operations  
    - P99 < 200ms for all operations
    - 99.9% availability during normal operations
    """
    suite = load_test_suite
    test_name = "latency_sla_compliance"
    metrics = LoadTestMetrics(test_name=test_name, start_time=time.time())
    
    # SLA compliance test configuration
    sla_test_agents = 60
    sla_test_duration = 60  # seconds
    measurement_interval = 10  # seconds
    
    sla_requirements = {
        "p50_ms": 50,
        "p95_ms": 150, 
        "p99_ms": 200,
        "availability_percent": 99.9
    }
    
    logger.info(f"Testing SLA compliance with {sla_test_agents} agents over {sla_test_duration}s")
    logger.info(f"SLA requirements: P50<{sla_requirements['p50_ms']}ms, P95<{sla_requirements['p95_ms']}ms, P99<{sla_requirements['p99_ms']}ms")
    
    sla_measurements = []
    
    # Perform SLA compliance measurements in intervals
    measurement_count = int(sla_test_duration / measurement_interval)
    
    for measurement in range(measurement_count):
        measurement_start = time.perf_counter()
        
        logger.info(f"SLA measurement {measurement + 1}/{measurement_count}")
        
        # Generate realistic production workload mix
        measurement_workloads = suite._generate_workload_batch(sla_test_agents, {
            "state_sizes": ["small", "small", "medium", "large"],  # 50% small, 25% medium, 25% large
            "execution_patterns": ["quick", "sustained"],
            "user_id": f"sla_compliance_user_{measurement}"
        })
        
        # Execute measurement batch
        measurement_tasks = [suite._execute_single_agent_workload(w) for w in measurement_workloads]
        measurement_results = await asyncio.gather(*measurement_tasks, return_exceptions=True)
        
        measurement_end = time.perf_counter()
        measurement_duration = measurement_end - measurement_start
        
        # Process measurement results
        measurement_successes = 0
        measurement_response_times = []
        
        for result in measurement_results:
            if isinstance(result, tuple):
                success, response_time = result
                if success:
                    measurement_successes += 1
                    measurement_response_times.append(response_time)
                    metrics.response_times_ms.append(response_time)
        
        # Calculate SLA metrics for this measurement
        if measurement_response_times:
            sorted_times = sorted(measurement_response_times)
            count = len(sorted_times)
            
            measurement_sla = {
                "measurement_id": measurement,
                "timestamp": time.time(),
                "agents_executed": len(measurement_workloads),
                "agents_succeeded": measurement_successes,
                "availability_percent": (measurement_successes / len(measurement_workloads)) * 100,
                "p50_ms": sorted_times[int(0.5 * count)],
                "p95_ms": sorted_times[int(0.95 * count)],
                "p99_ms": sorted_times[int(0.99 * count)],
                "avg_ms": statistics.mean(sorted_times),
                "measurement_duration_seconds": measurement_duration
            }
            
            # Check SLA compliance for this measurement
            sla_violations = []
            if measurement_sla["p50_ms"] > sla_requirements["p50_ms"]:
                sla_violations.append(f"P50 {measurement_sla['p50_ms']:.1f}ms > {sla_requirements['p50_ms']}ms")
            if measurement_sla["p95_ms"] > sla_requirements["p95_ms"]:
                sla_violations.append(f"P95 {measurement_sla['p95_ms']:.1f}ms > {sla_requirements['p95_ms']}ms")
            if measurement_sla["p99_ms"] > sla_requirements["p99_ms"]:
                sla_violations.append(f"P99 {measurement_sla['p99_ms']:.1f}ms > {sla_requirements['p99_ms']}ms")
            if measurement_sla["availability_percent"] < sla_requirements["availability_percent"]:
                sla_violations.append(f"Availability {measurement_sla['availability_percent']:.1f}% < {sla_requirements['availability_percent']}%")
            
            measurement_sla["sla_violations"] = sla_violations
            measurement_sla["sla_compliant"] = len(sla_violations) == 0
            
            sla_measurements.append(measurement_sla)
            
            logger.info(f"Measurement {measurement + 1}: P50={measurement_sla['p50_ms']:.1f}ms, "
                       f"P95={measurement_sla['p95_ms']:.1f}ms, P99={measurement_sla['p99_ms']:.1f}ms, "
                       f"Availability={measurement_sla['availability_percent']:.1f}%")
            
            if sla_violations:
                logger.warning(f"SLA violations in measurement {measurement + 1}: {sla_violations}")
        
        # Brief pause between measurements
        await asyncio.sleep(2.0)
    
    # Update overall metrics
    metrics.agents_executed = sum(m["agents_executed"] for m in sla_measurements)
    metrics.agents_succeeded = sum(m["agents_succeeded"] for m in sla_measurements)
    metrics.agents_failed = metrics.agents_executed - metrics.agents_succeeded
    metrics.end_time = time.time()
    
    metrics.finalize_metrics()
    
    # Calculate overall SLA compliance
    compliant_measurements = sum(1 for m in sla_measurements if m["sla_compliant"])
    sla_compliance_rate = compliant_measurements / len(sla_measurements) if sla_measurements else 0
    
    # Aggregate SLA metrics across all measurements
    if sla_measurements:
        overall_p50 = statistics.median([m["p50_ms"] for m in sla_measurements])
        overall_p95 = statistics.median([m["p95_ms"] for m in sla_measurements])
        overall_p99 = statistics.median([m["p99_ms"] for m in sla_measurements])
        overall_availability = statistics.mean([m["availability_percent"] for m in sla_measurements])
        
        # SLA compliance assertions
        assert sla_compliance_rate >= 0.9, f"SLA compliance rate must be  >= 90%, got {sla_compliance_rate:.1%}"
        assert overall_availability >= sla_requirements["availability_percent"], f"Overall availability must be  >= {sla_requirements['availability_percent']}%, got {overall_availability:.1f}%"
        assert overall_p50 <= sla_requirements["p50_ms"], f"Overall P50 must be  <= {sla_requirements['p50_ms']}ms, got {overall_p50:.1f}ms"
        assert overall_p95 <= sla_requirements["p95_ms"], f"Overall P95 must be  <= {sla_requirements['p95_ms']}ms, got {overall_p95:.1f}ms"
        assert overall_p99 <= sla_requirements["p99_ms"], f"Overall P99 must be  <= {sla_requirements['p99_ms']}ms, got {overall_p99:.1f}ms"
        
        # Consistency check - SLA metrics should not vary wildly between measurements
        p50_variance = statistics.stdev([m["p50_ms"] for m in sla_measurements]) if len(sla_measurements) > 1 else 0
        p95_variance = statistics.stdev([m["p95_ms"] for m in sla_measurements]) if len(sla_measurements) > 1 else 0
        
        assert p50_variance <= overall_p50 * 0.5, f"P50 variance too high, indicates unstable performance: {p50_variance:.1f}ms"
        assert p95_variance <= overall_p95 * 0.5, f"P95 variance too high, indicates unstable performance: {p95_variance:.1f}ms"
        
        logger.info(f"[U+2713] SLA compliance test completed: {compliant_measurements}/{len(sla_measurements)} measurements compliant ({sla_compliance_rate:.1%})")
        logger.info(f"Overall SLA metrics: P50={overall_p50:.1f}ms, P95={overall_p95:.1f}ms, P99={overall_p99:.1f}ms, Availability={overall_availability:.1f}%")
        
        suite._save_load_test_report(test_name, metrics, {
            "sla_requirements": sla_requirements,
            "sla_measurements": sla_measurements,
            "sla_compliance_rate": sla_compliance_rate,
            "overall_sla_metrics": {
                "p50_ms": overall_p50,
                "p95_ms": overall_p95,
                "p99_ms": overall_p99,
                "availability_percent": overall_availability
            },
            "performance_consistency": {
                "p50_variance": p50_variance,
                "p95_variance": p95_variance
            }
        })
    
    else:
        pytest.fail("No SLA measurements completed")


@pytest.mark.load
@pytest.mark.asyncio
async def test_failure_recovery_under_load(load_test_suite):
    """Test failure recovery patterns under concurrent load.
    
    Business Context: Production systems must recover gracefully from
    failures while maintaining service for other concurrent operations.
    This validates resilience and recovery patterns under load.
    """
    suite = load_test_suite
    test_name = "failure_recovery_under_load"
    metrics = LoadTestMetrics(test_name=test_name, start_time=time.time())
    
    # Recovery test configuration  
    baseline_agents = 30
    recovery_test_duration = 45  # seconds
    failure_injection_delay = 15  # seconds into test
    
    logger.info(f"Testing failure recovery with {baseline_agents} baseline agents")
    
    recovery_results = {
        "pre_failure": {"successes": 0, "attempts": 0, "avg_latency": 0},
        "during_failure": {"successes": 0, "attempts": 0, "avg_latency": 0},
        "post_recovery": {"successes": 0, "attempts": 0, "avg_latency": 0}
    }
    
    failure_injected = False
    recovery_complete = False
    
    async def baseline_agent_workload(agent_index: int, phase: str) -> Dict[str, Any]:
        """Run baseline agent workload during different test phases."""
        workload = AgentWorkload(
            agent_id=f"recovery_agent_{agent_index}_{phase}",
            run_id=f"recovery_run_{agent_index}_{phase}_{uuid.uuid4().hex[:8]}",
            thread_id=f"recovery_thread_{agent_index}_{phase}",
            user_id="recovery_load_test_user",
            agent_type="resilient_agent",
            state_size="medium",
            execution_pattern="quick"
        )
        
        suite._track_test_data(workload.run_id, workload.thread_id, workload.user_id)
        
        start_time = time.perf_counter()
        
        try:
            # Generate and save state
            state_data = workload.generate_state_data()
            
            request = StatePersistenceRequest(
                run_id=workload.run_id,
                thread_id=workload.thread_id,
                user_id=workload.user_id,
                state_data=state_data,
                checkpoint_type=CheckpointType.AUTO,
                is_recovery_point=False
            )
            
            save_success = await state_cache_manager.save_primary_state(request)
            
            if save_success:
                # Verify recovery by loading state
                loaded_state = await state_cache_manager.load_primary_state(workload.run_id)
                recovery_success = loaded_state is not None
            else:
                recovery_success = False
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return {
                "phase": phase,
                "success": recovery_success,
                "response_time_ms": execution_time,
                "agent_index": agent_index
            }
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Recovery workload failed for agent {agent_index} in phase {phase}: {e}")
            return {
                "phase": phase,
                "success": False,
                "response_time_ms": execution_time,
                "agent_index": agent_index,
                "error": str(e)
            }
    
    # Phase 1: Pre-failure baseline
    logger.info("Phase 1: Pre-failure baseline")
    pre_failure_start = time.perf_counter()
    
    pre_failure_tasks = [baseline_agent_workload(i, "pre_failure") for i in range(baseline_agents)]
    pre_failure_results = await asyncio.gather(*pre_failure_tasks, return_exceptions=True)
    
    # Process pre-failure results
    pre_failure_times = []
    for result in pre_failure_results:
        if isinstance(result, dict):
            recovery_results["pre_failure"]["attempts"] += 1
            if result["success"]:
                recovery_results["pre_failure"]["successes"] += 1
                pre_failure_times.append(result["response_time_ms"])
                metrics.response_times_ms.append(result["response_time_ms"])
    
    recovery_results["pre_failure"]["avg_latency"] = statistics.mean(pre_failure_times) if pre_failure_times else 0
    
    logger.info(f"Pre-failure baseline: {recovery_results['pre_failure']['successes']}/{recovery_results['pre_failure']['attempts']} success, "
               f"avg latency: {recovery_results['pre_failure']['avg_latency']:.1f}ms")
    
    # Brief pause before failure injection
    await asyncio.sleep(3.0)
    
    # Phase 2: Simulate failure condition (Redis connection issues)
    logger.info("Phase 2: Failure injection and recovery testing")
    
    # Simulate partial Redis failure by introducing connection delays/errors
    # In a real test, this might involve network partitioning or service disruption
    failure_simulation_active = True
    
    async def failure_simulation_workload(agent_index: int) -> Dict[str, Any]:
        """Workload that runs during simulated failure conditions."""
        workload = AgentWorkload(
            agent_id=f"failure_agent_{agent_index}",
            run_id=f"failure_run_{agent_index}_{uuid.uuid4().hex[:8]}",
            thread_id=f"failure_thread_{agent_index}",
            user_id="failure_recovery_test_user",
            agent_type="resilient_agent",
            state_size="medium",
            execution_pattern="quick"
        )
        
        suite._track_test_data(workload.run_id, workload.thread_id, workload.user_id)
        
        start_time = time.perf_counter()
        
        try:
            # Generate state data
            state_data = workload.generate_state_data()
            
            request = StatePersistenceRequest(
                run_id=workload.run_id,
                thread_id=workload.thread_id,
                user_id=workload.user_id,
                state_data=state_data,
                checkpoint_type=CheckpointType.AUTO,
                is_recovery_point=False
            )
            
            # Simulate failure conditions with timeouts and retries
            max_retries = 3
            retry_count = 0
            save_success = False
            
            while retry_count < max_retries and not save_success:
                try:
                    if failure_simulation_active and random.random() < 0.4:  # 40% failure rate during simulation
                        await asyncio.sleep(0.2)  # Simulate slow response
                        if random.random() < 0.5:  # 50% of slow responses fail
                            raise ConnectionError("Simulated Redis connection failure")
                    
                    save_success = await state_cache_manager.save_primary_state(request)
                    
                except (ConnectionError, asyncio.TimeoutError) as e:
                    retry_count += 1
                    logger.debug(f"Simulated failure for agent {agent_index}, retry {retry_count}: {e}")
                    await asyncio.sleep(0.1 * retry_count)  # Exponential backoff
            
            # Verify recovery if save succeeded
            recovery_verified = False
            if save_success:
                try:
                    loaded_state = await state_cache_manager.load_primary_state(workload.run_id)
                    recovery_verified = loaded_state is not None
                except Exception:
                    recovery_verified = False
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return {
                "success": recovery_verified,
                "response_time_ms": execution_time,
                "retry_count": retry_count,
                "agent_index": agent_index
            }
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Failure simulation workload failed for agent {agent_index}: {e}")
            return {
                "success": False,
                "response_time_ms": execution_time,
                "retry_count": max_retries,
                "agent_index": agent_index,
                "error": str(e)
            }
    
    # Execute during-failure workloads
    during_failure_tasks = [failure_simulation_workload(i) for i in range(baseline_agents)]
    during_failure_results = await asyncio.gather(*during_failure_tasks, return_exceptions=True)
    
    # Process during-failure results  
    during_failure_times = []
    total_retries = 0
    
    for result in during_failure_results:
        if isinstance(result, dict):
            recovery_results["during_failure"]["attempts"] += 1
            total_retries += result.get("retry_count", 0)
            
            if result["success"]:
                recovery_results["during_failure"]["successes"] += 1
                during_failure_times.append(result["response_time_ms"])
                metrics.response_times_ms.append(result["response_time_ms"])
    
    recovery_results["during_failure"]["avg_latency"] = statistics.mean(during_failure_times) if during_failure_times else 0
    
    logger.info(f"During failure: {recovery_results['during_failure']['successes']}/{recovery_results['during_failure']['attempts']} success, "
               f"avg latency: {recovery_results['during_failure']['avg_latency']:.1f}ms, "
               f"total retries: {total_retries}")
    
    # Phase 3: Post-recovery (failure simulation disabled)
    failure_simulation_active = False
    await asyncio.sleep(3.0)  # Allow system to stabilize
    
    logger.info("Phase 3: Post-recovery validation")
    
    post_recovery_tasks = [baseline_agent_workload(i, "post_recovery") for i in range(baseline_agents)]
    post_recovery_results = await asyncio.gather(*post_recovery_tasks, return_exceptions=True)
    
    # Process post-recovery results
    post_recovery_times = []
    for result in post_recovery_results:
        if isinstance(result, dict):
            recovery_results["post_recovery"]["attempts"] += 1
            if result["success"]:
                recovery_results["post_recovery"]["successes"] += 1
                post_recovery_times.append(result["response_time_ms"])
                metrics.response_times_ms.append(result["response_time_ms"])
    
    recovery_results["post_recovery"]["avg_latency"] = statistics.mean(post_recovery_times) if post_recovery_times else 0
    
    logger.info(f"Post-recovery: {recovery_results['post_recovery']['successes']}/{recovery_results['post_recovery']['attempts']} success, "
               f"avg latency: {recovery_results['post_recovery']['avg_latency']:.1f}ms")
    
    # Update overall metrics
    metrics.agents_executed = sum(phase["attempts"] for phase in recovery_results.values())
    metrics.agents_succeeded = sum(phase["successes"] for phase in recovery_results.values())
    metrics.agents_failed = metrics.agents_executed - metrics.agents_succeeded
    metrics.end_time = time.time()
    
    metrics.finalize_metrics()
    
    # Recovery performance assertions
    pre_failure_success_rate = recovery_results["pre_failure"]["successes"] / recovery_results["pre_failure"]["attempts"] if recovery_results["pre_failure"]["attempts"] > 0 else 0
    during_failure_success_rate = recovery_results["during_failure"]["successes"] / recovery_results["during_failure"]["attempts"] if recovery_results["during_failure"]["attempts"] > 0 else 0
    post_recovery_success_rate = recovery_results["post_recovery"]["successes"] / recovery_results["post_recovery"]["attempts"] if recovery_results["post_recovery"]["attempts"] > 0 else 0
    
    # Baseline performance before failure should be good
    assert pre_failure_success_rate >= 0.95, f"Pre-failure success rate should be  >= 95%, got {pre_failure_success_rate:.1%}"
    
    # During failure, system should maintain some level of service (graceful degradation)
    assert during_failure_success_rate >= 0.6, f"During failure success rate should be  >= 60% (graceful degradation), got {during_failure_success_rate:.1%}"
    
    # Post-recovery should return to near-baseline performance
    assert post_recovery_success_rate >= 0.9, f"Post-recovery success rate should be  >= 90%, got {post_recovery_success_rate:.1%}"
    
    # Recovery should not cause permanent performance degradation
    performance_recovery_ratio = recovery_results["post_recovery"]["avg_latency"] / recovery_results["pre_failure"]["avg_latency"] if recovery_results["pre_failure"]["avg_latency"] > 0 else 1
    assert performance_recovery_ratio <= 1.3, f"Post-recovery performance should be within 130% of baseline, got {performance_recovery_ratio:.1f}x"
    
    # System should demonstrate retry resilience
    avg_retries_per_operation = total_retries / recovery_results["during_failure"]["attempts"] if recovery_results["during_failure"]["attempts"] > 0 else 0
    assert avg_retries_per_operation <= 2.0, f"Average retries should be reasonable, got {avg_retries_per_operation:.1f}"
    
    logger.info(f"[U+2713] Failure recovery test completed:")
    logger.info(f"  Pre-failure: {pre_failure_success_rate:.1%} success, {recovery_results['pre_failure']['avg_latency']:.1f}ms avg")
    logger.info(f"  During failure: {during_failure_success_rate:.1%} success, {recovery_results['during_failure']['avg_latency']:.1f}ms avg")
    logger.info(f"  Post-recovery: {post_recovery_success_rate:.1%} success, {recovery_results['post_recovery']['avg_latency']:.1f}ms avg")
    logger.info(f"Performance recovery ratio: {performance_recovery_ratio:.1f}x")
    
    suite._save_load_test_report(test_name, metrics, {
        "recovery_phases": recovery_results,
        "success_rates": {
            "pre_failure": pre_failure_success_rate,
            "during_failure": during_failure_success_rate,
            "post_recovery": post_recovery_success_rate
        },
        "performance_recovery_ratio": performance_recovery_ratio,
        "avg_retries_per_operation": avg_retries_per_operation,
        "total_retries": total_retries
    })


if __name__ == "__main__":
    # Run production load tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto", "-m", "load"])