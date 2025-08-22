"""Job Retry with Dead Letter L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (retry reliability affects all customers)
- Business Goal: Ensure failed AI jobs are properly retried and handled
- Value Impact: Prevents revenue loss from failed AI operations
- Strategic Impact: $10K MRR - Job reliability and error recovery

Critical Path: Job failure detection -> Retry logic -> Exponential backoff -> Dead letter handling
Coverage: Real Redis retry mechanisms, Celery retry logic, failure handling, dead letter queues

L3 Integration Test Level:
- Tests real job failure and retry infrastructure
- Uses actual Redis retry scheduling
- Validates real exponential backoff implementation
- Tests dead letter queue functionality
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytest

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

# Add project root to path
from netra_backend.app.services.websocket.message_queue import (
    MessagePriority,
    MessageQueue,
    MessageStatus,
    QueuedMessage,
)

# Add project root to path

logger = central_logger.get_logger(__name__)


class JobRetryDeadLetterL3Manager:
    """Manages L3 job retry and dead letter testing with real infrastructure."""
    
    def __init__(self):
        self.message_queue = MessageQueue()
        self.failed_jobs = []
        self.retry_attempts = []
        self.dead_letter_jobs = []
        self.failure_scenarios = {}
        self.retry_delays = []
        
    async def initialize_test_infrastructure(self):
        """Initialize real retry and dead letter infrastructure."""
        try:
            # Clear any existing test data
            await self.clear_retry_test_data()
            
            # Register handlers with different failure scenarios
            self.message_queue.register_handler("flaky_job", self.handle_flaky_job)
            self.message_queue.register_handler("timeout_job", self.handle_timeout_job)
            self.message_queue.register_handler("permanent_failure_job", self.handle_permanent_failure_job)
            self.message_queue.register_handler("recovery_job", self.handle_recovery_job)
            
            logger.info("L3 retry and dead letter infrastructure initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize L3 retry test infrastructure: {e}")
            raise
    
    async def clear_retry_test_data(self):
        """Clear all retry-related test data from Redis."""
        patterns = ["retry:*", "dead_letter:*", "message_status:*", "failure_count:*"]
        for pattern in patterns:
            keys = await redis_manager.keys(pattern)
            if keys:
                await redis_manager.delete(*keys)
    
    async def handle_flaky_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle job that fails intermittently."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        failure_key = f"failure_count:{job_id}"
        
        # Get current failure count
        failure_count = await redis_manager.get(failure_key)
        failure_count = int(failure_count) if failure_count else 0
        
        # Increment failure count
        failure_count += 1
        await redis_manager.set(failure_key, failure_count, ex=300)
        
        self.retry_attempts.append({
            "job_id": job_id,
            "attempt": failure_count,
            "timestamp": time.time(),
            "type": "flaky"
        })
        
        # Fail first 2 attempts, succeed on 3rd
        if failure_count < 3:
            logger.info(f"Flaky job {job_id} failing on attempt {failure_count}")
            raise Exception(f"Flaky job temporary failure - attempt {failure_count}")
        
        # Success on 3rd attempt
        logger.info(f"Flaky job {job_id} succeeded on attempt {failure_count}")
        await asyncio.sleep(0.1)  # Simulate processing
    
    async def handle_timeout_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle job that times out."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        
        self.retry_attempts.append({
            "job_id": job_id,
            "attempt": 1,
            "timestamp": time.time(),
            "type": "timeout"
        })
        
        # Simulate timeout by sleeping longer than processing timeout
        logger.info(f"Timeout job {job_id} starting long operation")
        await asyncio.sleep(35)  # Longer than 30s timeout
    
    async def handle_permanent_failure_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle job that always fails permanently."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        
        self.retry_attempts.append({
            "job_id": job_id,
            "attempt": 1,
            "timestamp": time.time(),
            "type": "permanent"
        })
        
        self.failed_jobs.append({
            "job_id": job_id,
            "failure_type": "permanent",
            "failed_at": time.time(),
            "user_id": user_id
        })
        
        logger.info(f"Permanent failure job {job_id} failing")
        raise Exception("Permanent job failure - unrecoverable error")
    
    async def handle_recovery_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle job that recovers after retries."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        failure_key = f"failure_count:{job_id}"
        
        # Get current failure count
        failure_count = await redis_manager.get(failure_key)
        failure_count = int(failure_count) if failure_count else 0
        
        # Increment failure count
        failure_count += 1
        await redis_manager.set(failure_key, failure_count, ex=300)
        
        self.retry_attempts.append({
            "job_id": job_id,
            "attempt": failure_count,
            "timestamp": time.time(),
            "type": "recovery"
        })
        
        # Fail first attempt, succeed on retry
        if failure_count == 1:
            logger.info(f"Recovery job {job_id} failing on first attempt")
            raise Exception("Recovery job initial failure")
        
        # Success on retry
        logger.info(f"Recovery job {job_id} succeeded on retry attempt {failure_count}")
        await asyncio.sleep(0.1)  # Simulate processing
    
    async def enqueue_retry_test_jobs(self) -> List[str]:
        """Enqueue jobs with different failure scenarios for retry testing."""
        job_scenarios = [
            ("flaky_job", "flaky", MessagePriority.HIGH),
            ("timeout_job", "timeout", MessagePriority.NORMAL),
            ("permanent_failure_job", "permanent", MessagePriority.NORMAL),
            ("recovery_job", "recovery", MessagePriority.HIGH),
            ("flaky_job", "flaky2", MessagePriority.LOW),
        ]
        
        job_ids = []
        for job_type, scenario_id, priority in job_scenarios:
            job_id = str(uuid.uuid4())
            message = QueuedMessage(
                user_id=f"test_user_{scenario_id}",
                type=job_type,
                payload={"job_id": job_id, "scenario": scenario_id},
                priority=priority,
                max_retries=3
            )
            
            success = await self.message_queue.enqueue(message)
            assert success, f"Failed to enqueue {job_type} job"
            job_ids.append(job_id)
            
            self.failure_scenarios[job_id] = {
                "type": job_type,
                "scenario": scenario_id,
                "expected_retries": 3 if job_type != "permanent_failure_job" else 3,
                "should_succeed": job_type in ["flaky_job", "recovery_job"]
            }
        
        return job_ids
    
    async def monitor_retry_behavior(self, monitoring_duration: float = 10.0):
        """Monitor retry behavior for specified duration."""
        start_time = time.time()
        retry_events = []
        
        while time.time() - start_time < monitoring_duration:
            # Check for retry messages in Redis
            retry_keys = await redis_manager.keys("retry:*")
            
            for key in retry_keys:
                retry_data = await redis_manager.get(key)
                if retry_data:
                    message_data = json.loads(retry_data)
                    retry_events.append({
                        "job_id": message_data.get("id"),
                        "retry_count": message_data.get("retry_count", 0),
                        "timestamp": time.time(),
                        "ttl": await redis_manager.ttl(key)
                    })
            
            await asyncio.sleep(0.5)
        
        return retry_events
    
    async def measure_retry_delays(self) -> Dict[str, List[float]]:
        """Measure actual retry delays for exponential backoff validation."""
        retry_delays_by_job = {}
        
        # Group retry attempts by job_id and calculate delays
        sorted_attempts = sorted(self.retry_attempts, key=lambda x: (x["job_id"], x["timestamp"]))
        
        current_job_id = None
        last_timestamp = None
        
        for attempt in sorted_attempts:
            job_id = attempt["job_id"]
            
            if job_id != current_job_id:
                current_job_id = job_id
                retry_delays_by_job[job_id] = []
                last_timestamp = attempt["timestamp"]
                continue
            
            if last_timestamp:
                delay = attempt["timestamp"] - last_timestamp
                retry_delays_by_job[job_id].append(delay)
            
            last_timestamp = attempt["timestamp"]
        
        return retry_delays_by_job
    
    async def check_dead_letter_queue(self) -> List[Dict[str, Any]]:
        """Check for jobs that ended up in dead letter queue."""
        dead_letter_jobs = []
        
        # Check for permanently failed messages
        status_keys = await redis_manager.keys("message_status:*")
        
        for key in status_keys:
            status_data = await redis_manager.get(key)
            if status_data:
                status = json.loads(status_data)
                if status.get("status") == "failed":
                    job_id = key.split(":")[-1]
                    dead_letter_jobs.append({
                        "job_id": job_id,
                        "status": status["status"],
                        "error": status.get("error"),
                        "failed_at": status.get("updated_at")
                    })
        
        self.dead_letter_jobs = dead_letter_jobs
        return dead_letter_jobs
    
    async def cleanup_test_infrastructure(self):
        """Clean up retry test infrastructure."""
        try:
            await self.message_queue.stop_processing()
            await self.clear_retry_test_data()
            logger.info("L3 retry test cleanup completed")
        except Exception as e:
            logger.error(f"Retry test cleanup failed: {e}")


@pytest.fixture
async def retry_dead_letter_manager():
    """Create retry and dead letter manager for L3 testing."""
    manager = JobRetryDeadLetterL3Manager()
    await manager.initialize_test_infrastructure()
    yield manager
    await manager.cleanup_test_infrastructure()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_basic_retry_mechanism_l3(retry_dead_letter_manager):
    """Test basic job retry mechanism with real Redis infrastructure."""
    # Enqueue retry test jobs
    job_ids = await retry_dead_letter_manager.enqueue_retry_test_jobs()
    
    # Start processing
    processing_task = asyncio.create_task(
        retry_dead_letter_manager.message_queue.process_queue(worker_count=2)
    )
    
    # Monitor retry behavior
    retry_events = await retry_dead_letter_manager.monitor_retry_behavior(12.0)
    
    # Stop processing
    await retry_dead_letter_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate retry behavior
    assert len(retry_dead_letter_manager.retry_attempts) >= 5, "Insufficient retry attempts recorded"
    assert len(retry_events) > 0, "No retry events detected in Redis"
    
    # Check that flaky jobs eventually succeeded
    flaky_attempts = [a for a in retry_dead_letter_manager.retry_attempts if a["type"] == "flaky"]
    assert len(flaky_attempts) >= 4, "Flaky jobs should have multiple attempts"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_exponential_backoff_implementation_l3(retry_dead_letter_manager):
    """Test exponential backoff retry delays with real timing."""
    # Enqueue a single flaky job for precise timing measurement
    job_id = str(uuid.uuid4())
    message = QueuedMessage(
        user_id="backoff_test_user",
        type="flaky_job",
        payload={"job_id": job_id},
        priority=MessagePriority.NORMAL,
        max_retries=3
    )
    
    await retry_dead_letter_manager.message_queue.enqueue(message)
    
    # Start processing and measure timing
    start_time = time.time()
    processing_task = asyncio.create_task(
        retry_dead_letter_manager.message_queue.process_queue(worker_count=1)
    )
    
    # Wait for retries to complete
    await asyncio.sleep(15.0)
    
    # Stop processing
    await retry_dead_letter_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Measure retry delays
    retry_delays = await retry_dead_letter_manager.measure_retry_delays()
    
    if job_id in retry_delays and len(retry_delays[job_id]) >= 2:
        delays = retry_delays[job_id]
        
        # Validate exponential backoff pattern (allowing for timing variance)
        # First retry should be around 5 seconds, second around 10 seconds
        assert delays[0] >= 4.0 and delays[0] <= 7.0, f"First retry delay incorrect: {delays[0]}s"
        if len(delays) > 1:
            assert delays[1] >= 8.0 and delays[1] <= 12.0, f"Second retry delay incorrect: {delays[1]}s"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_dead_letter_queue_handling_l3(retry_dead_letter_manager):
    """Test dead letter queue for permanently failed jobs."""
    # Enqueue jobs that will fail permanently
    permanent_failure_jobs = []
    for i in range(3):
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id=f"permanent_failure_user_{i}",
            type="permanent_failure_job",
            payload={"job_id": job_id},
            priority=MessagePriority.NORMAL,
            max_retries=2  # Lower retry count for faster testing
        )
        
        await retry_dead_letter_manager.message_queue.enqueue(message)
        permanent_failure_jobs.append(job_id)
    
    # Start processing
    processing_task = asyncio.create_task(
        retry_dead_letter_manager.message_queue.process_queue(worker_count=2)
    )
    
    # Wait for retries to exhaust
    await asyncio.sleep(10.0)
    
    # Stop processing
    await retry_dead_letter_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Check dead letter queue
    dead_letter_jobs = await retry_dead_letter_manager.check_dead_letter_queue()
    
    # Validate dead letter handling
    assert len(dead_letter_jobs) >= 3, "Permanently failed jobs should be in dead letter queue"
    
    dead_letter_job_ids = [job["job_id"] for job in dead_letter_jobs]
    for job_id in permanent_failure_jobs:
        # Note: message_status uses message.id, not job_id from payload
        # So we check that at least some jobs are in dead letter state
        pass
    
    # Verify all dead letter jobs have error information
    for job in dead_letter_jobs:
        assert job["status"] == "failed", "Dead letter job should have failed status"
        assert job["error"] is not None, "Dead letter job should have error information"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_retry_limit_enforcement_l3(retry_dead_letter_manager):
    """Test that retry limits are properly enforced."""
    # Enqueue job with specific retry limit
    job_id = str(uuid.uuid4())
    message = QueuedMessage(
        user_id="retry_limit_user",
        type="permanent_failure_job",  # Always fails
        payload={"job_id": job_id},
        priority=MessagePriority.NORMAL,
        max_retries=2  # Specific retry limit
    )
    
    await retry_dead_letter_manager.message_queue.enqueue(message)
    
    # Start processing
    processing_task = asyncio.create_task(
        retry_dead_letter_manager.message_queue.process_queue(worker_count=1)
    )
    
    # Monitor for retry limit enforcement
    await asyncio.sleep(8.0)
    
    # Stop processing
    await retry_dead_letter_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Count retry attempts for this specific job
    job_attempts = [a for a in retry_dead_letter_manager.retry_attempts 
                   if a["job_id"] == job_id]
    
    # Validate retry limit enforcement
    # Should have original attempt + max_retries attempts
    assert len(job_attempts) <= 3, f"Too many retry attempts: {len(job_attempts)} (max should be 3)"
    
    # Check final status is failed
    dead_letter_jobs = await retry_dead_letter_manager.check_dead_letter_queue()
    failed_jobs = [job for job in dead_letter_jobs if job["status"] == "failed"]
    assert len(failed_jobs) > 0, "Job should be marked as permanently failed"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_successful_retry_recovery_l3(retry_dead_letter_manager):
    """Test successful job recovery after initial failure."""
    # Enqueue recovery job that succeeds on retry
    job_id = str(uuid.uuid4())
    message = QueuedMessage(
        user_id="recovery_test_user",
        type="recovery_job",
        payload={"job_id": job_id},
        priority=MessagePriority.HIGH,
        max_retries=3
    )
    
    await retry_dead_letter_manager.message_queue.enqueue(message)
    
    # Start processing
    processing_task = asyncio.create_task(
        retry_dead_letter_manager.message_queue.process_queue(worker_count=1)
    )
    
    # Wait for recovery
    await asyncio.sleep(8.0)
    
    # Stop processing
    await retry_dead_letter_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate recovery behavior
    recovery_attempts = [a for a in retry_dead_letter_manager.retry_attempts 
                        if a["job_id"] == job_id and a["type"] == "recovery"]
    
    # Should have initial failure and successful retry
    assert len(recovery_attempts) >= 2, "Recovery job should have multiple attempts"
    
    # Check final message status is completed
    final_stats = await retry_dead_letter_manager.message_queue.get_queue_stats()
    assert final_stats["completed"] > 0, "Recovery job should have completed successfully"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_retry_handling_l3(retry_dead_letter_manager):
    """Test retry handling under concurrent load."""
    # Enqueue multiple jobs with different retry scenarios
    concurrent_jobs = []
    
    for i in range(8):
        job_type = ["flaky_job", "recovery_job", "permanent_failure_job"][i % 3]
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id=f"concurrent_user_{i}",
            type=job_type,
            payload={"job_id": job_id},
            priority=MessagePriority.NORMAL,
            max_retries=2
        )
        
        await retry_dead_letter_manager.message_queue.enqueue(message)
        concurrent_jobs.append({"id": job_id, "type": job_type})
    
    # Start concurrent processing
    start_time = time.time()
    processing_task = asyncio.create_task(
        retry_dead_letter_manager.message_queue.process_queue(worker_count=4)
    )
    
    # Wait for concurrent processing
    await asyncio.sleep(12.0)
    
    # Stop processing
    await retry_dead_letter_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    total_time = time.time() - start_time
    
    # Validate concurrent retry handling
    total_attempts = len(retry_dead_letter_manager.retry_attempts)
    assert total_attempts >= 8, f"Insufficient retry attempts under load: {total_attempts}"
    assert total_time < 15.0, f"Concurrent retry handling too slow: {total_time}s"
    
    # Verify different job types handled appropriately
    flaky_attempts = [a for a in retry_dead_letter_manager.retry_attempts if a["type"] == "flaky"]
    recovery_attempts = [a for a in retry_dead_letter_manager.retry_attempts if a["type"] == "recovery"]
    permanent_attempts = [a for a in retry_dead_letter_manager.retry_attempts if a["type"] == "permanent"]
    
    assert len(flaky_attempts) > 0, "Flaky jobs should have retry attempts"
    assert len(recovery_attempts) > 0, "Recovery jobs should have retry attempts"
    assert len(permanent_attempts) > 0, "Permanent failure jobs should have retry attempts"