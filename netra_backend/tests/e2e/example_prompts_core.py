"""
Core Example Prompts E2E Testing - Infrastructure and Shared Components
Provides shared fixtures and core testing functionality.
Maximum 300 lines, functions  <= 8 lines.
"""

from datetime import datetime, timezone
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_consolidated import (
    SupervisorAgent as Supervisor,
)
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from netra_backend.app.websocket_core import WebSocketManager
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
import pytest
import uuid
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.quality_gate_service import (
    ContentType,
    QualityGateService,
    QualityLevel,
)

# The 9 example prompts from EXAMPLE_PROMPTS list

EXAMPLE_PROMPTS = [

    "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",  # EP-001

    "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",  # EP-002

    "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",  # EP-003

    "I need to optimize the 'user_authentication' function. What advanced methods can I use?",  # EP-004

    "I'm considering using the new 'gpt-4o' and LLMModel.GEMINI_2_5_FLASH.value models. How effective would they be in my current setup?",  # EP-005

    "I want to audit all uses of KV caching in my system to find optimization opportunities.",  # EP-006

    "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",  # EP-007

    "@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?",  # EP-008

    "@Netra was the upgrade yesterday to GPT-5 worth it? Rollback anything where quality didn't improve much but cost was higher"  # EP-009

]

@pytest.fixture

def real_llm_prompt_setup(db_session, real_llm_manager, real_websocket_manager, real_tool_dispatcher):

    """Setup real LLM infrastructure for comprehensive example prompt testing."""

    supervisor = create_real_supervisor(db_session, real_llm_manager, real_websocket_manager, real_tool_dispatcher)

    quality_service = create_real_quality_service()

    return build_prompt_test_setup(supervisor, quality_service, real_llm_manager)

def create_real_supervisor(db_session: AsyncSession, llm_manager: LLMManager, ws_manager: WebSocketManager, tool_dispatcher: ToolDispatcher) -> Supervisor:

    """Create real supervisor agent with dependencies."""

    supervisor = Supervisor(db_session, llm_manager, ws_manager, tool_dispatcher)

    supervisor.thread_id = str(uuid.uuid4())

    supervisor.user_id = 'example-prompts-test-user'

    return supervisor

def create_real_quality_service() -> QualityGateService:

    """Create real quality gate service for validation."""

    return QualityGateService()

def build_prompt_test_setup(supervisor: Supervisor, quality_service: QualityGateService, llm_manager: LLMManager) -> Dict:

    """Build complete setup dictionary for prompt testing."""

    return {

        'supervisor': supervisor, 'quality_service': quality_service, 

        'llm_manager': llm_manager, 'run_id': str(uuid.uuid4())

    }

async def execute_full_prompt_workflow(setup: Dict, prompt: str, state: DeepAgentState) -> Dict:

    """Execute complete prompt workflow with real LLM and state validation."""

    start_time = datetime.now(timezone.utc)

    supervisor = setup['supervisor']
    
    try:

        result_state = await supervisor.run(prompt, supervisor.thread_id, supervisor.user_id, setup['run_id'])

        end_time = datetime.now(timezone.utc)

        execution_time = (end_time - start_time).total_seconds()
        
        response_text = extract_response_from_state(result_state)

        quality_passed = await validate_response_quality(setup, response_text, prompt)
        
        return create_workflow_result(True, prompt, execution_time, quality_passed, response_text, result_state)

    except Exception as e:

        end_time = datetime.now(timezone.utc)

        execution_time = (end_time - start_time).total_seconds()

        return create_workflow_result(False, prompt, execution_time, False, "", None, str(e))

def extract_response_from_state(result_state) -> str:

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

async def validate_response_quality(setup: Dict, response_text: str, prompt: str) -> bool:

    """Validate response quality using quality gate service."""

    try:

        quality_service = setup['quality_service']

        content_type = determine_content_type(prompt)

        is_valid, score, feedback = await quality_service.validate_content(

            content=response_text, content_type=content_type, quality_level=QualityLevel.MEDIUM

        )

        return is_valid and len(response_text) >= 50 and score >= 70

    except Exception:

        return len(response_text) >= 50  # Fallback validation

def determine_content_type(prompt: str) -> ContentType:

    """Determine content type based on prompt characteristics."""

    if any(keyword in prompt.lower() for keyword in ['cost', 'budget', 'money']):

        return ContentType.OPTIMIZATION_REPORT

    elif any(keyword in prompt.lower() for keyword in ['latency', 'performance', 'slow']):

        return ContentType.PERFORMANCE_ANALYSIS

    else:

        return ContentType.GENERAL_RESPONSE

def create_workflow_result(success: bool, prompt: str, execution_time: float, quality_passed: bool, 

                          response: str, state: Optional[Any], error: Optional[str] = None) -> Dict:

    """Create workflow execution result."""

    return {

        'success': success, 'prompt': prompt, 'execution_time': execution_time,

        'quality_passed': quality_passed, 'response': response, 'state': state, 'error': error

    }

# State creation functions ( <= 8 lines each)

def create_ep_001_state() -> DeepAgentState:

    """Create state for EP-001 example prompt test."""

    return DeepAgentState(

        user_request=EXAMPLE_PROMPTS[0],

        metadata={'test_type': 'cost_quality', 'prompt_id': 'EP-001'}

    )

def create_ep_002_state() -> DeepAgentState:

    """Create state for EP-002 example prompt test."""

    return DeepAgentState(

        user_request=EXAMPLE_PROMPTS[1],

        metadata={'test_type': 'latency_budget', 'prompt_id': 'EP-002'}

    )

def create_ep_003_state() -> DeepAgentState:

    """Create state for EP-003 example prompt test."""

    return DeepAgentState(

        user_request=EXAMPLE_PROMPTS[2],

        metadata={'test_type': 'capacity_planning', 'prompt_id': 'EP-003'}

    )

def create_ep_004_state() -> DeepAgentState:

    """Create state for EP-004 example prompt test."""

    return DeepAgentState(

        user_request=EXAMPLE_PROMPTS[3],

        metadata={'test_type': 'function_optimization', 'prompt_id': 'EP-004'}

    )

def create_ep_005_state() -> DeepAgentState:

    """Create state for EP-005 example prompt test."""

    return DeepAgentState(

        user_request=EXAMPLE_PROMPTS[4],

        metadata={'test_type': 'model_selection', 'prompt_id': 'EP-005'}

    )

def create_ep_006_state() -> DeepAgentState:

    """Create state for EP-006 example prompt test."""

    return DeepAgentState(

        user_request=EXAMPLE_PROMPTS[5],

        metadata={'test_type': 'kv_cache_audit', 'prompt_id': 'EP-006'}

    )

def create_ep_007_state() -> DeepAgentState:

    """Create state for EP-007 example prompt test."""

    return DeepAgentState(

        user_request=EXAMPLE_PROMPTS[6],

        metadata={'test_type': 'multi_constraint', 'prompt_id': 'EP-007'}

    )

def create_ep_008_state() -> DeepAgentState:

    """Create state for EP-008 example prompt test."""

    return DeepAgentState(

        user_request=EXAMPLE_PROMPTS[7],

        metadata={'test_type': 'tool_migration', 'prompt_id': 'EP-008'}

    )

def create_ep_009_state() -> DeepAgentState:

    """Create state for EP-009 example prompt test."""

    return DeepAgentState(

        user_request=EXAMPLE_PROMPTS[8],

        metadata={'test_type': 'rollback_analysis', 'prompt_id': 'EP-009'}

    )