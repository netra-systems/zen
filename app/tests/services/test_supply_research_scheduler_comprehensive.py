"""
Comprehensive tests for SupplyResearchScheduler with complete coverage
Tests scheduling logic, execution, background tasks, error handling, and time calculations
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Dict, List, Any

from app.services.supply_research_scheduler import (
    SupplyResearchScheduler,
    ResearchSchedule,
    ScheduleFrequency
)
from app.agents.supply_researcher_sub_agent import ResearchType
from app.background import BackgroundTaskManager
from app.llm.llm_manager import LLMManager


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
        self.ask_llm = AsyncMock()


class MockDatabase:
    """Mock database context manager"""
    def __init__(self, db_session):
        self.db_session = db_session
    
    def get_db(self):
        return MockDBContext(self.db_session)


class MockDBContext:
    """Mock database context"""
    def __init__(self, db_session):
        self.db_session = db_session
    
    def __enter__(self):
        return self.db_session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


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


class MockSupplyResearchService:
    """Mock supply research service"""
    def __init__(self):
        self.calculate_price_changes = MagicMock()
        self.calculate_price_changes.return_value = {
            "all_changes": [
                {
                    "provider": "openai",
                    "model": "gpt-4",
                    "field": "pricing_input",
                    "percent_change": 15.5
                }
            ]
        }


class MockAgent:
    """Mock supply researcher agent"""
    def __init__(self):
        self.process_scheduled_research = AsyncMock()
        self.process_scheduled_research.return_value = {
            "results": [
                {
                    "provider": "openai",
                    "result": {
                        "updates_made": {
                            "updates_count": 2,
                            "updates": [
                                {"action": "created", "model": "new-model-1"},
                                {"action": "updated", "model": "existing-model"}
                            ]
                        }
                    }
                }
            ]
        }


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


class TestResearchSchedule:
    """Test ResearchSchedule class"""
    
    def test_schedule_initialization_default_values(self):
        """Test schedule initialization with default values"""
        schedule = ResearchSchedule(
            name="test_schedule",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.PRICING
        )
        
        assert schedule.name == "test_schedule"
        assert schedule.frequency == ScheduleFrequency.DAILY
        assert schedule.research_type == ResearchType.PRICING
        assert schedule.providers == ["openai", "anthropic", "google", "mistral"]
        assert schedule.enabled is True
        assert schedule.hour == 2  # Default 2 AM
        assert schedule.day_of_week == 1  # Default Monday
        assert schedule.day_of_month == 1  # Default 1st
        assert schedule.last_run is None
        assert schedule.next_run is not None
    
    def test_schedule_initialization_custom_values(self):
        """Test schedule initialization with custom values"""
        custom_providers = ["openai", "custom_provider"]
        
        schedule = ResearchSchedule(
            name="custom_schedule",
            frequency=ScheduleFrequency.WEEKLY,
            research_type=ResearchType.CAPABILITIES,
            providers=custom_providers,
            enabled=False,
            hour=10,
            day_of_week=3,
            day_of_month=15
        )
        
        assert schedule.providers == custom_providers
        assert schedule.enabled is False
        assert schedule.hour == 10
        assert schedule.day_of_week == 3
        assert schedule.day_of_month == 15
    
    def test_calculate_next_run_hourly(self):
        """Test next run calculation for hourly frequency"""
        schedule = ResearchSchedule(
            name="hourly_test",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.PRICING
        )
        
        now = datetime.utcnow()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        # Should be next hour on the hour
        assert schedule.next_run >= next_hour
        assert schedule.next_run < next_hour + timedelta(hours=1)
        assert schedule.next_run.minute == 0
        assert schedule.next_run.second == 0
    
    def test_calculate_next_run_daily(self):
        """Test next run calculation for daily frequency"""
        schedule = ResearchSchedule(
            name="daily_test",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.PRICING,
            hour=14  # 2 PM
        )
        
        # Should be at 2 PM today or tomorrow
        assert schedule.next_run.hour == 14
        assert schedule.next_run.minute == 0
        assert schedule.next_run.second == 0
        
        # Should be today or tomorrow
        now = datetime.utcnow()
        today_2pm = now.replace(hour=14, minute=0, second=0, microsecond=0)
        tomorrow_2pm = today_2pm + timedelta(days=1)
        
        assert schedule.next_run == today_2pm or schedule.next_run == tomorrow_2pm
    
    def test_calculate_next_run_weekly(self):
        """Test next run calculation for weekly frequency"""
        schedule = ResearchSchedule(
            name="weekly_test",
            frequency=ScheduleFrequency.WEEKLY,
            research_type=ResearchType.CAPABILITIES,
            hour=9,
            day_of_week=0  # Monday
        )
        
        # Should be Monday at 9 AM
        assert schedule.next_run.hour == 9
        assert schedule.next_run.minute == 0
        assert schedule.next_run.weekday() == 0  # Monday
    
    def test_calculate_next_run_monthly(self):
        """Test next run calculation for monthly frequency"""
        schedule = ResearchSchedule(
            name="monthly_test",
            frequency=ScheduleFrequency.MONTHLY,
            research_type=ResearchType.MARKET_OVERVIEW,
            hour=0,
            day_of_month=1
        )
        
        # Should be 1st of month at midnight
        assert schedule.next_run.day == 1
        assert schedule.next_run.hour == 0
        assert schedule.next_run.minute == 0
    
    def test_calculate_next_run_monthly_invalid_day(self):
        """Test monthly calculation handles invalid day (e.g., Feb 30)"""
        # Test with day 31 - should handle months with fewer days
        schedule = ResearchSchedule(
            name="monthly_edge_test",
            frequency=ScheduleFrequency.MONTHLY,
            research_type=ResearchType.PRICING,
            day_of_month=31
        )
        
        # Should not crash and should produce valid datetime
        assert isinstance(schedule.next_run, datetime)
    
    def test_should_run_enabled_and_time_reached(self):
        """Test should_run when enabled and time has been reached"""
        schedule = ResearchSchedule(
            name="test_should_run",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.PRICING,
            enabled=True
        )
        
        # Set next_run to past time
        schedule.next_run = datetime.utcnow() - timedelta(minutes=5)
        
        assert schedule.should_run() is True
    
    def test_should_run_disabled(self):
        """Test should_run when disabled"""
        schedule = ResearchSchedule(
            name="disabled_test",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.PRICING,
            enabled=False
        )
        
        # Even if time has passed, should not run if disabled
        schedule.next_run = datetime.utcnow() - timedelta(minutes=5)
        
        assert schedule.should_run() is False
    
    def test_should_run_time_not_reached(self):
        """Test should_run when time has not been reached"""
        schedule = ResearchSchedule(
            name="future_test",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.PRICING,
            enabled=True
        )
        
        # Set next_run to future time
        schedule.next_run = datetime.utcnow() + timedelta(minutes=30)
        
        assert schedule.should_run() is False
    
    def test_update_after_run(self):
        """Test updating schedule after successful run"""
        schedule = ResearchSchedule(
            name="update_test",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.PRICING
        )
        
        original_next_run = schedule.next_run
        original_last_run = schedule.last_run
        
        schedule.update_after_run()
        
        # Should update last_run and recalculate next_run
        assert schedule.last_run != original_last_run
        assert schedule.last_run is not None
        assert schedule.next_run != original_next_run


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
            assert scheduler.running is False
            assert len(scheduler.schedules) > 0  # Should have default schedules
    
    def test_initialization_without_redis(self, mock_background_manager, mock_llm_manager):
        """Test initialization when Redis is not available"""
        with patch('app.services.supply_research_scheduler.RedisManager', side_effect=Exception("Redis not available")):
            scheduler = SupplyResearchScheduler(mock_background_manager, mock_llm_manager)
            
            assert scheduler.redis_manager is None
    
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
        assert daily_pricing.enabled is True
        
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
        
        assert disabled_schedule.enabled is False
        
        scheduler.enable_schedule("disabled_test")
        
        assert disabled_schedule.enabled is True
    
    def test_enable_schedule_not_exists(self, scheduler):
        """Test enabling non-existent schedule"""
        # Should not crash
        scheduler.enable_schedule("non_existent")
    
    def test_disable_schedule(self, scheduler):
        """Test disabling schedule"""
        # Use existing enabled schedule
        schedule = scheduler.schedules[0]
        assert schedule.enabled is True
        
        scheduler.disable_schedule(schedule.name)
        
        assert schedule.enabled is False
    
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
        schedule.last_run = datetime.utcnow()
        
        status = scheduler.get_schedule_status()
        schedule_status = next(s for s in status if s["name"] == schedule.name)
        
        assert schedule_status["last_run"] is not None


@pytest.mark.asyncio
class TestScheduledResearchExecution:
    """Test scheduled research execution"""
    
    async def test_execute_scheduled_research_success(self, scheduler):
        """Test successful scheduled research execution"""
        schedule = scheduler.schedules[0]
        
        with patch('app.services.supply_research_scheduler.Database') as mock_db_class:
            mock_db_session = MagicMock()
            mock_db_class.return_value = MockDatabase(mock_db_session)
            
            with patch('app.services.supply_research_scheduler.SupplyResearchService') as mock_service_class:
                mock_service = MockSupplyResearchService()
                mock_service_class.return_value = mock_service
                
                with patch('app.services.supply_research_scheduler.SupplyResearcherAgent') as mock_agent_class:
                    mock_agent = MockAgent()
                    mock_agent_class.return_value = mock_agent
                    
                    result = await scheduler._execute_scheduled_research(schedule)
        
        assert result["schedule_name"] == schedule.name
        assert result["research_type"] == schedule.research_type.value
        assert result["status"] == "completed"
        assert "started_at" in result
        assert "completed_at" in result
        assert "results" in result
        
        # Verify agent was called with correct parameters
        mock_agent.process_scheduled_research.assert_called_once_with(
            schedule.research_type,
            schedule.providers
        )
    
    async def test_execute_scheduled_research_failure(self, scheduler):
        """Test scheduled research execution with failure"""
        schedule = scheduler.schedules[0]
        
        with patch('app.services.supply_research_scheduler.Database', side_effect=Exception("Database error")):
            result = await scheduler._execute_scheduled_research(schedule)
        
        assert result["schedule_name"] == schedule.name
        assert result["status"] == "failed"
        assert result["error"] == "Database error"
        assert "started_at" in result
    
    async def test_execute_scheduled_research_caching(self, scheduler):
        """Test that research results are cached"""
        schedule = scheduler.schedules[0]
        
        # Mock Redis to verify caching
        mock_redis = MockRedisManager()
        scheduler.redis_manager = mock_redis
        
        with patch('app.services.supply_research_scheduler.Database') as mock_db_class:
            mock_db_session = MagicMock()
            mock_db_class.return_value = MockDatabase(mock_db_session)
            
            with patch('app.services.supply_research_scheduler.SupplyResearchService') as mock_service_class:
                mock_service = MockSupplyResearchService()
                mock_service_class.return_value = mock_service
                
                with patch('app.services.supply_research_scheduler.SupplyResearcherAgent') as mock_agent_class:
                    mock_agent = MockAgent()
                    mock_agent_class.return_value = mock_agent
                    
                    result = await scheduler._execute_scheduled_research(schedule)
        
        # Should have cached the result
        cache_key = f"schedule_result:{schedule.name}:{datetime.utcnow().date()}"
        cached_data = await mock_redis.get(cache_key)
        assert cached_data is not None
        
        # Should be valid JSON
        parsed_data = json.loads(cached_data)
        assert parsed_data["schedule_name"] == schedule.name
    
    async def test_execute_scheduled_research_no_redis(self, scheduler):
        """Test research execution when Redis is not available"""
        schedule = scheduler.schedules[0]
        scheduler.redis_manager = None  # No Redis
        
        with patch('app.services.supply_research_scheduler.Database') as mock_db_class:
            mock_db_session = MagicMock()
            mock_db_class.return_value = MockDatabase(mock_db_session)
            
            with patch('app.services.supply_research_scheduler.SupplyResearchService') as mock_service_class:
                mock_service = MockSupplyResearchService()
                mock_service_class.return_value = mock_service
                
                with patch('app.services.supply_research_scheduler.SupplyResearcherAgent') as mock_agent_class:
                    mock_agent = MockAgent()
                    mock_agent_class.return_value = mock_agent
                    
                    result = await scheduler._execute_scheduled_research(schedule)
        
        # Should still succeed without Redis
        assert result["status"] == "completed"
    
    async def test_check_and_notify_changes_significant_price_changes(self, scheduler):
        """Test notification of significant price changes"""
        mock_service = MockSupplyResearchService()
        mock_service.calculate_price_changes.return_value = {
            "all_changes": [
                {
                    "provider": "openai",
                    "model": "gpt-4",
                    "field": "pricing_input",
                    "percent_change": 25.0  # Significant change > 10%
                }
            ]
        }
        
        result = {
            "results": []
        }
        
        mock_redis = MockRedisManager()
        scheduler.redis_manager = mock_redis
        
        await scheduler._check_and_notify_changes(result, mock_service)
        
        # Should have added notification to Redis
        notifications = mock_redis.lists.get("supply_notifications", [])
        assert len(notifications) > 0
        
        notification = json.loads(notifications[0])
        assert "changes" in notification
        assert len(notification["changes"]) == 1
        assert notification["changes"][0]["type"] == "price_change"
    
    async def test_check_and_notify_changes_new_models(self, scheduler):
        """Test notification of new models"""
        mock_service = MockSupplyResearchService()
        mock_service.calculate_price_changes.return_value = {"all_changes": []}
        
        result = {
            "results": [
                {
                    "provider": "openai",
                    "result": {
                        "updates_made": {
                            "updates_count": 1,
                            "updates": [
                                {"action": "created", "model": "gpt-5"}
                            ]
                        }
                    }
                }
            ]
        }
        
        mock_redis = MockRedisManager()
        scheduler.redis_manager = mock_redis
        
        await scheduler._check_and_notify_changes(result, mock_service)
        
        # Should have added notification for new model
        notifications = mock_redis.lists.get("supply_notifications", [])
        assert len(notifications) > 0
        
        notification = json.loads(notifications[0])
        assert len(notification["changes"]) == 1
        assert notification["changes"][0]["type"] == "new_model"
        assert notification["changes"][0]["model"]["model"] == "gpt-5"
    
    async def test_check_and_notify_changes_no_significant_changes(self, scheduler):
        """Test no notifications for insignificant changes"""
        mock_service = MockSupplyResearchService()
        mock_service.calculate_price_changes.return_value = {
            "all_changes": [
                {
                    "provider": "openai",
                    "model": "gpt-4",
                    "field": "pricing_input",
                    "percent_change": 5.0  # Below 10% threshold
                }
            ]
        }
        
        result = {"results": []}
        
        mock_redis = MockRedisManager()
        scheduler.redis_manager = mock_redis
        
        await scheduler._check_and_notify_changes(result, mock_service)
        
        # Should not have added any notifications
        notifications = mock_redis.lists.get("supply_notifications", [])
        assert len(notifications) == 0
    
    async def test_check_and_notify_changes_error_handling(self, scheduler):
        """Test error handling in change notification"""
        mock_service = MockSupplyResearchService()
        mock_service.calculate_price_changes.side_effect = Exception("Service error")
        
        result = {"results": []}
        
        # Should not raise exception
        await scheduler._check_and_notify_changes(result, mock_service)


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
        test_schedule.next_run = datetime.utcnow() - timedelta(minutes=5)  # Should run
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
            schedule.next_run = datetime.utcnow() + timedelta(hours=1)
        
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
            schedule.next_run = datetime.utcnow() - timedelta(minutes=5)
        
        scheduler.running = True
        
        original_sleep = asyncio.sleep
        
        async def mock_sleep(duration):
            scheduler.running = False
            await original_sleep(0.01)
        
        with patch('asyncio.sleep', mock_sleep):
            await scheduler._scheduler_loop()
        
        # Should not have added any tasks (all disabled)
        assert len(scheduler.background_manager.tasks) == 0


class TestSchedulerStartStop:
    """Test scheduler start/stop functionality"""
    
    def test_start_scheduler(self, scheduler):
        """Test starting the scheduler"""
        assert scheduler.running is False
        
        scheduler.start()
        
        assert scheduler.running is True
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
        
        assert scheduler.running is False


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


@pytest.mark.asyncio
class TestResultRetrieval:
    """Test result retrieval from cache"""
    
    async def test_get_recent_results_no_redis(self, scheduler):
        """Test getting recent results when Redis not available"""
        scheduler.redis_manager = None
        
        results = await scheduler.get_recent_results()
        
        assert results == []
    
    async def test_get_recent_results_with_redis(self, scheduler):
        """Test getting recent results from Redis"""
        mock_redis = MockRedisManager()
        scheduler.redis_manager = mock_redis
        
        # Add some test data to Redis
        test_result = {
            "schedule_name": "test_schedule",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        today = datetime.utcnow().date()
        cache_key = f"schedule_result:test_schedule:{today}"
        await mock_redis.set(cache_key, json.dumps(test_result))
        
        results = await scheduler.get_recent_results("test_schedule", days_back=1)
        
        assert len(results) == 1
        assert results[0]["schedule_name"] == "test_schedule"
    
    async def test_get_recent_results_all_schedules(self, scheduler):
        """Test getting results for all schedules"""
        mock_redis = MockRedisManager()
        scheduler.redis_manager = mock_redis
        
        # Add results for multiple schedules
        today = datetime.utcnow().date()
        for i, schedule in enumerate(scheduler.schedules[:2]):
            test_result = {
                "schedule_name": schedule.name,
                "status": "completed"
            }
            cache_key = f"schedule_result:{schedule.name}:{today}"
            await mock_redis.set(cache_key, json.dumps(test_result))
        
        results = await scheduler.get_recent_results(days_back=1)
        
        assert len(results) >= 2
    
    async def test_get_recent_results_multiple_days(self, scheduler):
        """Test getting results across multiple days"""
        mock_redis = MockRedisManager()
        scheduler.redis_manager = mock_redis
        
        schedule_name = "test_schedule"
        
        # Add results for multiple days
        for days_ago in [0, 1, 2]:
            date = (datetime.utcnow() - timedelta(days=days_ago)).date()
            test_result = {
                "schedule_name": schedule_name,
                "day": str(date)
            }
            cache_key = f"schedule_result:{schedule_name}:{date}"
            await mock_redis.set(cache_key, json.dumps(test_result))
        
        results = await scheduler.get_recent_results(schedule_name, days_back=3)
        
        assert len(results) == 3
    
    async def test_get_recent_results_redis_errors(self, scheduler):
        """Test handling Redis errors when getting results"""
        mock_redis = MockRedisManager()
        
        # Mock Redis get to raise exception
        async def failing_get(key):
            raise Exception("Redis error")
        
        mock_redis.get = failing_get
        scheduler.redis_manager = mock_redis
        
        # Should handle errors gracefully
        results = await scheduler.get_recent_results("test_schedule")
        
        assert results == []


class TestScheduleFrequencyEnum:
    """Test ScheduleFrequency enum"""
    
    def test_schedule_frequency_values(self):
        """Test that enum has expected values"""
        expected_values = ["hourly", "daily", "weekly", "monthly"]
        
        for value in expected_values:
            assert hasattr(ScheduleFrequency, value.upper())
            assert getattr(ScheduleFrequency, value.upper()).value == value


class TestIntegrationScenarios:
    """Test integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_execution_cycle(self, scheduler):
        """Test full execution cycle from schedule to notification"""
        # Create schedule that should run immediately
        test_schedule = ResearchSchedule(
            name="integration_test",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.PRICING
        )
        test_schedule.next_run = datetime.utcnow() - timedelta(minutes=1)
        scheduler.add_schedule(test_schedule)
        
        mock_redis = MockRedisManager()
        scheduler.redis_manager = mock_redis
        
        # Mock all dependencies
        with patch('app.services.supply_research_scheduler.Database') as mock_db_class:
            mock_db_session = MagicMock()
            mock_db_class.return_value = MockDatabase(mock_db_session)
            
            with patch('app.services.supply_research_scheduler.SupplyResearchService') as mock_service_class:
                mock_service = MockSupplyResearchService()
                mock_service_class.return_value = mock_service
                
                with patch('app.services.supply_research_scheduler.SupplyResearcherAgent') as mock_agent_class:
                    mock_agent = MockAgent()
                    mock_agent_class.return_value = mock_agent
                    
                    # Execute the research
                    result = await scheduler._execute_scheduled_research(test_schedule)
        
        # Verify execution completed successfully
        assert result["status"] == "completed"
        assert result["schedule_name"] == "integration_test"
        
        # Verify result was cached
        cache_key = f"schedule_result:integration_test:{datetime.utcnow().date()}"
        cached_result = await mock_redis.get(cache_key)
        assert cached_result is not None
        
        # Verify notifications were processed
        notifications = mock_redis.lists.get("supply_notifications", [])
        assert len(notifications) > 0  # Should have notifications for new models
    
    @pytest.mark.asyncio
    async def test_concurrent_schedule_execution(self, scheduler):
        """Test concurrent execution of multiple schedules"""
        # Create multiple schedules that should run
        schedules_to_run = []
        for i in range(3):
            schedule = ResearchSchedule(
                name=f"concurrent_test_{i}",
                frequency=ScheduleFrequency.HOURLY,
                research_type=ResearchType.PRICING
            )
            schedule.next_run = datetime.utcnow() - timedelta(minutes=1)
            scheduler.add_schedule(schedule)
            schedules_to_run.append(schedule)
        
        # Mock dependencies
        with patch('app.services.supply_research_scheduler.Database') as mock_db_class:
            mock_db_session = MagicMock()
            mock_db_class.return_value = MockDatabase(mock_db_session)
            
            with patch('app.services.supply_research_scheduler.SupplyResearchService') as mock_service_class:
                mock_service = MockSupplyResearchService()
                mock_service_class.return_value = mock_service
                
                with patch('app.services.supply_research_scheduler.SupplyResearcherAgent') as mock_agent_class:
                    mock_agent = MockAgent()
                    mock_agent_class.return_value = mock_agent
                    
                    # Execute all schedules concurrently
                    tasks = [
                        scheduler._execute_scheduled_research(schedule)
                        for schedule in schedules_to_run
                    ]
                    
                    results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 3
        for result in results:
            assert result["status"] == "completed"
    
    def test_schedule_time_calculations_across_boundaries(self):
        """Test schedule calculations across month/year boundaries"""
        # Test monthly schedule at year boundary
        schedule = ResearchSchedule(
            name="year_boundary_test",
            frequency=ScheduleFrequency.MONTHLY,
            research_type=ResearchType.PRICING,
            day_of_month=1
        )
        
        # Manually set current date to end of year
        with patch('app.services.supply_research_scheduler.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2023, 12, 31, 23, 59, 59)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            next_run = schedule._calculate_next_run()
            
            # Should be January 1st of next year
            assert next_run.year == 2024
            assert next_run.month == 1
            assert next_run.day == 1


class TestErrorHandling:
    """Test comprehensive error handling"""
    
    @pytest.mark.asyncio
    async def test_database_connection_failures(self, scheduler):
        """Test handling database connection failures"""
        schedule = scheduler.schedules[0]
        
        with patch('app.services.supply_research_scheduler.Database', side_effect=ConnectionError("DB connection failed")):
            result = await scheduler._execute_scheduled_research(schedule)
        
        assert result["status"] == "failed"
        assert "DB connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_agent_execution_failures(self, scheduler):
        """Test handling agent execution failures"""
        schedule = scheduler.schedules[0]
        
        with patch('app.services.supply_research_scheduler.Database') as mock_db_class:
            mock_db_session = MagicMock()
            mock_db_class.return_value = MockDatabase(mock_db_session)
            
            with patch('app.services.supply_research_scheduler.SupplyResearchService') as mock_service_class:
                mock_service = MockSupplyResearchService()
                mock_service_class.return_value = mock_service
                
                with patch('app.services.supply_research_scheduler.SupplyResearcherAgent') as mock_agent_class:
                    mock_agent = MockAgent()
                    mock_agent.process_scheduled_research.side_effect = Exception("Agent failed")
                    mock_agent_class.return_value = mock_agent
                    
                    result = await scheduler._execute_scheduled_research(schedule)
        
        assert result["status"] == "failed"
        assert "Agent failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_redis_failures_during_execution(self, scheduler):
        """Test handling Redis failures during execution"""
        schedule = scheduler.schedules[0]
        
        # Mock Redis that fails on set
        mock_redis = MockRedisManager()
        
        async def failing_set(*args, **kwargs):
            raise Exception("Redis set failed")
        
        mock_redis.set = failing_set
        scheduler.redis_manager = mock_redis
        
        with patch('app.services.supply_research_scheduler.Database') as mock_db_class:
            mock_db_session = MagicMock()
            mock_db_class.return_value = MockDatabase(mock_db_session)
            
            with patch('app.services.supply_research_scheduler.SupplyResearchService') as mock_service_class:
                mock_service = MockSupplyResearchService()
                mock_service_class.return_value = mock_service
                
                with patch('app.services.supply_research_scheduler.SupplyResearcherAgent') as mock_agent_class:
                    mock_agent = MockAgent()
                    mock_agent_class.return_value = mock_agent
                    
                    result = await scheduler._execute_scheduled_research(schedule)
        
        # Should still complete successfully despite Redis failure
        assert result["status"] == "completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])