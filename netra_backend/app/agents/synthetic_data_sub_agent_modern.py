"""Synthetic Data Sub-Agent Implementation

Business Value: Modernizes synthetic data generation for Enterprise tier.
BVJ: Growth & Enterprise | Increase Value Creation | +15% customer savings
"""

import time
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.database.session_manager import SessionManager

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.database.session_manager import SessionManager
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
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.serialization.unified_json_handler import safe_json_dumps
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
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: UnifiedToolDispatcher,
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
    
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
        """Execute synthetic data generation with UserExecutionContext.
        
        CRITICAL: Modern implementation using UserExecutionContext pattern.
        
        Args:
            context: User execution context containing all request-scoped state
            stream_updates: Whether to stream progress updates
            
        Returns:
            Synthetic data generation result
        """
        # Validate context
        if not isinstance(context, UserExecutionContext):
            raise TypeError(f"Expected UserExecutionContext, got {type(context)}")
        
        # Create database session manager (stub implementation)
        db_manager = SessionManager()
        
        try:
            # Use BaseAgent's WebSocket event emission capabilities
            await self.emit_agent_started("Starting modern synthetic data generation")
            
            logger.info(f"Starting modern synthetic data generation for user {context.user_id}, run {context.run_id}")
            
            # Get user request from context metadata
            user_request = context.metadata.get("user_request", "")
            
            # Check if synthetic data generation is needed
            if not self._should_execute_synthetic_data(user_request):
                result = {"status": "skipped", "message": "Synthetic data generation not required"}
                await self.emit_agent_completed(result)
                return result
            
            # Execute generation workflow with context
            result = await self._execute_with_context(context, stream_updates, db_manager)
            
            await self.emit_agent_completed({"status": "success", "result": result})
            logger.info(f"Modern synthetic data generation completed for run {context.run_id}")
            return result
            
        except Exception as e:
            logger.error(f"Modern synthetic data generation failed for run {context.run_id}: {e}")
            await self.emit_error(str(e), "execution_failure")
            raise
        finally:
            # Clean up database session
            await db_manager.close()

    def _should_execute_synthetic_data(self, user_request: str) -> bool:
        """Determine if synthetic data generation should be executed.
        
        Args:
            user_request: User request string
            
        Returns:
            True if synthetic data generation should be executed
        """
        if not user_request:
            return False
            
        request_lower = user_request.lower()
        synthetic_keywords = ["synthetic", "generate data", "mock data", "test data", "sample data"]
        
        return any(keyword in request_lower for keyword in synthetic_keywords)

    async def _execute_with_context(self, context: UserExecutionContext, 
                                   stream_updates: bool, db_manager: 'SessionManager') -> Dict[str, Any]:
        """Execute generation workflow using UserExecutionContext.
        
        Args:
            context: User execution context
            stream_updates: Whether to stream updates
            db_manager: Database session manager
            
        Returns:
            Generation workflow result
        """
        user_request = context.metadata.get("user_request", "")
        
        # Determine workload profile
        workload_profile = await self.profile_parser.determine_workload_profile(
            user_request, self.llm_manager
        )
        
        # Check approval requirements
        requires_approval = self._check_approval_requirements_context(workload_profile, context)
        
        if requires_approval:
            return await self._handle_approval_with_context(context, workload_profile)
        
        # Execute data generation
        return await self._execute_data_generation_with_context(context, workload_profile, stream_updates)

    def _check_approval_requirements_context(self, profile: 'WorkloadProfile', context: UserExecutionContext) -> bool:
        """Check if approval is required for context.
        
        Args:
            profile: Workload profile
            context: User execution context
            
        Returns:
            True if approval is required
        """
        # Large volume check
        if profile.volume > 50000:
            return True
            
        # Sensitive data check
        custom_params = profile.custom_parameters
        if custom_params.get("data_sensitivity") == "high":
            return True
            
        # Explicit approval request
        if context.metadata.get("require_approval", False):
            return True
            
        return False

    async def _handle_approval_with_context(self, context: UserExecutionContext, 
                                          profile: 'WorkloadProfile') -> Dict[str, Any]:
        """Handle approval workflow with context.
        
        Args:
            context: User execution context
            profile: Workload profile
            
        Returns:
            Approval workflow result
        """
        from netra_backend.app.schemas.generation import GenerationStatus
        from netra_backend.app.agents.synthetic_data_generator import SyntheticDataResult
        
        # Generate approval message
        workload_type = profile.workload_type.value.replace('_', ' ').title()
        base_info = f"{workload_type}, {profile.volume:,} records"
        timing_info = f"{profile.time_range_days} days, {profile.distribution} distribution"
        approval_message = f"📊 Synthetic Data Request: {base_info}, {timing_info}. Approve to proceed or reply 'modify' to adjust."
        
        # Create approval result
        result = SyntheticDataResult(
            success=False,
            workload_profile=profile,
            generation_status=GenerationStatus(status="pending_approval"),
            requires_approval=True,
            approval_message=approval_message
        )
        
        # Store in context metadata using SSOT method instead of global state
        self.store_metadata_result(context, 'synthetic_data_result', safe_json_dumps(result))
        self.store_metadata_result(context, 'approval_message', approval_message)
        self.store_metadata_result(context, 'requires_approval', True)
        
        # Send approval update
        if stream_updates:
            await self.emit_progress(f"⏳ {approval_message}")
        
        return safe_json_dumps(result)

    async def _execute_data_generation_with_context(self, context: UserExecutionContext, 
                                                   profile: 'WorkloadProfile', stream_updates: bool) -> Dict[str, Any]:
        """Execute data generation with context.
        
        Args:
            context: User execution context
            profile: Workload profile
            stream_updates: Whether to stream updates
            
        Returns:
            Data generation result
        """
        if stream_updates:
            await self.emit_progress(f"🔄 Generating {profile.volume:,} synthetic records...")
        
        # Generate data with user isolation
        result = await self.generator.generate_data(
            profile, context.run_id, stream_updates, 
            thread_id=context.thread_id, user_id=context.user_id
        )
        
        # Store result in context using SSOT method
        self.store_metadata_result(context, 'synthetic_data_result', safe_json_dumps(result))
        
        if stream_updates:
            records_count = result.generation_status.records_generated
            await self.emit_progress(f"✅ Successfully generated {records_count:,} synthetic records", is_complete=True)
        
        return safe_json_dumps(result)

    # Legacy support methods (for backward compatibility)
    async def _check_synthetic_data_conditions(self, state) -> bool:
        """Check if synthetic data generation conditions are met (legacy)."""
        logger.warning("Using legacy _check_synthetic_data_conditions method")
        if hasattr(state, 'triage_result'):
            triage_result = state.triage_result or {}
            if isinstance(triage_result, dict):
                category = triage_result.get("category", "")
                is_admin = triage_result.get("is_admin_mode", False)
                if "synthetic" in category.lower() or is_admin:
                    return True
        
        if hasattr(state, 'user_request') and state.user_request:
            request_lower = state.user_request.lower()
            return "synthetic" in request_lower or "generate data" in request_lower
        
        return False
    
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

    async def _determine_workload_profile(self, state) -> 'WorkloadProfile':
        """Determine workload profile from state with error handling (legacy)."""
        try:
            user_request = getattr(state, 'user_request', '')
            return await self.profile_parser.determine_workload_profile(
                user_request, self.llm_manager
            )
        except Exception as e:
            logger.warning(f"Failed to parse workload profile, using default: {e}")
            return self._create_default_workload_profile()

    async def _check_approval_requirements(self, profile: 'WorkloadProfile', state) -> bool:
        """Check if approval is required with enhanced logic (legacy)."""
        # Legacy implementation without workflow dependency
        if profile.volume > 50000:
            return True
        custom_params = profile.custom_parameters
        if custom_params.get("data_sensitivity") == "high":
            return True
        triage_result = getattr(state, 'triage_result', None) or {}
        if isinstance(triage_result, dict) and triage_result.get("require_approval", False):
            return True
        return False

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
        """Send legacy format update via BaseAgent WebSocket methods (factory pattern compliant)."""
        try:
            
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
    
    async def execute_legacy(self, state, run_id: str = "", 
                     stream_updates: bool = False) -> Any:
        """Execute agent with legacy patterns (backward compatibility)."""
        logger.warning("Using legacy execute_legacy method. Consider migrating to execute() with UserExecutionContext.")
        
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
    
    async def execute_with_modern_patterns(self, state, run_id: str,
                                         stream_updates: bool = False):
        """Legacy method for backward compatibility."""
        return await self.execute_legacy(state, run_id, stream_updates)
    
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
    
