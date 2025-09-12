#!/usr/bin/env python3
"""
Verification script for agent registry test fixes.
"""

import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, '/Users/anthony/Documents/GitHub/netra-apex')

from unittest.mock import Mock, AsyncMock
from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession, AgentLifecycleManager

async def test_websocket_manager_none_handling():
    """Test that UserAgentSession handles None websocket manager properly."""
    print("Testing UserAgentSession None websocket manager handling...")
    
    session = UserAgentSession("test_user")
    
    # This should not raise an exception and should not create a bridge
    await session.set_websocket_manager(None)
    
    # Verify the expected behavior
    assert session._websocket_manager is None
    assert session._websocket_bridge is None
    
    print(" PASS:  UserAgentSession handles None websocket manager correctly")

def test_lifecycle_manager_no_registry():
    """Test that AgentLifecycleManager works without registry."""
    print("Testing AgentLifecycleManager without registry...")
    
    manager = AgentLifecycleManager()
    
    # Should initialize properly without registry
    assert manager._registry is None
    assert isinstance(manager._memory_thresholds, dict)
    
    print(" PASS:  AgentLifecycleManager initializes correctly without registry")

async def test_lifecycle_manager_monitor_no_registry():
    """Test that monitoring returns 'no_registry' when no registry is set."""
    print("Testing AgentLifecycleManager monitoring without registry...")
    
    manager = AgentLifecycleManager()
    
    result = await manager.monitor_memory_usage("test_user")
    
    # Should return 'no_registry' status
    assert result['status'] == 'no_registry'
    assert result['user_id'] == "test_user"
    
    print(" PASS:  AgentLifecycleManager monitoring returns 'no_registry' correctly")

async def test_lifecycle_manager_with_registry():
    """Test that AgentLifecycleManager works with a registry."""
    print("Testing AgentLifecycleManager with mock registry...")
    
    # Create mock registry
    mock_registry = Mock()
    mock_user_session = Mock()
    mock_user_session._access_lock = asyncio.Lock()
    mock_user_session._agents = {"test_agent": Mock()}
    mock_registry._user_sessions = {"test_user": mock_user_session}
    
    manager = AgentLifecycleManager(registry=mock_registry)
    
    # Should have registry reference
    assert manager._registry is mock_registry
    
    # Should be able to cleanup resources
    await manager.cleanup_agent_resources("test_user", "test_agent")
    
    print(" PASS:  AgentLifecycleManager works correctly with registry")

async def main():
    """Run all verification tests."""
    print("[U+1F680] Running agent registry test fixes verification...\n")
    
    try:
        # Test UserAgentSession fixes
        await test_websocket_manager_none_handling()
        
        # Test AgentLifecycleManager fixes
        test_lifecycle_manager_no_registry()
        await test_lifecycle_manager_monitor_no_registry()
        await test_lifecycle_manager_with_registry()
        
        print("\n PASS:  All verification tests passed! The fixes are working correctly.")
        return True
        
    except Exception as e:
        print(f"\n FAIL:  Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)