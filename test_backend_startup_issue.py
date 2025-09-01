#!/usr/bin/env python
"""
Test script to reproduce and diagnose backend startup issues.
Specifically looking for BaseExecutionInterface initialization problems.
"""

import sys
import os
import traceback
sys.path.insert(0, os.path.abspath('.'))

def test_import_chain():
    """Test the import chain to identify where BaseExecutionInterface fails."""
    print("=" * 80)
    print("Testing Backend Import Chain")
    print("=" * 80)
    
    # Test 1: Import BaseExecutionInterface directly
    print("\n1. Testing BaseExecutionInterface import...")
    try:
        from netra_backend.app.agents.base.interface import BaseExecutionInterface
        print("[SUCCESS] BaseExecutionInterface imported successfully")
        print(f"   - __init__ signature: {BaseExecutionInterface.__init__.__code__.co_varnames}")
        print(f"   - Required args: {BaseExecutionInterface.__init__.__code__.co_argcount}")
    except Exception as e:
        print(f"[FAILED] Failed to import BaseExecutionInterface: {e}")
        traceback.print_exc()
        return False
    
    # Test 2: Import unified_tool_execution
    print("\n2. Testing unified_tool_execution import...")
    try:
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        print("[SUCCESS] UnifiedToolExecutionEngine imported successfully")
    except Exception as e:
        print(f"[FAILED] Failed to import UnifiedToolExecutionEngine: {e}")
        traceback.print_exc()
        return False
    
    # Test 3: Import security modules
    print("\n3. Testing security module imports...")
    security_modules = [
        "netra_backend.app.agents.security.circuit_breaker",
        "netra_backend.app.agents.security.resource_guard",
        "netra_backend.app.agents.security.security_manager"
    ]
    
    for module in security_modules:
        try:
            __import__(module)
            print(f"[SUCCESS] {module} imported successfully")
        except Exception as e:
            print(f"[FAILED] Failed to import {module}: {e}")
            traceback.print_exc()
    
    # Test 4: Import auth_client_core
    print("\n4. Testing auth_client_core import...")
    try:
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        print("[SUCCESS] AuthServiceClient imported successfully")
    except Exception as e:
        print(f"[FAILED] Failed to import AuthServiceClient: {e}")
        traceback.print_exc()
        return False
    
    # Test 5: Check for classes inheriting from BaseExecutionInterface
    print("\n5. Checking for BaseExecutionInterface inheritance issues...")
    try:
        # Search for potential subclasses
        import inspect
        import importlib
        
        potential_modules = [
            "netra_backend.app.agents.unified_tool_execution",
            "netra_backend.app.agents.security.circuit_breaker",
            "netra_backend.app.agents.security.resource_guard",
            "netra_backend.app.agents.security.security_manager",
        ]
        
        for module_name in potential_modules:
            try:
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, BaseExecutionInterface) and obj != BaseExecutionInterface:
                        print(f"   Found subclass: {module_name}.{name}")
                        # Check if __init__ calls super().__init__ correctly
                        if hasattr(obj, '__init__'):
                            init_code = inspect.getsource(obj.__init__)
                            if 'super().__init__' in init_code:
                                if 'agent_name' not in init_code:
                                    print(f"   [WARNING]  WARNING: {name}.__init__ may not pass agent_name to super()")
            except Exception as e:
                print(f"   [FAILED] Error checking {module_name}: {e}")
                
    except Exception as e:
        print(f"[FAILED] Error during inheritance check: {e}")
        traceback.print_exc()
    
    return True

def test_backend_startup():
    """Test actual backend startup to identify the failure point."""
    print("\n" + "=" * 80)
    print("Testing Backend Startup")
    print("=" * 80)
    
    try:
        # Set minimal environment variables
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['DATABASE_URL'] = 'sqlite:///test.db'
        os.environ['AUTH_SERVICE_ENABLED'] = 'false'
        
        print("\n6. Testing backend app initialization...")
        from netra_backend.app.main import app
        print("[SUCCESS] Backend app imported successfully")
        
        # Try to access startup components
        print("\n7. Testing startup components...")
        from netra_backend.app.core.startup import startup_event
        print("[SUCCESS] Startup components accessible")
        
    except Exception as e:
        print(f"[FAILED] Backend startup failed: {e}")
        traceback.print_exc()
        return False
    
    return True

def main():
    """Run all tests."""
    print("Backend Startup Issue Diagnosis")
    print("================================\n")
    
    # Run import chain test
    import_success = test_import_chain()
    
    # Run backend startup test
    startup_success = test_backend_startup()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if import_success and startup_success:
        print("[SUCCESS] All tests passed - no issues detected")
    else:
        print("[FAILED] Issues detected - see errors above")
        print("\nLikely causes:")
        print("1. BaseExecutionInterface.__init__() missing required 'agent_name' argument")
        print("2. Subclasses not passing agent_name to super().__init__()")
        print("3. Circular import dependencies")
        print("4. Missing environment variables or configuration")
    
    return 0 if (import_success and startup_success) else 1

if __name__ == "__main__":
    exit(main())