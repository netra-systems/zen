# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T10:35:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Helper module for ActionsToMeetGoalsSubAgent
# Git: v6 | 2c55fb99 | dirty (27 uncommitted)
# Change: Feature | Scope: Component | Risk: Medium
# Session: modernization-session | Seq: 2
# Review: Pending | Score: 95
# ================================
"""Helper module for action plan building and processing."""

from typing import Any, Dict, Optional

from netra_backend.app.agents.state import ActionPlanResult, PlanStep
from netra_backend.app.agents.utils import (
    extract_json_from_response,
    extract_partial_json,
)
from netra_backend.app.logging_config import central_logger as logger


class ActionPlanBuilder:
    """Handles action plan building and processing logic."""
    
    @staticmethod
    async def process_llm_response(
        llm_response: str, run_id: str
    ) -> ActionPlanResult:
        """Process LLM response to ActionPlanResult."""
        action_plan_dict = extract_json_from_response(llm_response)
        if not action_plan_dict:
            action_plan_dict = await ActionPlanBuilder._handle_extraction_failure(
                llm_response, run_id
            )
        return ActionPlanBuilder._convert_to_action_plan_result(action_plan_dict)
    
    @staticmethod
    def _convert_to_action_plan_result(data: dict) -> ActionPlanResult:
        """Convert dictionary to ActionPlanResult."""
        valid_fields = {
            k: v for k, v in data.items()
            if k in ActionPlanResult.model_fields
        }
        if 'actions' in data and 'plan_steps' not in valid_fields:
            valid_fields['plan_steps'] = ActionPlanBuilder._extract_plan_steps(data)
        return ActionPlanResult(**valid_fields)
    
    @staticmethod
    def _extract_plan_steps(data: dict) -> list:
        """Extract plan steps from data."""
        steps = data.get('plan_steps', [])
        if not isinstance(steps, list):
            return []
        return [ActionPlanBuilder._create_plan_step(s) for s in steps]
    
    @staticmethod
    def _create_plan_step(step_data) -> PlanStep:
        """Create PlanStep from data."""
        if isinstance(step_data, str):
            return PlanStep(step_id="1", description=step_data)
        elif isinstance(step_data, dict):
            # Handle different data structures that might come from LLM
            step_id = step_data.get('step_id', step_data.get('id', '1'))
            description = step_data.get('description', step_data.get('step', step_data.get('action', 'No description')))
            return PlanStep(step_id=str(step_id), description=str(description))
        return PlanStep(step_id='1', description='Default step')
    
    @staticmethod
    async def _handle_extraction_failure(
        llm_response: str, run_id: str
    ) -> dict:
        """Handle JSON extraction failure."""
        logger.debug(f"JSON extraction failed for {run_id}")
        partial = extract_partial_json(llm_response)
        if partial:
            return ActionPlanBuilder._build_from_partial(partial).model_dump()
        return ActionPlanBuilder.get_default_action_plan().model_dump()
    
    @staticmethod
    def _build_from_partial(partial: dict) -> ActionPlanResult:
        """Build ActionPlanResult from partial data."""
        base = ActionPlanBuilder.get_base_data()
        base.update({
            k: v for k, v in partial.items()
            if k in ActionPlanResult.model_fields
        })
        base["partial_extraction"] = True
        return ActionPlanResult(**base)
    
    @staticmethod
    def get_base_data() -> dict:
        """Get base action plan data."""
        return {
            "action_plan_summary": "Partial extraction - summary unavailable",
            "total_estimated_time": "To be determined",
            "required_approvals": [],
            "actions": [],
            "execution_timeline": [],
            "supply_config_updates": [],
            "post_implementation": {
                "monitoring_period": "30 days",
                "success_metrics": [],
                "optimization_review_schedule": "Weekly",
                "documentation_updates": []
            },
            "cost_benefit_analysis": {
                "implementation_cost": {"effort_hours": 0, "resource_cost": 0},
                "expected_benefits": {
                    "cost_savings_per_month": 0,
                    "performance_improvement_percentage": 0,
                    "roi_months": 0
                }
            }
        }
    
    @staticmethod
    def get_default_action_plan() -> ActionPlanResult:
        """Get default action plan for failures."""
        data = ActionPlanBuilder.get_base_data()
        data.update({
            "action_plan_summary": "Failed to generate action plan",
            "total_estimated_time": "Unknown",
            "error": "JSON extraction failed - using default"
        })
        return ActionPlanResult(**data)