"""Unit tests for ActionPlanBuilderUVS - UVS-Enhanced ActionPlanBuilder.

Business Value Justification (BVJ):
- Segment: Platform/Core - Action Plan Generation
- Business Goal: Guaranteed Value Delivery & User Experience
- Value Impact: Ensures action plans ALWAYS deliver value regardless of data availability
- Strategic Impact: Protects $500K+ ARR by never returning empty/error responses

CRITICAL: Tests validate UVS (Unified User Value System) compliance where action plans
must always provide substantive value even with zero data, failed triage, or LLM failures.
All tests use SSOT patterns and real services where appropriate.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from netra_backend.app.agents.actions_goals_plan_builder_uvs import (
    ActionPlanBuilderUVS,
    DataState,
    UVSPlanContext,
    create_uvs_action_plan_builder
)
from netra_backend.app.agents.state import ActionPlanResult, PlanStep
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState, AgentMetadata
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestActionPlanBuilderUVS(SSotAsyncTestCase):
    """Unit tests for ActionPlanBuilderUVS - UVS-compliant action plan generation."""

    def setup_method(self, method=None):
        """Setup test fixtures following SSOT patterns."""
        super().setup_method(method)
        
        # Create UVS-enhanced builder
        self.builder = ActionPlanBuilderUVS()
        
        # Sample user context for testing
        self.sample_context = UserExecutionContext(
            run_id="test-run-123",
            user_id="test-user-456",
            metadata={
                "user_request": "Help me optimize my AI costs",
                "chat_thread_id": "thread-789"
            },
            agent_state=DeepAgentState(
                user_request="Help me optimize my AI costs",
                user_prompt="Help me optimize my AI costs",
                user_id="test-user-456"
            )
        )
        
    def test_initialization(self):
        """Test ActionPlanBuilderUVS initialization."""
        assert self.builder.uvs_enabled is True
        assert hasattr(self.builder, 'FALLBACK_TEMPLATES')
        assert 'no_data' in self.builder.FALLBACK_TEMPLATES
        assert 'partial_data' in self.builder.FALLBACK_TEMPLATES
        assert 'error_recovery' in self.builder.FALLBACK_TEMPLATES
        
    def test_data_state_enum_values(self):
        """Test DataState enum contains all required values."""
        assert DataState.SUFFICIENT == "sufficient"
        assert DataState.PARTIAL == "partial"
        assert DataState.INSUFFICIENT == "insufficient"
        assert DataState.ERROR == "error"
        
    def test_uvs_plan_context_creation(self):
        """Test UVSPlanContext dataclass creation."""
        context = UVSPlanContext(
            data_state=DataState.SUFFICIENT,
            available_data={"triage": "test_data"},
            missing_components=["data_result"],
            user_goals="Cost optimization"
        )
        
        assert context.data_state == DataState.SUFFICIENT
        assert context.available_data == {"triage": "test_data"}
        assert context.missing_components == ["data_result"]
        assert context.user_goals == "Cost optimization"
        
    def test_assess_data_availability_sufficient(self):
        """Test data assessment with sufficient data."""
        # Setup context with all required data
        context = UserExecutionContext(
            run_id="test-run",
            user_id="test-user",
            metadata={
                "triage_result": {"status": "complete"},
                "data_result": {"usage": "high"},
                "optimizations_result": {"savings": "30%"},
                "user_request": "Optimize my AI spend"
            },
            agent_state=DeepAgentState(user_request="Optimize my AI spend")
        )
        
        uvs_context = self.builder._assess_data_availability(context)
        
        assert uvs_context.data_state == DataState.SUFFICIENT
        assert "triage" in uvs_context.available_data
        assert "data" in uvs_context.available_data
        assert "optimizations" in uvs_context.available_data
        assert len(uvs_context.missing_components) == 0
        assert uvs_context.user_goals == "Optimize my AI spend"
        
    def test_assess_data_availability_partial(self):
        """Test data assessment with partial data."""
        context = UserExecutionContext(
            run_id="test-run",
            user_id="test-user", 
            metadata={
                "triage_result": {"status": "complete"},
                "user_request": "Reduce costs"
            },
            agent_state=DeepAgentState(user_request="Reduce costs")
        )
        
        uvs_context = self.builder._assess_data_availability(context)
        
        assert uvs_context.data_state == DataState.PARTIAL
        assert "triage" in uvs_context.available_data
        assert "data_result" in uvs_context.missing_components
        assert "optimizations_result" in uvs_context.missing_components
        
    def test_assess_data_availability_insufficient(self):
        """Test data assessment with no data."""
        context = UserExecutionContext(
            run_id="test-run",
            user_id="test-user",
            metadata={"user_request": "Help with AI optimization"},
            agent_state=DeepAgentState(user_request="Help with AI optimization")
        )
        
        uvs_context = self.builder._assess_data_availability(context)
        
        assert uvs_context.data_state == DataState.INSUFFICIENT
        assert len(uvs_context.available_data) == 0
        assert "triage_result" in uvs_context.missing_components
        assert "data_result" in uvs_context.missing_components
        assert "optimizations_result" in uvs_context.missing_components
        
    def test_create_plan_step_from_template(self):
        """Test plan step creation from template."""
        template_step = {
            'step_id': 'test_step',
            'description': 'Test action',
            'estimated_duration': '30 minutes',
            'dependencies': ['step1'],
            'resources_needed': ['Data access'],
            'step_number': 1,
            'action': 'Perform test action'
        }
        
        plan_step = self.builder._create_plan_step_from_template(template_step)
        
        assert isinstance(plan_step, PlanStep)
        assert plan_step.step_id == 'test_step'
        assert plan_step.description == 'Test action'
        assert plan_step.estimated_duration == '30 minutes'
        assert plan_step.dependencies == ['step1']
        assert plan_step.resources_needed == ['Data access']
        assert plan_step.status == 'pending'
        
    def test_create_plan_step_from_template_fallback(self):
        """Test plan step creation with minimal template data."""
        template_step = {
            'step_number': 2,
            'action': 'Fallback action'
        }
        
        plan_step = self.builder._create_plan_step_from_template(template_step)
        
        assert plan_step.step_id == '2'
        assert plan_step.description == 'Fallback action'
        assert plan_step.dependencies == []
        assert plan_step.resources_needed == []
        assert plan_step.status == 'pending'
        
    async def test_generate_guidance_plan(self):
        """Test guidance plan generation for no data scenario."""
        uvs_context = UVSPlanContext(
            data_state=DataState.INSUFFICIENT,
            available_data={},
            missing_components=["triage_result", "data_result"],
            user_goals="Cost optimization"
        )
        
        result = await self.builder._generate_guidance_plan(self.sample_context, uvs_context)
        
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary is not None
        assert "cost" in result.action_plan_summary.lower()
        assert len(result.plan_steps) > 0
        assert result.metadata.custom_fields['uvs_mode'] == 'guidance'
        assert result.metadata.custom_fields['data_state'] == 'insufficient'
        assert 'next_steps' in result.metadata.custom_fields
        assert 'user_guidance' in result.metadata.custom_fields
        
    async def test_generate_guidance_plan_performance_focus(self):
        """Test guidance plan customization for performance goals."""
        uvs_context = UVSPlanContext(
            data_state=DataState.INSUFFICIENT,
            available_data={},
            missing_components=["triage_result", "data_result"],
            user_goals="Improve AI performance"
        )
        
        result = await self.builder._generate_guidance_plan(self.sample_context, uvs_context)
        
        assert "performance" in result.action_plan_summary.lower()
        
    async def test_generate_hybrid_plan(self):
        """Test hybrid plan generation for partial data."""
        uvs_context = UVSPlanContext(
            data_state=DataState.PARTIAL,
            available_data={"data": {"usage": "high"}},
            missing_components=["optimizations_result"],
            user_goals="Reduce costs"
        )
        
        result = await self.builder._generate_hybrid_plan(self.sample_context, uvs_context)
        
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary is not None
        assert len(result.plan_steps) > 0
        assert result.metadata.custom_fields['uvs_mode'] == 'hybrid'
        assert result.metadata.custom_fields['data_state'] == 'partial'
        assert 'next_steps' in result.metadata.custom_fields
        
    async def test_generate_hybrid_plan_optimizations_available(self):
        """Test hybrid plan when optimizations are available but data missing."""
        uvs_context = UVSPlanContext(
            data_state=DataState.PARTIAL,
            available_data={"optimizations": {"recommendations": ["Use GPT-4"]}},
            missing_components=["data_result"],
            user_goals="Optimize AI usage"
        )
        
        result = await self.builder._generate_hybrid_plan(self.sample_context, uvs_context)
        
        assert "optimization opportunities" in result.action_plan_summary
        assert "additional data" in result.action_plan_summary
        
    async def test_generate_error_recovery_plan(self):
        """Test error recovery plan generation."""
        uvs_context = UVSPlanContext(
            data_state=DataState.ERROR,
            available_data={},
            missing_components=[],
            user_goals="Optimize costs",
            error_details="Database connection failed"
        )
        
        result = await self.builder._generate_error_recovery_plan(self.sample_context, uvs_context)
        
        assert isinstance(result, ActionPlanResult)
        assert "Database connection failed" in result.action_plan_summary
        assert len(result.plan_steps) > 0
        assert result.metadata.custom_fields['uvs_mode'] == 'error_recovery'
        assert result.metadata.custom_fields['error'] == 'Database connection failed'
        assert 'next_steps' in result.metadata.custom_fields
        
    def test_create_template_based_full_plan(self):
        """Test template-based full plan creation."""
        uvs_context = UVSPlanContext(
            data_state=DataState.SUFFICIENT,
            available_data={
                "optimizations": MagicMock(recommendations=["Use caching", "Optimize models"]),
                "data": {"usage": "high"}
            },
            missing_components=[],
            user_goals="Full optimization"
        )
        
        result = self.builder._create_template_based_full_plan(uvs_context)
        
        assert isinstance(result, ActionPlanResult)
        assert len(result.plan_steps) > 0
        assert result.metadata.custom_fields['uvs_mode'] == 'template_full'
        assert result.metadata.custom_fields['source'] == 'fallback'
        
    def test_create_template_based_full_plan_no_optimizations(self):
        """Test template-based full plan with no optimization data."""
        uvs_context = UVSPlanContext(
            data_state=DataState.SUFFICIENT,
            available_data={"data": {"usage": "medium"}},
            missing_components=[],
            user_goals="General optimization"
        )
        
        result = self.builder._create_template_based_full_plan(uvs_context)
        
        assert isinstance(result, ActionPlanResult)
        assert len(result.plan_steps) >= 3  # Should have generic steps
        assert any("model selection" in step.description.lower() for step in result.plan_steps)
        assert any("caching" in step.description.lower() for step in result.plan_steps)
        assert any("monitoring" in step.description.lower() for step in result.plan_steps)
        
    def test_ensure_reporting_compatibility(self):
        """Test reporting compatibility enforcement."""
        # Create minimal plan
        plan = ActionPlanResult(
            action_plan_summary="",
            plan_steps=[],
            actions=[],
            total_estimated_time="0 minutes"
        )
        
        uvs_context = UVSPlanContext(
            data_state=DataState.PARTIAL,
            available_data={"triage": "complete"},
            missing_components=["data_result"],
            user_goals="Test optimization"
        )
        
        enhanced_plan = self.builder._ensure_reporting_compatibility(plan, uvs_context)
        
        assert enhanced_plan.action_plan_summary != ""
        assert len(enhanced_plan.plan_steps) > 0
        assert enhanced_plan.metadata.custom_fields['uvs_enabled'] is True
        assert enhanced_plan.metadata.custom_fields['data_state'] == 'partial'
        assert 'available_components' in enhanced_plan.metadata.custom_fields
        assert 'missing_components' in enhanced_plan.metadata.custom_fields
        assert 'next_steps' in enhanced_plan.metadata.custom_fields
        
    def test_generate_next_steps_insufficient_data(self):
        """Test next steps generation for insufficient data."""
        plan = ActionPlanResult(
            action_plan_summary="Test plan",
            plan_steps=[],
            actions=[]
        )
        
        uvs_context = UVSPlanContext(
            data_state=DataState.INSUFFICIENT,
            available_data={},
            missing_components=["triage_result", "data_result"],
            user_goals="Optimization"
        )
        
        next_steps = self.builder._generate_next_steps(plan, uvs_context)
        
        assert isinstance(next_steps, list)
        assert len(next_steps) > 0
        assert any("usage data" in step.lower() for step in next_steps)
        assert any("use cases" in step.lower() for step in next_steps)
        
    def test_generate_next_steps_partial_data(self):
        """Test next steps generation for partial data."""
        plan = ActionPlanResult(
            action_plan_summary="Test plan",
            plan_steps=[],
            actions=[]
        )
        
        uvs_context = UVSPlanContext(
            data_state=DataState.PARTIAL,
            available_data={"triage": "complete"},
            missing_components=["data_result"],
            user_goals="Optimization"
        )
        
        next_steps = self.builder._generate_next_steps(plan, uvs_context)
        
        assert isinstance(next_steps, list)
        assert len(next_steps) > 0
        assert any("upload" in step.lower() for step in next_steps)
        
    def test_get_ultimate_fallback_plan(self):
        """Test ultimate fallback plan generation."""
        error_msg = "Critical system failure"
        
        result = self.builder._get_ultimate_fallback_plan(error_msg)
        
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary is not None
        assert len(result.plan_steps) >= 3
        assert result.metadata.custom_fields['uvs_mode'] == 'ultimate_fallback'
        assert result.metadata.custom_fields['error'] == error_msg
        assert result.metadata.custom_fields['recovery_mode'] is True
        assert 'next_steps' in result.metadata.custom_fields
        assert 'user_guidance' in result.metadata.custom_fields
        
    async def test_generate_adaptive_plan_sufficient_data(self):
        """Test adaptive plan generation with sufficient data."""
        # Mock the parent method
        with patch.object(self.builder, 'process_llm_response', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = ActionPlanResult(
                action_plan_summary="Full optimization plan",
                plan_steps=[PlanStep(step_id="1", description="Optimize models")],
                actions=[]
            )
            
            # Context with sufficient data
            context = UserExecutionContext(
                run_id="test-run",
                user_id="test-user",
                metadata={
                    "triage_result": {"status": "complete"},
                    "data_result": {"usage": "high"},
                    "optimizations_result": {"savings": "30%"}
                },
                agent_state=DeepAgentState(user_request="Optimize AI")
            )
            
            result = await self.builder.generate_adaptive_plan(context)
            
            assert isinstance(result, ActionPlanResult)
            assert result.metadata.custom_fields.get('uvs_enabled') is True
            
    async def test_generate_adaptive_plan_insufficient_data(self):
        """Test adaptive plan generation with no data."""
        # Context with no data
        context = UserExecutionContext(
            run_id="test-run",
            user_id="test-user",
            metadata={"user_request": "Help optimize AI"},
            agent_state=DeepAgentState(user_request="Help optimize AI")
        )
        
        result = await self.builder.generate_adaptive_plan(context)
        
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary is not None
        assert len(result.plan_steps) > 0
        assert result.metadata.custom_fields['uvs_mode'] == 'guidance'
        assert result.metadata.custom_fields['data_state'] == 'insufficient'
        
    async def test_generate_adaptive_plan_error_handling(self):
        """Test adaptive plan generation error handling."""
        # Create context that will cause an error in assessment
        context = UserExecutionContext(
            run_id="test-run",
            user_id="test-user",
            metadata=None,  # This should cause an error
            agent_state=DeepAgentState(user_request="Test")
        )
        
        result = await self.builder.generate_adaptive_plan(context)
        
        # Should return ultimate fallback plan
        assert isinstance(result, ActionPlanResult)
        assert result.metadata.custom_fields['uvs_mode'] == 'ultimate_fallback'
        assert 'error' in result.metadata.custom_fields
        
    async def test_process_llm_response_override_empty_result(self):
        """Test LLM response processing override with empty result."""
        with patch.object(self.builder.__class__.__bases__[0], 'process_llm_response', new_callable=AsyncMock) as mock_super:
            # Mock parent returning empty result
            mock_super.return_value = ActionPlanResult(
                action_plan_summary="",
                plan_steps=[],
                actions=[]
            )
            
            result = await self.builder.process_llm_response("test response", "test-run-id")
            
            # Should return ultimate fallback
            assert isinstance(result, ActionPlanResult)
            assert result.metadata.custom_fields['uvs_mode'] == 'ultimate_fallback'
            
    async def test_process_llm_response_override_exception(self):
        """Test LLM response processing override with exception."""
        with patch.object(self.builder.__class__.__bases__[0], 'process_llm_response', new_callable=AsyncMock) as mock_super:
            # Mock parent raising exception
            mock_super.side_effect = Exception("LLM processing failed")
            
            result = await self.builder.process_llm_response("test response", "test-run-id")
            
            # Should return ultimate fallback
            assert isinstance(result, ActionPlanResult)
            assert result.metadata.custom_fields['uvs_mode'] == 'ultimate_fallback'
            assert "LLM processing failed" in result.metadata.custom_fields['error']
            
    def test_build_full_plan_prompt(self):
        """Test full plan prompt building."""
        uvs_context = UVSPlanContext(
            data_state=DataState.SUFFICIENT,
            available_data={
                "triage": {"status": "complete"},
                "data": {"usage": "high"},
                "optimizations": {"savings": "30%"}
            },
            missing_components=[],
            user_goals="Optimize AI spend"
        )
        
        prompt = self.builder._build_full_plan_prompt(uvs_context)
        
        assert isinstance(prompt, str)
        assert "comprehensive action plan" in prompt.lower()
        assert "optimize ai spend" in prompt.lower()
        
    async def test_get_llm_response_safe_fallback(self):
        """Test safe LLM response with fallback."""
        # This method should return None to trigger fallback
        result = await self.builder._get_llm_response_safe("test prompt", "test-run-id")
        
        assert result is None
        
    def test_fallback_templates_structure(self):
        """Test that all fallback templates have required structure."""
        required_keys = ['plan_steps', 'action_plan_summary', 'total_estimated_time', 'next_steps']
        
        for template_name, template in self.builder.FALLBACK_TEMPLATES.items():
            for key in required_keys:
                assert key in template, f"Missing {key} in {template_name} template"
                
            # Check plan_steps structure
            assert isinstance(template['plan_steps'], list)
            assert len(template['plan_steps']) > 0
            
            for step in template['plan_steps']:
                assert 'step_number' in step
                assert 'step_id' in step
                assert 'action' in step
                assert 'description' in step
                
    def test_factory_function(self):
        """Test factory function for backward compatibility."""
        builder = create_uvs_action_plan_builder()
        
        assert isinstance(builder, ActionPlanBuilderUVS)
        assert builder.uvs_enabled is True
        
    def test_factory_function_with_params(self):
        """Test factory function with parameters."""
        user_context = {"user_id": "test-user"}
        cache_manager = MagicMock()
        
        builder = create_uvs_action_plan_builder(user_context, cache_manager)
        
        assert isinstance(builder, ActionPlanBuilderUVS)
        assert builder.uvs_enabled is True


class TestActionPlanBuilderUVSEdgeCases(SSotAsyncTestCase):
    """Edge cases and error scenarios for ActionPlanBuilderUVS."""
    
    def setup_method(self, method=None):
        """Setup test fixtures."""
        super().setup_method(method)
        self.builder = ActionPlanBuilderUVS()
        
    async def test_generate_full_plan_llm_failure(self):
        """Test full plan generation when LLM fails."""
        uvs_context = UVSPlanContext(
            data_state=DataState.SUFFICIENT,
            available_data={"triage": "complete"},
            missing_components=[],
            user_goals="Optimization"
        )
        
        context = UserExecutionContext(
            run_id="test-run",
            user_id="test-user",
            metadata={"user_request": "Test"},
            agent_state=DeepAgentState(user_request="Test")
        )
        
        with patch.object(self.builder, '_get_llm_response_safe', return_value=None):
            result = await self.builder._generate_full_plan(context, uvs_context)
            
            # Should fall back to template-based plan
            assert isinstance(result, ActionPlanResult)
            assert len(result.plan_steps) > 0
            
    async def test_generate_full_plan_processing_failure(self):
        """Test full plan generation when processing fails."""
        uvs_context = UVSPlanContext(
            data_state=DataState.SUFFICIENT,
            available_data={"triage": "complete"},
            missing_components=[],
            user_goals="Optimization"
        )
        
        context = UserExecutionContext(
            run_id="test-run",
            user_id="test-user",
            metadata={"user_request": "Test"},
            agent_state=DeepAgentState(user_request="Test")
        )
        
        with patch.object(self.builder, '_get_llm_response_safe', return_value="test response"), \
             patch.object(self.builder, 'process_llm_response', side_effect=Exception("Processing failed")):
            
            result = await self.builder._generate_full_plan(context, uvs_context)
            
            # Should fall back to template-based plan
            assert isinstance(result, ActionPlanResult)
            assert len(result.plan_steps) > 0
            
    def test_hybrid_plan_missing_data_customization(self):
        """Test hybrid plan customization based on missing data."""
        uvs_context = UVSPlanContext(
            data_state=DataState.PARTIAL,
            available_data={"triage": "complete"},
            missing_components=["data_result", "optimizations_result"],
            user_goals="Test"
        )
        
        context = UserExecutionContext(
            run_id="test-run",
            user_id="test-user",
            metadata={"user_request": "Test"},
            agent_state=DeepAgentState(user_request="Test")
        )
        
        # This should add specific next steps for missing data
        result = asyncio.run(self.builder._generate_hybrid_plan(context, uvs_context))
        
        next_steps = result.metadata.custom_fields.get('next_steps', [])
        assert any("upload" in step.lower() or "data" in step.lower() for step in next_steps)
        
    def test_ensure_reporting_compatibility_missing_next_steps(self):
        """Test reporting compatibility when next_steps is missing."""
        plan = ActionPlanResult(
            action_plan_summary="Test summary",
            plan_steps=[PlanStep(step_id="1", description="Test")],
            actions=[]
        )
        
        # Ensure next_steps is not in custom_fields
        plan.metadata.custom_fields = {}
        
        uvs_context = UVSPlanContext(
            data_state=DataState.SUFFICIENT,
            available_data={"test": "data"},
            missing_components=[],
            user_goals="Test"
        )
        
        enhanced_plan = self.builder._ensure_reporting_compatibility(plan, uvs_context)
        
        assert 'next_steps' in enhanced_plan.metadata.custom_fields
        assert isinstance(enhanced_plan.metadata.custom_fields['next_steps'], list)
        assert len(enhanced_plan.metadata.custom_fields['next_steps']) > 0


class TestActionPlanBuilderUVSBusinessLogic(SSotAsyncTestCase):
    """Business logic tests for ActionPlanBuilderUVS."""
    
    def setup_method(self, method=None):
        """Setup test fixtures.""" 
        super().setup_method(method)
        self.builder = ActionPlanBuilderUVS()
        
    def test_uvs_core_principle_always_deliver_value(self):
        """Test that UVS always delivers value regardless of input."""
        # Test with completely empty context
        result = self.builder._get_ultimate_fallback_plan("test error")
        
        # Must always provide actionable value
        assert result.action_plan_summary != ""
        assert len(result.plan_steps) >= 3
        assert all(step.description != "" for step in result.plan_steps)
        assert result.total_estimated_time != ""
        
    def test_uvs_dynamic_workflow_adaptation(self):
        """Test that UVS adapts workflow based on available data."""
        # Test different data availability scenarios
        contexts = [
            # No data
            UVSPlanContext(DataState.INSUFFICIENT, {}, ["all"], "optimize"),
            # Partial data
            UVSPlanContext(DataState.PARTIAL, {"triage": "done"}, ["data"], "optimize"),  
            # Full data
            UVSPlanContext(DataState.SUFFICIENT, {"triage": "done", "data": "available", "optimizations": "ready"}, [], "optimize")
        ]
        
        for ctx in contexts:
            # Each context should produce different but valuable plans
            if ctx.data_state == DataState.INSUFFICIENT:
                result = asyncio.run(self.builder._generate_guidance_plan(
                    self._create_test_context(), ctx
                ))
                assert result.metadata.custom_fields['uvs_mode'] == 'guidance'
                
            elif ctx.data_state == DataState.PARTIAL:
                result = asyncio.run(self.builder._generate_hybrid_plan(
                    self._create_test_context(), ctx
                ))
                assert result.metadata.custom_fields['uvs_mode'] == 'hybrid'
                
            # All should provide value
            assert result.action_plan_summary != ""
            assert len(result.plan_steps) > 0
            
    def test_chat_is_king_principle(self):
        """Test that every response provides substantive chat value."""
        # Generate different plan types
        contexts = [
            UVSPlanContext(DataState.INSUFFICIENT, {}, ["all"], "optimize costs"),
            UVSPlanContext(DataState.ERROR, {}, [], "optimize", "system error")
        ]
        
        for ctx in contexts:
            if ctx.data_state == DataState.INSUFFICIENT:
                result = asyncio.run(self.builder._generate_guidance_plan(
                    self._create_test_context(), ctx
                ))
            else:
                result = asyncio.run(self.builder._generate_error_recovery_plan(
                    self._create_test_context(), ctx
                ))
            
            # Must provide substantive, actionable guidance
            assert len(result.action_plan_summary) > 50  # Substantial summary
            assert len(result.plan_steps) >= 2  # Multiple actionable steps
            assert all(len(step.description) > 20 for step in result.plan_steps)  # Detailed steps
            
    def _create_test_context(self) -> UserExecutionContext:
        """Helper to create test context."""
        return UserExecutionContext(
            run_id="test-run",
            user_id="test-user",
            metadata={"user_request": "test request"},
            agent_state=DeepAgentState(user_request="test request")
        )


if __name__ == "__main__":
    pytest.main([__file__])