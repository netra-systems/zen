"""Synthetic Data Sub-Agent Workflow Module

Generation workflow orchestration for ModernSyntheticDataSubAgent.
Handles approval workflows, direct generation, and result formatting.

Business Value: Streamlines synthetic data generation workflows.
BVJ: Growth & Enterprise | Process Efficiency | +25% throughput improvement
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.synthetic_data_generator import SyntheticDataResult
from netra_backend.app.agents.synthetic_data_presets import WorkloadProfile
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.serialization.unified_json_handler import safe_json_dumps

logger = central_logger.get_logger(__name__)


@dataclass
class SyntheticDataContext:
    """Extended context for synthetic data operations."""
    workload_profile: Optional[WorkloadProfile] = None
    requires_approval: bool = False
    generation_started: bool = False
    approval_requested: bool = False


class SyntheticDataWorkflowOrchestrator:
    """Orchestrator for synthetic data generation workflows."""
    
    def __init__(self, agent_instance):
        """Initialize orchestrator with agent reference."""
        self.agent = agent_instance
        self.logger = logger
    
    async def execute_generation_workflow(self, context: ExecutionContext,
                                        synthetic_context: SyntheticDataContext) -> SyntheticDataResult:
        """Execute complete generation workflow."""
        workload_profile = await self._determine_workload_profile(context.state)
        synthetic_context.workload_profile = workload_profile
        
        if await self._requires_approval(workload_profile, context.state):
            return await self._handle_approval_workflow(context, synthetic_context)
        
        return await self._execute_direct_generation(context, synthetic_context)
    
    async def _determine_workload_profile(self, state: DeepAgentState) -> WorkloadProfile:
        """Determine workload profile from user request."""
        return await self.agent.profile_parser.determine_workload_profile(
            state.user_request, self.agent.llm_manager
        )
    
    async def _requires_approval(self, profile: WorkloadProfile, state: DeepAgentState) -> bool:
        """Check if user approval is required for generation."""
        large_volume = profile.volume > 50000
        sensitive_data = self._is_sensitive_data_type(profile)
        explicit_approval = self._requires_explicit_approval(state)
        return large_volume or sensitive_data or explicit_approval
    
    def _is_sensitive_data_type(self, profile: WorkloadProfile) -> bool:
        """Check if profile contains sensitive data types."""
        custom_params = profile.custom_parameters
        return custom_params.get("data_sensitivity") == "high"
    
    def _requires_explicit_approval(self, state: DeepAgentState) -> bool:
        """Check if explicit approval is requested in state."""
        triage_result = state.triage_result or {}
        return triage_result.get("require_approval", False)
    
    async def _handle_approval_workflow(self, context: ExecutionContext,
                                      synthetic_context: SyntheticDataContext) -> SyntheticDataResult:
        """Handle approval workflow for sensitive operations."""
        synthetic_context.requires_approval = True
        synthetic_context.approval_requested = True
        
        approval_message = self._generate_approval_message(synthetic_context.workload_profile)
        result = self._create_approval_result(synthetic_context.workload_profile, approval_message)
        await self._send_approval_update(context, approval_message)
        
        return result
    
    async def _execute_direct_generation(self, context: ExecutionContext,
                                       synthetic_context: SyntheticDataContext) -> SyntheticDataResult:
        """Execute direct data generation without approval."""
        synthetic_context.generation_started = True
        await self.agent.send_status_update(context, "generating", "Starting data generation...")
        
        result = await self.agent.generator.generate_data(
            synthetic_context.workload_profile, context.run_id, context.stream_updates,
            context.thread_id, context.user_id
        )
        context.state.synthetic_data_result = safe_json_dumps(result)
        
        return result
    
    def _generate_approval_message(self, profile: WorkloadProfile) -> str:
        """Generate approval message for user review."""
        workload_type = profile.workload_type.value.replace('_', ' ').title()
        base_info = f"{workload_type}, {profile.volume:,} records"
        timing_info = f"{profile.time_range_days} days, {profile.distribution} distribution"
        return f" CHART:  Synthetic Data Request: {base_info}, {timing_info}. Approve to proceed."
    
    def _create_approval_result(self, profile: WorkloadProfile, message: str) -> SyntheticDataResult:
        """Create result indicating approval required."""
        from netra_backend.app.agents.synthetic_data_generator import GenerationStatus
        return SyntheticDataResult(
            success=False,
            workload_profile=profile,
            generation_status=GenerationStatus(status="pending_approval"),
            requires_approval=True,
            approval_message=message
        )
    
    async def _send_approval_update(self, context: ExecutionContext, message: str) -> None:
        """Send approval required update via WebSocket."""
        await self.agent.send_status_update(context, "approval_required", message)
    
    def format_execution_result(self, result: SyntheticDataResult) -> Dict[str, Any]:
        """Format SyntheticDataResult for standard execution result."""
        return {
            "success": result.success,
            "workload_profile": safe_json_dumps(result.workload_profile) if result.workload_profile else None,
            "generation_status": safe_json_dumps(result.generation_status) if result.generation_status else None,
            "requires_approval": result.requires_approval,
            "sample_data": result.sample_data[:5] if result.sample_data else None
        }
    
    async def handle_core_logic_error(self, context: ExecutionContext, error: Exception) -> Dict[str, Any]:
        """Handle errors in core logic execution."""
        logger.error(f"Core logic error in {context.agent_name}: {error}")
        return {
            "success": False,
            "error": str(error),
            "error_type": error.__class__.__name__
        }