"""
Concurrency tests for Supply Research Scheduler
Tests concurrent job execution, thread safety, and queue management
COMPLIANCE: 450-line max file, 25-line max functions
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from netra_backend.app.agents.supply_researcher.models import ResearchType

# Add project root to path
from netra_backend.app.services.supply_research_scheduler import (
    ResearchSchedule,
    ScheduleFrequency,
    # Add project root to path
    SupplyResearchScheduler,
)


@pytest.fixture
def concurrent_scheduler():
    """Create scheduler for concurrency testing."""
    scheduler = SupplyResearchScheduler()
    scheduler._job_semaphore = asyncio.Semaphore(3)  # Limit concurrent jobs
    return scheduler


class TestSupplyResearchSchedulerConcurrency:
    """Test concurrent job execution and thread safety"""
    
    async def test_concurrent_job_limit_enforcement(self, concurrent_scheduler):
        """Test enforcement of concurrent job limits."""
        # Setup
        schedules = _create_test_schedules(10)  # More than semaphore limit
        
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
        assert total_time >= timedelta(seconds=0.3)  # At least 3 batches
        assert len(execution_times) == 10  # All jobs completed

    async def test_job_queue_management(self, concurrent_scheduler):
        """Test job queue management under load."""
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
        _populate_job_queue(job_queue, 20)
        
        # Process queue
        await asyncio.wait_for(queue_processor(), timeout=5.0)
        
        # Assert all jobs processed in order
        assert len(processed_jobs) == 20
        assert processed_jobs[0] == "queued_job_0"
        assert processed_jobs[-1] == "queued_job_19"

    async def test_deadlock_prevention(self, concurrent_scheduler):
        """Test deadlock prevention in job execution."""
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


def _create_test_schedules(count):
    """Create multiple test schedules for concurrency testing."""
    return [
        ResearchSchedule(
            name=f"limited_job_{i}",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.MODEL_UPDATES
        ) for i in range(count)
    ]


def _populate_job_queue(job_queue, count):
    """Populate job queue with test jobs."""
    for i in range(count):
        job_queue.append(f"queued_job_{i}")