"""
Test to check if the agent execution bug still exists WITHOUT artificially creating it.

This will help determine if the bug is naturally present in the codebase or if
the reproduction test was only successful because we manually set components to None.
"""
import sys
import os
import asyncio
sys.path.append('.')

# Set test environment
os.environ['ENVIRONMENT'] = 'test'

from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from unittest.mock import MagicMock, AsyncMock
import time
from datetime import datetime, timezone


async def test_natural_execution_state():
    """Test agent execution with normal initialization - no artificial bug injection."""
    
    print("=== TESTING NATURAL EXECUTION STATE (NO ARTIFICIAL BUG) ===")
    
    # Create user context
    user_context = UserExecutionContext(
        user_id="test_user_natural_123",
        thread_id="test_thread_natural_456", 
        run_id=f"test_run_natural_{int(time.time())}",
        request_id=f"req_natural_{int(time.time()*1000)}"
    )
    
    # Mock dependencies
    mock_agent_factory = MagicMock()
    mock_agent_registry = MagicMock()
    mock_websocket_bridge = MagicMock()
    
    mock_agent_factory._agent_registry = mock_agent_registry
    mock_agent_factory._websocket_bridge = mock_websocket_bridge
    
    mock_websocket_emitter = AsyncMock()
    
    # Create agent execution context
    agent_context = AgentExecutionContext(
        user_id=user_context.user_id,
        thread_id=user_context.thread_id,
        run_id=user_context.run_id,
        agent_name="test_agent_natural"
    )
    
    # Create agent state
    agent_state = DeepAgentState(
        user_request='Test execution without artificial bugs',
        user_id=user_context.user_id,
        run_id=user_context.run_id,
        chat_thread_id=user_context.thread_id
    )
    
    # Create UserExecutionEngine with NORMAL initialization
    print("[NATURAL TEST] Creating UserExecutionEngine with normal initialization...")
    engine = UserExecutionEngine(
        context=user_context,
        agent_factory=mock_agent_factory,
        websocket_emitter=mock_websocket_emitter
    )
    
    # CHECK COMPONENT STATE AFTER NORMAL INITIALIZATION
    print(f"[COMPONENT STATE] periodic_update_manager: {engine.periodic_update_manager}")
    print(f"[COMPONENT STATE] periodic_update_manager type: {type(engine.periodic_update_manager)}")
    print(f"[COMPONENT STATE] fallback_manager: {engine.fallback_manager}")
    print(f"[COMPONENT STATE] fallback_manager type: {type(engine.fallback_manager)}")
    
    # Test if components have required methods
    if engine.periodic_update_manager and hasattr(engine.periodic_update_manager, 'track_operation'):
        print("[SUCCESS] periodic_update_manager properly initialized with track_operation")
    else:
        print("[ERROR] periodic_update_manager missing or lacks track_operation")
        
    if engine.fallback_manager and hasattr(engine.fallback_manager, 'create_fallback_result'):
        print("[SUCCESS] fallback_manager properly initialized with create_fallback_result") 
    else:
        print("[ERROR] fallback_manager missing or lacks create_fallback_result")
    
    # NOW TEST ACTUAL EXECUTION WITHOUT ARTIFICIAL BUG INJECTION
    print("\\n[NATURAL TEST] Testing agent execution with normal components...")
    
    try:
        result = await engine.execute_agent(agent_context, agent_state)
        
        print("[SUCCESS] AGENT EXECUTION SUCCEEDED")
        print(f"   Result success: {result.success if result else 'No result'}")
        print(f"   Execution history: {len(engine.run_history)} items")
        print("\\n[CONCLUSION] Bug appears to be FIXED in current codebase")
        print("   Components are properly initialized and execution succeeds")
        
        return True, "Success - bug appears fixed"
        
    except AttributeError as e:
        if "track_operation" in str(e):
            print("[ERROR] NATURAL BUG CONFIRMED - AttributeError on track_operation")
            print(f"   Error: {e}")
            print("\\n[CRITICAL] CONCLUSION: Bug still exists naturally in codebase")
            return False, f"Natural AttributeError: {e}"
        else:
            print(f"[ERROR] DIFFERENT AttributeError: {e}")
            return False, f"Different AttributeError: {e}"
            
    except RuntimeError as e:
        if "track_operation" in str(e):
            print("[ERROR] NATURAL BUG CONFIRMED - RuntimeError wrapping track_operation issue")
            print(f"   Error: {e}")
            print("\\n[CRITICAL] CONCLUSION: Bug still exists naturally in codebase")
            return False, f"Natural RuntimeError: {e}"
        else:
            print(f"[ERROR] DIFFERENT RuntimeError: {e}")
            return False, f"Different RuntimeError: {e}"
            
    except Exception as e:
        print(f"[ERROR] UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Unexpected error: {e}"


if __name__ == "__main__":
    success, message = asyncio.run(test_natural_execution_state())
    print(f"\\n=== FINAL RESULT ===")
    print(f"Success: {success}")
    print(f"Message: {message}")