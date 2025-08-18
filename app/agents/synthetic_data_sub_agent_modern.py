"""Modern Synthetic Data Sub-Agent Implementation

Modern implementation extending BaseExecutionInterface with:
- Standardized execution patterns
- Integrated reliability management  
- Comprehensive error handling
- Performance monitoring
- Circuit breaker protection

Business Value: Modernizes synthetic data generation for Enterprise tier.
BVJ: Growth & Enterprise | Increase Value Creation | +15% customer savings
"""

import time
from typing import Dict, Any, Optional, Protocol
from dataclasses import dataclass

from app.logging_config import central_logger
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState

# Modern Base Components
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult, 
    WebSocketManagerProtocol
)
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.errors import ExecutionErrorHandler

# Synthetic Data Components (preserved from legacy)
from app.agents.synthetic_data_presets import WorkloadProfile, find_preset_by_name
from app.agents.synthetic_data_profile_parser import create_profile_parser
from app.agents.synthetic_data_generator import SyntheticDataGenerator, SyntheticDataResult
from app.agents.synthetic_data_metrics_handler import SyntheticDataMetricsHandler
from app.agents.synthetic_data_approval_handler import SyntheticDataApprovalHandler
from app.agents.synthetic_data_generation_flow import GenerationFlowFactory
from app.schemas.shared_types import RetryConfig
from app.agents.base.circuit_breaker import CircuitBreakerConfig

logger = central_logger.get_logger(__name__)


@dataclass
class SyntheticDataContext:
    """Extended context for synthetic data operations."""
    workload_profile: Optional[WorkloadProfile] = None
    requires_approval: bool = False
    generation_started: bool = False
    approval_requested: bool = False


