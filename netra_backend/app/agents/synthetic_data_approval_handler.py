# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Extract approval flow logic from SyntheticDataSubAgent
# Git: 8-18-25-AM | created
# Change: Extract | Scope: Module | Risk: Low
# Session: approval-handler-extraction | Seq: 1
# Review: Pending | Score: 95
# ================================

from typing import Any, Awaitable, Callable, Dict, Optional

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.synthetic_data_generator import (
    GenerationStatus,
    SyntheticDataResult,
)
from netra_backend.app.agents.synthetic_data_presets import WorkloadProfile
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SyntheticDataApprovalHandler:
    """Handler for synthetic data generation approval flow"""
    
    def __init__(self, send_update_callback: Callable[[str, Dict[str, Any]], Awaitable[None]]):
        """Initialize with callback for sending updates"""
        self.send_update = send_update_callback
    
    async def requires_approval(
        self, profile: WorkloadProfile, state: DeepAgentState
    ) -> bool:
        """Check if user approval is required"""
        return await self.check_approval_requirements(profile, state)
    
    async def handle_approval_flow(
        self,
        profile: WorkloadProfile,
        state: DeepAgentState,
        run_id: str,
        stream_updates: bool
    ) -> None:
        """Handle approval request flow"""
        approval_message = self.generate_approval_message(profile)
        approval_result = self.create_approval_result(profile, approval_message)
        
        state.synthetic_data_result = approval_result.model_dump()
        await self.send_approval_if_needed(
            stream_updates, run_id, profile, approval_message
        )
    
    async def check_approval_requirements(
        self, profile: WorkloadProfile, state: DeepAgentState
    ) -> bool:
        """Check if user approval is required for this generation"""
        large_volume = self.is_large_volume(profile)
        sensitive_data = self.is_sensitive_data(profile)
        explicit_approval = self.requires_explicit_approval(state)
        return large_volume or sensitive_data or explicit_approval
    
    def is_large_volume(self, profile: WorkloadProfile) -> bool:
        """Check if volume requires approval"""
        return profile.volume > 50000
    
    def is_sensitive_data(self, profile: WorkloadProfile) -> bool:
        """Check if data type is sensitive"""
        custom_params = profile.custom_parameters
        return custom_params.get("data_sensitivity") == "high"
    
    def requires_explicit_approval(self, state: DeepAgentState) -> bool:
        """Check if explicit approval is requested"""
        triage_result = state.triage_result or {}
        if not isinstance(triage_result, dict):
            return False
        return triage_result.get("require_approval", False)
    
    def generate_approval_message(self, profile: WorkloadProfile) -> str:
        """Generate user-friendly approval message"""
        workload_type = self._format_workload_type(profile.workload_type.value)
        base_info = f"{workload_type}, {profile.volume:,} records"
        timing_info = self._format_timing_info(profile)
        approval_prompt = "Approve to proceed or reply 'modify' to adjust."
        return f" CHART:  Synthetic Data Request: {base_info}, {timing_info}. {approval_prompt}"
    
    def _format_workload_type(self, workload_type: str) -> str:
        """Format workload type for display"""
        return workload_type.replace('_', ' ').title()
    
    def _format_timing_info(self, profile: WorkloadProfile) -> str:
        """Format timing information for display"""
        return f"{profile.time_range_days} days, {profile.distribution} distribution"
    
    async def send_approval_if_needed(
        self, 
        stream_updates: bool, 
        run_id: str, 
        profile: WorkloadProfile, 
        message: str
    ) -> None:
        """Send approval update if streaming enabled"""
        if stream_updates:
            await self.send_approval_update(run_id, profile, message)
    
    def create_approval_result(
        self, profile: WorkloadProfile, message: str
    ) -> SyntheticDataResult:
        """Create approval required result"""
        return SyntheticDataResult(
            success=False,
            workload_profile=profile,
            generation_status=GenerationStatus(status="pending_approval"),
            requires_approval=True,
            approval_message=message
        )
    
    async def send_approval_update(
        self, run_id: str, profile: WorkloadProfile, message: str
    ) -> None:
        """Send approval required update"""
        update_data = self._build_approval_update_data(message, profile)
        await self.send_update(run_id, update_data)
    
    def _build_approval_update_data(
        self, message: str, profile: WorkloadProfile
    ) -> Dict[str, Any]:
        """Build approval update data dictionary"""
        return {
            "status": "approval_required",
            "message": message,
            "requires_user_action": True,
            "action_type": "approve_synthetic_data",
            "workload_profile": profile.model_dump()
        }


