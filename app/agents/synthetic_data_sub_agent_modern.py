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
from typing import Dict, Any, Optional, Protocol, List
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

# Validation and Workflow Modules
from app.agents.synthetic_data_sub_agent_validation import SyntheticDataValidator
from app.agents.synthetic_data_sub_agent_workflow import SyntheticDataWorkflowOrchestrator, SyntheticDataContext

logger = central_logger.get_logger(__name__)




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
        await self.send_status_update(context, "initializing", "Preparing synthetic data generation")
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
        await self.send_status_update(context, "completed", "Synthetic data generation completed")
        return formatted_result

    async def _handle_execution_error(self, context: ExecutionContext, error: Exception) -> Dict[str, Any]:
        """Handle execution errors with comprehensive error tracking."""
        self.monitor.record_error(context, error)
        await self.metrics_handler.record_generation_error(context.run_id, error)
        error_result = await self.workflow.handle_core_logic_error(context, error)
        await self.send_status_update(context, "failed", f"Generation failed: {str(error)}")
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
        from app.agents.synthetic_data_presets import WorkloadType
        return WorkloadProfile(
            workload_type=WorkloadType.GENERAL_ANALYTICS, 
            volume=1000,
            time_range_days=30,
            distribution="uniform"
        )
    
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
    
