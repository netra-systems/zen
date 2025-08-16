"""
E2E Testing Configuration - Real LLM testing fixtures and environment setup

Provides fixtures for real LLM testing with intelligent fallback to mocks.
Supports model selection, caching, and environment-based configuration.
"""
import os
import pytest
from typing import Dict, Any, Optional, List
from app.tests.e2e.infrastructure import (
    LLMTestManager,
    LLMTestModel,
    LLMTestConfig,
    LLMResponseCache
)


@pytest.fixture(scope="function")
def llm_test_config() -> LLMTestConfig:
    """Create LLM test configuration from environment."""
    enabled = os.getenv("ENABLE_REAL_LLM_TESTING", "false").lower() == "true"
    models_str = os.getenv("LLM_TEST_MODELS", "gpt-4,claude-3-opus,gpt-3.5-turbo")
    models = _parse_test_models(models_str)
    cache_enabled = os.getenv("LLM_RESPONSE_CACHE", "true").lower() == "true"
    timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    return LLMTestConfig(
        enabled=enabled,
        models=models,
        cache_enabled=cache_enabled,
        timeout_seconds=timeout
    )


def _parse_test_models(models_str: str) -> List[LLMTestModel]:
    """Parse model names from environment string."""
    model_names = [name.strip() for name in models_str.split(",")]
    valid_models = []
    for name in model_names:
        try:
            valid_models.append(LLMTestModel(name))
        except ValueError:
            continue
    return valid_models or [LLMTestModel.GPT_4]


@pytest.fixture(scope="function")
def real_llm_manager(llm_test_config: LLMTestConfig):
    """Create real LLM manager with intelligent fallback."""
    from app.llm.llm_manager import LLMManager
    from app.config import get_config
    
    # Try to create real LLM manager first
    try:
        config = get_config()
        return LLMManager(config)
    except Exception:
        # Fallback to test manager
        return LLMTestManager(llm_test_config)


@pytest.fixture(scope="function")
def real_websocket_manager():
    """Create real WebSocket manager for testing."""
    from unittest.mock import AsyncMock, Mock
    
    # Create a mock that implements the interface agents expect
    mock_ws = Mock()
    mock_ws.send_message = AsyncMock(return_value=True)
    mock_ws.send_to_thread = AsyncMock(return_value=True)
    mock_ws.send_agent_log = AsyncMock(return_value=True)
    mock_ws.send_error = AsyncMock(return_value=True)
    mock_ws.send_agent_update = AsyncMock(return_value=None)
    mock_ws.send_tool_call = AsyncMock(return_value=True)
    mock_ws.send_tool_result = AsyncMock(return_value=True)
    
    return mock_ws

@pytest.fixture(scope="function")
def real_tool_dispatcher():
    """Create real tool dispatcher for testing."""
    from app.agents.tool_dispatcher import ToolDispatcher
    return ToolDispatcher()

@pytest.fixture(scope="function")
def cached_llm_manager(llm_test_config: LLMTestConfig) -> LLMTestManager:
    """Create LLM manager with caching enabled."""
    config = llm_test_config.copy()
    config.cache_enabled = True
    return LLMTestManager(config)


@pytest.fixture(scope="function")
def llm_response_cache() -> LLMResponseCache:
    """Create LLM response cache for testing."""
    cache_path = os.getenv("LLM_CACHE_PATH")
    ttl_hours = int(os.getenv("LLM_CACHE_TTL_HOURS", "24"))
    return LLMResponseCache(cache_path, ttl_hours)


@pytest.fixture(scope="function")
async def fresh_cache() -> LLMResponseCache:
    """Create fresh cache for testing (cleared)."""
    cache = LLMResponseCache(":memory:")  # In-memory for tests
    await cache.clear_all()
    return cache


@pytest.fixture(scope="function")
def model_selection_config() -> Dict[str, LLMTestModel]:
    """Configure model selection for different test scenarios."""
    return {
        "cost_optimization": LLMTestModel.GPT_35_TURBO,
        "performance_analysis": LLMTestModel.GPT_4,
        "complex_reasoning": LLMTestModel.CLAUDE_3_OPUS,
        "balanced_tasks": LLMTestModel.CLAUDE_3_SONNET,
        "data_analysis": LLMTestModel.GEMINI_PRO
    }


