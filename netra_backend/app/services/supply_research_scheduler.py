"""
Supply Research Scheduler - Background task scheduling for periodic supply updates
Main scheduler service using modular components
"""

import asyncio
from typing import Any, Dict, List, Optional

from netra_backend.app.services.background_task_manager import BackgroundTaskManager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.supply_research.research_executor import (
    ResearchExecutor,
)
from netra_backend.app.services.supply_research.result_manager import ResultManager
from netra_backend.app.services.supply_research.schedule_manager import ScheduleManager

# Import modular components
from netra_backend.app.services.supply_research.scheduler_models import (
    ResearchSchedule,
    ScheduleFrequency,
)

# Mock Database class removed - was test stub in production code


class SupplyResearchScheduler:
    """Scheduler for automated supply research tasks"""
    
    def __init__(
        self,
        background_manager: BackgroundTaskManager,
        llm_manager: LLMManager
    ):
        self._initialize_dependencies(background_manager, llm_manager)
        self._setup_redis_connection()
        self._initialize_components()
    
    def _initialize_dependencies(self, background_manager: BackgroundTaskManager, llm_manager: LLMManager):
        """Initialize core dependencies"""
        self.background_manager = background_manager
        self.llm_manager = llm_manager
        self.running = False
        self.redis_manager = None
    
    def _setup_redis_connection(self):
        """Setup Redis connection with error handling"""
        try:
            from netra_backend.app.redis_manager import redis_manager
            self.redis_manager = redis_manager
        except Exception as e:
            logger.warning(f"Redis not available for scheduler: {e}")
    
    def _initialize_components(self):
        """Initialize modular components"""
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
            await self._run_scheduler_iteration()
        logger.info("Supply research scheduler stopped")
    
    async def _run_scheduler_iteration(self):
        """Run single scheduler iteration"""
        try:
            runnable_schedules = self.schedule_manager.get_runnable_schedules()
            await self._execute_runnable_schedules(runnable_schedules)
            await asyncio.sleep(60)
        except Exception as e:
            await self._handle_scheduler_error(e)
    
    async def _execute_runnable_schedules(self, runnable_schedules):
        """Execute all runnable schedules in background"""
        for schedule in runnable_schedules:
            self.background_manager.add_task(
                self.research_executor.execute_scheduled_research(schedule)
            )
    
    async def _handle_scheduler_error(self, error: Exception):
        """Handle scheduler loop error"""
        logger.error(f"Error in scheduler loop: {error}")
        await asyncio.sleep(60)
    
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
    
    async def _get_retry_count_from_redis(self, retry_key: str) -> int:
        """Get current retry count from Redis"""
        if not self.redis_manager:
            return 0
        try:
            return await self._fetch_retry_value_from_redis(retry_key)
        except Exception:
            return 0
    
    async def _fetch_retry_value_from_redis(self, retry_key: str) -> int:
        """Fetch and convert retry value from Redis"""
        current_count = await self.redis_manager.get(retry_key)
        return int(current_count) if current_count else 0
    
    async def _update_retry_count_in_redis(self, retry_key: str, retry_count: int) -> None:
        """Update retry count in Redis with TTL"""
        if not self.redis_manager:
            return
        try:
            await self._set_retry_count_with_ttl(retry_key, retry_count)
        except Exception as e:
            logger.warning(f"Failed to update retry state in Redis: {e}")
    
    async def _set_retry_count_with_ttl(self, retry_key: str, retry_count: int):
        """Set retry count and TTL in Redis"""
        new_count = retry_count + 1
        await self.redis_manager.set(retry_key, str(new_count))
        await self.redis_manager.expire(retry_key, 3600)
    
    async def _log_retry_attempt(self, schedule: ResearchSchedule, attempt: int, max_retries: int, error: Exception) -> None:
        """Log retry attempt information"""
        logger.error(f"Job execution failed for {schedule.name} (attempt {attempt + 1}/{max_retries}): {error}")
        if attempt == max_retries - 1:
            logger.error(f"Job {schedule.name} failed after {max_retries} attempts")
    
    async def _attempt_job_execution(self, schedule: ResearchSchedule, attempt: int, max_retries: int, retry_key: str) -> bool:
        """Attempt to execute job once with error handling"""
        retry_count = await self._get_current_retry_count(retry_key, attempt)
        try:
            return await self._execute_job_attempt(schedule)
        except Exception as e:
            await self._log_retry_attempt(schedule, attempt, max_retries, e)
            return False
    
    async def _get_current_retry_count(self, retry_key: str, attempt: int) -> int:
        """Get current retry count with fallback"""
        retry_count = await self._get_retry_count_from_redis(retry_key)
        return retry_count if self.redis_manager else attempt
    
    async def _execute_job_attempt(self, schedule: ResearchSchedule) -> bool:
        """Execute job and return result"""
        result = await self._execute_research_job(schedule)
        return result if result else False
    
    async def _execute_with_retry(self, schedule: ResearchSchedule, max_retries: int = 3) -> bool:
        """Execute with retry logic - calls _execute_research_job with retry"""
        import asyncio
        retry_key = f"scheduler:retry:{schedule.name}"
        return await self._run_retry_loop(schedule, max_retries, retry_key)
    
    async def _run_retry_loop(self, schedule: ResearchSchedule, max_retries: int, retry_key: str) -> bool:
        """Run the retry loop with delay handling"""
        for attempt in range(max_retries):
            if await self._attempt_job_execution(schedule, attempt, max_retries, retry_key):
                return True
            await self._handle_retry_delay(retry_key, attempt, max_retries)
        return False
    
    async def _handle_retry_delay(self, retry_key: str, attempt: int, max_retries: int):
        """Handle retry delay and count update"""
        await self._update_retry_count_in_redis(retry_key, attempt)
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)
    
    async def _execute_job_with_cleanup(self, schedule: ResearchSchedule) -> bool:
        """Execute job with cleanup - simplified wrapper"""
        try:
            return await self._run_job_with_cleanup(schedule)
        except Exception:
            await self._perform_cleanup_safely(schedule)
            return False
    
    async def _run_job_with_cleanup(self, schedule: ResearchSchedule) -> bool:
        """Run job and cleanup on success"""
        result = await self._execute_research_job(schedule)
        await self._cleanup_job_resources(schedule)
        return result
    
    async def _perform_cleanup_safely(self, schedule: ResearchSchedule):
        """Perform cleanup with error handling"""
        try:
            await self._cleanup_job_resources(schedule)
        except Exception:
            pass
    
    async def _cleanup_job_resources(self, schedule: ResearchSchedule):
        """Cleanup job resources after execution"""
        try:
            await self._clear_schedule_cache(schedule)
            self._log_cleanup_completion(schedule)
        except Exception as e:
            logger.warning(f"Resource cleanup failed for {schedule.name}: {e}")
    
    async def _clear_schedule_cache(self, schedule: ResearchSchedule):
        """Clear cache entries for schedule"""
        cache_key = f"schedule_{schedule.name}"
        if hasattr(self, 'cache') and self.cache:
            await self.cache.delete(cache_key)
    
    def _log_cleanup_completion(self, schedule: ResearchSchedule):
        """Log cleanup completion"""
        logger.debug(f"Cleaned up resources for schedule: {schedule.name}")
    
    async def _execute_job_with_metrics(self, schedule: ResearchSchedule) -> bool:
        """Execute job with metrics tracking - simplified wrapper"""
        start_time = self._get_current_time()
        try:
            return await self._execute_job_timed(schedule, start_time)
        except Exception:
            await self._handle_metrics_recording(schedule, start_time, False)
            return False
    
    def _get_current_time(self):
        """Get current UTC time"""
        from datetime import UTC, datetime
        return datetime.now(UTC)
    
    async def _execute_job_timed(self, schedule: ResearchSchedule, start_time) -> bool:
        """Execute job and record success metrics"""
        result = await self._execute_research_job(schedule)
        await self._handle_metrics_recording(schedule, start_time, result)
        return result
    
    async def _handle_metrics_recording(self, schedule: ResearchSchedule, start_time, result: bool):
        """Handle metrics recording for job execution"""
        from datetime import UTC, datetime
        end_time = datetime.now(UTC)
        execution_time = end_time - start_time
        await self._record_job_metrics(schedule.name, execution_time, result)
    
    async def _record_job_metrics(self, job_name: str, execution_time: Any, success: bool):
        """Record job metrics for monitoring and analysis"""
        try:
            metrics_data = self._build_metrics_data(job_name, execution_time, success)
            await self._store_metrics_data(job_name, metrics_data)
        except Exception as e:
            self._handle_metrics_error(job_name, e)
    
    def _build_metrics_data(self, job_name: str, execution_time: Any, success: bool) -> dict:
        """Build metrics data dictionary"""
        base_data = self._create_base_metrics(job_name, success)
        base_data["execution_time_seconds"] = self._calculate_execution_seconds(execution_time)
        return base_data
    
    def _create_base_metrics(self, job_name: str, success: bool) -> dict:
        """Create base metrics dictionary"""
        timestamp = self._get_current_timestamp()
        return self._build_base_dict(job_name, success, timestamp)
    
    def _get_current_timestamp(self) -> str:
        """Get current UTC timestamp as ISO string"""
        from datetime import UTC, datetime
        return datetime.now(UTC).isoformat()
    
    def _build_base_dict(self, job_name: str, success: bool, timestamp: str) -> dict:
        """Build base metrics dictionary"""
        return {
            "job_name": job_name,
            "success": success,
            "timestamp": timestamp,
            "scheduler_type": "supply_research"
        }
    
    def _calculate_execution_seconds(self, execution_time: Any) -> float:
        """Calculate execution time in seconds"""
        return execution_time.total_seconds() if hasattr(execution_time, 'total_seconds') else float(execution_time)
    
    async def _store_metrics_data(self, job_name: str, metrics_data: dict):
        """Store metrics data in logger and result manager"""
        logger.info(f"Job metrics recorded", extra=metrics_data)
        if hasattr(self, 'result_manager') and self.result_manager:
            await self.result_manager.store_metrics(job_name, metrics_data)
    
    def _handle_metrics_error(self, job_name: str, error: Exception):
        """Handle metrics recording error"""
        logger.error(f"Failed to record metrics for {job_name}: {error}")
    
    async def get_recent_results(
        self,
        schedule_name: Optional[str] = None,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """Get recent research results from cache"""
        return await self._delegate_recent_results(schedule_name, days_back)
    
    async def _delegate_recent_results(self, schedule_name: Optional[str], days_back: int) -> List[Dict[str, Any]]:
        """Delegate to result manager for recent results"""
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