
from app.llm.llm_manager import LLMManager
from app.services.deep_agent_v3.tools.log_fetcher import LogFetcher
from app.services.deep_agent_v3.tools.log_pattern_identifier import LogPatternIdentifier
from app.services.deep_agent_v3.tools.policy_proposer import PolicyProposer
from app.services.deep_agent_v3.tools.policy_simulator import PolicySimulator
from app.services.deep_agent_v3.tools.supply_catalog_search import SupplyCatalogSearch
from app.services.deep_agent_v3.tools.cost_estimator import CostEstimator
from app.services.deep_agent_v3.tools.performance_predictor import PerformancePredictor

class ToolBuilder:
    @staticmethod
    def build_all(db_session: any, llm_manager: LLMManager) -> Dict[str, Any]:
        return {
            "log_fetcher": LogFetcher(db_session),
            "log_pattern_identifier": LogPatternIdentifier(llm_manager),
            "policy_proposer": PolicyProposer(db_session, llm_manager),
            "policy_simulator": PolicySimulator(llm_manager),
            "supply_catalog_search": SupplyCatalogSearch(db_session),
            "cost_estimator": CostEstimator(llm_manager),
            "performance_predictor": PerformancePredictor(llm_manager),
        }
