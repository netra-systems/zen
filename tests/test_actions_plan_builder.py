"""
Tests for ActionPlanBuilder helper class
Tests for action plan building and processing logic.
Compliance: <300 lines, 8-line max functions, modular design.
"""

import pytest
from unittest.mock import patch

from app.agents.actions_goals_plan_builder import ActionPlanBuilder
from app.agents.state import ActionPlanResult, PlanStep


class TestActionPlanBuilder:
    """Test ActionPlanBuilder helper class"""
    
    @patch('app.agents.actions_goals_plan_builder.extract_json_from_response')
    async def test_process_llm_response_success(self, mock_extract):
        """Test successful LLM response processing"""
        mock_extract.return_value = {
            "action_plan_summary": "Test plan",
            "total_estimated_time": "2 weeks",
            "actions": [],
            "required_approvals": ["Manager"],
            "execution_timeline": []
        }
        
        result = await ActionPlanBuilder.process_llm_response("test response", "run-id")
        
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary == "Test plan"
        assert result.total_estimated_time == "2 weeks"

    @patch('app.agents.actions_goals_plan_builder.extract_json_from_response')
    @patch('app.agents.actions_goals_plan_builder.extract_partial_json')
    async def test_process_llm_response_extraction_failure(self, mock_partial, mock_extract):
        """Test LLM response processing with extraction failure"""
        mock_extract.return_value = None
        mock_partial.return_value = {"action_plan_summary": "Partial"}
        
        result = await ActionPlanBuilder.process_llm_response("invalid response", "run-id")
        
        assert isinstance(result, ActionPlanResult)
        assert result.partial_extraction is True

    @patch('app.agents.actions_goals_plan_builder.extract_json_from_response')
    @patch('app.agents.actions_goals_plan_builder.extract_partial_json')
    async def test_process_llm_response_complete_failure(self, mock_partial, mock_extract):
        """Test LLM response processing with complete extraction failure"""
        mock_extract.return_value = None
        mock_partial.return_value = None
        
        result = await ActionPlanBuilder.process_llm_response("completely invalid", "run-id")
        
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary == "Failed to generate action plan"
        assert result.error == "JSON extraction failed - using default"

    def test_convert_to_action_plan_result_valid_fields(self):
        """Test conversion with valid fields only"""
        data = {
            "action_plan_summary": "Test summary",
            "total_estimated_time": "1 week",
            "invalid_field": "should be ignored",
            "actions": [{"step_id": "1", "description": "Test step"}]
        }
        
        result = ActionPlanBuilder._convert_to_action_plan_result(data)
        
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary == "Test summary"
        assert result.total_estimated_time == "1 week"
        # Invalid field should not be included
        assert not hasattr(result, 'invalid_field')

    def test_extract_plan_steps_from_actions(self):
        """Test plan step extraction from actions field"""
        data = {
            "actions": [
                {"step_id": "1", "description": "First step"},
                {"step_id": "2", "description": "Second step"}
            ]
        }
        
        steps = ActionPlanBuilder._extract_plan_steps(data)
        
        assert len(steps) == 2
        assert all(isinstance(step, PlanStep) for step in steps)
        assert steps[0].step_id == "1"
        assert steps[0].description == "First step"

    def test_extract_plan_steps_empty_actions(self):
        """Test plan step extraction with empty actions"""
        data = {"actions": []}
        
        steps = ActionPlanBuilder._extract_plan_steps(data)
        
        assert steps == []

    def test_extract_plan_steps_invalid_actions(self):
        """Test plan step extraction with invalid actions format"""
        data = {"actions": "invalid_format"}
        
        steps = ActionPlanBuilder._extract_plan_steps(data)
        
        assert steps == []

    def test_create_plan_step_from_string(self):
        """Test creating PlanStep from string"""
        step_data = "Test step description"
        
        step = ActionPlanBuilder._create_plan_step(step_data)
        
        assert isinstance(step, PlanStep)
        assert step.step_id == str(len(step_data))  # Uses string length as ID
        assert step.description == "Test step description"

    def test_create_plan_step_from_dict(self):
        """Test creating PlanStep from dictionary"""
        step_data = {"step_id": "test-1", "description": "Test description"}
        
        step = ActionPlanBuilder._create_plan_step(step_data)
        
        assert isinstance(step, PlanStep)
        assert step.step_id == "test-1"
        assert step.description == "Test description"

    def test_create_plan_step_from_incomplete_dict(self):
        """Test creating PlanStep from incomplete dictionary"""
        step_data = {"step_id": "test-1"}  # Missing description
        
        step = ActionPlanBuilder._create_plan_step(step_data)
        
        assert isinstance(step, PlanStep)
        assert step.step_id == "test-1"
        assert step.description == "No description"

    def test_create_plan_step_from_invalid_type(self):
        """Test creating PlanStep from invalid type"""
        step_data = 12345  # Invalid type
        
        step = ActionPlanBuilder._create_plan_step(step_data)
        
        assert isinstance(step, PlanStep)
        assert step.step_id == "1"
        assert step.description == "Default step"

    def test_build_from_partial_data(self):
        """Test building ActionPlanResult from partial data"""
        partial = {
            "action_plan_summary": "Partial summary",
            "actions": [{"step_id": "1", "description": "Test"}]
        }
        
        result = ActionPlanBuilder._build_from_partial(partial)
        
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary == "Partial summary"
        assert result.partial_extraction is True
        # Should include base data for missing fields
        assert result.total_estimated_time == "To be determined"

    def test_get_base_data_structure(self):
        """Test base data structure creation"""
        base_data = ActionPlanBuilder.get_base_data()
        
        required_fields = [
            "action_plan_summary", "total_estimated_time", 
            "required_approvals", "actions", "execution_timeline",
            "supply_config_updates", "post_implementation", 
            "cost_benefit_analysis"
        ]
        
        for field in required_fields:
            assert field in base_data
            
        # Verify nested structures
        assert "monitoring_period" in base_data["post_implementation"]
        assert "implementation_cost" in base_data["cost_benefit_analysis"]
        assert "expected_benefits" in base_data["cost_benefit_analysis"]

    def test_get_base_data_default_values(self):
        """Test base data structure has proper default values"""
        base_data = ActionPlanBuilder.get_base_data()
        
        assert base_data["action_plan_summary"] == "Partial extraction - summary unavailable"
        assert base_data["total_estimated_time"] == "To be determined"
        assert base_data["required_approvals"] == []
        assert base_data["actions"] == []
        assert base_data["execution_timeline"] == []
        assert base_data["supply_config_updates"] == []
        
        # Verify cost benefit structure
        cost_benefit = base_data["cost_benefit_analysis"]
        assert cost_benefit["implementation_cost"]["effort_hours"] == 0
        assert cost_benefit["implementation_cost"]["resource_cost"] == 0
        assert cost_benefit["expected_benefits"]["cost_savings_per_month"] == 0

    def test_get_default_action_plan(self):
        """Test default action plan creation"""
        default_plan = ActionPlanBuilder.get_default_action_plan()
        
        assert isinstance(default_plan, ActionPlanResult)
        assert default_plan.action_plan_summary == "Failed to generate action plan"
        assert default_plan.total_estimated_time == "Unknown"
        assert default_plan.error == "JSON extraction failed - using default"
        
        # Should still have all required structure
        assert default_plan.required_approvals == []
        assert default_plan.actions == []

    async def test_handle_extraction_failure_with_partial(self):
        """Test handling extraction failure with partial recovery"""
        with patch('app.agents.actions_goals_plan_builder.extract_partial_json') as mock_partial:
            mock_partial.return_value = {"action_plan_summary": "Recovered partial"}
            
            result_dict = await ActionPlanBuilder._handle_extraction_failure("invalid", "test-run")
            
            assert "action_plan_summary" in result_dict
            # Should be built from partial, so will have partial_extraction flag
            # when converted back to ActionPlanResult

    async def test_handle_extraction_failure_complete(self):
        """Test handling complete extraction failure"""
        with patch('app.agents.actions_goals_plan_builder.extract_partial_json') as mock_partial:
            mock_partial.return_value = None
            
            result_dict = await ActionPlanBuilder._handle_extraction_failure("invalid", "test-run")
            
            # Should return default plan as dict
            assert result_dict["action_plan_summary"] == "Failed to generate action plan"
            assert result_dict["error"] == "JSON extraction failed - using default"


