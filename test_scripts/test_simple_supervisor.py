#!/usr/bin/env python3
"""Simple test script to verify SupervisorAgent refactoring works correctly."""

import sys
import os
from shared.isolated_environment import IsolatedEnvironment

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    
    print("SUCCESS: Imported SupervisorAgent and dependencies")
    
    # Test new constructor signature
    llm_manager = Mock(spec=LLMManager)
    websocket_manager = Mock()
    tool_dispatcher = Mock(spec=ToolDispatcher)
    mock_session_factory = Mock()
    
    # This should work with the new signature
    supervisor = SupervisorAgent(
        llm_manager, 
        websocket_manager, 
        tool_dispatcher,
        db_session_factory=mock_session_factory
    )
    print("SUCCESS: New constructor signature works")
    
    # Test that state_manager is properly initialized
    assert supervisor.state_manager is not None, "state_manager not initialized"
    print("SUCCESS: state_manager properly initialized")
    
    # Test that db_session_factory is stored
    assert supervisor.db_session_factory == mock_session_factory, "db_session_factory not stored"
    print("SUCCESS: db_session_factory properly stored")
    
    print("SUCCESS: SupervisorAgent refactoring validation PASSED!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)