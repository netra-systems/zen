from typing import Any, List, Dict
from app.models.schemas import Log
from app.services.deepagents.state import DeepAgentState

class ToolContext:
    def __init__(self, db_session: Any, llm_manager: Any, cost_estimator: Any, state: DeepAgentState, logs: List[Log] = None):
        self.logs = logs if logs is not None else []
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.cost_estimator = cost_estimator
        self.state = state