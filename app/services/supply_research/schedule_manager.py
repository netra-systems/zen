"""
Schedule Management
Handles CRUD operations for research schedules
"""

from typing import List, Dict, Any
from app.agents.supply_researcher.models import ResearchType
from app.logging_config import central_logger as logger
from .scheduler_models import ScheduleFrequency, ResearchSchedule


class ScheduleManager:
    """Manages research schedules with CRUD operations"""
    
    def __init__(self):
        self.schedules: List[ResearchSchedule] = []
        self._initialize_default_schedules()
    
    def _initialize_default_schedules(self):
        """Initialize default research schedules"""
        
        # Daily pricing check at 2 AM UTC
        self.schedules.append(ResearchSchedule(
            name="daily_pricing_check",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.PRICING,
            hour=2,
            enabled=True
        ))
        
        # Weekly capability scan on Mondays at 9 AM UTC
        self.schedules.append(ResearchSchedule(
            name="weekly_capability_scan",
            frequency=ScheduleFrequency.WEEKLY,
            research_type=ResearchType.CAPABILITIES,
            day_of_week=0,  # Monday
            hour=9,
            enabled=True
        ))
        
        # Weekly new model check on Fridays at 10 AM UTC
        self.schedules.append(ResearchSchedule(
            name="weekly_new_models",
            frequency=ScheduleFrequency.WEEKLY,
            research_type=ResearchType.NEW_MODEL,
            day_of_week=4,  # Friday
            hour=10,
            enabled=True
        ))
        
        # Monthly market overview on 1st at midnight UTC
        self.schedules.append(ResearchSchedule(
            name="monthly_market_report",
            frequency=ScheduleFrequency.MONTHLY,
            research_type=ResearchType.MARKET_OVERVIEW,
            day_of_month=1,
            hour=0,
            enabled=True
        ))
        
        logger.info(f"Initialized {len(self.schedules)} default research schedules")
    
    def add_schedule(self, schedule: ResearchSchedule):
        """Add a new research schedule"""
        self.schedules.append(schedule)
        logger.info(f"Added research schedule: {schedule.name}")
    
    def remove_schedule(self, name: str):
        """Remove a research schedule by name"""
        self.schedules = [s for s in self.schedules if s.name != name]
        logger.info(f"Removed research schedule: {name}")
    
    def enable_schedule(self, name: str):
        """Enable a research schedule"""
        for schedule in self.schedules:
            if schedule.name == name:
                schedule.enabled = True
                logger.info(f"Enabled research schedule: {name}")
                break
    
    def disable_schedule(self, name: str):
        """Disable a research schedule"""
        for schedule in self.schedules:
            if schedule.name == name:
                schedule.enabled = False
                logger.info(f"Disabled research schedule: {name}")
                break
    
    def get_schedule_status(self) -> List[Dict[str, Any]]:
        """Get status of all schedules"""
        return [
            {
                "name": schedule.name,
                "frequency": schedule.frequency.value,
                "research_type": schedule.research_type.value,
                "enabled": schedule.enabled,
                "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
                "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
                "providers": schedule.providers
            }
            for schedule in self.schedules
        ]
    
    def get_schedule_by_name(self, name: str) -> ResearchSchedule:
        """Get schedule by name"""
        for schedule in self.schedules:
            if schedule.name == name:
                return schedule
        raise ValueError(f"Schedule not found: {name}")
    
    def get_runnable_schedules(self) -> List[ResearchSchedule]:
        """Get schedules that should run now"""
        return [schedule for schedule in self.schedules if schedule.should_run()]