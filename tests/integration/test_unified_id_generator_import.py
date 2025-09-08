"""
Test to ensure UnifiedIdGenerator import works correctly in agent_handler.

This test prevents regression of the import shadowing issue documented in
the Five Whys analysis for the error:
"cannot access local variable 'UnifiedIdGenerator' where it is not associated with a value"
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def test_unified_id_generator_import_in_agent_handler():
    """
    Regression test: Ensure UnifiedIdGenerator is properly imported and accessible
    throughout the agent_handler module without shadowing issues.
    """
    # Import the module to check for import errors
    from netra_backend.app.websocket_core import agent_handler
    
    # Verify UnifiedIdGenerator is available at module level
    assert hasattr(agent_handler, 'UnifiedIdGenerator')
    
    # Verify it's the correct class
    from shared.id_generation import UnifiedIdGenerator
    assert agent_handler.UnifiedIdGenerator == UnifiedIdGenerator
    
    # Test that the methods we use are available
    assert hasattr(UnifiedIdGenerator, 'generate_base_id')
    assert hasattr(UnifiedIdGenerator, 'generate_websocket_connection_id')
    
    # Test actual ID generation works
    thread_id = UnifiedIdGenerator.generate_base_id("thread")
    assert thread_id.startswith("thread_")
    
    ws_conn_id = UnifiedIdGenerator.generate_websocket_connection_id("test_user_123")
    assert ws_conn_id.startswith("ws_conn_")  # Check it starts with the right prefix


def test_agent_handler_handle_message_source_code():
    """
    Test that the _handle_message_v3_clean method source code is correct.
    
    This specifically tests the code path that was failing with the UnifiedIdGenerator error.
    We check the source code directly without instantiating objects to avoid complex dependencies.
    """
    from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
    
    # We can check the source code of the method directly without creating instances
    # This follows CLAUDE.md: testing what matters without unnecessary complexity
    import inspect
    
    # Get the source of the problematic method
    source = inspect.getsource(AgentMessageHandler._handle_message_v3_clean)
    
    # Verify the UnifiedIdGenerator is used correctly (not imported inside the function)
    assert "UnifiedIdGenerator.generate_base_id" in source, "UnifiedIdGenerator should be used in the method"
    assert "from shared.id_generation.unified_id_generator import UnifiedIdGenerator" not in source, \
           "UnifiedIdGenerator should NOT be imported inside the method (causes scope shadowing)"
    
    # Verify the method has the correct signature
    assert "async def _handle_message_v3_clean" in source
    assert "user_id: str" in source
    assert "websocket: WebSocket" in source
    assert "message: WebSocketMessage" in source
    

def test_no_duplicate_imports_in_agent_handler():
    """
    Ensure there are no duplicate or shadowing imports of UnifiedIdGenerator.
    """
    with open("netra_backend/app/websocket_core/agent_handler.py", "r") as f:
        content = f.read()
    
    # Count imports of UnifiedIdGenerator
    import_lines = [line for line in content.split('\n') if 'import UnifiedIdGenerator' in line]
    
    # Should only have one import at module level
    assert len(import_lines) == 1, f"Found {len(import_lines)} imports of UnifiedIdGenerator, expected 1"
    
    # Verify it's the correct import
    assert any('from shared.id_generation import UnifiedIdGenerator' in line for line in import_lines)
    

if __name__ == "__main__":
    pytest.main([__file__, "-v"])