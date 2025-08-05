from typing import List, Any
from app.db.models_clickhouse import UnifiedLogEntry
from app.schema import DiscoveredPattern
from app.services.deep_agent_v3.core import enrich_and_cluster_logs

class LogPatternIdentifier:
    def __init__(self, llm_connector: Any):
        self.llm_connector = llm_connector

    async def execute(
        self, spans: List[UnifiedLogEntry], n_patterns: int = 5
    ) -> List[DiscoveredPattern]:
        return await enrich_and_cluster_logs(spans, n_patterns, self.llm_connector)