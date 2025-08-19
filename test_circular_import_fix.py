"""Test if circular import is fixed"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if we can import all the necessary modules without circular import errors"""
    
    print("Testing imports after circular dependency fix...")
    
    try:
        print("1. Importing agents.base.executor...")
        from app.agents.base.executor import BaseExecutionEngine
        print("   [OK] Success: BaseExecutionEngine imported")
    except ImportError as e:
        print(f"   [FAIL] Failed: {e}")
        return False
    
    try:
        print("2. Importing agents.supervisor_consolidated...")
        from app.agents.supervisor_consolidated import SupervisorAgent
        print("   [OK] Success: SupervisorAgent imported")
    except ImportError as e:
        print(f"   [FAIL] Failed: {e}")
        return False
    
    try:
        print("3. Importing agent registry...")
        from app.agents.supervisor.agent_registry import AgentRegistry
        print("   [OK] Success: AgentRegistry imported")
    except ImportError as e:
        print(f"   [FAIL] Failed: {e}")
        return False
    
    try:
        print("4. Importing WebSocket modules...")
        from app.websocket.connection_executor import ConnectionExecutor
        from app.websocket.message_handler_core import ReliableMessageHandler
        from app.websocket.websocket_broadcast_executor import BroadcastExecutor
        print("   [OK] Success: WebSocket modules imported")
    except ImportError as e:
        print(f"   [FAIL] Failed: {e}")
        return False
    
    try:
        print("5. Importing agent service...")
        from app.services.agent_service_core import AgentService
        print("   [OK] Success: AgentService imported")
    except ImportError as e:
        print(f"   [FAIL] Failed: {e}")
        return False
    
    print("\n[SUCCESS] All imports successful! Circular dependency is fixed.")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)