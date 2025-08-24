"""
Core job execution tests for Supply Research Scheduler
Tests basic job scheduling, execution, and resource cleanup
COMPLIANCE: 450-line max file, 25-line max functions
"""

import sys
from pathlib import Path

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import pytest
from netra_backend.app.services.background_task_manager import BackgroundTaskManager

from netra_backend.app.agents.supply_researcher.models import ResearchType
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager

from netra_backend.app.services.supply_research_scheduler import (
    ResearchSchedule,
    ScheduleFrequency,
    SupplyResearchScheduler,
)

@pytest.fixture
def mock_dependencies():
    """Mock all scheduler dependencies."""
    return {
        # Mock: Background task isolation to prevent real tasks during testing
        'background_manager': MagicMock(spec=BackgroundTaskManager),
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        'llm_manager': MagicMock(spec=LLMManager),
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        'redis_manager': MagicMock(spec=RedisManager),
        # Mock: Database access isolation for fast, reliable unit testing
        'database': MagicMock()
    }

@pytest.fixture
def scheduler(mock_dependencies):
    """Create scheduler with mocked dependencies."""
    # Mock: Component isolation for testing without external dependencies
    with patch('app.services.supply_research_scheduler.BackgroundTaskManager', 
              return_value=mock_dependencies['background_manager']):
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.supply_research_scheduler.LLMManager', 
                  return_value=mock_dependencies['llm_manager']):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.services.supply_research_scheduler.RedisManager', 
                      return_value=mock_dependencies['redis_manager']):
                scheduler = SupplyResearchScheduler(
                    background_manager=mock_dependencies['background_manager'],
                    llm_manager=mock_dependencies['llm_manager']
                )
                scheduler.redis_manager = mock_dependencies['redis_manager']
                return scheduler

