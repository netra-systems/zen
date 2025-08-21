"""
Retry logic tests for Supply Research Scheduler
Tests retry mechanisms, exponential backoff, and circuit breaker patterns
COMPLIANCE: 450-line max file, 25-line max functions
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path

from netra_backend.app.services.supply_research_scheduler import (

# Add project root to path
    SupplyResearchScheduler,
    ResearchSchedule,
    ScheduleFrequency
)
from netra_backend.app.agents.supply_researcher.models import ResearchType
from background import BackgroundTaskManager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.core.exceptions_base import NetraException


@pytest.fixture
def scheduler_with_redis():
    """Create scheduler with Redis for retry logic."""
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


class TestSupplyResearchSchedulerRetryLogic:
    """Test retry logic and failure handling"""
    
    async def test_exponential_backoff_retry_timing(self, scheduler_with_redis):
        """Test exponential backoff timing in retry logic."""
        scheduler, mock_redis = scheduler_with_redis
        
        schedule = _create_backoff_schedule()
        
        scheduler._execute_research_job = AsyncMock(side_effect=NetraException("Retry needed"))
        mock_redis.get = AsyncMock(side_effect=["0", "1", "2"])
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
        """Test retry state persistence in Redis."""
        scheduler, mock_redis = scheduler_with_redis
        
        schedule = _create_persistent_schedule()
        
        # Mock Redis operations
        mock_redis.get = AsyncMock(return_value="1")
        mock_redis.set = AsyncMock()
        mock_redis.expire = AsyncMock()
        
        scheduler._execute_research_job = AsyncMock(side_effect=NetraException("Failed"))
        
        # Execute
        with patch('asyncio.sleep', new_callable=AsyncMock):
            await scheduler._execute_with_retry(schedule, max_retries=3)
        
        # Assert Redis operations
        _assert_redis_retry_operations(mock_redis, schedule)

    async def test_retry_circuit_breaker(self, scheduler_with_redis):
        """Test circuit breaker pattern for failing jobs."""
        scheduler, mock_redis = scheduler_with_redis
        
        schedule = _create_circuit_schedule()
        
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
        """Test jitter in retry timing to prevent thundering herd."""
        scheduler, mock_redis = scheduler_with_redis
        
        schedule = _create_jitter_schedule()
        
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
        assert 0.5 <= sleep_times[0] <= 1.5


def _create_backoff_schedule():
    """Create schedule for backoff testing."""
    return ResearchSchedule(
        name="backoff_job",
        frequency=ScheduleFrequency.DAILY,
        research_type=ResearchType.MODEL_UPDATES
    )


def _create_persistent_schedule():
    """Create schedule for persistence testing."""
    return ResearchSchedule(
        name="persistent_job",
        frequency=ScheduleFrequency.HOURLY,
        research_type=ResearchType.PERFORMANCE_BENCHMARKS
    )


def _create_circuit_schedule():
    """Create schedule for circuit breaker testing."""
    return ResearchSchedule(
        name="circuit_job",
        frequency=ScheduleFrequency.DAILY,
        research_type=ResearchType.PROVIDER_COMPARISON
    )


def _create_jitter_schedule():
    """Create schedule for jitter testing."""
    return ResearchSchedule(
        name="jitter_job",
        frequency=ScheduleFrequency.HOURLY,
        research_type=ResearchType.COST_ANALYSIS
    )


def _assert_redis_retry_operations(mock_redis, schedule):
    """Assert Redis retry operations are called correctly."""
    mock_redis.get.assert_called_with(f"scheduler:retry:{schedule.name}")
    mock_redis.set.assert_called_with(f"scheduler:retry:{schedule.name}", "2")
    mock_redis.expire.assert_called_with(f"scheduler:retry:{schedule.name}", 3600)