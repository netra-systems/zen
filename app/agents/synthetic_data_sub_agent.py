# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CLAUDE.md compliance - Refactor to ≤300 lines, functions ≤8 lines
# Git: anthony-aug-13-2 | modified
# Change: Refactor | Scope: Component | Risk: Low
# Session: claude-md-compliance | Seq: 3
# Review: Pending | Score: 90
# ================================

import time
from typing import Optional, List

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.synthetic_data_presets import (
    WorkloadProfile, DataGenerationType, find_preset_by_name
)
from app.agents.synthetic_data_profile_parser import create_profile_parser
from app.agents.synthetic_data_generator import (
    SyntheticDataGenerator, SyntheticDataResult, GenerationStatus
)
from app.agents.synthetic_data_metrics_handler import SyntheticDataMetricsHandler
from app.agents.synthetic_data_approval_handler import (
    SyntheticDataApprovalHandler, ApprovalFlowOrchestrator,
    ApprovalValidationHelper, ApprovalMessageBuilder
)
from app.agents.synthetic_data_generation_flow import (
    SyntheticDataGenerationFlow, GenerationFlowFactory
)
from app.logging_config import central_logger
from app.llm.observability import log_agent_communication
from app.core.synthetic_data_llm_handler import (
    SyntheticDataLLMHandler, PromptBuilder
)

logger = central_logger.get_logger(__name__)


