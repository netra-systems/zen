import json
import logging

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import optimizations_core_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState

logger = logging.getLogger(__name__)

class OptimizationsCoreSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="OptimizationsCoreSubAgent", description="This agent formulates optimization strategies.")
        self.tool_dispatcher = tool_dispatcher

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have data and triage results to work with."""
        return state.data_result is not None and state.triage_result is not None
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the optimizations core logic."""
        # Update status via WebSocket
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Formulating optimization strategies based on data analysis..."
            })

        prompt = optimizations_core_prompt_template.format(
            data=state.data_result,
            triage_result=state.triage_result,
            user_request=state.user_request
        )

        llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='optimizations_core')
        
        try:
            optimizations_result = json.loads(llm_response_str)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode LLM response for run_id: {run_id}. Response: {llm_response_str}")
            optimizations_result = {
                "optimizations": [],
            }

        state.optimizations_result = optimizations_result
        
        # Update with results
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processed",
                "message": "Optimization strategies formulated successfully",
                "result": optimizations_result
            })
