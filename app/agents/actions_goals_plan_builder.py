"""Action Plan Builder Helper Module

Provides default data structures and plan building utilities for 
ActionsToMeetGoalsSubAgent to maintain 300-line module limit.

Business Value: Enables structured action plan generation for Enterprise customers.
"""

from app.agents.state import ActionPlanResult, PlanStep


class ActionPlanBuilder:
    """Helper class for building action plans and default structures."""
    
    @staticmethod
    def get_base_action_plan_data() -> dict:
        """Get base action plan data with defaults for ActionPlanResult."""
        return {
            "action_plan_summary": "Partial extraction - summary unavailable",
            "total_estimated_time": "To be determined",
            "required_approvals": [],
            "actions": [],
            "execution_timeline": [],
            "supply_config_updates": [],
            "post_implementation": ActionPlanBuilder._get_default_post_implementation(),
            "cost_benefit_analysis": ActionPlanBuilder._get_default_cost_benefit()
        }
    
    @staticmethod
    def _get_default_post_implementation() -> dict:
        """Get default post implementation structure."""
        return {
            "monitoring_period": "30 days",
            "success_metrics": [],
            "optimization_review_schedule": "Weekly", 
            "documentation_updates": []
        }
    
    @staticmethod
    def _get_default_cost_benefit() -> dict:
        """Get default cost benefit analysis structure."""
        return {
            "implementation_cost": {"effort_hours": 0, "resource_cost": 0},
            "expected_benefits": {
                "cost_savings_per_month": 0,
                "performance_improvement_percentage": 0,
                "roi_months": 0
            }
        }
    
    @staticmethod
    def get_default_action_plan() -> ActionPlanResult:
        """Get a default action plan when extraction completely fails."""
        base_data = ActionPlanBuilder.get_base_action_plan_data()
        base_data["action_plan_summary"] = "Failed to generate action plan from LLM response"
        base_data["total_estimated_time"] = "Unknown"
        base_data["error"] = "JSON extraction failed - using default structure"
        return ActionPlanResult(**base_data)
    
    @staticmethod
    def build_action_plan_from_partial(partial_data: dict) -> ActionPlanResult:
        """Build a complete action plan structure from partial extracted data."""
        base_data = ActionPlanBuilder.get_base_action_plan_data()
        for key, value in partial_data.items():
            if key in ActionPlanResult.model_fields:
                base_data[key] = value
        
        base_data["partial_extraction"] = True
        base_data["extracted_fields"] = list(partial_data.keys())
        return ActionPlanResult(**base_data)
    
    @staticmethod
    def extract_plan_steps(action_plan_dict: dict) -> list:
        """Extract and convert plan steps from dictionary."""
        steps_data = action_plan_dict.get('plan_steps', [])
        if not isinstance(steps_data, list):
            return []
        return [ActionPlanBuilder._create_plan_step(step) for step in steps_data]
    
    @staticmethod
    def _create_plan_step(step_data) -> PlanStep:
        """Create PlanStep from step data with safe defaults."""
        if isinstance(step_data, str):
            return PlanStep(step_id=str(len(step_data)), description=step_data)
        elif isinstance(step_data, dict):
            return ActionPlanBuilder._create_plan_step_from_dict(step_data)
        return PlanStep(step_id='1', description='Default step')
    
    @staticmethod
    def _create_plan_step_from_dict(step_data: dict) -> PlanStep:
        """Create PlanStep from dictionary data."""
        return PlanStep(
            step_id=step_data.get('step_id', '1'),
            description=step_data.get('description', 'No description')
        )