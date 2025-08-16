"""
Comprehensive Example Prompts E2E Real LLM Testing Suite
Tests all 9 example prompts with real LLM calls and complete validation.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.state import DeepAgentState
from app.schemas import SubAgentLifecycle
from app.llm.llm_manager import LLMManager
from app.services.quality_gate_service import QualityGateService, ContentType, QualityLevel
from app.services.state_persistence_service import state_persistence_service
from app.agents.tool_dispatcher import ToolDispatcher
from app.ws_manager import WebSocketManager
from app.config import get_config
from app.core.exceptions import NetraException


# The 9 example prompts from EXAMPLE_PROMPTS list
EXAMPLE_PROMPTS = [
    "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",  # EP-001
    "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",  # EP-002
    "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",  # EP-003
    "I need to optimize the 'user_authentication' function. What advanced methods can I use?",  # EP-004
    "I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",  # EP-005
    "I want to audit all uses of KV caching in my system to find optimization opportunities.",  # EP-006
    "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",  # EP-007
    "@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?",  # EP-008
    "@Netra was the upgrade yesterday to GPT-5 worth it? Rollback anything where quality didn't improve much but cost was higher"  # EP-009
]


@pytest.fixture
def real_llm_prompt_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real LLM infrastructure for comprehensive example prompt testing."""
    supervisor = _create_real_supervisor(real_llm_manager, real_websocket_manager, real_tool_dispatcher)
    quality_service = _create_real_quality_service()
    return _build_prompt_test_setup(supervisor, quality_service, real_llm_manager)


def _create_real_supervisor(llm_manager: LLMManager, ws_manager: WebSocketManager, tool_dispatcher: ToolDispatcher) -> Supervisor:
    """Create real supervisor agent with dependencies."""
    supervisor = Supervisor(llm_manager, tool_dispatcher)
    supervisor.websocket_manager = ws_manager
    supervisor.thread_id = str(uuid.uuid4())
    supervisor.user_id = 'example-prompts-test-user'
    return supervisor


def _create_real_quality_service() -> QualityGateService:
    """Create real quality gate service for validation."""
    return QualityGateService()


def _build_prompt_test_setup(supervisor: Supervisor, quality_service: QualityGateService, llm_manager: LLMManager) -> Dict:
    """Build complete setup dictionary for prompt testing."""
    return {
        'supervisor': supervisor, 'quality_service': quality_service, 
        'llm_manager': llm_manager, 'run_id': str(uuid.uuid4())
    }


@pytest.mark.real_llm
class TestExamplePromptsComprehensive:
    """Test all 9 example prompts with real LLM calls and complete validation."""
    
    async def test_ep_001_cost_quality_optimization(self, real_llm_prompt_setup):
        """Test EP-001: Cost reduction with quality preservation constraints."""
        setup = real_llm_prompt_setup
        state = _create_cost_quality_state()
        result = await _execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[0], state)
        _validate_cost_optimization_result(result, setup)
    
    async def test_ep_002_latency_budget_constraint(self, real_llm_prompt_setup):
        """Test EP-002: Latency optimization with budget constraints."""
        setup = real_llm_prompt_setup
        state = _create_latency_constraint_state()
        result = await _execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[1], state)
        _validate_performance_optimization_result(result, setup)
    
    async def test_ep_003_capacity_planning_analysis(self, real_llm_prompt_setup):
        """Test EP-003: Capacity planning for usage increase."""
        setup = real_llm_prompt_setup
        state = _create_capacity_planning_state()
        result = await _execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[2], state)
        _validate_capacity_planning_result(result, setup)
    
    async def test_ep_004_function_optimization(self, real_llm_prompt_setup):
        """Test EP-004: Advanced function optimization methods."""
        setup = real_llm_prompt_setup
        state = _create_function_optimization_state()
        result = await _execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[3], state)
        _validate_function_optimization_result(result, setup)
    
    async def test_ep_005_model_selection_evaluation(self, real_llm_prompt_setup):
        """Test EP-005: Model selection and effectiveness analysis."""
        setup = real_llm_prompt_setup
        state = _create_model_selection_state()
        result = await _execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[4], state)
        _validate_model_selection_result(result, setup)
    
    async def test_ep_006_kv_cache_audit(self, real_llm_prompt_setup):
        """Test EP-006: KV cache audit and optimization opportunities."""
        setup = real_llm_prompt_setup
        state = _create_kv_cache_audit_state()
        result = await _execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[5], state)
        _validate_kv_cache_audit_result(result, setup)
    
    async def test_ep_007_multi_constraint_optimization(self, real_llm_prompt_setup):
        """Test EP-007: Multi-constraint optimization with usage scaling."""
        setup = real_llm_prompt_setup
        state = _create_multi_constraint_state()
        result = await _execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[6], state)
        _validate_multi_constraint_result(result, setup)
    
    async def test_ep_008_tool_migration_analysis(self, real_llm_prompt_setup):
        """Test EP-008: Tool migration to new models analysis."""
        setup = real_llm_prompt_setup
        state = _create_tool_migration_state()
        result = await _execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[7], state)
        _validate_tool_migration_result(result, setup)
    
    async def test_ep_009_rollback_cost_analysis(self, real_llm_prompt_setup):
        """Test EP-009: Rollback analysis and cost-effectiveness evaluation."""
        setup = real_llm_prompt_setup
        state = _create_rollback_analysis_state()
        result = await _execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[8], state)
        _validate_rollback_analysis_result(result, setup)


