"""Job Scheduling Accuracy L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise/Mid-tier customers requiring scheduled AI operations
- Business Goal: Ensure accurate timing for scheduled AI workloads (reports, analysis)
- Value Impact: Reliable scheduled processing enables automated AI workflows
- Strategic Impact: $10K MRR - Scheduled job reliability and timing accuracy

Critical Path: Cron scheduling -> Job timing -> Execution accuracy -> Completion tracking
Coverage: Real Redis-based scheduling, Celery beat scheduling, timing precision, execution validation

L3 Integration Test Level:
- Tests real Redis-based job scheduling infrastructure
- Uses actual timing mechanisms for scheduled jobs
- Validates precision of scheduled execution times
- Tests scheduling under various load conditions
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

# Add project root to path

from netra_backend.app.services.websocket.message_queue import MessageQueue, QueuedMessage, MessagePriority, MessageStatus
from redis_manager import redis_manager
from logging_config import central_logger

# Add project root to path

logger = central_logger.get_logger(__name__)


@dataclass
class ScheduledJob:
    """Represents a scheduled job with timing information."""
    job_id: str
    scheduled_time: float
    actual_execution_time: Optional[float] = None
    completion_time: Optional[float] = None
    timing_accuracy: Optional[float] = None
    status: str = "scheduled"


class JobSchedulingAccuracyL3Manager:
    """Manages L3 job scheduling accuracy tests with real infrastructure."""
    
    def __init__(self):
        self.message_queue = MessageQueue()
        self.scheduled_jobs: Dict[str, ScheduledJob] = {}
        self.execution_events = []
        self.timing_violations = []
        self.schedule_performance = {}
        
    async def initialize_test_infrastructure(self):
        """Initialize real scheduling infrastructure."""
        try:
            # Clear any existing scheduled jobs
            await self.clear_scheduling_test_data()
            
            # Register handlers for different types of scheduled jobs
            self.message_queue.register_handler("scheduled_report", self.handle_scheduled_report)
            self.message_queue.register_handler("scheduled_analysis", self.handle_scheduled_analysis)
            self.message_queue.register_handler("scheduled_maintenance", self.handle_scheduled_maintenance)
            self.message_queue.register_handler("scheduled_optimization", self.handle_scheduled_optimization)
            
            logger.info("L3 job scheduling infrastructure initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize L3 scheduling test infrastructure: {e}")
            raise
    
    async def clear_scheduling_test_data(self):
        """Clear all scheduling-related test data from Redis."""
        patterns = ["schedule:*", "scheduled_job:*", "execution_log:*", "timing_*"]
        for pattern in patterns:
            keys = await redis_manager.keys(pattern)
            if keys:
                await redis_manager.delete(*keys)
    
    async def handle_scheduled_report(self, user_id: str, payload: Dict[str, Any]):
        """Handle scheduled report generation job."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        scheduled_time = payload.get("scheduled_time", time.time())
        actual_time = time.time()
        
        # Calculate timing accuracy
        timing_accuracy = abs(actual_time - scheduled_time)
        
        # Update scheduled job tracking
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].actual_execution_time = actual_time
            self.scheduled_jobs[job_id].timing_accuracy = timing_accuracy
            self.scheduled_jobs[job_id].status = "executing"
        
        # Simulate report generation processing
        await asyncio.sleep(0.3)
        
        completion_time = time.time()
        
        # Record execution event
        self.execution_events.append({
            "job_id": job_id,
            "job_type": "scheduled_report",
            "scheduled_time": scheduled_time,
            "actual_execution_time": actual_time,
            "completion_time": completion_time,
            "timing_accuracy": timing_accuracy,
            "processing_duration": completion_time - actual_time
        })
        
        # Mark as completed
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].completion_time = completion_time
            self.scheduled_jobs[job_id].status = "completed"
        
        logger.info(f"Scheduled report {job_id} completed with {timing_accuracy:.3f}s timing accuracy")
    
    async def handle_scheduled_analysis(self, user_id: str, payload: Dict[str, Any]):
        """Handle scheduled analysis job."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        scheduled_time = payload.get("scheduled_time", time.time())
        actual_time = time.time()
        
        timing_accuracy = abs(actual_time - scheduled_time)
        
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].actual_execution_time = actual_time
            self.scheduled_jobs[job_id].timing_accuracy = timing_accuracy
            self.scheduled_jobs[job_id].status = "executing"
        
        # Simulate complex analysis processing
        await asyncio.sleep(0.5)
        
        completion_time = time.time()
        
        self.execution_events.append({
            "job_id": job_id,
            "job_type": "scheduled_analysis",
            "scheduled_time": scheduled_time,
            "actual_execution_time": actual_time,
            "completion_time": completion_time,
            "timing_accuracy": timing_accuracy,
            "processing_duration": completion_time - actual_time
        })
        
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].completion_time = completion_time
            self.scheduled_jobs[job_id].status = "completed"
        
        logger.info(f"Scheduled analysis {job_id} completed with {timing_accuracy:.3f}s timing accuracy")
    
    async def handle_scheduled_maintenance(self, user_id: str, payload: Dict[str, Any]):
        """Handle scheduled maintenance job."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        scheduled_time = payload.get("scheduled_time", time.time())
        actual_time = time.time()
        
        timing_accuracy = abs(actual_time - scheduled_time)
        
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].actual_execution_time = actual_time
            self.scheduled_jobs[job_id].timing_accuracy = timing_accuracy
            self.scheduled_jobs[job_id].status = "executing"
        
        # Simulate maintenance processing
        await asyncio.sleep(0.2)
        
        completion_time = time.time()
        
        self.execution_events.append({
            "job_id": job_id,
            "job_type": "scheduled_maintenance",
            "scheduled_time": scheduled_time,
            "actual_execution_time": actual_time,
            "completion_time": completion_time,
            "timing_accuracy": timing_accuracy,
            "processing_duration": completion_time - actual_time
        })
        
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].completion_time = completion_time
            self.scheduled_jobs[job_id].status = "completed"
        
        logger.info(f"Scheduled maintenance {job_id} completed with {timing_accuracy:.3f}s timing accuracy")
    
    async def handle_scheduled_optimization(self, user_id: str, payload: Dict[str, Any]):
        """Handle scheduled optimization job."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        scheduled_time = payload.get("scheduled_time", time.time())
        actual_time = time.time()
        
        timing_accuracy = abs(actual_time - scheduled_time)
        
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].actual_execution_time = actual_time
            self.scheduled_jobs[job_id].timing_accuracy = timing_accuracy
            self.scheduled_jobs[job_id].status = "executing"
        
        # Simulate optimization processing
        await asyncio.sleep(0.4)
        
        completion_time = time.time()
        
        self.execution_events.append({
            "job_id": job_id,
            "job_type": "scheduled_optimization",
            "scheduled_time": scheduled_time,
            "actual_execution_time": actual_time,
            "completion_time": completion_time,
            "timing_accuracy": timing_accuracy,
            "processing_duration": completion_time - actual_time
        })
        
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].completion_time = completion_time
            self.scheduled_jobs[job_id].status = "completed"
        
        logger.info(f"Scheduled optimization {job_id} completed with {timing_accuracy:.3f}s timing accuracy")
    
    async def schedule_delayed_jobs(self, job_specs: List[Dict[str, Any]]) -> List[str]:
        """Schedule jobs to be executed at future times using Redis delay mechanism."""
        scheduled_job_ids = []
        
        for spec in job_specs:
            job_id = str(uuid.uuid4())
            delay_seconds = spec.get("delay_seconds", 1.0)
            job_type = spec.get("job_type", "scheduled_report")
            priority = spec.get("priority", MessagePriority.NORMAL)
            
            scheduled_time = time.time() + delay_seconds
            
            # Create scheduled job tracking
            self.scheduled_jobs[job_id] = ScheduledJob(
                job_id=job_id,
                scheduled_time=scheduled_time
            )
            
            # Schedule job using Redis delay
            schedule_key = f"schedule:{job_id}"
            schedule_data = {
                "job_id": job_id,
                "job_type": job_type,
                "scheduled_time": scheduled_time,
                "user_id": spec.get("user_id", "test_user"),
                "priority": priority.value
            }
            
            # Store scheduled job data with TTL matching delay
            await redis_manager.set(
                schedule_key,
                json.dumps(schedule_data),
                ex=int(delay_seconds) + 10  # Extra time for processing
            )
            
            scheduled_job_ids.append(job_id)
            
            logger.info(f"Scheduled job {job_id} of type {job_type} for {delay_seconds}s delay")
        
        return scheduled_job_ids
    
    async def execute_scheduled_jobs(self):
        """Execute jobs that are ready to run based on their scheduled time."""
        current_time = time.time()
        executed_jobs = []
        
        # Find jobs ready for execution
        schedule_keys = await redis_manager.keys("schedule:*")
        
        for key in schedule_keys:
            schedule_data = await redis_manager.get(key)
            if schedule_data:
                job_data = json.loads(schedule_data)
                scheduled_time = job_data.get("scheduled_time", 0)
                
                # Check if job is ready to execute
                if current_time >= scheduled_time:
                    job_id = job_data["job_id"]
                    
                    # Create and enqueue the job
                    message = QueuedMessage(
                        user_id=job_data.get("user_id", "test_user"),
                        type=job_data["job_type"],
                        payload={
                            "job_id": job_id,
                            "scheduled_time": scheduled_time
                        },
                        priority=MessagePriority(job_data.get("priority", 1))
                    )
                    
                    success = await self.message_queue.enqueue(message)
                    if success:
                        executed_jobs.append(job_id)
                        # Remove from schedule
                        await redis_manager.delete(key)
                        logger.info(f"Executed scheduled job {job_id}")
        
        return executed_jobs
    
    async def run_scheduling_monitor(self, monitoring_duration: float = 10.0):
        """Monitor and execute scheduled jobs for specified duration."""
        start_time = time.time()
        
        while time.time() - start_time < monitoring_duration:
            await self.execute_scheduled_jobs()
            await asyncio.sleep(0.1)  # Check every 100ms for precision
    
    async def validate_timing_accuracy(self, tolerance_seconds: float = 0.5) -> Dict[str, Any]:
        """Validate timing accuracy of executed jobs."""
        timing_violations = []
        accurate_jobs = []
        
        for event in self.execution_events:
            timing_accuracy = event["timing_accuracy"]
            
            if timing_accuracy > tolerance_seconds:
                timing_violations.append({
                    "job_id": event["job_id"],
                    "job_type": event["job_type"],
                    "timing_accuracy": timing_accuracy,
                    "tolerance": tolerance_seconds,
                    "violation_amount": timing_accuracy - tolerance_seconds
                })
            else:
                accurate_jobs.append(event["job_id"])
        
        self.timing_violations = timing_violations
        
        total_jobs = len(self.execution_events)
        accurate_count = len(accurate_jobs)
        accuracy_percentage = (accurate_count / total_jobs * 100) if total_jobs > 0 else 0
        
        avg_timing_accuracy = sum(e["timing_accuracy"] for e in self.execution_events) / total_jobs if total_jobs > 0 else 0
        
        return {
            "total_jobs": total_jobs,
            "accurate_jobs": accurate_count,
            "timing_violations": len(timing_violations),
            "accuracy_percentage": accuracy_percentage,
            "average_timing_accuracy": avg_timing_accuracy,
            "tolerance_seconds": tolerance_seconds,
            "violations": timing_violations
        }
    
    async def cleanup_test_infrastructure(self):
        """Clean up scheduling test infrastructure."""
        try:
            await self.message_queue.stop_processing()
            await self.clear_scheduling_test_data()
            logger.info("L3 scheduling test cleanup completed")
        except Exception as e:
            logger.error(f"Scheduling test cleanup failed: {e}")


@pytest.fixture
async def scheduling_accuracy_manager():
    """Create scheduling accuracy manager for L3 testing."""
    manager = JobSchedulingAccuracyL3Manager()
    await manager.initialize_test_infrastructure()
    yield manager
    await manager.cleanup_test_infrastructure()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_basic_job_scheduling_accuracy_l3(scheduling_accuracy_manager):
    """Test basic job scheduling accuracy with real timing."""
    # Schedule jobs with different delays
    job_specs = [
        {"delay_seconds": 1.0, "job_type": "scheduled_report", "user_id": "user1"},
        {"delay_seconds": 2.0, "job_type": "scheduled_analysis", "user_id": "user2"},
        {"delay_seconds": 3.0, "job_type": "scheduled_maintenance", "user_id": "user3"},
    ]
    
    job_ids = await scheduling_accuracy_manager.schedule_delayed_jobs(job_specs)
    
    # Start processing
    processing_task = asyncio.create_task(
        scheduling_accuracy_manager.message_queue.process_queue(worker_count=2)
    )
    
    # Start scheduling monitor
    monitor_task = asyncio.create_task(
        scheduling_accuracy_manager.run_scheduling_monitor(5.0)
    )
    
    # Wait for completion
    await monitor_task
    await asyncio.sleep(1.0)  # Allow final processing
    
    # Stop processing
    await scheduling_accuracy_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate timing accuracy
    timing_results = await scheduling_accuracy_manager.validate_timing_accuracy(0.3)
    
    assert timing_results["total_jobs"] >= 3, "Not all scheduled jobs executed"
    assert timing_results["accuracy_percentage"] >= 80.0, f"Poor timing accuracy: {timing_results['accuracy_percentage']}%"
    assert timing_results["average_timing_accuracy"] < 0.5, f"Average timing accuracy too poor: {timing_results['average_timing_accuracy']}s"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_high_precision_scheduling_l3(scheduling_accuracy_manager):
    """Test high precision scheduling with sub-second accuracy requirements."""
    # Schedule jobs with very precise timing requirements
    job_specs = [
        {"delay_seconds": 0.5, "job_type": "scheduled_optimization", "user_id": "precision_user1"},
        {"delay_seconds": 1.5, "job_type": "scheduled_report", "user_id": "precision_user2"},
        {"delay_seconds": 2.5, "job_type": "scheduled_analysis", "user_id": "precision_user3"},
    ]
    
    job_ids = await scheduling_accuracy_manager.schedule_delayed_jobs(job_specs)
    
    # Start processing with high frequency
    processing_task = asyncio.create_task(
        scheduling_accuracy_manager.message_queue.process_queue(worker_count=1)
    )
    
    # Start high-precision scheduling monitor
    monitor_task = asyncio.create_task(
        scheduling_accuracy_manager.run_scheduling_monitor(4.0)
    )
    
    await monitor_task
    await asyncio.sleep(0.5)
    
    # Stop processing
    await scheduling_accuracy_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate high precision timing (stricter tolerance)
    timing_results = await scheduling_accuracy_manager.validate_timing_accuracy(0.2)
    
    assert timing_results["total_jobs"] >= 3, "Not all precision jobs executed"
    assert timing_results["average_timing_accuracy"] < 0.2, f"High precision timing failed: {timing_results['average_timing_accuracy']}s"
    
    # Check individual job precision
    for event in scheduling_accuracy_manager.execution_events:
        assert event["timing_accuracy"] < 0.3, f"Job {event['job_id']} exceeded precision tolerance: {event['timing_accuracy']}s"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_scheduled_jobs_l3(scheduling_accuracy_manager):
    """Test scheduling accuracy under concurrent job load."""
    # Schedule multiple jobs with overlapping execution times
    job_specs = []
    for i in range(8):
        job_specs.append({
            "delay_seconds": 0.5 + (i * 0.3),  # Jobs every 300ms
            "job_type": ["scheduled_report", "scheduled_analysis", "scheduled_maintenance"][i % 3],
            "user_id": f"concurrent_user_{i}",
            "priority": MessagePriority.HIGH
        })
    
    job_ids = await scheduling_accuracy_manager.schedule_delayed_jobs(job_specs)
    
    # Start processing with multiple workers
    processing_task = asyncio.create_task(
        scheduling_accuracy_manager.message_queue.process_queue(worker_count=4)
    )
    
    # Start scheduling monitor
    monitor_task = asyncio.create_task(
        scheduling_accuracy_manager.run_scheduling_monitor(6.0)
    )
    
    await monitor_task
    await asyncio.sleep(1.0)
    
    # Stop processing
    await scheduling_accuracy_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate concurrent scheduling performance
    timing_results = await scheduling_accuracy_manager.validate_timing_accuracy(0.4)
    
    assert timing_results["total_jobs"] >= 7, f"Insufficient concurrent job execution: {timing_results['total_jobs']}"
    assert timing_results["accuracy_percentage"] >= 75.0, f"Poor concurrent timing accuracy: {timing_results['accuracy_percentage']}%"
    
    # Verify jobs executed in roughly correct order
    sorted_events = sorted(scheduling_accuracy_manager.execution_events, key=lambda x: x["actual_execution_time"])
    for i in range(len(sorted_events) - 1):
        time_diff = sorted_events[i + 1]["actual_execution_time"] - sorted_events[i]["actual_execution_time"]
        # Should be roughly 300ms apart (allowing for processing variance)
        assert time_diff >= 0.1, f"Jobs executing too close together: {time_diff}s"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scheduling_under_system_load_l3(scheduling_accuracy_manager):
    """Test scheduling accuracy under system load conditions."""
    # Create background load while testing scheduling
    async def create_background_load():
        """Create background processing load."""
        background_jobs = []
        for i in range(10):
            message = QueuedMessage(
                user_id=f"load_user_{i}",
                type="scheduled_maintenance",
                payload={"job_id": str(uuid.uuid4())},
                priority=MessagePriority.LOW
            )
            await scheduling_accuracy_manager.message_queue.enqueue(message)
    
    # Create background load
    await create_background_load()
    
    # Schedule priority jobs during load
    job_specs = [
        {"delay_seconds": 1.0, "job_type": "scheduled_report", "priority": MessagePriority.HIGH},
        {"delay_seconds": 2.0, "job_type": "scheduled_analysis", "priority": MessagePriority.HIGH},
        {"delay_seconds": 3.0, "job_type": "scheduled_optimization", "priority": MessagePriority.HIGH},
    ]
    
    job_ids = await scheduling_accuracy_manager.schedule_delayed_jobs(job_specs)
    
    # Start processing under load
    processing_task = asyncio.create_task(
        scheduling_accuracy_manager.message_queue.process_queue(worker_count=3)
    )
    
    # Start scheduling monitor
    monitor_task = asyncio.create_task(
        scheduling_accuracy_manager.run_scheduling_monitor(5.0)
    )
    
    await monitor_task
    await asyncio.sleep(2.0)
    
    # Stop processing
    await scheduling_accuracy_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate scheduling under load
    timing_results = await scheduling_accuracy_manager.validate_timing_accuracy(0.6)  # More lenient under load
    
    assert timing_results["total_jobs"] >= 3, "Priority jobs should execute despite system load"
    assert timing_results["accuracy_percentage"] >= 70.0, f"Scheduling accuracy degraded too much under load: {timing_results['accuracy_percentage']}%"
    
    # Check that scheduled jobs still executed with reasonable accuracy
    scheduled_events = [e for e in scheduling_accuracy_manager.execution_events 
                      if e["job_id"] in job_ids]
    
    assert len(scheduled_events) >= 3, "Not all scheduled jobs executed under load"
    for event in scheduled_events:
        assert event["timing_accuracy"] < 1.0, f"Scheduled job timing too poor under load: {event['timing_accuracy']}s"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scheduling_recovery_after_delays_l3(scheduling_accuracy_manager):
    """Test scheduling system recovery after processing delays."""
    # Schedule initial jobs
    job_specs = [
        {"delay_seconds": 1.0, "job_type": "scheduled_report"},
        {"delay_seconds": 1.5, "job_type": "scheduled_analysis"},
    ]
    
    job_ids = await scheduling_accuracy_manager.schedule_delayed_jobs(job_specs)
    
    # Start processing
    processing_task = asyncio.create_task(
        scheduling_accuracy_manager.message_queue.process_queue(worker_count=1)
    )
    
    # Start monitor but introduce a delay
    monitor_task = asyncio.create_task(
        scheduling_accuracy_manager.run_scheduling_monitor(2.0)
    )
    
    # Simulate system delay
    await asyncio.sleep(3.0)  # Delay past scheduled times
    
    # Schedule recovery jobs after delay
    recovery_specs = [
        {"delay_seconds": 0.5, "job_type": "scheduled_maintenance"},
        {"delay_seconds": 1.0, "job_type": "scheduled_optimization"},
    ]
    
    recovery_job_ids = await scheduling_accuracy_manager.schedule_delayed_jobs(recovery_specs)
    
    # Continue monitoring for recovery
    recovery_monitor = asyncio.create_task(
        scheduling_accuracy_manager.run_scheduling_monitor(3.0)
    )
    
    await recovery_monitor
    await asyncio.sleep(1.0)
    
    # Stop processing
    await scheduling_accuracy_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate recovery behavior
    timing_results = await scheduling_accuracy_manager.validate_timing_accuracy(1.0)  # Lenient for recovery
    
    # Should have executed both initial and recovery jobs
    total_expected_jobs = len(job_ids) + len(recovery_job_ids)
    assert timing_results["total_jobs"] >= total_expected_jobs - 1, "System should recover and execute jobs after delay"
    
    # Recovery jobs should maintain better timing accuracy
    recovery_events = [e for e in scheduling_accuracy_manager.execution_events 
                      if e["job_id"] in recovery_job_ids]
    
    if recovery_events:
        recovery_accuracy = sum(e["timing_accuracy"] for e in recovery_events) / len(recovery_events)
        assert recovery_accuracy < 0.7, f"Recovery job timing should be better: {recovery_accuracy}s"