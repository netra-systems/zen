"""Clean ActionsToMeetGoalsSubAgent using BaseAgent infrastructure (<200 lines).

Follows the golden pattern established by TriageSubAgent:
- Inherits reliability management, execution patterns, WebSocket events from BaseAgent
- Contains ONLY action plan generation business logic
- Clean single inheritance pattern with no infrastructure duplication
- Full SSOT compliance

Business Value: Action plan generation for optimization strategies.
BVJ: ALL segments | Strategic Planning | Automated action plan creation
"""

import time
from typing import Any, Dict, Optional

from netra_backend.app.agents.actions_goals_plan_builder import ActionPlanBuilder
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.input_validation import validate_agent_input
from netra_backend.app.agents.prompts import actions_to_meet_goals_prompt_template
from netra_backend.app.agents.state import ActionPlanResult, DeepAgentState, OptimizationsResult
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import DataAnalysisResponse

logger = central_logger.get_logger(__name__)


class ActionsToMeetGoalsSubAgent(BaseAgent):
    """Clean action plan generation agent using BaseAgent infrastructure.
    
    Contains ONLY action plan business logic - all infrastructure
    (reliability, execution, WebSocket events) inherited from BaseAgent.
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        """Initialize with BaseAgent infrastructure."""
        # Initialize BaseAgent with full infrastructure
        super().__init__(
            llm_manager=llm_manager,
            name="ActionsToMeetGoalsSubAgent", 
            description="Creates actionable plans from optimization strategies",
            enable_reliability=True,      # Get circuit breaker + retry
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=False,         # No caching needed for plan generation
        )
        # Store business logic dependencies only
        self.tool_dispatcher = tool_dispatcher
        self.action_plan_builder = ActionPlanBuilder()

    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for action plan generation."""
        state = context.state
        
        if not state.user_request:
            self.logger.warning(f"No user request provided in run_id: {context.run_id}")
            return False
            
        missing_deps = []
        if not state.optimizations_result:
            missing_deps.append("optimizations_result")
        if not state.data_result:
            missing_deps.append("data_result")
        
        # Handle missing dependencies gracefully with defaults
        if missing_deps:
            self.logger.warning(f"Missing dependencies: {missing_deps}. Applying defaults for graceful degradation.")
            self._apply_defaults_for_missing_deps(state, missing_deps)
        
        return True  # Continue execution with available/default data

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
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
        self._update_state_with_result(context.state, action_plan_result)
        
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
        
        return {"action_plan_result": action_plan_result}

    async def _generate_action_plan(self, context: ExecutionContext) -> ActionPlanResult:
        """Generate action plan from state data with tool execution transparency."""
        state = context.state
        run_id = context.run_id
        
        # Show tool execution for transparency
        await self.emit_tool_executing("prompt_builder", {"optimizations": bool(state.optimizations_result), "data": bool(state.data_result)})
        prompt = self._build_action_plan_prompt(state)
        await self.emit_tool_completed("prompt_builder", {"prompt_size_kb": len(prompt) / 1024})
        
        # LLM execution with transparency
        await self.emit_tool_executing("llm_processor", {"config": "actions_to_meet_goals"})
        llm_response = await self._get_llm_response_with_monitoring(prompt)
        await self.emit_tool_completed("llm_processor", {"response_size_kb": len(llm_response) / 1024})
        
        # Action plan processing
        await self.emit_tool_executing("action_plan_processor", {})
        result = await self.action_plan_builder.process_llm_response(llm_response, run_id)
        await self.emit_tool_completed("action_plan_processor", {"steps_generated": len(result.plan_steps) if result.plan_steps else 0})
        
        return result
        
    def _update_state_with_result(self, state: DeepAgentState, action_plan_result: ActionPlanResult) -> None:
        """Update state with the generated action plan result."""
        state.action_plan_result = action_plan_result

    def _build_action_plan_prompt(self, state: DeepAgentState) -> str:
        """Build prompt for action plan generation from state data."""
        return actions_to_meet_goals_prompt_template.format(
            optimizations=state.optimizations_result,
            data=state.data_result,
            user_request=state.user_request
        )
        
    async def _get_llm_response_with_monitoring(self, prompt: str) -> str:
        """Get LLM response with simplified monitoring."""
        try:
            # Use BaseAgent's LLM infrastructure
            response = await self.llm_manager.ask_llm(
                prompt, llm_config_name='actions_to_meet_goals'
            )
            return response
        except Exception as e:
            self.logger.error(f"LLM request failed: {e}")
            raise

    @validate_agent_input('ActionsToMeetGoalsSubAgent')
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute action plan generation - uses BaseAgent's reliability infrastructure."""
        await self.execute_with_reliability(
            lambda: self._execute_action_plan_main(state, run_id, stream_updates),
            "execute_action_plan",
            fallback=lambda: self._execute_action_plan_fallback(state, run_id, stream_updates)
        )
        
    async def _execute_action_plan_main(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Main execution path using modern patterns."""
        context = ExecutionContext(
            run_id=run_id,
            agent_name=self.name,
            state=state,
            stream_updates=stream_updates,
            metadata={"description": self.description}
        )
        
        # Use BaseAgent's modern execution infrastructure
        if not await self.validate_preconditions(context):
            raise ValueError("Precondition validation failed")
            
        result = await self.execute_core_logic(context)
        
    async def _execute_action_plan_fallback(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Fallback execution with default action plan - includes proper WebSocket events."""
        if stream_updates:
            # CRITICAL: Send WebSocket events even in fallback mode for user transparency
            await self.emit_agent_started("Creating fallback action plan due to processing issues")
            await self.emit_thinking("Switching to fallback action plan generation...")
            
        self.logger.warning(f"Using fallback action plan for run_id: {run_id}")
        fallback_plan = ActionPlanBuilder.get_default_action_plan()
        state.action_plan_result = fallback_plan
        
        if stream_updates:
            # CRITICAL: Complete the WebSocket event flow even in fallback
            await self.emit_agent_completed({
                "success": True,
                "fallback_used": True,
                "steps_generated": len(fallback_plan.plan_steps) if fallback_plan.plan_steps else 0,
                "message": "Action plan created using fallback method"
            })

    def _apply_defaults_for_missing_deps(self, state: DeepAgentState, missing_deps: list) -> None:
        """Apply default values for missing dependencies to enable graceful degradation."""
        if "optimizations_result" in missing_deps and not state.optimizations_result:
            state.optimizations_result = OptimizationsResult(
                optimization_type="default",
                recommendations=["Manual review required - limited optimization data available"],
                confidence_score=0.2
            )
        
        if "data_result" in missing_deps and not state.data_result:
            state.data_result = DataAnalysisResponse(
                query="Default query - using available context",
                results=[],
                insights={"status": "Limited data analysis - using optimization context"},
                metadata={"source": "default_graceful_degradation"},
                recommendations=["Collect additional data for comprehensive analysis"]
            )
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Legacy entry condition check - maintained for backward compatibility."""
        # Apply defaults if needed for backward compatibility
        if not state.optimizations_result or not state.data_result:
            missing = []
            if not state.optimizations_result:
                missing.append("optimizations_result")
            if not state.data_result:
                missing.append("data_result")
            
            self.logger.warning(f"Legacy check_entry_conditions: missing {missing}, applying defaults")
            self._apply_defaults_for_missing_deps(state, missing)
        
        return True  # Always allow execution with defaults