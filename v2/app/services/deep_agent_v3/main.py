import io
from typing import Any, Dict
from langfuse import Langfuse, observe
import json

from app.db.models_clickhouse import AnalysisRequest
from app.db.models_postgres import DeepAgentRun
from app.services.deep_agent_v3.state import AgentState
from app.config import settings
from app.logging_config_custom.logger import app_logger
from app.services.deep_agent_v3.pipeline import Pipeline
from app.services.deep_agent_v3.scenario_finder import ScenarioFinder
from app.services.deep_agent_v3.steps import ALL_STEPS
from app.services.deep_agent_v3.tool_builder import ToolBuilder
from app.db.session import get_db_session

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
        self.langfuse = self._init_langfuse()
        self.tools = self._init_tools()
        self.pipeline = self._init_pipeline()
        self.status = "in_progress"
        app_logger.info(f"DeepAgentV3 initialized for run_id: {self.run_id}")

    def _init_langfuse(self):
        if settings.langfuse.secret_key and settings.langfuse.public_key and settings.langfuse.host:
            return Langfuse(
                secret_key=settings.langfuse.secret_key,
                public_key=settings.langfuse.public_key,
                host=settings.langfuse.host
            )
        return None

    def _init_tools(self) -> Dict[str, Any]:
        return ToolBuilder.build_all(self.db_session, self.llm_connector)

    def _init_pipeline(self) -> Pipeline:
        scenario_finder = ScenarioFinder(self.llm_connector)
        prompt = self.request.workloads[0].get("query", "")
        scenario = scenario_finder.find_scenario(prompt)
        step_functions = [ALL_STEPS[step_name] for step_name in scenario["steps"] if step_name in ALL_STEPS]
        return Pipeline(steps=step_functions)

    @observe()
    async def run_full_analysis(self) -> AgentState:
        """Executes the entire analysis pipeline from start to finish."""
        app_logger.info(f"Starting full analysis for run_id: {self.run_id}")
        try:
            while not self.pipeline.is_complete():
                result = await self.run_next_step()
                if result["status"] == "failed":
                    self.status = "failed"
                    app_logger.error(f"Full analysis failed for run_id: {self.run_id} at step: {result.get('step')}")
                    await self._generate_and_save_run_report()
                    return self.state
            
            self.status = "complete"
            app_logger.info(f"Full analysis completed for run_id: {self.run_id}")
            await self._generate_and_save_run_report()
        except Exception as e:
            self.status = "failed"
            app_logger.error(f"An unexpected error occurred during full analysis for run_id: {self.run_id}. Error: {e}")
            await self._generate_and_save_run_report()
        finally:
            if self.langfuse:
                self.langfuse.flush()
        
        return self.state

    @observe()
    async def run_next_step(self, confirmation: bool = True):
        """Executes the next step in the analysis pipeline."""
        if self.pipeline.is_complete():
            return {"status": "complete", "message": "Analysis is already complete."}

        if self.status == "awaiting_confirmation" and not confirmation:
            return {"status": "awaiting_confirmation", "message": "Awaiting user confirmation to proceed."}

        step_name = self.pipeline.get_current_step_name()
        app_logger.info(f"Running step: {step_name} for run_id: {self.run_id}")

        input_data = self.state.model_dump()
        result = await self.pipeline.run_next_step(self.state, self.tools, self.request)
        output_data = self.state.model_dump()

        await self._record_step_history(result.get("completed_step"), input_data, output_data, result)

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

    async def _record_step_history(self, step_name: str, input_data: dict, output_data: dict, result: dict):
        if not step_name:
            return
        
        log_message = {
            "run_id": self.run_id,
            "step_name": step_name,
            "status": result.get("status"),
            "result": result.get("result"),
            "error": result.get("error"),
        }
        app_logger.info(json.dumps(log_message))

        async with get_db_session() as db_session:
            new_run = DeepAgentRun(
                run_id=self.run_id,
                step_name=step_name,
                step_input=input_data,
                step_output=output_data,
                run_log=json.dumps(log_message)
            )
            db_session.add(new_run)

    async def _generate_and_save_run_report(self):
        """Generates a markdown report of the entire run and saves it to the database."""
        from sqlmodel import select

        report = f"# Deep Agent Run Report: {self.run_id}\n\n"
        report += f"**Status:** {self.status}\n\n"
        report += "## Steps\n\n"

        async with get_db_session() as db_session:
            runs_result = await db_session.execute(select(DeepAgentRun).where(DeepAgentRun.run_id == self.run_id))
            runs = runs_result.scalars().all()
            for run in runs:
                report += f"### {run.step_name}\n\n"
                report += f"**Status:** {json.loads(run.run_log).get('status')}\n\n"
                result = json.loads(run.run_log).get('result')
                if isinstance(result, (dict, list)):
                    report += f"**Result:**\n```json\n{json.dumps(result, indent=2)}\n```\n\n"
                else:
                    report += f"**Result:**\n{result}\n\n"
                if json.loads(run.run_log).get('error'):
                    report += f"**Error:**\n```\n{json.loads(run.run_log).get('error')}\n```\n\n"

            final_run_result = await db_session.execute(select(DeepAgentRun).where(DeepAgentRun.run_id == self.run_id).order_by(DeepAgentRun.timestamp.desc()))
            final_run = final_run_result.scalar_one_or_none()
            if final_run:
                final_run.run_report = report

    def is_complete(self) -> bool:
        """Checks if the analysis has completed all steps."""
        return self.status == "complete" or self.status == "failed"