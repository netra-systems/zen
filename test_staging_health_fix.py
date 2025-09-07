#!/usr/bin/env python3
"""
Test the staging health endpoint fix with simulated staging environment conditions.
"""

import asyncio
import os
import logging
from unittest.mock import MagicMock, patch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_staging_health_with_failing_optional_services():
    """Test health endpoint in staging with failing ClickHouse and Redis."""
    print("Testing staging health endpoint with failing optional services...")
    
    # Set environment to staging
    os.environ['ENVIRONMENT'] = 'staging'
    os.environ['CLICKHOUSE_REQUIRED'] = 'true'
    os.environ['REDIS_REQUIRED'] = 'true'
    
    try:
        from netra_backend.app.routes.health import health
        from unittest.mock import MagicMock
        
        # Create mock request for staging
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url = "https://api.staging.netrasystems.ai/health"
        mock_request.headers = {}
        mock_request.app.state = None
        
        mock_response = MagicMock()
        mock_response.headers = {}
        
        result = await health(mock_request, mock_response)
        print(f"Staging health result: {result}")
        
        # Check if it returns healthy even with failing optional services
        return result.get('status') in ['healthy', 'ready']
        
    except Exception as e:
        print(f"Staging health test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        # Clean up environment
        if 'ENVIRONMENT' in os.environ:
            del os.environ['ENVIRONMENT']
        if 'CLICKHOUSE_REQUIRED' in os.environ:
            del os.environ['CLICKHOUSE_REQUIRED']
        if 'REDIS_REQUIRED' in os.environ:
            del os.environ['REDIS_REQUIRED']

async def test_health_interface_basic_level():
    """Test the health interface at BASIC level specifically."""
    print("Testing health interface BASIC level...")
    
    try:
        from netra_backend.app.core.health import HealthInterface, HealthLevel
        
        # Create health interface
        health_interface = HealthInterface("test-service", "1.0.0")
        
        # Get basic health - should not call any checkers
        result = await health_interface.get_health_status(HealthLevel.BASIC)
        print(f"Basic health result: {result}")
        
        return result.get('status') == 'healthy'
        
    except Exception as e:
        print(f"Health interface test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Run staging health fix tests."""
    print("Testing staging health endpoint fix...")
    
    tests = [
        ("Health Interface BASIC Level", test_health_interface_basic_level),
        ("Staging Health with Failing Services", test_staging_health_with_failing_optional_services),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            success = await test_func()
            results.append((test_name, success))
            status = "PASSED" if success else "FAILED"
            print(f"{test_name}: {status}")
        except Exception as e:
            print(f"UNEXPECTED ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    print("\n--- SUMMARY ---")
    for test_name, success in results:
        status = "PASSED" if success else "FAILED"
        print(f"{test_name}: {status}")
    
    failed_count = sum(1 for _, success in results if not success)
    if failed_count > 0:
        print(f"\n{failed_count} test(s) failed - fix may not work properly in staging.")
        return 1
    else:
        print("\nAll tests passed - fix should work in staging.")
        return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except Exception as e:
        print(f"Script failed: {e}")
        exit(1)