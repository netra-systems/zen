
from typing import Any, Dict
from app.schema import DiscoveredPattern, PredictedOutcome
from app.db.models_postgres import SupplyOption
from app.services.deep_agent_v3.core import simulate_policy_outcome

class PolicySimulator:
    def __init__(self, llm_connector: Any):
        self.llm_connector = llm_connector

    async def execute(
        self, pattern: DiscoveredPattern, supply_option: SupplyOption, user_goal: str, span: Dict[str, Any]
    ) -> PredictedOutcome:
        return await simulate_policy_outcome(
            pattern, supply_option, user_goal, self.llm_connector, span
        )
