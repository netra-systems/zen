import json
import logging

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import triage_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response

logger = logging.getLogger(__name__)

class TriageSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="TriageSubAgent", description="This agent triages the user request and categorizes it.")
        self.tool_dispatcher = tool_dispatcher

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have a user request to triage."""
        return bool(state.user_request)
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the triage logic."""
        # Update status via WebSocket
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Analyzing user request and determining category..."
            })
        
        prompt = triage_prompt_template.format(user_request=state.user_request)

        llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='triage')
        
        triage_result = extract_json_from_response(llm_response_str)
        if not triage_result:
            self.logger.warning(f"Could not extract JSON from LLM response for run_id: {run_id}. Using default category.")
            triage_result = {
                "category": "General Inquiry",
            }

        state.triage_result = triage_result
        
        # Update with results
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processed",
                "message": f"Request categorized as: {triage_result.get('category', 'Unknown')}",
                "result": triage_result
            })
