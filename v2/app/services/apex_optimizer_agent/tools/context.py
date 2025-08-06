from typing import Any, List
from app.models.schemas import Log

class ToolContext:
    def __init__(self, logs: List[Log], db_session: Any, llm_manager: Any, cost_estimator: Any):
        self.logs = logs
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.cost_estimator = cost_estimator
