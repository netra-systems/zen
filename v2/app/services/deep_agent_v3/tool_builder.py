
from typing import Any, Dict
from app.services.deep_agent_v3.tools.log_fetcher import LogFetcher
from app.services.deep_agent_v3.tools.log_pattern_identifier import LogPatternIdentifier
from app.services.deep_agent_v3.tools.policy_proposer import PolicyProposer
from app.services.deep_agent_v3.tools.policy_simulator import PolicySimulator
from app.services.deep_agent_v3.tools.supply_catalog_search import SupplyCatalogSearch
from app.services.deep_agent_v3.tools.cost_estimator import CostEstimator
from app.services.deep_agent_v3.tools.performance_predictor import PerformancePredictor

class ToolBuilder:
    @staticmethod
    def build_all(db_session: Any, llm_connector: any) -> Dict[str, Any]:
        return {
            "log_fetcher": LogFetcher(db_session),
            "log_pattern_identifier": LogPatternIdentifier(llm_connector),
            "policy_proposer": PolicyProposer(db_session, llm_connector),
            "policy_simulator": PolicySimulator(llm_connector),
            "supply_catalog_search": SupplyCatalogSearch(db_session),
            "cost_estimator": CostEstimator(llm_connector),
            "performance_predictor": PerformancePredictor(llm_connector),
        }
