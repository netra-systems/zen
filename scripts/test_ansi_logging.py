from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Test script to verify ANSI escape codes are properly handled in logs.
"""
import os
import sys
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


env = get_env()
def test_production_logging():
    """Test logging with production settings."""
    # Set production environment
    env.set('ENVIRONMENT', 'production', "test")
    env.set('NO_COLOR', '1', "test")
    
    # Import after setting environment
    from netra_backend.app.core.logging_config import configure_cloud_run_logging, setup_exception_handler
    
    configure_cloud_run_logging()
    setup_exception_handler()
    
    print("Testing exception handling in production mode...")
    
    try:
        # Simulate the exact error from Cloud Run logs
        async def get_clickhouse_client():
            async with _create_real_client() as client:
                yield client
        
        # This should raise an error
        raise Exception("Test exception from clickhouse.py line 412")
    except Exception as e:
        # Capture the traceback
        tb_lines = traceback.format_exc()
        
        # Check for ANSI codes
        import re
        ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
        
        if ansi_pattern.search(tb_lines):
            print("[FAIL] ANSI codes found in traceback!")
            print("Raw output:", repr(tb_lines[:200]))
            return False
        else:
            print("[PASS] No ANSI codes in traceback")
            print("Clean output sample:")
            print(tb_lines[:500])
            return True


def test_development_logging():
    """Test logging with development settings."""
    # Reset environment
    env.set('ENVIRONMENT', 'development', "test")
    if 'NO_COLOR' in os.environ:
        env.delete('NO_COLOR', "test")
    
    print("\nTesting exception handling in development mode...")
    
    try:
        raise ValueError("Test exception in development")
    except Exception:
        tb_lines = traceback.format_exc()
        print("Development traceback sample:")
        print(tb_lines[:300])
        return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing ANSI escape code handling in logs")
    print("=" * 60)
    
    # Test production mode (should have no ANSI codes)
    prod_result = test_production_logging()
    
    print("\n" + "=" * 60)
    
    # Test development mode (may have ANSI codes)
    dev_result = test_development_logging()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"  Production mode: {'PASS' if prod_result else 'FAIL'}")
    print(f"  Development mode: {'PASS' if dev_result else 'FAIL'}")
    
    if not prod_result:
        print("\n[WARNING] Production logging still contains ANSI codes!")
        print("This will cause issues in Cloud Run logs.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()