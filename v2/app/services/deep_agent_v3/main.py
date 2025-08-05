import json
import io
from typing import Any
from langfuse import Langfuse, observe

from app.db.models_clickhouse import AnalysisRequest
from app.db.models_postgres import DeepAgentRun
from app.services.deep_agent_v3.state import AgentState
from app.config import settings
from app.logging_config_custom.logger import app_logger
from app.services.deep_agent_v3.tools.log_fetcher import LogFetcher
from app.services.deep_agent_v3.tools.log_pattern_identifier import LogPatternIdentifier
from app.services.deep_agent_v3.tools.policy_proposer import PolicyProposer
from app.services.deep_agent_v3.tools.policy_simulator import PolicySimulator
from app.services.deep_agent_v3.tools.supply_catalog_search import SupplyCatalogSearch
from app.services.deep_agent_v3.tools.cost_estimator import CostEstimator
from app.services.deep_agent_v3.tools.performance_predictor import PerformancePredictor
from app.services.deep_agent_v3.pipeline import Pipeline
from app.services.deep_agent_v3.steps.fetch_raw_logs import fetch_raw_logs
from app.services.deep_agent_v3.steps.enrich_and_cluster import enrich_and_cluster
from app.services.deep_agent_v3.steps.propose_optimal_policies import propose_optimal_policies
from app.services.deep_agent_v3.steps.generate_final_report import generate_final_report

class DeepAgentV3:
    """
    A stateful, step-by-step agent for conducting deep analysis of LLM usage.
    This engine is designed for interactive control, monitoring, and extensibility.
    """

    def __init__(self, run_id: str, request: AnalysisRequest, db_session: Any, llm_connector: any):
        self.run_id = run_id
        self.request = request
        self.db_session = db_session
        self.llm_connector = llm_connector
        self.state = AgentState(messages=[])
        self.log_stream = io.StringIO()
        self.langfuse = None
        if settings.langfuse.secret_key and settings.langfuse.public_key and settings.langfuse.host:
            self.langfuse = Langfuse(
                secret_key=settings.langfuse.secret_key,
                public_key=settings.langfuse.public_key,
                host=settings.langfuse.host
            )

        self.tools = {
            "log_fetcher": LogFetcher(self.db_session),
            "log_pattern_identifier": LogPatternIdentifier(self.llm_connector),
            "policy_proposer": PolicyProposer(self.db_session, self.llm_connector),
            "policy_simulator": PolicySimulator(self.llm_connector),
            "supply_catalog_search": SupplyCatalogSearch(self.db_session),
            "cost_estimator": CostEstimator(self.llm_connector),
            "performance_predictor": PerformancePredictor(self.llm_connector),
        }

        self.pipeline = Pipeline(steps=[
            fetch_raw_logs,
            enrich_and_cluster,
            propose_optimal_policies,
            generate_final_report,
        ])
        self.status = "in_progress"
        app_logger.info(f"DeepAgentV3 initialized for run_id: {self.run_id}")

    @observe()
    async def run_full_analysis(self):
        """Executes the entire analysis pipeline from start to finish."""
        app_logger.info(f"Starting full analysis for run_id: {self.run_id}")
        while not self.pipeline.is_complete():
            result = await self.run_next_step()
            if result["status"] == "failed":
                self.status = "failed"
                app_logger.error(f"Full analysis failed for run_id: {self.run_id} at step: {result.get('step')}")
                return result
        
        self.status = "complete"
        app_logger.info(f"Full analysis completed for run_id: {self.run_id}")
        if self.langfuse:
            self.langfuse.flush()
        return self.state.final_report

    @observe()
    async def run_next_step(self, confirmation: bool = True):
        """Executes the next step in the analysis pipeline."""
        if self.pipeline.is_complete():
            return {"status": "complete", "message": "Analysis is already complete."}

        if self.status == "awaiting_confirmation" and not confirmation:
            return {"status": "awaiting_confirmation", "message": "Awaiting user confirmation to proceed."}

        step_name = self.pipeline.steps[self.pipeline.current_step_index].__name__
        app_logger.info(f"Running step: {step_name} for run_id: {self.run_id}")

        input_data = self.state.model_dump()
        result = await self.pipeline.run_next_step(self.state, self.tools, self.request)
        output_data = self.state.model_dump()

        self._record_step_history(result.get("completed_step"), input_data, output_data)

        if result["status"] == "failed":
            self.status = "failed"
            app_logger.error(f"Step {step_name} failed for run_id: {self.run_id}. Error: {result.get('error')}")
        elif self.pipeline.is_complete():
            self.status = "complete"
            app_logger.info(f"Pipeline completed for run_id: {self.run_id}")
        else:
            self.status = "awaiting_confirmation"
            app_logger.info(f"Step {step_name} completed for run_id: {self.run_id}. Awaiting confirmation.")
        
        if self.langfuse:
            self.langfuse.flush()

        return result

    def _record_step_history(self, step_name: str, input_data: dict, output_data: dict):
        if not step_name:
            return
        
        log_contents = self.log_stream.getvalue()
        self.log_stream.truncate(0)
        self.log_stream.seek(0)

        new_run = DeepAgentRun(
            run_id=self.run_id,
            step_name=step_name,
            step_input=input_data,
            step_output=output_data,
            run_log=log_contents
        )
        self.db_session.add(new_run)
        self.db_session.commit()
        app_logger.info(f"Recorded history for step: {step_name} for run_id: {self.run_id}")

    def is_complete(self) -> bool:
        """Checks if the analysis has completed all steps."""
        return self.pipeline.is_complete()
