# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T10:30:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Modernize with BaseExecutionInterface pattern
# Git: v6 | 2c55fb99 | dirty (27 uncommitted)
# Change: Feature | Scope: Component | Risk: High
# Session: modernization-session | Seq: 1
# Review: Pending | Score: 95
# ================================
import json
from typing import Dict, Any, Optional

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, 
    ExecutionResult, ExecutionStatus
)
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.errors import (
    ExecutionErrorHandler, ValidationError,
    AgentExecutionError
)
from app.agents.prompts import actions_to_meet_goals_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState, ActionPlanResult, PlanStep
from app.agents.utils import extract_json_from_response, extract_partial_json
from app.logging_config import central_logger as logger
from app.llm.observability import (
    start_llm_heartbeat, stop_llm_heartbeat, generate_llm_correlation_id,
    log_agent_communication, log_agent_input, log_agent_output
)
from app.core.reliability_utils import create_agent_reliability_wrapper
from app.core.fallback_utils import create_agent_fallback_strategy
from app.agents.input_validation import validate_agent_input


class ActionsToMeetGoalsSubAgent(BaseExecutionInterface, BaseSubAgent):
    """Modernized agent implementing BaseExecutionInterface pattern."""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        """Initialize with modern execution patterns."""
        BaseSubAgent.__init__(
            self, llm_manager, 
            name="ActionsToMeetGoalsSubAgent", 
            description="This agent creates a plan of action."
        )
        BaseExecutionInterface.__init__(self, "ActionsToMeetGoalsSubAgent")
        
        self.tool_dispatcher = tool_dispatcher
        
        # Modern execution infrastructure
        self.monitor = ExecutionMonitor()
        self.reliability_manager = ReliabilityManager(
            circuit_breaker_config={"failure_threshold": 5, "recovery_timeout": 60},
            retry_config={"max_retries": 3, "base_delay": 1.0}
        )
        self.execution_engine = BaseExecutionEngine(
            self.reliability_manager, self.monitor
        )
        self.error_handler = ExecutionErrorHandler()
        
        # Backward compatibility
        self.reliability = create_agent_reliability_wrapper("ActionsToMeetGoalsSubAgent")
        self.fallback_strategy = create_agent_fallback_strategy("ActionsToMeetGoalsSubAgent")

    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions."""
        state = context.state
        if not state.optimizations_result or not state.data_result:
            raise ValidationError(
                "Missing required state: optimizations_result and data_result required"
            )
        return True

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core action plan generation logic."""
        state = context.state
        run_id = context.run_id
        
        # Send processing update
        await self.send_status_update(
            context, "executing", 
            "Creating action plan based on optimization strategies..."
        )
        
        # Generate action plan
        prompt = self._build_action_plan_prompt(state)
        llm_response = await self._get_llm_response(prompt, run_id)
        action_plan_result = await self._process_llm_response(llm_response, run_id)
        
        # Update state
        state.action_plan_result = action_plan_result
        
        # Send completion update
        await self.send_status_update(
            context, "completed",
            "Action plan created successfully"
        )
        
        return {"action_plan_result": action_plan_result}

    async def send_status_update(
        self, context: ExecutionContext, 
        status: str, message: str
    ) -> None:
        """Send status update via WebSocket."""
        if context.stream_updates:
            status_map = {
                "executing": "processing",
                "completed": "processed",
                "failed": "error"
            }
            await self._send_update(context.run_id, {
                "status": status_map.get(status, status),
                "message": message
            })

    @validate_agent_input('ActionsToMeetGoalsSubAgent')
    async def execute(
        self, state: DeepAgentState, 
        run_id: str, stream_updates: bool
    ) -> None:
        """Modernized execute using BaseExecutionEngine."""
        log_agent_communication(
            "Supervisor", "ActionsToMeetGoalsSubAgent", 
            run_id, "execute_request"
        )
        
        # Create execution context
        context = ExecutionContext(
            run_id=run_id,
            agent_name=self.name,
            state=state,
            stream_updates=stream_updates,
            metadata={"description": self.description}
        )
        
        try:
            # Execute with modern pattern
            result = await self.execution_engine.execute(self, context)
            
            # Handle result
            if not result.success:
                await self._handle_execution_failure(result, state, run_id)
            
        except Exception as e:
            # Fallback to legacy execution
            await self._execute_fallback_workflow(state, run_id, stream_updates)
            
        finally:
            log_agent_communication(
                "ActionsToMeetGoalsSubAgent", "Supervisor",
                run_id, "execute_response"
            )

    async def _handle_execution_failure(
        self, result: ExecutionResult,
        state: DeepAgentState, run_id: str
    ) -> None:
        """Handle execution failure with fallback."""
        logger.error(f"Execution failed: {result.error}")
        fallback_plan = self._get_default_action_plan()
        state.action_plan_result = fallback_plan

    async def _execute_fallback_workflow(
        self, state: DeepAgentState,
        run_id: str, stream_updates: bool
    ) -> None:
        """Backward compatibility fallback workflow."""
        main_executor = self._create_main_executor(state, run_id, stream_updates)
        fallback_executor = self._create_fallback_executor(state, run_id, stream_updates)
        result = await self._execute_with_protection(
            main_executor, fallback_executor, run_id
        )
        await self._apply_reliability_protection(result)

    def _build_action_plan_prompt(self, state: DeepAgentState) -> str:
        """Build prompt for action plan generation."""
        return actions_to_meet_goals_prompt_template.format(
            optimizations=state.optimizations_result,
            data=state.data_result,
            user_request=state.user_request
        )

    async def _get_llm_response(self, prompt: str, run_id: str) -> str:
        """Get LLM response with monitoring."""
        correlation_id = generate_llm_correlation_id()
        start_llm_heartbeat(correlation_id, "ActionsToMeetGoalsSubAgent")
        try:
            self._log_prompt_size(prompt, run_id)
            log_agent_input(
                "ActionsToMeetGoalsSubAgent", "LLM",
                len(prompt), correlation_id
            )
            response = await self.llm_manager.ask_llm(
                prompt, llm_config_name='actions_to_meet_goals'
            )
            log_agent_output(
                "LLM", "ActionsToMeetGoalsSubAgent",
                len(response) if response else 0,
                "success", correlation_id
            )
            return response
        finally:
            stop_llm_heartbeat(correlation_id)

    async def _process_llm_response(
        self, llm_response: str, run_id: str
    ) -> ActionPlanResult:
        """Process LLM response to ActionPlanResult."""
        action_plan_dict = extract_json_from_response(llm_response, max_retries=5)
        if not action_plan_dict:
            action_plan_dict = await self._handle_extraction_failure(
                llm_response, run_id
            )
        return self._convert_to_action_plan_result(action_plan_dict)

    def _convert_to_action_plan_result(self, data: dict) -> ActionPlanResult:
        """Convert dictionary to ActionPlanResult."""
        valid_fields = {
            k: v for k, v in data.items()
            if k in ActionPlanResult.model_fields
        }
        if 'actions' in data and 'plan_steps' not in valid_fields:
            valid_fields['plan_steps'] = self._extract_plan_steps(data)
        return ActionPlanResult(**valid_fields)

    def _extract_plan_steps(self, data: dict) -> list:
        """Extract plan steps from data."""
        steps = data.get('plan_steps', [])
        if not isinstance(steps, list):
            return []
        return [self._create_plan_step(s) for s in steps]

    def _create_plan_step(self, step_data) -> PlanStep:
        """Create PlanStep from data."""
        if isinstance(step_data, str):
            return PlanStep(step_id=str(len(step_data)), description=step_data)
        elif isinstance(step_data, dict):
            return PlanStep(
                step_id=step_data.get('step_id', '1'),
                description=step_data.get('description', 'No description')
            )
        return PlanStep(step_id='1', description='Default step')

    async def _handle_extraction_failure(
        self, llm_response: str, run_id: str
    ) -> dict:
        """Handle JSON extraction failure."""
        logger.debug(f"JSON extraction failed for {run_id}")
        partial = extract_partial_json(llm_response, required_fields=None)
        if partial:
            return self._build_from_partial(partial).model_dump()
        return self._get_default_action_plan().model_dump()

    def _build_from_partial(self, partial: dict) -> ActionPlanResult:
        """Build ActionPlanResult from partial data."""
        base = self._get_base_data()
        base.update({
            k: v for k, v in partial.items()
            if k in ActionPlanResult.model_fields
        })
        base["partial_extraction"] = True
        return ActionPlanResult(**base)

    def _get_base_data(self) -> dict:
        """Get base action plan data."""
        return {
            "action_plan_summary": "Partial extraction - summary unavailable",
            "total_estimated_time": "To be determined",
            "required_approvals": [],
            "actions": [],
            "execution_timeline": [],
            "supply_config_updates": [],
            "post_implementation": {
                "monitoring_period": "30 days",
                "success_metrics": [],
                "optimization_review_schedule": "Weekly",
                "documentation_updates": []
            },
            "cost_benefit_analysis": {
                "implementation_cost": {"effort_hours": 0, "resource_cost": 0},
                "expected_benefits": {
                    "cost_savings_per_month": 0,
                    "performance_improvement_percentage": 0,
                    "roi_months": 0
                }
            }
        }

    def _get_default_action_plan(self) -> ActionPlanResult:
        """Get default action plan for failures."""
        data = self._get_base_data()
        data.update({
            "action_plan_summary": "Failed to generate action plan",
            "total_estimated_time": "Unknown",
            "error": "JSON extraction failed - using default"
        })
        return ActionPlanResult(**data)

    # Legacy compatibility methods
    def _create_main_executor(self, state, run_id, stream_updates):
        """Legacy main executor."""
        async def execute():
            await self._send_processing_update(run_id, stream_updates)
            prompt = self._build_action_plan_prompt(state)
            response = await self._get_llm_response(prompt, run_id)
            result = await self._process_llm_response(response, run_id)
            state.action_plan_result = result
            return result
        return execute

    def _create_fallback_executor(self, state, run_id, stream_updates):
        """Legacy fallback executor."""
        async def fallback():
            plan = self._get_default_action_plan()
            state.action_plan_result = plan
            return plan
        return fallback

    async def _execute_with_protection(self, main, fallback, run_id):
        """Legacy protection wrapper."""
        return await self.fallback_strategy.execute_with_fallback(
            main, fallback, "action_plan_generation", run_id
        )

    async def _apply_reliability_protection(self, result):
        """Legacy reliability wrapper."""
        async def op():
            return result
        await self.reliability.execute_safely(op, "execute", timeout=45.0)

    async def _send_processing_update(self, run_id, stream_updates):
        """Legacy processing update."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Creating action plan..."
            })

    def _log_prompt_size(self, prompt: str, run_id: str):
        """Log large prompt warning."""
        size_mb = len(prompt) / (1024 * 1024)
        if size_mb > 1:
            logger.info(f"Large prompt ({size_mb:.2f}MB) for {run_id}")

    def get_health_status(self) -> dict:
        """Get comprehensive health status."""
        return {
            "agent": self.name,
            "modern_health": self.monitor.get_health_status(),
            "reliability": self.reliability_manager.get_health_status(),
            "legacy_health": self.reliability.get_health_status()
        }

    def get_performance_metrics(self) -> dict:
        """Get performance metrics."""
        return self.monitor.get_agent_metrics(self.name)

    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status."""
        return self.reliability_manager.get_circuit_breaker_status()

    async def check_entry_conditions(
        self, state: DeepAgentState, run_id: str
    ) -> bool:
        """Legacy entry condition check."""
        return state.optimizations_result is not None and state.data_result is not None