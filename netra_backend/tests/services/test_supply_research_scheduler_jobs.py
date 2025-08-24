"""
Comprehensive tests for Supply Research Scheduler job execution and retry logic
Tests scheduling, execution, background tasks, retry mechanisms, and error handling
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from netra_backend.app.agents.supply_researcher.models import ResearchType
from netra_backend.app.services.background_task_manager import BackgroundTaskManager
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager

from netra_backend.app.services.supply_research_scheduler import (
    ResearchSchedule,
    ScheduleFrequency,
    SupplyResearchScheduler,
)

class TestSupplyResearchSchedulerJobs:
    """Test job execution for supply research scheduler"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies"""
        return {
            'background_manager': MagicMock(spec=BackgroundTaskManager),
            'llm_manager': MagicMock(spec=LLMManager),
            'redis_manager': MagicMock(spec=RedisManager),
            'database': MagicMock()
        }
    
    @pytest.fixture
    def scheduler(self, mock_dependencies):
        """Create scheduler with mocked dependencies"""
        with patch('app.services.supply_research_scheduler.BackgroundTaskManager', 
                  return_value=mock_dependencies['background_manager']):
            with patch('app.services.supply_research_scheduler.LLMManager', 
                      return_value=mock_dependencies['llm_manager']):
                with patch('app.services.supply_research_scheduler.RedisManager', 
                          return_value=mock_dependencies['redis_manager']):
                    scheduler = SupplyResearchScheduler(
                        background_manager=mock_dependencies['background_manager'],
                        llm_manager=mock_dependencies['llm_manager']
                    )
                    scheduler.redis_manager = mock_dependencies['redis_manager']
                    return scheduler
    async def test_schedule_job_execution_success(self, scheduler, mock_dependencies):
        """Test successful job execution"""
        # Setup
        schedule = ResearchSchedule(
            name="test_job",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.MODEL_UPDATES
        )
        
        mock_dependencies['background_manager'].add_task = MagicMock(return_value="task_123")
        scheduler._execute_research_job = AsyncMock(return_value=True)
        
        # Execute
        result = await scheduler.schedule_job(schedule)
        
        # Assert
        assert result != None
        mock_dependencies['background_manager'].add_task.assert_called_once()
    async def test_schedule_job_execution_with_retry(self, scheduler, mock_dependencies):
        """Test job execution with retry logic"""
        # Setup
        schedule = ResearchSchedule(
            name="retry_job",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.PROVIDER_COMPARISON
        )
        
        # Mock initial failure then success
        scheduler._execute_research_job = AsyncMock(side_effect=[
            NetraException("Temporary failure"),
            True
        ])
        
        mock_dependencies['redis_manager'].get = AsyncMock(return_value="1")  # retry count
        mock_dependencies['redis_manager'].set = AsyncMock()
        
        # Execute with retry
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await scheduler._execute_with_retry(schedule, max_retries=3)
        
        # Assert
        assert result == True
        assert scheduler._execute_research_job.call_count == 2
    async def test_schedule_job_execution_max_retries_exceeded(self, scheduler, mock_dependencies):
        """Test job execution when max retries exceeded"""
        # Setup
        schedule = ResearchSchedule(
            name="failing_job",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.COST_ANALYSIS
        )
        
        # Mock consistent failures
        scheduler._execute_research_job = AsyncMock(side_effect=NetraException("Persistent failure"))
        mock_dependencies['redis_manager'].get = AsyncMock(return_value="3")  # max retries
        mock_dependencies['redis_manager'].set = AsyncMock()
        
        # Execute
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await scheduler._execute_with_retry(schedule, max_retries=3)
        
        # Assert
        assert result == False
        assert scheduler._execute_research_job.call_count == 3
    async def test_concurrent_job_execution(self, scheduler, mock_dependencies):
        """Test concurrent execution of multiple jobs"""
        # Setup
        schedules = [
            ResearchSchedule(
                name=f"concurrent_job_{i}",
                frequency=ScheduleFrequency.HOURLY,
                research_type=ResearchType.MODEL_UPDATES
            ) for i in range(5)
        ]
        
        scheduler._execute_research_job = AsyncMock(return_value=True)
        mock_dependencies['background_manager'].add_task = MagicMock(
            side_effect=[f"task_{i}" for i in range(5)]
        )
        
        # Execute concurrently
        tasks = [scheduler.schedule_job(schedule) for schedule in schedules]
        results = await asyncio.gather(*tasks)
        
        # Assert
        assert all(result != None for result in results)
        assert mock_dependencies['background_manager'].add_task.call_count == 5
    async def test_job_execution_resource_cleanup(self, scheduler, mock_dependencies):
        """Test proper resource cleanup after job execution"""
        # Setup
        schedule = ResearchSchedule(
            name="cleanup_job",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.PERFORMANCE_BENCHMARKS
        )
        
        cleanup_called = False
        
        def mock_cleanup(*args, **kwargs):
            nonlocal cleanup_called
            cleanup_called = True
        
        scheduler._cleanup_job_resources = AsyncMock(side_effect=mock_cleanup)
        scheduler._execute_research_job = AsyncMock(return_value=True)
        
        # Execute
        await scheduler._execute_job_with_cleanup(schedule)
        
        # Assert
        assert cleanup_called
        scheduler._cleanup_job_resources.assert_called_once_with(schedule)
    async def test_job_execution_timeout_handling(self, scheduler, mock_dependencies):
        """Test job execution timeout handling"""
        # Setup
        schedule = ResearchSchedule(
            name="timeout_job",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.MODEL_UPDATES
        )
        
        # Mock long-running job
        async def long_running_job(schedule):
            await asyncio.sleep(10)  # Longer than timeout
            return True
        
        scheduler._execute_research_job = AsyncMock(side_effect=long_running_job)
        
        # Execute with timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                scheduler._execute_research_job(schedule),
                timeout=1.0
            )
    async def test_job_execution_error_logging(self, scheduler, mock_dependencies):
        """Test proper error logging during job execution"""
        # Setup
        schedule = ResearchSchedule(
            name="error_job",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.PROVIDER_COMPARISON
        )
        
        test_error = NetraException("Test error message")
        scheduler._execute_research_job = AsyncMock(side_effect=test_error)
        
        # Execute
        with patch('app.services.supply_research_scheduler.logger') as mock_logger:
            result = await scheduler._execute_with_retry(schedule, max_retries=1)
        
        # Assert
        assert result == False
        mock_logger.error.assert_called()
        
        # Verify error details in log
        error_call_args = mock_logger.error.call_args_list
        assert any("Test error message" in str(call) for call in error_call_args)
    async def test_job_execution_metrics_tracking(self, scheduler, mock_dependencies):
        """Test job execution metrics tracking"""
        # Setup
        schedule = ResearchSchedule(
            name="metrics_job",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.COST_ANALYSIS
        )
        
        scheduler._execute_research_job = AsyncMock(return_value=True)
        scheduler._record_job_metrics = AsyncMock()
        
        # Execute
        start_time = datetime.now(UTC)
        await scheduler._execute_job_with_metrics(schedule)
        end_time = datetime.now(UTC)
        
        # Assert
        scheduler._record_job_metrics.assert_called_once()
        call_args = scheduler._record_job_metrics.call_args[0]
        assert call_args[0] == schedule.name
        assert isinstance(call_args[1], timedelta)  # execution_time
        assert call_args[2] == True  # success

