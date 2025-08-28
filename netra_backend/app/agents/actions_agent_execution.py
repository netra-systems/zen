"""Execution manager for ActionsToMeetGoalsSubAgent following SRP."""

from typing import Any, Dict

from netra_backend.app.agents.actions_goals_plan_builder import ActionPlanBuilder
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.errors import ValidationError
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.state import ActionPlanResult, DeepAgentState
from netra_backend.app.core.fallback_utils import create_agent_fallback_strategy
from netra_backend.app.core.reliability_utils import create_agent_reliability_wrapper
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.shared_types import RetryConfig


class ActionsAgentExecutionManager:
    """Manages execution flow and infrastructure for the Actions agent."""
    
    def __init__(self):
        """Initialize execution infrastructure."""
        self._setup_modern_execution_infrastructure()
        self._setup_backward_compatibility()

    def _setup_modern_execution_infrastructure(self) -> None:
        """Setup modern execution infrastructure components."""
        self.monitor = ExecutionMonitor()
        self.reliability_manager = self._create_reliability_manager()
        self.execution_engine = BaseExecutionEngine(
            self.reliability_manager, self.monitor
        )
        self.error_handler = ExecutionErrorHandler()

    def _create_reliability_manager(self) -> ReliabilityManager:
        """Create configured reliability manager."""
        return ReliabilityManager(
            circuit_breaker_config=CircuitBreakerConfig(
                name="ActionsToMeetGoalsSubAgent",
                failure_threshold=5,
                recovery_timeout=60
            ),
            retry_config=RetryConfig(
                max_retries=3,
                base_delay=1.0
            )
        )

    def _setup_backward_compatibility(self) -> None:
        """Setup backward compatibility components."""
        agent_name = "ActionsToMeetGoalsSubAgent"
        self.reliability = create_agent_reliability_wrapper(agent_name)
        self.fallback_strategy = create_agent_fallback_strategy(agent_name)

    def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions."""
        state = context.state
        if not state.optimizations_result or not state.data_result:
            raise ValidationError(
                "Missing required state: optimizations_result and data_result required"
            )
        return True

    async def execute_core_logic(
        self, context: ExecutionContext,
        monitoring_service, llm_handler
    ) -> Dict[str, Any]:
        """Execute core action plan generation logic."""
        await monitoring_service.send_execution_start_update(context)
        action_plan_result = await self._execute_action_plan_generation(
            context, llm_handler
        )
        await self._update_state_and_notify(
            context, action_plan_result, monitoring_service
        )
        return {"action_plan_result": action_plan_result}

    async def _execute_action_plan_generation(
        self, context: ExecutionContext, llm_handler
    ) -> ActionPlanResult:
        """Generate action plan from state data."""
        state = context.state
        run_id = context.run_id
        prompt = self._build_action_plan_prompt(state)
        llm_response = await llm_handler.get_llm_response(prompt, run_id)
        return await self._process_llm_response(llm_response, run_id)

    def _build_action_plan_prompt(self, state: DeepAgentState) -> str:
        """Build prompt for action plan generation."""
        from netra_backend.app.agents.prompts import actions_to_meet_goals_prompt_template
        return actions_to_meet_goals_prompt_template.format(
            optimizations=state.optimizations_result,
            data=state.data_result,
            user_request=state.user_request
        )

    async def _process_llm_response(
        self, llm_response: str, run_id: str
    ) -> ActionPlanResult:
        """Process LLM response to ActionPlanResult."""
        return await ActionPlanBuilder.process_llm_response(llm_response, run_id)

    async def _update_state_and_notify(
        self, context: ExecutionContext, 
        action_plan_result: ActionPlanResult,
        monitoring_service
    ) -> None:
        """Update state with result and send completion notification."""
        context.state.action_plan_result = action_plan_result
        await monitoring_service.send_completion_update(context)

    async def execute_with_fallback(
        self, context: ExecutionContext
    ) -> None:
        """Execute with modern pattern."""
        await self._execute_with_modern_pattern(context)

    async def _execute_with_modern_pattern(self, context: ExecutionContext) -> None:
        """Execute using modern execution pattern."""
        result = await self.execution_engine.execute(self, context)
        if not result.success:
            await self._handle_execution_failure(result, context.state, context.run_id)

    async def _handle_execution_failure(
        self, result: ExecutionResult,
        state: DeepAgentState, run_id: str
    ) -> None:
        """Handle execution failure with fallback."""
        logger.error(f"Execution failed: {result.error}")
        fallback_plan = ActionPlanBuilder.get_default_action_plan()
        state.action_plan_result = fallback_plan

    def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check entry conditions for execution."""
        return (state.optimizations_result is not None and 
                state.data_result is not None)

    def get_health_status(self) -> dict:
        """Get execution manager health status."""
        return {
            "monitor": self.monitor.get_health_status(),
            "reliability": self.reliability_manager.get_health_status()
        }

    def get_performance_metrics(self) -> dict:
        """Get performance metrics."""
        return self.monitor.get_agent_metrics("ActionsToMeetGoalsSubAgent")

    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status."""
        return self.reliability_manager.get_circuit_breaker_status()