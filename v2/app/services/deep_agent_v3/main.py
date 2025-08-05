import io
from typing import Any, Dict, List
from langfuse import Langfuse, observe
import json
from datetime import datetime, timezone

from app.db.models_clickhouse import AnalysisRequest
from app.db.models_postgres import DeepAgentRun
from app.services.deep_agent_v3.state import AgentState
from app.config import settings
from app.logging_config_custom.logger import app_logger
from app.services.deep_agent_v3.core import AgentCore
from app.services.deep_agent_v3.scenario_finder import ScenarioFinder
from app.services.deep_agent_v3.tool_builder import ToolBuilder
from app.db.session import get_db_session

class DeepAgentV3:
    """
    A stateful, agentic system for conducting deep analysis of LLM usage.
    This engine is designed for interactive control, monitoring, and extensibility.
    """

    def __init__(self, run_id: str, request: AnalysisRequest, db_session: Any, llm_connector: any):
        self.run_id = run_id
        self.request = request
        self.db_session = db_session
        self.llm_connector = llm_connector
        self.state = AgentState(messages=[], current_step=None)
        self.langfuse = self._init_langfuse()
        self.tools = self._init_tools()
        self.agent_core = AgentCore(self.llm_connector, list(self.tools.values()))
        self.triage_result: Dict[str, Any] | None = None
        self.status = "starting"
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

    @observe()
    async def run(self):
        """Executes the agentic workflow."""
        app_logger.info(f"Starting agent run for run_id: {self.run_id}")
        self.status = "in_progress"

        try:
            # 1. Triage
            self.state.current_step = "triage"
            scenario_finder = ScenarioFinder(self.llm_connector)
            self.triage_result = scenario_finder.find_scenario(self.request.query)
            scenario = self.triage_result["scenario"]
            app_logger.info(f"Scenario selected for run_id {self.run_id}: "
                            f"Name='{scenario['name']}', "
                            f"Confidence={self.triage_result['confidence']}, "
                            f"Justification='{self.triage_result['justification']}'")
            self.state.messages.append({"role": "assistant", "content": f"Scenario identified: {scenario['name']}"})


            # 2. Execute based on scenario
            steps = scenario["steps"]

            for step in steps:
                self.state.current_step = step
                tool_name = step
                if tool_name not in self.tools:
                    app_logger.warning(f"Tool '{tool_name}' not found in available tools. Skipping step.")
                    continue

                next_step = self.agent_core.decide_next_step(self.state, [tool_name])
                if not next_step:
                    break

                tool_input = next_step["tool_input"]
                
                app_logger.info(f"Executing tool: {tool_name} for run_id: {self.run_id}")
                
                # Execute the tool
                tool_function = self.tools[tool_name]
                # This is a simplified execution. A real implementation would handle async and tool arguments better.
                result = tool_function.run(state=self.state, **tool_input) 

                self.state.messages.append({"role": "tool", "name": tool_name, "content": result})
                await self._record_step_history(tool_name, tool_input, self.state.model_dump(), {"status": "success", "result": result})


            self.status = "complete"
            self.state.current_step = "complete"
            app_logger.info(f"Agent run completed for run_id: {self.run_id}")
            await self._generate_and_save_run_report()

        except Exception as e:
            self.status = "failed"
            self.state.current_step = "failed"
            app_logger.error(f"An unexpected error occurred during agent run for run_id: {self.run_id}. Error: {e}")
            await self._generate_and_save_run_report()
        finally:
            if self.langfuse:
                self.langfuse.flush()
        
        return self.state


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
                run_log=json.dumps(log_message),
                timestamp=datetime.now(timezone.utc)
            )
            db_session.add(new_run)

    async def _generate_and_save_run_report(self):
        """Generates a markdown report of the entire run and saves it to the database."""
        from sqlmodel import select

        report = f"# Deep Agent Run Report: {self.run_id}\n\n"
        report += f"**Status:** {self.status}\n\n"
        
        if self.triage_result:
            report += "## Triage\n\n"
            report += f"**Scenario:** {self.triage_result['scenario']['name']}\n"
            report += f"**Confidence:** {self.triage_result['confidence']}\n"
            report += f"**Justification:** {self.triage_result['justification']}\n\n"

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
        """Checks if the analysis has completed."""
        return self.status == "complete" or self.status == "failed"