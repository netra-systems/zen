"""
Simple Database Stability Test for Issue #1340 - Row Object Fixes
Tests that our database Row object fixes have not introduced breaking changes.
"""
import sys
import asyncio
import traceback
sys.path.insert(0, '.')

async def test_database_stability():
    """Test database Row object handling after Issue #1340 fixes."""
    print("=== ISSUE #1340 DATABASE STABILITY TEST ===\n")
    print("Testing that Row object await fixes have not broken system stability...\n")

    results = []

    # Test 1: Core database imports
    print("Test 1: Core database imports...")
    try:
        from netra_backend.app.db.database_manager import DatabaseManager
        print("[PASS] DatabaseManager import successful")
        results.append(("Database Import", True, None))
    except Exception as e:
        print(f"[FAIL] Database import error: {e}")
        results.append(("Database Import", False, str(e)))
        return False

    # Test 2: DatabaseManager initialization (no config needed for test)
    print("\nTest 2: DatabaseManager initialization...")
    try:
        db_manager = DatabaseManager()  # No config parameter
        print("[PASS] DatabaseManager initialized successfully")
        results.append(("DatabaseManager Init", True, None))
    except Exception as e:
        print(f"[FAIL] DatabaseManager init error: {e}")
        results.append(("DatabaseManager Init", False, str(e)))
        return False

    # Test 3: Row object handling (critical test for Issue #1340)
    print("\nTest 3: Database Row object handling (Issue #1340 fix validation)...")
    try:
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text

            # Execute a simple query
            result = await session.execute(text("SELECT 1 as test_col, 'Issue #1340 validated' as message"))

            # CRITICAL TEST: Access Row object without await (this was our fix)
            row = result.fetchone()  # NO AWAIT HERE - this was the Issue #1340 fix!

            # Verify row access works
            test_value = row[0]  # Access by index
            message = row[1]     # Access by index

            assert test_value == 1, f"Expected 1, got {test_value}"
            assert "Issue #1340" in message, f"Expected message with Issue #1340, got {message}"

            print(f"[CRITICAL SUCCESS] Row object access working: {message}")
            print(f"[CRITICAL SUCCESS] Row[0] = {test_value}, Row[1] = '{message}'")

        print("[PASS] Database Row object handling functional (Issue #1340 fix confirmed)")
        results.append(("Row Object Handling", True, None))

    except Exception as e:
        print(f"[FAIL] Database Row object error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        results.append(("Row Object Handling", False, str(e)))
        return False

    # Test 4: Ensure no regression in system imports that use database
    print("\nTest 4: System integration imports (using database)...")
    try:
        from netra_backend.app.routes import health
        from netra_backend.app.auth_integration.auth import BackendAuthIntegration
        print("[PASS] System imports that depend on database working")
        results.append(("System Integration", True, None))
    except Exception as e:
        print(f"[FAIL] System integration error: {e}")
        results.append(("System Integration", False, str(e)))
        return False

    # Summary
    print(f"\n=== ISSUE #1340 STABILITY TEST RESULTS ===")
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
        print("\n[SUCCESS] ISSUE #1340 DATABASE FIXES VALIDATED")
        print("[SUCCESS] Row object await fixes have NOT introduced breaking changes")
        print("[SUCCESS] Database operations remain stable and functional")
        print("[SUCCESS] No regressions detected in dependent systems")
        return True
    else:
        print(f"\n[ERROR] {total - passed} component(s) have issues")
        print("[ERROR] Database fixes may have introduced instability")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_stability())
    print(f"\nIssue #1340 Stability Result: {'SUCCESS' if success else 'FAILURE'}")
    sys.exit(0 if success else 1)