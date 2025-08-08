import json
import logging
from typing import Any, Dict

from app.llm.llm_manager import LLMManager
from app.schemas import SubAgentLifecycle
from app.agents.base import BaseSubAgent
from app.agents.prompts import data_prompt_template

logger = logging.getLogger(__name__)

class DataSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager):
        super().__init__(llm_manager)

    async def run(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool) -> Dict[str, Any]:
        logger.info(f"DataSubAgent starting for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.RUNNING)

        prompt = data_prompt_template.format(triage_result=input_data["triage_result"])

        llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='data')
        
        try:
            data_result = json.loads(llm_response_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode LLM response for run_id: {run_id}. Response: {llm_response_str}")
            data_result = {
                "data": "No data could be gathered.",
            }

        logger.info(f"DataSubAgent finished for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.COMPLETED)

        input_data["data_result"] = data_result
        return input_data