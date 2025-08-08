import json
import logging
from typing import Any, Dict

from app.llm.llm_manager import LLMManager
from app.schemas import SubAgentLifecycle
from app.agents.base import BaseSubAgent
from app.agents.prompts import triage_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher

logger = logging.getLogger(__name__)

class TriageSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="TriageSubAgent", description="This agent triages the user request and categorizes it.")
        self.tool_dispatcher = tool_dispatcher

    async def run(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool) -> Dict[str, Any]:
        logger.info(f"TriageSubAgent starting for run_id: {run_id}")

        prompt = triage_prompt_template.format(user_request=input_data["request"]["query"])

        llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='triage')
        
        try:
            triage_result = json.loads(llm_response_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode LLM response for run_id: {run_id}. Response: {llm_response_str}")
            triage_result = {
                "category": "General Inquiry",
            }

        logger.info(f"TriageSubAgent finished for run_id: {run_id}")

        return {"triage_result": triage_result}
