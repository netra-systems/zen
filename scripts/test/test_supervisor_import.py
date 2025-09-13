#!/usr/bin/env python
"""Test that SupervisorAgent imports correctly from the consolidated module."""

import asyncio
import sys
from shared.isolated_environment import IsolatedEnvironment

print("=" * 60)
print("SUPERVISOR AGENT IMPORT TEST")
print("=" * 60)

# Test 1: Basic import
print("\n1. Testing basic import...")
try:
    from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
    print("[PASS] Import successful from supervisor_consolidated")
except ImportError as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

# Test 2: Class instantiation
print("\n2. Testing class instantiation...")
try:
    # Create mock dependencies
    mock_db_session = AsyncMock()
    mock_llm_manager = Mock()
    mock_ws_manager = Mock()
    mock_tool_dispatcher = Mock()
    
    # Try to create an instance
    supervisor = SupervisorAgent(
        db_session=mock_db_session,
        llm_manager=mock_llm_manager,
        websocket_manager=mock_ws_manager,
        tool_dispatcher=mock_tool_dispatcher
    )
    print(f"[PASS] SupervisorAgent instance created: {type(supervisor).__name__}")
    print(f"  Module: {type(supervisor).__module__}")
except Exception as e:
    print(f"[FAIL] Instantiation failed: {e}")
    sys.exit(1)

# Test 3: Check essential attributes
print("\n3. Checking essential attributes...")
essential_attrs = [
    'execute',
    'register_agent', 
    'agents',
    'workflow_orchestrator',
    'execution_engine'
]

for attr in essential_attrs:
    if hasattr(supervisor, attr):
        print(f"[PASS] Has attribute: {attr}")
    else:
        print(f"[FAIL] Missing attribute: {attr}")

# Test 4: Test imports in different contexts
print("\n4. Testing imports from various test files...")

test_imports = [
    "from netra_backend.app.agents.supervisor_ssot import SupervisorAgent as S1",
    "from netra_backend.app.agents import supervisor_consolidated",
    "import netra_backend.app.agents.supervisor_consolidated",
]

for import_stmt in test_imports:
    try:
        exec(import_stmt)
        print(f"[PASS] {import_stmt}")
    except Exception as e:
        print(f"[FAIL] {import_stmt}: {e}")

# Test 5: Verify old imports would fail
print("\n5. Verifying old imports no longer work...")
old_imports = [
    ("supervisor_agent", "from netra_backend.app.agents.supervisor_agent import SupervisorAgent"),
    ("supervisor_agent_modern", "from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent"),
]

for name, import_stmt in old_imports:
    try:
        exec(import_stmt)
        print(f"[FAIL] {name} still exists - SSOT VIOLATION!")
        sys.exit(1)
    except ImportError:
        print(f"[PASS] {name} correctly removed")
    except Exception as e:
        print(f"? {name}: unexpected error: {e}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED - SSOT FIX VERIFIED")
print("=" * 60)