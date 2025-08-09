import json
import logging
from typing import Any, Dict

from app.llm.llm_manager import LLMManager
from app.schemas import SubAgentLifecycle
from app.agents.base import BaseSubAgent
from app.agents.prompts import actions_to_meet_goals_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState

logger = logging.getLogger(__name__)

class ActionsToMeetGoalsSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="ActionsToMeetGoalsSubAgent", description="This agent creates a plan of action.")
        self.tool_dispatcher = tool_dispatcher

    async def run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        logger.info(f"ActionsToMeetGoalsSubAgent starting for run_id: {run_id}")

        prompt = actions_to_meet_goals_prompt_template.format(optimizations=state.optimizations_result)

        llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='actions_to_meet_goals')
        
        try:
            action_plan_result = json.loads(llm_response_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode LLM response for run_id: {run_id}. Response: {llm_response_str}")
            action_plan_result = {
                "action_plan": [],
            }

        state.action_plan_result = action_plan_result
        logger.info(f"ActionsToMeetGoalsSubAgent finished for run_id: {run_id}")