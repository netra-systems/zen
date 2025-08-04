
from app.services.deep_agent_v3.core import propose_optimal_policies

class PolicyProposer:
    def __init__(self, db_session, llm_connector):
        self.db_session = db_session
        self.llm_connector = llm_connector

    async def execute(self, patterns: list, span_map: dict):
        return await propose_optimal_policies(self.db_session, patterns, span_map, self.llm_connector)
