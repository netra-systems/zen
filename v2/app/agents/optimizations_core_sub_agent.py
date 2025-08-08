import json
import logging
from typing import Any, Dict

from app.llm.llm_manager import LLMManager
from app.schemas import SubAgentLifecycle
from app.agents.base import BaseSubAgent
from app.agents.prompts import optimizations_core_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher

logger = logging.getLogger(__name__)

class OptimizationsCoreSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="OptimizationsCoreSubAgent", description="This agent formulates optimization strategies.")
        self.tool_dispatcher = tool_dispatcher

    async def run(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool) -> Dict[str, Any]:
        logger.info(f"OptimizationsCoreSubAgent starting for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.RUNNING)

        prompt = optimizations_core_prompt_template.format(data=input_data["data_result"])

        llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='optimizations_core')
        
        try:
            optimizations_result = json.loads(llm_response_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode LLM response for run_id: {run_id}. Response: {llm_response_str}")
            optimizations_result = {
                "optimizations": [],
            }

        logger.info(f"OptimizationsCoreSubAgent finished for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.COMPLETED)

        input_data["optimizations_result"] = optimizations_result
        return input_data
