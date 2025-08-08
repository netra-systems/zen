import logging
from typing import Any, Dict, Optional

from app.llm.llm_manager import LLMManager
from app.schemas import SubAgentLifecycle
from app.services.agents.base import BaseSubAgent

logger = logging.getLogger(__name__)

class ReportingSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager):
        super().__init__(llm_manager)
        self.prompt_template = """
        Based on the following action plan, please generate a comprehensive report.
        Action Plan: {action_plan}
        Original Request: {original_request}

        The report should be well-structured and easy to understand.
        Return the report as a JSON object with a "report" key.
        """

    async def run(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool) -> Dict[str, Any]:
        logger.info(f"ReportingSubAgent starting for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.RUNNING)

        action_plan = input_data.get("action_plan", {})
        original_request = input_data.get("original_request", "")

        if action_plan:
            prompt = self.prompt_template.format(
                action_plan=action_plan,
                original_request=original_request
            )
            # Simulate LLM call for now
            report = f"""
            # Analysis Report

            ## Original Request
            {original_request}

            ## Action Plan
            **{action_plan.get('title')}**

            Here are the steps to be taken:
            """
            for step in action_plan.get('steps', []):
                report += f"""
                ### Step {step.get('step')}: {step.get('action')}
                {step.get('details')}
                """
        else:
            report = "No action plan was generated."

        logger.info(f"ReportingSubAgent finished for run_id: {run_id}")
        self.set_state(SubAgentLifecycle.COMPLETED)

        return {"report": report}