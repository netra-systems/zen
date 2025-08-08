from app.services.agents.base import BaseSubAgent
from app.schemas import AnalysisRequest
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

class TriageSubAgent(BaseSubAgent):
    async def run(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool) -> Dict[str, Any]:
        logger.info(f"TriageSubAgent starting for run_id: {run_id}")

        analysis_request = AnalysisRequest.parse_obj(input_data)

        prompt = f"""
        Analyze the following user request and categorize it.
        User request: {analysis_request.request.query}
        
        Categories:
        - Data Analysis
        - Code Optimization
        - General Inquiry
        
        Based on the user request, determine the primary category and provide a brief justification.
        """
        
        # For now, we'll simulate the LLM call and return a mock response.
        # In a real implementation, you would use self.llm_manager.ask_llm(prompt)
        
        # Mock response for demonstration purposes
        triage_result = {
            "category": "Data Analysis",
            "justification": "The user is asking to analyze data, so the 'Data Analysis' category is most appropriate."
        }
        
        logger.info(f"TriageSubAgent finished for run_id: {run_id}")
        
        # The output of this agent will be passed to the next agent in the supervisor
        return {
            "triage_result": triage_result,
            "original_request": analysis_request.request.query
        }
