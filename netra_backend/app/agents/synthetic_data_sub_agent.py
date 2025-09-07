# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-09-02T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CRITICAL MIGRATION - UserExecutionContext pattern
# Git: critical-remediation-20250823 | migrate main synthetic data agent
# Change: Migrate | Scope: Module | Risk: Medium
# Session: synthetic-data-migration | Seq: 2
# Review: Required | Score: 95
# ================================

import time
from typing import List, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
# DatabaseSessionManager removed - use SSOT database module get_db() instead
from netra_backend.app.schemas.agent_models import DeepAgentState

# Import modular components
from netra_backend.app.agents.synthetic_data.approval_flow import (
    ApprovalRequirements,
    ApprovalWorkflow,
)
from netra_backend.app.agents.synthetic_data.generation_workflow import (
    GenerationErrorHandler,
    GenerationExecutor,
)
from netra_backend.app.agents.synthetic_data.llm_handler import SyntheticDataLLMExecutor
from netra_backend.app.agents.synthetic_data.messaging import CommunicationCoordinator
from netra_backend.app.agents.synthetic_data.validation import (
    MetricsValidator,
    RequestValidator,
)
from netra_backend.app.agents.synthetic_data_generator import SyntheticDataGenerator
from netra_backend.app.agents.synthetic_data_metrics_handler import (
    SyntheticDataMetricsHandler,
)
from netra_backend.app.agents.synthetic_data_presets import WorkloadProfile
from netra_backend.app.agents.synthetic_data_profile_parser import create_profile_parser
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.observability import log_agent_communication
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.serialization.unified_json_handler import safe_json_dumps

logger = central_logger.get_logger(__name__)