class TestActionPlanBuilderIntegration:
    """Integration tests for ActionPlanBuilder"""
    
    @patch('app.agents.actions_goals_plan_builder.extract_json_from_response')
    async def test_end_to_end_successful_processing(self, mock_extract):
        """Test end-to-end successful processing flow"""
        mock_extract.return_value = {
            "action_plan_summary": "Complete optimization plan",
            "total_estimated_time": "4 weeks",
            "required_approvals": ["Tech Lead", "Product Manager"],
            "actions": [
                {"step_id": "1", "description": "Analyze current performance"},
                {"step_id": "2", "description": "Implement optimizations"}
            ],
            "execution_timeline": [
                {"phase": "Analysis", "duration": "1 week"},
                {"phase": "Implementation", "duration": "3 weeks"}
            ],
            "cost_benefit_analysis": {
                "implementation_cost": {"effort_hours": 160, "resource_cost": 20000},
                "expected_benefits": {"cost_savings_per_month": 5000, "roi_months": 4}
            }
        }
        
        result = await ActionPlanBuilder.process_llm_response(
            "Valid JSON response", "integration-test-run"
        )
        
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary == "Complete optimization plan"
        assert result.total_estimated_time == "4 weeks"
        assert len(result.required_approvals) == 2
        assert len(result.execution_timeline) == 2
        assert result.partial_extraction is False  # Should be complete
        
        # Verify cost benefit analysis was preserved
        cost_benefit = result.cost_benefit_analysis
        assert cost_benefit["implementation_cost"]["effort_hours"] == 160
        assert cost_benefit["expected_benefits"]["cost_savings_per_month"] == 5000