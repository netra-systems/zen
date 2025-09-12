"""
Synthetic Data Approval Flow Module

Handles all approval-related workflows for synthetic data generation,
including approval requirements checking and user interaction flows.
"""

from typing import Optional

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.synthetic_data_generator import (
    GenerationStatus,
    SyntheticDataResult,
)
from netra_backend.app.agents.synthetic_data_presets import WorkloadProfile
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ApprovalRequirements:
    """Checks approval requirements for synthetic data generation"""
    
    @staticmethod
    def check_approval_requirements(profile: WorkloadProfile, state: DeepAgentState) -> bool:
        """Check if user approval is required for this generation"""
        large_volume = ApprovalRequirements._is_large_volume(profile)
        sensitive_data = ApprovalRequirements._is_sensitive_data(profile)
        explicit_approval = ApprovalRequirements._requires_explicit_approval(state)
        return large_volume or sensitive_data or explicit_approval
    
    @staticmethod
    def _is_large_volume(profile: WorkloadProfile) -> bool:
        """Check if volume requires approval"""
        return profile.volume > 50000
    
    @staticmethod
    def _is_sensitive_data(profile: WorkloadProfile) -> bool:
        """Check if data type is sensitive"""
        custom_params = profile.custom_parameters
        return custom_params.get("data_sensitivity") == "high"
    
    @staticmethod
    def _requires_explicit_approval(state: DeepAgentState) -> bool:
        """Check if explicit approval is requested"""
        triage_result = state.triage_result or {}
        if not isinstance(triage_result, dict):
            return False
        return triage_result.get("require_approval", False)


class ApprovalMessageBuilder:
    """Builds user-friendly approval messages"""
    
    @staticmethod
    def generate_approval_message(profile: WorkloadProfile) -> str:
        """Generate user-friendly approval message"""
        workload_type = profile.workload_type.value.replace('_', ' ').title()
        base_info = f"{workload_type}, {profile.volume:,} records"
        timing_info = f"{profile.time_range_days} days, {profile.distribution} distribution"
        return f" CHART:  Synthetic Data Request: {base_info}, {timing_info}. Approve to proceed or reply 'modify' to adjust."


class ApprovalResultBuilder:
    """Creates approval-related results"""
    
    @staticmethod
    def create_approval_result(profile: WorkloadProfile, message: str) -> SyntheticDataResult:
        """Create approval required result"""
        return SyntheticDataResult(
            success=False,
            workload_profile=profile,
            generation_status=GenerationStatus(status="pending_approval"),
            requires_approval=True,
            approval_message=message
        )


class ApprovalWorkflow:
    """Orchestrates approval workflow processes"""
    
    def __init__(self, send_update_callback):
        self.send_update_callback = send_update_callback
        self.requirements = ApprovalRequirements()
        self.message_builder = ApprovalMessageBuilder()
        self.result_builder = ApprovalResultBuilder()
    
    async def process_approval_workflow(
        self, profile: WorkloadProfile, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Process the approval workflow steps."""
        approval_message = self.message_builder.generate_approval_message(profile)
        approval_result = self.result_builder.create_approval_result(profile, approval_message)
        state.synthetic_data_result = approval_result.model_dump()
        await self._send_approval_if_needed(stream_updates, run_id, profile, approval_message)
    
    async def _send_approval_if_needed(
        self, stream_updates: bool, run_id: str, profile: WorkloadProfile, message: str
    ) -> None:
        """Send approval update if streaming enabled."""
        if stream_updates:
            await self._send_approval_update(run_id, profile, message)
    
    async def _send_approval_update(
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