class SyntheticDataSubAgent(BaseSubAgent):
    """Sub-agent dedicated to synthetic data generation"""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(
            llm_manager, 
            name="SyntheticDataSubAgent", 
            description="Agent specialized in generating synthetic data for workload simulation"
        )
        self.tool_dispatcher = tool_dispatcher
        self.generator = SyntheticDataGenerator(tool_dispatcher)
        self.profile_parser = create_profile_parser()
        self.metrics_handler = SyntheticDataMetricsHandler("SyntheticDataSubAgent")
        self.approval_handler = SyntheticDataApprovalHandler(self._send_update)
        self.approval_orchestrator = ApprovalFlowOrchestrator(
            self.approval_handler,
            ApprovalValidationHelper(),
            ApprovalMessageBuilder()
        )
        self.llm_handler = SyntheticDataLLMHandler(llm_manager, "SyntheticDataSubAgent")
        self.generation_flow = GenerationFlowFactory.create_flow(
            generator=self.generator,
            send_update_callback=self._send_update,
            approval_handler=self._handle_approval_flow
        )

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if conditions are met for synthetic data generation"""
        if self._is_admin_request(state):
            return True
        if self._is_synthetic_request(state):
            return True
        
        self.logger.info(f"Synthetic data generation not required for run_id: {run_id}")
        return False
    
    def _is_admin_request(self, state: DeepAgentState) -> bool:
        """Check if request is from admin mode"""
        triage_result = state.triage_result or {}
        if not isinstance(triage_result, dict):
            return False
        
        category = triage_result.get("category", "")
        is_admin = triage_result.get("is_admin_mode", False)
        return "synthetic" in category.lower() or is_admin
    
    def _is_synthetic_request(self, state: DeepAgentState) -> bool:
        """Check if request explicitly mentions synthetic data"""
        if not state.user_request:
            return False
        request_lower = state.user_request.lower()
        return "synthetic" in request_lower or "generate data" in request_lower

    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute synthetic data generation"""
        log_agent_communication("Supervisor", "SyntheticDataSubAgent", run_id, "execute_request")
        start_time = time.time()
        
        try:
            await self._execute_main_flow(state, run_id, stream_updates, start_time)
            self.metrics_handler.log_successful_execution(run_id)
        except Exception as e:
            await self.metrics_handler.handle_generation_error(
                e, state, run_id, stream_updates, self._send_update
            )
            raise
    
    async def _execute_main_flow(self, state: DeepAgentState, run_id: str, 
                               stream_updates: bool, start_time: float) -> None:
        """Execute the main generation flow using the flow module."""
        workload_profile = await self._determine_workload_profile(state)
        
        approval_handled = await self.approval_orchestrator.execute_approval_flow(
            workload_profile, state, run_id, stream_updates
        )
        
        await self.generation_flow.execute_generation_flow(
            state, run_id, stream_updates, start_time, workload_profile, requires_approval
        )
    
    
    async def _requires_approval(self, profile: WorkloadProfile, state: DeepAgentState) -> bool:
        """Check if user approval is required"""
        return await self._check_approval_requirements(profile, state)
    
    async def _handle_approval_flow(
        self,
        profile: WorkloadProfile,
        state: DeepAgentState,
        run_id: str,
        stream_updates: bool
    ) -> None:
        """Handle approval request flow"""
        return await self._process_approval_workflow(profile, state, run_id, stream_updates)

    async def _process_approval_workflow(
        self, profile: WorkloadProfile, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Process the approval workflow steps."""
        approval_message = self._generate_approval_message(profile)
        approval_result = self._create_approval_result(profile, approval_message)
        state.synthetic_data_result = approval_result.model_dump()
        await self._send_approval_if_needed(stream_updates, run_id, profile, approval_message)
    
    async def _execute_generation(
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
            await self._send_update(run_id, {
                "status": "generating",
                "message": f"🔄 Generating {profile.volume:,} synthetic records...",
                "progress": 0
            })
    
    async def _send_completion_update(
        self, result: SyntheticDataResult, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Send completion update"""
        if not stream_updates:
            return
        
        duration = self._calculate_duration(start_time)
        completion_data = self._build_completion_data(result, duration)
        await self._send_update(run_id, completion_data)
    
    def _calculate_duration(self, start_time: float) -> int:
        """Calculate duration in milliseconds"""
        return int((time.time() - start_time) * 1000)
    
    def _log_completion(self, run_id: str, result: SyntheticDataResult) -> None:
        """Log successful completion"""
        self.logger.info(
            f"Synthetic data generation completed for run_id {run_id}: "
            f"{result.generation_status.records_generated} records generated"
        )
    
    async def _handle_generation_error(
        self, error: Exception, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Handle generation errors"""
        self.logger.error(f"Synthetic data generation failed for run_id {run_id}: {error}")
        error_result = self._create_error_result(error)
        state.synthetic_data_result = error_result.model_dump()
        await self._send_error_update_if_needed(stream_updates, run_id, error)

    async def _determine_workload_profile(self, state: DeepAgentState) -> WorkloadProfile:
        """Determine workload profile from user request"""
        return await self.profile_parser.determine_workload_profile(
            state.user_request, self.llm_manager
        )
    
    
    
    
    async def _call_llm_with_logging(self, prompt: str) -> str:
        """Call LLM with proper logging and heartbeat."""
        correlation_id = self._setup_llm_tracking()
        
        try:
            return await self._execute_llm_call(prompt, correlation_id)
        finally:
            stop_llm_heartbeat(correlation_id)
    
    def _setup_llm_tracking(self) -> str:
        """Setup LLM tracking and heartbeat."""
        correlation_id = generate_llm_correlation_id()
        start_llm_heartbeat(correlation_id, "SyntheticDataSubAgent")
        return correlation_id
    
    async def _execute_llm_call(
        self, 
        prompt: str, 
        correlation_id: str
    ) -> str:
        """Execute LLM call with logging."""
        try:
            return await self._execute_llm_with_logging(prompt, correlation_id)
        except Exception as e:
            self._log_llm_error(correlation_id)
            raise
    
    async def _execute_llm_with_logging(
        self, prompt: str, correlation_id: str
    ) -> str:
        """Execute LLM call with input/output logging."""
        self._log_llm_input(prompt, correlation_id)
        response = await self._get_llm_response(prompt)
        self._log_llm_success(response, correlation_id)
        return response
    
    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM manager"""
        return await self.llm_manager.ask_llm(prompt, llm_config_name='default')
    
    
    
    

    async def _check_approval_requirements(self, profile: WorkloadProfile, state: DeepAgentState) -> bool:
        """Check if user approval is required for this generation"""
        large_volume = self._is_large_volume(profile)
        sensitive_data = self._is_sensitive_data(profile)
        explicit_approval = self._requires_explicit_approval(state)
        return large_volume or sensitive_data or explicit_approval
    
    def _is_large_volume(self, profile: WorkloadProfile) -> bool:
        """Check if volume requires approval"""
        return profile.volume > 50000
    
    def _is_sensitive_data(self, profile: WorkloadProfile) -> bool:
        """Check if data type is sensitive"""
        custom_params = profile.custom_parameters
        return custom_params.get("data_sensitivity") == "high"
    
    def _requires_explicit_approval(self, state: DeepAgentState) -> bool:
        """Check if explicit approval is requested"""
        triage_result = state.triage_result or {}
        if not isinstance(triage_result, dict):
            return False
        return triage_result.get("require_approval", False)

    def _generate_approval_message(self, profile: WorkloadProfile) -> str:
        """Generate user-friendly approval message"""
        workload_type = profile.workload_type.value.replace('_', ' ').title()
        base_info = f"{workload_type}, {profile.volume:,} records"
        timing_info = f"{profile.time_range_days} days, {profile.distribution} distribution"
        return f"📊 Synthetic Data Request: {base_info}, {timing_info}. Approve to proceed or reply 'modify' to adjust."
    
    async def _send_approval_if_needed(
        self, stream_updates: bool, run_id: str, profile: WorkloadProfile, message: str
    ) -> None:
        """Send approval update if streaming enabled."""
        if stream_updates:
            await self._send_approval_update(run_id, profile, message)
    
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
        return f"✅ Successfully generated {records_count:,} synthetic records in {duration}ms"
    
    async def _send_error_update_if_needed(
        self, stream_updates: bool, run_id: str, error: Exception
    ) -> None:
        """Send error update if streaming enabled."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "error",
                "message": f"❌ Synthetic data generation failed: {str(error)}",
                "error": str(error)
            })
    
    
    def _log_llm_input(self, prompt: str, correlation_id: str) -> None:
        """Log LLM input with correlation ID."""
        log_agent_input(
            "SyntheticDataSubAgent", "LLM", len(prompt), correlation_id
        )
    
    def _log_llm_success(self, response: str, correlation_id: str) -> None:
        """Log successful LLM response."""
        log_agent_output(
            "LLM", "SyntheticDataSubAgent", 
            len(response), "success", correlation_id
        )
    
    def _log_llm_error(self, correlation_id: str) -> None:
        """Log LLM error response."""
        log_agent_output(
            "LLM", "SyntheticDataSubAgent", 0, "error", correlation_id
        )
    
    
    def _create_approval_result(self, profile: WorkloadProfile, message: str) -> SyntheticDataResult:
        """Create approval required result"""
        return SyntheticDataResult(
            success=False,
            workload_profile=profile,
            generation_status=GenerationStatus(status="pending_approval"),
            requires_approval=True,
            approval_message=message
        )
    
    async def _send_approval_update(
        self, run_id: str, profile: WorkloadProfile, message: str
    ) -> None:
        """Send approval required update"""
        await self._send_update(run_id, {
            "status": "approval_required",
            "message": message,
            "requires_user_action": True,
            "action_type": "approve_synthetic_data",
            "workload_profile": profile.model_dump()
        })
    
    def _create_error_result(self, error: Exception) -> SyntheticDataResult:
        """Create error result"""
        return SyntheticDataResult(
            success=False,
            workload_profile=WorkloadProfile(workload_type=DataGenerationType.CUSTOM),
            generation_status=GenerationStatus(
                status="failed",
                errors=[str(error)]
            )
        )

    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution"""
        await super().cleanup(state, run_id)
        await self._log_final_metrics(state)
    
    async def _log_final_metrics(self, state: DeepAgentState) -> None:
        """Log final generation metrics."""
        if not self._has_valid_result(state):
            return
        result = state.synthetic_data_result
        metadata = result.get('metadata', {})
        status = result.get('generation_status', {})
        self._log_completion_summary(metadata, status)
    
    def _has_valid_result(self, state: DeepAgentState) -> bool:
        """Check if state has valid synthetic data result."""
        return (hasattr(state, 'synthetic_data_result') and 
                state.synthetic_data_result and 
                isinstance(state.synthetic_data_result, dict))
    
    def _log_completion_summary(self, metadata: dict, status: dict) -> None:
        """Log completion summary with metrics."""
        table_name = metadata.get('table_name')
        records = status.get('records_generated')
        self.logger.info(
            f"Synthetic data generation completed: "
            f"table={table_name}, records={records}"
        )