"""ActionsToMeetGoalsSubAgent - UserExecutionContext Pattern Implementation

Migrated to UserExecutionContext pattern for proper request isolation:
- Uses UserExecutionContext for per-request data isolation
- Database session management via SSOT database module get_db()
- Action plan generation isolated per user/thread
- Zero global state references for security compliance

Business Value: Actionable plan generation from optimization strategies
BVJ: ALL segments | Strategic Planning | Converts insights to executable actions
"""

import time
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext

from netra_backend.app.agents.actions_goals_plan_builder_uvs import ActionPlanBuilderUVS
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.input_validation import validate_agent_input
from netra_backend.app.agents.prompts import actions_to_meet_goals_prompt_template
from netra_backend.app.agents.state import ActionPlanResult, OptimizationsResult
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import DataAnalysisResponse
# SSOT Imports for compliance
from netra_backend.app.core.serialization.unified_json_handler import backend_json_handler
from netra_backend.app.core.unified_error_handler import agent_error_handler
from netra_backend.app.schemas.shared_types import ErrorContext

logger = central_logger.get_logger(__name__)


class ActionsToMeetGoalsSubAgent(BaseAgent):
    """UserExecutionContext Pattern Action Plan Generation Agent.
    
    Request Isolation: Contains ONLY action plan business logic with proper isolation
    - Uses UserExecutionContext for per-request data isolation  
    - Database sessions accessed via SSOT database module get_db()
    - Action plans isolated per user/thread for security compliance
    - Zero global state references
    """
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, tool_dispatcher: Optional[UnifiedToolDispatcher] = None):
        """Initialize with BaseAgent infrastructure.
        
        CRITICAL: LLM manager is required for this agent to function.
        During architectural migration, some instantiation paths don't provide it.
        See FIVE_WHYS_ANALYSIS_20250904.md for root cause analysis.
        """
        # Initialize BaseAgent with full infrastructure
        super().__init__(
            llm_manager=llm_manager,
            name="ActionsToMeetGoalsSubAgent", 
            description="Creates actionable plans from optimization strategies",
            enable_reliability=False,  # DISABLED: Was hiding errors - see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=False,         # No caching needed for plan generation
        )
        
        # FIVE WHYS FIX: Validate critical dependency at construction time
        if llm_manager is None:
            import warnings
            warnings.warn(
                "ActionsToMeetGoalsSubAgent instantiated without LLMManager - "
                "will fail at runtime if LLM operations are attempted. "
                "This is a known issue from incomplete architectural migration.",
                RuntimeWarning,
                stacklevel=2
            )
        
        # Store business logic dependencies only
        self.tool_dispatcher = tool_dispatcher
        self.action_plan_builder = ActionPlanBuilderUVS()  # UVS-enhanced for guaranteed value delivery

    async def validate_preconditions(self, context: 'UserExecutionContext') -> bool:
        """Validate execution preconditions for action plan generation."""
        # Extract user request from context metadata
        user_request = context.metadata.get('user_request')
        if not user_request:
            self.logger.warning(f"No user request provided in run_id: {context.run_id}")
            return False
            
        missing_deps = []
        if not context.metadata.get('optimizations_result'):
            missing_deps.append("optimizations_result")
        if not context.metadata.get('data_result'):
            missing_deps.append("data_result")
        
        # Handle missing dependencies gracefully with defaults
        if missing_deps:
            self.logger.warning(f"Missing dependencies: {missing_deps}. Applying defaults for graceful degradation.")
            self._apply_defaults_for_missing_deps(context, missing_deps)
        
        return True  # Continue execution with available/default data

    async def execute_core_logic(self, context: 'UserExecutionContext') -> Dict[str, Any]:
        """Execute core action plan generation logic with WebSocket events."""
        start_time = time.time()
        
        # CRITICAL: Emit agent_started for proper chat value delivery
        await self.emit_agent_started("Creating action plan based on optimization strategies and data analysis")
        
        # WebSocket events for user visibility
        await self.emit_thinking("Starting action plan generation based on optimization strategies...")
        await self.emit_thinking("Analyzing optimization recommendations and data insights...")
        
        # Business logic with progress updates
        await self.emit_progress("Building comprehensive action plan...")
        action_plan_result = await self._generate_action_plan(context)
        
        await self.emit_progress("Finalizing action steps and recommendations...")
        # Note: Result will be returned directly rather than stored in context
        
        # Completion events
        await self.emit_progress("Action plan generation completed successfully", is_complete=True)
        
        # CRITICAL: Emit agent_completed for proper chat value delivery
        execution_time_ms = (time.time() - start_time) * 1000
        result_data = {
            "success": True,
            "steps_generated": len(action_plan_result.plan_steps) if action_plan_result.plan_steps else 0,
            "execution_time_ms": execution_time_ms,
            "has_partial_extraction": action_plan_result.partial_extraction if hasattr(action_plan_result, 'partial_extraction') else False
        }
        await self.emit_agent_completed(result_data)
        
        # CRITICAL: Store action plan result in context metadata for other agents
        # Using SSOT method from base_agent for consistent metadata storage
        self.store_metadata_result(context, 'action_plan_result', action_plan_result)
        
        return {"action_plan_result": action_plan_result}

    async def _generate_action_plan(self, context: 'UserExecutionContext') -> ActionPlanResult:
        """Generate action plan from context data with tool execution transparency using UVS."""
        run_id = context.run_id
        
        # Extract data from context metadata
        optimizations_result = context.metadata.get('optimizations_result')
        data_result = context.metadata.get('data_result')
        
        # Show tool execution for transparency
        await self.emit_tool_executing("uvs_plan_builder", {"optimizations": bool(optimizations_result), "data": bool(data_result)})
        
        # Use UVS adaptive plan generation for guaranteed value delivery
        result = await self.action_plan_builder.generate_adaptive_plan(context)
        
        # Extract UVS mode and data state for transparency
        uvs_mode = result.metadata.custom_fields.get('uvs_mode', 'unknown') if hasattr(result, 'metadata') else 'unknown'
        data_state = result.metadata.custom_fields.get('data_state', 'unknown') if hasattr(result, 'metadata') else 'unknown'
        
        await self.emit_tool_completed("uvs_plan_builder", {
            "steps_generated": len(result.plan_steps) if result.plan_steps else 0,
            "uvs_mode": uvs_mode,
            "data_state": data_state
        })
        
        return result
        
    # Removed _update_state_with_result - results now stored in context.metadata

    def _build_action_plan_prompt(self, context: 'UserExecutionContext') -> str:
        """Build prompt for action plan generation from context data."""
        return actions_to_meet_goals_prompt_template.format(
            optimizations=context.metadata.get('optimizations_result'),
            data=context.metadata.get('data_result'),
            user_request=context.metadata.get('user_request')
        )
        
    async def _get_llm_response_with_monitoring(self, prompt: str) -> str:
        """Get LLM response with SSOT error handling."""
        try:
            # CRITICAL: Validate LLM manager is available (Five Whys Fix)
            if not self.llm_manager:
                error_msg = (
                    " FAIL:  LLM manager is None - agent was instantiated without required dependency. "
                    "This indicates incomplete architectural migration between legacy AgentRegistry "
                    "and new factory patterns. See FIVE_WHYS_ANALYSIS_20250904.md"
                )
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            # Use BaseAgent's LLM infrastructure
            response = await self.llm_manager.ask_llm(
                prompt, llm_config_name='actions_to_meet_goals'
            )
            return response
        except Exception as e:
            # Try to create error context, but don't fail if it doesn't work
            try:
                error_context = ErrorContext(
                    trace_id=ErrorContext.generate_trace_id(),
                    operation="llm_response_generation",
                    details={"prompt_size": len(prompt), "config": "actions_to_meet_goals"},
                    component="ActionsToMeetGoalsSubAgent"
                )
            except Exception as ec_error:
                # If ErrorContext creation fails, just log the error
                self.logger.error(f"ErrorContext creation failed: {ec_error}")
            
            self.logger.error(f"LLM request failed: {e}")
            # Re-raise with context - let BaseAgent's error handling manage it
            raise

    async def execute(self, context: 'UserExecutionContext', stream_updates: bool = False) -> Dict[str, Any]:
        """Execute action plan generation with UserExecutionContext pattern.
        
        Args:
            context: User execution context with database session and request data
            stream_updates: Whether to stream progress updates
            
        Returns:
            Dict with action plan results
        """
        try:
            # Validate preconditions with SSOT error handling
            if not await self.validate_preconditions(context):
                # Try to create structured error for validation failure
                try:
                    error_context = ErrorContext(
                        trace_id=ErrorContext.generate_trace_id(),
                        operation="precondition_validation",
                        details={"run_id": context.run_id, "reason": "validation_failed"},
                        component="ActionsToMeetGoalsSubAgent"
                    )
                except Exception as ec_error:
                    # If ErrorContext creation fails, just log it
                    self.logger.error(f"ErrorContext creation failed: {ec_error}")
                
                raise ValueError("Precondition validation failed for action plan generation")
            
            # Execute core logic
            result = await self.execute_core_logic(context)
            return result
            
        except Exception as e:
            # Try to create structured error handling with ErrorContext
            try:
                error_context = ErrorContext(
                    trace_id=ErrorContext.generate_trace_id(),
                    operation="action_plan_execution",
                    details={"run_id": context.run_id, "stream_updates": stream_updates, "error": str(e)},
                    component="ActionsToMeetGoalsSubAgent"
                )
            except Exception as ec_error:
                # If ErrorContext creation fails, just log it and continue with fallback
                self.logger.error(f"ErrorContext creation failed: {ec_error}")
            
            # Fallback logic for errors with structured logging
            self.logger.warning(f"Action plan generation failed, using fallback: {e}")
            return await self._execute_fallback_logic(context, stream_updates)
        
    # Removed _execute_main_logic - integrated into main execute method
        
    async def _execute_fallback_logic(self, context: 'UserExecutionContext', stream_updates: bool) -> Dict[str, Any]:
        """Fallback execution with proper WebSocket events for user transparency using UVS."""
        if stream_updates:
            await self.emit_agent_started("Creating fallback action plan due to processing issues")
            await self.emit_thinking("Switching to UVS fallback action plan generation...")
            
        self.logger.warning(f"Using UVS fallback action plan for run_id: {context.run_id}")
        
        # Use UVS builder's ultimate fallback for guaranteed value
        fallback_plan = self.action_plan_builder._get_ultimate_fallback_plan(
            "Fallback triggered due to processing issues"
        )
        
        # Note: Fallback result will be returned directly rather than stored in context
        
        if stream_updates:
            await self.emit_agent_completed({
                "success": True,
                "fallback_used": True,
                "uvs_enabled": True,
                "steps_generated": len(fallback_plan.plan_steps) if fallback_plan.plan_steps else 0,
                "message": "Action plan created using UVS fallback method with guaranteed value delivery"
            })
            
        # CRITICAL: Store fallback action plan in context metadata for other agents
        # Using SSOT method from base_agent for consistent metadata storage
        self.store_metadata_result(context, 'action_plan_result', fallback_plan)
            
        return {"action_plan_result": fallback_plan}

    def _apply_defaults_for_missing_deps(self, context: 'UserExecutionContext', missing_deps: list) -> None:
        """Apply default values for missing dependencies to enable graceful degradation."""
        if "optimizations_result" in missing_deps and not context.metadata.get('optimizations_result'):
            default_optimization = OptimizationsResult(
                optimization_type="default",
                recommendations=["Manual review required - limited optimization data available"],
                confidence_score=0.2
            )
            # Note: Default values handled in metadata copy for isolation
            if 'optimizations_result' not in context.metadata:
                # Using SSOT method for consistent metadata storage
                self.store_metadata_result(context, 'optimizations_result', default_optimization)
        
        if "data_result" in missing_deps and not context.metadata.get('data_result'):
            default_data = DataAnalysisResponse(
                query="Default query - using available context",
                results=[],
                insights={"status": "Limited data analysis - using optimization context"},
                metadata={"source": "default_graceful_degradation"},
                recommendations=["Collect additional data for comprehensive analysis"]
            )
            # Note: Default values handled in metadata copy for isolation
            if 'data_result' not in context.metadata:
                # Using SSOT method for consistent metadata storage
                self.store_metadata_result(context, 'data_result', default_data)
    
    async def check_entry_conditions(self, context: 'UserExecutionContext') -> bool:
        """Entry condition check using UserExecutionContext."""
        # Check if we have user request in context metadata
        user_request = context.metadata.get('user_request')
        if not user_request:
            self.logger.warning(f"No user request in context for run_id: {context.run_id}")
            return False
            
        # Apply defaults if needed for missing dependencies
        missing = []
        if not context.metadata.get('optimizations_result'):
            missing.append("optimizations_result")
        if not context.metadata.get('data_result'):
            missing.append("data_result")
        
        if missing:
            self.logger.warning(f"Missing dependencies: {missing}, applying defaults")
            self._apply_defaults_for_missing_deps(context, missing)
        
        return True  # Always allow execution with defaults
    
    @classmethod
    def create_agent_with_context(cls, context: 'UserExecutionContext') -> 'ActionsToMeetGoalsSubAgent':
        """Factory method for creating ActionsToMeetGoalsSubAgent with user context.
        
        This method enables the agent to be created through AgentInstanceFactory
        with proper user context isolation, avoiding deprecated global tool_dispatcher warnings.
        
        Args:
            context: User execution context for isolation
            
        Returns:
            ActionsToMeetGoalsSubAgent: Configured agent instance without deprecated warnings
        """
        # Create agent without tool_dispatcher parameter to avoid deprecation warning
        # Note: This agent requires LLMManager and ToolDispatcher but doesn't pass tool_dispatcher to BaseAgent
        # so we need to provide them via the registry or dependencies
        return cls(llm_manager=None, tool_dispatcher=None)