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
from typing import Optional

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response
from app.agents.synthetic_data_presets import (
    WorkloadProfile, DataGenerationType, get_all_presets, find_preset_by_name
)
from app.agents.synthetic_data_generator import (
    SyntheticDataGenerator, SyntheticDataResult, GenerationStatus
)
from app.logging_config import central_logger
from app.llm.observability import (
    start_llm_heartbeat, stop_llm_heartbeat, generate_llm_correlation_id,
    log_agent_communication, log_agent_input, log_agent_output
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
        self.preseeded_workloads = get_all_presets()

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
            await self._execute_generation_flow(state, run_id, stream_updates, start_time)
            log_agent_communication("SyntheticDataSubAgent", "Supervisor", run_id, "execute_response")
        except Exception as e:
            await self._handle_generation_error(e, state, run_id, stream_updates)
            raise
    
    async def _execute_generation_flow(self, state: DeepAgentState, run_id: str, 
                                     stream_updates: bool, start_time: float) -> None:
        """Execute the full generation flow."""
        await self._send_initial_update(run_id, stream_updates)
        workload_profile = await self._determine_workload_profile(state)
        
        if await self._requires_approval(workload_profile, state):
            await self._handle_approval_flow(workload_profile, state, run_id, stream_updates)
            return
        
        await self._execute_generation(workload_profile, state, run_id, stream_updates, start_time)
    
    async def _send_initial_update(self, run_id: str, stream_updates: bool) -> None:
        """Send initial status update"""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "starting",
                "message": "🎲 Initializing synthetic data generation...",
                "agent": "SyntheticDataSubAgent"
            })
    
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
        approval_message = self._generate_approval_message(profile)
        
        state.synthetic_data_result = self._create_approval_result(
            profile, approval_message
        ).model_dump()
        
        if stream_updates:
            await self._send_approval_update(run_id, profile, approval_message)
    
    async def _execute_generation(
        self,
        profile: WorkloadProfile,
        state: DeepAgentState,
        run_id: str,
        stream_updates: bool,
        start_time: float
    ) -> None:
        """Execute the actual data generation"""
        await self._send_generation_update(profile, run_id, stream_updates)
        
        result = await self.generator.generate_data(profile, run_id, stream_updates)
        state.synthetic_data_result = result.model_dump()
        
        await self._send_completion_update(result, run_id, stream_updates, start_time)
        
        self._log_completion(run_id, result)
    
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
        if stream_updates:
            duration = int((time.time() - start_time) * 1000)
            await self._send_update(run_id, {
                "status": "completed",
                "message": f"✅ Successfully generated {result.generation_status.records_generated:,} synthetic records in {duration}ms",
                "result": result.model_dump(),
                "sample_data": result.sample_data[:5] if result.sample_data else None
            })
    
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
        
        state.synthetic_data_result = self._create_error_result(error).model_dump()
        
        if stream_updates:
            await self._send_update(run_id, {
                "status": "error",
                "message": f"❌ Synthetic data generation failed: {str(error)}",
                "error": str(error)
            })

    async def _determine_workload_profile(self, state: DeepAgentState) -> WorkloadProfile:
        """Determine workload profile from user request"""
        if not state.user_request:
            return self._get_default_profile()
        
        preset = self._find_matching_preset(state.user_request)
        if preset:
            return preset
        
        return await self._parse_custom_profile(state.user_request)
    
    def _find_matching_preset(self, user_request: str) -> Optional[WorkloadProfile]:
        """Find matching preset from user request"""
        request_lower = user_request.lower()
        for name, profile in self.preseeded_workloads.items():
            if name in request_lower:
                self.logger.info(f"Using pre-seeded workload: {name}")
                return profile
        return None
    
    async def _parse_custom_profile(self, user_request: str) -> WorkloadProfile:
        """Parse custom profile from user request"""
        try:
            prompt = self._create_parsing_prompt(user_request)
            response = await self._call_llm_with_logging(prompt)
            params = extract_json_from_response(response)
            
            if params:
                return WorkloadProfile(**params)
        except Exception as e:
            self.logger.warning(f"Failed to parse workload profile: {e}")
        
        return self._get_default_profile()
    
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
            log_agent_input(
                "SyntheticDataSubAgent", "LLM", len(prompt), correlation_id
            )
            
            response = await self.llm_manager.ask_llm(
                prompt, llm_config_name='default'
            )
            
            log_agent_output(
                "LLM", "SyntheticDataSubAgent", 
                len(response), "success", correlation_id
            )
            return response
        except Exception as e:
            log_agent_output(
                "LLM", "SyntheticDataSubAgent", 0, "error", correlation_id
            )
            raise
    
    def _create_parsing_prompt(self, user_request: str) -> str:
        """Create prompt for parsing user request"""
        return f"""
Analyze this request for synthetic data parameters: {user_request}

Return JSON with fields: workload_type (inference_logs|training_data|performance_metrics|cost_data|custom), volume (100-1000000), time_range_days (1-365), distribution (normal|uniform|exponential), noise_level (0.0-0.5), custom_parameters.

Default volume to 1000 if not specified.
"""
    
    def _get_default_profile(self) -> WorkloadProfile:
        """Get default workload profile"""
        return WorkloadProfile(
            workload_type=DataGenerationType.INFERENCE_LOGS,
            volume=1000,
            time_range_days=30
        )

    async def _check_approval_requirements(self, profile: WorkloadProfile, state: DeepAgentState) -> bool:
        """Check if user approval is required for this generation"""
        if self._is_large_volume(profile):
            return True
        if self._is_sensitive_data(profile):
            return True
        if self._requires_explicit_approval(state):
            return True
        return False
    
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
        return f"""📊 Synthetic Data Request: {workload_type}, {profile.volume:,} records, {profile.time_range_days} days, {profile.distribution} distribution. Approve to proceed or reply 'modify' to adjust."""
    
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
        
        # Log final metrics
        if (hasattr(state, 'synthetic_data_result') and 
            state.synthetic_data_result and 
            isinstance(state.synthetic_data_result, dict)):
            result = state.synthetic_data_result
            metadata = result.get('metadata', {})
            status = result.get('generation_status', {})
            self.logger.info(
                f"Synthetic data generation completed: "
                f"table={metadata.get('table_name')}, "
                f"records={status.get('records_generated')}"
            )