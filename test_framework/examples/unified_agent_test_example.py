"""
Example implementation of the unified agent testing framework.

This module demonstrates how to use the unified testing framework
for different agent types, showing both Pydantic and dictionary result patterns.

Business Value: Provides concrete examples for implementing consistent
agent tests across the entire platform.
"""
import pytest
import asyncio
from typing import Dict, Any
from test_framework.agent_test_helpers import AgentResultValidator, AgentTestExecutor, ResultAssertion, ValidationConfig, CommonValidators, create_standard_validation_config
from test_framework.fixtures.agent_fixtures import agent_validator, agent_executor, result_assertion, triage_validation_config, optimization_validation_config, action_plan_validation_config, agent_test_helper
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

class TestTriageAgentUnified:
    """
    Example test class for TriageSubAgent using unified framework.
    Demonstrates testing dictionary-based results with status fields.
    """

    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_triage_classification_unified_framework(self, real_triage_agent, agent_test_helper, triage_validation_config, db_session):
        """
        Example test using unified framework for triage agent.
        Shows how to test dictionary-based results consistently.
        """
        state = DeepAgentState(run_id='unified_test_triage_001', user_request='I need to optimize my GPT-4 costs while maintaining quality', user_id='test_user_123')
        validation_result = await agent_test_helper.test_agent_execution(agent=real_triage_agent, state=state, result_field='triage_result', validation_config=triage_validation_config, timeout_seconds=30.0)
        result = validation_result.validated_data
        assert result['category'] != 'Error'
        assert result['category'] != 'General Inquiry'
        assert 'user_intent' in result
        assert result['user_intent']['primary_intent'] is not None
        if 'extracted_entities' in result:
            entities = result['extracted_entities']
            assert 'models_mentioned' in entities
            models = entities.get('models_mentioned', [])
            assert any(('gpt' in model.lower() for model in models))
        logger.info(f"Unified triage test completed: {result['category']}")

class TestOptimizationAgentUnified:
    """
    Example test class for OptimizationsCoreAgent using unified framework.
    Demonstrates testing Pydantic model results.
    """

    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_optimization_recommendations_unified_framework(self, real_optimization_agent, agent_test_helper, optimization_validation_config, db_session):
        """
        Example test using unified framework for optimization agent.
        Shows how to test Pydantic model results consistently.
        """
        state = DeepAgentState(run_id='unified_test_optimization_001', user_request='Optimize my AI model costs for customer support', triage_result={'category': 'cost_optimization', 'confidence_score': 0.95, 'status': 'success'}, data_result={'cost_breakdown': [{'model': 'gpt-4', 'daily_cost': 450.0, 'request_count': 15000, 'avg_tokens': 2500}]})
        validation_result = await agent_test_helper.test_agent_execution(agent=real_optimization_agent, state=state, result_field='optimizations_result', validation_config=optimization_validation_config, timeout_seconds=45.0)
        result = validation_result.validated_data
        result_assertion = ResultAssertion()
        result_assertion.assert_field_value(result, 'confidence_score', float, validator=lambda x: 0.0 <= x <= 1.0)
        result_assertion.assert_field_value(result, 'recommendations', list, not_empty=True)
        recommendations_text = ' '.join(result.recommendations).lower()
        optimization_indicators = ['gpt-3.5', 'batch', 'cache', 'optimize', 'reduce', 'cost']
        assert any((indicator in recommendations_text for indicator in optimization_indicators))
        if result.cost_savings is not None:
            assert result.cost_savings >= 0, 'Cost savings should be non-negative'
        logger.info(f'Unified optimization test completed: {len(result.recommendations)} recommendations')

