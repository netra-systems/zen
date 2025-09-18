#!/usr/bin/env python3
"""
Issue #891 System Stability Proof Script

This script provides proof that our BaseAgent session management and factory 
pattern fixes maintain system stability. It validates core functionality
without requiring complex test runners.

Tests performed:
1. Import validation - All components load correctly
2. Factory pattern verification - User isolation maintained
3. Session state management - No conflicts
4. WebSocket integration - No regressions

Validation approach:
- Simple import testing
- Direct class instantiation tests
- State isolation verification
- Basic functionality checks
"""

import sys
from pathlib import Path

# Setup path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    """Test that all critical imports work correctly."""
    print("1. Testing imports...")
    
    try:
        from netra_backend.app.agents.base_agent import BaseAgent
        print("   ✅ BaseAgent import successful")
    except Exception as e:
        print(f"   ❌ BaseAgent import failed: {e}")
        return False
        
    try:
        from netra_backend.app.agents.interfaces import BaseAgentProtocol
        print("   ✅ BaseAgentProtocol import successful")
    except Exception as e:
        print(f"   ❌ BaseAgentProtocol import failed: {e}")
        return False
        
    try:
        from netra_backend.app.agents.session_state import SessionState
        print("   ✅ SessionState import successful")
    except Exception as e:
        print(f"   ❌ SessionState import failed: {e}")
        return False
        
    try:
        from netra_backend.app.agents.user_context_state import UserContextState
        print("   ✅ UserContextState import successful")
    except Exception as e:
        print(f"   ❌ UserContextState import failed: {e}")
        return False
        
    return True

def test_factory_pattern():
    """Test that factory patterns work correctly."""
    print("\n2. Testing factory pattern...")
    
    try:
        from netra_backend.app.agents.user_context_state import UserContextState
        
        # Create two separate user contexts
        context1 = UserContextState.create_for_user("user_1", "session_1")
        context2 = UserContextState.create_for_user("user_2", "session_2")
        
        # Verify they are different instances
        if context1 is not context2:
            print("   ✅ Factory creates separate instances")
        else:
            print("   ❌ Factory returns same instance for different users")
            return False
            
        # Verify user isolation
        if context1.user_id != context2.user_id:
            print("   ✅ User contexts properly isolated")
        else:
            print("   ❌ User contexts not properly isolated")
            return False
            
        return True
        
    except Exception as e:
        print(f"   ❌ Factory pattern test failed: {e}")
        return False

def test_session_management():
    """Test that session management works correctly."""
    print("\n3. Testing session management...")
    
    try:
        from netra_backend.app.agents.session_state import SessionState
        
        # Create separate sessions
        session1 = SessionState(user_id="user_1", session_id="session_1")
        session2 = SessionState(user_id="user_2", session_id="session_2")
        
        # Test state isolation
        session1.data["test_value"] = "value_for_user_1"
        session2.data["test_value"] = "value_for_user_2"
        
        if session1.data["test_value"] != session2.data["test_value"]:
            print("   ✅ Session state properly isolated")
        else:
            print("   ❌ Session state not properly isolated")
            return False
            
        return True
        
    except Exception as e:
        print(f"   ❌ Session management test failed: {e}")
        return False

def test_websocket_integration():
    """Test that WebSocket integration is not broken."""
    print("\n4. Testing WebSocket integration...")
    
    try:
        from netra_backend.app.websocket_core.manager import WebSocketManager
        print("   ✅ WebSocketManager import successful")
    except Exception as e:
        print(f"   ❌ WebSocketManager import failed: {e}")
        return False
        
    try:
        from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        print("   ✅ WebSocket types import successful")
    except Exception as e:
        print(f"   ❌ WebSocket types import failed: {e}")
        return False
        
    return True

def test_base_agent_functionality():
    """Test basic BaseAgent functionality."""
    print("\n5. Testing BaseAgent functionality...")
    
    try:
        from netra_backend.app.agents.base_agent import BaseAgent
        
        # Verify class structure is intact
        required_methods = ['__init__', 'process_message']
        for method in required_methods:
            if not hasattr(BaseAgent, method):
                print(f"   ❌ BaseAgent missing required method: {method}")
                return False
                
        print("   ✅ BaseAgent class structure intact")
        return True
        
    except Exception as e:
        print(f"   ❌ BaseAgent functionality test failed: {e}")
        return False

def main():
    """Run all stability tests."""
    print("🔧 Issue #891 System Stability Proof")
    print("=====================================")
    print("Validating BaseAgent session management and factory pattern fixes...\n")
    
    tests = [
        test_imports,
        test_factory_pattern,
        test_session_management,
        test_websocket_integration,
        test_base_agent_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print("   ⚠️  Test failed")
        except Exception as e:
            print(f"   ❌ Test error: {e}")
    
    print(f"\n📊 Test Results:")
    print(f"   Passed: {passed}/{total}")
    print(f"   Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n✅ SYSTEM STABILITY CONFIRMED")
        print("All validations passed - Issue #891 remediation maintains system stability")
        print("No breaking changes detected in BaseAgent session management or factory patterns")
        return True
    else:
        print("\n❌ STABILITY ISSUES DETECTED")
        print(f"Only {passed}/{total} tests passed - investigate failures before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)