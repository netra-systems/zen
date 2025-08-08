from typing import Any, List, Dict
from app.schemas import Log
from app.agents.state import DeepAgentState
from app.services.supply_catalog_service import SupplyCatalogService

class ToolContext:
    def __init__(self, db_session: Any, llm_manager: Any, cost_estimator: Any, state: DeepAgentState, supply_catalog: SupplyCatalogService, logs: List[Log] = None):
        self.logs = logs if logs is not None else []
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.cost_estimator = cost_estimator
        self.supply_catalog = supply_catalog
        self.state = state

    def __post_init__(self):
        self.state = DeepAgentState()