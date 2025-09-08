"""
Synthetic Data Progress Tracking Module

Handles progress tracking and WebSocket communication for 
synthetic data generation operations.
"""

from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core import get_websocket_manager
from netra_backend.app.schemas.generation import GenerationStatus

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
        batch_size: int,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_context=None
    ) -> None:
        """Handle progress update if needed"""
        if stream_updates and self.should_send_update(batch_start, batch_size):
            await self.send_progress_update(run_id, status, thread_id, user_id, user_context)
    
    async def send_progress_update(self, run_id: str, status: GenerationStatus,
                                  thread_id: Optional[str] = None,
                                  user_id: Optional[str] = None,
                                  user_context=None) -> None:
        """Send progress update via WebSocket manager"""
        try:
            if user_context:
                from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                websocket_manager = create_websocket_manager(user_context)
                await self._send_websocket_update(websocket_manager, run_id, status, thread_id, user_id)
            else:
                logger.debug("WebSocket update not sent - no user context provided")
                self._log_progress_update(status)
        except ImportError:
            logger.debug("WebSocket manager factory not available, logging progress locally")
            self._log_progress_update(status)
        except Exception as e:
            logger.debug(f"Failed to send WebSocket update: {e}")
            self._log_progress_update(status)
    
    async def _send_websocket_update(self, websocket_manager, run_id: str, status: GenerationStatus,
                                    thread_id: Optional[str] = None,
                                    user_id: Optional[str] = None) -> None:
        """Send update via WebSocket manager using appropriate method"""
        message = self.create_progress_message(status)
        
        # Prefer thread-based messaging if thread_id is available
        if thread_id:
            await websocket_manager.send_to_thread(thread_id, message)
        elif user_id and not user_id.startswith("run_"):
            # Only send to user if we have a real user ID (not a run ID)
            await websocket_manager.send_to_user(user_id, message)
        else:
            # Log but don't fail if no valid recipient
            logger.debug(f"No valid recipient for WebSocket message (run_id: {run_id})")
    
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