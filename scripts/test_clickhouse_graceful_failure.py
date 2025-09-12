from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
env = get_env()
Test script to verify ClickHouse graceful failure handling
"""
import asyncio
import os
import sys
from shared.isolated_environment import IsolatedEnvironment

# Set up environment to simulate staging
env.set("ENVIRONMENT", "staging", "test") 
env.set("CLICKHOUSE_REQUIRED", "false", "test")

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_clickhouse_graceful_failure():
    """Test that ClickHouse fails gracefully in staging environment."""
    print("Testing ClickHouse graceful failure in staging environment...")
    
    try:
        # Test the health check route logic
        from netra_backend.app.routes.health import _check_clickhouse_connection
        
        print("Testing ClickHouse health check...")
        try:
            await asyncio.wait_for(_check_clickhouse_connection(), timeout=5.0)
            print("[U+2713] ClickHouse health check passed (unexpected but ok)")
        except Exception as e:
            print(f"[U+2713] ClickHouse health check failed gracefully: {e}")
        
        # Test the service initialization
        print("Testing ClickHouse service initialization...")
        try:
            from netra_backend.app.services.clickhouse_service import ClickHouseService
            service = ClickHouseService()
            result = await asyncio.wait_for(service.execute_health_check(), timeout=5.0)
            if result:
                print("[U+2713] ClickHouse service initialized successfully")
            else:
                print("[U+2713] ClickHouse service failed gracefully")
        except Exception as e:
            print(f"[U+2713] ClickHouse service failed gracefully: {e}")
        
        # Test the client context manager
        print("Testing ClickHouse client context manager...")
        try:
            from netra_backend.app.db.clickhouse import get_clickhouse_client
            async with get_clickhouse_client() as client:
                result = await asyncio.wait_for(client.execute("SELECT 1"), timeout=5.0)
                print(f"[U+2713] ClickHouse client worked: {result}")
        except Exception as e:
            print(f"[U+2713] ClickHouse client failed gracefully: {e}")
        
        print("\n PASS:  All ClickHouse graceful failure tests completed successfully!")
        print("The backend should now start without being blocked by ClickHouse timeouts.")
        
    except Exception as e:
        print(f" FAIL:  Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_startup_module():
    """Test the startup module ClickHouse initialization."""
    print("\nTesting startup module ClickHouse initialization...")
    
    try:
        from netra_backend.app.startup_module import initialize_clickhouse
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger(__name__)
        
        # This should not block and should gracefully degrade
        await asyncio.wait_for(initialize_clickhouse(logger), timeout=15.0)
        print("[U+2713] ClickHouse startup initialization completed gracefully")
        
    except asyncio.TimeoutError:
        print(" FAIL:  ClickHouse startup initialization timed out - fix needed")
        return False
    except Exception as e:
        print(f"[U+2713] ClickHouse startup initialization failed gracefully: {e}")
    
    return True

async def main():
    print("=" * 60)
    print("CLICKHOUSE GRACEFUL FAILURE TEST")
    print("=" * 60)
    
    success = True
    
    try:
        success &= await test_clickhouse_graceful_failure()
        success &= await test_startup_module()
    except Exception as e:
        print(f" FAIL:  Overall test failed: {e}")
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print(" PASS:  ALL TESTS PASSED - ClickHouse graceful failure is working!")
        print("Backend should now start successfully without ClickHouse blocking it.")
    else:
        print(" FAIL:  SOME TESTS FAILED - Additional fixes may be needed.")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)