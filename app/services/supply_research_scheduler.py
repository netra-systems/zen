"""
Supply Research Scheduler - Background task scheduling for periodic supply updates
Main scheduler service using modular components
"""

import asyncio
from typing import Dict, List, Optional, Any
from app.background import BackgroundTaskManager
from app.llm.llm_manager import LLMManager
from app.redis_manager import RedisManager
from app.logging_config import central_logger as logger

# Import modular components
from app.services.supply_research.scheduler_models import ScheduleFrequency, ResearchSchedule
from app.services.supply_research.schedule_manager import ScheduleManager
from app.services.supply_research.research_executor import ResearchExecutor
from app.services.supply_research.result_manager import ResultManager

# Mock Database class removed - was test stub in production code


class SupplyResearchScheduler:
    """Scheduler for automated supply research tasks"""
    
    def __init__(
        self,
        background_manager: BackgroundTaskManager,
        llm_manager: LLMManager
    ):
        self.background_manager = background_manager
        self.llm_manager = llm_manager
        self.running = False
        self.redis_manager = None
        
        try:
            self.redis_manager = RedisManager()
        except Exception as e:
            logger.warning(f"Redis not available for scheduler: {e}")
        
        # Initialize modular components
        self.schedule_manager = ScheduleManager()
        self.research_executor = ResearchExecutor(self.llm_manager, self.redis_manager)
        self.result_manager = ResultManager(self.redis_manager)
    
    # Delegate schedule management to ScheduleManager
    def add_schedule(self, schedule: ResearchSchedule):
        """Add a new research schedule"""
        self.schedule_manager.add_schedule(schedule)
    
    def remove_schedule(self, name: str):
        """Remove a research schedule by name"""
        self.schedule_manager.remove_schedule(name)
    
    def enable_schedule(self, name: str):
        """Enable a research schedule"""
        self.schedule_manager.enable_schedule(name)
    
    def disable_schedule(self, name: str):
        """Disable a research schedule"""
        self.schedule_manager.disable_schedule(name)
    
    def get_schedule_status(self) -> List[Dict[str, Any]]:
        """Get status of all schedules"""
        return self.schedule_manager.get_schedule_status()
    
    @property
    def schedules(self) -> Dict[str, Any]:
        """Get all schedules - compatibility property for tests"""
        return self.schedule_manager.schedules
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Supply research scheduler started")
        
        while self.running:
            try:
                # Check each schedule
                runnable_schedules = self.schedule_manager.get_runnable_schedules()
                
                for schedule in runnable_schedules:
                    # Execute in background
                    self.background_manager.add_task(
                        self.research_executor.execute_scheduled_research(schedule)
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
    
    async def _execute_scheduled_research(self, schedule: ResearchSchedule) -> Dict[str, Any]:
        """Execute scheduled research - delegation to research executor"""
        return await self.research_executor.execute_scheduled_research(schedule)
    
    async def run_schedule_now(self, name: str) -> Dict[str, Any]:
        """Manually trigger a schedule to run immediately"""
        schedule = self.schedule_manager.get_schedule_by_name(name)
        logger.info(f"Manually triggering schedule: {name}")
        return await self.research_executor.execute_scheduled_research(schedule)
    
    async def get_recent_results(
        self,
        schedule_name: Optional[str] = None,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """Get recent research results from cache"""
        return await self.result_manager.get_recent_results(
            self.schedule_manager.schedules,
            schedule_name,
            days_back
        )


# Re-export classes for backward compatibility
__all__ = [
    'SupplyResearchScheduler',
    'ScheduleFrequency',
    'ResearchSchedule'
]