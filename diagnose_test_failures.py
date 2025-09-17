#!/usr/bin/env python3
"""
Diagnostic script to identify common test failure patterns.
Focuses on SSOT compliance and import issues.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def diagnose_websocket_imports():
    """Diagnose WebSocket-related import issues."""
    print("🔍 Diagnosing WebSocket imports...")

    tests = [
        ("Canonical imports", lambda: __import__('netra_backend.app.websocket_core.canonical_import_patterns', fromlist=[''])),
        ("Standardized factory", lambda: __import__('netra_backend.app.websocket_core.standardized_factory_interface', fromlist=[''])),
        ("Agent bridge", lambda: __import__('netra_backend.app.services.agent_websocket_bridge', fromlist=[''])),
        ("Protocols", lambda: __import__('netra_backend.app.websocket_core.protocols', fromlist=[''])),
        ("Unified manager", lambda: __import__('netra_backend.app.websocket_core.unified_manager', fromlist=[''])),
    ]

    failures = []
    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ {name}")
        except Exception as e:
            print(f"❌ {name}: {e}")
            failures.append((name, str(e)))

    return failures

def diagnose_agent_imports():
    """Diagnose agent-related import issues."""
    print("\n🔍 Diagnosing agent imports...")

    tests = [
        ("Agent registry", lambda: __import__('netra_backend.app.agents.registry', fromlist=[''])),
        ("Supervisor agent", lambda: __import__('netra_backend.app.agents.supervisor_agent_modern', fromlist=[''])),
        ("Execution engine", lambda: __import__('netra_backend.app.agents.supervisor.execution_engine', fromlist=[''])),
        ("Tool dispatcher", lambda: __import__('netra_backend.app.tools.enhanced_dispatcher', fromlist=[''])),
    ]

    failures = []
    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ {name}")
        except Exception as e:
            print(f"❌ {name}: {e}")
            failures.append((name, str(e)))

    return failures

def diagnose_database_imports():
    """Diagnose database-related import issues."""
    print("\n🔍 Diagnosing database imports...")

    tests = [
        ("Database manager", lambda: __import__('netra_backend.app.db.database_manager', fromlist=[''])),
        ("Clickhouse client", lambda: __import__('netra_backend.app.db.clickhouse', fromlist=[''])),
        ("Postgres client", lambda: __import__('netra_backend.app.db.postgres', fromlist=[''])),
    ]

    failures = []
    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ {name}")
        except Exception as e:
            print(f"❌ {name}: {e}")
            failures.append((name, str(e)))

    return failures

def diagnose_configuration_imports():
    """Diagnose configuration-related import issues."""
    print("\n🔍 Diagnosing configuration imports...")

    tests = [
        ("Base config", lambda: __import__('netra_backend.app.core.configuration.base', fromlist=[''])),
        ("Database config", lambda: __import__('netra_backend.app.core.configuration.database', fromlist=[''])),
        ("Services config", lambda: __import__('netra_backend.app.core.configuration.services', fromlist=[''])),
        ("Main config", lambda: __import__('netra_backend.app.config', fromlist=[''])),
    ]

    failures = []
    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ {name}")
        except Exception as e:
            print(f"❌ {name}: {e}")
            failures.append((name, str(e)))

    return failures

def diagnose_ssot_test_infrastructure():
    """Diagnose SSOT test infrastructure imports."""
    print("\n🔍 Diagnosing SSOT test infrastructure...")

    tests = [
        ("Unified test runner", lambda: __import__('tests.unified_test_runner', fromlist=[''])),
        ("SSOT base test case", lambda: __import__('test_framework.ssot.base_test_case', fromlist=[''])),
        ("SSOT mock factory", lambda: __import__('test_framework.ssot.mock_factory', fromlist=[''])),
        ("SSOT orchestration", lambda: __import__('test_framework.ssot.orchestration', fromlist=[''])),
    ]

    failures = []
    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ {name}")
        except Exception as e:
            print(f"❌ {name}: {e}")
            failures.append((name, str(e)))

    return failures

def check_specific_websocket_functionality():
    """Check specific WebSocket functionality that often fails."""
    print("\n🔧 Checking specific WebSocket functionality...")

    try:
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

        # Try to create a manager (this often fails with various issues)
        manager = get_websocket_manager()
        print("✅ WebSocket manager creation")

        # Check essential methods
        if hasattr(manager, 'send_to_thread'):
            print("✅ send_to_thread method exists")
        else:
            print("❌ send_to_thread method missing")

        if hasattr(manager, 'emit_event'):
            print("✅ emit_event method exists")
        else:
            print("❌ emit_event method missing")

        return []

    except Exception as e:
        print(f"❌ WebSocket functionality check failed: {e}")
        return [("WebSocket functionality", str(e))]

def main():
    """Run all diagnostic tests."""
    print("🩺 SSOT Compliance & Test Failure Diagnostic")
    print("=" * 60)

    all_failures = []

    # Run all diagnostic tests
    all_failures.extend(diagnose_websocket_imports())
    all_failures.extend(diagnose_agent_imports())
    all_failures.extend(diagnose_database_imports())
    all_failures.extend(diagnose_configuration_imports())
    all_failures.extend(diagnose_ssot_test_infrastructure())
    all_failures.extend(check_specific_websocket_functionality())

    print("\n" + "=" * 60)
    if not all_failures:
        print("🎉 All diagnostic tests PASSED - imports and basic functionality working")
        print("   Test failures may be due to environment, configuration, or runtime issues")
        return 0
    else:
        print(f"💥 {len(all_failures)} diagnostic test(s) FAILED:")
        for i, (name, error) in enumerate(all_failures, 1):
            print(f"   {i}. {name}: {error}")
        print("\n   These import/functionality issues likely cause test failures.")
        return 1

if __name__ == "__main__":
    sys.exit(main())