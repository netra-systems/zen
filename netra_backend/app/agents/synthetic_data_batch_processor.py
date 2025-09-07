"""
Synthetic Data Batch Processing Module

Handles batch processing logic for synthetic data generation,
including batch size calculation and progress tracking.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
# DatabaseSessionManager removed - use SSOT database module get_db() instead
from netra_backend.app.agents.synthetic_data_presets import WorkloadProfile
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.generation import GenerationStatus

logger = central_logger.get_logger(__name__)


class SyntheticDataBatchProcessor:
    """Handles batch processing for synthetic data generation"""
    
    def __init__(self, tool_dispatcher: UnifiedToolDispatcher):
        self.tool_dispatcher = tool_dispatcher
        from netra_backend.app.agents.synthetic_data_progress_tracker import (
            SyntheticDataProgressTracker,
        )
        self.progress_tracker = SyntheticDataProgressTracker()
    
    async def process_all_batches(
        self,
        profile: WorkloadProfile,
        status: GenerationStatus,
        context: UserExecutionContext,
        stream_updates: bool,
        batch_size: int
    ) -> List[Dict[str, Any]]:
        """Process all batches for data generation with user context isolation"""
        generated_data = []
        for batch_start in range(0, profile.volume, batch_size):
            await self._process_single_batch(
                profile, status, context, stream_updates, batch_start, 
                batch_size, generated_data
            )
        return generated_data
    
    async def _process_single_batch(
        self,
        profile: WorkloadProfile,
        status: GenerationStatus,
        context: UserExecutionContext,
        stream_updates: bool,
        batch_start: int,
        batch_size: int,
        generated_data: List[Dict[str, Any]]
    ) -> None:
        """Process a single batch and update progress with context isolation"""
        batch_data = await self._generate_batch(
            profile, batch_start, batch_size, context
        )
        generated_data.extend(batch_data)
        self.progress_tracker.update_progress(status, len(generated_data), profile.volume)
        await self.progress_tracker.handle_progress_update(
            context.run_id, status, stream_updates, batch_start, batch_size, 
            context.thread_id, context.user_id
        )
        await asyncio.sleep(0.01)  # Prevent overwhelming
    
    async def _generate_batch(
        self,
        profile: WorkloadProfile,
        start_index: int,
        batch_size: int,
        context: UserExecutionContext
    ) -> List[Dict[str, Any]]:
        """Generate a single batch of data with context isolation"""
        actual_size = self._calculate_actual_batch_size(
            batch_size, profile.volume, start_index
        )
        self._validate_tool_availability()
        return await self._generate_via_tool(
            profile, actual_size, context
        )
    
    def _calculate_actual_batch_size(
        self, batch_size: int, total_volume: int, start_index: int
    ) -> int:
        """Calculate actual batch size based on remaining volume"""
        return min(batch_size, total_volume - start_index)
    
    def _validate_tool_availability(self) -> None:
        """Validate that required tool is available"""
        if not self.tool_dispatcher.has_tool("generate_synthetic_data_batch"):
            raise RuntimeError(
                "generate_synthetic_data_batch tool not available - "
                "real synthetic data generation required for demo"
            )
    
    async def _generate_via_tool(
        self,
        profile: WorkloadProfile,
        batch_size: int,
        context: UserExecutionContext
    ) -> List[Dict[str, Any]]:
        """Generate batch using tool dispatcher with context"""
        result = await self._dispatch_generation_tool(
            profile, batch_size, context
        )
        return result.get("data", [])
    
    async def _dispatch_generation_tool(
        self,
        profile: WorkloadProfile,
        batch_size: int,
        context: UserExecutionContext
    ) -> Dict[str, Any]:
        """Dispatch synthetic data generation tool with context"""
        return await self.tool_dispatcher.dispatch_tool(
            tool_name="generate_synthetic_data_batch",
            parameters=self._create_tool_params(profile, batch_size),
            context=context,  # Use context instead of DeepAgentState
            run_id=context.run_id
        )
    
    def _create_tool_params(self, profile: WorkloadProfile, batch_size: int) -> Dict[str, Any]:
        """Create parameters for tool dispatcher"""
        return self._build_tool_parameter_dict(
            profile, batch_size
        )
    
    def _build_tool_parameter_dict(
        self, profile: WorkloadProfile, batch_size: int
    ) -> Dict[str, Any]:
        """Build tool parameter dictionary"""
        return {
            "workload_type": profile.workload_type.value,
            "batch_size": batch_size,
            "distribution": profile.distribution,
            "noise_level": profile.noise_level,
            "custom_parameters": profile.custom_parameters
        }
    
    def calculate_batch_size(self, total_volume: int) -> int:
        """Calculate optimal batch size"""
        return min(1000, max(10, total_volume // 10))