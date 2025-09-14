"""
Pytest fixtures for unified agent testing framework.

Provides standardized fixtures for agent integration tests,
ensuring consistency across all agent types and test patterns.
"""

import pytest
from typing import Dict, Any, List

from test_framework.agent_test_helpers import (
    AgentResultValidator,
    AgentTestExecutor,
    ResultAssertion,
    ValidationConfig,
    CommonValidators,
    create_standard_validation_config
)
from netra_backend.app.schemas.agent_models import DeepAgentState


@pytest.fixture
def agent_validator():
    """Unified agent result validator for all tests"""
    return AgentResultValidator()


@pytest.fixture
def agent_executor():
    """Standardized agent executor for all tests"""
    return AgentTestExecutor()


@pytest.fixture
def result_assertion():
    """Result assertion helpers for all tests"""
    return ResultAssertion()


@pytest.fixture
def common_validators():
    """Common business logic validators"""
    return CommonValidators()


# Agent-specific validation configurations
@pytest.fixture
def triage_validation_config():
    """Validation config for TriageSubAgent (dictionary result)"""
    return ValidationConfig(
        required_fields=["category", "user_intent", "confidence_score"],
        optional_fields=["secondary_categories", "extracted_entities", "tool_recommendations"],
        status_field="status",
        expected_status="success",
        business_validators={
            "confidence_score": CommonValidators.confidence_score,
            "category": CommonValidators.not_empty_string
        }
    )


@pytest.fixture
def optimization_validation_config():
    """Validation config for OptimizationsCoreAgent (Pydantic result)"""
    return ValidationConfig(
        required_fields=["optimization_type", "recommendations", "confidence_score"],
        optional_fields=["cost_savings", "performance_improvement"],
        business_validators={
            "confidence_score": CommonValidators.confidence_score,
            "recommendations": CommonValidators.not_empty_list,
            "optimization_type": CommonValidators.not_empty_string
        }
    )


@pytest.fixture
def action_plan_validation_config():
    """Validation config for ActionsToMeetGoalsAgent (Pydantic result)"""
    return ValidationConfig(
        required_fields=["action_plan_summary", "actions", "execution_timeline"],
        optional_fields=["required_resources", "success_metrics", "cost_benefit_analysis"],
        business_validators={
            "actions": CommonValidators.not_empty_list,
            "execution_timeline": CommonValidators.not_empty_list,
            "action_plan_summary": CommonValidators.not_empty_string
        }
    )


@pytest.fixture
def report_validation_config():
    """Validation config for ReportingAgent (Pydantic result)"""
    return ValidationConfig(
        required_fields=["report_type", "content"],
        optional_fields=["sections", "attachments"],
        business_validators={
            "content": CommonValidators.not_empty_string,
            "report_type": CommonValidators.not_empty_string
        }
    )


@pytest.fixture
def synthetic_data_validation_config():
    """Validation config for SyntheticDataAgent (Pydantic result)"""
    return ValidationConfig(
        required_fields=["data_type", "generation_method", "sample_count"],
        optional_fields=["quality_score", "file_path"],
        business_validators={
            "sample_count": CommonValidators.non_negative_number,
            "quality_score": CommonValidators.confidence_score,
            "data_type": CommonValidators.not_empty_string
        }
    )


@pytest.fixture
def supply_research_validation_config():
    """Validation config for SupplyResearchAgent (Pydantic result)"""
    return ValidationConfig(
        required_fields=["research_scope", "findings"],
        optional_fields=["recommendations", "data_sources", "confidence_level"],
        business_validators={
            "findings": CommonValidators.not_empty_list,
            "research_scope": CommonValidators.not_empty_string,
            "confidence_level": CommonValidators.confidence_score
        }
    )


# Test data factories
@pytest.fixture
def sample_triage_state():
    """Sample DeepAgentState for triage testing"""
    return DeepAgentState(
        run_id="test_triage_001",
        user_request="Optimize my GPT-4 usage and reduce costs",
        user_id="test_user_123",
        chat_thread_id="thread_456"
    )


@pytest.fixture
def sample_optimization_state():
    """Sample DeepAgentState for optimization testing"""
    return DeepAgentState(
        run_id="test_optimization_001",
        user_request="Generate cost optimization recommendations for my AI workload",
        triage_result={
            "category": "cost_optimization",
            "confidence_score": 0.95,
            "status": "success"
        },
        data_result={
            "cost_breakdown": [
                {"model": "gpt-4", "daily_cost": 450.00},
                {"model": "gpt-3.5-turbo", "daily_cost": 25.00}
            ]
        }
    )


