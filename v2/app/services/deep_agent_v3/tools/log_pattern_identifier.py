
from app.services.deep_agent_v3.core import enrich_and_cluster_logs

class LogPatternIdentifier:
    def __init__(self, llm_connector):
        self.llm_connector = llm_connector

    async def execute(self, spans: list, n_patterns: int):
        return await enrich_and_cluster_logs(spans, n_patterns, self.llm_connector)
