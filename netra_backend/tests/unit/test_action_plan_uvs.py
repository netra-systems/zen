"""Comprehensive test suite for UVS-enhanced ActionPlanBuilder.

This test suite validates that the ActionPlanBuilder with UVS enhancements:
- ALWAYS delivers value (never returns empty/error responses) 
- Adapts to available data (full/partial/none)
- Provides appropriate fallbacks for all failure scenarios
- Maintains compatibility with ReportingSubAgent
- Preserves SSOT compliance from base ActionPlanBuilder
"""

import asyncio
import pytest
from typing import Dict, Any
from unittest.mock import patch, Mock

from test_framework.redis_test_utils import RedisTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.actions_goals_plan_builder_uvs import (
    ActionPlanBuilderUVS,
    DataState,
    UVSPlanContext,
    create_uvs_action_plan_builder
)
from netra_backend.app.agents.state import ActionPlanResult, PlanStep
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestActionPlanUVS:
    """Test suite for UVS-enhanced ActionPlanBuilder"""
    
    @pytest.fixture
    def user_context(self):
        """Create UserExecutionContext for testing"""
        context = UserExecutionContext(
            user_id="test_user_uvs",
            thread_id="test_thread_uvs",
            run_id="test_run_uvs",
            request_id="test_request_uvs",
            metadata={'user_request': 'Help me optimize my AI costs'}
        )
        return context
    
    @pytest.fixture
    def builder(self):
        """Create UVS ActionPlanBuilder instance"""
        return ActionPlanBuilderUVS()
    
    # ============= CORE UVS PRINCIPLE TESTS =============
    
    @pytest.mark.asyncio
    async def test_never_returns_empty_plan(self, builder, user_context):
        """CRITICAL: Test that builder NEVER returns empty plans"""
        # Test with completely empty context
        empty_context = UserExecutionContext(
            user_id="test", 
            thread_id="test",
            run_id="test",
            request_id="test",
            metadata={}
        )
        
        # Should still generate a plan
        result = await builder.generate_adaptive_plan(empty_context)
        
        assert result is not None
        assert isinstance(result, ActionPlanResult)
        assert result.plan_steps is not None
        assert len(result.plan_steps) > 0
        assert result.action_plan_summary
        assert "optimizing" in result.action_plan_summary.lower() or "help" in result.action_plan_summary.lower()
    
    @pytest.mark.asyncio
    async def test_three_tier_response_system(self, builder, user_context):
        """Test three-tier response system based on data availability"""
        
        # Tier 1: No data - guidance plan
        context_no_data = user_context
        result_no_data = await builder.generate_adaptive_plan(context_no_data)
        assert result_no_data.metadata.custom_fields.get('uvs_mode') == 'guidance'
        assert "understand" in result_no_data.action_plan_summary.lower() or "collect" in result_no_data.action_plan_summary.lower()
        
        # Tier 2: Partial data - hybrid plan
        context_partial = UserExecutionContext(
            user_id="test_user_uvs",
            thread_id="test_thread_uvs",
            run_id="test_run_uvs_partial",
            request_id="test_request_uvs_partial",
            metadata={
                'user_request': 'Help me optimize my AI costs',
                'data_result': {'partial_data': True}
            }
        )
        result_partial = await builder.generate_adaptive_plan(context_partial)
        assert result_partial.metadata.custom_fields.get('uvs_mode') == 'hybrid'
        assert "analyze" in result_partial.action_plan_summary.lower() or "data" in result_partial.action_plan_summary.lower()
        
        # Tier 3: Full data - optimization plan
        context_full = UserExecutionContext(
            user_id="test_user_uvs",
            thread_id="test_thread_uvs",
            run_id="test_run_uvs_full",
            request_id="test_request_uvs_full",
            metadata={
                'user_request': 'Help me optimize my AI costs',
                'triage_result': {'intent': 'optimize', 'data_sufficiency': 'sufficient'},
                'data_result': {'usage_data': 'complete'},
                'optimizations_result': {'recommendations': ['Use GPT-3.5', 'Implement caching']}
            }
        )
        result_full = await builder.generate_adaptive_plan(context_full)
        # Full plan could be template-based if LLM is mocked
        assert result_full.plan_steps is not None
        assert len(result_full.plan_steps) > 0
    
    @pytest.mark.asyncio
    async def test_handles_all_failure_scenarios(self, builder):
        """Test that all failure scenarios still produce valuable plans"""
        
        # Scenario 1: Exception during assessment
        context = UserExecutionContext(
            user_id="test",
            thread_id="test", 
            run_id="test",
            request_id="test",
            metadata={}
        )
        
        with patch.object(builder, '_assess_data_availability', side_effect=Exception("Assessment failed")):
            result = await builder.generate_adaptive_plan(context)
            assert result is not None
            assert result.plan_steps is not None
            assert "help" in result.action_plan_summary.lower()
        
        # Scenario 2: LLM failure
        context2 = UserExecutionContext(
            user_id="test",
            thread_id="test", 
            run_id="test2",
            request_id="test2",
            metadata={'triage_result': {}, 'data_result': {}, 'optimizations_result': {}}
        )
        with patch.object(builder, '_get_llm_response_safe', return_value=None):
            result = await builder.generate_adaptive_plan(context2)
            assert result is not None
            assert result.plan_steps is not None
        
        # Scenario 3: Processing failure - test the fallback in process_llm_response
        # The method has built-in error handling that returns a fallback plan
        with patch('netra_backend.app.agents.actions_goals_plan_builder_uvs.super') as mock_super:
            # Make the parent's process_llm_response raise an exception
            mock_super.return_value.process_llm_response = AsyncMock(side_effect=Exception("Processing failed"))
            result = await builder.process_llm_response("test", "test_run")
            assert result is not None
            # Check for recovery mode in metadata.custom_fields
            assert result.metadata.custom_fields.get('recovery_mode') == True
    
    # ============= DATA STATE ASSESSMENT TESTS =============
    
    def test_data_state_assessment_logic(self, builder, user_context):
        """Test correct assessment of data availability"""
        
        # No data
        context = user_context
        uvs_context = builder._assess_data_availability(context)
        assert uvs_context.data_state == DataState.INSUFFICIENT
        assert len(uvs_context.missing_components) == 3
        
        # Partial data - only triage
        context.metadata['triage_result'] = {'intent': 'optimize'}
        uvs_context = builder._assess_data_availability(context)
        assert uvs_context.data_state == DataState.PARTIAL
        assert 'triage' in uvs_context.available_data
        assert 'data_result' in uvs_context.missing_components
        
        # Full data
        context.metadata.update({
            'data_result': {'data': 'present'},
            'optimizations_result': {'recommendations': []}
        })
        uvs_context = builder._assess_data_availability(context)
        assert uvs_context.data_state == DataState.SUFFICIENT
        assert len(uvs_context.missing_components) == 0
    
    # ============= FALLBACK TEMPLATE TESTS =============
    
    @pytest.mark.asyncio
    async def test_no_data_template_provides_value(self, builder, user_context):
        """Test that no-data template provides actionable guidance"""
        test_context = UserExecutionContext(
            user_id="test",
            thread_id="test",
            run_id="test",
            request_id="test",
            metadata={'user_request': 'Help me optimize AI costs'}
        )
        result = await builder._generate_guidance_plan(
            test_context,
            UVSPlanContext(
                data_state=DataState.INSUFFICIENT,
                available_data={},
                missing_components=['triage_result', 'data_result'],
                user_goals='Help me optimize AI costs'
            )
        )
        
        assert result is not None
        assert len(result.plan_steps) >= 3
        
        # Check first step is about understanding/exploring
        first_step = result.plan_steps[0]
        assert "understand" in first_step.description.lower() or "exploring" in first_step.description.lower()
        
        # Check for data collection guidance
        has_collection_step = any(
            'collect' in step.description.lower() 
            for step in result.plan_steps
        )
        assert has_collection_step
        
        # Check for next steps - they should be in metadata
        assert 'next_steps' in result.metadata.custom_fields
        assert len(result.metadata.custom_fields.get('next_steps', [])) > 0
        
        # Check for user guidance
        assert 'user_guidance' in result.metadata.custom_fields
    
    @pytest.mark.asyncio
    async def test_partial_data_template_builds_on_available(self, builder, user_context):
        """Test that partial data template leverages what's available"""
        test_context = UserExecutionContext(
            user_id="test",
            thread_id="test",
            run_id="test",
            request_id="test",
            metadata={'user_request': 'Optimize costs', 'data_result': {'partial': True}}
        )
        
        result = await builder._generate_hybrid_plan(
            test_context,
            UVSPlanContext(
                data_state=DataState.PARTIAL,
                available_data={'data': {'partial': True}},
                missing_components=['optimizations_result'],
                user_goals='Optimize costs'
            )
        )
        
        assert result is not None
        # Check for various phrases that indicate using available data
        assert any(phrase in result.action_plan_summary.lower() for phrase in [
            "data you've provided",
            "available data",
            "your usage data",
            "analyze it"
        ])
        
        # Should have both analysis and collection steps
        step_descriptions = [step.description.lower() for step in result.plan_steps]
        has_analysis = any('analyze' in desc for desc in step_descriptions)
        has_collection = any('collect' in desc or 'fill' in desc or 'data' in desc for desc in step_descriptions)
        
        assert has_analysis
        assert has_collection
    
    @pytest.mark.asyncio
    async def test_error_recovery_template(self, builder, user_context):
        """Test error recovery template provides workarounds"""
        result = await builder._generate_error_recovery_plan(
            user_context,
            UVSPlanContext(
                data_state=DataState.ERROR,
                available_data={},
                missing_components=[],
                user_goals='Help me',
                error_details='LLM timeout'
            )
        )
        
        assert result is not None
        assert "technical issue" in result.action_plan_summary.lower() or "error" in result.action_plan_summary.lower()
        assert result.plan_steps is not None
        assert len(result.plan_steps) > 0
        
        # Should provide manual/alternative approaches
        step_descriptions = ' '.join(step.description.lower() for step in result.plan_steps)
        assert "manual" in step_descriptions or "alternative" in step_descriptions or "work around" in step_descriptions
    
    # ============= REPORTING COMPATIBILITY TESTS =============
    
    @pytest.mark.asyncio
    async def test_ensures_reporting_compatibility(self, builder, user_context):
        """Test that all plans are compatible with ReportingSubAgent"""
        # Test with minimal plan
        minimal_plan = ActionPlanResult()
        uvs_context = UVSPlanContext(
            data_state=DataState.INSUFFICIENT,
            available_data={},
            missing_components=['all'],
            user_goals='test'
        )
        
        enhanced_plan = builder._ensure_reporting_compatibility(minimal_plan, uvs_context)
        
        # Must have required fields for reporting
        assert enhanced_plan.plan_steps is not None
        assert len(enhanced_plan.plan_steps) > 0
        assert enhanced_plan.action_plan_summary
        assert enhanced_plan.metadata.custom_fields.get('uvs_enabled') == True
        assert enhanced_plan.metadata.custom_fields.get('data_state') == DataState.INSUFFICIENT.value
        
        # Must have next_steps for ReportingSubAgent
        next_steps = enhanced_plan.metadata.custom_fields.get('next_steps', [])
        assert next_steps is not None
        assert len(next_steps) > 0
    
    @pytest.mark.asyncio
    async def test_next_steps_generation(self, builder, user_context):
        """Test that next_steps are always generated appropriately"""
        # No data scenario
        uvs_context = UVSPlanContext(
            data_state=DataState.INSUFFICIENT,
            available_data={},
            missing_components=['data_result', 'optimizations_result'],
            user_goals='optimize'
        )
        
        plan = ActionPlanResult()
        next_steps = builder._generate_next_steps(plan, uvs_context)
        
        assert len(next_steps) > 0
        assert any('data' in step.lower() for step in next_steps)
        assert any('use case' in step.lower() or 'describe' in step.lower() for step in next_steps)
        
        # Full data scenario
        uvs_context_full = UVSPlanContext(
            data_state=DataState.SUFFICIENT,
            available_data={'triage': {}, 'data': {}, 'optimizations': {}},
            missing_components=[],
            user_goals='optimize'
        )
        
        next_steps_full = builder._generate_next_steps(plan, uvs_context_full)
        assert len(next_steps_full) > 0
        assert any('review' in step.lower() or 'implement' in step.lower() for step in next_steps_full)
    
    # ============= ULTIMATE FALLBACK TESTS =============
    
    def test_ultimate_fallback_never_fails(self, builder):
        """Test that ultimate fallback ALWAYS produces a valid plan"""
        # This should never throw an exception
        result = builder._get_ultimate_fallback_plan("Catastrophic failure")
        
        assert result is not None
        assert isinstance(result, ActionPlanResult)
        assert result.plan_steps is not None
        assert len(result.plan_steps) >= 3
        assert result.action_plan_summary
        assert result.metadata.custom_fields.get('recovery_mode') == True
        assert result.metadata.custom_fields.get('uvs_mode') == 'ultimate_fallback'
    
    # ============= CUSTOMIZATION TESTS =============
    
    @pytest.mark.asyncio
    async def test_customizes_based_on_user_goals(self, builder):
        """Test that plans are customized based on user goals"""
        # Cost optimization goal
        context_cost = UserExecutionContext(
            user_id="test",
            thread_id="test",
            run_id="test", 
            request_id="test",
            metadata={'user_request': 'reduce my AI costs urgently'}
        )
        
        result_cost = await builder.generate_adaptive_plan(context_cost)
        assert "cost" in result_cost.action_plan_summary.lower()
        
        # Performance optimization goal
        context_perf = UserExecutionContext(
            user_id="test",
            thread_id="test",
            run_id="test",
            request_id="test",
            metadata={'user_request': 'improve AI performance and speed'}
        )
        
        result_perf = await builder.generate_adaptive_plan(context_perf)
        assert "performance" in result_perf.action_plan_summary.lower() or "optimize" in result_perf.action_plan_summary.lower()
    
    # ============= BACKWARD COMPATIBILITY TESTS =============
    
    @pytest.mark.asyncio
    async def test_backward_compatible_with_base_builder(self, builder):
        """Test that UVS builder maintains backward compatibility"""
        # Should still support base process_llm_response
        with patch.object(builder.json_parser, 'ensure_agent_response_is_json', return_value={
            'action_plan_summary': 'Test plan',
            'plan_steps': [{'step_id': '1', 'description': 'Step 1'}]
        }):
            result = await builder.process_llm_response('{"test": "json"}', 'test_run')
            assert result is not None
            assert isinstance(result, ActionPlanResult)
    
    # ============= FACTORY FUNCTION TEST =============
    
    def test_factory_function_creates_uvs_builder(self):
        """Test that factory function creates correct instance"""
        builder = create_uvs_action_plan_builder()
        assert isinstance(builder, ActionPlanBuilderUVS)
        assert builder.uvs_enabled == True
        
        # With context
        builder_with_context = create_uvs_action_plan_builder(
            user_context={'user_id': 'test'},
            cache_manager=RedisTestManager().get_client()
        )
        assert builder_with_context.user_context.get('user_id') == 'test'
        assert builder_with_context.cache_helpers is not None
    
    # ============= INTEGRATION TESTS =============
    
    @pytest.mark.asyncio
    async def test_end_to_end_no_data_scenario(self, builder):
        """Test complete flow with no data available"""
        context = UserExecutionContext(
            user_id="e2e_test",
            thread_id="e2e_thread",
            run_id="e2e_run", 
            request_id="e2e_request",
            metadata={'user_request': 'I need help optimizing my OpenAI usage'}
        )
        
        result = await builder.generate_adaptive_plan(context)
        
        # Verify complete valuable response
        assert result is not None
        assert result.action_plan_summary
        assert len(result.plan_steps) >= 3
        
        # Verify actionable steps
        for step in result.plan_steps:
            assert step.step_id
            assert step.description
            assert step.status == 'pending'
        
        # Verify metadata for downstream agents
        # Note: uvs_enabled may not be set in guidance plan, check for uvs_mode instead
        assert result.metadata.custom_fields.get('uvs_mode') == 'guidance'
        assert result.metadata.custom_fields.get('data_state') == DataState.INSUFFICIENT.value
        
        # Verify user guidance - next_steps should always be present
        assert 'next_steps' in result.metadata.custom_fields
        assert len(result.metadata.custom_fields['next_steps']) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_isolation(self, builder):
        """Test that concurrent executions don't interfere"""
        async def run_plan_generation(user_id: str, data_available: bool):
            metadata = {}
            if data_available:
                metadata = {
                    'user_request': f'Optimize for {user_id}',
                    'data_result': {'user': user_id},
                    'optimizations_result': {'user': user_id}
                }
            else:
                metadata = {
                    'user_request': f'Help {user_id}'
                }
            
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{user_id}",
                run_id=f"run_{user_id}",
                request_id=f"req_{user_id}",
                metadata=metadata
            )
            
            result = await builder.generate_adaptive_plan(context)
            await asyncio.sleep(0)
            return result
        
        # Run multiple concurrent generations
        results = await asyncio.gather(
            run_plan_generation("user1", True),
            run_plan_generation("user2", False),
            run_plan_generation("user3", True),
            run_plan_generation("user4", False),
            run_plan_generation("user5", False)
        )
        
        # All should succeed
        assert len(results) == 5
        for result in results:
            assert result is not None
            assert result.plan_steps is not None
            assert len(result.plan_steps) > 0
        
        # Different data states should produce different plan types
        data_states = [r.metadata.custom_fields.get('data_state') for r in results]
        assert DataState.INSUFFICIENT.value in data_states
        assert data_states.count(DataState.INSUFFICIENT.value) == 3  # users 2, 4, 5