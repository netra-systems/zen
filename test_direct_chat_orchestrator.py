#!/usr/bin/env python3
"""Direct test to reproduce ChatOrchestrator AttributeError"""

from unittest.mock import AsyncMock, Mock
from netra_backend.app.agents.chat_orchestrator_main import ChatOrchestrator

def test_direct_initialization():
    """Directly test ChatOrchestrator initialization"""
    print("Creating mock dependencies...")

    # Create minimal mocks
    mock_db_session = AsyncMock()
    mock_llm_manager = Mock()
    mock_websocket_manager = Mock()
    mock_tool_dispatcher = Mock()
    mock_cache_manager = Mock()

    print("Attempting ChatOrchestrator initialization...")

    try:
        orchestrator = ChatOrchestrator(
            db_session=mock_db_session,
            llm_manager=mock_llm_manager,
            websocket_manager=mock_websocket_manager,
            tool_dispatcher=mock_tool_dispatcher,
            cache_manager=mock_cache_manager,
            semantic_cache_enabled=True
        )
        print("✅ SUCCESS: ChatOrchestrator initialized without error")
        print(f"Has registry attribute: {hasattr(orchestrator, 'registry')}")
        print(f"Has agent_registry attribute: {hasattr(orchestrator, 'agent_registry')}")
        print(f"Has agent_factory attribute: {hasattr(orchestrator, 'agent_factory')}")
    except AttributeError as e:
        print(f"❌ FAILED: AttributeError occurred: {e}")
        print(f"Error details: {repr(e)}")
        print(f"Error args: {e.args}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Other error occurred: {e}")
        return False

    return True

if __name__ == "__main__":
    test_direct_initialization()