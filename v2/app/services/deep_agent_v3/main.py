import json
from typing import Any, Callable
from langfuse import Langfuse, observe

from app.db.models_clickhouse import AnalysisRequest
from app.db.models_postgres import DeepAgentRun
from app.services.deep_agent_v3.state import AgentState
from app.config import settings
from app.services.deep_agent_v3.tools.log_fetcher import LogFetcher
from app.services.deep_agent_v3.tools.log_pattern_identifier import LogPatternIdentifier
from app.services.deep_agent_v3.tools.policy_proposer import PolicyProposer
from app.services.deep_agent_v3.tools.policy_simulator import PolicySimulator
from app.services.deep_agent_v3.tools.supply_catalog_search import SupplyCatalogSearch
from app.services.deep_agent_v3.tools.cost_estimator import CostEstimator
from app.services.deep_agent_v3.tools.performance_predictor import PerformancePredictor

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

        self.steps = [
            self.fetch_raw_logs,
            self.enrich_and_cluster,
            self.propose_optimal_policies,
            self.generate_final_report,
        ]
        self.current_step_index = 0
        self.status = "in_progress"

    @observe()
    async def run_full_analysis(self):
        """Executes the entire analysis pipeline from start to finish."""
        for step_func in self.steps:
            result = await self._execute_step(step_func)
            if result["status"] == "failed":
                self.status = "failed"
                return result
            self.current_step_index += 1
        
        self.status = "complete"
        if self.langfuse:
            self.langfuse.flush()
        return self.state.final_report

    @observe()
    async def run_next_step(self, confirmation: bool = True):
        """Executes the next step in the analysis pipeline."""
        if self.is_complete():
            return {"status": "complete", "message": "Analysis is already complete."}

        if self.status == "awaiting_confirmation" and not confirmation:
            return {"status": "awaiting_confirmation", "message": "Awaiting user confirmation to proceed."}

        step_func = self.steps[self.current_step_index]

        result = await self._execute_step(step_func)
        self.current_step_index += 1

        if self.is_complete():
            self.status = "complete"
        else:
            self.status = "awaiting_confirmation"
        if self.langfuse:
            self.langfuse.flush()

        return result

    @observe()
    async def _execute_step(self, step_func: Callable):
        step_name = step_func.__name__

        try:
            input_data = self.state.model_dump() # Capture state before the step
            result_message = await step_func(self.state)
            output_data = self.state.model_dump() # Capture state after the step

            self._record_step_history(step_name, input_data, output_data)

            return {"status": "awaiting_confirmation", "completed_step": step_name, "result": result_message}
        except Exception as e:
            self.status = "failed"
            return {"status": "failed", "step": step_name, "error": str(e)}

    def _record_step_history(self, step_name: str, input_data: dict, output_data: dict):
        new_run = DeepAgentRun(
            run_id=self.run_id,
            step_name=step_name,
            step_input=input_data,
            step_output=output_data,
        )
        self.db_session.add(new_run)
        self.db_session.commit()

    def is_complete(self) -> bool:
        """Checks if the analysis has completed all steps."""
        return self.current_step_index >= len(self.steps)

    async def fetch_raw_logs(self, state):
        tool = self.tools["log_fetcher"]
        state.raw_logs = await tool.execute(
            source_table=self.request.data_source["source_table"],
            start_time=self.request.time_range["start_time"],
            end_time=self.request.time_range["end_time"],
        )
        return f"Fetched {len(state.raw_logs)} raw logs."

    async def enrich_and_cluster(self, state):
        tool = self.tools["log_pattern_identifier"]
        state.patterns = await tool.execute(state.raw_logs, n_patterns=5) # Assuming n_patterns=5 for now
        state.span_map = {span.trace_context['span_id']: span for span in state.raw_logs}
        return f"Identified {len(state.patterns)} patterns."

    async def propose_optimal_policies(self, state):
        tool = self.tools["policy_proposer"]
        state.policies = await tool.execute(state.patterns, state.span_map)
        return f"Proposed {len(state.policies)} policies."

    async def generate_final_report(self, state):
        # Placeholder for final report generation
        state.final_report = "Analysis Complete. Final report to be generated."
        return state.final_report