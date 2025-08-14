"""
Supply Research Scheduler Models
Defines scheduling models and frequency enums for supply research tasks
"""

from typing import List, Optional
from datetime import datetime, timedelta, UTC
from enum import Enum
from app.agents.supply_researcher_sub_agent import ResearchType


class ScheduleFrequency(Enum):
    """Schedule frequency options"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ResearchSchedule:
    """Configuration for a scheduled research task"""
    
    def __init__(
        self,
        name: str,
        frequency: ScheduleFrequency,
        research_type: ResearchType,
        providers: Optional[List[str]] = None,
        enabled: bool = True,
        hour: Optional[int] = None,  # For daily/weekly/monthly
        day_of_week: Optional[int] = None,  # For weekly (0=Monday)
        day_of_month: Optional[int] = None  # For monthly
    ):
        self.name = name
        self.frequency = frequency
        self.research_type = research_type
        self.providers = providers or ["openai", "anthropic", "google", "mistral"]
        self.enabled = enabled
        self.hour = hour if hour is not None else 2  # Default to 2 AM
        self.day_of_week = day_of_week if day_of_week is not None else 0  # Default to Monday
        self.day_of_month = day_of_month if day_of_month is not None else 1  # Default to 1st
        self.last_run = None
        self.next_run = self._calculate_next_run()
    
    def _calculate_next_run(self) -> datetime:
        """Calculate next run time based on frequency"""
        # Use last_run as base if available, otherwise use current time
        base_time = self.last_run if self.last_run else datetime.now(UTC)
        now = datetime.now(UTC)
        
        if self.frequency == ScheduleFrequency.HOURLY:
            # Next hour from base_time
            next_run = base_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        elif self.frequency == ScheduleFrequency.DAILY:
            # Next day at specified hour
            next_run = now.replace(hour=self.hour, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        
        elif self.frequency == ScheduleFrequency.WEEKLY:
            # Next specified day of week
            current_weekday = now.weekday()
            days_ahead = self.day_of_week - current_weekday
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            next_run = now.replace(hour=self.hour, minute=0, second=0, microsecond=0)
            next_run += timedelta(days=days_ahead)
        
        elif self.frequency == ScheduleFrequency.MONTHLY:
            # Next month on specified day
            if now.day >= self.day_of_month:
                # Move to next month
                if now.month == 12:
                    next_run = now.replace(year=now.year + 1, month=1)
                else:
                    next_run = now.replace(month=now.month + 1)
            else:
                next_run = now
            
            # Set to specified day and hour
            try:
                next_run = next_run.replace(
                    day=self.day_of_month,
                    hour=self.hour,
                    minute=0,
                    second=0,
                    microsecond=0
                )
            except ValueError:
                # Handle months with fewer days
                next_run = next_run.replace(day=1) + timedelta(days=self.day_of_month - 1)
        
        return next_run
    
    def should_run(self) -> bool:
        """Check if schedule should run now"""
        if not self.enabled:
            return False
        
        now = datetime.now(UTC)
        return now >= self.next_run
    
    def update_after_run(self):
        """Update schedule after successful run"""
        self.last_run = datetime.now(UTC)
        # When updating after a run, calculate next run from the current last_run
        # This ensures next_run advances properly
        if self.frequency == ScheduleFrequency.HOURLY:
            self.next_run = self.last_run.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            self.next_run = self._calculate_next_run()