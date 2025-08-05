import io
from typing import Any, Dict, List
from langfuse import Langfuse, observe
import json
from datetime import datetime, timezone

from app.config import settings
from app.db.models_clickhouse import AnalysisRequest
from app.db.models_postgres import DeepAgentRun, DeepAgentRunReport
from app.services.apex_optimizer_agent.state import AgentState
from app.llm.llm_manager import LLMManager
from app.logging_config_custom.logger import app_logger
from app.services.apex_optimizer_agent.triage import Triage
from app.services.apex_optimizer_agent.tool_builder import ToolBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

class NetraOptimizerAgent:
    """
    A stateful, agentic system for conducting deep analysis of LLM usage.
    This engine is designed for interactive control, monitoring, and extensibility.
    """

    def __init__(self, run_id: str, request: AnalysisRequest, db_session: AsyncSession, llm_manager: LLMManager, triage: Triage = None):
        self.run_id = run_id
        self.request = request
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.state = AgentState(messages=[], current_step=None)
        self.langfuse = self._init_langfuse()
        self.all_tools, self.super_tools = self._init_tools()
        self.triage = triage or Triage(self.llm_manager)
        self.triage_result: Dict[str, Any] | None = None
        self.status = "starting"
        app_logger.info(f"NetraOptimizerAgent initialized for run_id: {self.run_id}")

    def _init_langfuse(self):
        """Initializes the Langfuse client if configured."""
        if settings.langfuse and settings.langfuse.public_key and settings.langfuse.secret_key:
            try:
                return Langfuse(
                    public_key=settings.langfuse.public_key,
                    secret_key=settings.langfuse.secret_key,
                    host=settings.langfuse.host,
                )
            except Exception as e:
                app_logger.error(f"Failed to initialize Langfuse: {e}")
                return None
        return None

    def _init_tools(self) -> (Dict[str, Any], Dict[str, Any]):
        return ToolBuilder.build_all(self.db_session, self.llm_manager)

    @observe()
    async def start_agent(self):
        """Executes the agentic workflow."""
        app_logger.info(f"Starting agent run for run_id: {self.run_id}")
        self.status = "in_progress"

        try:
            # 1. Triage
            self.state.current_step = "triage"
            self.triage_result = await self.triage.triage_request(self.request.query)
            
            triage_category = self.triage_result.get("triage_category")

            # Continue with the agentic workflow using the selected tools
            next_step = self.UPDATE_THIS_NAME.decide_next_step(self.state, list(self.UPDATE_THIS_NAME.tools.keys()))
            tool_name = next_step["tool_name"]
            tool_input = next_step["tool_input"]
            
            app_logger.info(f"Executing tool: {tool_name} for run_id: {self.run_id}")
            
            tool_function = self.UPDATE_THIS_NAME.tools[tool_name]
            result = await tool_function.run(state=self.state, **tool_input)

            self.state.messages.append({"role": "tool", "name": tool_name, "content": json.dumps(result)})
            await self._record_step_history(tool_name, tool_input, self.state.model_dump(), {"status": "success", "result": result})

            self.state.current_step = "complete"
            app_logger.info(f"Agent run completed for run_id: {self.run_id}")
            await self._generate_and_save_run_report()

        except Exception as e:
            self.status = "failed"
            self.state.current_step = "failed"
            app_logger.error(f"An unexpected error occurred during agent run for run_id: {self.run_id}. Error: {e}", exc_info=True)
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

        new_run = DeepAgentRun(
            run_id=self.run_id,
            step_name=step_name,
            step_input=input_data,
            step_output=output_data,
            run_log=json.dumps(log_message),
            timestamp=datetime.now(timezone.utc)
        )
        self.db_session.add(new_run)
        await self.db_session.commit()

    async def _generate_and_save_run_report(self):
        """Generates a markdown report of the entire run and saves it to the database."""
        report = f"# Deep Agent Run Report: {self.run_id}\n\n"
        report += f"**Status:** {self.status}\n\n"
        
        if self.triage_result:
            report += "## Triage\n\n"
            report += f"**Category:** {self.triage_result.get('triage_category')}\n"
            report += f"**Confidence:** {self.triage_result.get('confidence')}\n"
            report += f"**Justification:** {self.triage_result.get('justification')}\n"
            report += f"**Suggested Next Steps:**\n"
            for step in self.triage_result.get('suggested_next_steps', []):
                report += f"- {step}\n"
            report += "\n"


        report += "## Steps\n\n"

        runs_result = await self.db_session.execute(select(DeepAgentRun).where(DeepAgentRun.run_id == self.run_id))
        runs = runs_result.scalars().all()
        for run in runs:
            report += f"### {run.step_name}\n\n"
            run_log = json.loads(run.run_log)
            report += f"**Status:** {run_log.get('status')}\n\n"
            result = run_log.get('result')
            if isinstance(result, (dict, list)):
                report += f"**Result:**\n```json\n{json.dumps(result, indent=2)}\n```\n\n"
            else:
                report += f"**Result:**\n{result}\n\n"
            if run_log.get('error'):
                report += f"**Error:**\n```\n{run_log.get('error')}\n```\n\n"

        new_report = DeepAgentRunReport(
            run_id=self.run_id,
            report=report,
            timestamp=datetime.now(timezone.utc)
        )
        self.db_session.add(new_report)
        await self.db_session.commit()

    def is_complete(self) -> bool:
        """Checks if the analysis has completed."""
        return self.status == "complete" or self.status == "failed"