class SyntheticDataSubAgent(BaseAgent):
    """Sub-agent dedicated to synthetic data generation"""
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, tool_dispatcher: Optional[UnifiedToolDispatcher] = None):
        super().__init__(
            llm_manager, 
            name="SyntheticDataSubAgent", 
            description="Agent specialized in generating synthetic data for workload simulation"
        )
        self.tool_dispatcher = tool_dispatcher
        self.generator = SyntheticDataGenerator(tool_dispatcher)
        self.profile_parser = create_profile_parser()
        self.metrics_handler = SyntheticDataMetricsHandler("SyntheticDataSubAgent")
        
        # Initialize modular components
        self.approval_workflow = ApprovalWorkflow(self._send_update)
        self.llm_executor = SyntheticDataLLMExecutor(llm_manager)
        self.generation_executor = GenerationExecutor(self.generator, self._send_update)
        self.error_handler = GenerationErrorHandler(self._send_update)
        self.communicator = CommunicationCoordinator(self._send_update)
        self.validator = RequestValidator()
        self.approval_requirements = ApprovalRequirements()

    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> None:
        """Execute synthetic data generation with UserExecutionContext.
        
        CRITICAL: Migrated to use UserExecutionContext for proper request isolation.
        
        Args:
            context: User execution context containing all request-scoped state
            stream_updates: Whether to stream progress updates
            
        Raises:
            TypeError: If context is not UserExecutionContext
        """
        # Validate context type
        if not isinstance(context, UserExecutionContext):
            raise TypeError(f"Expected UserExecutionContext, got {type(context)}")
        
        # Create database session manager
        db_manager = DatabaseSessionManager(context)
        
        try:
            log_agent_communication("Supervisor", "SyntheticDataSubAgent", context.run_id, "execute_request")
            start_time = time.time()
            
            logger.info(f"Starting synthetic data generation for user {context.user_id}, run {context.run_id}")
            
            # Get user request from context metadata
            user_request = context.metadata.get("user_request", "")
            
            # Check if synthetic data generation is needed
            if not self._should_execute_synthetic_data(user_request):
                logger.info(f"Synthetic data generation not required for run_id: {context.run_id}")
                return
            
            await self._execute_main_flow_with_context(context, stream_updates, start_time, db_manager)
            self.metrics_handler.log_successful_execution(context.run_id)
            
        except Exception as e:
            await self._handle_generation_error_with_context(e, context, stream_updates)
            raise
        finally:
            # Clean up database session
            await db_manager.close()
    
    def _should_execute_synthetic_data(self, user_request: str) -> bool:
        """Determine if synthetic data generation should be executed."""
        if not user_request:
            return False
            
        request_lower = user_request.lower()
        synthetic_keywords = ["synthetic", "generate data", "mock data", "test data", "sample data"]
        
        return any(keyword in request_lower for keyword in synthetic_keywords)

    async def check_entry_conditions(self, state, run_id: str) -> bool:
        """Check if conditions are met for synthetic data generation (legacy)"""
        logger.warning("Using legacy check_entry_conditions method")
        return getattr(self.validator, 'check_entry_conditions', lambda s, r: True)(state, run_id)
    
    async def _execute_main_flow_with_context(self, context: UserExecutionContext, 
                                         stream_updates: bool, start_time: float, 
                                         db_manager: DatabaseSessionManager) -> None:
        """Execute the main generation flow using UserExecutionContext."""
        user_request = context.metadata.get("user_request", "")
        workload_profile = await self._determine_workload_profile_from_request(user_request)
        
        requires_approval = self._check_approval_requirements_context(workload_profile, context)
        
        if requires_approval:
            await self._handle_approval_with_context(context, workload_profile, stream_updates)
        else:
            await self._execute_generation_with_context(
                context, workload_profile, stream_updates, start_time
            )

    async def _determine_workload_profile_from_request(self, user_request: str) -> WorkloadProfile:
        """Determine workload profile from user request."""
        return await self.profile_parser.determine_workload_profile(user_request, self.llm_manager)
    
    def _check_approval_requirements_context(self, profile: WorkloadProfile, context: UserExecutionContext) -> bool:
        """Check if approval is required for context."""
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
                                          profile: WorkloadProfile, stream_updates: bool) -> None:
        """Handle approval workflow with context."""
        # Generate approval message
        workload_type = profile.workload_type.value.replace('_', ' ').title()
        base_info = f"{workload_type}, {profile.volume:,} records"
        timing_info = f"{profile.time_range_days} days, {profile.distribution} distribution"
        approval_message = f"📊 Synthetic Data Request: {base_info}, {timing_info}. Approve to proceed or reply 'modify' to adjust."
        
        # Store in context metadata
        context.metadata['approval_message'] = approval_message
        context.metadata['requires_approval'] = True
        context.metadata['workload_profile'] = safe_json_dumps(profile)
        
        # Send approval update
        if stream_updates:
            await self.communicator.send_approval_update(context.run_id, approval_message)
    
    async def _execute_generation_with_context(self, context: UserExecutionContext, 
                                             profile: WorkloadProfile, stream_updates: bool, start_time: float) -> None:
        """Execute data generation with context."""
        # Generate synthetic data
        result = await self.generator.generate_data(
            profile, context.run_id, stream_updates,
            thread_id=context.thread_id, user_id=context.user_id
        )
        
        # Store result in context metadata
        context.metadata['synthetic_data_result'] = safe_json_dumps(result)
        
        # Send completion update
        if stream_updates:
            records_count = result.generation_status.records_generated
            duration = int((time.time() - start_time) * 1000)
            message = f"✅ Successfully generated {records_count:,} synthetic records in {duration}ms"
            await self.communicator.send_completion_update(context.run_id, message, result)

    # Legacy support methods
    async def _execute_main_flow(self, state, run_id: str, 
                               stream_updates: bool, start_time: float) -> None:
        """Execute the main generation flow using modular components (legacy)."""
        logger.warning("Using legacy _execute_main_flow method")
        workload_profile = await self._determine_workload_profile(state)
        
        requires_approval = self.approval_requirements.check_approval_requirements(
            workload_profile, state
        )
        
        if requires_approval:
            await self.approval_workflow.process_approval_workflow(
                workload_profile, state, run_id, stream_updates
            )
        else:
            await self.generation_executor.execute_generation(
                workload_profile, state, run_id, stream_updates, start_time
            )

    async def _handle_generation_error_with_context(
        self, error: Exception, context: UserExecutionContext, stream_updates: bool
    ) -> None:
        """Handle generation errors with context."""
        self.logger.error(f"Synthetic data generation failed for run_id {context.run_id}: {error}")
        error_result = self.error_handler.create_error_result(error)
        context.metadata['synthetic_data_result'] = safe_json_dumps(error_result)
        context.metadata['error'] = str(error)
        await self.error_handler.send_error_update_if_needed(stream_updates, context.run_id, error)

    # Legacy methods for backward compatibility
    async def _handle_generation_error(
        self, error: Exception, state, run_id: str, stream_updates: bool
    ) -> None:
        """Handle generation errors (legacy)"""
        logger.warning("Using legacy _handle_generation_error method")
        self.logger.error(f"Synthetic data generation failed for run_id {run_id}: {error}")
        error_result = self.error_handler.create_error_result(error)
        if hasattr(state, 'synthetic_data_result'):
            state.synthetic_data_result = safe_json_dumps(error_result)
        await self.error_handler.send_error_update_if_needed(stream_updates, run_id, error)

    async def _determine_workload_profile(self, state) -> WorkloadProfile:
        """Determine workload profile from user request (legacy)"""
        logger.warning("Using legacy _determine_workload_profile method")
        user_request = getattr(state, 'user_request', '')
        return await self.profile_parser.determine_workload_profile(
            user_request, self.llm_manager
        )

    async def cleanup(self, state, run_id: str) -> None:
        """Cleanup after execution (legacy)"""
        logger.warning("Using legacy cleanup method")
        if hasattr(super(), 'cleanup'):
            await super().cleanup(state, run_id)
        if hasattr(self, 'MetricsValidator'):
            self.MetricsValidator.log_final_metrics(state)
    
    @classmethod
    def create_agent_with_context(cls, context: 'UserExecutionContext') -> 'SyntheticDataSubAgent':
        """Factory method for creating SyntheticDataSubAgent with user context.
        
        This method enables the agent to be created through AgentInstanceFactory
        with proper user context isolation, avoiding deprecated global tool_dispatcher warnings.
        
        Args:
            context: User execution context for isolation
            
        Returns:
            SyntheticDataSubAgent: Configured agent instance without deprecated warnings
        """
        # Create agent without tool_dispatcher parameter to avoid deprecation warning
        # Note: This agent requires LLMManager and ToolDispatcher but doesn't pass tool_dispatcher to BaseAgent
        return cls(llm_manager=None, tool_dispatcher=None)