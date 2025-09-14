#!/usr/bin/env python3
"""Debug why the pytest test is passing when it should fail"""

import pytest
from unittest.mock import Mock, AsyncMock
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.chat_orchestrator_main import ChatOrchestrator

def test_debug_behavior():
    """Debug the test behavior to understand why it's passing"""

    print("Creating SSOT mocks...")
    mock_db_session = SSotMockFactory.create_database_session_mock()
    mock_llm_manager = SSotMockFactory.create_mock_llm_manager()
    mock_websocket_manager = SSotMockFactory.create_websocket_manager_mock()

    # Create simple tool dispatcher mock (not available in SSOT factory yet)
    mock_tool_dispatcher = AsyncMock()
    mock_tool_dispatcher.execute = AsyncMock()
    mock_tool_dispatcher.get_available_tools = AsyncMock(return_value=[])

    mock_cache_manager = Mock()

    print("Created mocks successfully")

    print("Attempting ChatOrchestrator initialization...")

    # Try with pytest.raises to see what happens
    try:
        with pytest.raises(AttributeError) as exc_info:
            orchestrator = ChatOrchestrator(
                db_session=mock_db_session,
                llm_manager=mock_llm_manager,
                websocket_manager=mock_websocket_manager,
                tool_dispatcher=mock_tool_dispatcher,
                cache_manager=mock_cache_manager,
                semantic_cache_enabled=True
            )

        print(f"pytest.raises captured exception: {exc_info.value}")
        print(f"Exception message: {str(exc_info.value)}")
        return True

    except Exception as e:
        print(f"pytest.raises failed to catch exception: {e}")
        print(f"Type of exception: {type(e)}")

        # Try direct initialization to see what happens
        try:
            orchestrator = ChatOrchestrator(
                db_session=mock_db_session,
                llm_manager=mock_llm_manager,
                websocket_manager=mock_websocket_manager,
                tool_dispatcher=mock_tool_dispatcher,
                cache_manager=mock_cache_manager,
                semantic_cache_enabled=True
            )
            print("❌ Direct initialization succeeded - no AttributeError!")
            print(f"Has registry: {hasattr(orchestrator, 'registry')}")
            print(f"Has agent_registry: {hasattr(orchestrator, 'agent_registry')}")
            return False
        except AttributeError as ae:
            print(f"✅ Direct initialization failed with AttributeError: {ae}")
            return True
        except Exception as ex:
            print(f"Direct initialization failed with other error: {ex}")
            return False

if __name__ == "__main__":
    test_debug_behavior()