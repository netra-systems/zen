"""
L3-11: Background Job Processing with Real Redis Queue Integration Test

BVJ: Ensures reliable async task processing for AI workloads, critical for
handling long-running LLM operations and maintaining system responsiveness.

Tests background job processing with real Redis containers and job queues.
"""

import pytest
import asyncio
import docker
import time
import json
import uuid
from typing import Dict, Any, List, Optional
import redis.asyncio as aioredis
from background_jobs.job_manager import JobManager
from background_jobs.worker import JobWorker
from background_jobs.queue import RedisQueue


@pytest.mark.L3
class TestBackgroundJobsRedisQueueL3:
    """Test background job processing with real Redis queue."""
    
    @pytest.fixture(scope="class")
    async def docker_client(self):
        """Docker client for container management."""
        client = docker.from_env()
        yield client
        client.close()
    
    @pytest.fixture(scope="class")
    async def redis_container(self, docker_client):
        """Start Redis container for testing."""
        container = docker_client.containers.run(
            "redis:7-alpine",
            ports={'6379/tcp': None},
            detach=True,
            name="jobs_test_redis"
        )
        
        # Get assigned port
        container.reload()
        port = container.attrs['NetworkSettings']['Ports']['6379/tcp'][0]['HostPort']
        
        # Wait for Redis to be ready
        await self._wait_for_redis(port)
        
        redis_config = {
            "host": "localhost",
            "port": int(port),
            "db": 0
        }
        
        yield redis_config
        
        container.stop()
        container.remove()
    
    async def _wait_for_redis(self, port: str, timeout: int = 30):
        """Wait for Redis to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                redis_client = aioredis.Redis(
                    host="localhost",
                    port=int(port),
                    decode_responses=True
                )
                await redis_client.ping()
                await redis_client.close()
                return
            except:
                await asyncio.sleep(0.5)
        raise TimeoutError(f"Redis not ready within {timeout}s")
    
    @pytest.fixture
    async def job_manager(self, redis_container):
        """Create job manager with Redis backend."""
        manager = JobManager(redis_config=redis_container)
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    async def job_queue(self, redis_container):
        """Create Redis job queue."""
        queue = RedisQueue("test_jobs", redis_config=redis_container)
        await queue.initialize()
        yield queue
        await queue.cleanup()
    
    @pytest.fixture
    async def job_worker(self, redis_container):
        """Create job worker."""
        worker = JobWorker(redis_config=redis_container, worker_id="test_worker")
        await worker.initialize()
        yield worker
        await worker.stop()
    
    @pytest.mark.asyncio
    async def test_job_enqueue_and_dequeue(self, job_queue):
        """Test basic job enqueue and dequeue operations."""
        # Enqueue a test job
        job_data = {
            "type": "test_job",
            "payload": {"message": "Hello, World!"},
            "priority": 1
        }
        
        job_id = await job_queue.enqueue(job_data)
        assert job_id is not None
        
        # Dequeue the job
        dequeued_job = await job_queue.dequeue()
        
        assert dequeued_job is not None
        assert dequeued_job["id"] == job_id
        assert dequeued_job["type"] == "test_job"
        assert dequeued_job["payload"]["message"] == "Hello, World!"
    
    @pytest.mark.asyncio
    async def test_job_priority_ordering(self, job_queue):
        """Test that jobs are processed in priority order."""
        # Enqueue jobs with different priorities
        low_priority_job = {
            "type": "low_priority",
            "payload": {"order": 3},
            "priority": 1
        }
        
        high_priority_job = {
            "type": "high_priority", 
            "payload": {"order": 1},
            "priority": 3
        }
        
        medium_priority_job = {
            "type": "medium_priority",
            "payload": {"order": 2},
            "priority": 2
        }
        
        # Enqueue in random order
        await job_queue.enqueue(low_priority_job)
        await job_queue.enqueue(high_priority_job)
        await job_queue.enqueue(medium_priority_job)
        
        # Dequeue jobs - should come out in priority order
        first_job = await job_queue.dequeue()
        second_job = await job_queue.dequeue()
        third_job = await job_queue.dequeue()
        
        assert first_job["payload"]["order"] == 1  # High priority
        assert second_job["payload"]["order"] == 2  # Medium priority
        assert third_job["payload"]["order"] == 3   # Low priority
    
    @pytest.mark.asyncio
    async def test_job_worker_processing(self, job_manager, job_worker):
        """Test job worker processing jobs from queue."""
        results = []
        
        # Define job handler
        async def test_job_handler(job_data):
            results.append(job_data["payload"])
            return {"status": "completed", "result": job_data["payload"]["value"] * 2}
        
        # Register job handler
        job_worker.register_handler("math_job", test_job_handler)
        
        # Start worker
        worker_task = asyncio.create_task(job_worker.start())
        
        # Enqueue test jobs
        for i in range(3):
            await job_manager.enqueue_job(
                "math_job",
                {"value": i + 1},
                priority=1
            )
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Stop worker
        await job_worker.stop()
        worker_task.cancel()
        
        # Verify all jobs were processed
        assert len(results) == 3
        assert {"value": 1} in results
        assert {"value": 2} in results
        assert {"value": 3} in results
    
    @pytest.mark.asyncio
    async def test_job_retry_mechanism(self, job_manager, job_worker):
        """Test job retry mechanism on failures."""
        attempt_count = 0
        
        async def failing_job_handler(job_data):
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:
                raise Exception(f"Attempt {attempt_count} failed")
            
            return {"status": "completed", "attempts": attempt_count}
        
        # Register failing job handler
        job_worker.register_handler("failing_job", failing_job_handler)
        
        # Start worker
        worker_task = asyncio.create_task(job_worker.start())
        
        # Enqueue failing job with retry policy
        job_id = await job_manager.enqueue_job(
            "failing_job",
            {"test": "data"},
            retry_policy={
                "max_retries": 3,
                "retry_delay": 0.1
            }
        )
        
        # Wait for processing and retries
        await asyncio.sleep(3)
        
        # Stop worker
        await job_worker.stop()
        worker_task.cancel()
        
        # Verify job eventually succeeded
        job_status = await job_manager.get_job_status(job_id)
        assert job_status["status"] == "completed"
        assert attempt_count == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_job_processing(self, job_manager, redis_container):
        """Test concurrent job processing with multiple workers."""
        # Create multiple workers
        workers = []
        for i in range(3):
            worker = JobWorker(
                redis_config=redis_container,
                worker_id=f"worker_{i}"
            )
            await worker.initialize()
            workers.append(worker)
        
        results = []
        
        async def concurrent_job_handler(job_data):
            await asyncio.sleep(0.1)  # Simulate work
            results.append(job_data["payload"]["job_number"])
            return {"status": "completed"}
        
        # Register handlers on all workers
        for worker in workers:
            worker.register_handler("concurrent_job", concurrent_job_handler)
        
        # Start all workers
        worker_tasks = []
        for worker in workers:
            task = asyncio.create_task(worker.start())
            worker_tasks.append(task)
        
        # Enqueue many jobs
        job_count = 10
        for i in range(job_count):
            await job_manager.enqueue_job(
                "concurrent_job",
                {"job_number": i},
                priority=1
            )
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Stop all workers
        for worker in workers:
            await worker.stop()
        for task in worker_tasks:
            task.cancel()
        
        # Verify all jobs were processed
        assert len(results) == job_count
        assert set(results) == set(range(job_count))
    
    @pytest.mark.asyncio
    async def test_job_scheduling_and_delayed_execution(self, job_manager, job_worker):
        """Test scheduling jobs for future execution."""
        execution_times = []
        
        async def scheduled_job_handler(job_data):
            execution_times.append(time.time())
            return {"status": "completed"}
        
        job_worker.register_handler("scheduled_job", scheduled_job_handler)
        
        # Start worker
        worker_task = asyncio.create_task(job_worker.start())
        
        start_time = time.time()
        
        # Schedule job for 1 second in the future
        schedule_time = start_time + 1.0
        await job_manager.schedule_job(
            "scheduled_job",
            {"message": "delayed execution"},
            scheduled_at=schedule_time
        )
        
        # Schedule another job for 2 seconds in the future
        schedule_time_2 = start_time + 2.0
        await job_manager.schedule_job(
            "scheduled_job",
            {"message": "more delayed execution"},
            scheduled_at=schedule_time_2
        )
        
        # Wait for jobs to execute
        await asyncio.sleep(3)
        
        # Stop worker
        await job_worker.stop()
        worker_task.cancel()
        
        # Verify jobs executed at correct times
        assert len(execution_times) == 2
        assert execution_times[0] >= start_time + 0.9  # First job
        assert execution_times[1] >= start_time + 1.9  # Second job
        assert execution_times[1] > execution_times[0]  # Order maintained
    
    @pytest.mark.asyncio
    async def test_job_queue_persistence(self, redis_container):
        """Test that jobs persist across queue restarts."""
        # Create first queue instance
        queue1 = RedisQueue("persistent_jobs", redis_config=redis_container)
        await queue1.initialize()
        
        # Enqueue jobs
        job_data = {
            "type": "persistent_job",
            "payload": {"data": "should persist"},
            "priority": 1
        }
        
        job_id = await queue1.enqueue(job_data)
        await queue1.cleanup()
        
        # Create second queue instance (simulating restart)
        queue2 = RedisQueue("persistent_jobs", redis_config=redis_container)
        await queue2.initialize()
        
        # Dequeue job - should still be there
        dequeued_job = await queue2.dequeue()
        
        assert dequeued_job is not None
        assert dequeued_job["id"] == job_id
        assert dequeued_job["payload"]["data"] == "should persist"
        
        await queue2.cleanup()
    
    @pytest.mark.asyncio
    async def test_job_progress_tracking(self, job_manager, job_worker):
        """Test job progress tracking and status updates."""
        progress_updates = []
        
        async def progress_job_handler(job_data):
            # Simulate work with progress updates
            for i in range(5):
                await job_worker.update_job_progress(job_data["id"], i * 20)
                progress_updates.append(i * 20)
                await asyncio.sleep(0.1)
            
            return {"status": "completed", "final_result": "done"}
        
        job_worker.register_handler("progress_job", progress_job_handler)
        
        # Start worker
        worker_task = asyncio.create_task(job_worker.start())
        
        # Enqueue job
        job_id = await job_manager.enqueue_job(
            "progress_job",
            {"work": "progress tracking test"}
        )
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Check job progress
        job_status = await job_manager.get_job_status(job_id)
        
        # Stop worker
        await job_worker.stop()
        worker_task.cancel()
        
        # Verify progress was tracked
        assert job_status["status"] == "completed"
        assert job_status["progress"] == 80  # Last progress update
        assert len(progress_updates) == 5
    
    @pytest.mark.asyncio
    async def test_dead_letter_queue(self, job_manager, job_worker):
        """Test dead letter queue for permanently failed jobs."""
        async def always_failing_job_handler(job_data):
            raise Exception("This job always fails")
        
        job_worker.register_handler("failing_job", always_failing_job_handler)
        
        # Start worker
        worker_task = asyncio.create_task(job_worker.start())
        
        # Enqueue job with limited retries
        job_id = await job_manager.enqueue_job(
            "failing_job",
            {"test": "permanent failure"},
            retry_policy={
                "max_retries": 2,
                "retry_delay": 0.1
            }
        )
        
        # Wait for failure and retries
        await asyncio.sleep(2)
        
        # Stop worker
        await job_worker.stop()
        worker_task.cancel()
        
        # Check job ended up in dead letter queue
        job_status = await job_manager.get_job_status(job_id)
        assert job_status["status"] == "failed"
        
        # Check dead letter queue
        dead_jobs = await job_manager.get_dead_letter_jobs()
        dead_job_ids = [job["id"] for job in dead_jobs]
        assert job_id in dead_job_ids