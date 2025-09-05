#!/usr/bin/env python3
"""Test script to verify startup fixes for critical issues."""

import asyncio
import sys
import os
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_reliability_wrapper_fix():
    """Test that get_reliability_wrapper function is properly initialized."""
    print("Testing reliability wrapper fix...")
    try:
        from netra_backend.app.core.reliability import get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
        
        # Test that get_reliability_wrapper is callable (not None)
        assert callable(get_reliability_wrapper), "get_reliability_wrapper should be callable, not None"
        
        # Test creating a wrapper
        wrapper = get_reliability_wrapper(
            "test_agent",
            CircuitBreakerConfig(name="test_circuit"),
            RetryConfig(max_retries=3)
        )
        
        assert wrapper is not None, "Wrapper should be created successfully"
        assert hasattr(wrapper, 'execute_with_reliability'), "Wrapper should have execute_with_reliability method"
        
        print("[PASS] Reliability wrapper fix verified")
        return True
    except Exception as e:
        print(f"[FAIL] Reliability wrapper test failed: {e}")
        return False


async def test_database_transaction_fix():
    """Test that database transactions are properly handled."""
    print("Testing database transaction fix...")
    try:
        from netra_backend.app.db.database_manager import DatabaseManager
        from sqlalchemy import text
        
        # Create an engine for testing
        engine = DatabaseManager.create_application_engine()
        
        # Test connection with proper transaction handling
        async with engine.connect() as conn:
            # Test query in transaction
            async with conn.begin() as trans:
                try:
                    result = await conn.execute(text("SELECT 1"))
                    assert result.scalar() == 1
                    await trans.commit()
                except Exception as e:
                    await trans.rollback()
                    raise e
            
            # Test another query to ensure previous transaction doesn't affect it
            async with conn.begin() as trans:
                try:
                    result = await conn.execute(text("SELECT 2"))
                    assert result.scalar() == 2
                    await trans.commit()
                except Exception as e:
                    await trans.rollback()
                    raise e
        
        await engine.dispose()
        print("[PASS] Database transaction handling verified")
        return True
    except Exception as e:
        print(f"[FAIL] Database transaction test failed: {e}")
        return False


async def test_startup_sequence():
    """Test the complete startup sequence."""
    print("Testing startup sequence...")
    try:
        from netra_backend.app.startup_module import run_complete_startup
        from netra_backend.app.main import app
        
        # Run startup tasks
        await run_complete_startup(app)
        
        print("[PASS] Startup sequence completed successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Startup sequence failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("="*60)
    print("Running Startup Fix Verification Tests")
    print("="*60)
    
    tests = [
        test_reliability_wrapper_fix(),
        test_database_transaction_fix(),
        test_startup_sequence()
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    print("\n" + "="*60)
    print("Test Results Summary:")
    print("="*60)
    
    passed = sum(1 for r in results if r is True)
    failed = sum(1 for r in results if r is False or isinstance(r, Exception))
    
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed > 0:
        print("\n[WARNING] Some tests failed. Please review the output above.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All tests passed! Startup issues have been resolved.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())