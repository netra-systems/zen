from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import Log
from app.agents.state import DeepAgentState
from app.services.supply_catalog_service import SupplyCatalogService
from app.llm.llm_manager import LLMManager

if TYPE_CHECKING:
    from app.services.apex_optimizer_agent.tools.cost_estimator import CostEstimator

class ToolContext:
    def __init__(
        self,
        db_session: AsyncSession,
        llm_manager: LLMManager,
        cost_estimator: "CostEstimator",
        state: DeepAgentState,
        supply_catalog: SupplyCatalogService,
        logs: Optional[List[Log]] = None
    ) -> None:
        self.logs = logs if logs is not None else []
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.cost_estimator = cost_estimator
        self.supply_catalog = supply_catalog
        self.state = state

    def __post_init__(self):
        # Only create a new state if one wasn't provided
        if not hasattr(self, 'state') or self.state is None:
            self.state = DeepAgentState(user_request="tool_context_operation")