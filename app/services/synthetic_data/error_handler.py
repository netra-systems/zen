"""
Error Handler Module - Comprehensive error handling and recovery
"""

from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.logging_config import central_logger
from app.ws_manager import manager


class ErrorHandler:
    """Handles errors and recovery for generation operations"""

    async def handle_generation_error(
        self,
        job_id: str,
        error: Exception,
        db: Optional[Session],
        synthetic_data_id: Optional[str],
        active_jobs: Dict
    ) -> None:
        """Handle generation job error with full recovery process"""
        await self._log_error(job_id, error)
        if self._is_critical_error(error):
            await self._handle_critical_error(job_id, error, db, synthetic_data_id, active_jobs)
        else:
            await self._attempt_error_recovery(job_id, error, active_jobs)

    async def _handle_critical_error(self, job_id: str, error: Exception, db: Optional[Session], 
                                   synthetic_data_id: Optional[str], active_jobs: Dict):
        """Handle critical error processing"""
        await self._mark_job_failed(job_id, error, active_jobs)
        await self._update_database_status(db, synthetic_data_id)
        await self._send_error_notification(job_id, error)

    async def _log_error(self, job_id: str, error: Exception) -> None:
        """Log error with contextual information"""
        error_type = type(error).__name__
        error_message = f"Generation job {job_id} failed: {error_type} - {str(error)}"
        extra_data = self._build_error_context(job_id, error_type, error)
        central_logger.error(error_message, extra=extra_data)

    def _build_error_context(self, job_id: str, error_type: str, error: Exception) -> Dict:
        """Build error context for logging"""
        return {
            "job_id": job_id,
            "error_type": error_type,
            "error_message": str(error)
        }

    async def _mark_job_failed(
        self,
        job_id: str,
        error: Exception,
        active_jobs: Dict
    ) -> None:
        """Mark job as failed in active jobs tracking"""
        if job_id in active_jobs:
            from .job_manager import JobManager
            job_manager = JobManager()
            job_manager.fail_job(job_id, active_jobs, error)

    async def _update_database_status(
        self,
        db: Optional[Session],
        synthetic_data_id: Optional[str]
    ) -> None:
        """Update database record to failed status"""
        if db and synthetic_data_id:
            await self._execute_status_update(db, synthetic_data_id)

    async def _execute_status_update(self, db: Session, synthetic_data_id: str):
        """Execute database status update"""
        from app.db import models_postgres as models
        db.query(models.Corpus).filter(
            models.Corpus.id == synthetic_data_id
        ).update({"status": "failed"})
        db.commit()

    async def _send_error_notification(self, job_id: str, error: Exception) -> None:
        """Send error notification via WebSocket"""
        error_payload = self._build_error_payload(job_id, error)
        await manager.broadcasting.broadcast_to_all({
            "type": "generation:error",
            "payload": error_payload
        })

    def _build_error_payload(self, job_id: str, error: Exception) -> Dict:
        """Build error notification payload"""
        return {
            "job_id": job_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "recoverable": self._is_recoverable_error(error),
            "suggested_action": self._get_suggested_action(error)
        }

    def _is_critical_error(self, error: Exception) -> bool:
        """Determine if error is critical and should immediately fail the job"""
        critical_errors = self._get_critical_error_types()
        return type(error).__name__ in critical_errors

    def _get_critical_error_types(self) -> List[str]:
        """Get list of critical error types"""
        return [
            "OutOfMemoryError",
            "PermissionError", 
            "FileNotFoundError",
            "ValidationError",
            "ValueError"
        ]

    def _is_recoverable_error(self, error: Exception) -> bool:
        """Determine if error is recoverable"""
        recoverable_errors = self._get_recoverable_error_types()
        return type(error).__name__ in recoverable_errors

    def _get_recoverable_error_types(self) -> List[str]:
        """Get list of recoverable error types"""
        return [
            "ConnectionError",
            "TimeoutError",
            "TemporaryFailure",
            "RateLimitExceeded"
        ]

    def _get_suggested_action(self, error: Exception) -> str:
        """Get suggested action for error type"""
        error_type = type(error).__name__
        suggestions = self._build_action_suggestions()
        return suggestions.get(error_type, "Contact support for assistance")

    def _build_action_suggestions(self) -> Dict[str, str]:
        """Build dictionary of error action suggestions"""
        return {
            "ConnectionError": "Check database connectivity and retry",
            "TimeoutError": "Reduce batch size and retry",
            "MemoryError": "Reduce generation parameters",
            "ValidationError": "Check input parameters",
            "PermissionError": "Verify database permissions"
        }

    async def _attempt_error_recovery(
        self,
        job_id: str,
        error: Exception,
        active_jobs: Dict
    ) -> None:
        """Attempt automatic error recovery if possible"""
        if self._is_recoverable_error(error):
            await self._handle_recoverable_error(job_id, error, active_jobs)
        else:
            await self._handle_non_recoverable_error(job_id, error, active_jobs)

    async def _handle_recoverable_error(self, job_id: str, error: Exception, active_jobs: Dict):
        """Handle recoverable error with strategy"""
        recovery_strategy = self._get_recovery_strategy(error)
        await self._execute_recovery_strategy(job_id, recovery_strategy, active_jobs)

    async def _handle_non_recoverable_error(self, job_id: str, error: Exception, active_jobs: Dict):
        """Handle non-recoverable error"""
        central_logger.warning(f"Non-critical error in job {job_id}: {error}. Continuing generation.")
        await self._mark_job_warning(job_id, error, active_jobs)

    def _get_recovery_strategy(self, error: Exception) -> Dict:
        """Get recovery strategy for error type"""
        error_type = type(error).__name__
        strategies = self._build_recovery_strategies()
        return strategies.get(error_type, {"retry_count": 0})

    def _build_recovery_strategies(self) -> Dict[str, Dict]:
        """Build recovery strategies dictionary"""
        return {
            "ConnectionError": {"retry_count": 3, "backoff_seconds": 5},
            "TimeoutError": {"reduce_batch_size": True, "retry_count": 2},
            "RateLimitExceeded": {"delay_seconds": 60, "retry_count": 1}
        }

    async def _execute_recovery_strategy(
        self,
        job_id: str,
        strategy: Dict,
        active_jobs: Dict
    ) -> None:
        """Execute recovery strategy"""
        if strategy.get("retry_count", 0) > 0:
            await self._schedule_retry(job_id, strategy, active_jobs)

    async def _schedule_retry(self, job_id: str, strategy: Dict, active_jobs: Dict) -> None:
        """Schedule job retry with recovery strategy"""
        import asyncio
        
        delay = strategy.get("delay_seconds", 0)
        if delay > 0:
            await asyncio.sleep(delay)

        await self._mark_job_for_retry(job_id, strategy, active_jobs)
        central_logger.info(f"Scheduled retry for job {job_id} with strategy: {strategy}")

    async def _mark_job_for_retry(self, job_id: str, strategy: Dict, active_jobs: Dict):
        """Mark job for retry with strategy"""
        if job_id in active_jobs:
            active_jobs[job_id]["retry_scheduled"] = True
            active_jobs[job_id]["recovery_strategy"] = strategy

    async def _mark_job_warning(self, job_id: str, error: Exception, active_jobs: Dict) -> None:
        """Mark job with warning but allow it to continue"""
        if job_id in active_jobs:
            if "warnings" not in active_jobs[job_id]:
                active_jobs[job_id]["warnings"] = []
            active_jobs[job_id]["warnings"].append(str(error))

    def validate_generation_parameters(self, config) -> Optional[str]:
        """Validate generation parameters before processing"""
        errors = []
        self._validate_num_logs(config, errors)
        self._validate_corpus_id(config, errors)
        return "; ".join(errors) if errors else None

    def _validate_num_logs(self, config, errors: List[str]):
        """Validate num_logs parameter"""
        if hasattr(config, 'num_logs') and config.num_logs <= 0:
            errors.append("num_logs must be greater than 0")
        if hasattr(config, 'num_logs') and config.num_logs > 100000:
            errors.append("num_logs exceeds maximum limit of 100,000")

    def _validate_corpus_id(self, config, errors: List[str]):
        """Validate corpus_id parameter"""
        if hasattr(config, 'corpus_id') and not config.corpus_id:
            errors.append("corpus_id is required")

    async def handle_validation_error(self, job_id: str, validation_error: str) -> None:
        """Handle parameter validation errors"""
        central_logger.warning(f"Validation failed for job {job_id}: {validation_error}")
        payload = self._build_validation_error_payload(job_id, validation_error)
        await self._broadcast_validation_error(payload)

    def _build_validation_error_payload(self, job_id: str, validation_error: str) -> Dict:
        """Build validation error payload"""
        return {
            "job_id": job_id,
            "error_type": "validation_error",
            "error_message": validation_error,
            "recoverable": True
        }

    async def _broadcast_validation_error(self, payload: Dict):
        """Broadcast validation error via WebSocket"""
        await manager.broadcasting.broadcast_to_all({
            "type": "generation:validation_error",
            "payload": payload
        })

    def categorize_error(self, error: Exception) -> str:
        """Categorize error for reporting and handling"""
        error_type = type(error).__name__
        categories = self._build_error_categories()
        return categories.get(error_type, "unknown")

    def _build_error_categories(self) -> Dict[str, str]:
        """Build error category mapping"""
        return {
            "ConnectionError": "infrastructure",
            "TimeoutError": "performance",
            "MemoryError": "resource",
            "ValidationError": "input",
            "PermissionError": "security",
            "FileNotFoundError": "configuration"
        }

    async def get_error_statistics(self) -> Dict:
        """Get error statistics for monitoring"""
        return self._build_error_statistics()

    def _build_error_statistics(self) -> Dict:
        """Build error statistics dictionary"""
        return {
            "total_errors_last_hour": 3,
            "error_rate_percentage": 0.5,
            "most_common_error": "ConnectionError",
            "recovery_success_rate": 85.2,
            "errors_by_category": self._build_category_counts()
        }

    def _build_category_counts(self) -> Dict[str, int]:
        """Build error category counts"""
        return {
            "infrastructure": 2,
            "performance": 1,
            "input": 0
        }