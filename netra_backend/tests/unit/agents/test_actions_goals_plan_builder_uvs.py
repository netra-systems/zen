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
from netra_backend.app.agents.actions_goals_plan_builder_uvs import ActionPlanBuilderUVS, DataState, UVSPlanContext, create_uvs_action_plan_builder
from netra_backend.app.agents.state import ActionPlanResult, PlanStep
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState, AgentMetadata
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class TestActionPlanBuilderUVS(SSotAsyncTestCase):
    """Unit tests for ActionPlanBuilderUVS - UVS-compliant action plan generation."""

    def setup_method(self, method=None):
        """Setup test fixtures following SSOT patterns."""
        super().setup_method(method)
        self.builder = ActionPlanBuilderUVS()
        self.sample_context = UserExecutionContext(run_id='test-run-123', user_id='test-user-456', metadata={'user_request': 'Help me optimize my AI costs', 'chat_thread_id': 'thread-789'}, agent_state=DeepAgentState(user_request='Help me optimize my AI costs', user_prompt='Help me optimize my AI costs', user_id='test-user-456'))

    def test_initialization(self):
        """Test ActionPlanBuilderUVS initialization."""
        assert self.builder.uvs_enabled is True
        assert hasattr(self.builder, 'FALLBACK_TEMPLATES')
        assert 'no_data' in self.builder.FALLBACK_TEMPLATES
        assert 'partial_data' in self.builder.FALLBACK_TEMPLATES
        assert 'error_recovery' in self.builder.FALLBACK_TEMPLATES

    def test_data_state_enum_values(self):
        """Test DataState enum contains all required values."""
        assert DataState.SUFFICIENT == 'sufficient'
        assert DataState.PARTIAL == 'partial'
        assert DataState.INSUFFICIENT == 'insufficient'
        assert DataState.ERROR == 'error'

    def test_uvs_plan_context_creation(self):
        """Test UVSPlanContext dataclass creation."""
        context = UVSPlanContext(data_state=DataState.SUFFICIENT, available_data={'triage': 'test_data'}, missing_components=['data_result'], user_goals='Cost optimization')
        assert context.data_state == DataState.SUFFICIENT
        assert context.available_data == {'triage': 'test_data'}
        assert context.missing_components == ['data_result']
        assert context.user_goals == 'Cost optimization'

    def test_assess_data_availability_sufficient(self):
        """Test data assessment with sufficient data."""
        context = UserExecutionContext(run_id='test-run', user_id='test-user', metadata={'triage_result': {'status': 'complete'}, 'data_result': {'usage': 'high'}, 'optimizations_result': {'savings': '30%'}, 'user_request': 'Optimize my AI spend'}, agent_state=DeepAgentState(user_request='Optimize my AI spend'))
        uvs_context = self.builder._assess_data_availability(context)
        assert uvs_context.data_state == DataState.SUFFICIENT
        assert 'triage' in uvs_context.available_data
        assert 'data' in uvs_context.available_data
        assert 'optimizations' in uvs_context.available_data
        assert len(uvs_context.missing_components) == 0
        assert uvs_context.user_goals == 'Optimize my AI spend'

    def test_assess_data_availability_partial(self):
        """Test data assessment with partial data."""
        context = UserExecutionContext(run_id='test-run', user_id='test-user', metadata={'triage_result': {'status': 'complete'}, 'user_request': 'Reduce costs'}, agent_state=DeepAgentState(user_request='Reduce costs'))
        uvs_context = self.builder._assess_data_availability(context)
        assert uvs_context.data_state == DataState.PARTIAL
        assert 'triage' in uvs_context.available_data
        assert 'data_result' in uvs_context.missing_components
        assert 'optimizations_result' in uvs_context.missing_components

    def test_assess_data_availability_insufficient(self):
        """Test data assessment with no data."""
        context = UserExecutionContext(run_id='test-run', user_id='test-user', metadata={'user_request': 'Help with AI optimization'}, agent_state=DeepAgentState(user_request='Help with AI optimization'))
        uvs_context = self.builder._assess_data_availability(context)
        assert uvs_context.data_state == DataState.INSUFFICIENT
        assert len(uvs_context.available_data) == 0
        assert 'triage_result' in uvs_context.missing_components
        assert 'data_result' in uvs_context.missing_components
        assert 'optimizations_result' in uvs_context.missing_components

    def test_create_plan_step_from_template(self):
        """Test plan step creation from template."""
        template_step = {'step_id': 'test_step', 'description': 'Test action', 'estimated_duration': '30 minutes', 'dependencies': ['step1'], 'resources_needed': ['Data access'], 'step_number': 1, 'action': 'Perform test action'}
        plan_step = self.builder._create_plan_step_from_template(template_step)
        assert isinstance(plan_step, PlanStep)
        assert plan_step.step_id == 'test_step'
        assert plan_step.description == 'Test action'
        assert plan_step.estimated_duration == '30 minutes'
        assert plan_step.dependencies == ['step1']
        assert plan_step.resources_needed == ['Data access']
        assert plan_step.status == 'pending'

    async def test_generate_guidance_plan(self):
        """Test guidance plan generation for no data scenario."""
        uvs_context = UVSPlanContext(data_state=DataState.INSUFFICIENT, available_data={}, missing_components=['triage_result', 'data_result'], user_goals='Cost optimization')
        result = await self.builder._generate_guidance_plan(self.sample_context, uvs_context)
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary is not None
        assert 'cost' in result.action_plan_summary.lower()
        assert len(result.plan_steps) > 0
        assert result.metadata.custom_fields['uvs_mode'] == 'guidance'
        assert result.metadata.custom_fields['data_state'] == 'insufficient'
        assert 'next_steps' in result.metadata.custom_fields
        assert 'user_guidance' in result.metadata.custom_fields

    async def test_generate_hybrid_plan(self):
        """Test hybrid plan generation for partial data."""
        uvs_context = UVSPlanContext(data_state=DataState.PARTIAL, available_data={'data': {'usage': 'high'}}, missing_components=['optimizations_result'], user_goals='Reduce costs')
        result = await self.builder._generate_hybrid_plan(self.sample_context, uvs_context)
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary is not None
        assert len(result.plan_steps) > 0
        assert result.metadata.custom_fields['uvs_mode'] == 'hybrid'
        assert result.metadata.custom_fields['data_state'] == 'partial'
        assert 'next_steps' in result.metadata.custom_fields

    async def test_generate_error_recovery_plan(self):
        """Test error recovery plan generation."""
        uvs_context = UVSPlanContext(data_state=DataState.ERROR, available_data={}, missing_components=[], user_goals='Optimize costs', error_details='Database connection failed')
        result = await self.builder._generate_error_recovery_plan(self.sample_context, uvs_context)
        assert isinstance(result, ActionPlanResult)
        assert 'Database connection failed' in result.action_plan_summary
        assert len(result.plan_steps) > 0
        assert result.metadata.custom_fields['uvs_mode'] == 'error_recovery'
        assert result.metadata.custom_fields['error'] == 'Database connection failed'
        assert 'next_steps' in result.metadata.custom_fields

    def test_get_ultimate_fallback_plan(self):
        """Test ultimate fallback plan generation."""
        error_msg = 'Critical system failure'
        result = self.builder._get_ultimate_fallback_plan(error_msg)
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary is not None
        assert len(result.plan_steps) >= 3
        assert result.metadata.custom_fields['uvs_mode'] == 'ultimate_fallback'
        assert result.metadata.custom_fields['error'] == error_msg
        assert result.metadata.custom_fields['recovery_mode'] is True
        assert 'next_steps' in result.metadata.custom_fields
        assert 'user_guidance' in result.metadata.custom_fields

    async def test_generate_adaptive_plan_insufficient_data(self):
        """Test adaptive plan generation with no data."""
        context = UserExecutionContext(run_id='test-run', user_id='test-user', metadata={'user_request': 'Help optimize AI'}, agent_state=DeepAgentState(user_request='Help optimize AI'))
        result = await self.builder.generate_adaptive_plan(context)
        assert isinstance(result, ActionPlanResult)
        assert result.action_plan_summary is not None
        assert len(result.plan_steps) > 0
        assert result.metadata.custom_fields['uvs_mode'] == 'guidance'
        assert result.metadata.custom_fields['data_state'] == 'insufficient'

    def test_factory_function(self):
        """Test factory function for backward compatibility."""
        builder = create_uvs_action_plan_builder()
        assert isinstance(builder, ActionPlanBuilderUVS)
        assert builder.uvs_enabled is True
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')