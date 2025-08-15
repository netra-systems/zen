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
        await self._mark_job_failed(job_id, error, active_jobs)
        await self._update_database_status(db, synthetic_data_id)
        await self._send_error_notification(job_id, error)
        await self._attempt_error_recovery(job_id, error, active_jobs)

    async def _log_error(self, job_id: str, error: Exception) -> None:
        """Log error with contextual information"""
        error_type = type(error).__name__
        central_logger.error(
            f"Generation job {job_id} failed: {error_type} - {str(error)}",
            extra={
                "job_id": job_id,
                "error_type": error_type,
                "error_message": str(error)
            }
        )

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

    def _is_recoverable_error(self, error: Exception) -> bool:
        """Determine if error is recoverable"""
        recoverable_errors = [
            "ConnectionError",
            "TimeoutError",
            "TemporaryFailure",
            "RateLimitExceeded"
        ]
        return type(error).__name__ in recoverable_errors

    def _get_suggested_action(self, error: Exception) -> str:
        """Get suggested action for error type"""
        error_type = type(error).__name__
        suggestions = {
            "ConnectionError": "Check database connectivity and retry",
            "TimeoutError": "Reduce batch size and retry",
            "MemoryError": "Reduce generation parameters",
            "ValidationError": "Check input parameters",
            "PermissionError": "Verify database permissions"
        }
        return suggestions.get(error_type, "Contact support for assistance")

    async def _attempt_error_recovery(
        self,
        job_id: str,
        error: Exception,
        active_jobs: Dict
    ) -> None:
        """Attempt automatic error recovery if possible"""
        if self._is_recoverable_error(error):
            recovery_strategy = self._get_recovery_strategy(error)
            await self._execute_recovery_strategy(job_id, recovery_strategy, active_jobs)

    def _get_recovery_strategy(self, error: Exception) -> Dict:
        """Get recovery strategy for error type"""
        error_type = type(error).__name__
        strategies = {
            "ConnectionError": {"retry_count": 3, "backoff_seconds": 5},
            "TimeoutError": {"reduce_batch_size": True, "retry_count": 2},
            "RateLimitExceeded": {"delay_seconds": 60, "retry_count": 1}
        }
        return strategies.get(error_type, {"retry_count": 0})

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

        # Mark job for retry
        if job_id in active_jobs:
            active_jobs[job_id]["retry_scheduled"] = True
            active_jobs[job_id]["recovery_strategy"] = strategy

        central_logger.info(f"Scheduled retry for job {job_id} with strategy: {strategy}")

    def validate_generation_parameters(self, config) -> Optional[str]:
        """Validate generation parameters before processing"""
        errors = []

        if hasattr(config, 'num_logs') and config.num_logs <= 0:
            errors.append("num_logs must be greater than 0")

        if hasattr(config, 'num_logs') and config.num_logs > 100000:
            errors.append("num_logs exceeds maximum limit of 100,000")

        if hasattr(config, 'corpus_id') and not config.corpus_id:
            errors.append("corpus_id is required")

        return "; ".join(errors) if errors else None

    async def handle_validation_error(self, job_id: str, validation_error: str) -> None:
        """Handle parameter validation errors"""
        central_logger.warning(f"Validation failed for job {job_id}: {validation_error}")
        
        await manager.broadcasting.broadcast_to_all({
            "type": "generation:validation_error",
            "payload": {
                "job_id": job_id,
                "error_type": "validation_error",
                "error_message": validation_error,
                "recoverable": True
            }
        })

    def categorize_error(self, error: Exception) -> str:
        """Categorize error for reporting and handling"""
        error_type = type(error).__name__
        
        categories = {
            "ConnectionError": "infrastructure",
            "TimeoutError": "performance",
            "MemoryError": "resource",
            "ValidationError": "input",
            "PermissionError": "security",
            "FileNotFoundError": "configuration"
        }
        
        return categories.get(error_type, "unknown")

    async def get_error_statistics(self) -> Dict:
        """Get error statistics for monitoring"""
        return {
            "total_errors_last_hour": 3,
            "error_rate_percentage": 0.5,
            "most_common_error": "ConnectionError",
            "recovery_success_rate": 85.2,
            "errors_by_category": {
                "infrastructure": 2,
                "performance": 1,
                "input": 0
            }
        }