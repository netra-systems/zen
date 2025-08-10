import json
import logging

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import actions_to_meet_goals_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response

logger = logging.getLogger(__name__)

class ActionsToMeetGoalsSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="ActionsToMeetGoalsSubAgent", description="This agent creates a plan of action.")
        self.tool_dispatcher = tool_dispatcher

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have optimizations and data results to work with."""
        return state.optimizations_result is not None and state.data_result is not None
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the actions to meet goals logic."""
        # Update status via WebSocket
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Creating action plan based on optimization strategies..."
            })

        prompt = actions_to_meet_goals_prompt_template.format(
            optimizations=state.optimizations_result,
            data=state.data_result,
            user_request=state.user_request
        )

        llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='actions_to_meet_goals')
        
        action_plan_result = extract_json_from_response(llm_response_str)
        if not action_plan_result:
            self.logger.warning(f"Could not extract JSON from LLM response for run_id: {run_id}. Using default action plan.")
            action_plan_result = {
                "action_plan": [],
            }

        state.action_plan_result = action_plan_result
        
        # Update with results
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processed",
                "message": "Action plan created successfully",
                "result": action_plan_result
            })
