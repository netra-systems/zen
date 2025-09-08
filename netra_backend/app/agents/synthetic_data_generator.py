"""
Synthetic Data Generator - Main Orchestrator

Coordinates synthetic data generation using modular components
for batch processing, progress tracking, and record creation.
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.synthetic_data_batch_processor import (
    SyntheticDataBatchProcessor,
)
from netra_backend.app.agents.synthetic_data_presets import WorkloadProfile
from netra_backend.app.agents.synthetic_data_progress_tracker import (
    SyntheticDataProgressTracker,
)
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.logging_config import central_logger

# Import consolidated types from single source of truth
from netra_backend.app.schemas.generation import GenerationStatus, SyntheticDataResult

logger = central_logger.get_logger(__name__)


class SyntheticDataGenerator:
    """Main orchestrator for synthetic data generation operations"""
    
    def __init__(self, tool_dispatcher: UnifiedToolDispatcher):
        self.tool_dispatcher = tool_dispatcher
        self.batch_processor = SyntheticDataBatchProcessor(tool_dispatcher)
        self.progress_tracker = SyntheticDataProgressTracker()
    
    async def generate_data(
        self, 
        profile: WorkloadProfile,
        run_id: str,
        stream_updates: bool = True,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> SyntheticDataResult:
        """Generate synthetic data based on profile"""
        status, table_name = self._setup_generation(profile)
        try:
            data = await self._generate_batched_data(
                profile, status, run_id, stream_updates, thread_id, user_id
            )
            return self._create_success_result(
                profile, status, data, table_name
            )
        except Exception as e:
            return self._create_error_result(profile, str(e))
    
    def _setup_generation(self, profile: WorkloadProfile) -> tuple[GenerationStatus, str]:
        """Setup generation status and table name"""
        status = self._create_initial_status(profile)
        table_name = self._generate_table_name(profile)
        status.table_name = table_name
        return status, table_name
    
    def _create_initial_status(self, profile: WorkloadProfile) -> GenerationStatus:
        """Create initial generation status"""
        return GenerationStatus(
            status="generating",
            total_records=profile.volume
        )
    
    def _generate_table_name(self, profile: WorkloadProfile) -> str:
        """Generate unique table name for data"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"synthetic_{profile.workload_type.value}_{timestamp}"
    
    async def _generate_batched_data(
        self,
        profile: WorkloadProfile,
        status: GenerationStatus,
        run_id: str,
        stream_updates: bool,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate data in batches with progress tracking"""
        # Create a UserExecutionContext from the parameters for batch processing
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        context = UserExecutionContext(
            user_id=user_id or "unknown",
            thread_id=thread_id or "unknown", 
            run_id=run_id
        )
        
        batch_size = self.batch_processor.calculate_batch_size(profile.volume)
        generated_data = await self.batch_processor.process_all_batches(
            profile, status, context, stream_updates, batch_size
        )
        self.progress_tracker.finalize_generation(status)
        return generated_data
    
    def _create_success_result(
        self,
        profile: WorkloadProfile,
        status: GenerationStatus,
        data: List[Dict[str, Any]],
        table_name: str
    ) -> SyntheticDataResult:
        """Create successful generation result"""
        return SyntheticDataResult(
            success=True,
            workload_profile=profile,
            generation_status=status,
            sample_data=data[:10],
            metadata=self._create_result_metadata(table_name, data)
        )
    
    def _create_result_metadata(
        self, table_name: str, data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create metadata for successful result"""
        return {
            "table_name": table_name,
            "generation_time_ms": int(time.time() * 1000),
            "checksum": self._calculate_checksum(data)
        }
    
    def _create_error_result(self, profile: WorkloadProfile, error: str) -> SyntheticDataResult:
        """Create error result"""
        return SyntheticDataResult(
            success=False,
            workload_profile=profile,
            generation_status=GenerationStatus(
                status="failed",
                errors=[error]
            )
        )
    
    def _calculate_checksum(self, data: List[Dict[str, Any]]) -> str:
        """Calculate checksum for generated data"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()