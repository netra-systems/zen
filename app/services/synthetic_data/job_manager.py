"""
Job Management Module - Handles job lifecycle and status tracking
"""

from datetime import datetime, UTC
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app import schemas
from app.db import models_postgres as models
from app.ws_manager import manager
from app.logging_config import central_logger

from .enums import GenerationStatus
from .metrics import calculate_generation_rate


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
        return {
            "status": GenerationStatus.INITIATED.value,
            "config": config,
            "corpus_id": corpus_id,
            "start_time": datetime.now(UTC),
            "records_generated": 0,
            "records_ingested": 0,
            "errors": [],
            "table_name": table_name,
            "user_id": user_id
        }

    async def start_job(self, job_id: str, active_jobs: Dict) -> None:
        """Start job execution"""
        active_jobs[job_id]["status"] = GenerationStatus.RUNNING.value
        await self._send_started_notification(job_id, active_jobs[job_id])
        central_logger.info(f"Generation job {job_id} started")

    async def _send_started_notification(self, job_id: str, job_data: Dict) -> None:
        """Send job started notification"""
        await manager.broadcasting.broadcast_to_all({
            "type": "generation:started",
            "payload": {
                "job_id": job_id,
                "total_records": job_data["config"].num_logs,
                "start_time": datetime.now(UTC).isoformat()
            }
        })

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
        job_data = active_jobs[job_id]
        if job_data["records_generated"] % 100 == 0:
            progress = self.calculate_progress(job_id, active_jobs)
            payload = self._create_progress_payload(job_id, active_jobs, progress, batch_num)
            await manager.broadcasting.broadcast_to_all({
                "type": "generation:progress",
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
        return {
            "job_id": job_id,
            "progress_percentage": progress,
            "records_generated": job_data["records_generated"],
            "records_ingested": job_data["records_ingested"],
            "current_batch": batch_num,
            "generation_rate": calculate_generation_rate(job_data)
        }

    async def complete_job(
        self,
        job_id: str,
        active_jobs: Dict,
        db: Optional[Session],
        synthetic_data_id: Optional[str]
    ) -> None:
        """Complete job successfully"""
        self._mark_job_completed(job_id, active_jobs)
        await self._update_database_status(db, synthetic_data_id, "completed")
        await self._send_completion_notification(job_id, active_jobs)
        central_logger.info(f"Generation job {job_id} completed successfully")

    def _mark_job_completed(self, job_id: str, active_jobs: Dict) -> None:
        """Mark job as completed with timestamp"""
        active_jobs[job_id]["status"] = GenerationStatus.COMPLETED.value
        active_jobs[job_id]["end_time"] = datetime.now(UTC)

    async def _update_database_status(
        self,
        db: Optional[Session],
        synthetic_data_id: Optional[str],
        status: str
    ) -> None:
        """Update database status if available"""
        if db and synthetic_data_id:
            db.query(models.Corpus).filter(
                models.Corpus.id == synthetic_data_id
            ).update({"status": status})
            db.commit()

    async def _send_completion_notification(self, job_id: str, active_jobs: Dict) -> None:
        """Send job completion notification"""
        job_data = active_jobs[job_id]
        duration = self._calculate_duration(job_data)
        
        await manager.broadcasting.broadcast_to_all({
            "type": "generation:complete",
            "payload": {
                "job_id": job_id,
                "total_records": job_data["records_generated"],
                "duration_seconds": duration,
                "destination_table": job_data["table_name"]
            }
        })

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
        """Cancel generation job"""
        if job_id in active_jobs:
            active_jobs[job_id]["status"] = GenerationStatus.CANCELLED.value
            if reason:
                active_jobs[job_id]["cancel_reason"] = reason
            
            await self._send_cancellation_notification(job_id, active_jobs)
            return {
                "cancelled": True,
                "records_completed": active_jobs[job_id].get("records_generated", 0)
            }
        return {"cancelled": False}

    async def _send_cancellation_notification(self, job_id: str, active_jobs: Dict) -> None:
        """Send job cancellation notification"""
        job_data = active_jobs[job_id]
        await manager.broadcasting.broadcast_to_all({
            "type": "generation:cancelled",
            "payload": {
                "job_id": job_id,
                "records_completed": job_data.get("records_generated", 0),
                "reason": job_data.get("cancel_reason", "User requested")
            }
        })

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
        if job_id in active_jobs:
            active_jobs[job_id]["status"] = GenerationStatus.FAILED.value
            active_jobs[job_id]["errors"].append(str(error))
            active_jobs[job_id]["end_time"] = datetime.now(UTC)

    async def send_error_notification(self, job_id: str, error: Exception) -> None:
        """Send error notification via WebSocket"""
        await manager.broadcasting.broadcast_to_all({
            "type": "generation:error",
            "payload": {
                "job_id": job_id,
                "error_type": "generation_failure",
                "error_message": str(error),
                "recoverable": False
            }
        })