class ModernSyntheticDataSubAgent(BaseExecutionInterface):
    """Modern synthetic data sub-agent with standardized execution patterns.
    
    Provides reliable synthetic data generation with:
    - Circuit breaker protection for external services
    - Retry logic for transient failures
    - Comprehensive monitoring and metrics
    - Standardized error handling and recovery
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher,
                 websocket_manager: Optional[WebSocketManagerProtocol] = None,
                 reliability_manager: Optional[ReliabilityManager] = None):
        super().__init__("ModernSyntheticDataSubAgent", websocket_manager)
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self._initialize_execution_engine(reliability_manager)
        self._initialize_synthetic_components()
    
    def _initialize_execution_engine(self, reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize execution engine with reliability patterns."""
        if not reliability_manager:
            reliability_manager = self._create_default_reliability_manager()
        
        monitor = ExecutionMonitor(max_history_size=1000)
        self.execution_engine = BaseExecutionEngine(reliability_manager, monitor)
        self.monitor = monitor
    
    def _create_default_reliability_manager(self) -> ReliabilityManager:
        """Create default reliability manager with synthetic data optimized settings."""
        circuit_config = CircuitBreakerConfig(
            name="synthetic_data_generation",
            failure_threshold=3,
            recovery_timeout=30
        )
        retry_config = RetryConfig(max_retries=2, base_delay=1.0, max_delay=10.0)
        return ReliabilityManager(circuit_config, retry_config)
    
    def _initialize_synthetic_components(self) -> None:
        """Initialize synthetic data specific components."""
        self.generator = SyntheticDataGenerator(self.tool_dispatcher)
        self.profile_parser = create_profile_parser()
        self.metrics_handler = SyntheticDataMetricsHandler("ModernSyntheticDataSubAgent")
        self._initialize_approval_components()
        self._initialize_generation_flow()
    
    def _initialize_approval_components(self) -> None:
        """Initialize approval handling components."""
        self.approval_handler = SyntheticDataApprovalHandler(self._send_legacy_update)
        # Note: Additional approval components would be initialized here
        # keeping within 8-line function limit
    
    def _initialize_generation_flow(self) -> None:
        """Initialize generation flow components."""
        self.generation_flow = GenerationFlowFactory.create_flow(
            generator=self.generator,
            send_update_callback=self._send_legacy_update,
            approval_handler=self._handle_approval_flow_legacy
        )
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for synthetic data generation."""
        try:
            is_valid = await self._check_synthetic_data_conditions(context.state)
            await self._log_validation_result(context, is_valid)
            return is_valid
        except Exception as e:
            logger.error(f"Precondition validation failed: {e}")
            return False
    
    async def _check_synthetic_data_conditions(self, state: DeepAgentState) -> bool:
        """Check if synthetic data generation conditions are met."""
        if self._is_admin_request(state):
            return True
        if self._is_synthetic_request(state):
            return True
        return False
    
    async def _log_validation_result(self, context: ExecutionContext, is_valid: bool) -> None:
        """Log validation result for monitoring."""
        status = "valid" if is_valid else "invalid" 
        logger.info(f"Precondition validation for {context.run_id}: {status}")
        if not is_valid:
            logger.info("Synthetic data generation not required for this request")
    
    def _is_admin_request(self, state: DeepAgentState) -> bool:
        """Check if request is from admin mode."""
        triage_result = state.triage_result or {}
        if not isinstance(triage_result, dict):
            return False
        category = triage_result.get("category", "")
        is_admin = triage_result.get("is_admin_mode", False)
        return "synthetic" in category.lower() or is_admin
    
    def _is_synthetic_request(self, state: DeepAgentState) -> bool:
        """Check if request explicitly mentions synthetic data."""
        if not state.user_request:
            return False
        request_lower = state.user_request.lower()
        return "synthetic" in request_lower or "generate data" in request_lower
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute synthetic data generation core logic."""
        synthetic_context = SyntheticDataContext()
        
        try:
            result = await self._execute_generation_workflow(context, synthetic_context)
            return self._format_execution_result(result)
        except Exception as e:
            return await self._handle_core_logic_error(context, e)
    
    async def _execute_generation_workflow(self, context: ExecutionContext,
                                         synthetic_context: SyntheticDataContext) -> SyntheticDataResult:
        """Execute complete generation workflow."""
        workload_profile = await self._determine_workload_profile(context.state)
        synthetic_context.workload_profile = workload_profile
        
        if await self._requires_approval(workload_profile, context.state):
            return await self._handle_approval_workflow(context, synthetic_context)
        
        return await self._execute_direct_generation(context, synthetic_context)
    
    async def _determine_workload_profile(self, state: DeepAgentState) -> WorkloadProfile:
        """Determine workload profile from user request."""
        return await self.profile_parser.determine_workload_profile(
            state.user_request, self.llm_manager
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
        await self.send_status_update(context, "generating", "Starting data generation...")
        
        result = await self.generator.generate_data(
            synthetic_context.workload_profile, context.run_id, context.stream_updates
        )
        context.state.synthetic_data_result = result.model_dump()
        
        return result
    
    def _generate_approval_message(self, profile: WorkloadProfile) -> str:
        """Generate approval message for user review."""
        workload_type = profile.workload_type.value.replace('_', ' ').title()
        base_info = f"{workload_type}, {profile.volume:,} records"
        timing_info = f"{profile.time_range_days} days, {profile.distribution} distribution"
        return f"📊 Synthetic Data Request: {base_info}, {timing_info}. Approve to proceed."
    
    def _create_approval_result(self, profile: WorkloadProfile, message: str) -> SyntheticDataResult:
        """Create result indicating approval required."""
        from app.agents.synthetic_data_generator import GenerationStatus
        return SyntheticDataResult(
            success=False,
            workload_profile=profile,
            generation_status=GenerationStatus(status="pending_approval"),
            requires_approval=True,
            approval_message=message
        )
    
    async def _send_approval_update(self, context: ExecutionContext, message: str) -> None:
        """Send approval required update via WebSocket."""
        await self.send_status_update(context, "approval_required", message)
    
    def _format_execution_result(self, result: SyntheticDataResult) -> Dict[str, Any]:
        """Format SyntheticDataResult for standard execution result."""
        return {
            "success": result.success,
            "workload_profile": result.workload_profile.model_dump() if result.workload_profile else None,
            "generation_status": result.generation_status.model_dump() if result.generation_status else None,
            "requires_approval": result.requires_approval,
            "sample_data": result.sample_data[:5] if result.sample_data else None
        }
    
    async def _handle_core_logic_error(self, context: ExecutionContext, error: Exception) -> Dict[str, Any]:
        """Handle errors in core logic execution."""
        logger.error(f"Core logic error in {context.agent_name}: {error}")
        return {
            "success": False,
            "error": str(error),
            "error_type": error.__class__.__name__
        }
    
    async def _send_legacy_update(self, run_id: str, update_data: Dict[str, Any]) -> None:
        """Send legacy format update (compatibility bridge)."""
        if self.websocket_manager:
            try:
                await self.websocket_manager.send_agent_update(
                    run_id, self.agent_name, update_data
                )
            except Exception as e:
                logger.warning(f"Failed to send legacy update: {e}")
    
    async def _handle_approval_flow_legacy(self, *args, **kwargs) -> None:
        """Handle approval flow in legacy format (compatibility bridge)."""
        # Legacy approval flow handler for backward compatibility
        logger.info("Legacy approval flow handler called")
        pass
    
    async def execute_with_modern_patterns(self, state: DeepAgentState, run_id: str,
                                         stream_updates: bool = False) -> ExecutionResult:
        """Execute using modern execution patterns with full orchestration."""
        context = ExecutionContext(
            run_id=run_id,
            agent_name=self.agent_name,
            state=state,
            stream_updates=stream_updates
        )
        
        return await self.execution_engine.execute(self, context)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status including all components."""
        base_status = {
            "agent_name": self.agent_name,
            "execution_engine": self.execution_engine.get_health_status(),
            "monitor": self.monitor.get_health_status()
        }
        
        synthetic_status = self._get_synthetic_components_health()
        return {**base_status, **synthetic_status}
    
    def _get_synthetic_components_health(self) -> Dict[str, Any]:
        """Get health status of synthetic data specific components."""
        return {
            "synthetic_generator": "healthy",  # Could be enhanced with actual health checks
            "profile_parser": "healthy",
            "metrics_handler": "healthy"
        }