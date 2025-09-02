"""Synthetic Data Sub-Agent Implementation

Business Value: Modernizes synthetic data generation for Enterprise tier.
BVJ: Growth & Enterprise | Increase Value Creation | +15% customer savings
"""

import time
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult, WebSocketManagerProtocol
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.synthetic_data_approval_handler import (
    SyntheticDataApprovalHandler,
)
from netra_backend.app.agents.synthetic_data_generation_flow import (
    GenerationFlowFactory,
)
from netra_backend.app.agents.synthetic_data_generator import (
    SyntheticDataGenerator,
    SyntheticDataResult,
)
from netra_backend.app.agents.synthetic_data_metrics_handler import (
    SyntheticDataMetricsHandler,
)

# Synthetic Data Components (preserved from legacy)
from netra_backend.app.agents.synthetic_data_presets import (
    WorkloadProfile,
    find_preset_by_name,
)
from netra_backend.app.agents.synthetic_data_profile_parser import create_profile_parser

# Validation and Workflow Modules
from netra_backend.app.agents.synthetic_data_sub_agent_validation import (
    SyntheticDataValidator,
)
from netra_backend.app.agents.synthetic_data_sub_agent_workflow import (
    SyntheticDataContext,
    SyntheticDataWorkflowOrchestrator,
)
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import RetryConfig

logger = central_logger.get_logger(__name__)




