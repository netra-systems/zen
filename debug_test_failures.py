#!/usr/bin/env python3
"""
Quick script to debug the failing agent registry tests.
This will help understand the root cause without relying on pytest.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

try:
    # Import the modules to check for import issues
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    print("✅ AgentRegistry imported successfully")
    
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    print("✅ UserExecutionContext imported successfully")
    
    # Try to check if the method exists
    print(f"✅ AgentRegistry has create_tool_dispatcher_for_user: {hasattr(AgentRegistry, 'create_tool_dispatcher_for_user')}")
    print(f"✅ AgentRegistry has _default_dispatcher_factory: {hasattr(AgentRegistry, '_default_dispatcher_factory')}")
    print(f"✅ AgentRegistry has tool_dispatcher property: {hasattr(AgentRegistry, 'tool_dispatcher')}")
    
    # Try creating an instance
    from unittest.mock import AsyncMock
    mock_llm_manager = AsyncMock()
    mock_llm_manager._initialized = True
    
    registry = AgentRegistry(llm_manager=mock_llm_manager)
    print("✅ AgentRegistry instance created successfully")
    
    # Check what attributes it has
    print(f"✅ Registry tool_dispatcher_factory: {type(registry.tool_dispatcher_factory).__name__}")
    print(f"✅ Registry has _default_dispatcher_factory: {hasattr(registry, '_default_dispatcher_factory')}")
    
    # Try to call the method
    import uuid
    test_user_context = UserExecutionContext(
        user_id=f"test_user_{uuid.uuid4().hex[:8]}",
        request_id=f"test_request_{uuid.uuid4().hex[:8]}",
        thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
        run_id=f"test_run_{uuid.uuid4().hex[:8]}"
    )
    print("✅ UserExecutionContext created successfully")
    
    # Test that the method exists and can be called
    print(f"✅ create_tool_dispatcher_for_user method exists: {hasattr(registry, 'create_tool_dispatcher_for_user')}")
    if hasattr(registry, 'create_tool_dispatcher_for_user'):
        print(f"✅ Method signature: {registry.create_tool_dispatcher_for_user.__doc__ or 'No docstring'}")
    
    print("✅ All imports and basic tests passed")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()