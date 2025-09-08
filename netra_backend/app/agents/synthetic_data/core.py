"""Synthetic Data Agent Core Implementation

Modern synthetic data generation following standardized execution patterns.
Business Value: Customer-facing data generation - HIGH revenue impact
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.interface import (
    ExecutionContext,
)
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.services.user_execution_context import UserExecutionContext
# DatabaseSessionManager removed - use SSOT database module get_db() instead
from netra_backend.app.agents.synthetic_data_approval_handler import (
    ApprovalFlowOrchestrator,
    ApprovalMessageBuilder,
    ApprovalValidationHelper,
    SyntheticDataApprovalHandler,
)
from netra_backend.app.agents.synthetic_data_generation_flow import (
    GenerationFlowFactory,
)
from netra_backend.app.agents.synthetic_data_generator import (
    GenerationStatus,
    SyntheticDataGenerator,
    SyntheticDataResult,
)
from netra_backend.app.agents.synthetic_data_metrics_handler import (
    SyntheticDataMetricsHandler,
)
from netra_backend.app.agents.synthetic_data_presets import WorkloadProfile
from netra_backend.app.agents.synthetic_data_profile_parser import create_profile_parser
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.core.synthetic_data_llm_handler import SyntheticDataLLMHandler
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class SyntheticDataExecutionContext(ExecutionContext):
    """Extended execution context for synthetic data operations."""
    workload_profile: Optional[WorkloadProfile] = None
    requires_approval: bool = False
    approval_message: Optional[str] = None
    generation_start_time: Optional[float] = None


class SyntheticDataAgentCore(ABC):
    """Modern synthetic data agent core with standardized execution patterns.
    
    Uses ExecutionContext/ExecutionResult types for consistent execution workflow
    while maintaining all synthetic data generation capabilities.
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: UnifiedToolDispatcher):
        # Using single inheritance with standardized execution patterns
        self.agent_name = "SyntheticDataSubAgent"
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self._initialize_components()
        self._setup_reliability_systems()
    
    def _initialize_components(self) -> None:
        """Initialize synthetic data generation components."""
        self.generator = SyntheticDataGenerator(self.tool_dispatcher)
        self.profile_parser = create_profile_parser()
        self.metrics_handler = SyntheticDataMetricsHandler("SyntheticDataSubAgent")
        self.approval_handler = SyntheticDataApprovalHandler(self._send_update)
        self.approval_orchestrator = ApprovalFlowOrchestrator(
            self.approval_handler, ApprovalValidationHelper(), ApprovalMessageBuilder())
        self.llm_handler = SyntheticDataLLMHandler(self.llm_manager, "SyntheticDataSubAgent")
        self.generation_flow = GenerationFlowFactory.create_flow(
            generator=self.generator, send_update_callback=self._send_update,
            approval_handler=self._handle_approval_flow)
    
    def _setup_reliability_systems(self) -> None:
        """Setup monitoring and error handling systems."""
        self.error_handler = ExecutionErrorHandler
        self.monitor = ExecutionMonitor()
    
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
        """Execute synthetic data generation with UserExecutionContext.
        
        CRITICAL: Uses UserExecutionContext pattern for request isolation.
        
        Args:
            context: User execution context containing all request-scoped state
            stream_updates: Whether to stream progress updates
            
        Returns:
            Synthetic data generation result
        """
        # Validate context
        if not isinstance(context, UserExecutionContext):
            raise TypeError(f"Expected UserExecutionContext, got {type(context)}")
        
        # Get user request from context metadata
        user_request = context.metadata.get("user_request", "")
        
        # Check if synthetic data generation is needed
        if not self._should_execute_synthetic_data(user_request, context):
            logger.info(f"Synthetic data generation not required for run_id: {context.run_id}")
            return {"status": "skipped", "message": "Synthetic data generation not required"}
        
        # Create database session manager for this request
        # Database session available via context.db_session if needed
        
        try:
            logger.info(f"Starting synthetic data generation for user {context.user_id}, run {context.run_id}")
            
            # Execute generation workflow
            result = await self._execute_generation_workflow_with_context(context, stream_updates)
            
            logger.info(f"Synthetic data generation completed for run {context.run_id}")
            return result
            
        except Exception as e:
            logger.error(f"Synthetic data generation failed for run {context.run_id}: {e}")
            await self._handle_execution_error_with_context(e, context)
            raise
        finally:
            # Clean up database session
            # Session cleanup handled by context manager
    
    def _should_execute_synthetic_data(self, user_request: str, context: UserExecutionContext) -> bool:
        """Determine if synthetic data generation should be executed.
        
        Args:
            user_request: User request string
            context: User execution context
            
        Returns:
            True if synthetic data generation should be executed
        """
        # Check for explicit synthetic data request
        if not user_request:
            return False
            
        request_lower = user_request.lower()
        synthetic_keywords = ["synthetic", "generate data", "mock data", "test data", "sample data"]
        
        return any(keyword in request_lower for keyword in synthetic_keywords)

    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for synthetic data generation."""
        if self._is_admin_request(context.state):
            return True
        if self._is_synthetic_request(context.state):
            return True
        
        logger.info(f"Synthetic data generation not required for run_id: {context.run_id}")
        return False
    
    async def _execute_generation_workflow_with_context(self, context: UserExecutionContext, 
                                                       stream_updates: bool) -> Dict[str, Any]:
        """Execute generation workflow using UserExecutionContext.
        
        Args:
            context: User execution context
            stream_updates: Whether to stream updates
            db_manager: Database session manager
            
        Returns:
            Generation workflow result
        """
        await self.send_status_update_with_context(context, "initializing", "Determining workload profile...")
        
        # Get user request from context
        user_request = context.metadata.get("user_request", "")
        
        # Determine workload profile
        workload_profile = await self._determine_workload_profile_from_request(user_request)
        
        # Check if approval is needed
        if await self._requires_approval_for_context(workload_profile, context):
            return await self._handle_approval_workflow_with_context(context, workload_profile)
        
        # Execute data generation
        return await self._execute_data_generation_with_context(context, workload_profile, stream_updates)
    
    async def _determine_workload_profile_from_request(self, user_request: str) -> WorkloadProfile:
        """Determine workload profile from user request.
        
        Args:
            user_request: User request string
            
        Returns:
            Workload profile for generation
        """
        return await self.profile_parser.determine_workload_profile(
            user_request, self.llm_manager
        )
    
    async def _requires_approval_for_context(self, profile: WorkloadProfile, context: UserExecutionContext) -> bool:
        """Check if approval is required for context.
        
        Args:
            profile: Workload profile
            context: User execution context
            
        Returns:
            True if approval is required
        """
        return (self._is_large_volume(profile) or 
                self._is_sensitive_data(profile) or 
                context.metadata.get("require_approval", False))
    
    async def _handle_approval_workflow_with_context(self, context: UserExecutionContext, 
                                                   profile: WorkloadProfile) -> Dict[str, Any]:
        """Handle approval workflow with context.
        
        Args:
            context: User execution context
            profile: Workload profile
            
        Returns:
            Approval workflow result
        """
        approval_message = self._generate_approval_message(profile)
        result = self._create_approval_result(profile, approval_message)
        
        # Store in context metadata instead of global state
        context.metadata['synthetic_data_result'] = result.model_dump()
        context.metadata['approval_message'] = approval_message
        context.metadata['requires_approval'] = True
        
        await self._send_approval_update_with_context(context, approval_message)
        return result.model_dump()
    
    async def _execute_data_generation_with_context(self, context: UserExecutionContext, 
                                                   profile: WorkloadProfile, stream_updates: bool) -> Dict[str, Any]:
        """Execute data generation with context.
        
        Args:
            context: User execution context
            profile: Workload profile
            stream_updates: Whether to stream updates
            
        Returns:
            Data generation result
        """
        generation_start_time = time.time()
        await self.send_status_update_with_context(
            context, "generating", 
            f"🔄 Generating {profile.volume:,} synthetic records..."
        )
        
        # Generate data
        result = await self.generator.generate_data(
            profile, context.run_id, stream_updates, 
            thread_id=context.thread_id, user_id=context.user_id
        )
        
        # Store result in context
        context.metadata['synthetic_data_result'] = result.model_dump()
        
        # Finalize generation
        duration = self._calculate_duration(generation_start_time)
        await self._send_completion_update_with_context(context, result, duration)
        self._log_completion(context.run_id, result)
        
        return result.model_dump()
    
    async def send_status_update_with_context(self, context: UserExecutionContext, status: str, message: str) -> None:
        """Send status update using context.
        
        Args:
            context: User execution context
            status: Status string
            message: Status message
        """
        await self._send_update(context.run_id, {"status": status, "message": message})
    
    async def _send_approval_update_with_context(self, context: UserExecutionContext, message: str) -> None:
        """Send approval update using context.
        
        Args:
            context: User execution context
            message: Approval message
        """
        await self._send_update(context.run_id, {
            "status": "approval_required",
            "message": message,
            "requires_user_action": True,
            "action_type": "approve_synthetic_data"
        })
    
    async def _send_completion_update_with_context(self, context: UserExecutionContext, 
                                                 result: SyntheticDataResult, duration: int) -> None:
        """Send completion update using context.
        
        Args:
            context: User execution context
            result: Generation result
            duration: Generation duration in milliseconds
        """
        completion_data = self._build_completion_data(result, duration)
        await self._send_update(context.run_id, completion_data)
    
    async def _handle_execution_error_with_context(self, error: Exception, context: UserExecutionContext) -> None:
        """Handle execution error with context.
        
        Args:
            error: Exception that occurred
            context: User execution context
        """
        logger.error(f"Synthetic data generation failed for run_id {context.run_id}: {error}")
        error_result = self._create_error_result(error)
        context.metadata['synthetic_data_result'] = error_result.model_dump()
        
        await self._send_update(context.run_id, {
            "status": "error",
            "message": f"❌ Synthetic data generation failed: {str(error)}",
            "error": str(error)
        })

    def _is_admin_request(self, state) -> bool:
        """Check if request is from admin mode."""
        triage_result = getattr(state, 'triage_result', None) or {}
        if not isinstance(triage_result, dict):
            return False
        
        category = triage_result.get("category", "")
        is_admin = triage_result.get("is_admin_mode", False)
        return "synthetic" in category.lower() or is_admin
    
    def _is_synthetic_request(self, state) -> bool:
        """Check if request explicitly mentions synthetic data."""
        user_request = getattr(state, 'user_request', None)
        if not user_request:
            return False
        request_lower = user_request.lower()
        return "synthetic" in request_lower or "generate data" in request_lower
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute synthetic data generation core logic (legacy support)."""
        logger.warning(f"Using legacy execute_core_logic for run_id: {context.run_id}. "
                      "Consider migrating to execute() with UserExecutionContext.")
        
        # Cast to our extended context type
        synth_context = self._create_synthetic_context(context)
        
        try:
            return await self._execute_generation_workflow(synth_context)
        except Exception as e:
            await self._handle_execution_error(e, synth_context)
            raise
    
    def _create_synthetic_context(self, context: ExecutionContext) -> SyntheticDataExecutionContext:
        """Create extended synthetic data context."""
        return SyntheticDataExecutionContext(
            run_id=context.run_id,
            agent_name=context.agent_name,
            state=context.state,
            stream_updates=context.stream_updates,
            thread_id=context.thread_id,
            user_id=context.user_id,
            retry_count=context.retry_count,
            max_retries=context.max_retries,
            start_time=context.start_time,
            correlation_id=context.correlation_id,
            metadata=context.metadata or {}
        )
    
    async def _execute_generation_workflow(self, context: SyntheticDataExecutionContext) -> Dict[str, Any]:
        """Execute the complete generation workflow."""
        await self.send_status_update(context, "initializing", "Determining workload profile...")
        
        workload_profile = await self._determine_workload_profile(context.state)
        context.workload_profile = workload_profile
        
        approval_result = await self._handle_approval_if_needed(context)
        if approval_result:
            return approval_result
        
        return await self._execute_data_generation(context)
    
    async def _determine_workload_profile(self, state) -> WorkloadProfile:
        """Determine workload profile from user request."""
        user_request = getattr(state, 'user_request', '')
        return await self.profile_parser.determine_workload_profile(
            user_request, self.llm_manager
        )
    
    async def _handle_approval_if_needed(self, context: SyntheticDataExecutionContext) -> Optional[Dict[str, Any]]:
        """Handle approval flow if required."""
        if not await self._requires_approval(context.workload_profile, context.state):
            return None
        await self.send_status_update(context, "approval_required", "User approval required...")
        approval_result = await self._process_approval_workflow(context)
        # Store in state for backward compatibility
        if hasattr(context.state, 'synthetic_data_result'):
            context.state.synthetic_data_result = approval_result
        return approval_result
    
    async def _requires_approval(self, profile: WorkloadProfile, state) -> bool:
        """Check if user approval is required."""
        return (self._is_large_volume(profile) or self._is_sensitive_data(profile) or 
                self._requires_explicit_approval(state))
    
    def _is_large_volume(self, profile: WorkloadProfile) -> bool:
        """Check if volume requires approval."""
        return profile.volume > 50000
    
    def _is_sensitive_data(self, profile: WorkloadProfile) -> bool:
        """Check if data type is sensitive."""
        custom_params = profile.custom_parameters
        return custom_params.get("data_sensitivity") == "high"
    
    def _requires_explicit_approval(self, state) -> bool:
        """Check if explicit approval is requested."""
        triage_result = getattr(state, 'triage_result', None) or {}
        if not isinstance(triage_result, dict):
            return False
        return triage_result.get("require_approval", False)
    
    async def _process_approval_workflow(self, context: SyntheticDataExecutionContext) -> Dict[str, Any]:
        """Process the approval workflow steps."""
        approval_message = self._generate_approval_message(context.workload_profile)
        context.approval_message = approval_message
        approval_result = self._create_approval_result(context.workload_profile, approval_message)
        await self._send_approval_update_if_needed(context, approval_message)
        return approval_result.model_dump()
    
    def _generate_approval_message(self, profile: WorkloadProfile) -> str:
        """Generate user-friendly approval message."""
        workload_type = profile.workload_type.value.replace('_', ' ').title()
        base_info = f"{workload_type}, {profile.volume:,} records"
        timing_info = f"{profile.time_range_days} days, {profile.distribution} distribution"
        return f"📊 Synthetic Data Request: {base_info}, {timing_info}. Approve to proceed or reply 'modify' to adjust."
    
    def _create_approval_result(self, profile: WorkloadProfile, message: str) -> SyntheticDataResult:
        """Create approval required result."""
        return SyntheticDataResult(
            success=False,
            workload_profile=profile,
            generation_status=GenerationStatus(status="pending_approval"),
            requires_approval=True,
            approval_message=message
        )
    
    async def _send_approval_update_if_needed(self, context: SyntheticDataExecutionContext, message: str) -> None:
        """Send approval update if streaming enabled."""
        if context.stream_updates:
            await self._send_approval_update(context, message)
    
    async def _send_approval_update(self, context: SyntheticDataExecutionContext, message: str) -> None:
        """Send approval required update."""
        await self._send_update(context.run_id, {
            "status": "approval_required",
            "message": message,
            "requires_user_action": True,
            "action_type": "approve_synthetic_data",
            "workload_profile": context.workload_profile.model_dump() if context.workload_profile else {}
        })
    
    async def _execute_data_generation(self, context: SyntheticDataExecutionContext) -> Dict[str, Any]:
        """Execute the actual data generation."""
        context.generation_start_time = time.time()
        await self.send_status_update(context, "generating", 
                                    f"🔄 Generating {context.workload_profile.volume:,} synthetic records...")
        result = await self._generate_and_store_result(context)
        await self._finalize_generation(context, result)
        return result.model_dump()
    
    async def _generate_and_store_result(self, context: SyntheticDataExecutionContext) -> SyntheticDataResult:
        """Generate data and store result in state."""
        result = await self.generator.generate_data(
            context.workload_profile, context.run_id, context.stream_updates)
        # Store in state for backward compatibility
        if hasattr(context.state, 'synthetic_data_result'):
            context.state.synthetic_data_result = result.model_dump()
        return result
    
    async def _finalize_generation(self, context: SyntheticDataExecutionContext, result: SyntheticDataResult) -> None:
        """Finalize generation with updates and logging."""
        duration = self._calculate_duration(context.generation_start_time)
        await self._send_completion_update(context, result, duration)
        self._log_completion(context.run_id, result)
    
    def _calculate_duration(self, start_time: Optional[float]) -> int:
        """Calculate duration in milliseconds."""
        if not start_time:
            return 0
        return int((time.time() - start_time) * 1000)
    
    async def _send_completion_update(self, context: SyntheticDataExecutionContext, 
                                    result: SyntheticDataResult, duration: int) -> None:
        """Send completion update."""
        if not context.stream_updates:
            return
        completion_data = self._build_completion_data(result, duration)
        await self._send_update(context.run_id, completion_data)
    
    def _build_completion_data(self, result: SyntheticDataResult, duration: int) -> Dict[str, Any]:
        """Build completion update data dictionary."""
        records_count = result.generation_status.records_generated
        sample_data = result.sample_data[:5] if result.sample_data else None
        message = f"✅ Successfully generated {records_count:,} synthetic records in {duration}ms"
        return {"status": "completed", "message": message, "result": result.model_dump(), "sample_data": sample_data}
    
    def _log_completion(self, run_id: str, result: SyntheticDataResult) -> None:
        """Log successful completion."""
        logger.info(
            f"Synthetic data generation completed for run_id {run_id}: "
            f"{result.generation_status.records_generated} records generated"
        )
    
    async def _handle_execution_error(self, error: Exception, context: SyntheticDataExecutionContext) -> None:
        """Handle execution errors."""
        logger.error(f"Synthetic data generation failed for run_id {context.run_id}: {error}")
        error_result = self._create_error_result(error)
        # Store in state for backward compatibility
        if hasattr(context.state, 'synthetic_data_result'):
            context.state.synthetic_data_result = error_result.model_dump()
        await self._send_error_update_if_needed(context, error)
    
    def _create_error_result(self, error: Exception) -> SyntheticDataResult:
        """Create error result."""
        return SyntheticDataResult(success=False, workload_profile=None,
                                 generation_status=GenerationStatus(status="failed", errors=[str(error)]))
    
    async def _send_error_update_if_needed(self, context: SyntheticDataExecutionContext, error: Exception) -> None:
        """Send error update if streaming enabled."""
        if context.stream_updates:
            await self._send_update(context.run_id, {"status": "error",
                                                   "message": f"❌ Synthetic data generation failed: {str(error)}",
                                                   "error": str(error)})
    
    async def _send_update(self, run_id: str, update: Dict[str, Any]) -> None:
        """Send update via callback (placeholder for actual websocket integration)."""
        logger.debug(f"Update for {run_id}: {update.get('status', 'unknown')}")
    
    async def _handle_approval_flow(self, profile: WorkloadProfile, state,
                                   run_id: str, stream_updates: bool) -> None:
        """Handle approval request flow (legacy compatibility method)."""
        context = SyntheticDataExecutionContext(run_id=run_id, agent_name=self.agent_name,
                                               state=state, stream_updates=stream_updates, workload_profile=profile)
        await self._process_approval_workflow(context)