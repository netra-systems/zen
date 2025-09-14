#!/usr/bin/env python3
"""Test script to validate modern UserExecutionEngine API works correctly.

This test validates that Issue #874 ExecutionEngine fragmentation is actually
resolved and the modern API pattern works as expected.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_modern_user_execution_engine():
    """Test the modern UserExecutionEngine API."""
    try:
        # Import the SSOT implementation
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        print("SUCCESS: UserExecutionEngine import successful")

        # Check for modern factory method
        if hasattr(UserExecutionEngine, 'create_execution_engine'):
            print("SUCCESS: Modern create_execution_engine method available")
        else:
            print("ERROR: create_execution_engine method missing")
            return False

        # Test that we can create a UserExecutionContext
        try:
            # Create minimal user context using the available factory method
            user_context = UserExecutionContext.create_for_user(
                user_id="test_user_123",
                thread_id="test_thread_123",
                run_id="test_run_123",
                request_id="test_request_123"
            )
            print("SUCCESS: UserExecutionContext creation works")

            # Test modern factory method
            engine = await UserExecutionEngine.create_execution_engine(
                user_context=user_context,
                registry=None,  # Optional in modern API
                websocket_bridge=None  # Optional in modern API
            )

            print("SUCCESS: Modern UserExecutionEngine creation works")
            print(f"Engine type: {type(engine).__name__}")
            print(f"Engine module: {type(engine).__module__}")

            # Check that engine has user context
            if hasattr(engine, 'user_context') and engine.user_context:
                print(f"SUCCESS: Engine has user context: {engine.user_context.user_id}")
            else:
                print("WARNING: Engine missing user_context")

            # Test engine methods
            if hasattr(engine, 'execute_agent'):
                print("SUCCESS: Engine has execute_agent method")
            if hasattr(engine, 'execute_pipeline'):
                print("SUCCESS: Engine has execute_pipeline method")
            if hasattr(engine, 'cleanup'):
                print("SUCCESS: Engine has cleanup method")

            return True

        except Exception as e:
            print(f"ERROR: Modern API test failed: {e}")
            return False

    except ImportError as e:
        print(f"ERROR: Import failed: {e}")
        return False

async def test_legacy_redirect_compatibility():
    """Test that legacy execution_engine.py redirect works."""
    try:
        # Test that legacy import redirects to SSOT
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

        print("SUCCESS: Legacy execution_engine.py redirect works")

        # Verify it's the same class
        if ExecutionEngine is UserExecutionEngine:
            print("SUCCESS: ExecutionEngine redirects to UserExecutionEngine SSOT")
            return True
        else:
            print("ERROR: ExecutionEngine is not redirecting to UserExecutionEngine")
            return False

    except ImportError as e:
        print(f"ERROR: Legacy redirect failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("=" * 60)
    print("TESTING: Issue #874 ExecutionEngine Fragmentation Status")
    print("=" * 60)

    success = True

    print("\n1. Testing Modern UserExecutionEngine API...")
    if not await test_modern_user_execution_engine():
        success = False

    print("\n2. Testing Legacy Redirect Compatibility...")
    if not await test_legacy_redirect_compatibility():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("RESULT: ALL TESTS PASSED - ExecutionEngine SSOT appears functional")
        print("CONCLUSION: Issue #874 may be test update problem, not architecture problem")
    else:
        print("RESULT: TESTS FAILED - ExecutionEngine SSOT issues confirmed")
        print("CONCLUSION: Issue #874 architecture problems confirmed")
    print("=" * 60)

    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)