class TestActionPlanAgentUnified:
    """
    Example test class for ActionsToMeetGoalsAgent using unified framework.
    Demonstrates testing complex Pydantic models with nested structures.
    """

    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_action_plan_generation_unified_framework(self, real_actions_agent, agent_test_helper, action_plan_validation_config, db_session):
        """
        Example test using unified framework for action plan agent.
        Shows how to test complex Pydantic models with business logic.
        """
        state = DeepAgentState(run_id='unified_test_action_plan_001', user_request='Create an action plan to reduce AI costs by 30%', optimizations_result={'optimization_type': 'cost_reduction', 'recommendations': ['Switch simple queries to GPT-3.5-turbo', 'Implement request batching', 'Add response caching'], 'confidence_score': 0.9})
        validation_result = await agent_test_helper.test_agent_execution(agent=real_actions_agent, state=state, result_field='action_plan_result', validation_config=action_plan_validation_config, timeout_seconds=60.0)
        result = validation_result.validated_data
        result_assertion = ResultAssertion()
        if hasattr(result, 'error'):
            assert result.error is None or result.error == '', f'Action plan has error: {result.error}'
        result_assertion.assert_field_value(result, 'actions', list, not_empty=True)
        result_assertion.assert_field_value(result, 'execution_timeline', list, not_empty=True)
        result_assertion.assert_field_value(result, 'action_plan_summary', str, not_empty=True)
        assert len(result.actions) >= 2, 'Should have at least 2 actions for meaningful plan'
        assert len(result.execution_timeline) >= 1, 'Should have timeline phases'
        if hasattr(result, 'cost_benefit_analysis') and result.cost_benefit_analysis:
            assert isinstance(result.cost_benefit_analysis, dict), 'Cost-benefit analysis should be dict'
        logger.info(f'Unified action plan test completed: {len(result.actions)} actions')

class TestErrorHandlingUnified:
    """
    Example test class demonstrating unified error handling patterns.
    Shows how to test error conditions consistently across agent types.
    """

    @pytest.mark.integration
    async def test_timeout_handling_unified(self, mock_slow_agent, agent_test_helper):
        """
        Example test for timeout handling using unified framework.
        """
        state = DeepAgentState(run_id='unified_test_timeout_001', user_request='This request will timeout', user_id='test_user_timeout')
        error_validation_config = ValidationConfig(required_fields=[], optional_fields=[], allow_partial=True, timeout_seconds=1.0)
        with pytest.raises(AssertionError, match='Agent execution failed'):
            await agent_test_helper.test_agent_execution(agent=mock_slow_agent, state=state, result_field='test_result', validation_config=error_validation_config, timeout_seconds=1.0)

    @pytest.mark.integration
    async def test_partial_result_handling_unified(self, mock_partial_agent, agent_validator):
        """
        Example test for partial result handling using unified framework.
        """
        state = DeepAgentState(run_id='unified_test_partial_001', user_request='Request that returns partial results', user_id='test_user_partial')
        await mock_partial_agent.execute(state, state.run_id, stream_updates=False)
        partial_validation_config = ValidationConfig(required_fields=['partial_extraction', 'extracted_fields'], optional_fields=['error'], allow_partial=True)
        validation_result = agent_validator.validate_execution_success(state, 'action_plan_result', partial_validation_config)
        assert validation_result.success
        result = validation_result.validated_data
        if hasattr(result, 'partial_extraction'):
            if result.partial_extraction:
                assert hasattr(result, 'extracted_fields')
                assert isinstance(result.extracted_fields, list)
        logger.info('Unified partial result test completed')

async def demonstrate_framework_patterns():
    """
    Demonstration function showing various framework usage patterns.
    Not a test itself, but shows how to use the framework components.
    """
    validator = AgentResultValidator()
    executor = AgentTestExecutor()
    assertion = ResultAssertion()
    custom_config = ValidationConfig(required_fields=['status', 'result'], business_validators={'confidence': CommonValidators.confidence_score, 'count': CommonValidators.positive_number})
    business_validators = {'recommendations': CommonValidators.not_empty_list, 'confidence_score': CommonValidators.confidence_score, 'cost_savings': lambda x: x is None or x >= 0}

    def validate_optimization_result(result):
        assertion.assert_field_exists(result, 'optimization_type')
        assertion.assert_field_value(result, 'confidence_score', float)
        assertion.assert_business_logic(result, business_validators)
    logger.info('Framework pattern demonstration completed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')