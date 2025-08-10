import json
import logging

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import data_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response

logger = logging.getLogger(__name__)

class DataSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="DataSubAgent", description="This agent gathers and enriches data.")
        self.tool_dispatcher = tool_dispatcher

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have triage results to work with."""
        return state.triage_result is not None
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the data gathering logic."""
        # Update status via WebSocket
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Gathering and enriching data based on triage results..."
            })

        prompt = data_prompt_template.format(
            triage_result=state.triage_result,
            user_request=state.user_request,
            thread_id=run_id
        )

        llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='data')
        
        data_result = extract_json_from_response(llm_response_str)
        if not data_result:
            self.logger.warning(f"Could not extract JSON from LLM response for run_id: {run_id}. Using default data.")
            data_result = {
                "data": "No data could be gathered.",
            }

        state.data_result = data_result
        
        # Update with results
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processed",
                "message": "Data gathering completed",
                "result": data_result
            })
