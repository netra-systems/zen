import json
import logging
from typing import Any, Dict, Optional

from app.llm.llm_manager import LLMManager
from app.schemas import AnalysisRequest, SubAgentLifecycle
from app.services.agents.base import BaseSubAgent

logger = logging.getLogger(__name__)

class TriageSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager):
        super().__init__(llm_manager)
        self.prompt_template = """
        Analyze the following user request and categorize it.
        User request: {query}

        Categories:
        - Data Analysis
        - Code Optimization
        - General Inquiry

        Based on the user request, determine the primary category and provide a brief justification.
        Return the result as a JSON object with "category" and "justification" keys.
        """

    async def run(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool) -> Dict[str, Any]:
        logger.info(f"TriageSubAgent starting for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.RUNNING)

        analysis_request = AnalysisRequest.parse_obj(input_data["analysis_request"])
        
        prompt = self.prompt_template.format(query=analysis_request.request.query)

        llm_response_str = await self.llm_manager.ask_llm(prompt)
        
        try:
            triage_result = json.loads(llm_response_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode LLM response for run_id: {run_id}. Response: {llm_response_str}")
            triage_result = {
                "category": "General Inquiry",
                "justification": "Could not determine category from user request."
            }

        logger.info(f"TriageSubAgent finished for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.COMPLETED)

        input_data["triage_result"] = triage_result
        input_data["current_agent"] = "DataSubAgent"
        return input_data
