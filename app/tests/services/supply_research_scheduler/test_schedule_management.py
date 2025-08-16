"""
Tests for schedule management operations
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import patch

from app.services.supply_research_scheduler import (
    SupplyResearchScheduler,
    ResearchSchedule,
    ScheduleFrequency
)
from app.agents.supply_researcher.models import ResearchType
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


class TestScheduleManagement:
    """Test schedule management operations"""
    
    def test_add_schedule(self, scheduler):
        """Test adding new schedule"""
        initial_count = len(scheduler.schedules)
        
        new_schedule = ResearchSchedule(
            name="custom_schedule",
            frequency=ScheduleFrequency.WEEKLY,
            research_type=ResearchType.CAPABILITIES
        )
        
        scheduler.add_schedule(new_schedule)
        
        assert len(scheduler.schedules) == initial_count + 1
        assert new_schedule in scheduler.schedules
    
    def test_remove_schedule_exists(self, scheduler):
        """Test removing existing schedule"""
        initial_count = len(scheduler.schedules)
        
        # Remove first schedule
        schedule_to_remove = scheduler.schedules[0]
        scheduler.remove_schedule(schedule_to_remove.name)
        
        assert len(scheduler.schedules) == initial_count - 1
        assert schedule_to_remove not in scheduler.schedules
    
    def test_remove_schedule_not_exists(self, scheduler):
        """Test removing non-existent schedule"""
        initial_count = len(scheduler.schedules)
        
        scheduler.remove_schedule("non_existent_schedule")
        
        # Should not change anything
        assert len(scheduler.schedules) == initial_count
    
    def test_enable_schedule(self, scheduler):
        """Test enabling schedule"""
        # Add disabled schedule
        disabled_schedule = ResearchSchedule(
            name="disabled_test",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.PRICING,
            enabled=False
        )
        scheduler.add_schedule(disabled_schedule)
        
        assert disabled_schedule.enabled == False
        
        scheduler.enable_schedule("disabled_test")
        
        assert disabled_schedule.enabled == True
    
    def test_enable_schedule_not_exists(self, scheduler):
        """Test enabling non-existent schedule"""
        # Should not crash
        scheduler.enable_schedule("non_existent")
    
    def test_disable_schedule(self, scheduler):
        """Test disabling schedule"""
        # Use existing enabled schedule
        schedule = scheduler.schedules[0]
        assert schedule.enabled == True
        
        scheduler.disable_schedule(schedule.name)
        
        assert schedule.enabled == False
    
    def test_disable_schedule_not_exists(self, scheduler):
        """Test disabling non-existent schedule"""
        # Should not crash
        scheduler.disable_schedule("non_existent")
    
    def test_get_schedule_status(self, scheduler):
        """Test getting status of all schedules"""
        status = scheduler.get_schedule_status()
        
        assert isinstance(status, list)
        assert len(status) == len(scheduler.schedules)
        
        for schedule_info in status:
            assert "name" in schedule_info
            assert "frequency" in schedule_info
            assert "research_type" in schedule_info
            assert "enabled" in schedule_info
            assert "last_run" in schedule_info
            assert "next_run" in schedule_info
            assert "providers" in schedule_info
    
    def test_get_schedule_status_with_run_history(self, scheduler):
        """Test schedule status includes run history"""
        # Update a schedule to have run history
        schedule = scheduler.schedules[0]
        schedule.last_run = datetime.now(UTC)
        
        status = scheduler.get_schedule_status()
        schedule_status = next(s for s in status if s["name"] == schedule.name)
        
        assert schedule_status["last_run"] != None