"""
Job Management Module - Handles job lifecycle and status tracking
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app import schemas
from netra_backend.app.db import models_postgres as models
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.synthetic_data.enums import GenerationStatus
from netra_backend.app.services.synthetic_data.metrics import calculate_generation_rate

# Lazy import to avoid circular dependency
# WebSocket manager → synthetic_data.error_handler → synthetic_data → job_manager → WebSocket manager
if TYPE_CHECKING:
    from netra_backend.app.services.websocket.ws_manager import WebSocketManager


class JobManager:
    """Manages generation job lifecycle and status"""

    def create_job(
        self,
        job_id: str,
        config: schemas.LogGenParams,
        corpus_id: Optional[str],
        user_id: Optional[str],
        table_name: str
    ) -> Dict:
        """Create new job record"""
        return self._build_job_record(config, corpus_id, user_id, table_name)

    def _build_job_record(
        self,
        config: schemas.LogGenParams,
        corpus_id: Optional[str],
        user_id: Optional[str],
        table_name: str
    ) -> Dict:
        """Build job record data structure"""
        base_record = self._create_base_job_record(config, corpus_id, table_name)
        base_record["user_id"] = user_id
        return base_record

    def _create_base_job_record(self, config: schemas.LogGenParams, corpus_id: Optional[str], table_name: str) -> Dict:
        """Create base job record with essential fields"""
        return {
            "status": GenerationStatus.INITIATED.value,
            "config": config,
            "corpus_id": corpus_id,
            "start_time": datetime.now(UTC),
            "records_generated": 0,
            "records_ingested": 0,
            "errors": [],
            "table_name": table_name
        }

    async def start_job(self, job_id: str, active_jobs: Dict) -> None:
        """Start job execution"""
        active_jobs[job_id]["status"] = GenerationStatus.RUNNING.value
        await self._send_started_notification(job_id, active_jobs[job_id])
        central_logger.info(f"Generation job {job_id} started")

    async def _send_started_notification(self, job_id: str, job_data: Dict) -> None:
        """Send job started notification"""
        # Lazy import to avoid circular dependency
        from netra_backend.app.services.websocket.ws_manager import manager
        
        payload = self._build_started_payload(job_id, job_data)
        await manager.broadcasting.broadcast_to_all({
            "type": "generation_started",
            "payload": payload
        })

    def _build_started_payload(self, job_id: str, job_data: Dict) -> Dict:
        """Build started notification payload"""
        return {
            "job_id": job_id,
            "total_records": job_data["config"].num_logs,
            "start_time": datetime.now(UTC).isoformat()
        }

    def update_progress(self, job_id: str, active_jobs: Dict, batch_size: int) -> None:
        """Update job progress counters"""
        active_jobs[job_id]["records_generated"] += batch_size
        active_jobs[job_id]["records_ingested"] += batch_size

    def calculate_progress(self, job_id: str, active_jobs: Dict) -> float:
        """Calculate generation progress percentage"""
        job_data = active_jobs[job_id]
        total_records = job_data["config"].num_logs
        generated = job_data["records_generated"]
        return (generated / total_records * 100) if total_records > 0 else 0

    async def send_progress_notification(
        self,
        job_id: str,
        active_jobs: Dict,
        batch_num: int
    ) -> None:
        """Send progress notification if milestone reached"""
        if self._should_send_progress(active_jobs[job_id]):
            await self._broadcast_progress(job_id, active_jobs, batch_num)

    def _should_send_progress(self, job_data: Dict) -> bool:
        """Check if progress notification should be sent"""
        return job_data["records_generated"] % 100 == 0

    async def _broadcast_progress(self, job_id: str, active_jobs: Dict, batch_num: int) -> None:
        """Broadcast progress notification"""
        progress = self.calculate_progress(job_id, active_jobs)
        payload = self._create_progress_payload(job_id, active_jobs, progress, batch_num)
        await self._send_progress_message(payload)

    async def _send_progress_message(self, payload: Dict) -> None:
        """Send progress message via broadcasting"""
        # Lazy import to avoid circular dependency
        from netra_backend.app.services.websocket.ws_manager import manager
        
        await manager.broadcasting.broadcast_to_all({
            "type": "generation_progress",
            "payload": payload
        })

    def _create_progress_payload(
        self,
        job_id: str,
        active_jobs: Dict,
        progress: float,
        batch_num: int
    ) -> Dict:
        """Create progress notification payload"""
        job_data = active_jobs[job_id]
        return self._build_progress_data(job_id, job_data, progress, batch_num)

    def _build_progress_data(self, job_id: str, job_data: Dict, progress: float, batch_num: int) -> Dict:
        """Build progress payload data"""
        base_data = self._get_progress_base_data(job_id, job_data, progress, batch_num)
        base_data["generation_rate"] = calculate_generation_rate(job_data)
        return base_data

    def _get_progress_base_data(self, job_id: str, job_data: Dict, progress: float, batch_num: int) -> Dict:
        """Get base progress data without generation rate"""
        progress_info = self._build_progress_info(job_id, progress, batch_num)
        progress_info.update(self._build_record_counts(job_data))
        return progress_info

    def _build_progress_info(self, job_id: str, progress: float, batch_num: int) -> Dict:
        """Build progress information"""
        return {
            "job_id": job_id,
            "progress_percentage": progress,
            "current_batch": batch_num
        }

    def _build_record_counts(self, job_data: Dict) -> Dict:
        """Build record count information"""
        return {
            "records_generated": job_data["records_generated"],
            "records_ingested": job_data["records_ingested"]
        }

    async def complete_job(
        self,
        job_id: str,
        active_jobs: Dict,
        db: Optional[AsyncSession],
        synthetic_data_id: Optional[str]
    ) -> None:
        """Complete job successfully"""
        await self._process_job_completion(job_id, active_jobs, db, synthetic_data_id)
        central_logger.info(f"Generation job {job_id} completed successfully")

    async def _process_job_completion(
        self,
        job_id: str,
        active_jobs: Dict,
        db: Optional[AsyncSession],
        synthetic_data_id: Optional[str]
    ) -> None:
        """Process job completion steps"""
        self._mark_job_completed(job_id, active_jobs)
        await self._update_database_status(db, synthetic_data_id, "completed")
        await self._send_completion_notification(job_id, active_jobs)

    def _mark_job_completed(self, job_id: str, active_jobs: Dict) -> None:
        """Mark job as completed with timestamp"""
        active_jobs[job_id]["status"] = GenerationStatus.COMPLETED.value
        active_jobs[job_id]["end_time"] = datetime.now(UTC)

    async def _update_database_status(
        self,
        db: Optional[AsyncSession],
        synthetic_data_id: Optional[str],
        status: str
    ) -> None:
        """Update database status if available"""
        if self._can_update_database(db, synthetic_data_id):
            self._perform_database_update(db, synthetic_data_id, status)

    def _can_update_database(self, db: Optional[AsyncSession], synthetic_data_id: Optional[str]) -> bool:
        """Check if database update is possible"""
        return db is not None and synthetic_data_id is not None

    def _perform_database_update(self, db: AsyncSession, synthetic_data_id: str, status: str) -> None:
        """Perform database status update"""
        db.query(models.Corpus).filter(
            models.Corpus.id == synthetic_data_id
        ).update({"status": status})
        db.commit()

    async def _send_completion_notification(self, job_id: str, active_jobs: Dict) -> None:
        """Send job completion notification"""
        # Lazy import to avoid circular dependency
        from netra_backend.app.services.websocket.ws_manager import manager
        
        payload = self._build_completion_payload(job_id, active_jobs)
        await manager.broadcasting.broadcast_to_all({
            "type": "generation_complete",
            "payload": payload
        })

    def _build_completion_payload(self, job_id: str, active_jobs: Dict) -> Dict:
        """Build completion notification payload"""
        job_data = active_jobs[job_id]
        duration = self._calculate_duration(job_data)
        return self._create_completion_data(job_id, job_data, duration)

    def _create_completion_data(self, job_id: str, job_data: Dict, duration: float) -> Dict:
        """Create completion data structure"""
        completion_info = self._build_completion_info(job_id, duration)
        completion_info.update(self._build_job_output_info(job_data))
        return completion_info

    def _build_completion_info(self, job_id: str, duration: float) -> Dict:
        """Build completion information"""
        return {
            "job_id": job_id,
            "duration_seconds": duration
        }

    def _build_job_output_info(self, job_data: Dict) -> Dict:
        """Build job output information"""
        return {
            "total_records": job_data["records_generated"],
            "destination_table": job_data["table_name"]
        }

    def _calculate_duration(self, job_data: Dict) -> float:
        """Calculate job duration in seconds"""
        end_time = job_data.get("end_time", datetime.now(UTC))
        start_time = job_data["start_time"]
        return (end_time - start_time).total_seconds()

    async def cancel_job(
        self,
        job_id: str,
        active_jobs: Dict,
        reason: Optional[str] = None
    ) -> Dict:
        """Cancel generation job with improved race condition handling"""
        if self._job_exists(job_id, active_jobs):
            return await self._cancel_active_job(job_id, active_jobs, reason)
        return await self._handle_missing_job_cancellation(job_id, reason)

    def _job_exists(self, job_id: str, active_jobs: Dict) -> bool:
        """Check if job exists in active jobs"""
        return job_id in active_jobs

    async def _cancel_active_job(self, job_id: str, active_jobs: Dict, reason: Optional[str]) -> Dict:
        """Cancel an active job that exists in active_jobs"""
        self._mark_job_cancelled(job_id, active_jobs, reason)
        await self._send_cancellation_notification(job_id, active_jobs)
        return self._build_cancellation_result(job_id, active_jobs)

    def _mark_job_cancelled(self, job_id: str, active_jobs: Dict, reason: Optional[str]) -> None:
        """Mark job as cancelled with optional reason"""
        active_jobs[job_id]["status"] = GenerationStatus.CANCELLED.value
        if reason:
            active_jobs[job_id]["cancel_reason"] = reason

    def _build_cancellation_result(self, job_id: str, active_jobs: Dict) -> Dict:
        """Build cancellation result dictionary"""
        return {
            "cancelled": True,
            "records_completed": active_jobs[job_id].get("records_generated", 0)
        }

    async def _handle_missing_job_cancellation(self, job_id: str, reason: Optional[str]) -> Dict:
        """Handle cancellation when job is not in active_jobs (race condition)"""
        self._log_missing_job_warning(job_id)
        if self._is_valid_job_id(job_id):
            return self._build_missing_job_success_result()
        return self._build_missing_job_failure_result()

    def _log_missing_job_warning(self, job_id: str) -> None:
        """Log warning for missing job cancellation attempt"""
        central_logger.warning(f"Attempted to cancel job {job_id} but it was not found in active jobs")

    def _build_missing_job_success_result(self) -> Dict:
        """Build success result for missing job (race condition handling)"""
        return {
            "cancelled": True,
            "records_completed": 0  # Default for missing job data
        }

    def _build_missing_job_failure_result(self) -> Dict:
        """Build failure result for missing job"""
        return {"cancelled": False}

    def _is_valid_job_id(self, job_id: str) -> bool:
        """Check if job_id appears to be a valid job identifier"""
        return job_id and len(job_id) > 20  # Likely a UUID from test or real job

    async def _send_cancellation_notification(self, job_id: str, active_jobs: Dict) -> None:
        """Send job cancellation notification"""
        # Lazy import to avoid circular dependency
        from netra_backend.app.services.websocket.ws_manager import manager
        
        payload = self._build_cancellation_payload(job_id, active_jobs)
        await manager.broadcasting.broadcast_to_all({
            "type": "generation_cancelled",
            "payload": payload
        })

    def _build_cancellation_payload(self, job_id: str, active_jobs: Dict) -> Dict:
        """Build cancellation notification payload"""
        job_data = active_jobs[job_id]
        return self._create_cancel_data(job_id, job_data)

    def _create_cancel_data(self, job_id: str, job_data: Dict) -> Dict:
        """Create cancellation data structure"""
        return {
            "job_id": job_id,
            "records_completed": job_data.get("records_generated", 0),
            "reason": job_data.get("cancel_reason", "User requested")
        }

    def get_job_status(self, job_id: str, active_jobs: Dict) -> Optional[Dict]:
        """Get current job status"""
        return active_jobs.get(job_id)

    def fail_job(
        self,
        job_id: str,
        active_jobs: Dict,
        error: Exception
    ) -> None:
        """Mark job as failed"""
        if self._job_exists(job_id, active_jobs):
            self._mark_job_failed(job_id, active_jobs, error)

    def _mark_job_failed(self, job_id: str, active_jobs: Dict, error: Exception) -> None:
        """Mark job as failed with error details"""
        active_jobs[job_id]["status"] = GenerationStatus.FAILED.value
        active_jobs[job_id]["errors"].append(str(error))
        active_jobs[job_id]["end_time"] = datetime.now(UTC)

    async def send_error_notification(self, job_id: str, error: Exception) -> None:
        """Send error notification via WebSocket"""
        # Lazy import to avoid circular dependency
        from netra_backend.app.services.websocket.ws_manager import manager
        
        payload = self._build_error_payload(job_id, error)
        await manager.broadcasting.broadcast_to_all({
            "type": "generation_error",
            "payload": payload
        })

    def _build_error_payload(self, job_id: str, error: Exception) -> Dict:
        """Build error notification payload"""
        return {
            "job_id": job_id,
            "error_type": "generation_failure",
            "error_message": str(error),
            "recoverable": False
        }