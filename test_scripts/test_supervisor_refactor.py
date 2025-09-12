#!/usr/bin/env python3
"""Test script to verify SupervisorAgent refactoring works correctly."""

import sys
import os
from shared.isolated_environment import IsolatedEnvironment

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    
    print(" PASS:  Successfully imported SupervisorAgent and dependencies")
    
    # Test old constructor signature (should fail)
    try:
        # Mock objects
        llm_manager = Mock(spec=LLMManager)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        mock_session = Mock()
        
        # This should fail with the old signature
        supervisor_old = SupervisorAgent(mock_session, llm_manager, websocket_manager, tool_dispatcher)
        print(" FAIL:  ERROR: Old constructor signature still works - refactoring failed")
        sys.exit(1)
    except TypeError as e:
        print(f" PASS:  Old constructor signature correctly rejected: {e}")
    
    # Test new constructor signature (should work)
    try:
        # Mock objects
        llm_manager = Mock(spec=LLMManager)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        mock_session_factory = Mock()
        
        # This should work with the new signature
        supervisor_new = SupervisorAgent(
            llm_manager, 
            websocket_manager, 
            tool_dispatcher,
            db_session_factory=mock_session_factory
        )
        print(" PASS:  New constructor signature works correctly")
        
        # Test that state_manager is properly initialized
        assert supervisor_new.state_manager is not None, "state_manager not initialized"
        print(" PASS:  state_manager properly initialized")
        
        # Test that db_session_factory is stored
        assert supervisor_new.db_session_factory == mock_session_factory, "db_session_factory not stored"
        print(" PASS:  db_session_factory properly stored")
        
        # Test that no global db_session is stored
        assert not hasattr(supervisor_new, 'db_session') or supervisor_new.db_session is None, "Global db_session still stored"
        print(" PASS:  No global db_session stored")
        
        print("\n CELEBRATION:  SupervisorAgent refactoring validation PASSED!")
        print("   - Old constructor signature rejected")  
        print("   - New constructor signature works")
        print("   - Session factory pattern implemented")
        print("   - No global session storage")
        
    except Exception as e:
        print(f" FAIL:  ERROR: New constructor signature failed: {e}")
        sys.exit(1)
        
except ImportError as e:
    print(f" FAIL:  Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f" FAIL:  Unexpected error: {e}")
    sys.exit(1)