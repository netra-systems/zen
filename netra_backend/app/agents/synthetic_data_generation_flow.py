# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CLAUDE.md compliance - Extract generation flow logic
# Git: 8-18-25-AM | new file
# Change: Extract | Scope: Module | Risk: Low
# Session: synthetic-data-flow-extraction | Seq: 1
# Review: Pending | Score: 95
# ================================

import time
from typing import Any, Callable, Dict, Optional

from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
# DatabaseSessionManager removed - use SSOT database module get_db() instead
from netra_backend.app.agents.synthetic_data_generator import (
    SyntheticDataGenerator,
    SyntheticDataResult,
)
from netra_backend.app.agents.synthetic_data_presets import WorkloadProfile
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SyntheticDataGenerationFlow:
    """Handles the synthetic data generation flow logic"""
    
    def __init__(
        self,
        generator: SyntheticDataGenerator,
        send_update_callback: Callable[[str, Dict[str, Any]], None],
        approval_handler: Optional[Callable] = None
    ):
        self.generator = generator
        self._send_update = send_update_callback
        self._handle_approval = approval_handler
    
    async def execute_generation_flow(
        self, 
        context: UserExecutionContext, 
        stream_updates: bool, 
        start_time: float,
        workload_profile: WorkloadProfile,
        requires_approval: bool = False
    ) -> None:
        """Execute the full generation flow with UserExecutionContext."""
        await self._send_initial_update(context.run_id, stream_updates)
        
        if requires_approval and self._handle_approval:
            await self._handle_approval(workload_profile, context, stream_updates)
            return
        
        await self._execute_generation(workload_profile, context, stream_updates, start_time)
    
    async def _send_initial_update(self, run_id: str, stream_updates: bool) -> None:
        """Send initial status update"""
        if not stream_updates:
            return
        
        await self._send_update(run_id, {
            "status": "starting",
            "message": "🎲 Initializing synthetic data generation...",
            "agent": "SyntheticDataSubAgent"
        })
    
    async def _execute_generation(
        self,
        profile: WorkloadProfile,
        context: UserExecutionContext,
        stream_updates: bool,
        start_time: float
    ) -> None:
        """Execute the actual data generation with context isolation"""
        await self._send_generation_update(profile, context.run_id, stream_updates)
        result = await self._generate_and_store_result(profile, context, stream_updates)
        await self._finalize_generation(result, context.run_id, stream_updates, start_time)
    
    async def _send_generation_update(
        self, profile: WorkloadProfile, run_id: str, stream_updates: bool
    ) -> None:
        """Send generation start update"""
        if not stream_updates:
            return
        
        await self._send_update(run_id, {
            "status": "generating",
            "message": f"🔄 Generating {profile.volume:,} synthetic records...",
            "progress": 0
        })
    
    async def _generate_and_store_result(
        self, profile: WorkloadProfile, context: UserExecutionContext, stream_updates: bool
    ) -> SyntheticDataResult:
        """Generate data and store result with proper user isolation."""
        result = await self.generator.generate_data(
            profile, context.run_id, stream_updates, 
            thread_id=context.thread_id, user_id=context.user_id
        )
        # Store result in context metadata instead of global state
        context.metadata['synthetic_data_result'] = result.model_dump()
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
        await self._send_update(run_id, completion_data)
    
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
        return {
            "status": "completed",
            "message": message,
            "result": result.model_dump(),
            "sample_data": sample_data
        }
    
    def _get_sample_data(self, result: SyntheticDataResult) -> Optional[list]:
        """Get sample data from result"""
        if not result.sample_data:
            return None
        return result.sample_data[:5]
    
    def _format_completion_message(self, records_count: int, duration: int) -> str:
        """Format completion message"""
        return f"✅ Successfully generated {records_count:,} synthetic records in {duration}ms"
    
    def _calculate_duration(self, start_time: float) -> int:
        """Calculate duration in milliseconds"""
        current_time = time.time()
        duration_seconds = current_time - start_time
        return int(duration_seconds * 1000)
    
    def _log_completion(self, run_id: str, result: SyntheticDataResult) -> None:
        """Log successful completion"""
        records_generated = result.generation_status.records_generated
        logger.info(
            f"Synthetic data generation completed for run_id {run_id}: "
            f"{records_generated} records generated"
        )


class GenerationFlowFactory:
    """Factory for creating generation flow instances"""
    
    @staticmethod
    def create_flow(
        generator: SyntheticDataGenerator,
        send_update_callback: Callable[[str, Dict[str, Any]], None],
        approval_handler: Optional[Callable] = None
    ) -> SyntheticDataGenerationFlow:
        """Create a new generation flow instance with UserExecutionContext support"""
        return SyntheticDataGenerationFlow(
            generator=generator,
            send_update_callback=send_update_callback,
            approval_handler=approval_handler
        )
    
    @staticmethod
    def create_basic_flow(
        generator: SyntheticDataGenerator,
        send_update_callback: Callable[[str, Dict[str, Any]], None]
    ) -> SyntheticDataGenerationFlow:
        """Create a basic generation flow without approval handling"""
        return SyntheticDataGenerationFlow(
            generator=generator,
            send_update_callback=send_update_callback,
            approval_handler=None
        )