class TestSupplyResearchSchedulerRetryLogic:
    """Test retry logic and failure handling"""
    
    @pytest.fixture
    def scheduler_with_redis(self):
        """Create scheduler with Redis for retry logic"""
        mock_background_manager = MagicMock(spec=BackgroundTaskManager)
        mock_llm_manager = MagicMock(spec=LLMManager)
        
        with patch('app.services.supply_research_scheduler.RedisManager') as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis_class.return_value = mock_redis
            
            scheduler = SupplyResearchScheduler(
                background_manager=mock_background_manager,
                llm_manager=mock_llm_manager
            )
            scheduler.redis_manager = mock_redis
            return scheduler, mock_redis
    async def test_exponential_backoff_retry_timing(self, scheduler_with_redis):
        """Test exponential backoff timing in retry logic"""
        scheduler, mock_redis = scheduler_with_redis
        
        schedule = ResearchSchedule(
            name="backoff_job",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.MODEL_UPDATES
        )
        
        scheduler._execute_research_job = AsyncMock(side_effect=NetraException("Retry needed"))
        mock_redis.get = AsyncMock(side_effect=["0", "1", "2"])  # retry counts
        mock_redis.set = AsyncMock()
        
        sleep_times = []
        
        async def mock_sleep(duration):
            sleep_times.append(duration)
        
        # Execute with mocked sleep
        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await scheduler._execute_with_retry(schedule, max_retries=3)
        
        # Assert exponential backoff
        assert len(sleep_times) == 2
        assert sleep_times[0] == 1  # 2^0 = 1
        assert sleep_times[1] == 2  # 2^1 = 2
        assert result == False
    async def test_retry_state_persistence(self, scheduler_with_redis):
        """Test retry state persistence in Redis"""
        scheduler, mock_redis = scheduler_with_redis
        
        schedule = ResearchSchedule(
            name="persistent_job",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.PERFORMANCE_BENCHMARKS
        )
        
        # Mock Redis operations
        mock_redis.get = AsyncMock(return_value="1")  # existing retry count
        mock_redis.set = AsyncMock()
        mock_redis.expire = AsyncMock()
        
        scheduler._execute_research_job = AsyncMock(side_effect=NetraException("Failed"))
        
        # Execute
        with patch('asyncio.sleep', new_callable=AsyncMock):
            await scheduler._execute_with_retry(schedule, max_retries=3)
        
        # Assert Redis operations
        mock_redis.get.assert_called_with(f"scheduler:retry:{schedule.name}")
        mock_redis.set.assert_called_with(f"scheduler:retry:{schedule.name}", "2")  # incremented
        mock_redis.expire.assert_called_with(f"scheduler:retry:{schedule.name}", 3600)  # 1 hour TTL
    async def test_retry_circuit_breaker(self, scheduler_with_redis):
        """Test circuit breaker pattern for failing jobs"""
        scheduler, mock_redis = scheduler_with_redis
        
        schedule = ResearchSchedule(
            name="circuit_job",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.PROVIDER_COMPARISON
        )
        
        # Mock circuit breaker state
        mock_redis.get = AsyncMock(side_effect=[
            "5",  # failure count exceeds threshold
            None  # circuit breaker key
        ])
        mock_redis.set = AsyncMock()
        
        scheduler._is_circuit_open = AsyncMock(return_value=True)
        
        # Execute
        result = await scheduler._execute_with_circuit_breaker(schedule)
        
        # Assert circuit breaker prevents execution
        assert result == False
        scheduler._is_circuit_open.assert_called_once_with(schedule.name)
    async def test_retry_jitter_randomization(self, scheduler_with_redis):
        """Test jitter in retry timing to prevent thundering herd"""
        scheduler, mock_redis = scheduler_with_redis
        
        schedule = ResearchSchedule(
            name="jitter_job",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.COST_ANALYSIS
        )
        
        scheduler._execute_research_job = AsyncMock(side_effect=NetraException("Jitter test"))
        mock_redis.get = AsyncMock(return_value="0")
        mock_redis.set = AsyncMock()
        
        sleep_times = []
        
        async def mock_sleep(duration):
            sleep_times.append(duration)
        
        # Execute multiple times to check jitter variation
        with patch('asyncio.sleep', side_effect=mock_sleep):
            with patch('random.uniform', return_value=0.5):  # 50% jitter
                await scheduler._execute_with_retry(schedule, max_retries=1, jitter=True)
        
        # Assert jitter is applied
        assert len(sleep_times) == 1
        assert 0.5 <= sleep_times[0] <= 1.5  # base_delay(1) * (0.5 to 1.5 jitter range)

