"""
Synthetic Data Messaging Module

Handles all messaging, updates, and communication for synthetic data operations,
including progress updates, completion notifications, and error messages.
"""

from typing import Any, Callable, Dict, Optional

from netra_backend.app.agents.synthetic_data_presets import WorkloadProfile
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class UpdateSender:
    """Handles sending updates during synthetic data operations"""
    
    def __init__(self, send_update_callback: Callable):
        self.send_update_callback = send_update_callback
    
    async def send_generation_start(
        self, profile: WorkloadProfile, run_id: str, stream_updates: bool
    ) -> None:
        """Send generation start update"""
        if stream_updates:
            await self.send_update_callback(run_id, {
                "status": "generating",
                "message": f" CYCLE:  Generating {profile.volume:,} synthetic records...",
                "progress": 0
            })
    
    async def send_completion_update(
        self, run_id: str, completion_data: Dict[str, Any], stream_updates: bool
    ) -> None:
        """Send completion update if streaming enabled"""
        if stream_updates:
            await self.send_update_callback(run_id, completion_data)
    
    async def send_error_update(
        self, run_id: str, error: Exception, stream_updates: bool
    ) -> None:
        """Send error update if streaming enabled"""
        if stream_updates:
            await self.send_update_callback(run_id, {
                "status": "error",
                "message": f" FAIL:  Synthetic data generation failed: {str(error)}",
                "error": str(error)
            })
    
    async def send_approval_update(
        self, run_id: str, profile: WorkloadProfile, message: str
    ) -> None:
        """Send approval required update"""
        await self.send_update_callback(run_id, {
            "status": "approval_required",
            "message": message,
            "requires_user_action": True,
            "action_type": "approve_synthetic_data",
            "workload_profile": profile.model_dump()
        })


class MessageFormatter:
    """Formats various messages for synthetic data operations"""
    
    @staticmethod
    def format_approval_message(profile: WorkloadProfile) -> str:
        """Generate user-friendly approval message"""
        workload_type = profile.workload_type.value.replace('_', ' ').title()
        base_info = f"{workload_type}, {profile.volume:,} records"
        timing_info = f"{profile.time_range_days} days, {profile.distribution} distribution"
        return f" CHART:  Synthetic Data Request: {base_info}, {timing_info}. Approve to proceed or reply 'modify' to adjust."
    
    @staticmethod
    def format_completion_message(records_count: int, duration: int) -> str:
        """Format completion message"""
        return f" PASS:  Successfully generated {records_count:,} synthetic records in {duration}ms"
    
    @staticmethod
    def format_generation_start_message(volume: int) -> str:
        """Format generation start message"""
        return f" CYCLE:  Generating {volume:,} synthetic records..."
    
    @staticmethod
    def format_error_message(error: Exception) -> str:
        """Format error message"""
        return f" FAIL:  Synthetic data generation failed: {str(error)}"


class CompletionDataBuilder:
    """Builds completion data structures for updates"""
    
    @staticmethod
    def build_completion_data(
        message: str, 
        result: Any, 
        sample_data: Optional[list] = None
    ) -> Dict[str, Any]:
        """Build completion data dictionary structure."""
        return {
            "status": "completed",
            "message": message,
            "result": result.model_dump() if hasattr(result, 'model_dump') else result,
            "sample_data": sample_data
        }
    
    @staticmethod
    def get_sample_data(result: Any, limit: int = 5) -> Optional[list]:
        """Get sample data from result with specified limit"""
        if hasattr(result, 'sample_data') and result.sample_data:
            return result.sample_data[:limit]
        return None


class CommunicationCoordinator:
    """Coordinates all communication aspects of synthetic data operations"""
    
    def __init__(self, send_update_callback: Callable):
        self.update_sender = UpdateSender(send_update_callback)
        self.message_formatter = MessageFormatter()
        self.completion_builder = CompletionDataBuilder()
    
    async def send_formatted_approval(
        self, run_id: str, profile: WorkloadProfile, stream_updates: bool
    ) -> None:
        """Send formatted approval update"""
        if stream_updates:
            message = self.message_formatter.format_approval_message(profile)
            await self.update_sender.send_approval_update(run_id, profile, message)
    
    async def send_formatted_completion(
        self, run_id: str, result: Any, duration: int, stream_updates: bool
    ) -> None:
        """Send formatted completion update"""
        if stream_updates:
            records_count = getattr(result.generation_status, 'records_generated', 0)
            message = self.message_formatter.format_completion_message(records_count, duration)
            sample_data = self.completion_builder.get_sample_data(result)
            completion_data = self.completion_builder.build_completion_data(message, result, sample_data)
            await self.update_sender.send_completion_update(run_id, completion_data, True)