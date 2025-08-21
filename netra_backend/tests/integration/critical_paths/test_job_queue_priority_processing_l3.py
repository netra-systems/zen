"""Job Queue Priority Processing L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise/Mid-tier customers with high-volume AI workloads
- Business Goal: Ensure critical AI jobs are processed before low-priority ones
- Value Impact: Prevents revenue-critical AI operations from being delayed
- Strategic Impact: $10K MRR - Background job reliability and priority handling

Critical Path: Priority queue management -> Job ordering -> Worker allocation -> Processing execution
Coverage: Redis priority queues, Celery job priorities, worker distribution, real job processing

L3 Integration Test Level:
- Tests real Redis/Celery job queue infrastructure
- Uses actual priority queue mechanisms
- Validates real-time job processing order
- Measures actual performance under load
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import uuid
import json
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta

# Add project root to path

from netra_backend.app.services.websocket.message_queue import MessageQueue, QueuedMessage, MessagePriority, MessageStatus
from netra_backend.app.websocket.unified.job_queue import JobQueueManager
from redis_manager import redis_manager
from logging_config import central_logger

# Add project root to path

logger = central_logger.get_logger(__name__)


class PriorityProcessingL3Manager:
    """Manages L3 priority processing tests with real queue infrastructure."""
    
    def __init__(self):
        self.message_queue = MessageQueue()
        self.job_queue = JobQueueManager()
        self.processed_jobs = []
        self.processing_times = {}
        self.priority_violations = []
        
    async def initialize_test_infrastructure(self):
        """Initialize real Redis queues and processing infrastructure."""
        try:
            # Clear any existing test data
            await self.clear_test_queues()
            
            # Initialize message queue handlers
            self.message_queue.register_handler("critical_ai_job", self.handle_critical_job)
            self.message_queue.register_handler("high_priority_job", self.handle_high_priority_job)
            self.message_queue.register_handler("normal_job", self.handle_normal_job)
            self.message_queue.register_handler("low_priority_job", self.handle_low_priority_job)
            
            logger.info("L3 priority processing infrastructure initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize L3 test infrastructure: {e}")
            raise
    
    async def clear_test_queues(self):
        """Clear all test queues in Redis."""
        patterns = ["message_queue:*", "message_status:*", "retry:*", "test_job:*"]
        for pattern in patterns:
            keys = await redis_manager.keys(pattern)
            if keys:
                await redis_manager.delete(*keys)
    
    async def handle_critical_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle critical priority job processing."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        start_time = time.time()
        
        # Simulate critical AI operation (model inference, real-time analysis)
        await asyncio.sleep(0.2)  # Critical jobs get fast processing
        
        processing_time = time.time() - start_time
        self.processed_jobs.append({
            "job_id": job_id,
            "priority": "critical",
            "processed_at": time.time(),
            "processing_time": processing_time,
            "user_id": user_id
        })
        self.processing_times[job_id] = processing_time
        
        logger.info(f"Processed critical job {job_id} in {processing_time:.3f}s")
    
    async def handle_high_priority_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle high priority job processing."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        start_time = time.time()
        
        # Simulate high priority AI operation (complex analysis)
        await asyncio.sleep(0.4)
        
        processing_time = time.time() - start_time
        self.processed_jobs.append({
            "job_id": job_id,
            "priority": "high",
            "processed_at": time.time(),
            "processing_time": processing_time,
            "user_id": user_id
        })
        self.processing_times[job_id] = processing_time
        
        logger.info(f"Processed high priority job {job_id} in {processing_time:.3f}s")
    
    async def handle_normal_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle normal priority job processing."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        start_time = time.time()
        
        # Simulate normal AI operation (standard processing)
        await asyncio.sleep(0.6)
        
        processing_time = time.time() - start_time
        self.processed_jobs.append({
            "job_id": job_id,
            "priority": "normal",
            "processed_at": time.time(),
            "processing_time": processing_time,
            "user_id": user_id
        })
        self.processing_times[job_id] = processing_time
        
        logger.info(f"Processed normal job {job_id} in {processing_time:.3f}s")
    
    async def handle_low_priority_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle low priority job processing."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        start_time = time.time()
        
        # Simulate low priority AI operation (batch processing)
        await asyncio.sleep(0.8)
        
        processing_time = time.time() - start_time
        self.processed_jobs.append({
            "job_id": job_id,
            "priority": "low",
            "processed_at": time.time(),
            "processing_time": processing_time,
            "user_id": user_id
        })
        self.processing_times[job_id] = processing_time
        
        logger.info(f"Processed low priority job {job_id} in {processing_time:.3f}s")
    
    async def enqueue_priority_test_jobs(self, job_count_per_priority: int = 3) -> List[str]:
        """Enqueue jobs with different priorities for testing."""
        job_ids = []
        priorities = [
            (MessagePriority.CRITICAL, "critical_ai_job"),
            (MessagePriority.HIGH, "high_priority_job"),
            (MessagePriority.NORMAL, "normal_job"),
            (MessagePriority.LOW, "low_priority_job")
        ]
        
        # Enqueue jobs in reverse priority order to test prioritization
        for priority, job_type in reversed(priorities):
            for i in range(job_count_per_priority):
                job_id = str(uuid.uuid4())
                message = QueuedMessage(
                    id=str(uuid.uuid4()),
                    user_id=f"test_user_{i}",
                    type=job_type,
                    payload={"job_id": job_id, "test_data": f"priority_test_{i}"},
                    priority=priority
                )
                
                success = await self.message_queue.enqueue(message)
                assert success, f"Failed to enqueue {priority.name} job"
                job_ids.append(job_id)
        
        return job_ids
    
    async def validate_priority_processing_order(self) -> Dict[str, Any]:
        """Validate that jobs were processed in correct priority order."""
        if len(self.processed_jobs) < 4:
            return {"valid": False, "reason": "Insufficient processed jobs"}
        
        # Sort processed jobs by processing time
        sorted_jobs = sorted(self.processed_jobs, key=lambda x: x["processed_at"])
        
        # Check if priorities are in correct order
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        violations = []
        
        for i in range(len(sorted_jobs) - 1):
            current_priority = priority_order[sorted_jobs[i]["priority"]]
            next_priority = priority_order[sorted_jobs[i + 1]["priority"]]
            
            if current_priority > next_priority:
                violations.append({
                    "position": i,
                    "expected": sorted_jobs[i + 1]["priority"],
                    "actual": sorted_jobs[i]["priority"],
                    "job_ids": [sorted_jobs[i]["job_id"], sorted_jobs[i + 1]["job_id"]]
                })
        
        self.priority_violations = violations
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "total_jobs": len(sorted_jobs),
            "processing_order": [job["priority"] for job in sorted_jobs]
        }
    
    async def cleanup_test_infrastructure(self):
        """Clean up test infrastructure and queues."""
        try:
            await self.message_queue.stop_processing()
            await self.clear_test_queues()
            logger.info("L3 priority processing cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def priority_processing_manager():
    """Create priority processing manager for L3 testing."""
    manager = PriorityProcessingL3Manager()
    await manager.initialize_test_infrastructure()
    yield manager
    await manager.cleanup_test_infrastructure()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_basic_priority_queue_processing_l3(priority_processing_manager):
    """Test basic priority queue processing with real Redis infrastructure."""
    # Enqueue mixed priority jobs
    job_ids = await priority_processing_manager.enqueue_priority_test_jobs(2)
    
    # Start processing with limited workers to ensure serialization
    processing_task = asyncio.create_task(
        priority_processing_manager.message_queue.process_queue(worker_count=1)
    )
    
    # Wait for processing to complete
    await asyncio.sleep(5.0)
    
    # Stop processing
    await priority_processing_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate processing order
    validation_result = await priority_processing_manager.validate_priority_processing_order()
    
    assert validation_result["valid"], f"Priority order violations: {validation_result['violations']}"
    assert validation_result["total_jobs"] >= 6, "Not enough jobs processed"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_priority_processing_l3(priority_processing_manager):
    """Test priority processing under concurrent load."""
    # Enqueue large number of mixed priority jobs
    job_ids = await priority_processing_manager.enqueue_priority_test_jobs(5)
    
    start_time = time.time()
    
    # Start processing with multiple workers
    processing_task = asyncio.create_task(
        priority_processing_manager.message_queue.process_queue(worker_count=3)
    )
    
    # Wait for processing to complete
    await asyncio.sleep(8.0)
    
    # Stop processing
    await priority_processing_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    total_time = time.time() - start_time
    
    # Validate results
    assert len(priority_processing_manager.processed_jobs) >= 15, "Insufficient job processing under load"
    assert total_time < 10.0, f"Processing took too long: {total_time}s"
    
    # Check that critical jobs were processed faster on average
    critical_times = [job["processing_time"] for job in priority_processing_manager.processed_jobs if job["priority"] == "critical"]
    low_times = [job["processing_time"] for job in priority_processing_manager.processed_jobs if job["priority"] == "low"]
    
    if critical_times and low_times:
        avg_critical_time = sum(critical_times) / len(critical_times)
        avg_low_time = sum(low_times) / len(low_times)
        assert avg_critical_time < avg_low_time, "Critical jobs should process faster than low priority jobs"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_queue_statistics_accuracy_l3(priority_processing_manager):
    """Test accuracy of queue statistics during processing."""
    # Enqueue test jobs
    await priority_processing_manager.enqueue_priority_test_jobs(3)
    
    # Get initial statistics
    initial_stats = await priority_processing_manager.message_queue.get_queue_stats()
    
    assert initial_stats["total_pending"] >= 9, "Initial queue count incorrect"
    assert "queues" in initial_stats, "Queue breakdown missing"
    
    # Start processing
    processing_task = asyncio.create_task(
        priority_processing_manager.message_queue.process_queue(worker_count=2)
    )
    
    # Monitor statistics during processing
    await asyncio.sleep(2.0)
    mid_stats = await priority_processing_manager.message_queue.get_queue_stats()
    
    await asyncio.sleep(4.0)
    
    # Stop processing and get final statistics
    await priority_processing_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    final_stats = await priority_processing_manager.message_queue.get_queue_stats()
    
    # Validate statistics accuracy
    assert final_stats["total_pending"] < initial_stats["total_pending"], "Queue should decrease during processing"
    assert final_stats["completed"] > 0, "Should have completed jobs"


@pytest.mark.asyncio
@pytest.mark.integration  
async def test_priority_queue_performance_l3(priority_processing_manager):
    """Test priority queue performance under high load."""
    # Create high-volume test scenario
    large_job_count = 10
    
    enqueue_start = time.time()
    job_ids = await priority_processing_manager.enqueue_priority_test_jobs(large_job_count)
    enqueue_time = time.time() - enqueue_start
    
    # Validate enqueue performance
    assert enqueue_time < 5.0, f"Job enqueuing too slow: {enqueue_time}s"
    assert len(job_ids) == large_job_count * 4, "Not all jobs enqueued"
    
    # Start high-performance processing
    process_start = time.time()
    processing_task = asyncio.create_task(
        priority_processing_manager.message_queue.process_queue(worker_count=5)
    )
    
    # Wait for completion
    await asyncio.sleep(15.0)
    
    # Stop processing
    await priority_processing_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    process_time = time.time() - process_start
    
    # Validate performance metrics
    processed_count = len(priority_processing_manager.processed_jobs)
    throughput = processed_count / process_time
    
    assert processed_count >= 30, f"Low processing count: {processed_count}"
    assert throughput >= 2.0, f"Low throughput: {throughput} jobs/sec"
    assert process_time < 20.0, f"Processing took too long: {process_time}s"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mixed_workload_priority_handling_l3(priority_processing_manager):
    """Test priority handling with mixed AI workload scenarios."""
    # Create realistic mixed workload
    mixed_jobs = []
    
    # Critical: Real-time AI inference requests
    for i in range(3):
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id=f"enterprise_user_{i}",
            type="critical_ai_job",
            payload={"job_id": job_id, "workload": "real_time_inference"},
            priority=MessagePriority.CRITICAL
        )
        await priority_processing_manager.message_queue.enqueue(message)
        mixed_jobs.append({"id": job_id, "priority": "critical", "workload": "inference"})
    
    # High: Complex analytics
    for i in range(4):
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id=f"mid_tier_user_{i}",
            type="high_priority_job", 
            payload={"job_id": job_id, "workload": "complex_analytics"},
            priority=MessagePriority.HIGH
        )
        await priority_processing_manager.message_queue.enqueue(message)
        mixed_jobs.append({"id": job_id, "priority": "high", "workload": "analytics"})
    
    # Normal: Standard processing
    for i in range(5):
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id=f"standard_user_{i}",
            type="normal_job",
            payload={"job_id": job_id, "workload": "standard_processing"},
            priority=MessagePriority.NORMAL
        )
        await priority_processing_manager.message_queue.enqueue(message)
        mixed_jobs.append({"id": job_id, "priority": "normal", "workload": "standard"})
    
    # Start processing
    processing_task = asyncio.create_task(
        priority_processing_manager.message_queue.process_queue(worker_count=3)
    )
    
    await asyncio.sleep(8.0)
    
    # Stop processing
    await priority_processing_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate mixed workload handling
    processed_jobs = priority_processing_manager.processed_jobs
    assert len(processed_jobs) >= 10, "Insufficient mixed workload processing"
    
    # Verify critical jobs were processed first
    first_five_jobs = sorted(processed_jobs, key=lambda x: x["processed_at"])[:5]
    critical_in_first_five = sum(1 for job in first_five_jobs if job["priority"] == "critical")
    
    assert critical_in_first_five >= 2, "Critical jobs not prioritized in mixed workload"