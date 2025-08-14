"""
Tests for SupplyResearchScheduler initialization and setup
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.supply_research_scheduler import (
    SupplyResearchScheduler,
    ScheduleFrequency,
    ResearchSchedule
)
from app.agents.supply_researcher_sub_agent import ResearchType


class MockBackgroundTaskManager:
    """Mock background task manager"""
    def __init__(self):
        self.tasks = []
        self.running_tasks = []
    
    def add_task(self, task):
        self.tasks.append(task)
        return f"task_{len(self.tasks)}"


class MockLLMManager:
    """Mock LLM manager"""
    def __init__(self):
        self.ask_llm = MagicMock()


class MockRedisManager:
    """Mock Redis manager"""
    def __init__(self):
        self.data = {}
        self.lists = {}
    
    async def get(self, key):
        return self.data.get(key)
    
    async def set(self, key, value, ex=None):
        self.data[key] = value
        return True
    
    async def lpush(self, key, value):
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].insert(0, value)
        return len(self.lists[key])


@pytest.fixture
def mock_background_manager():
    """Create mock background task manager"""
    return MockBackgroundTaskManager()


@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager"""
    return MockLLMManager()


@pytest.fixture
def scheduler(mock_background_manager, mock_llm_manager):
    """Create SupplyResearchScheduler instance"""
    with patch('app.services.supply_research_scheduler.RedisManager') as mock_redis_class:
        mock_redis_class.return_value = MockRedisManager()
        return SupplyResearchScheduler(mock_background_manager, mock_llm_manager)


class TestSchedulerInitialization:
    """Test scheduler initialization"""
    
    def test_initialization_with_redis(self, mock_background_manager, mock_llm_manager):
        """Test initialization with Redis available"""
        with patch('app.services.supply_research_scheduler.RedisManager') as mock_redis_class:
            mock_redis_instance = MockRedisManager()
            mock_redis_class.return_value = mock_redis_instance
            
            scheduler = SupplyResearchScheduler(mock_background_manager, mock_llm_manager)
            
            assert scheduler.background_manager == mock_background_manager
            assert scheduler.llm_manager == mock_llm_manager
            assert scheduler.redis_manager == mock_redis_instance
            assert scheduler.running == False
            assert len(scheduler.schedules) > 0  # Should have default schedules
    
    def test_initialization_without_redis(self, mock_background_manager, mock_llm_manager):
        """Test initialization when Redis is not available"""
        with patch('app.services.supply_research_scheduler.RedisManager', side_effect=Exception("Redis not available")):
            scheduler = SupplyResearchScheduler(mock_background_manager, mock_llm_manager)
            
            assert scheduler.redis_manager == None
    
    def test_default_schedules_created(self, scheduler):
        """Test that default schedules are created"""
        # Should have default schedules
        assert len(scheduler.schedules) == 4
        
        schedule_names = [s.name for s in scheduler.schedules]
        expected_names = [
            "daily_pricing_check",
            "weekly_capability_scan", 
            "weekly_new_models",
            "monthly_market_report"
        ]
        
        for name in expected_names:
            assert name in schedule_names
    
    def test_default_schedule_configurations(self, scheduler):
        """Test default schedule configurations are correct"""
        schedules_by_name = {s.name: s for s in scheduler.schedules}
        
        # Daily pricing check
        daily_pricing = schedules_by_name["daily_pricing_check"]
        assert daily_pricing.frequency == ScheduleFrequency.DAILY
        assert daily_pricing.research_type == ResearchType.PRICING
        assert daily_pricing.hour == 2
        assert daily_pricing.enabled == True
        
        # Weekly capability scan
        weekly_cap = schedules_by_name["weekly_capability_scan"]
        assert weekly_cap.frequency == ScheduleFrequency.WEEKLY
        assert weekly_cap.research_type == ResearchType.CAPABILITIES
        assert weekly_cap.day_of_week == 0  # Monday
        assert weekly_cap.hour == 9
        
        # Weekly new models
        weekly_models = schedules_by_name["weekly_new_models"]
        assert weekly_models.frequency == ScheduleFrequency.WEEKLY
        assert weekly_models.research_type == ResearchType.NEW_MODEL
        assert weekly_models.day_of_week == 4  # Friday
        assert weekly_models.hour == 10
        
        # Monthly market report
        monthly_market = schedules_by_name["monthly_market_report"]
        assert monthly_market.frequency == ScheduleFrequency.MONTHLY
        assert monthly_market.research_type == ResearchType.MARKET_OVERVIEW
        assert monthly_market.day_of_month == 1
        assert monthly_market.hour == 0


class TestSchedulerStartStop:
    """Test scheduler start/stop functionality"""
    
    def test_start_scheduler(self, scheduler):
        """Test starting the scheduler"""
        assert scheduler.running == False
        
        scheduler.start()
        
        assert scheduler.running == True
        # Should have added scheduler loop task
        assert len(scheduler.background_manager.tasks) == 1
    
    def test_start_scheduler_already_running(self, scheduler):
        """Test starting scheduler when already running"""
        scheduler.running = True
        initial_task_count = len(scheduler.background_manager.tasks)
        
        scheduler.start()
        
        # Should not add another task
        assert len(scheduler.background_manager.tasks) == initial_task_count
    
    def test_stop_scheduler(self, scheduler):
        """Test stopping the scheduler"""
        scheduler.running = True
        
        scheduler.stop()
        
        assert scheduler.running == False