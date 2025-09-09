#!/usr/bin/env python3
"""Quick test to verify registry proliferation fix."""

import sys
import os
sys.path.insert(0, '/Users/anthony/Documents/GitHub/netra-apex')

from netra_backend.app.core.registry.universal_registry import ToolRegistry
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext

def test_registry_fix():
    """Test that registry is properly reused."""
    
    # Create a user context
    context = UserExecutionContext(
        user_id="test_user",
        run_id="test_run",
        thread_id="test_thread"
    )
    
    # Create a registry
    pre_created_registry = ToolRegistry(scope_id="test_registry")
    print(f"✅ Created pre-registry: {id(pre_created_registry)}")
    
    # Create dispatcher without registry (should create its own)
    dispatcher1 = UnifiedToolDispatcherFactory.create_for_request(
        user_context=context,
        tools=None,
        websocket_manager=None
    )
    print(f"🔧 Dispatcher1 registry: {id(dispatcher1.registry)} (no pre-registry passed)")
    
    # Create dispatcher with pre-created registry (should reuse)
    dispatcher2 = UnifiedToolDispatcherFactory.create_for_request(
        user_context=context,
        tools=None,
        websocket_manager=None,
        registry=pre_created_registry
    )
    print(f"🔧 Dispatcher2 registry: {id(dispatcher2.registry)} (pre-registry passed)")
    
    # Check results
    if id(dispatcher2.registry) == id(pre_created_registry):
        print("✅ SUCCESS: Pre-created registry was reused!")
        return True
    else:
        print("❌ FAILURE: Pre-created registry was NOT reused!")
        return False

if __name__ == "__main__":
    success = test_registry_fix()
    sys.exit(0 if success else 1)