"""
Tests for ResearchSchedule class and schedule time calculations
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import patch

from app.services.supply_research_scheduler import (
    ResearchSchedule,
    ScheduleFrequency
)
from app.agents.supply_researcher.models import ResearchType


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
        assert schedule.enabled == True
        assert schedule.hour == 2  # Default 2 AM
        assert schedule.day_of_week == 0  # Default Monday
        assert schedule.day_of_month == 1  # Default 1st
        assert schedule.last_run == None
        assert schedule.next_run != None
    
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
        assert schedule.enabled == False
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
        
        now = datetime.now(UTC)
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
        now = datetime.now(UTC)
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
        schedule.next_run = datetime.now(UTC) - timedelta(minutes=5)
        
        assert schedule.should_run() == True
    
    def test_should_run_disabled(self):
        """Test should_run when disabled"""
        schedule = ResearchSchedule(
            name="disabled_test",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.PRICING,
            enabled=False
        )
        
        # Even if time has passed, should not run if disabled
        schedule.next_run = datetime.now(UTC) - timedelta(minutes=5)
        
        assert schedule.should_run() == False
    
    def test_should_run_time_not_reached(self):
        """Test should_run when time has not been reached"""
        schedule = ResearchSchedule(
            name="future_test",
            frequency=ScheduleFrequency.HOURLY,
            research_type=ResearchType.PRICING,
            enabled=True
        )
        
        # Set next_run to future time
        schedule.next_run = datetime.now(UTC) + timedelta(minutes=30)
        
        assert schedule.should_run() == False
    
    def test_update_after_run(self):
        """Test updating schedule after successful run"""
        # Use real datetime objects
        initial_time = datetime(2024, 1, 1, 10, 30, 0, tzinfo=UTC)
        
        with patch('app.services.supply_research.scheduler_models.datetime') as mock_datetime:
            # Configure the mock datetime class
            mock_datetime.now.return_value = initial_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Also handle datetime.now(UTC) calls
            def now_with_tz(tz=None):
                if tz:
                    return initial_time
                return initial_time.replace(tzinfo=None)
            mock_datetime.now = now_with_tz
            
            schedule = ResearchSchedule(
                name="update_test",
                frequency=ScheduleFrequency.HOURLY,
                research_type=ResearchType.PRICING
            )
            
            original_next_run = schedule.next_run
            original_last_run = schedule.last_run
            
            # Move time forward by an hour for the update
            updated_time = initial_time + timedelta(hours=1)
            def now_with_tz_updated(tz=None):
                if tz:
                    return updated_time
                return updated_time.replace(tzinfo=None)
            mock_datetime.now = now_with_tz_updated
            
            schedule.update_after_run()
            
            # Should update last_run and recalculate next_run
            assert schedule.last_run != original_last_run
            assert schedule.last_run != None
            assert schedule.next_run > original_next_run  # Should be later than original


class TestScheduleFrequencyEnum:
    """Test ScheduleFrequency enum"""
    
    def test_schedule_frequency_values(self):
        """Test that enum has expected values"""
        expected_values = ["hourly", "daily", "weekly", "monthly"]
        
        for value in expected_values:
            assert hasattr(ScheduleFrequency, value.upper())
            assert getattr(ScheduleFrequency, value.upper()).value == value


class TestScheduleTimeBoundaries:
    """Test schedule calculations across time boundaries"""
    
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
        mock_time = datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC)
        with patch('app.services.supply_research.scheduler_models.datetime') as mock_datetime:
            # Set up the mock to handle both datetime() constructor and datetime.now(UTC)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            mock_datetime.now.return_value = mock_time
            
            # Make sure the datetime.now(UTC) works
            def now_with_tz(tz=None):
                if tz:
                    return mock_time
                return mock_time.replace(tzinfo=None)
            mock_datetime.now = now_with_tz
            
            next_run = schedule._calculate_next_run()
            
            # Should be January 1st of next year
            assert next_run.year == 2024
            assert next_run.month == 1
            assert next_run.day == 1