class ModernSyntheticDataSubAgent(BaseAgent):
    """Modern synthetic data sub-agent with standardized execution patterns.
    
    Provides reliable synthetic data generation with:
    - Circuit breaker protection for external services
    - Retry logic for transient failures
    - Comprehensive monitoring and metrics
    - Standardized error handling and recovery
    Uses ExecutionContext/ExecutionResult types for consistency.
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher,
                 reliability_manager: Optional[ReliabilityManager] = None):
        # Initialize BaseAgent with proper parameters
        super().__init__(
            llm_manager=llm_manager,
            name="ModernSyntheticDataSubAgent",
            description="Modern synthetic data generation agent with enhanced reliability"
        )
        
        # Store additional dependencies
        self.tool_dispatcher = tool_dispatcher
        
        # Initialize execution patterns and components
        self._initialize_execution_engine(reliability_manager)
        self._initialize_synthetic_components()
    
    def _initialize_execution_engine(self, reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize execution engine with reliability patterns."""
        if not reliability_manager:
            reliability_manager = self._create_default_reliability_manager()
        
        self.monitor = ExecutionMonitor(max_history_size=1000)
        self.execution_engine = BaseExecutionEngine(reliability_manager, self.monitor)
    
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
        # keeping within 25-line function limit
    
    def _initialize_generation_flow(self) -> None:
        """Initialize generation flow components."""
        self.generation_flow = GenerationFlowFactory.create_flow(
            generator=self.generator,
            send_update_callback=self._send_legacy_update,
            approval_handler=self._handle_approval_flow_legacy
        )
        self.validator = SyntheticDataValidator(self)
        self.workflow = SyntheticDataWorkflowOrchestrator(self)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for synthetic data generation."""
        try:
            validation_checks = await self.validator.run_comprehensive_validation(context)
            is_valid = all(validation_checks.values())
            await self.validator.log_validation_result(context, is_valid, validation_checks)
            return is_valid
        except Exception as e:
            logger.error(f"Precondition validation failed: {e}", exc_info=True)
            return False
    
    async def _check_synthetic_data_conditions(self, state: DeepAgentState) -> bool:
        """Check if synthetic data generation conditions are met."""
        if self._is_admin_request(state):
            return True
        if self._is_synthetic_request(state):
            return True
        return False
    
    
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
        """Execute synthetic data generation core logic with modern patterns."""
        synthetic_context = await self._prepare_synthetic_context(context)
        await self._track_execution_start(context, synthetic_context)
        
        try:
            result = await self._execute_generation_workflow(context, synthetic_context)
            return await self._finalize_successful_execution(context, result)
        except Exception as e:
            return await self._handle_execution_error(context, e)
    
    async def _prepare_synthetic_context(self, context: ExecutionContext) -> SyntheticDataContext:
        """Prepare synthetic data context with enhanced tracking."""
        synthetic_context = SyntheticDataContext()
        synthetic_context.workload_profile = await self._determine_workload_profile(context.state)
        synthetic_context.requires_approval = await self._check_approval_requirements(
            synthetic_context.workload_profile, context.state
        )
        return synthetic_context

    async def _track_execution_start(self, context: ExecutionContext, 
                                   synthetic_context: SyntheticDataContext) -> None:
        """Track execution start with monitoring integration."""
        self.monitor.start_execution(context)
        # Use base class WebSocket methods
        await self.emit_thinking("Preparing synthetic data generation")
        await self.metrics_handler.record_execution_start(context.run_id, synthetic_context.workload_profile)

    async def _execute_generation_workflow(self, context: ExecutionContext,
                                         synthetic_context: SyntheticDataContext) -> SyntheticDataResult:
        """Execute workflow with enhanced monitoring."""
        result = await self.workflow.execute_generation_workflow(context, synthetic_context)
        self._record_generation_metrics(context, result, synthetic_context)
        return result

    async def _finalize_successful_execution(self, context: ExecutionContext, 
                                           result: SyntheticDataResult) -> Dict[str, Any]:
        """Finalize successful execution with metrics tracking."""
        formatted_result = self.workflow.format_execution_result(result)
        await self.metrics_handler.record_successful_generation(context.run_id, result)
        # Use base class WebSocket methods for completion
        await self.emit_progress("Synthetic data generation completed", is_complete=True)
        return formatted_result

    async def _handle_execution_error(self, context: ExecutionContext, error: Exception) -> Dict[str, Any]:
        """Handle execution errors with comprehensive error tracking."""
        self.monitor.record_error(context, error)
        await self.metrics_handler.record_generation_error(context.run_id, error)
        error_result = await self.workflow.handle_core_logic_error(context, error)
        # Use base class error emission
        await self.emit_error(f"Generation failed: {str(error)}", "execution_error")
        return error_result

    def _record_generation_metrics(self, context: ExecutionContext, result: SyntheticDataResult,
                                 synthetic_context: SyntheticDataContext) -> None:
        """Record generation-specific metrics for performance tracking."""
        metrics = {
            "workload_type": synthetic_context.workload_profile.workload_type.value,
            "volume": synthetic_context.workload_profile.volume,
            "requires_approval": synthetic_context.requires_approval,
            "generation_success": result.success
        }
        context.metadata.update(metrics)

    async def _determine_workload_profile(self, state: DeepAgentState) -> 'WorkloadProfile':
        """Determine workload profile from state with error handling."""
        try:
            return await self.profile_parser.determine_workload_profile(
                state.user_request, self.llm_manager
            )
        except Exception as e:
            logger.warning(f"Failed to parse workload profile, using default: {e}")
            return self._create_default_workload_profile()

    async def _check_approval_requirements(self, profile: 'WorkloadProfile', 
                                         state: DeepAgentState) -> bool:
        """Check if approval is required with enhanced logic."""
        return await self.workflow._requires_approval(profile, state)

    def _create_default_workload_profile(self) -> 'WorkloadProfile':
        """Create default workload profile for error cases."""
        from netra_backend.app.agents.synthetic_data_presets import WorkloadType
        return WorkloadProfile(
            workload_type=WorkloadType.GENERAL_ANALYTICS, 
            volume=1000,
            time_range_days=30,
            distribution="uniform"
        )
    
    async def _send_legacy_update(self, run_id: str, update_data: Dict[str, Any]) -> None:
        """Send legacy format update via AgentWebSocketBridge (compatibility bridge)."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            
            # Use BaseAgent's WebSocket methods instead of direct bridge access
            status = update_data.get('status', 'processing')
            message = update_data.get('message', '')
            
            # Map update status to appropriate base class WebSocket methods
            if status == 'processing':
                await self.emit_thinking(message)
            elif status == 'generating':
                await self.emit_tool_executing("synthetic_data_generation", 
                                              {"data_type": update_data.get("data_type", "unknown")})
            elif status == 'completed':
                await self.emit_tool_completed("synthetic_data_generation",
                                              result=update_data.get('result'))
            elif status == 'failed':
                await self.emit_error(message, "generation_failure")
            else:
                # Use progress for custom status updates
                await self.emit_progress(f"Status: {status} - {message}")
                
        except Exception as e:
            logger.warning(f"Failed to send legacy update via bridge: {e}")
    
    async def _handle_approval_flow_legacy(self, *args, **kwargs) -> None:
        """Handle approval flow in legacy format (compatibility bridge)."""
        # Legacy approval flow handler for backward compatibility
        logger.info("Legacy approval flow handler called")
        pass
    
    async def execute(self, state: Optional[DeepAgentState], run_id: str = "", 
                     stream_updates: bool = False) -> Any:
        """Execute agent with modern patterns (implements BaseAgent abstract method)."""
        # Use BaseAgent's WebSocket event emission capabilities
        await self.emit_agent_started("Starting synthetic data generation")
        
        context = ExecutionContext(
            run_id=run_id,
            agent_name=self.name,  # Use base class 'name' attribute
            state=state,
            stream_updates=stream_updates
        )
        
        try:
            result = await self.execution_engine.execute(self, context)
            await self.emit_agent_completed({"status": "success", "result": result})
            return result
        except Exception as e:
            await self.emit_error(str(e), "execution_failure")
            raise
    
    async def execute_with_modern_patterns(self, state: DeepAgentState, run_id: str,
                                         stream_updates: bool = False) -> ExecutionResult:
        """Legacy method for backward compatibility."""
        return await self.execute(state, run_id, stream_updates)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status including all components."""
        base_status = {
            "agent_name": self.name,  # Use base class 'name' attribute
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
    