@pytest.fixture
def sample_action_plan_state():
    """Sample DeepAgentState for action plan testing"""
    return DeepAgentState(
        run_id="test_action_plan_001",
        user_request="Create an action plan to implement cost optimizations",
        optimizations_result={
            "optimization_type": "cost_reduction",
            "recommendations": ["Use GPT-3.5 for simple tasks", "Implement batching"],
            "confidence_score": 0.9
        }
    )


@pytest.fixture
def sample_report_state():
    """Sample DeepAgentState for report testing"""
    return DeepAgentState(
        run_id="test_report_001",
        user_request="Generate a cost analysis report",
        data_result={
            "analysis_summary": "Cost analysis completed",
            "key_findings": ["High GPT-4 usage", "Optimization opportunities"]
        }
    )


# Business logic assertion helpers
@pytest.fixture
def business_validators():
    """Dictionary of common business validators for different agent types"""
    return {
        "triage": {
            "confidence_score": CommonValidators.confidence_score,
            "category": CommonValidators.not_empty_string,
            "user_intent": lambda x: isinstance(x, dict) and "primary_intent" in x
        },
        "optimization": {
            "confidence_score": CommonValidators.confidence_score,
            "recommendations": CommonValidators.not_empty_list,
            "cost_savings": lambda x: x is None or (isinstance(x, (int, float)) and x >= 0)
        },
        "action_plan": {
            "actions": CommonValidators.not_empty_list,
            "execution_timeline": CommonValidators.not_empty_list,
            "total_estimated_time": CommonValidators.not_empty_string
        },
        "report": {
            "content": CommonValidators.not_empty_string,
            "report_type": CommonValidators.not_empty_string
        },
        "synthetic_data": {
            "sample_count": CommonValidators.non_negative_number,
            "quality_score": CommonValidators.confidence_score
        },
        "supply_research": {
            "findings": CommonValidators.not_empty_list,
            "confidence_level": CommonValidators.confidence_score
        }
    }


# Error scenario fixtures
@pytest.fixture
def error_state():
    """Sample error state for testing error handling"""
    return DeepAgentState(
        run_id="test_error_001",
        user_request="",  # Empty request to trigger error
        user_id="test_user_error"
    )


@pytest.fixture
def timeout_state():
    """Sample state for testing timeout scenarios"""
    return DeepAgentState(
        run_id="test_timeout_001",
        user_request="This is a very complex request that might timeout",
        user_id="test_user_timeout"
    )


# Performance testing fixtures
@pytest.fixture
def performance_thresholds():
    """Performance thresholds for different agent types"""
    return {
        "triage": {"max_execution_time_ms": 5000},
        "optimization": {"max_execution_time_ms": 15000},
        "action_plan": {"max_execution_time_ms": 20000},
        "report": {"max_execution_time_ms": 10000},
        "synthetic_data": {"max_execution_time_ms": 30000},
        "supply_research": {"max_execution_time_ms": 25000}
    }


# Convenience helper function fixtures
@pytest.fixture
def create_validation_config():
    """Factory function to create custom validation configs"""
    def _create_config(
        required_fields: List[str],
        business_validators: Dict[str, Any] = None,
        status_field: str = None,
        expected_status: str = "success"
    ):
        return ValidationConfig(
            required_fields=required_fields,
            optional_fields=[],
            status_field=status_field,
            expected_status=expected_status,
            business_validators=business_validators or {}
        )
    return _create_config


@pytest.fixture
def agent_test_helper():
    """
    All-in-one helper for agent testing.
    Combines validator, executor, and assertion helpers.
    """
    class AgentTestHelper:
        def __init__(self):
            self.validator = AgentResultValidator()
            self.executor = AgentTestExecutor()
            self.assertion = ResultAssertion()
            self.validators = CommonValidators()
        
        async def test_agent_execution(
            self,
            agent,
            state: DeepAgentState,
            result_field: str,
            validation_config: ValidationConfig,
            timeout_seconds: float = 30.0
        ):
            """
            Complete agent test execution with validation.
            
            Returns:
                ValidationResult with all test outcomes
            """
            # Execute agent
            success, error_msg, metrics = await self.executor.execute_with_metrics(
                agent, state, state.run_id or "test_run", False, timeout_seconds
            )
            
            if not success:
                raise AssertionError(f"Agent execution failed: {error_msg}")
            
            # Validate results
            validation_result = self.validator.validate_execution_success(
                state, result_field, validation_config
            )
            
            # Assert success
            self.assertion.assert_success(validation_result)
            
            # Add execution metrics to result
            validation_result.validated_data = {
                **validation_result.validated_data,
                "_test_metrics": metrics
            } if isinstance(validation_result.validated_data, dict) else validation_result.validated_data
            
            return validation_result
    
    return AgentTestHelper()