"""
Supply Research Scheduler - Background task scheduling for periodic supply updates
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import json

from app.background import BackgroundTaskManager
from app.agents.supply_researcher_sub_agent import SupplyResearcherAgent, ResearchType
from app.services.supply_research_service import SupplyResearchService
from app.llm.llm_manager import LLMManager
from app.redis_manager import RedisManager
from app.core.exceptions import NetraException
from app.db.postgres import Database

logger = logging.getLogger(__name__)


class ScheduleFrequency(Enum):
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
        self.hour = hour or 2  # Default to 2 AM
        self.day_of_week = day_of_week or 1  # Default to Monday
        self.day_of_month = day_of_month or 1  # Default to 1st
        self.last_run = None
        self.next_run = self._calculate_next_run()
    
    def _calculate_next_run(self) -> datetime:
        """Calculate next run time based on frequency"""
        # Use last_run as base if available, otherwise use current time
        base_time = self.last_run if self.last_run else datetime.utcnow()
        now = datetime.utcnow()
        
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
            days_ahead = self.day_of_week - now.weekday()
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
        
        now = datetime.utcnow()
        return now >= self.next_run
    
    def update_after_run(self):
        """Update schedule after successful run"""
        self.last_run = datetime.utcnow()
        # When updating after a run, calculate next run from the current last_run
        # This ensures next_run advances properly
        if self.frequency == ScheduleFrequency.HOURLY:
            self.next_run = self.last_run.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            self.next_run = self._calculate_next_run()


class SupplyResearchScheduler:
    """Scheduler for automated supply research tasks"""
    
    def __init__(
        self,
        background_manager: BackgroundTaskManager,
        llm_manager: LLMManager
    ):
        self.background_manager = background_manager
        self.llm_manager = llm_manager
        self.schedules: List[ResearchSchedule] = []
        self.running = False
        self.redis_manager = None
        
        try:
            self.redis_manager = RedisManager()
        except Exception as e:
            logger.warning(f"Redis not available for scheduler: {e}")
        
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
    
    async def _execute_scheduled_research(
        self,
        schedule: ResearchSchedule
    ) -> Dict[str, Any]:
        """Execute a scheduled research task"""
        logger.info(f"Executing scheduled research: {schedule.name}")
        
        result = {
            "schedule_name": schedule.name,
            "started_at": datetime.utcnow().isoformat(),
            "research_type": schedule.research_type.value,
            "providers": schedule.providers,
            "results": []
        }
        
        try:
            # Get database session
            db_manager = Database()
            with db_manager.get_db() as db:
                # Create agent and service
                supply_service = SupplyResearchService(db)
                agent = SupplyResearcherAgent(self.llm_manager, db, supply_service)
                
                # Process research for each provider
                research_result = await agent.process_scheduled_research(
                    schedule.research_type,
                    schedule.providers
                )
                
                result["results"] = research_result.get("results", [])
                result["status"] = "completed"
                result["completed_at"] = datetime.utcnow().isoformat()
                
                # Cache result if Redis available
                if self.redis_manager:
                    cache_key = f"schedule_result:{schedule.name}:{datetime.utcnow().date()}"
                    await self.redis_manager.set(
                        cache_key,
                        json.dumps(result, default=str),
                        ex=86400  # Cache for 24 hours
                    )
                
                # Check for significant changes and send notifications
                await self._check_and_notify_changes(result, supply_service)
                
                # Update schedule
                schedule.update_after_run()
                
                logger.info(f"Completed scheduled research: {schedule.name}")
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled research {schedule.name}: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result
    
    async def _check_and_notify_changes(
        self,
        result: Dict[str, Any],
        supply_service: SupplyResearchService
    ):
        """Check for significant changes and send notifications"""
        try:
            # Check for price changes above threshold
            price_changes = supply_service.calculate_price_changes(days_back=1)
            
            significant_changes = []
            for change in price_changes.get("all_changes", []):
                if abs(change["percent_change"]) > 10:  # 10% threshold
                    significant_changes.append({
                        "type": "price_change",
                        "provider": change["provider"],
                        "model": change["model"],
                        "field": change["field"],
                        "percent_change": change["percent_change"]
                    })
            
            # Check for new models
            for provider_result in result.get("results", []):
                if provider_result.get("result", {}).get("updates_made", {}).get("updates_count", 0) > 0:
                    for update in provider_result["result"]["updates_made"]["updates"]:
                        if update.get("action") == "created":
                            significant_changes.append({
                                "type": "new_model",
                                "model": update["model"]
                            })
            
            if significant_changes:
                # In production, send notifications via email/webhook/etc.
                logger.warning(f"Significant changes detected: {json.dumps(significant_changes, indent=2)}")
                
                # Cache notifications
                if self.redis_manager:
                    await self.redis_manager.lpush(
                        "supply_notifications",
                        json.dumps({
                            "timestamp": datetime.utcnow().isoformat(),
                            "changes": significant_changes
                        }, default=str)
                    )
        
        except Exception as e:
            logger.error(f"Failed to check and notify changes: {e}")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Supply research scheduler started")
        
        while self.running:
            try:
                # Check each schedule
                for schedule in self.schedules:
                    if schedule.should_run():
                        # Execute in background
                        self.background_manager.add_task(
                            self._execute_scheduled_research(schedule)
                        )
                
                # Sleep for 1 minute before next check
                await asyncio.sleep(60)
            
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Continue after error
        
        logger.info("Supply research scheduler stopped")
    
    def start(self):
        """Start the scheduler"""
        if not self.running:
            self.running = True
            self.background_manager.add_task(self._scheduler_loop())
            logger.info("Supply research scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Supply research scheduler stopping...")
    
    async def run_schedule_now(self, name: str) -> Dict[str, Any]:
        """Manually trigger a schedule to run immediately"""
        for schedule in self.schedules:
            if schedule.name == name:
                logger.info(f"Manually triggering schedule: {name}")
                return await self._execute_scheduled_research(schedule)
        
        raise ValueError(f"Schedule not found: {name}")
    
    async def get_recent_results(
        self,
        schedule_name: Optional[str] = None,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """Get recent research results from cache"""
        if not self.redis_manager:
            return []
        
        results = []
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Build cache key pattern
        if schedule_name:
            pattern = f"schedule_result:{schedule_name}:*"
        else:
            pattern = "schedule_result:*"
        
        # Get matching keys (simplified - in production use SCAN)
        # For now, check last N days
        for i in range(days_back):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            
            if schedule_name:
                keys = [f"schedule_result:{schedule_name}:{date}"]
            else:
                keys = [f"schedule_result:{s.name}:{date}" for s in self.schedules]
            
            for key in keys:
                try:
                    data = await self.redis_manager.get(key)
                    if data:
                        result = json.loads(data)
                        results.append(result)
                except Exception as e:
                    logger.debug(f"Failed to get cached result for {key}: {e}")
        
        return results