"""
Test fixtures for corpus admin testing.

Provides standardized fixtures for creating test states, agents, and environments
for corpus admin testing scenarios.
"""

from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

from netra_backend.app.agents.corpus_admin.agent import CorpusAdminSubAgent
from netra_backend.app.agents.corpus_admin.models import (
    CorpusMetadata,
    CorpusOperation,
    CorpusType,
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager


def create_test_deep_state(
    user_request: str = "test request",
    chat_thread_id: str = "test_thread",
    user_id: str = "test_user",
    **kwargs
) -> DeepAgentState:
    """
    Create a test DeepAgentState with default or custom values.
    
    Args:
        user_request: The user's request text
        chat_thread_id: The chat thread identifier
        user_id: The user identifier
        **kwargs: Additional attributes to set on the state
    
    Returns:
        DeepAgentState configured for testing
    """
    state = DeepAgentState(
        user_request=user_request,
        chat_thread_id=chat_thread_id,
        user_id=user_id
    )
    
    # Add any additional attributes
    for key, value in kwargs.items():
        setattr(state, key, value)
    
    return state


def create_test_corpus_metadata(
    corpus_id: str = "test_corpus",
    name: str = "Test Corpus",
    corpus_type: CorpusType = CorpusType.KNOWLEDGE_BASE,
    **kwargs
) -> CorpusMetadata:
    """
    Create test corpus metadata with default or custom values.
    
    Args:
        corpus_id: The corpus identifier
        name: The corpus name
        corpus_type: The type of corpus
        **kwargs: Additional metadata fields
    
    Returns:
        CorpusMetadata configured for testing
    """
    return CorpusMetadata(
        corpus_id=corpus_id,
        name=name,
        type=corpus_type,
        description=kwargs.get("description", "Test corpus description"),
        version=kwargs.get("version", "1.0.0"),
        created_by=kwargs.get("created_by", "test_user"),
        tags=kwargs.get("tags", ["test", "corpus"]),
        settings=kwargs.get("settings", {}),
    )


async def create_test_corpus_admin_agent(
    with_real_llm: bool = False,
    websocket_manager: Optional[Any] = None
) -> CorpusAdminSubAgent:
    """
    Create a test corpus admin agent with mocked or real components.
    
    Args:
        with_real_llm: Whether to use a real LLM manager (requires API keys)
        websocket_manager: Optional websocket manager for status updates
    
    Returns:
        CorpusAdminSubAgent configured for testing
    """
    if with_real_llm:
        # This would require real API keys - typically not used in tests
        llm_manager = LLMManager()
    else:
        # Create mock LLM manager
        llm_manager = AsyncMock(spec=LLMManager)
        llm_manager.ask_llm = AsyncMock(return_value="Mock LLM response")
        llm_manager.get_model_info = MagicMock(return_value={"model": "mock-model"})
    
    # Create tool dispatcher
    tool_dispatcher = ToolDispatcher()
    
    # Create agent
    agent = CorpusAdminSubAgent(
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        websocket_manager=websocket_manager
    )
    
    return agent


def create_test_execution_context(
    run_id: str = "test_run_001",
    agent_name: str = "CorpusAdminSubAgent",
    state: Optional[DeepAgentState] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a test execution context for corpus admin operations.
    
    Args:
        run_id: The execution run identifier
        agent_name: The agent name
        state: Optional DeepAgentState (creates default if not provided)
        **kwargs: Additional context fields
    
    Returns:
        Dictionary representing an execution context
    """
    if state is None:
        state = create_test_deep_state()
    
    return {
        "run_id": run_id,
        "agent_name": agent_name,
        "state": state,
        "stream_updates": kwargs.get("stream_updates", False),
        "thread_id": kwargs.get("thread_id", state.chat_thread_id),
        "user_id": kwargs.get("user_id", state.user_id),
        **kwargs
    }


class MockAsyncContextManager:
    """
    Helper class for creating async context managers in tests.
    """
    def __init__(self, return_value=None):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


def create_async_mock_with_context(return_value=None):
    """
    Create an async mock that can be used as a context manager.
    
    Args:
        return_value: Value to return from the context manager
    
    Returns:
        AsyncMock configured as a context manager
    """
    mock = AsyncMock()
    mock.return_value = MockAsyncContextManager(return_value)
    return mock