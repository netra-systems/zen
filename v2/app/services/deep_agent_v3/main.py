import json
from typing import Any, Callable
from langfuse import Langfuse

from app.db.models_clickhouse import AnalysisRequest
from app.db.models_postgres import DeepAgentRun
from app.services.deep_agent_v3.state import AgentState
from app.services.deep_agent_v3.steps import (
    _step_1_fetch_raw_logs,
    _step_2_enrich_and_cluster,
    _step_3_propose_optimal_policies,
    _step_4_dispatch_tool,
    _step_5_generate_final_report,
)
from app.config import settings

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
        self.langfuse = Langfuse(
            secret_key=settings.langfuse.secret_key,
            public_key=settings.langfuse.public_key,
            host=settings.langfuse.host
        )

        self.steps = [
            self.step_1_fetch_raw_logs,
            self.step_2_enrich_and_cluster,
            self.step_3_propose_optimal_policies,
            self.step_4_dispatch_tool,
            self.step_5_generate_final_report,
        ]
        self.current_step_index = 0
        self.status = "in_progress"

    async def run_full_analysis(self):
        """Executes the entire analysis pipeline from start to finish."""
        trace = self.langfuse.trace(id=self.run_id, name="FullAnalysis")
        
        for step_func in self.steps:
            await self._execute_step(step_func, trace)
        
        self.status = "complete"
        return self.state.final_report

    async def run_next_step(self, confirmation: bool = True):
        """Executes the next step in the analysis pipeline."""
        if self.is_complete():
            return {"status": "complete", "message": "Analysis is already complete."}

        if self.status == "awaiting_confirmation" and not confirmation:
            return {"status": "awaiting_confirmation", "message": "Awaiting user confirmation to proceed."}

        step_func = self.steps[self.current_step_index]
        trace = self.langfuse.trace(id=f"{self.run_id}-{self.current_step_index}", name=step_func.__name__)

        result = await self._execute_step(step_func, trace)
        self.current_step_index += 1

        if self.is_complete():
            self.status = "complete"
        else:
            self.status = "awaiting_confirmation"

        return result

    async def _execute_step(self, step_func: Callable, trace: Any):
        step_name = step_func.__name__
        span = trace.span(name=step_name)

        try:
            input_data = self.state.model_dump() # Capture state before the step
            result_message = await step_func(self.state, self.db_session, self.llm_connector)
            output_data = self.state.model_dump() # Capture state after the step

            span.end(output=output_data)
            self._record_step_history(step_name, input_data, output_data)

            return {"status": "awaiting_confirmation", "completed_step": step_name, "result": result_message}
        except Exception as e:
            span.end(level="ERROR", status_message=str(e))
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

    async def step_1_fetch_raw_logs(self, state, db_session, llm_connector):
        return await _step_1_fetch_raw_logs(state, db_session)

    async def step_2_enrich_and_cluster(self, state, db_session, llm_connector):
        return await _step_2_enrich_and_cluster(state, llm_connector)

    async def step_3_propose_optimal_policies(self, state, db_session, llm_connector):
        return await _step_3_propose_optimal_policies(state, db_session, llm_connector)

    async def step_4_dispatch_tool(self, state, db_session, llm_connector):
        return await _step_4_dispatch_tool(state, llm_connector)

    async def step_5_generate_final_report(self, state, db_session, llm_connector):
        return await _step_5_generate_final_report(state)
