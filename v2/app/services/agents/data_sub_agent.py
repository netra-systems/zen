import logging
from typing import Any, Dict, Optional

from app.llm.llm_manager import LLMManager
from app.schemas import SubAgentLifecycle
from app.services.agents.base import BaseSubAgent

logger = logging.getLogger(__name__)

class DataSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager):
        super().__init__(llm_manager)
        self.prompt_template = """
        Based on the following triage result, please process the data.
        Triage result: {triage_result}
        Original request: {original_request}

        Please provide a summary of the processed data and key findings.
        Return the result as a JSON object with "summary" and "key_findings" keys.
        """

    async def run(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool) -> Dict[str, Any]:
        logger.info(f"DataSubAgent starting for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.RUNNING)

        triage_result = input_data.get("triage_result", {})
        original_request = input_data.get("original_request", "")

        if triage_result.get("category") == "Data Analysis":
            prompt = self.prompt_template.format(
                triage_result=triage_result,
                original_request=original_request
            )
            
            # Simulate LLM call for now
            processed_data = {
                "dataset": "Sample Dataset",
                "summary": "This is a summary of the processed data.",
                "key_findings": [
                    "Finding 1",
                    "Finding 2",
                    "Finding 3"
                ]
            }
        else:
            processed_data = {}

        logger.info(f"DataSubAgent finished for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.COMPLETED)

        input_data["processed_data"] = processed_data
        input_data["current_agent"] = "OptimizationsCoreSubAgent"
        return input_data
