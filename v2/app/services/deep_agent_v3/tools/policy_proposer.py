from typing import List, Dict, Any
from app.db.models_clickhouse import UnifiedLogEntry
from app.schema import DiscoveredPattern, LearnedPolicy
from app.services.deep_agent_v3.core import propose_optimal_policies

class PolicyProposer:
    def __init__(self, db_session: Any, llm_connector: Any):
        self.db_session = db_session
        self.llm_connector = llm_connector

    async def execute(
        self, patterns: List[DiscoveredPattern], span_map: Dict[str, UnifiedLogEntry]
    ) -> List[LearnedPolicy]:
        return await propose_optimal_policies(
            self.db_session, patterns, span_map, self.llm_connector
        )