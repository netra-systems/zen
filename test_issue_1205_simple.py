#!/usr/bin/env python3
"""Simple test to reproduce Issue #1205 - AgentRegistryAdapter get_async signature issue"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import Mock, AsyncMock
from shared.types import UserID, ThreadID, RequestID
from netra_backend.app.agents.supervisor.user_execution_engine import AgentRegistryAdapter
from netra_backend.app.services.user_execution_context import UserExecutionContext


async def test_issue_1205_reproduction():
    """Reproduce Issue #1205: AgentRegistryAdapter.get_async signature mismatch"""

    print("=" * 60)
    print("TESTING Issue #1205: AgentRegistryAdapter get_async signature")
    print("=" * 60)

    # Create test user context
    user_context = UserExecutionContext(
        user_id=UserID("test-user"),
        thread_id=ThreadID("test-thread"),
        run_id=RequestID("test-run"),
        agent_context={}
    )

    # Create AgentRegistryAdapter with mock dependencies
    mock_registry = Mock()
    mock_factory = AsyncMock()

    adapter = AgentRegistryAdapter(
        agent_class_registry=mock_registry,
        agent_factory=mock_factory,
        user_context=user_context
    )

    print("OK Created AgentRegistryAdapter instance")

    # Test 1: Check if get_async method exists
    has_get_async = hasattr(adapter, 'get_async')
    print(f"✓ get_async method exists: {has_get_async}")

    if not has_get_async:
        print("❌ ERROR: get_async method not found!")
        return False

    # Test 2: Check method signature
    import inspect
    method = getattr(adapter, 'get_async')
    sig = inspect.signature(method)
    params = list(sig.parameters.keys())

    print(f"✓ Current signature: {sig}")
    print(f"✓ Parameters: {params}")

    # Test 3: Try calling without context (should work)
    try:
        mock_registry.get.return_value = Mock()
        mock_factory.create_instance.return_value = Mock()

        result = await adapter.get_async("test_agent")
        print(f"✓ Call without context succeeded")
    except Exception as e:
        print(f"❌ Call without context failed: {e}")
        return False

    # Test 4: Try calling WITH context parameter (this should fail - Issue #1205)
    try:
        result = await adapter.get_async("test_agent", context=user_context)
        print(f"❌ Call with context succeeded - this indicates bug is already fixed!")
        return False
    except TypeError as e:
        if "unexpected keyword argument 'context'" in str(e):
            print(f"✓ REPRODUCTION SUCCESSFUL: {e}")
            print(f"✓ This confirms Issue #1205 exists")
            return True
        else:
            print(f"❌ Unexpected TypeError: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_agent_execution_core_call_simulation():
    """Simulate how AgentExecutionCore calls get_async"""

    print("\n" + "=" * 60)
    print("SIMULATING AgentExecutionCore call pattern")
    print("=" * 60)

    # This simulates the call from AgentExecutionCore._get_agent_or_error line 1066:
    # agent = await self.registry.get_async(agent_name, context=user_execution_context)

    user_context = UserExecutionContext(
        user_id=UserID("test-user"),
        thread_id=ThreadID("test-thread"),
        run_id=RequestID("test-run"),
        agent_context={}
    )

    mock_registry = Mock()
    mock_factory = AsyncMock()

    adapter = AgentRegistryAdapter(
        agent_class_registry=mock_registry,
        agent_factory=mock_factory,
        user_context=user_context
    )

    # Simulate the exact call pattern from AgentExecutionCore
    agent_name = "test_agent"
    user_execution_context = user_context

    print(f"Simulating call: await registry.get_async('{agent_name}', context={user_execution_context.user_id})")

    try:
        # This is the EXACT call that AgentExecutionCore makes
        agent = await adapter.get_async(agent_name, context=user_execution_context)
        print("❌ ERROR: Call succeeded - Issue #1205 might already be fixed!")
        return False
    except TypeError as e:
        if "unexpected keyword argument 'context'" in str(e):
            print(f"✓ CONFIRMED: AgentExecutionCore call pattern fails with: {e}")
            return True
        else:
            print(f"❌ Unexpected TypeError: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def analyze_fix_requirements():
    """Analyze what the fix should look like"""

    print("\n" + "=" * 60)
    print("ISSUE #1205 FIX REQUIREMENTS")
    print("=" * 60)

    print("CURRENT (BROKEN):")
    print("  async def get_async(self, agent_name: str)")
    print()
    print("REQUIRED (FIXED) - Option 1:")
    print("  async def get_async(self, agent_name: str, context=None)")
    print()
    print("REQUIRED (FIXED) - Option 2:")
    print("  async def get_async(self, agent_name: str, *, context=None)")
    print()
    print("REQUIRED (FIXED) - Option 3:")
    print("  async def get_async(self, agent_name: str, **kwargs)")
    print()
    print("The fix must allow this call to work:")
    print("  await registry.get_async(agent_name, context=user_execution_context)")
    print()


async def main():
    """Run all tests"""
    print("ISSUE #1205 REPRODUCTION TEST SUITE")
    print("Testing AgentRegistryAdapter get_async method signature issue")
    print()

    # Test 1: Basic reproduction
    test1_result = await test_issue_1205_reproduction()

    # Test 2: AgentExecutionCore call simulation
    test2_result = await test_agent_execution_core_call_simulation()

    # Analysis
    analyze_fix_requirements()

    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Basic reproduction test: {'✓ PASSED' if test1_result else '❌ FAILED'}")
    print(f"AgentExecutionCore simulation: {'✓ PASSED' if test2_result else '❌ FAILED'}")

    if test1_result and test2_result:
        print("\n✓ Issue #1205 CONFIRMED: get_async signature incompatibility exists")
        print("✓ Ready to create fix and validation tests")
        return True
    else:
        print("\n❌ Issue #1205 NOT REPRODUCED - may already be fixed or test error")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)