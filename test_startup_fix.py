# Test script for Issue #1340 - Validate startup checks Row object fixes
import asyncio
import sys
sys.path.insert(0, '.')

async def test_startup_checks():
    print("Testing startup checks after Row object fixes...")

    try:
        from netra_backend.app.db.optimized_startup_checks import run_optimized_database_checks

        # Create a mock app object with minimal properties
        class MockApp:
            pass

        app = MockApp()

        # This should work without the await error now
        results = await run_optimized_database_checks(app)

        if results:
            print("+ Startup checks completed successfully")
            print(f"+ Results: {len(results)} checks executed")
            return True
        else:
            print("~ Startup checks returned empty results")
            return False

    except Exception as e:
        print(f"- Error during startup checks: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_startup_checks())
    sys.exit(0 if success else 1)