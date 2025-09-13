#!/usr/bin/env python
"""Test that startup_module.py can import and use SupervisorAgent correctly."""

import asyncio
import sys
from shared.isolated_environment import IsolatedEnvironment

print("=" * 60)
print("STARTUP MODULE SUPERVISOR TEST")
print("=" * 60)

async def test_startup_module():
    """Test that startup_module can properly import and use SupervisorAgent."""
    
    # Test import from startup_module
    print("\n1. Testing startup_module import...")
    try:
        # Import the module
        from netra_backend.app import startup_module
        print("[PASS] startup_module imported successfully")
        
        # Check if SupervisorAgent is imported
        if hasattr(startup_module, 'SupervisorAgent'):
            print(f"[PASS] SupervisorAgent found in startup_module")
            print(f"  Module: {startup_module.SupervisorAgent.__module__}")
            
            # Verify it's from the correct module
            if startup_module.SupervisorAgent.__module__ == 'netra_backend.app.agents.supervisor_consolidated':
                print("[PASS] SupervisorAgent is from correct module (supervisor_consolidated)")
            else:
                print(f"[FAIL] SupervisorAgent is from wrong module: {startup_module.SupervisorAgent.__module__}")
                return False
        else:
            # Check if it's imported but not exposed
            import_found = False
            with open('netra_backend/app/startup_module.py', 'r') as f:
                content = f.read()
                if 'from netra_backend.app.agents.supervisor_ssot import SupervisorAgent' in content:
                    print("[PASS] Import statement found in startup_module.py")
                    import_found = True
                else:
                    print("[FAIL] SupervisorAgent import not found in startup_module")
                    return False
                    
    except Exception as e:
        print(f"[FAIL] Error testing startup_module: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test creating supervisor through typical startup flow
    print("\n2. Testing supervisor creation pattern...")
    try:
        # Mock dependencies
        mock_db_session = AsyncMock()
        mock_llm_manager = Mock()
        mock_ws_manager = Mock()
        mock_tool_dispatcher = Mock()
        
        # Import and create
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        
        supervisor = SupervisorAgent(
            db_session=mock_db_session,
            llm_manager=mock_llm_manager,
            websocket_manager=mock_ws_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        print("[PASS] SupervisorAgent created successfully")
        print(f"  Type: {type(supervisor).__name__}")
        print(f"  Has execute method: {hasattr(supervisor, 'execute')}")
        
    except Exception as e:
        print(f"[FAIL] Error creating supervisor: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("\nRunning startup module tests...")
    
    # Run async test
    success = asyncio.run(test_startup_module())
    
    print("\n" + "=" * 60)
    if success:
        print("ALL STARTUP MODULE TESTS PASSED")
    else:
        print("STARTUP MODULE TESTS FAILED")
        sys.exit(1)
    print("=" * 60)