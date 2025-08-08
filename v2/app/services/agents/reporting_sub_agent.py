from app.services.agents.base import BaseSubAgent
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

class ReportingSubAgent(BaseSubAgent):
    async def run(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool) -> Dict[str, Any]:
        logger.info(f"ReportingSubAgent starting for run_id: {run_id}")

        action_plan = input_data.get("action_plan", {})
        original_request = input_data.get("original_request", "")

        # Simulate generating a report based on the action plan
        if action_plan:
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

        return {"report": report}