# State creation functions (≤8 lines each)
def _create_cost_quality_state() -> DeepAgentState:
    """Create state for cost-quality optimization test."""
    return DeepAgentState(
        user_request=EXAMPLE_PROMPTS[0],
        metadata={'test_type': 'cost_quality', 'prompt_id': 'EP-001'}
    )


def _create_latency_constraint_state() -> DeepAgentState:
    """Create state for latency optimization with budget constraints."""
    return DeepAgentState(
        user_request=EXAMPLE_PROMPTS[1],
        metadata={'test_type': 'latency_budget', 'prompt_id': 'EP-002'}
    )


def _create_capacity_planning_state() -> DeepAgentState:
    """Create state for capacity planning analysis."""
    return DeepAgentState(
        user_request=EXAMPLE_PROMPTS[2],
        metadata={'test_type': 'capacity_planning', 'prompt_id': 'EP-003'}
    )


def _create_function_optimization_state() -> DeepAgentState:
    """Create state for function optimization analysis."""
    return DeepAgentState(
        user_request=EXAMPLE_PROMPTS[3],
        metadata={'test_type': 'function_optimization', 'prompt_id': 'EP-004'}
    )


def _create_model_selection_state() -> DeepAgentState:
    """Create state for model selection evaluation."""
    return DeepAgentState(
        user_request=EXAMPLE_PROMPTS[4],
        metadata={'test_type': 'model_selection', 'prompt_id': 'EP-005'}
    )


def _create_kv_cache_audit_state() -> DeepAgentState:
    """Create state for KV cache audit."""
    return DeepAgentState(
        user_request=EXAMPLE_PROMPTS[5],
        metadata={'test_type': 'kv_cache_audit', 'prompt_id': 'EP-006'}
    )


def _create_multi_constraint_state() -> DeepAgentState:
    """Create state for multi-constraint optimization."""
    return DeepAgentState(
        user_request=EXAMPLE_PROMPTS[6],
        metadata={'test_type': 'multi_constraint', 'prompt_id': 'EP-007'}
    )


def _create_tool_migration_state() -> DeepAgentState:
    """Create state for tool migration analysis."""
    return DeepAgentState(
        user_request=EXAMPLE_PROMPTS[7],
        metadata={'test_type': 'tool_migration', 'prompt_id': 'EP-008'}
    )


def _create_rollback_analysis_state() -> DeepAgentState:
    """Create state for rollback analysis."""
    return DeepAgentState(
        user_request=EXAMPLE_PROMPTS[8],
        metadata={'test_type': 'rollback_analysis', 'prompt_id': 'EP-009'}
    )


# Core execution and validation functions
async def _execute_full_prompt_workflow(setup: Dict, prompt: str, state: DeepAgentState) -> Dict:
    """Execute complete prompt workflow with real LLM and state validation."""
    start_time = datetime.now(timezone.utc)
    supervisor = setup['supervisor']
    
    try:
        result_state = await supervisor.run(prompt, supervisor.thread_id, supervisor.user_id, setup['run_id'])
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()
        
        response_text = _extract_response_from_state(result_state)
        quality_passed = await _validate_response_quality(setup, response_text, prompt)
        
        return _create_workflow_result(True, prompt, execution_time, quality_passed, response_text, result_state)
    except Exception as e:
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()
        return _create_workflow_result(False, prompt, execution_time, False, "", None, str(e))


