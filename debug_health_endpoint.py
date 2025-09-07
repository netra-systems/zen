#!/usr/bin/env python3
"""
Debug script for staging health endpoint 500 errors.
Tests the health endpoint locally to understand what's causing the failures.
"""

import asyncio
import traceback
import logging
import sys
from typing import Dict, Any
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_health_endpoint_direct():
    """Test the health endpoint directly to see what's failing."""
    try:
        # Import the health router
        from netra_backend.app.routes.health import health, health_interface, response_builder
        from fastapi import Request
        from unittest.mock import MagicMock
        from fastapi.responses import Response
        
        print("=" * 60)
        print("TESTING HEALTH ENDPOINT DIRECTLY")
        print("=" * 60)
        
        # Create mock request and response objects
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url = "http://testserver/health"
        mock_request.headers = {}
        mock_request.app.state = None  # No app state in direct test
        
        mock_response = MagicMock()
        mock_response.headers = {}
        
        print("1. Testing basic health check function...")
        result = await health(mock_request, mock_response)
        print(f"SUCCESS Health check result: {result}")
        
    except Exception as e:
        print(f"ERROR Health check failed with error: {e}")
        print(f"Exception type: {type(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return False
        
    return True

async def test_database_components():
    """Test individual database health components."""
    try:
        print("\n" + "=" * 60)
        print("TESTING DATABASE COMPONENTS")
        print("=" * 60)
        
        # Test database manager
        print("1. Testing DatabaseManager...")
        from netra_backend.app.db.database_manager import get_database_manager
        
        db_manager = get_database_manager()
        print(f"   DatabaseManager created: {db_manager}")
        
        # Try to initialize
        print("2. Testing DatabaseManager initialization...")
        try:
            await db_manager.initialize()
            print("   SUCCESS DatabaseManager initialized successfully")
        except Exception as e:
            print(f"   ERROR DatabaseManager initialization failed: {e}")
            print(f"   Traceback: {traceback.format_exc()}")
            return False
        
        # Test health check
        print("3. Testing database health check...")
        try:
            health_result = await db_manager.health_check()
            print(f"   SUCCESS Database health check result: {health_result}")
        except Exception as e:
            print(f"   ERROR Database health check failed: {e}")
            print(f"   Traceback: {traceback.format_exc()}")
            return False
            
    except Exception as e:
        print(f"✗ Database component testing failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False
        
    return True

async def test_environment_config():
    """Test environment configuration."""
    try:
        print("\n" + "=" * 60)
        print("TESTING ENVIRONMENT CONFIGURATION")
        print("=" * 60)
        
        # Test isolated environment
        print("1. Testing isolated environment...")
        from shared.isolated_environment import get_env
        
        env = get_env()
        print(f"   Environment name: {env.get_environment_name()}")
        print(f"   Environment: {env.get('ENVIRONMENT', 'not set')}")
        
        # Test important health check related variables
        critical_vars = [
            'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB',
            'REDIS_HOST', 'REDIS_REQUIRED', 'CLICKHOUSE_HOST', 'CLICKHOUSE_REQUIRED',
            'DATABASE_URL'
        ]
        
        print("2. Testing critical environment variables...")
        for var in critical_vars:
            value = env.get(var, 'NOT SET')
            # Mask sensitive values
            if 'PASSWORD' in var or 'SECRET' in var:
                display_value = '***' if value != 'NOT SET' else 'NOT SET'
            else:
                display_value = value
            print(f"   {var}: {display_value}")
        
        # Test DatabaseURLBuilder
        print("3. Testing DatabaseURLBuilder...")
        from shared.database_url_builder import DatabaseURLBuilder
        
        builder = DatabaseURLBuilder(env.as_dict())
        print(f"   Environment: {builder.environment}")
        print(f"   Cloud SQL enabled: {builder.cloud_sql.is_cloud_sql}")
        print(f"   TCP config available: {builder.tcp.has_config}")
        
        validation_result = builder.validate()
        print(f"   Validation result: {validation_result}")
        
        # Try to get URL
        try:
            url = builder.get_url_for_environment(sync=False)
            if url:
                # Safe log message
                safe_msg = builder.get_safe_log_message()
                print(f"   ✓ Database URL built successfully: {safe_msg}")
            else:
                print("   ✗ Database URL is None")
        except Exception as e:
            print(f"   ✗ Database URL building failed: {e}")
            
    except Exception as e:
        print(f"✗ Environment config testing failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False
        
    return True

async def test_health_interface():
    """Test the health interface components."""
    try:
        print("\n" + "=" * 60)
        print("TESTING HEALTH INTERFACE")
        print("=" * 60)
        
        # Test health interface directly
        print("1. Testing health interface...")
        from netra_backend.app.routes.health import health_interface
        from netra_backend.app.core.health import HealthLevel
        
        try:
            health_status = await health_interface.get_health_status(HealthLevel.BASIC)
            print(f"   ✓ Health interface result: {health_status}")
        except Exception as e:
            print(f"   ✗ Health interface failed: {e}")
            print(f"   Traceback: {traceback.format_exc()}")
            return False
            
    except Exception as e:
        print(f"✗ Health interface testing failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False
        
    return True

async def main():
    """Run all diagnostic tests."""
    print("Starting health endpoint diagnostics...")
    
    tests = [
        ("Environment Configuration", test_environment_config),
        ("Database Components", test_database_components),
        ("Health Interface", test_health_interface),
        ("Health Endpoint Direct", test_health_endpoint_direct),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in {test_name}: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    failed_tests = [name for name, success in results if not success]
    if failed_tests:
        print(f"\nFailed tests: {', '.join(failed_tests)}")
        print("These failures may be causing the 500 errors in staging.")
        return 1
    else:
        print("\n✓ All tests passed - the issue may be staging environment specific.")
        return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nDiagnostics interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)