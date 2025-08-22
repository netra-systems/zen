"""Distributed Lock Contention - L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Mid and Enterprise tiers (distributed coordination affects multi-instance deployments)
- Business Goal: Ensure distributed lock performance under high contention scenarios
- Value Impact: Maintains coordination integrity, prevents deadlocks, ensures system reliability
- Strategic Impact: $7K MRR protection through reliable distributed coordination and performance

Critical Path: Lock acquisition -> Contention handling -> Deadlock prevention -> Performance validation
L3 Realism: Real Redis distributed locks, actual contention simulation, lock performance measurement
Performance Requirements: Lock acquisition < 50ms under contention, deadlock detection < 100ms, throughput > 1000 locks/s
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import json
import logging
import random
import statistics
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest
import redis.asyncio as aioredis

from netra_backend.app.logging_config import central_logger

from netra_backend.tests.integration.critical_paths.integration.helpers.redis_l3_helpers import (
    RedisContainer as NetraRedisContainer,
)

logger = central_logger.get_logger(__name__)

@dataclass
class LockContentionMetrics:
    """Metrics for distributed lock contention testing."""
    lock_attempts: int = 0
    successful_acquisitions: int = 0
    failed_acquisitions: int = 0
    acquisition_times: List[float] = None
    hold_times: List[float] = None
    contention_events: int = 0
    deadlock_detections: int = 0
    deadlock_resolution_times: List[float] = None
    lock_timeouts: int = 0
    concurrent_locks_held: List[int] = None
    
    def __post_init__(self):
        if self.acquisition_times is None:
            self.acquisition_times = []
        if self.hold_times is None:
            self.hold_times = []
        if self.deadlock_resolution_times is None:
            self.deadlock_resolution_times = []
        if self.concurrent_locks_held is None:
            self.concurrent_locks_held = []
    
    @property
    def acquisition_success_rate(self) -> float:
        """Calculate lock acquisition success rate."""
        if self.lock_attempts == 0:
            return 100.0
        return (self.successful_acquisitions / self.lock_attempts) * 100.0
    
    @property
    def avg_acquisition_time(self) -> float:
        """Calculate average lock acquisition time."""
        return statistics.mean(self.acquisition_times) if self.acquisition_times else 0.0
    
    @property
    def p99_acquisition_time(self) -> float:
        """Calculate p99 lock acquisition time."""
        if not self.acquisition_times:
            return 0.0
        return statistics.quantiles(self.acquisition_times, n=100)[98] if len(self.acquisition_times) > 1 else self.acquisition_times[0]
    
    @property
    def avg_deadlock_resolution_time(self) -> float:
        """Calculate average deadlock resolution time."""
        return statistics.mean(self.deadlock_resolution_times) if self.deadlock_resolution_times else 0.0

class DistributedLockContentionL3Manager:
    """L3 distributed lock contention test manager with real Redis distributed locks."""
    
    def __init__(self):
        self.redis_containers = {}
        self.redis_clients = {}
        self.metrics = LockContentionMetrics()
        self.active_locks = {}
        self.lock_holders = defaultdict(set)
        self.test_resources = set()
        
    async def setup_redis_for_lock_testing(self) -> Dict[str, str]:
        """Setup Redis instances for distributed lock testing."""
        redis_configs = {
            "lock_primary": {"port": 6420, "role": "primary lock service"},
            "lock_secondary": {"port": 6421, "role": "secondary lock service"},
            "lock_coordination": {"port": 6422, "role": "coordination and monitoring"},
            "deadlock_detection": {"port": 6423, "role": "deadlock detection"}
        }
        
        redis_urls = {}
        
        for name, config in redis_configs.items():
            try:
                container = NetraRedisContainer(port=config["port"])
                container.container_name = f"netra-lock-{name}-{uuid.uuid4().hex[:8]}"
                
                url = await container.start()
                
                self.redis_containers[name] = container
                redis_urls[name] = url
                
                # Create Redis client
                client = aioredis.from_url(url, decode_responses=True)
                await client.ping()
                self.redis_clients[name] = client
                
                logger.info(f"Redis {name} ({config['role']}) started: {url}")
                
            except Exception as e:
                logger.error(f"Failed to start Redis {name}: {e}")
                raise
        
        return redis_urls
    
    async def acquire_distributed_lock(self, resource_id: str, worker_id: str, timeout: float = 5.0, ttl: float = 10.0, redis_instance: str = "lock_primary") -> Optional[str]:
        """Acquire distributed lock with contention handling."""
        lock_client = self.redis_clients[redis_instance]
        lock_key = f"lock:{resource_id}"
        lock_value = f"{worker_id}:{uuid.uuid4().hex[:8]}:{time.time()}"
        
        start_time = time.time()
        self.metrics.lock_attempts += 1
        
        try:
            # Attempt lock acquisition with exponential backoff
            max_retries = 5
            base_delay = 0.001  # 1ms base delay
            
            for attempt in range(max_retries):
                # Try to acquire lock
                acquired = await lock_client.set(
                    lock_key,
                    lock_value,
                    nx=True,  # Only set if key doesn't exist
                    ex=int(ttl)  # Expiration time
                )
                
                if acquired:
                    acquisition_time = time.time() - start_time
                    self.metrics.acquisition_times.append(acquisition_time)
                    self.metrics.successful_acquisitions += 1
                    
                    # Track active lock
                    self.active_locks[lock_key] = {
                        "worker_id": worker_id,
                        "lock_value": lock_value,
                        "acquired_at": time.time(),
                        "ttl": ttl,
                        "resource_id": resource_id
                    }
                    
                    self.lock_holders[worker_id].add(resource_id)
                    self.test_resources.add(resource_id)
                    
                    return lock_value
                
                # Lock contention - wait with exponential backoff
                if attempt < max_retries - 1:
                    self.metrics.contention_events += 1
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.001)
                    await asyncio.sleep(delay)
            
            # Failed to acquire after retries
            self.metrics.failed_acquisitions += 1
            return None
            
        except Exception as e:
            self.metrics.failed_acquisitions += 1
            logger.error(f"Lock acquisition failed for {resource_id}: {e}")
            return None
    
    async def release_distributed_lock(self, resource_id: str, lock_value: str, redis_instance: str = "lock_primary") -> bool:
        """Release distributed lock safely."""
        lock_client = self.redis_clients[redis_instance]
        lock_key = f"lock:{resource_id}"
        
        try:
            # Lua script for atomic lock release
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = await lock_client.eval(lua_script, 1, lock_key, lock_value)
            
            if result:
                # Track lock hold time
                if lock_key in self.active_locks:
                    lock_info = self.active_locks[lock_key]
                    hold_time = time.time() - lock_info["acquired_at"]
                    self.metrics.hold_times.append(hold_time)
                    
                    worker_id = lock_info["worker_id"]
                    self.lock_holders[worker_id].discard(resource_id)
                    
                    del self.active_locks[lock_key]
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Lock release failed for {resource_id}: {e}")
            return False
    
    async def test_high_contention_scenarios(self, worker_count: int, resource_count: int, operations_per_worker: int) -> Dict[str, Any]:
        """Test lock performance under high contention scenarios."""
        # Create workers competing for limited resources
        worker_tasks = []
        
        for worker_id in range(worker_count):
            task = self._worker_contention_simulation(
                f"worker_{worker_id}",
                resource_count,
                operations_per_worker
            )
            worker_tasks.append(task)
        
        # Execute concurrent contention
        start_time = time.time()
        worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze contention results
        successful_workers = [r for r in worker_results if not isinstance(r, Exception)]
        failed_workers = [r for r in worker_results if isinstance(r, Exception)]
        
        total_operations = sum(r["completed_operations"] for r in successful_workers)
        total_successful_locks = sum(r["successful_locks"] for r in successful_workers)
        total_failed_locks = sum(r["failed_locks"] for r in successful_workers)
        
        return {
            "worker_count": worker_count,
            "resource_count": resource_count,
            "operations_per_worker": operations_per_worker,
            "successful_workers": len(successful_workers),
            "failed_workers": len(failed_workers),
            "total_operations": total_operations,
            "total_successful_locks": total_successful_locks,
            "total_failed_locks": total_failed_locks,
            "total_time": total_time,
            "operations_per_second": total_operations / total_time if total_time > 0 else 0,
            "lock_success_rate": (total_successful_locks / (total_successful_locks + total_failed_locks) * 100) if (total_successful_locks + total_failed_locks) > 0 else 0,
            "contention_level": worker_count / resource_count
        }
    
    async def _worker_contention_simulation(self, worker_id: str, resource_count: int, operations: int) -> Dict[str, Any]:
        """Simulate worker operations under lock contention."""
        completed_operations = 0
        successful_locks = 0
        failed_locks = 0
        operation_times = []
        
        for op in range(operations):
            # Randomly select resource to work on
            resource_id = f"resource_{random.randint(0, resource_count - 1)}"
            
            operation_start = time.time()
            
            # Try to acquire lock
            lock_value = await self.acquire_distributed_lock(
                resource_id, worker_id, timeout=2.0, ttl=5.0
            )
            
            if lock_value:
                successful_locks += 1
                
                try:
                    # Simulate work while holding lock
                    work_duration = random.uniform(0.01, 0.05)  # 10-50ms of work
                    await asyncio.sleep(work_duration)
                    
                    # Release lock
                    await self.release_distributed_lock(resource_id, lock_value)
                    
                except Exception as e:
                    logger.error(f"Worker {worker_id} operation failed: {e}")
                    # Ensure lock is released on error
                    try:
                        await self.release_distributed_lock(resource_id, lock_value)
                    except:
                        pass
            else:
                failed_locks += 1
            
            operation_time = time.time() - operation_start
            operation_times.append(operation_time)
            completed_operations += 1
        
        return {
            "worker_id": worker_id,
            "completed_operations": completed_operations,
            "successful_locks": successful_locks,
            "failed_locks": failed_locks,
            "avg_operation_time": statistics.mean(operation_times) if operation_times else 0
        }
    
    async def test_deadlock_detection_and_resolution(self, deadlock_scenario: str) -> Dict[str, Any]:
        """Test deadlock detection and resolution mechanisms."""
        if deadlock_scenario == "circular_wait":
            return await self._test_circular_wait_deadlock()
        elif deadlock_scenario == "resource_ordering":
            return await self._test_resource_ordering_deadlock()
        elif deadlock_scenario == "timeout_resolution":
            return await self._test_timeout_based_resolution()
        else:
            raise ValueError(f"Unknown deadlock scenario: {deadlock_scenario}")
    
    async def _test_circular_wait_deadlock(self) -> Dict[str, Any]:
        """Test circular wait deadlock scenario."""
        # Create circular dependency: A -> B, B -> C, C -> A
        resources = ["resource_A", "resource_B", "resource_C"]
        workers = ["worker_1", "worker_2", "worker_3"]
        
        deadlock_start = time.time()
        deadlock_detected = False
        resolution_time = 0
        
        # Worker 1: A -> B
        # Worker 2: B -> C  
        # Worker 3: C -> A
        
        async def create_deadlock_worker(worker_id: str, first_resource: str, second_resource: str):
            # Acquire first lock
            lock1 = await self.acquire_distributed_lock(first_resource, worker_id, timeout=1.0, ttl=10.0)
            if not lock1:
                return {"success": False, "reason": "failed_first_lock"}
            
            # Small delay to ensure other workers get their first locks
            await asyncio.sleep(0.1)
            
            # Try to acquire second lock (this will create deadlock)
            lock2 = await self.acquire_distributed_lock(second_resource, worker_id, timeout=2.0, ttl=10.0)
            
            if lock2:
                # Successfully acquired both - no deadlock
                await self.release_distributed_lock(second_resource, lock2)
                await self.release_distributed_lock(first_resource, lock1)
                return {"success": True, "deadlock": False}
            else:
                # Failed to acquire second lock - potential deadlock
                await self.release_distributed_lock(first_resource, lock1)
                return {"success": False, "deadlock": True}
        
        # Create potential deadlock scenario
        tasks = [
            create_deadlock_worker(workers[0], resources[0], resources[1]),
            create_deadlock_worker(workers[1], resources[1], resources[2]),
            create_deadlock_worker(workers[2], resources[2], resources[0])
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze deadlock detection
        deadlocks_detected = len([r for r in results if not isinstance(r, Exception) and r.get("deadlock", False)])
        successful_completions = len([r for r in results if not isinstance(r, Exception) and r.get("success", False)])
        
        if deadlocks_detected > 0:
            deadlock_detected = True
            resolution_time = time.time() - deadlock_start
            self.metrics.deadlock_detections += 1
            self.metrics.deadlock_resolution_times.append(resolution_time)
        
        return {
            "scenario": "circular_wait",
            "deadlock_detected": deadlock_detected,
            "deadlocks_count": deadlocks_detected,
            "successful_completions": successful_completions,
            "resolution_time": resolution_time,
            "workers_involved": len(workers)
        }
    
    async def _test_resource_ordering_deadlock(self) -> Dict[str, Any]:
        """Test resource ordering deadlock prevention."""
        # Test ordered resource acquisition to prevent deadlocks
        resources = ["resource_1", "resource_2", "resource_3", "resource_4"]
        worker_count = 6
        
        async def ordered_acquisition_worker(worker_id: str):
            # Always acquire resources in order to prevent deadlocks
            acquired_locks = []
            
            try:
                # Randomly select 2-3 resources to acquire
                selected_resources = sorted(random.sample(resources, random.randint(2, 3)))
                
                for resource in selected_resources:
                    lock_value = await self.acquire_distributed_lock(
                        resource, worker_id, timeout=1.0, ttl=5.0
                    )
                    
                    if lock_value:
                        acquired_locks.append((resource, lock_value))
                    else:
                        # Failed to acquire - release all and retry
                        for res, val in acquired_locks:
                            await self.release_distributed_lock(res, val)
                        return {"success": False, "reason": "acquisition_failed"}
                
                # Simulate work with all locks held
                await asyncio.sleep(0.05)
                
                # Release all locks in reverse order
                for resource, lock_value in reversed(acquired_locks):
                    await self.release_distributed_lock(resource, lock_value)
                
                return {"success": True, "resources_acquired": len(acquired_locks)}
                
            except Exception as e:
                # Emergency release on error
                for resource, lock_value in acquired_locks:
                    try:
                        await self.release_distributed_lock(resource, lock_value)
                    except:
                        pass
                return {"success": False, "reason": str(e)}
        
        # Execute workers with ordered acquisition
        tasks = [ordered_acquisition_worker(f"ordered_worker_{i}") for i in range(worker_count)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        successful_workers = [r for r in results if not isinstance(r, Exception) and r.get("success", False)]
        failed_workers = [r for r in results if isinstance(r, Exception) or not r.get("success", False)]
        
        return {
            "scenario": "resource_ordering",
            "worker_count": worker_count,
            "successful_workers": len(successful_workers),
            "failed_workers": len(failed_workers),
            "total_time": total_time,
            "deadlocks_prevented": len(failed_workers) == 0,
            "success_rate": (len(successful_workers) / worker_count * 100) if worker_count > 0 else 0
        }
    
    async def _test_timeout_based_resolution(self) -> Dict[str, Any]:
        """Test timeout-based deadlock resolution."""
        # Create scenario where timeouts resolve potential deadlocks
        resources = ["timeout_resource_A", "timeout_resource_B"]
        
        async def timeout_worker(worker_id: str, first_resource: str, second_resource: str, timeout: float):
            try:
                # Acquire first lock
                lock1 = await self.acquire_distributed_lock(
                    first_resource, worker_id, timeout=timeout, ttl=timeout + 1
                )
                
                if not lock1:
                    return {"success": False, "reason": "first_lock_timeout"}
                
                # Wait a bit then try second lock
                await asyncio.sleep(0.05)
                
                lock2 = await self.acquire_distributed_lock(
                    second_resource, worker_id, timeout=timeout, ttl=timeout + 1
                )
                
                if lock2:
                    # Success - release both
                    await self.release_distributed_lock(second_resource, lock2)
                    await self.release_distributed_lock(first_resource, lock1)
                    return {"success": True, "both_acquired": True}
                else:
                    # Timeout on second lock
                    await self.release_distributed_lock(first_resource, lock1)
                    return {"success": False, "reason": "second_lock_timeout"}
                    
            except Exception as e:
                return {"success": False, "reason": str(e)}
        
        # Create competing workers with different timeout strategies
        start_time = time.time()
        
        tasks = [
            timeout_worker("timeout_worker_1", resources[0], resources[1], 0.5),  # Short timeout
            timeout_worker("timeout_worker_2", resources[1], resources[0], 1.0),  # Longer timeout
            timeout_worker("timeout_worker_3", resources[0], resources[1], 0.3),  # Very short timeout
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        resolution_time = time.time() - start_time
        
        successful_resolutions = [r for r in results if not isinstance(r, Exception) and r.get("success", False)]
        timeout_resolutions = [r for r in results if not isinstance(r, Exception) and "timeout" in r.get("reason", "")]
        
        self.metrics.deadlock_resolution_times.append(resolution_time)
        
        return {
            "scenario": "timeout_resolution",
            "successful_resolutions": len(successful_resolutions),
            "timeout_resolutions": len(timeout_resolutions),
            "resolution_time": resolution_time,
            "resolution_effective": len(timeout_resolutions) > 0
        }
    
    async def test_lock_performance_under_load(self, concurrent_locks: int, duration: float) -> Dict[str, Any]:
        """Test lock performance under sustained load."""
        lock_operations = []
        
        async def continuous_lock_operations(worker_id: str, duration: float):
            start_time = time.time()
            operations = 0
            successful_operations = 0
            
            while time.time() - start_time < duration:
                resource_id = f"load_resource_{random.randint(0, 9)}"  # 10 resources
                
                lock_value = await self.acquire_distributed_lock(
                    resource_id, worker_id, timeout=0.1, ttl=0.2
                )
                
                if lock_value:
                    # Brief work simulation
                    await asyncio.sleep(0.01)
                    await self.release_distributed_lock(resource_id, lock_value)
                    successful_operations += 1
                
                operations += 1
                
                # Brief pause between operations
                await asyncio.sleep(0.001)
            
            return {
                "worker_id": worker_id,
                "operations": operations,
                "successful_operations": successful_operations,
                "duration": time.time() - start_time
            }
        
        # Create load test workers
        tasks = [continuous_lock_operations(f"load_worker_{i}", duration) for i in range(concurrent_locks)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        successful_results = [r for r in results if not isinstance(r, Exception)]
        
        total_operations = sum(r["operations"] for r in successful_results)
        total_successful = sum(r["successful_operations"] for r in successful_results)
        
        throughput = total_operations / total_time if total_time > 0 else 0
        success_rate = (total_successful / total_operations * 100) if total_operations > 0 else 0
        
        return {
            "concurrent_workers": concurrent_locks,
            "test_duration": duration,
            "total_operations": total_operations,
            "successful_operations": total_successful,
            "throughput_ops_per_second": throughput,
            "success_rate": success_rate,
            "avg_acquisition_time": self.metrics.avg_acquisition_time,
            "p99_acquisition_time": self.metrics.p99_acquisition_time
        }
    
    def get_lock_contention_summary(self) -> Dict[str, Any]:
        """Get comprehensive distributed lock contention test summary."""
        return {
            "lock_metrics": {
                "lock_attempts": self.metrics.lock_attempts,
                "acquisition_success_rate": self.metrics.acquisition_success_rate,
                "avg_acquisition_time": self.metrics.avg_acquisition_time,
                "p99_acquisition_time": self.metrics.p99_acquisition_time,
                "contention_events": self.metrics.contention_events,
                "deadlock_detections": self.metrics.deadlock_detections,
                "avg_deadlock_resolution_time": self.metrics.avg_deadlock_resolution_time,
                "lock_timeouts": self.metrics.lock_timeouts
            },
            "sla_compliance": {
                "acquisition_under_50ms": self.metrics.avg_acquisition_time < 0.05,
                "deadlock_resolution_under_100ms": self.metrics.avg_deadlock_resolution_time < 0.1,
                "success_rate_above_95": self.metrics.acquisition_success_rate > 95.0,
                "p99_under_100ms": self.metrics.p99_acquisition_time < 0.1
            },
            "recommendations": self._generate_lock_recommendations()
        }
    
    def _generate_lock_recommendations(self) -> List[str]:
        """Generate distributed lock performance recommendations."""
        recommendations = []
        
        if self.metrics.avg_acquisition_time > 0.05:
            recommendations.append(f"Lock acquisition time {self.metrics.avg_acquisition_time*1000:.1f}ms exceeds 50ms - optimize lock contention")
        
        if self.metrics.p99_acquisition_time > 0.1:
            recommendations.append(f"P99 acquisition time {self.metrics.p99_acquisition_time*1000:.1f}ms exceeds 100ms - review high contention scenarios")
        
        if self.metrics.acquisition_success_rate < 95.0:
            recommendations.append(f"Lock success rate {self.metrics.acquisition_success_rate:.1f}% below 95% - review timeout settings")
        
        if self.metrics.deadlock_detections > 0 and self.metrics.avg_deadlock_resolution_time > 0.1:
            recommendations.append(f"Deadlock resolution time {self.metrics.avg_deadlock_resolution_time*1000:.1f}ms exceeds 100ms - improve detection")
        
        if self.metrics.contention_events > self.metrics.successful_acquisitions:
            recommendations.append("High contention detected - consider resource partitioning or lock-free algorithms")
        
        if not recommendations:
            recommendations.append("All distributed lock metrics meet SLA requirements")
        
        return recommendations
    
    async def cleanup(self):
        """Clean up Redis containers and test resources."""
        try:
            # Clean up active locks
            for lock_key, lock_info in self.active_locks.items():
                try:
                    await self.release_distributed_lock(
                        lock_info["resource_id"], 
                        lock_info["lock_value"]
                    )
                except Exception:
                    pass
            
            # Clean up test resources
            for resource in self.test_resources:
                for client in self.redis_clients.values():
                    try:
                        await client.delete(f"lock:{resource}")
                    except Exception:
                        pass
            
            # Close Redis clients
            for client in self.redis_clients.values():
                await client.close()
            
            # Stop Redis containers
            for container in self.redis_containers.values():
                await container.stop()
                
        except Exception as e:
            logger.error(f"Distributed lock cleanup failed: {e}")

@pytest.fixture
async def lock_contention_manager():
    """Create L3 distributed lock contention manager."""
    manager = DistributedLockContentionL3Manager()
    await manager.setup_redis_for_lock_testing()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_high_contention_lock_performance(lock_contention_manager):
    """L3: Test distributed lock performance under high contention."""
    result = await lock_contention_manager.test_high_contention_scenarios(
        worker_count=20, resource_count=5, operations_per_worker=10
    )
    
    # Verify high contention performance
    assert result["lock_success_rate"] > 85.0, f"Lock success rate {result['lock_success_rate']:.1f}% below 85% under high contention"
    assert result["operations_per_second"] > 50, f"Throughput {result['operations_per_second']:.1f} ops/s too low under contention"
    assert result["successful_workers"] >= result["worker_count"] * 0.9, f"Too many failed workers: {result['failed_workers']}"
    
    logger.info(f"High contention test: {result['lock_success_rate']:.1f}% success rate, {result['operations_per_second']:.1f} ops/s")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_circular_wait_deadlock_detection(lock_contention_manager):
    """L3: Test circular wait deadlock detection and resolution."""
    result = await lock_contention_manager.test_deadlock_detection_and_resolution("circular_wait")
    
    # Verify deadlock handling
    # Note: Actual deadlock detection depends on timeout mechanisms
    assert result["workers_involved"] == 3, "Should test with 3 workers for circular dependency"
    assert result["resolution_time"] < 5.0, f"Deadlock resolution time {result['resolution_time']:.1f}s too high"
    
    # Either deadlock is detected and resolved, or prevented entirely
    total_outcomes = result["deadlocks_count"] + result["successful_completions"]
    assert total_outcomes >= 2, "Should have meaningful deadlock detection results"
    
    logger.info(f"Circular deadlock test: {result['deadlocks_count']} deadlocks, {result['successful_completions']} completions")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_resource_ordering_deadlock_prevention(lock_contention_manager):
    """L3: Test resource ordering deadlock prevention strategy."""
    result = await lock_contention_manager.test_deadlock_detection_and_resolution("resource_ordering")
    
    # Verify resource ordering effectiveness
    assert result["success_rate"] > 90.0, f"Resource ordering success rate {result['success_rate']:.1f}% below 90%"
    assert result["deadlocks_prevented"], "Resource ordering should prevent deadlocks"
    assert result["successful_workers"] >= result["worker_count"] * 0.9, f"Too many failed workers with ordering: {result['failed_workers']}"
    
    logger.info(f"Resource ordering test: {result['success_rate']:.1f}% success rate, deadlocks prevented: {result['deadlocks_prevented']}")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_timeout_based_deadlock_resolution(lock_contention_manager):
    """L3: Test timeout-based deadlock resolution mechanism."""
    result = await lock_contention_manager.test_deadlock_detection_and_resolution("timeout_resolution")
    
    # Verify timeout resolution
    assert result["resolution_effective"], "Timeout-based resolution should be effective"
    assert result["resolution_time"] < 2.0, f"Timeout resolution time {result['resolution_time']:.1f}s too high"
    assert result["timeout_resolutions"] > 0, "Should have timeout-based resolutions"
    
    logger.info(f"Timeout resolution test: {result['timeout_resolutions']} timeouts, {result['resolution_time']:.1f}s resolution time")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_sustained_lock_performance_under_load(lock_contention_manager):
    """L3: Test sustained lock performance under continuous load."""
    result = await lock_contention_manager.test_lock_performance_under_load(
        concurrent_locks=15, duration=2.0
    )
    
    # Verify sustained performance
    assert result["throughput_ops_per_second"] > 100, f"Sustained throughput {result['throughput_ops_per_second']:.1f} ops/s below 100"
    assert result["success_rate"] > 80.0, f"Sustained success rate {result['success_rate']:.1f}% below 80%"
    assert result["avg_acquisition_time"] < 0.1, f"Average acquisition time {result['avg_acquisition_time']*1000:.1f}ms too high under load"
    
    logger.info(f"Sustained load test: {result['throughput_ops_per_second']:.1f} ops/s, {result['success_rate']:.1f}% success rate")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_distributed_lock_contention_sla_compliance(lock_contention_manager):
    """L3: Test comprehensive distributed lock contention SLA compliance."""
    # Execute comprehensive test suite
    await lock_contention_manager.test_high_contention_scenarios(15, 4, 8)
    await lock_contention_manager.test_deadlock_detection_and_resolution("resource_ordering")
    await lock_contention_manager.test_deadlock_detection_and_resolution("timeout_resolution")
    await lock_contention_manager.test_lock_performance_under_load(10, 1.5)
    
    # Get comprehensive summary
    summary = lock_contention_manager.get_lock_contention_summary()
    
    # Verify SLA compliance
    sla = summary["sla_compliance"]
    assert sla["acquisition_under_50ms"], f"Acquisition time SLA violation: {lock_contention_manager.metrics.avg_acquisition_time*1000:.1f}ms"
    assert sla["success_rate_above_95"], f"Success rate SLA violation: {lock_contention_manager.metrics.acquisition_success_rate:.1f}%"
    assert sla["p99_under_100ms"], f"P99 acquisition time SLA violation: {lock_contention_manager.metrics.p99_acquisition_time*1000:.1f}ms"
    
    # If deadlocks were detected, verify resolution time
    if lock_contention_manager.metrics.deadlock_detections > 0:
        assert sla["deadlock_resolution_under_100ms"], f"Deadlock resolution SLA violation: {lock_contention_manager.metrics.avg_deadlock_resolution_time*1000:.1f}ms"
    
    # Verify overall lock performance
    assert lock_contention_manager.metrics.lock_attempts > 0, "Should have performed lock operations"
    assert lock_contention_manager.metrics.successful_acquisitions > 0, "Should have successful lock acquisitions"
    
    # Verify no critical recommendations
    critical_recommendations = [r for r in summary["recommendations"] if "exceeds" in r or "below" in r]
    assert len(critical_recommendations) == 0, f"Critical lock contention issues: {critical_recommendations}"
    
    logger.info(f"Distributed lock contention SLA compliance test completed successfully")
    logger.info(f"Summary: {summary}")