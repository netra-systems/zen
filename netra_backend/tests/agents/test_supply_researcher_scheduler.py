from unittest.mock import AsyncMock, Mock, patch, MagicMock
import asyncio

"""
Tests for SupplyResearchScheduler functionality
""""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

from datetime import UTC, datetime, timedelta

import pytest
from netra_backend.app.services.background_task_manager import BackgroundTaskManager

from netra_backend.app.agents.supply_researcher_sub_agent import (
    ResearchType,
    SupplyResearcherAgent,
)

from netra_backend.app.services.supply_research_scheduler import (
    ResearchSchedule,
    ScheduleFrequency,
    SupplyResearchScheduler,
)

class TestSupplyResearchScheduler:
    """Test suite for SupplyResearchScheduler"""
    
    def test_scheduler_initialization(self):
        """Test scheduler initializes with default schedules"""
        background_manager = BackgroundTaskManager()
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager = llm_manager_instance  # Initialize appropriate service
        
        scheduler = SupplyResearchScheduler(background_manager, llm_manager)
        
        assert len(scheduler.schedules) > 0
        assert any(s.name == "daily_pricing_check" for s in scheduler.schedules)
        assert any(s.name == "weekly_capability_scan" for s in scheduler.schedules)
    
    def test_schedule_next_run_calculation(self):
        """Test calculating next run time for schedules"""
        schedule = ResearchSchedule(
            name="test_daily",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.PRICING,
            hour=14  # 2 PM
        )
        
        next_run = schedule._calculate_next_run()
        assert next_run > datetime.now(UTC)
        assert next_run.hour == 14
    
    def test_schedule_should_run(self):
        """Test checking if schedule should run"""
        schedule = ResearchSchedule(
            name="test",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.PRICING
        )
        
        # Set next run to past
        schedule.next_run = datetime.now(UTC) - timedelta(minutes=1)
        assert schedule.should_run()
        
        # Set next run to future
        schedule.next_run = datetime.now(UTC) + timedelta(hours=1)
        assert not schedule.should_run()
    @pytest.mark.asyncio
    async def test_scheduler_execute_research(self):
        """Test executing scheduled research task"""
        background_manager = BackgroundTaskManager()
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager = llm_manager_instance  # Initialize appropriate service
        scheduler = SupplyResearchScheduler(background_manager, llm_manager)
        
        schedule = ResearchSchedule(
            name="test_schedule",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.PRICING,
            providers=["openai"]
        )
        
        # Mock: Database access isolation for fast, reliable unit testing
        with patch('netra_backend.app.services.supply_research.research_executor.Database') as mock_db_manager:
            # Mock: Generic component isolation for controlled unit testing
            mock_db = TestDatabaseManager().get_session()
            # Mock: Component isolation for controlled unit testing
            mock_db_manager.return_value.get_db.return_value.__enter__ = Mock(return_value=mock_db)
            # Mock: Component isolation for controlled unit testing
            mock_db_manager.return_value.get_db.return_value.__exit__ = Mock(return_value=None)
            
            with patch.object(SupplyResearcherAgent, 'process_scheduled_research', new_callable=AsyncMock) as mock_process:
                mock_process.return_value = {"results": []]
                
                result = await scheduler._execute_scheduled_research(schedule)
                
                assert result["schedule_name"] == "test_schedule"
                assert result["status"] == "completed"
    
    def test_scheduler_add_remove_schedules(self):
        """Test adding and removing schedules"""
        background_manager = BackgroundTaskManager()
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager = llm_manager_instance  # Initialize appropriate service
        scheduler = SupplyResearchScheduler(background_manager, llm_manager)
        
        initial_count = len(scheduler.schedules)
        
        # Add schedule
        new_schedule = ResearchSchedule(
            name="custom_schedule",
            frequency=ScheduleFrequency.WEEKLY,
            research_type=ResearchType.NEW_MODEL
        )
        scheduler.add_schedule(new_schedule)
        assert len(scheduler.schedules) == initial_count + 1
        
        # Remove schedule
        scheduler.remove_schedule("custom_schedule")
        assert len(scheduler.schedules) == initial_count
    
    def test_scheduler_enable_disable(self):
        """Test enabling and disabling schedules"""
        background_manager = BackgroundTaskManager()
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager = llm_manager_instance  # Initialize appropriate service
        scheduler = SupplyResearchScheduler(background_manager, llm_manager)
        
        # Disable a schedule
        scheduler.disable_schedule("daily_pricing_check")
        schedule = next(s for s in scheduler.schedules if s.name == "daily_pricing_check")
        assert not schedule.enabled
        
        # Re-enable it
        scheduler.enable_schedule("daily_pricing_check")
        assert schedule.enabled
    
    def test_scheduler_get_status(self):
        """Test getting status of all schedules"""
        background_manager = BackgroundTaskManager()
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager = llm_manager_instance  # Initialize appropriate service
        scheduler = SupplyResearchScheduler(background_manager, llm_manager)
        
        status = scheduler.get_schedule_status()
        
        assert isinstance(status, list)
        assert len(status) == len(scheduler.schedules)
        assert all("name" in s for s in status)
        assert all("frequency" in s for s in status)
        assert all("next_run" in s for s in status)
    @pytest.mark.asyncio
    async def test_scheduler_agent_integration(self):
        """Test scheduler integration with agent"""
        background_manager = BackgroundTaskManager()
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager = llm_manager_instance  # Initialize appropriate service
        scheduler = SupplyResearchScheduler(background_manager, llm_manager)
        
        # Mock: Database access isolation for fast, reliable unit testing
        with patch('netra_backend.app.db.postgres.Database') as mock_db_manager:
            # Mock: Generic component isolation for controlled unit testing
            mock_db = TestDatabaseManager().get_session()
            # Mock: Component isolation for controlled unit testing
            mock_db_manager.return_value.get_db.return_value.__enter__ = Mock(return_value=mock_db)
            # Mock: Component isolation for controlled unit testing
            mock_db_manager.return_value.get_db.return_value.__exit__ = Mock(return_value=None)
            
            # Mock agent execution
            with patch.object(SupplyResearcherAgent, 'execute', new_callable=AsyncMock):
                result = await scheduler.run_schedule_now("daily_pricing_check")
                assert result["schedule_name"] == "daily_pricing_check"