def _extract_response_from_state(result_state) -> str:
    """Extract response text from result state."""
    if not result_state:
        return "No response generated"
    
    # Check multiple possible response fields
    response_fields = ['final_response', 'reporting_result', 'optimizations_result']
    for field in response_fields:
        if hasattr(result_state, field) and getattr(result_state, field):
            response = getattr(result_state, field)
            return str(response) if response else "Empty response"
    
    return "Response not found in state"


async def _validate_response_quality(setup: Dict, response_text: str, prompt: str) -> bool:
    """Validate response quality using quality gate service."""
    try:
        quality_service = setup['quality_service']
        content_type = _determine_content_type(prompt)
        is_valid, score, feedback = await quality_service.validate_content(
            content=response_text, content_type=content_type, quality_level=QualityLevel.MEDIUM
        )
        return is_valid and len(response_text) >= 50 and score >= 70
    except Exception:
        return len(response_text) >= 50  # Fallback validation


def _determine_content_type(prompt: str) -> ContentType:
    """Determine content type based on prompt characteristics."""
    if any(keyword in prompt.lower() for keyword in ['cost', 'budget', 'money']):
        return ContentType.OPTIMIZATION_REPORT
    elif any(keyword in prompt.lower() for keyword in ['latency', 'performance', 'slow']):
        return ContentType.PERFORMANCE_ANALYSIS
    else:
        return ContentType.GENERAL_RESPONSE


def _create_workflow_result(success: bool, prompt: str, execution_time: float, quality_passed: bool, 
                          response: str, state: Optional[Any], error: Optional[str] = None) -> Dict:
    """Create workflow execution result."""
    return {
        'success': success, 'prompt': prompt, 'execution_time': execution_time,
        'quality_passed': quality_passed, 'response': response, 'state': state, 'error': error
    }


# Validation functions for each prompt type (≤8 lines each)
def _validate_cost_optimization_result(result: Dict, setup: Dict):
    """Validate cost optimization workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for cost optimization"
    assert any(keyword in result['response'].lower() for keyword in ['cost', 'optimization', 'budget'])


def _validate_performance_optimization_result(result: Dict, setup: Dict):
    """Validate performance optimization workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for performance optimization"
    assert any(keyword in result['response'].lower() for keyword in ['latency', 'performance', 'speed'])


def _validate_capacity_planning_result(result: Dict, setup: Dict):
    """Validate capacity planning workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for capacity planning"
    assert any(keyword in result['response'].lower() for keyword in ['capacity', 'usage', 'scale'])


def _validate_function_optimization_result(result: Dict, setup: Dict):
    """Validate function optimization workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for function optimization"
    assert any(keyword in result['response'].lower() for keyword in ['function', 'optimization', 'method'])


def _validate_model_selection_result(result: Dict, setup: Dict):
    """Validate model selection workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for model selection"
    assert any(keyword in result['response'].lower() for keyword in ['model', 'gpt', 'claude'])


def _validate_kv_cache_audit_result(result: Dict, setup: Dict):
    """Validate KV cache audit workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for KV cache audit"
    assert any(keyword in result['response'].lower() for keyword in ['cache', 'kv', 'audit'])


def _validate_multi_constraint_result(result: Dict, setup: Dict):
    """Validate multi-constraint optimization workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for multi-constraint optimization"
    assert any(keyword in result['response'].lower() for keyword in ['cost', 'latency', 'usage'])


def _validate_tool_migration_result(result: Dict, setup: Dict):
    """Validate tool migration workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for tool migration"
    assert any(keyword in result['response'].lower() for keyword in ['tool', 'migration', 'gpt-5'])


def _validate_rollback_analysis_result(result: Dict, setup: Dict):
    """Validate rollback analysis workflow results."""
    assert result['success'], f"Workflow failed: {result.get('error')}"
    assert result['quality_passed'], "Response quality validation failed"
    assert len(result['response']) > 100, "Response too short for rollback analysis"
    assert any(keyword in result['response'].lower() for keyword in ['rollback', 'upgrade', 'cost'])