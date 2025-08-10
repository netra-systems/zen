import json
import logging

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import reporting_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response

logger = logging.getLogger(__name__)

class ReportingSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="ReportingSubAgent", description="This agent generates a final report.")
        self.tool_dispatcher = tool_dispatcher

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have all previous results to generate a report."""
        return (state.action_plan_result is not None and 
                state.optimizations_result is not None and 
                state.data_result is not None and 
                state.triage_result is not None)
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the reporting logic."""
        # Update status via WebSocket
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Generating final report with all analysis results..."
            })

        prompt = reporting_prompt_template.format(
            action_plan=state.action_plan_result,
            optimizations=state.optimizations_result,
            data=state.data_result,
            triage_result=state.triage_result,
            user_request=state.user_request
        )

        llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='reporting')
        
        report_result = extract_json_from_response(llm_response_str)
        if not report_result:
            self.logger.warning(f"Could not extract JSON from LLM response for run_id: {run_id}. Using default report.")
            report_result = {
                "report": "No report could be generated.",
            }

        state.report_result = report_result
        
        # Update with results
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processed",
                "message": "Final report generated successfully",
                "result": report_result
            })
