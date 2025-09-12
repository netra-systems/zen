# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CLAUDE.md compliance - Extract metrics and logging logic
# Git: 8-18-25-AM | new
# Change: Create | Scope: Module | Risk: Low
# Session: claude-md-compliance | Seq: 1
# Review: Pending | Score: 95
# ================================

import time
from typing import Any, Dict, Optional

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.synthetic_data_generator import (
    GenerationStatus,
    SyntheticDataResult,
)
from netra_backend.app.agents.synthetic_data_presets import (
    DataGenerationType,
    WorkloadProfile,
)
from netra_backend.app.llm.observability import log_agent_communication
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SyntheticDataMetricsHandler:
    """Handler for synthetic data generation metrics and logging"""
    
    def __init__(self, agent_name: str = "SyntheticDataSubAgent"):
        self.agent_name = agent_name
        self.logger = logger
    
    def log_successful_execution(self, run_id: str) -> None:
        """Log successful execution completion"""
        log_agent_communication(
            self.agent_name, "Supervisor", run_id, "execute_response"
        )
    
    def log_completion(self, run_id: str, result: SyntheticDataResult) -> None:
        """Log successful completion with record count"""
        records = result.generation_status.records_generated
        self.logger.info(
            f"Synthetic data generation completed for run_id {run_id}: "
            f"{records} records generated"
        )
    
    def log_parsing_failure(self, error: Exception) -> None:
        """Log workload profile parsing failure"""
        self.logger.warning(f"Failed to parse workload profile: {error}")
    
    async def handle_generation_error(
        self, 
        error: Exception, 
        state: DeepAgentState, 
        run_id: str, 
        stream_updates: bool,
        send_update_callback
    ) -> None:
        """Handle generation errors with logging and state update"""
        self._log_generation_error(error, run_id)
        error_result = self.create_error_result(error)
        state.synthetic_data_result = error_result.model_dump()
        await self.send_error_update_if_needed(
            stream_updates, run_id, error, send_update_callback
        )
    
    def _log_generation_error(self, error: Exception, run_id: str) -> None:
        """Log generation error with run ID"""
        self.logger.error(
            f"Synthetic data generation failed for run_id {run_id}: {error}"
        )
    
    async def send_error_update_if_needed(
        self, 
        stream_updates: bool, 
        run_id: str, 
        error: Exception,
        send_update_callback
    ) -> None:
        """Send error update if streaming is enabled"""
        if not stream_updates:
            return
        
        error_data = self._build_error_update_data(error)
        await send_update_callback(run_id, error_data)
    
    def _build_error_update_data(self, error: Exception) -> Dict[str, Any]:
        """Build error update data dictionary"""
        return {
            "status": "error",
            "message": f" FAIL:  Synthetic data generation failed: {str(error)}",
            "error": str(error)
        }
    
    def create_error_result(self, error: Exception) -> SyntheticDataResult:
        """Create standardized error result"""
        default_profile = WorkloadProfile(
            workload_type=DataGenerationType.CUSTOM
        )
        error_status = GenerationStatus(
            status="failed", errors=[str(error)]
        )
        return SyntheticDataResult(
            success=False,
            workload_profile=default_profile,
            generation_status=error_status
        )
    
    async def log_final_metrics(self, state: DeepAgentState) -> None:
        """Log final generation metrics from state"""
        if not self.has_valid_result(state):
            return
        
        result = state.synthetic_data_result
        self._extract_and_log_metrics(result)
    
    def _extract_and_log_metrics(self, result: Dict[str, Any]) -> None:
        """Extract and log metrics from result dictionary"""
        metadata = result.get('metadata', {})
        status = result.get('generation_status', {})
        self.log_completion_summary(metadata, status)
    
    def has_valid_result(self, state: DeepAgentState) -> bool:
        """Check if state has valid synthetic data result"""
        return self._has_result_attribute(state) and self._is_valid_result_dict(state)
    
    def _has_result_attribute(self, state: DeepAgentState) -> bool:
        """Check if state has synthetic_data_result attribute"""
        return hasattr(state, 'synthetic_data_result') and state.synthetic_data_result
    
    def _is_valid_result_dict(self, state: DeepAgentState) -> bool:
        """Check if result is a valid dictionary"""
        return isinstance(state.synthetic_data_result, dict)
    
    def log_completion_summary(self, metadata: Dict[str, Any], status: Dict[str, Any]) -> None:
        """Log completion summary with key metrics"""
        table_name = metadata.get('table_name')
        records = status.get('records_generated')
        self._log_summary_message(table_name, records)
    
    def _log_summary_message(self, table_name: Optional[str], records: Optional[int]) -> None:
        """Log formatted summary message"""
        self.logger.info(
            f"Synthetic data generation completed: "
            f"table={table_name}, records={records}"
        )
    
    def calculate_duration_ms(self, start_time: float) -> int:
        """Calculate duration in milliseconds from start time"""
        return int((time.time() - start_time) * 1000)
    
    def build_completion_data(
        self, 
        result: SyntheticDataResult, 
        duration_ms: int
    ) -> Dict[str, Any]:
        """Build completion update data with metrics"""
        records_count = result.generation_status.records_generated
        sample_data = self._get_sample_data(result)
        message = self._format_completion_message(records_count, duration_ms)
        return self._create_completion_dict(message, result, sample_data)
    
    def _get_sample_data(self, result: SyntheticDataResult) -> Optional[list]:
        """Get limited sample data from result"""
        if not result.sample_data:
            return None
        return result.sample_data[:5]
    
    def _format_completion_message(self, records_count: int, duration_ms: int) -> str:
        """Format human-readable completion message"""
        return (
            f" PASS:  Successfully generated {records_count:,} "
            f"synthetic records in {duration_ms}ms"
        )
    
    def _create_completion_dict(
        self, 
        message: str, 
        result: SyntheticDataResult, 
        sample_data: Optional[list]
    ) -> Dict[str, Any]:
        """Create structured completion data dictionary"""
        return {
            "status": "completed",
            "message": message,
            "result": result.model_dump(),
            "sample_data": sample_data
        }
    
    def log_generation_start(self, profile: WorkloadProfile, run_id: str) -> None:
        """Log generation start with profile info"""
        self.logger.info(
            f"Starting synthetic data generation for run_id {run_id}: "
            f"{profile.volume:,} records of type {profile.workload_type.value}"
        )
    
    def log_approval_required(self, profile: WorkloadProfile, run_id: str) -> None:
        """Log when user approval is required"""
        self.logger.info(
            f"User approval required for run_id {run_id}: "
            f"volume={profile.volume:,}, type={profile.workload_type.value}"
        )
    
    def create_metrics_summary(self, result: SyntheticDataResult) -> Dict[str, Any]:
        """Create metrics summary from generation result"""
        status = result.generation_status
        profile = result.workload_profile
        return self._build_metrics_dict(status, profile)
    
    def _build_metrics_dict(
        self, 
        status: GenerationStatus, 
        profile: WorkloadProfile
    ) -> Dict[str, Any]:
        """Build metrics dictionary from status and profile"""
        return {
            "records_generated": status.records_generated,
            "workload_type": profile.workload_type.value,
            "volume_requested": profile.volume,
            "success_rate": self._calculate_success_rate(status),
            "has_errors": len(status.errors) > 0,
            "error_count": len(status.errors)
        }
    
    def _calculate_success_rate(self, status: GenerationStatus) -> float:
        """Calculate success rate from generation status"""
        if status.records_requested == 0:
            return 0.0
        return status.records_generated / status.records_requested
    
    def log_performance_metrics(
        self, 
        duration_ms: int, 
        records_generated: int
    ) -> None:
        """Log performance metrics for generation"""
        if records_generated > 0:
            rate = records_generated / (duration_ms / 1000.0)
            self.logger.info(
                f"Generation performance: {rate:.1f} records/second, "
                f"total_time={duration_ms}ms"
            )