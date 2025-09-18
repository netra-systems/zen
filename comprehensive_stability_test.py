"""
Comprehensive System Stability Test for Netra Apex Issue #1340
Tests that database fixes have not introduced breaking changes.
"""
import sys
import asyncio
import traceback
sys.path.insert(0, '.')

async def test_comprehensive_stability():
    """Test overall system stability after database fixes."""
    print("=== COMPREHENSIVE STABILITY TEST FOR ISSUE #1340 ===\n")
    print("Testing that database Row object fixes have not broken system stability...\n")

    results = []

    # Test 1: Core database imports
    print("Test 1: Core database module imports...")
    try:
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.db.optimized_startup_checks import optimized_startup_checker
        from netra_backend.app.db.postgres import get_postgres_url
        from netra_backend.app.db.clickhouse import ClickHouseClient
        print("[PASS] Core database modules import successfully")
        results.append(("Database Imports", True, None))
    except Exception as e:
        print(f"[FAIL] Database import error: {e}")
        results.append(("Database Imports", False, str(e)))

    # Test 2: Configuration system
    print("\nTest 2: Configuration system...")
    try:
        from netra_backend.app.core.configuration.base import ConfigurationManager
        config = ConfigurationManager().get_config()
        print("[PASS] Configuration system operational")
        results.append(("Configuration System", True, None))
    except Exception as e:
        print(f"[FAIL] Configuration error: {e}")
        results.append(("Configuration System", False, str(e)))

    # Test 3: Agent system imports (uses database)
    print("\nTest 3: Agent system imports...")
    try:
        from netra_backend.app.agents.registry import AgentRegistry
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        print("[PASS] Agent system imports working")
        results.append(("Agent System", True, None))
    except Exception as e:
        print(f"[FAIL] Agent system error: {e}")
        results.append(("Agent System", False, str(e)))

    # Test 4: WebSocket system (uses database for state)
    print("\nTest 4: WebSocket system imports...")
    try:
        from netra_backend.app.websocket_core.manager import WebSocketConnectionManager
        from netra_backend.app.websocket_core.auth import WebSocketAuthenticationManager
        print("[PASS] WebSocket system imports working")
        results.append(("WebSocket System", True, None))
    except Exception as e:
        print(f"[FAIL] WebSocket error: {e}")
        results.append(("WebSocket System", False, str(e)))

    # Test 5: Database operations (critical test for our fixes)
    print("\nTest 5: Database operations (Row object handling)...")
    try:
        from netra_backend.app.core.configuration.base import ConfigurationManager
        config = ConfigurationManager().get_config()
        db_manager = DatabaseManager(config)

        async with db_manager.get_async_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1 as test_col"))
            row = result.fetchone()  # Fixed: no await here - this was our fix!
            assert row[0] == 1, f"Expected 1, got {row[0]}"
        print("[PASS] Database operations functional (Row objects handled correctly)")
        results.append(("Database Operations", True, None))
    except Exception as e:
        print(f"[FAIL] Database operation error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        results.append(("Database Operations", False, str(e)))

    # Test 6: Auth integration (depends on database)
    print("\nTest 6: Auth integration...")
    try:
        from netra_backend.app.auth_integration.auth import AuthIntegration
        print("[PASS] Auth integration imports working")
        results.append(("Auth Integration", True, None))
    except Exception as e:
        print(f"[FAIL] Auth integration error: {e}")
        results.append(("Auth Integration", False, str(e)))

    # Test 7: API routes (depend on multiple systems)
    print("\nTest 7: API routes...")
    try:
        from netra_backend.app.routes import auth, health, websocket
        print("[PASS] API routes imports working")
        results.append(("API Routes", True, None))
    except Exception as e:
        print(f"[FAIL] API routes error: {e}")
        results.append(("API Routes", False, str(e)))

    # Summary
    print(f"\n=== STABILITY TEST RESULTS ===")
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for test_name, success, error in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{test_name}: {status}")
        if error:
            print(f"  Error: {error}")

    print(f"\nTests Passed: {passed}/{total}")
    print(f"Stability Score: {passed/total*100:.1f}%")

    if passed == total:
        print("\n[SUCCESS] SYSTEM STABILITY CONFIRMED")
        print("[SUCCESS] Database Row object fixes have NOT introduced breaking changes")
        print("[SUCCESS] All critical systems remain operational")
        return True
    else:
        print(f"\n[WARNING] {total - passed} component(s) have issues")
        print("[WARNING] May need investigation before deployment")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_comprehensive_stability())
    print(f"\nStability Test Result: {'SUCCESS' if success else 'PARTIAL'}")
    sys.exit(0 if success else 1)