class TestSupplyResearchSchedulerJobs:
    """Test job execution for supply research scheduler"""
    
    @pytest.mark.asyncio
    async def test_schedule_job_execution_success(self, scheduler, mock_dependencies):
        """Test successful job execution."""
        # Setup
        schedule = _create_test_schedule("test_job", ResearchType.MODEL_UPDATES)
        
        # Mock: Background task isolation to prevent real tasks during testing
        mock_dependencies['background_manager'].add_task = MagicMock(return_value="task_123")
        # Mock: Async component isolation for testing without real async operations
        scheduler._execute_research_job = AsyncMock(return_value=True)
        
        # Execute
        result = await scheduler.schedule_job(schedule)
        
        # Assert
        assert result != None
        mock_dependencies['background_manager'].add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_job_execution_with_retry(self, scheduler, mock_dependencies):
        """Test job execution with retry logic."""
        # Setup
        schedule = _create_test_schedule("retry_job", ResearchType.PROVIDER_COMPARISON)
        
        # Mock initial failure then success
        # Mock: Async component isolation for testing without real async operations
        scheduler._execute_research_job = AsyncMock(side_effect=[
            NetraException("Temporary failure"),
            True
        ])
        
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_dependencies['redis_manager'].get = AsyncMock(return_value="1")
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_dependencies['redis_manager'].set = AsyncMock()
        
        # Execute with retry
        # Mock: Async component isolation for testing without real async operations
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await scheduler._execute_with_retry(schedule, max_retries=3)
        
        # Assert
        assert result == True
        assert scheduler._execute_research_job.call_count == 2

    @pytest.mark.asyncio
    async def test_schedule_job_execution_max_retries_exceeded(self, scheduler, mock_dependencies):
        """Test job execution when max retries exceeded."""
        # Setup
        schedule = _create_test_schedule("failing_job", ResearchType.COST_ANALYSIS)
        
        # Mock consistent failures
        # Mock: Async component isolation for testing without real async operations
        scheduler._execute_research_job = AsyncMock(side_effect=NetraException("Persistent failure"))
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_dependencies['redis_manager'].get = AsyncMock(return_value="3")
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_dependencies['redis_manager'].set = AsyncMock()
        
        # Execute
        # Mock: Async component isolation for testing without real async operations
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await scheduler._execute_with_retry(schedule, max_retries=3)
        
        # Assert
        assert result == False
        assert scheduler._execute_research_job.call_count == 3

    @pytest.mark.asyncio
    async def test_concurrent_job_execution(self, scheduler, mock_dependencies):
        """Test concurrent execution of multiple jobs."""
        # Setup
        schedules = _create_concurrent_schedules(5)
        
        # Mock: Async component isolation for testing without real async operations
        scheduler._execute_research_job = AsyncMock(return_value=True)
        # Mock: Background task isolation to prevent real tasks during testing
        mock_dependencies['background_manager'].add_task = MagicMock(
            side_effect=[f"task_{i}" for i in range(5)]
        )
        
        # Execute concurrently
        tasks = [scheduler.schedule_job(schedule) for schedule in schedules]
        results = await asyncio.gather(*tasks)
        
        # Assert
        assert all(result != None for result in results)
        assert mock_dependencies['background_manager'].add_task.call_count == 5

    @pytest.mark.asyncio
    async def test_job_execution_resource_cleanup(self, scheduler, mock_dependencies):
        """Test proper resource cleanup after job execution."""
        # Setup
        schedule = _create_test_schedule("cleanup_job", ResearchType.PERFORMANCE_BENCHMARKS)
        
        cleanup_called = False
        
        async def mock_cleanup(*args, **kwargs):
            nonlocal cleanup_called
            cleanup_called = True
        
        # Mock: Async component isolation for testing without real async operations
        scheduler._cleanup_job_resources = AsyncMock(side_effect=mock_cleanup)
        # Mock: Async component isolation for testing without real async operations
        scheduler._execute_research_job = AsyncMock(return_value=True)
        
        # Execute
        await scheduler._execute_job_with_cleanup(schedule)
        
        # Assert
        assert cleanup_called
        scheduler._cleanup_job_resources.assert_called_once_with(schedule)

    @pytest.mark.asyncio
    async def test_job_execution_timeout_handling(self, scheduler, mock_dependencies):
        """Test job execution timeout handling."""
        # Setup
        schedule = _create_test_schedule("timeout_job", ResearchType.MODEL_UPDATES)
        
        # Mock long-running job
        async def long_running_job(schedule):
            await asyncio.sleep(10)
            return True
        
        # Mock: Async component isolation for testing without real async operations
        scheduler._execute_research_job = AsyncMock(side_effect=long_running_job)
        
        # Execute with timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                scheduler._execute_research_job(schedule),
                timeout=1.0
            )

    @pytest.mark.asyncio
    async def test_job_execution_error_logging(self, scheduler, mock_dependencies):
        """Test proper error logging during job execution."""
        # Setup
        schedule = _create_test_schedule("error_job", ResearchType.PROVIDER_COMPARISON)
        
        test_error = NetraException("Test error message")
        # Mock: Async component isolation for testing without real async operations
        scheduler._execute_research_job = AsyncMock(side_effect=test_error)
        
        # Execute
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.supply_research_scheduler.logger') as mock_logger:
            result = await scheduler._execute_with_retry(schedule, max_retries=1)
        
        # Assert
        assert result == False
        mock_logger.error.assert_called()
        
        # Verify error details in log
        error_call_args = mock_logger.error.call_args_list
        assert any("Test error message" in str(call) for call in error_call_args)

    @pytest.mark.asyncio
    async def test_job_execution_metrics_tracking(self, scheduler, mock_dependencies):
        """Test job execution metrics tracking."""
        # Setup
        schedule = _create_test_schedule("metrics_job", ResearchType.COST_ANALYSIS)
        
        # Mock: Async component isolation for testing without real async operations
        scheduler._execute_research_job = AsyncMock(return_value=True)
        # Mock: Generic component isolation for controlled unit testing
        scheduler._record_job_metrics = AsyncMock()
        
        # Execute
        start_time = datetime.now(UTC)
        await scheduler._execute_job_with_metrics(schedule)
        end_time = datetime.now(UTC)
        
        # Assert
        scheduler._record_job_metrics.assert_called_once()
        call_args = scheduler._record_job_metrics.call_args[0]
        assert call_args[0] == schedule.name
        assert isinstance(call_args[1], timedelta)
        assert call_args[2] == True

def _create_test_schedule(name, research_type):
    """Create test schedule with given parameters."""
    return ResearchSchedule(
        name=name,
        frequency=ScheduleFrequency.DAILY,
        research_type=research_type
    )

def _create_concurrent_schedules(count):
    """Create multiple test schedules for concurrency testing."""
    return [
        ResearchSchedule(
            name=f"concurrent_job_{i}",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.MODEL_UPDATES
        ) for i in range(count)
    ]