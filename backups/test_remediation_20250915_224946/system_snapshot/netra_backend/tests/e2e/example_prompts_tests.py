"""
Example Prompts and Quality Validation Tests
Tests for specific example prompts (EP-005, EP-008, EP-009) with real LLM validation
"""

from typing import Dict, List
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


import pytest

from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.services.quality_gate_service import (
    ContentType,
    QualityGateService,
    QualityLevel,
)
from netra_backend.tests.e2e.model_effectiveness_tests import (
    _execute_model_selection_workflow,
    _validate_model_effectiveness_results,
)

@pytest.mark.real_llm
class TestExamplePromptsModelSelection:
    """Test specific example prompts EP-005, EP-008, EP-009 with real LLM validation."""
    
    async def test_ep_005_model_effectiveness_real_llm(self, model_selection_setup):
        """Test EP-005: Model effectiveness analysis using real LLM."""
        setup = model_selection_setup
        state = _create_ep_005_state()
        results = await _execute_model_selection_workflow(setup, state)
        await _validate_ep_005_results(results, state, setup)
    
    async def test_ep_008_tool_migration_real_llm(self, model_selection_setup):
        """Test EP-008: Tool migration to GPT-5 using real LLM."""
        setup = model_selection_setup
        state = _create_ep_008_state()
        results = await _execute_model_selection_workflow(setup, state)
        await _validate_ep_008_results(results, state, setup)
    
    async def test_ep_009_upgrade_rollback_real_llm(self, model_selection_setup):
        """Test EP-009: Upgrade rollback analysis using real LLM."""
        setup = model_selection_setup
        state = _create_ep_009_state()
        results = await _execute_model_selection_workflow(setup, state)
        await _validate_ep_009_results(results, state, setup)

def _create_ep_005_state() -> DeepAgentState:
    """Create state for EP-005 example prompt test."""
    return DeepAgentState(
        user_request="I'm considering using the new 'gpt-4o' and LLMModel.GEMINI_2_5_FLASH.value models. How effective would they be in my current setup?",
        metadata={'test_type': 'ep_005', 'prompt_id': 'EP-005', 'candidate_models': ['gpt-4o', LLMModel.GEMINI_2_5_FLASH.value]}
    )

def _create_ep_008_state() -> DeepAgentState:
    """Create state for EP-008 example prompt test."""
    return DeepAgentState(
        user_request="@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?",
        metadata={'test_type': 'ep_008', 'prompt_id': 'EP-008', 'target_model': 'GPT-5'}
    )

def _create_ep_009_state() -> DeepAgentState:
    """Create state for EP-009 example prompt test."""
    return DeepAgentState(
        user_request="@Netra was the upgrade yesterday to GPT-5 worth it? Rollback anything where quality didn't improve much but cost was higher",
        metadata={'test_type': 'ep_009', 'prompt_id': 'EP-009', 'upgrade_model': 'GPT-5', 'analysis_type': 'rollback'}
    )

async def _validate_ep_005_results(results: List[Dict], state: DeepAgentState, setup: Dict):
    """Validate EP-005 results with enhanced quality checks."""
    _validate_model_effectiveness_results(results, state)
    await _validate_response_quality_ep_005(results, setup)

async def _validate_ep_008_results(results: List[Dict], state: DeepAgentState, setup: Dict):
    """Validate EP-008 results with enhanced quality checks."""
    _validate_tool_migration_results(results, state)
    await _validate_response_quality_ep_008(results, setup)

async def _validate_ep_009_results(results: List[Dict], state: DeepAgentState, setup: Dict):
    """Validate EP-009 results with enhanced quality checks."""
    _validate_rollback_analysis_results(results, state)
    await _validate_response_quality_ep_009(results, setup)

def _validate_tool_migration_results(results: List[Dict], state: DeepAgentState):
    """Validate tool migration workflow results."""
    assert len(results) > 0, "No results returned from workflow"
    assert 'GPT-5' in state.user_request
    assert any('tool' in str(result).lower() for result in results)

def _validate_rollback_analysis_results(results: List[Dict], state: DeepAgentState):
    """Validate rollback analysis workflow results."""
    assert len(results) > 0, "No results returned from workflow"
    assert 'rollback' in state.user_request.lower()
    assert 'GPT-5' in state.user_request

async def _validate_response_quality_ep_005(results: List[Dict], setup: Dict):
    """Validate response quality for EP-005 using quality gate service."""
    quality_service = QualityGateService()
    final_result = results[-1] if results else None
    
    if final_result:
        response_text = _extract_response_text_model(final_result)
        is_valid, score, feedback = await quality_service.validate_content(
            content=response_text, content_type=ContentType.MODEL_ANALYSIS, quality_level=QualityLevel.MEDIUM
        )
        assert is_valid, f"EP-005 response quality validation failed: {feedback}"
        assert score >= 70, f"EP-005 quality score too low: {score}"

async def _validate_response_quality_ep_008(results: List[Dict], setup: Dict):
    """Validate response quality for EP-008 using quality gate service."""
    quality_service = QualityGateService()
    final_result = results[-1] if results else None
    
    if final_result:
        response_text = _extract_response_text_model(final_result)
        is_valid, score, feedback = await quality_service.validate_content(
            content=response_text, content_type=ContentType.MIGRATION_PLAN, quality_level=QualityLevel.MEDIUM
        )
        assert is_valid, f"EP-008 response quality validation failed: {feedback}"
        assert score >= 70, f"EP-008 quality score too low: {score}"

async def _validate_response_quality_ep_009(results: List[Dict], setup: Dict):
    """Validate response quality for EP-009 using quality gate service."""
    quality_service = QualityGateService()
    final_result = results[-1] if results else None
    
    if final_result:
        response_text = _extract_response_text_model(final_result)
        is_valid, score, feedback = await quality_service.validate_content(
            content=response_text, content_type=ContentType.ROLLBACK_ANALYSIS, quality_level=QualityLevel.MEDIUM
        )
        assert is_valid, f"EP-009 response quality validation failed: {feedback}"
        assert score >= 70, f"EP-009 quality score too low: {score}"

def _extract_response_text_model(result) -> str:
    """Extract response text from model selection workflow result."""
    if isinstance(result, dict):
        return str(result.get('execution_result', result.get('response', str(result))))
    return str(result)