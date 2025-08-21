"""Job Concurrency Limits L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise customers with high-volume concurrent AI workloads
- Business Goal: Prevent system overload while maximizing throughput
- Value Impact: Optimal resource utilization prevents performance degradation
- Strategic Impact: $10K MRR - Concurrency management and system stability

Critical Path: Worker allocation -> Concurrency enforcement -> Resource management -> Performance optimization
Coverage: Real worker pool management, Redis-based concurrency control, resource limits, throughput measurement

L3 Integration Test Level:
- Tests real Redis-based concurrency control mechanisms
- Uses actual worker pool limits and management
- Validates resource allocation under concurrent load
- Measures actual performance metrics and limits
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import uuid
import json
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, deque
from dataclasses import dataclass

# Add project root to path

from netra_backend.app.services.websocket.message_queue import MessageQueue, QueuedMessage, MessagePriority, MessageStatus
from redis_manager import redis_manager
from logging_config import central_logger

# Add project root to path

logger = central_logger.get_logger(__name__)


@dataclass
class ConcurrencyMetrics:
    """Tracks concurrency metrics for analysis."""
    max_concurrent_jobs: int = 0
    total_jobs_processed: int = 0
    concurrent_violations: int = 0
    resource_exhaustion_events: int = 0
    average_queue_time: float = 0.0
    average_processing_time: float = 0.0
    throughput_per_second: float = 0.0


class JobConcurrencyLimitsL3Manager:
    """Manages L3 job concurrency limits tests with real infrastructure."""
    
    def __init__(self):
        self.message_queue = MessageQueue()
        self.active_jobs: Set[str] = set()
        self.completed_jobs: List[Dict[str, Any]] = []
        self.concurrency_events = []
        self.resource_usage_log = []
        self.max_concurrent_workers = 5
        self.max_jobs_per_user = 3
        self.current_worker_count = 0
        self.worker_assignments: Dict[str, str] = {}  # job_id -> worker_id
        self.worker_utilization: Dict[str, List[float]] = defaultdict(list)
        
    async def initialize_test_infrastructure(self):
        """Initialize real concurrency control infrastructure."""
        try:
            # Clear any existing concurrency data
            await self.clear_concurrency_test_data()
            
            # Initialize concurrency control in Redis
            await redis_manager.set("max_concurrent_workers", self.max_concurrent_workers)
            await redis_manager.set("max_jobs_per_user", self.max_jobs_per_user)
            await redis_manager.set("current_active_jobs", 0)
            
            # Register handlers for different job types with concurrency tracking
            self.message_queue.register_handler("cpu_intensive_job", self.handle_cpu_intensive_job)
            self.message_queue.register_handler("memory_intensive_job", self.handle_memory_intensive_job)
            self.message_queue.register_handler("io_intensive_job", self.handle_io_intensive_job)
            self.message_queue.register_handler("quick_job", self.handle_quick_job)
            
            logger.info("L3 concurrency limits infrastructure initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize L3 concurrency test infrastructure: {e}")
            raise
    
    async def clear_concurrency_test_data(self):
        """Clear all concurrency-related test data from Redis."""
        patterns = [
            "concurrency:*", "worker:*", "user_jobs:*", 
            "active_jobs:*", "resource_usage:*", "job_assignment:*"
        ]
        for pattern in patterns:
            keys = await redis_manager.keys(pattern)
            if keys:
                await redis_manager.delete(*keys)
    
    async def acquire_worker_slot(self, job_id: str, user_id: str) -> Optional[str]:
        """Acquire a worker slot with concurrency limits enforcement."""
        # Check global worker limit
        current_workers = await redis_manager.get("current_active_jobs")
        current_workers = int(current_workers) if current_workers else 0
        
        if current_workers >= self.max_concurrent_workers:
            logger.warning(f"Worker limit reached: {current_workers}/{self.max_concurrent_workers}")
            return None
        
        # Check per-user job limit
        user_jobs_key = f"user_jobs:{user_id}"
        user_job_count = await redis_manager.scard(user_jobs_key)
        
        if user_job_count >= self.max_jobs_per_user:
            logger.warning(f"User {user_id} job limit reached: {user_job_count}/{self.max_jobs_per_user}")
            return None
        
        # Acquire slot
        worker_id = f"worker_{current_workers + 1}"
        
        # Atomically increment worker count and assign job
        pipe = redis_manager.pipeline()
        pipe.incr("current_active_jobs")
        pipe.sadd(user_jobs_key, job_id)
        pipe.set(f"job_assignment:{job_id}", worker_id, ex=300)
        pipe.set(f"worker:{worker_id}:job", job_id, ex=300)
        await pipe.execute()
        
        self.active_jobs.add(job_id)
        self.worker_assignments[job_id] = worker_id
        self.current_worker_count = current_workers + 1
        
        logger.info(f"Acquired worker {worker_id} for job {job_id} (user: {user_id})")
        return worker_id
    
    async def release_worker_slot(self, job_id: str, user_id: str, worker_id: str):
        """Release worker slot and update concurrency tracking."""
        # Release slot atomically
        pipe = redis_manager.pipeline()
        pipe.decr("current_active_jobs")
        pipe.srem(f"user_jobs:{user_id}", job_id)
        pipe.delete(f"job_assignment:{job_id}")
        pipe.delete(f"worker:{worker_id}:job")
        await pipe.execute()
        
        self.active_jobs.discard(job_id)
        self.worker_assignments.pop(job_id, None)
        self.current_worker_count = max(0, self.current_worker_count - 1)
        
        logger.info(f"Released worker {worker_id} for job {job_id}")
    
    async def handle_cpu_intensive_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle CPU-intensive job with concurrency control."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        start_time = time.time()
        
        # Try to acquire worker slot
        worker_id = await self.acquire_worker_slot(job_id, user_id)
        if not worker_id:
            # Job rejected due to concurrency limits
            self.concurrency_events.append({
                "job_id": job_id,
                "event": "rejected",
                "reason": "worker_limit_reached",
                "timestamp": time.time(),
                "user_id": user_id
            })
            raise Exception("Worker limit reached - job rejected")
        
        try:
            # Record job start
            self.concurrency_events.append({
                "job_id": job_id,
                "event": "started",
                "worker_id": worker_id,
                "timestamp": time.time(),
                "user_id": user_id,
                "job_type": "cpu_intensive"
            })
            
            # Simulate CPU-intensive processing
            await asyncio.sleep(0.8)  # Simulate heavy CPU work
            
            processing_time = time.time() - start_time
            
            # Record completion
            self.completed_jobs.append({
                "job_id": job_id,
                "job_type": "cpu_intensive",
                "worker_id": worker_id,
                "user_id": user_id,
                "processing_time": processing_time,
                "completed_at": time.time()
            })
            
            self.concurrency_events.append({
                "job_id": job_id,
                "event": "completed",
                "worker_id": worker_id,
                "timestamp": time.time(),
                "processing_time": processing_time
            })
            
            logger.info(f"CPU intensive job {job_id} completed on {worker_id} in {processing_time:.3f}s")
            
        finally:
            # Always release worker slot
            await self.release_worker_slot(job_id, user_id, worker_id)
    
    async def handle_memory_intensive_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle memory-intensive job with concurrency control."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        start_time = time.time()
        
        worker_id = await self.acquire_worker_slot(job_id, user_id)
        if not worker_id:
            self.concurrency_events.append({
                "job_id": job_id,
                "event": "rejected",
                "reason": "worker_limit_reached",
                "timestamp": time.time(),
                "user_id": user_id
            })
            raise Exception("Worker limit reached - job rejected")
        
        try:
            self.concurrency_events.append({
                "job_id": job_id,
                "event": "started",
                "worker_id": worker_id,
                "timestamp": time.time(),
                "user_id": user_id,
                "job_type": "memory_intensive"
            })
            
            # Simulate memory-intensive processing
            await asyncio.sleep(0.6)
            
            processing_time = time.time() - start_time
            
            self.completed_jobs.append({
                "job_id": job_id,
                "job_type": "memory_intensive",
                "worker_id": worker_id,
                "user_id": user_id,
                "processing_time": processing_time,
                "completed_at": time.time()
            })
            
            self.concurrency_events.append({
                "job_id": job_id,
                "event": "completed",
                "worker_id": worker_id,
                "timestamp": time.time(),
                "processing_time": processing_time
            })
            
            logger.info(f"Memory intensive job {job_id} completed on {worker_id} in {processing_time:.3f}s")
            
        finally:
            await self.release_worker_slot(job_id, user_id, worker_id)
    
    async def handle_io_intensive_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle IO-intensive job with concurrency control."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        start_time = time.time()
        
        worker_id = await self.acquire_worker_slot(job_id, user_id)
        if not worker_id:
            self.concurrency_events.append({
                "job_id": job_id,
                "event": "rejected",
                "reason": "worker_limit_reached",
                "timestamp": time.time(),
                "user_id": user_id
            })
            raise Exception("Worker limit reached - job rejected")
        
        try:
            self.concurrency_events.append({
                "job_id": job_id,
                "event": "started",
                "worker_id": worker_id,
                "timestamp": time.time(),
                "user_id": user_id,
                "job_type": "io_intensive"
            })
            
            # Simulate IO-intensive processing
            await asyncio.sleep(0.4)
            
            processing_time = time.time() - start_time
            
            self.completed_jobs.append({
                "job_id": job_id,
                "job_type": "io_intensive",
                "worker_id": worker_id,
                "user_id": user_id,
                "processing_time": processing_time,
                "completed_at": time.time()
            })
            
            self.concurrency_events.append({
                "job_id": job_id,
                "event": "completed",
                "worker_id": worker_id,
                "timestamp": time.time(),
                "processing_time": processing_time
            })
            
            logger.info(f"IO intensive job {job_id} completed on {worker_id} in {processing_time:.3f}s")
            
        finally:
            await self.release_worker_slot(job_id, user_id, worker_id)
    
    async def handle_quick_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle quick job with concurrency control."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        start_time = time.time()
        
        worker_id = await self.acquire_worker_slot(job_id, user_id)
        if not worker_id:
            self.concurrency_events.append({
                "job_id": job_id,
                "event": "rejected",
                "reason": "worker_limit_reached",
                "timestamp": time.time(),
                "user_id": user_id
            })
            raise Exception("Worker limit reached - job rejected")
        
        try:
            self.concurrency_events.append({
                "job_id": job_id,
                "event": "started",
                "worker_id": worker_id,
                "timestamp": time.time(),
                "user_id": user_id,
                "job_type": "quick"
            })
            
            # Simulate quick processing
            await asyncio.sleep(0.1)
            
            processing_time = time.time() - start_time
            
            self.completed_jobs.append({
                "job_id": job_id,
                "job_type": "quick",
                "worker_id": worker_id,
                "user_id": user_id,
                "processing_time": processing_time,
                "completed_at": time.time()
            })
            
            self.concurrency_events.append({
                "job_id": job_id,
                "event": "completed",
                "worker_id": worker_id,
                "timestamp": time.time(),
                "processing_time": processing_time
            })
            
            logger.info(f"Quick job {job_id} completed on {worker_id} in {processing_time:.3f}s")
            
        finally:
            await self.release_worker_slot(job_id, user_id, worker_id)
    
    async def enqueue_concurrent_test_jobs(self, job_count: int, users: List[str], job_types: List[str]) -> List[str]:
        """Enqueue jobs for concurrency testing."""
        job_ids = []
        
        for i in range(job_count):
            job_id = str(uuid.uuid4())
            user_id = users[i % len(users)]
            job_type = job_types[i % len(job_types)]
            
            message = QueuedMessage(
                user_id=user_id,
                type=job_type,
                payload={"job_id": job_id, "test_index": i},
                priority=MessagePriority.NORMAL
            )
            
            success = await self.message_queue.enqueue(message)
            assert success, f"Failed to enqueue job {job_id}"
            job_ids.append(job_id)
        
        return job_ids
    
    async def monitor_concurrency_metrics(self, duration: float = 5.0) -> ConcurrencyMetrics:
        """Monitor concurrency metrics during job processing."""
        start_time = time.time()
        max_concurrent = 0
        concurrent_samples = []
        
        while time.time() - start_time < duration:
            current_active = await redis_manager.get("current_active_jobs")
            current_active = int(current_active) if current_active else 0
            
            max_concurrent = max(max_concurrent, current_active)
            concurrent_samples.append(current_active)
            
            # Log resource usage
            self.resource_usage_log.append({
                "timestamp": time.time(),
                "active_jobs": current_active,
                "worker_slots_used": current_active
            })
            
            await asyncio.sleep(0.1)
        
        # Calculate metrics
        total_jobs = len(self.completed_jobs)
        rejected_jobs = len([e for e in self.concurrency_events if e["event"] == "rejected"])
        
        processing_times = [job["processing_time"] for job in self.completed_jobs]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        throughput = total_jobs / duration if duration > 0 else 0
        
        return ConcurrencyMetrics(
            max_concurrent_jobs=max_concurrent,
            total_jobs_processed=total_jobs,
            concurrent_violations=rejected_jobs,
            average_processing_time=avg_processing_time,
            throughput_per_second=throughput
        )
    
    async def validate_concurrency_limits_enforcement(self) -> Dict[str, Any]:
        """Validate that concurrency limits were properly enforced."""
        violations = []
        
        # Check for worker limit violations
        for event in self.concurrency_events:
            if event["event"] == "started":
                # Count concurrent jobs at this timestamp
                concurrent_at_start = len([
                    e for e in self.concurrency_events 
                    if e["event"] == "started" and 
                    e["timestamp"] <= event["timestamp"] and
                    not any(comp["job_id"] == e["job_id"] and comp["timestamp"] <= event["timestamp"] 
                           for comp in self.concurrency_events if comp["event"] == "completed")
                ])
                
                if concurrent_at_start > self.max_concurrent_workers:
                    violations.append({
                        "type": "worker_limit",
                        "job_id": event["job_id"],
                        "concurrent_count": concurrent_at_start,
                        "limit": self.max_concurrent_workers,
                        "timestamp": event["timestamp"]
                    })
        
        # Check for per-user limit violations
        user_job_counts = defaultdict(int)
        for event in sorted(self.concurrency_events, key=lambda x: x["timestamp"]):
            if event["event"] == "started":
                user_job_counts[event["user_id"]] += 1
                if user_job_counts[event["user_id"]] > self.max_jobs_per_user:
                    violations.append({
                        "type": "user_limit",
                        "user_id": event["user_id"],
                        "job_count": user_job_counts[event["user_id"]],
                        "limit": self.max_jobs_per_user,
                        "timestamp": event["timestamp"]
                    })
            elif event["event"] == "completed":
                user_job_counts[event["user_id"]] = max(0, user_job_counts[event["user_id"]] - 1)
        
        return {
            "violations": violations,
            "total_violations": len(violations),
            "limits_enforced": len(violations) == 0
        }
    
    async def cleanup_test_infrastructure(self):
        """Clean up concurrency test infrastructure."""
        try:
            await self.message_queue.stop_processing()
            await self.clear_concurrency_test_data()
            logger.info("L3 concurrency test cleanup completed")
        except Exception as e:
            logger.error(f"Concurrency test cleanup failed: {e}")


@pytest.fixture
async def concurrency_limits_manager():
    """Create concurrency limits manager for L3 testing."""
    manager = JobConcurrencyLimitsL3Manager()
    await manager.initialize_test_infrastructure()
    yield manager
    await manager.cleanup_test_infrastructure()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_basic_worker_concurrency_limits_l3(concurrency_limits_manager):
    """Test basic worker concurrency limits enforcement."""
    # Enqueue more jobs than worker limit allows
    users = ["user1", "user2", "user3"]
    job_types = ["cpu_intensive_job", "memory_intensive_job"]
    
    job_ids = await concurrency_limits_manager.enqueue_concurrent_test_jobs(10, users, job_types)
    
    # Start processing with limited workers
    processing_task = asyncio.create_task(
        concurrency_limits_manager.message_queue.process_queue(worker_count=3)
    )
    
    # Monitor concurrency
    metrics = await concurrency_limits_manager.monitor_concurrency_metrics(6.0)
    
    # Stop processing
    await concurrency_limits_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate concurrency limits
    validation = await concurrency_limits_manager.validate_concurrency_limits_enforcement()
    
    assert validation["limits_enforced"], f"Concurrency limits violated: {validation['violations']}"
    assert metrics.max_concurrent_jobs <= concurrency_limits_manager.max_concurrent_workers, \
        f"Worker limit exceeded: {metrics.max_concurrent_jobs}"
    assert metrics.total_jobs_processed >= 5, "Insufficient job processing"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_per_user_job_limits_l3(concurrency_limits_manager):
    """Test per-user job concurrency limits."""
    # Create scenario where one user tries to exceed their limit
    heavy_user_jobs = []
    other_user_jobs = []
    
    # Heavy user tries to submit many jobs
    for i in range(6):  # More than max_jobs_per_user (3)
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id="heavy_user",
            type="cpu_intensive_job",
            payload={"job_id": job_id},
            priority=MessagePriority.NORMAL
        )
        await concurrency_limits_manager.message_queue.enqueue(message)
        heavy_user_jobs.append(job_id)
    
    # Other users submit normal loads
    for i in range(4):
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id=f"normal_user_{i}",
            type="io_intensive_job",
            payload={"job_id": job_id},
            priority=MessagePriority.NORMAL
        )
        await concurrency_limits_manager.message_queue.enqueue(message)
        other_user_jobs.append(job_id)
    
    # Start processing
    processing_task = asyncio.create_task(
        concurrency_limits_manager.message_queue.process_queue(worker_count=4)
    )
    
    # Monitor processing
    metrics = await concurrency_limits_manager.monitor_concurrency_metrics(8.0)
    
    # Stop processing
    await concurrency_limits_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate per-user limits
    validation = await concurrency_limits_manager.validate_concurrency_limits_enforcement()
    
    assert validation["limits_enforced"], f"Per-user limits violated: {validation['violations']}"
    
    # Check that heavy user was limited but other users processed normally
    heavy_user_completed = len([job for job in concurrency_limits_manager.completed_jobs 
                               if job["user_id"] == "heavy_user"])
    other_users_completed = len([job for job in concurrency_limits_manager.completed_jobs 
                                if job["user_id"].startswith("normal_user")])
    
    assert heavy_user_completed <= concurrency_limits_manager.max_jobs_per_user, \
        f"Heavy user exceeded limit: {heavy_user_completed}"
    assert other_users_completed >= 2, "Other users should process normally"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mixed_workload_concurrency_l3(concurrency_limits_manager):
    """Test concurrency limits with mixed job types and priorities."""
    # Create mixed workload with different job types
    mixed_jobs = []
    
    # CPU intensive jobs (slow)
    for i in range(3):
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id=f"cpu_user_{i}",
            type="cpu_intensive_job",
            payload={"job_id": job_id},
            priority=MessagePriority.LOW
        )
        await concurrency_limits_manager.message_queue.enqueue(message)
        mixed_jobs.append(("cpu", job_id))
    
    # Quick jobs (fast)
    for i in range(8):
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id=f"quick_user_{i}",
            type="quick_job",
            payload={"job_id": job_id},
            priority=MessagePriority.HIGH
        )
        await concurrency_limits_manager.message_queue.enqueue(message)
        mixed_jobs.append(("quick", job_id))
    
    # IO intensive jobs (medium)
    for i in range(4):
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id=f"io_user_{i}",
            type="io_intensive_job",
            payload={"job_id": job_id},
            priority=MessagePriority.NORMAL
        )
        await concurrency_limits_manager.message_queue.enqueue(message)
        mixed_jobs.append(("io", job_id))
    
    # Start processing
    processing_task = asyncio.create_task(
        concurrency_limits_manager.message_queue.process_queue(worker_count=5)
    )
    
    # Monitor mixed workload processing
    metrics = await concurrency_limits_manager.monitor_concurrency_metrics(10.0)
    
    # Stop processing
    await concurrency_limits_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Analyze mixed workload performance
    completed_by_type = defaultdict(int)
    processing_times_by_type = defaultdict(list)
    
    for job in concurrency_limits_manager.completed_jobs:
        job_type = job["job_type"]
        completed_by_type[job_type] += 1
        processing_times_by_type[job_type].append(job["processing_time"])
    
    # Validate mixed workload handling
    assert metrics.total_jobs_processed >= 10, f"Insufficient mixed workload processing: {metrics.total_jobs_processed}"
    assert metrics.max_concurrent_jobs <= concurrency_limits_manager.max_concurrent_workers, \
        "Worker limits exceeded during mixed workload"
    
    # Quick jobs should have higher completion rate
    quick_completed = completed_by_type.get("quick", 0)
    cpu_completed = completed_by_type.get("cpu_intensive", 0)
    
    assert quick_completed >= 6, f"Quick jobs should complete faster: {quick_completed}"
    assert cpu_completed >= 1, f"Some CPU jobs should complete: {cpu_completed}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrency_under_high_load_l3(concurrency_limits_manager):
    """Test concurrency limits under high load conditions."""
    # Create high load scenario
    high_load_jobs = []
    users = [f"load_user_{i}" for i in range(20)]
    job_types = ["cpu_intensive_job", "memory_intensive_job", "io_intensive_job", "quick_job"]
    
    # Enqueue large number of jobs rapidly
    for i in range(30):
        job_id = str(uuid.uuid4())
        user_id = users[i % len(users)]
        job_type = job_types[i % len(job_types)]
        
        message = QueuedMessage(
            user_id=user_id,
            type=job_type,
            payload={"job_id": job_id, "load_test": True},
            priority=MessagePriority.NORMAL
        )
        
        await concurrency_limits_manager.message_queue.enqueue(message)
        high_load_jobs.append(job_id)
    
    start_time = time.time()
    
    # Start processing under high load
    processing_task = asyncio.create_task(
        concurrency_limits_manager.message_queue.process_queue(worker_count=6)
    )
    
    # Monitor high load performance
    metrics = await concurrency_limits_manager.monitor_concurrency_metrics(12.0)
    
    # Stop processing
    await concurrency_limits_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    total_time = time.time() - start_time
    
    # Validate high load handling
    validation = await concurrency_limits_manager.validate_concurrency_limits_enforcement()
    
    assert validation["limits_enforced"], f"Limits failed under high load: {validation['violations']}"
    assert metrics.total_jobs_processed >= 15, f"Poor throughput under high load: {metrics.total_jobs_processed}"
    assert metrics.throughput_per_second >= 1.0, f"Low throughput: {metrics.throughput_per_second} jobs/sec"
    assert total_time < 15.0, f"High load processing too slow: {total_time}s"
    
    # Check that system remained stable under load
    rejected_jobs = len([e for e in concurrency_limits_manager.concurrency_events if e["event"] == "rejected"])
    total_attempted = len(high_load_jobs)
    rejection_rate = rejected_jobs / total_attempted if total_attempted > 0 else 0
    
    # Some rejections are expected under high load, but should be controlled
    assert rejection_rate < 0.4, f"Too many job rejections under load: {rejection_rate * 100}%"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_dynamic_concurrency_adjustment_l3(concurrency_limits_manager):
    """Test dynamic adjustment of concurrency limits during runtime."""
    # Start with initial jobs
    initial_jobs = await concurrency_limits_manager.enqueue_concurrent_test_jobs(
        5, ["user1", "user2"], ["cpu_intensive_job"]
    )
    
    # Start processing
    processing_task = asyncio.create_task(
        concurrency_limits_manager.message_queue.process_queue(worker_count=3)
    )
    
    # Monitor initial phase
    await asyncio.sleep(2.0)
    
    # Dynamically increase worker limit
    new_worker_limit = 8
    await redis_manager.set("max_concurrent_workers", new_worker_limit)
    concurrency_limits_manager.max_concurrent_workers = new_worker_limit
    
    # Add more jobs after limit increase
    additional_jobs = await concurrency_limits_manager.enqueue_concurrent_test_jobs(
        8, ["user3", "user4", "user5"], ["io_intensive_job", "quick_job"]
    )
    
    # Monitor after adjustment
    metrics = await concurrency_limits_manager.monitor_concurrency_metrics(6.0)
    
    # Stop processing
    await concurrency_limits_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate dynamic adjustment
    assert metrics.max_concurrent_jobs <= new_worker_limit, \
        f"New worker limit exceeded: {metrics.max_concurrent_jobs} > {new_worker_limit}"
    assert metrics.total_jobs_processed >= 8, "Should process more jobs after limit increase"
    
    # Check that higher concurrency was achieved after adjustment
    later_events = [e for e in concurrency_limits_manager.resource_usage_log 
                   if e["timestamp"] > time.time() - 4.0]  # Last 4 seconds
    
    if later_events:
        max_later_concurrent = max(e["active_jobs"] for e in later_events)
        assert max_later_concurrent > 5, "Should achieve higher concurrency after limit increase"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resource_exhaustion_handling_l3(concurrency_limits_manager):
    """Test system behavior when approaching resource exhaustion."""
    # Create scenario that pushes system to limits
    exhaustion_jobs = []
    
    # Fill up worker slots with long-running jobs
    for i in range(concurrency_limits_manager.max_concurrent_workers):
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id=f"long_user_{i}",
            type="cpu_intensive_job",  # Long running
            payload={"job_id": job_id},
            priority=MessagePriority.LOW
        )
        await concurrency_limits_manager.message_queue.enqueue(message)
        exhaustion_jobs.append(job_id)
    
    # Try to add more jobs that should be rejected
    overflow_jobs = []
    for i in range(5):
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id=f"overflow_user_{i}",
            type="quick_job",
            payload={"job_id": job_id},
            priority=MessagePriority.HIGH  # High priority but should still be rejected
        )
        await concurrency_limits_manager.message_queue.enqueue(message)
        overflow_jobs.append(job_id)
    
    # Start processing
    processing_task = asyncio.create_task(
        concurrency_limits_manager.message_queue.process_queue(worker_count=3)
    )
    
    # Monitor resource exhaustion handling
    metrics = await concurrency_limits_manager.monitor_concurrency_metrics(8.0)
    
    # Stop processing
    await concurrency_limits_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate resource exhaustion handling
    rejected_events = [e for e in concurrency_limits_manager.concurrency_events 
                      if e["event"] == "rejected"]
    
    assert len(rejected_events) > 0, "Should reject jobs when resources exhausted"
    assert metrics.max_concurrent_jobs <= concurrency_limits_manager.max_concurrent_workers, \
        "Should not exceed worker limits even under pressure"
    
    # System should remain stable and process what it can
    assert metrics.total_jobs_processed >= 3, "Should still process some jobs despite exhaustion"
    
    # Check that high priority jobs were handled appropriately
    completed_job_types = [job["job_type"] for job in concurrency_limits_manager.completed_jobs]
    rejection_reasons = [e["reason"] for e in rejected_events]
    
    assert "worker_limit_reached" in rejection_reasons, "Should reject with appropriate reason"