class ApprovalValidationHelper:
    """Helper class for approval validation logic"""
    
    @staticmethod
    def validate_approval_state(state: DeepAgentState) -> bool:
        """Validate that state is ready for approval checking"""
        return isinstance(state, DeepAgentState)
    
    @staticmethod
    def validate_profile(profile: WorkloadProfile) -> bool:
        """Validate workload profile for approval"""
        return isinstance(profile, WorkloadProfile) and profile.volume > 0
    
    @staticmethod
    def extract_sensitivity_level(profile: WorkloadProfile) -> str:
        """Extract data sensitivity level from profile"""
        custom_params = profile.custom_parameters or {}
        return custom_params.get("data_sensitivity", "low")
    
    @staticmethod
    def extract_approval_flag(state: DeepAgentState) -> bool:
        """Extract approval requirement flag from state"""
        triage_result = state.triage_result or {}
        if not isinstance(triage_result, dict):
            return False
        return triage_result.get("require_approval", False)
    
    @staticmethod
    def calculate_risk_score(profile: WorkloadProfile) -> float:
        """Calculate risk score for approval decision"""
        base_score = min(profile.volume / 100000, 1.0)
        sensitivity_multiplier = ApprovalValidationHelper._get_sensitivity_multiplier(profile)
        return base_score * sensitivity_multiplier
    
    @staticmethod
    def _get_sensitivity_multiplier(profile: WorkloadProfile) -> float:
        """Get sensitivity multiplier for risk calculation"""
        sensitivity = ApprovalValidationHelper.extract_sensitivity_level(profile)
        multipliers = {"low": 1.0, "medium": 1.5, "high": 2.0}
        return multipliers.get(sensitivity, 1.0)


class ApprovalMessageBuilder:
    """Builder for approval messages"""
    
    @staticmethod
    def build_standard_message(profile: WorkloadProfile) -> str:
        """Build standard approval message"""
        components = ApprovalMessageBuilder._extract_message_components(profile)
        return ApprovalMessageBuilder._format_standard_message(components)
    
    @staticmethod
    def build_high_risk_message(profile: WorkloadProfile) -> str:
        """Build high-risk approval message"""
        base_message = ApprovalMessageBuilder.build_standard_message(profile)
        risk_warning = " WARNING: [U+FE0F] HIGH RISK: Large volume and/or sensitive data detected."
        return f"{risk_warning} {base_message}"
    
    @staticmethod
    def _extract_message_components(profile: WorkloadProfile) -> Dict[str, str]:
        """Extract components for message building"""
        return {
            "workload_type": profile.workload_type.value.replace('_', ' ').title(),
            "volume": f"{profile.volume:,}",
            "days": str(profile.time_range_days),
            "distribution": profile.distribution
        }
    
    @staticmethod
    def _format_standard_message(components: Dict[str, str]) -> str:
        """Format standard message from components"""
        header = f" CHART:  Synthetic Data Request: {components['workload_type']}"
        details = f"{components['volume']} records, {components['days']} days"
        distribution = f"{components['distribution']} distribution"
        prompt = "Approve to proceed or reply 'modify' to adjust."
        return f"{header}, {details}, {distribution}. {prompt}"


class ApprovalFlowOrchestrator:
    """Orchestrator for the complete approval flow"""
    
    def __init__(
        self, 
        handler: SyntheticDataApprovalHandler,
        validator: ApprovalValidationHelper,
        message_builder: ApprovalMessageBuilder
    ):
        """Initialize with components"""
        self.handler = handler
        self.validator = validator
        self.message_builder = message_builder
    
    async def execute_approval_flow(
        self,
        profile: WorkloadProfile,
        state: DeepAgentState,
        run_id: str,
        stream_updates: bool
    ) -> bool:
        """Execute complete approval flow, return True if handled"""
        if not self._validate_flow_prerequisites(profile, state):
            return False
        
        if not await self.handler.requires_approval(profile, state):
            return False
        
        await self.handler.handle_approval_flow(profile, state, run_id, stream_updates)
        return True
    
    def _validate_flow_prerequisites(
        self, profile: WorkloadProfile, state: DeepAgentState
    ) -> bool:
        """Validate prerequisites for approval flow"""
        profile_valid = self.validator.validate_profile(profile)
        state_valid = self.validator.validate_approval_state(state)
        return profile_valid and state_valid