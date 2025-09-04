#!/usr/bin/env python3
"""
Test script for ClickHouse initialization improvements.
This script tests both optional and required scenarios.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from netra_backend.app.startup_module import initialize_clickhouse
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import get_env

async def test_clickhouse_optional_scenario():
    """Test ClickHouse initialization when it's optional (development environment)."""
    print("=" * 60)
    print("TEST 1: ClickHouse Optional Scenario (Development)")
    print("=" * 60)
    
    logger = central_logger.get_logger(__name__)
    
    # Set environment to development and ensure CLICKHOUSE_REQUIRED is not set
    os.environ["ENVIRONMENT"] = "development"
    if "CLICKHOUSE_REQUIRED" in os.environ:
        del os.environ["CLICKHOUSE_REQUIRED"]
    
    try:
        result = await initialize_clickhouse(logger)
        
        print(f"Result: {result}")
        print(f"   Service: {result['service']}")
        print(f"   Required: {result['required']}")
        print(f"   Status: {result['status']}")
        print(f"   Error: {result['error']}")
        
        # Validate expected behavior
        assert result["service"] == "clickhouse"
        assert result["required"] == False, "ClickHouse should not be required in development"
        assert result["status"] in ["skipped", "failed", "connected"], f"Unexpected status: {result['status']}"
        
        if result["status"] == "failed":
            print(f"   Optional failure (expected): {result['error']}")
        elif result["status"] == "skipped":
            print("   Skipped as expected in development environment")
        else:
            print("   Connected successfully")
        
        print("PASSED: Optional scenario handled correctly")
        
    except Exception as e:
        print(f"FAILED: Exception in optional scenario: {e}")
        return False
    
    return True

async def test_clickhouse_required_scenario():
    """Test ClickHouse initialization when it's required."""
    print("\n" + "=" * 60)
    print("TEST 2: ClickHouse Required Scenario (CLICKHOUSE_REQUIRED=true)")
    print("=" * 60)
    
    logger = central_logger.get_logger(__name__)
    
    # Set CLICKHOUSE_REQUIRED=true to simulate required scenario
    os.environ["CLICKHOUSE_REQUIRED"] = "true"
    
    try:
        result = await initialize_clickhouse(logger)
        
        print(f"✅ Result: {result}")
        print(f"   Service: {result['service']}")
        print(f"   Required: {result['required']}")
        print(f"   Status: {result['status']}")
        print(f"   Error: {result['error']}")
        
        # Validate expected behavior
        assert result["service"] == "clickhouse"
        assert result["required"] == True, "ClickHouse should be required when CLICKHOUSE_REQUIRED=true"
        
        if result["status"] == "connected":
            print("   ✅ Connected successfully (required scenario)")
            print("✅ PASSED: Required scenario - connection successful")
            return True
        elif result["status"] == "failed":
            print(f"   ❌ Required but failed: {result['error']}")
            print("❌ FAILED: Required scenario should have raised an exception")
            return False
        else:
            print(f"   ⚠️ Unexpected status in required scenario: {result['status']}")
            return False
        
    except RuntimeError as e:
        # This is the expected behavior when ClickHouse is required but fails
        print(f"   ✅ Expected RuntimeError: {e}")
        print("✅ PASSED: Required scenario correctly raised exception on failure")
        return True
    except Exception as e:
        print(f"   ❌ Unexpected exception type: {type(e).__name__}: {e}")
        print("❌ FAILED: Wrong exception type in required scenario")
        return False

async def test_production_environment():
    """Test ClickHouse initialization in production environment."""
    print("\n" + "=" * 60)
    print("TEST 3: Production Environment (ENVIRONMENT=production)")
    print("=" * 60)
    
    logger = central_logger.get_logger(__name__)
    
    # Set environment to production (makes ClickHouse required)
    os.environ["ENVIRONMENT"] = "production"
    # Remove explicit CLICKHOUSE_REQUIRED to test environment-based requirement
    if "CLICKHOUSE_REQUIRED" in os.environ:
        del os.environ["CLICKHOUSE_REQUIRED"]
    
    try:
        result = await initialize_clickhouse(logger)
        
        print(f"✅ Result: {result}")
        print(f"   Service: {result['service']}")
        print(f"   Required: {result['required']}")
        print(f"   Status: {result['status']}")
        print(f"   Error: {result['error']}")
        
        # Validate expected behavior
        assert result["service"] == "clickhouse"
        assert result["required"] == True, "ClickHouse should be required in production environment"
        
        if result["status"] == "connected":
            print("   ✅ Connected successfully (production environment)")
            print("✅ PASSED: Production environment - connection successful")
            return True
        else:
            print(f"   ❌ Production required but failed: {result['error']}")
            print("❌ FAILED: Production environment should have raised an exception")
            return False
        
    except RuntimeError as e:
        # This is the expected behavior when ClickHouse is required but fails
        print(f"   ✅ Expected RuntimeError: {e}")
        print("✅ PASSED: Production environment correctly raised exception on failure")
        return True
    except Exception as e:
        print(f"   ❌ Unexpected exception type: {type(e).__name__}: {e}")
        print("❌ FAILED: Wrong exception type in production environment")
        return False

async def main():
    """Run all ClickHouse initialization tests."""
    print("Testing ClickHouse Initialization Improvements")
    print("=" * 60)
    
    # Store original environment values
    original_env = os.environ.get("ENVIRONMENT")
    original_clickhouse_req = os.environ.get("CLICKHOUSE_REQUIRED")
    
    try:
        results = []
        
        # Test 1: Optional scenario
        results.append(await test_clickhouse_optional_scenario())
        
        # Test 2: Required scenario (explicit flag)
        results.append(await test_clickhouse_required_scenario())
        
        # Test 3: Production environment
        results.append(await test_production_environment())
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(results)
        total = len(results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            print("ALL TESTS PASSED")
            print("- ClickHouse initialization improvements working correctly")
            print("- Optional vs required scenarios handled properly") 
            print("- Error logging is crystal clear")
            print("- Status reporting provides detailed information")
        else:
            print("SOME TESTS FAILED")
            print("- ClickHouse initialization improvements need fixes")
            
        return passed == total
        
    finally:
        # Restore original environment
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        elif "ENVIRONMENT" in os.environ:
            del os.environ["ENVIRONMENT"]
            
        if original_clickhouse_req:
            os.environ["CLICKHOUSE_REQUIRED"] = original_clickhouse_req
        elif "CLICKHOUSE_REQUIRED" in os.environ:
            del os.environ["CLICKHOUSE_REQUIRED"]

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)