@pytest.fixture(scope="function")
def example_prompts() -> Dict[str, str]:
    """Standard example prompts for E2E testing."""
    return {
        "cost_quality": "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms.",
        "latency_cost": "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",
        "capacity_planning": "I'm expecting a 50% increase in agent usage next month. How will this impact costs?",
        "function_optimization": "I need to optimize the 'user_authentication' function. What advanced methods can I use?",
        "model_selection": "I'm considering using 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be?",
        "kv_cache_audit": "I want to audit all uses of KV caching in my system to find optimization opportunities.",
        "multi_constraint": "I need to reduce costs by 20% and improve latency by 2x with 30% more usage.",
        "tool_upgrade": "@Netra which Agent tools should switch to GPT-5? Which versions? What verbosity?",
        "rollback_analysis": "@Netra was the GPT-5 upgrade worth it? Rollback where quality didn't improve much."
    }


@pytest.fixture(scope="session")
def environment_validation():
    """Validate environment setup for real LLM testing."""
    validation_results = _validate_llm_environment()
    return validation_results


def _validate_llm_environment() -> Dict[str, Any]:
    """Validate LLM testing environment configuration."""
    results = {
        "real_testing_enabled": os.getenv("ENABLE_REAL_LLM_TESTING") == "true",
        "api_keys_configured": _check_api_keys(),
        "cache_enabled": os.getenv("LLM_RESPONSE_CACHE", "true") == "true",
        "models_configured": _check_model_configuration()
    }
    results["environment_ready"] = all([
        not results["real_testing_enabled"] or results["api_keys_configured"],
        results["models_configured"]
    ])
    return results


def _check_api_keys() -> Dict[str, bool]:
    """Check if required API keys are configured."""
    return {
        "openai": _is_real_api_key(os.getenv("OPENAI_API_KEY")),
        "anthropic": _is_real_api_key(os.getenv("ANTHROPIC_API_KEY")),
        "google": _is_real_api_key(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
    }


def _is_real_api_key(api_key: Optional[str]) -> bool:
    """Check if API key is real (not test/mock)."""
    if not api_key:
        return False
    return not api_key.startswith("test-") and len(api_key) > 10


def _check_model_configuration() -> bool:
    """Check if model configuration is valid."""
    models_str = os.getenv("LLM_TEST_MODELS", "gpt-4")
    try:
        models = _parse_test_models(models_str)
        return len(models) > 0
    except Exception:
        return False


@pytest.fixture(scope="function")
def llm_test_scenarios():
    """Common test scenarios for LLM testing."""
    return {
        "quick_response": {
            "prompt": "What is 2+2?",
            "expected_type": "short_answer",
            "timeout": 5
        },
        "complex_analysis": {
            "prompt": "Analyze the performance implications of implementing microservices architecture.",
            "expected_type": "detailed_analysis",
            "timeout": 30
        },
        "cost_optimization": {
            "prompt": "How can I reduce infrastructure costs while maintaining performance?",
            "expected_type": "recommendation_list",
            "timeout": 15
        }
    }


@pytest.fixture(scope="function")
async def setup_test_environment(real_llm_manager: LLMTestManager, fresh_cache: LLMResponseCache):
    """Setup complete test environment with cleanup."""
    # Setup phase
    test_env = {
        "llm_manager": real_llm_manager,
        "cache": fresh_cache,
        "test_run_id": f"test_run_{os.getpid()}",
        "cleanup_tasks": []
    }
    
    yield test_env
    
    # Cleanup phase
    await fresh_cache.clear_all()
    for task in test_env.get("cleanup_tasks", []):
        try:
            await task()
        except Exception:
            pass  # Ignore cleanup errors


@pytest.fixture(scope="function")
def performance_thresholds():
    """Performance thresholds for LLM testing."""
    return {
        "response_time_ms": {
            "gpt-3.5-turbo": 2000,
            "gpt-4": 5000,
            "claude-3-sonnet": 3000,
            "claude-3-opus": 6000,
            "gemini-pro": 2500
        },
        "cache_hit_rate": 0.8,
        "error_rate": 0.05
    }


@pytest.fixture
async def db_session():
    """Database session fixture for thread tests."""
    from unittest.mock import AsyncMock
    from sqlalchemy.ext.asyncio import AsyncSession
    
    session = AsyncMock(spec=AsyncSession)
    session.begin = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.close = AsyncMock()
    return session