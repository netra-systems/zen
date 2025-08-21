"""
Synthetic Data Progress Tracking Module

Handles progress tracking and WebSocket communication for 
synthetic data generation operations.
"""

from typing import Any, Dict

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.Generation import GenerationStatus

logger = central_logger.get_logger(__name__)


class SyntheticDataProgressTracker:
    """Handles progress tracking for synthetic data generation"""
    
    def update_progress(self, status: GenerationStatus, current: int, total: int) -> None:
        """Update generation progress"""
        status.records_generated = current
        status.progress_percentage = (current / total) * 100
    
    def should_send_update(self, batch_start: int, batch_size: int) -> bool:
        """Determine if progress update should be sent"""
        return batch_start % (batch_size * 5) == 0
    
    async def handle_progress_update(
        self,
        run_id: str,
        status: GenerationStatus,
        stream_updates: bool,
        batch_start: int,
        batch_size: int
    ) -> None:
        """Handle progress update if needed"""
        if stream_updates and self.should_send_update(batch_start, batch_size):
            await self.send_progress_update(run_id, status)
    
    async def send_progress_update(self, run_id: str, status: GenerationStatus) -> None:
        """Send progress update via WebSocket manager"""
        try:
            from netra_backend.app.services.websocket.ws_manager import (
                manager as ws_manager,
            )
            await self._send_websocket_update(ws_manager, run_id, status)
        except ImportError:
            logger.debug("WebSocket manager not available, logging progress locally")
            self._log_progress_update(status)
    
    async def _send_websocket_update(self, ws_manager, run_id: str, status: GenerationStatus) -> None:
        """Send update via WebSocket manager"""
        message = self.create_progress_message(status)
        await ws_manager.send_message(run_id, message)
    
    def _log_progress_update(self, status: GenerationStatus) -> None:
        """Log progress update locally"""
        logger.info(
            f"Progress: {status.records_generated:,}/{status.total_records:,} "
            f"({status.progress_percentage:.1f}%)"
        )
    
    def create_progress_message(self, status: GenerationStatus) -> Dict[str, Any]:
        """Create progress message for WebSocket"""
        return {
            "type": "synthetic_data_progress",
            "data": self._create_progress_data(status)
        }
    
    def _create_progress_data(self, status: GenerationStatus) -> Dict[str, Any]:
        """Create progress data dictionary"""
        return {
            "status": status.status,
            "records_generated": status.records_generated,
            "total_records": status.total_records,
            "progress_percentage": status.progress_percentage,
            "table_name": status.table_name
        }
    
    def finalize_generation(self, status: GenerationStatus) -> None:
        """Finalize generation status"""
        status.status = "completed"
        status.progress_percentage = 100.0