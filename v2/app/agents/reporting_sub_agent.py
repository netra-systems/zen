import json
import logging

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import reporting_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.schemas import DeepAgentState

logger = logging.getLogger(__name__)

class ReportingSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="ReportingSubAgent", description="This agent generates a final report.")
        self.tool_dispatcher = tool_dispatcher

    async def run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        logger.info(f"ReportingSubAgent starting for run_id: {run_id}")

        prompt = reporting_prompt_template.format(action_plan=state.action_plan_result)

        llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='reporting')
        
        try:
            report_result = json.loads(llm_response_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode LLM response for run_id: {run_id}. Response: {llm_response_str}")
            report_result = {
                "report": "No report could be generated.",
            }

        state.report_result = report_result
        logger.info(f"ReportingSubAgent finished for run_id: {run_id}")
