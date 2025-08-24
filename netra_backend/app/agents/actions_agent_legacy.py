"""Legacy compatibility layer for ActionsToMeetGoalsSubAgent following SRP."""

from netra_backend.app.agents.actions_goals_plan_builder import ActionPlanBuilder
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.fallback_utils import create_agent_fallback_strategy
from netra_backend.app.core.reliability_utils import create_agent_reliability_wrapper


class ActionsAgentLegacyCompat:
    """Provides backward compatibility for legacy execution patterns."""

    def __init__(self):
        """Initialize legacy compatibility layer."""
        self._setup_legacy_infrastructure()

    def _setup_legacy_infrastructure(self) -> None:
        """Setup legacy infrastructure components."""
        agent_name = "ActionsToMeetGoalsSubAgent"
        self.reliability = create_agent_reliability_wrapper(agent_name)
        self.fallback_strategy = create_agent_fallback_strategy(agent_name)

    async def execute_fallback_workflow(
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

    def _create_main_executor(self, state, run_id, stream_updates):
        """Legacy main executor."""
        async def execute():
            await self._send_processing_update(run_id, stream_updates)
            # This would need to be connected to the actual prompt building and LLM
            plan = ActionPlanBuilder.get_default_action_plan()
            state.action_plan_result = plan
            return plan
        return execute

    def _create_fallback_executor(self, state, run_id, stream_updates):
        """Legacy fallback executor."""
        async def fallback():
            plan = ActionPlanBuilder.get_default_action_plan()
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

    async def _send_update(self, run_id: str, update_data: dict) -> None:
        """Send update via WebSocket - placeholder for actual implementation."""
        # This would connect to the actual WebSocket service
        pass

    def get_health_status(self) -> dict:
        """Get legacy compatibility health status."""
        return {
            "service": "legacy_compat",
            "status": "healthy",
            "reliability": self.reliability.get_health_status()
        }