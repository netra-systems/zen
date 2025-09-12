"""
Synthetic Data Generation Workflow Module

Orchestrates the complete generation workflow including setup,
execution, and finalization of synthetic data generation.
"""

import time
from typing import Optional

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.synthetic_data_generator import (
    GenerationStatus,
    SyntheticDataGenerator,
    SyntheticDataResult,
)
from netra_backend.app.agents.synthetic_data_presets import (
    DataGenerationType,
    WorkloadProfile,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class GenerationExecutor:
    """Handles the core generation execution logic"""
    
    def __init__(self, generator: SyntheticDataGenerator, send_update_callback):
        self.generator = generator
        self.send_update_callback = send_update_callback
    
    async def execute_generation(
        self,
        profile: WorkloadProfile,
        state: DeepAgentState,
        run_id: str,
        stream_updates: bool,
        start_time: float
    ) -> None:
        """Execute the actual data generation"""
        await self._perform_generation_workflow(profile, state, run_id, stream_updates, start_time)

    async def _perform_generation_workflow(
        self, profile: WorkloadProfile, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Perform complete generation workflow."""
        await self._send_generation_update(profile, run_id, stream_updates)
        result = await self._generate_and_store_result(profile, state, run_id, stream_updates)
        await self._finalize_generation(result, run_id, stream_updates, start_time)
    
    async def _send_generation_update(
        self, profile: WorkloadProfile, run_id: str, stream_updates: bool
    ) -> None:
        """Send generation start update"""
        if stream_updates:
            await self.send_update_callback(run_id, {
                "status": "generating",
                "message": f" CYCLE:  Generating {profile.volume:,} synthetic records...",
                "progress": 0
            })
    
    async def _generate_and_store_result(
        self, profile: WorkloadProfile, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> SyntheticDataResult:
        """Generate data and store result in state."""
        result = await self.generator.generate_data(profile, run_id, stream_updates)
        state.synthetic_data_result = result.model_dump()
        return result
    
    async def _finalize_generation(
        self, result: SyntheticDataResult, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Finalize generation with updates and logging."""
        await self._send_completion_update(result, run_id, stream_updates, start_time)
        self._log_completion(run_id, result)
    
    async def _send_completion_update(
        self, result: SyntheticDataResult, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Send completion update"""
        if not stream_updates:
            return
        
        duration = self._calculate_duration(start_time)
        completion_data = self._build_completion_data(result, duration)
        await self.send_update_callback(run_id, completion_data)
    
    def _calculate_duration(self, start_time: float) -> int:
        """Calculate duration in milliseconds"""
        return int((time.time() - start_time) * 1000)
    
    def _log_completion(self, run_id: str, result: SyntheticDataResult) -> None:
        """Log successful completion"""
        logger.info(
            f"Synthetic data generation completed for run_id {run_id}: "
            f"{result.generation_status.records_generated} records generated"
        )
    
    def _build_completion_data(self, result: SyntheticDataResult, duration: int) -> dict:
        """Build completion update data dictionary."""
        records_count = result.generation_status.records_generated
        sample_data = self._get_sample_data(result)
        message = self._format_completion_message(records_count, duration)
        return self._create_completion_dict(message, result, sample_data)
    
    def _create_completion_dict(
        self, message: str, result: SyntheticDataResult, sample_data: Optional[list]
    ) -> dict:
        """Create completion data dictionary."""
        return self._build_completion_data_dict(message, result, sample_data)

    def _build_completion_data_dict(
        self, message: str, result: SyntheticDataResult, sample_data: Optional[list]
    ) -> dict:
        """Build completion data dictionary structure."""
        return {
            "status": "completed",
            "message": message,
            "result": result.model_dump(),
            "sample_data": sample_data
        }
    
    def _get_sample_data(self, result: SyntheticDataResult) -> Optional[list]:
        """Get sample data from result"""
        return result.sample_data[:5] if result.sample_data else None
    
    def _format_completion_message(self, records_count: int, duration: int) -> str:
        """Format completion message"""
        return f" PASS:  Successfully generated {records_count:,} synthetic records in {duration}ms"


class GenerationErrorHandler:
    """Handles generation errors and error results"""
    
    def __init__(self, send_update_callback):
        self.send_update_callback = send_update_callback
    
    def create_error_result(self, error: Exception) -> SyntheticDataResult:
        """Create error result"""
        return SyntheticDataResult(
            success=False,
            workload_profile=WorkloadProfile(workload_type=DataGenerationType.CUSTOM),
            generation_status=GenerationStatus(
                status="failed",
                errors=[str(error)]
            )
        )
    
    async def send_error_update_if_needed(
        self, stream_updates: bool, run_id: str, error: Exception
    ) -> None:
        """Send error update if streaming enabled."""
        if stream_updates:
            await self.send_update_callback(run_id, {
                "status": "error",
                "message": f" FAIL:  Synthetic data generation failed: {str(error)}",
                "error": str(error)
            })