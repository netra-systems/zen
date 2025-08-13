"""
Tests for scheduler loop functionality
"""

import pytest
import asyncio
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, patch

from app.services.supply_research_scheduler import (
    SupplyResearchScheduler,
    ResearchSchedule,
    ScheduleFrequency
)
from app.agents.supply_researcher_sub_agent import ResearchType
from app.tests.services.supply_research_scheduler.test_scheduler_initialization import (
    MockBackgroundTaskManager,
    MockLLMManager,
    MockRedisManager
)


@pytest.fixture
def scheduler():
    """Create SupplyResearchScheduler instance"""
    mock_background_manager = MockBackgroundTaskManager()
    mock_llm_manager = MockLLMManager()
    
    with patch('app.services.supply_research_scheduler.RedisManager') as mock_redis_class:
        mock_redis_class.return_value = MockRedisManager()
        return SupplyResearchScheduler(mock_background_manager, mock_llm_manager)


@pytest.mark.asyncio
class TestSchedulerLoop:
    """Test main scheduler loop functionality"""
    
    async def test_scheduler_loop_execution(self, scheduler):
        """Test scheduler loop executes due schedules"""
        # Create schedule that should run
        test_schedule = ResearchSchedule(
            name="test_immediate",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.PRICING
        )
        test_schedule.next_run = datetime.now(UTC) - timedelta(minutes=5)  # Should run
        scheduler.add_schedule(test_schedule)
        
        scheduler.running = True
        
        # Mock to stop after first iteration
        iteration_count = 0
        original_sleep = asyncio.sleep
        
        async def mock_sleep(duration):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 2:  # Stop after 2 iterations
                scheduler.running = False
            await original_sleep(0.01)  # Very short sleep
        
        with patch('asyncio.sleep', mock_sleep):
            await scheduler._scheduler_loop()
        
        # Should have added task to background manager
        assert len(scheduler.background_manager.tasks) > 0
    
    async def test_scheduler_loop_no_due_schedules(self, scheduler):
        """Test scheduler loop when no schedules are due"""
        # Ensure all schedules are in the future
        for schedule in scheduler.schedules:
            schedule.next_run = datetime.now(UTC) + timedelta(hours=1)
        
        scheduler.running = True
        
        # Mock to stop after first iteration
        original_sleep = asyncio.sleep
        
        async def mock_sleep(duration):
            scheduler.running = False
            await original_sleep(0.01)
        
        with patch('asyncio.sleep', mock_sleep):
            await scheduler._scheduler_loop()
        
        # Should not have added any tasks
        assert len(scheduler.background_manager.tasks) == 0
    
    async def test_scheduler_loop_error_handling(self, scheduler):
        """Test scheduler loop handles errors gracefully"""
        scheduler.running = True
        
        # Make should_run raise exception for first schedule
        original_should_run = scheduler.schedules[0].should_run
        scheduler.schedules[0].should_run = MagicMock(side_effect=Exception("Test error"))
        
        iteration_count = 0
        original_sleep = asyncio.sleep
        
        async def mock_sleep(duration):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 2:
                scheduler.running = False
            await original_sleep(0.01)
        
        with patch('asyncio.sleep', mock_sleep):
            await scheduler._scheduler_loop()
        
        # Should have continued despite error
        assert iteration_count >= 2
    
    async def test_scheduler_loop_disabled_schedules(self, scheduler):
        """Test scheduler loop skips disabled schedules"""
        # Disable all schedules
        for schedule in scheduler.schedules:
            schedule.enabled = False
            schedule.next_run = datetime.now(UTC) - timedelta(minutes=5)
        
        scheduler.running = True
        
        original_sleep = asyncio.sleep
        
        async def mock_sleep(duration):
            scheduler.running = False
            await original_sleep(0.01)
        
        with patch('asyncio.sleep', mock_sleep):
            await scheduler._scheduler_loop()
        
        # Should not have added any tasks (all disabled)
        assert len(scheduler.background_manager.tasks) == 0


@pytest.mark.asyncio
class TestManualExecution:
    """Test manual schedule execution"""
    
    async def test_run_schedule_now_exists(self, scheduler):
        """Test manually running existing schedule"""
        schedule_name = scheduler.schedules[0].name
        
        with patch.object(scheduler, '_execute_scheduled_research') as mock_execute:
            mock_execute.return_value = {"status": "completed"}
            
            result = await scheduler.run_schedule_now(schedule_name)
        
        assert result["status"] == "completed"
        mock_execute.assert_called_once_with(scheduler.schedules[0])
    
    async def test_run_schedule_now_not_exists(self, scheduler):
        """Test manually running non-existent schedule"""
        with pytest.raises(ValueError, match="Schedule not found"):
            await scheduler.run_schedule_now("non_existent_schedule")