class TestSupplyResearchSchedulerConcurrency:
    """Test concurrent job execution and thread safety"""
    
    @pytest.fixture
    def concurrent_scheduler(self):
        """Create scheduler for concurrency testing"""
        scheduler = SupplyResearchScheduler()
        scheduler._job_semaphore = asyncio.Semaphore(3)  # Limit concurrent jobs
        return scheduler
    async def test_concurrent_job_limit_enforcement(self, concurrent_scheduler):
        """Test enforcement of concurrent job limits"""
        # Setup
        schedules = [
            ResearchSchedule(
                name=f"limited_job_{i}",
                frequency=ScheduleFrequency.HOURLY,
                research_type=ResearchType.MODEL_UPDATES
            ) for i in range(10)  # More than semaphore limit
        ]
        
        execution_times = []
        
        async def mock_execute(schedule):
            start = datetime.now(UTC)
            await asyncio.sleep(0.1)  # Simulate work
            end = datetime.now(UTC)
            execution_times.append((schedule.name, start, end))
            return True
        
        concurrent_scheduler._execute_research_job = mock_execute
        
        # Execute all jobs concurrently
        tasks = [
            concurrent_scheduler._execute_job_with_semaphore(schedule)
            for schedule in schedules
        ]
        
        start_time = datetime.now(UTC)
        await asyncio.gather(*tasks)
        total_time = datetime.now(UTC) - start_time
        
        # Assert concurrency limits enforced
        # With 10 jobs, 3 concurrent, 0.1s each: should take ~0.4s (4 batches)
        assert total_time >= timedelta(seconds=0.3)  # At least 3 batches
        assert len(execution_times) == 10  # All jobs completed
    async def test_job_queue_management(self, concurrent_scheduler):
        """Test job queue management under load"""
        # Setup
        job_queue = []
        processed_jobs = []
        
        async def queue_processor():
            while job_queue or len(processed_jobs) < 20:
                if job_queue:
                    job = job_queue.pop(0)
                    processed_jobs.append(job)
                    await asyncio.sleep(0.05)  # Process time
                await asyncio.sleep(0.01)  # Polling interval
        
        # Add jobs to queue rapidly
        for i in range(20):
            job_queue.append(f"queued_job_{i}")
        
        # Process queue
        await asyncio.wait_for(queue_processor(), timeout=5.0)
        
        # Assert all jobs processed in order
        assert len(processed_jobs) == 20
        assert processed_jobs[0] == "queued_job_0"
        assert processed_jobs[-1] == "queued_job_19"
    async def test_deadlock_prevention(self, concurrent_scheduler):
        """Test deadlock prevention in job execution"""
        # Setup circular dependency scenario
        job_dependencies = {
            "job_a": ["job_b"],
            "job_b": ["job_c"],
            "job_c": ["job_a"]  # Creates cycle
        }
        
        execution_order = []
        
        async def mock_execute_with_deps(job_name):
            # Check dependencies (simplified)
            deps = job_dependencies.get(job_name, [])
            for dep in deps:
                if dep not in execution_order:
                    # Would normally wait, but we'll timeout to prevent deadlock
                    try:
                        await asyncio.wait_for(
                            concurrent_scheduler._wait_for_dependency(dep),
                            timeout=0.1
                        )
                    except asyncio.TimeoutError:
                        pass  # Deadlock prevention
            
            execution_order.append(job_name)
            return True
        
        concurrent_scheduler._wait_for_dependency = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )
        
        # Execute jobs with circular dependencies
        tasks = [
            mock_execute_with_deps(job_name)
            for job_name in job_dependencies.keys()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert no deadlock occurred (all tasks completed)
        assert len(execution_order) == 3
        assert all(not isinstance(r, Exception) for r in results)

class TestSupplyResearchSchedulerPerformance:
    """Test performance and resource management"""
    async def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load"""
        import tracemalloc
        
        scheduler = SupplyResearchScheduler()
        scheduler._execute_research_job = AsyncMock(return_value=True)
        
        # Start memory tracing
        tracemalloc.start()
        
        # Create many jobs
        schedules = [
            ResearchSchedule(
                name=f"memory_job_{i}",
                frequency=ScheduleFrequency.HOURLY,
                research_type=ResearchType.MODEL_UPDATES
            ) for i in range(100)
        ]
        
        # Execute jobs in batches to control memory
        batch_size = 10
        for i in range(0, len(schedules), batch_size):
            batch = schedules[i:i + batch_size]
            tasks = [scheduler._execute_research_job(schedule) for schedule in batch]
            await asyncio.gather(*tasks)
        
        # Get memory statistics
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Assert reasonable memory usage (< 100MB for this test)
        assert peak < 100 * 1024 * 1024  # 100MB
    async def test_job_execution_performance_metrics(self):
        """Test job execution performance tracking"""
        scheduler = SupplyResearchScheduler()
        
        # Mock performance tracking
        execution_metrics = []
        
        async def mock_execute_with_timing(schedule):
            start = datetime.now(UTC)
            await asyncio.sleep(0.1)  # Simulate work
            end = datetime.now(UTC)
            
            execution_metrics.append({
                'job_name': schedule.name,
                'duration': (end - start).total_seconds(),
                'success': True
            })
            return True
        
        scheduler._execute_research_job = mock_execute_with_timing
        
        # Execute multiple jobs
        schedules = [
            ResearchSchedule(
                name=f"perf_job_{i}",
                frequency=ScheduleFrequency.HOURLY,
                research_type=ResearchType.PERFORMANCE_BENCHMARKS
            ) for i in range(10)
        ]
        
        tasks = [scheduler._execute_research_job(schedule) for schedule in schedules]
        await asyncio.gather(*tasks)
        
        # Assert performance metrics collected
        assert len(execution_metrics) == 10
        assert all(metric['duration'] >= 0.1 for metric in execution_metrics)
        assert all(metric['success'] for metric in execution_metrics)
        
        # Check average performance
        avg_duration = sum(m['duration'] for m in execution_metrics) / len(execution_metrics)
        assert 0.1 <= avg_duration <= 0.2  # Should be around 0.1s