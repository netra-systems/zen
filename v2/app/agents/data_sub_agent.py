# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:47:58.912941+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to sub-agents
# Git: v6 | 2c55fb99 | dirty (27 uncommitted)
# Change: Feature | Scope: Component | Risk: High
# Session: ca70b55b-5f0c-4900-9648-9218422567b5 | Seq: 2
# Review: Pending | Score: 85
# ================================
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
