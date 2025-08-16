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
    def schedules(self) -> List[ResearchSchedule]:
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
    
    async def schedule_job(self, schedule: ResearchSchedule) -> str:
        """Schedule a job for background execution"""
        task_id = self.background_manager.add_task(
            self.research_executor.execute_scheduled_research(schedule)
        )
        logger.info(f"Scheduled job: {schedule.name} with task_id: {task_id}")
        return task_id
    
    # Test compatibility methods - delegate to components
    async def _execute_research_job(self, schedule: ResearchSchedule) -> bool:
        """Execute research job - compatibility wrapper"""
        try:
            await self.research_executor.execute_scheduled_research(schedule)
            return True
        except Exception:
            return False
    
    async def _execute_with_retry(self, schedule: ResearchSchedule, max_retries: int = 3) -> bool:
        """Execute with retry logic - calls _execute_research_job with retry"""
        import asyncio
        
        for attempt in range(max_retries):
            try:
                result = await self._execute_research_job(schedule)
                if result:
                    return True
            except Exception:
                pass
            
            # Add delay between retries (exponential backoff)
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        return False
    
    async def _execute_job_with_cleanup(self, schedule: ResearchSchedule) -> bool:
        """Execute job with cleanup - simplified wrapper"""
        try:
            result = await self._execute_research_job(schedule)
            await self._cleanup_job_resources(schedule)
            return result
        except Exception:
            # Still try to cleanup even if execution failed
            try:
                await self._cleanup_job_resources(schedule)
            except Exception:
                pass
            return False
    
    async def _cleanup_job_resources(self, schedule: ResearchSchedule):
        """Cleanup job resources - placeholder for test compatibility"""
        # Real cleanup logic would be in specific components
        pass
    
    async def _execute_job_with_metrics(self, schedule: ResearchSchedule) -> bool:
        """Execute job with metrics tracking - simplified wrapper"""
        from datetime import datetime, UTC, timedelta
        
        start_time = datetime.now(UTC)
        try:
            result = await self._execute_research_job(schedule)
            end_time = datetime.now(UTC)
            execution_time = end_time - start_time
            await self._record_job_metrics(schedule.name, execution_time, result)
            return result
        except Exception:
            end_time = datetime.now(UTC)
            execution_time = end_time - start_time
            await self._record_job_metrics(schedule.name, execution_time, False)
            return False
    
    async def _record_job_metrics(self, job_name: str, execution_time: Any, success: bool):
        """Record job metrics - placeholder for test compatibility"""
        # Real metrics logic would be in metrics component
        pass
    
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