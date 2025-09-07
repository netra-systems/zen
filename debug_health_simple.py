#!/usr/bin/env python3
"""
Simple debug script for staging health endpoint 500 errors.
Tests the health endpoint components to find the root cause.
"""

import asyncio
import traceback
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_database_manager():
    """Test the database manager initialization and health check."""
    print("Testing DatabaseManager...")
    
    try:
        from netra_backend.app.db.database_manager import get_database_manager
        
        db_manager = get_database_manager()
        print(f"DatabaseManager created: {db_manager}")
        
        # Try to initialize
        print("Initializing DatabaseManager...")
        await db_manager.initialize()
        print("DatabaseManager initialized successfully")
        
        # Try health check
        print("Running health check...")
        result = await db_manager.health_check()
        print(f"Health check result: {result}")
        
        return result.get('status') == 'healthy'
        
    except Exception as e:
        print(f"DatabaseManager test failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def test_environment_vars():
    """Test environment variables configuration."""
    print("Testing environment configuration...")
    
    try:
        from shared.isolated_environment import get_env
        
        env = get_env()
        critical_vars = [
            'POSTGRES_HOST', 'REDIS_REQUIRED', 'CLICKHOUSE_REQUIRED'
        ]
        
        for var in critical_vars:
            value = env.get(var, 'NOT SET')
            print(f"{var}: {value}")
            
        return True
        
    except Exception as e:
        print(f"Environment test failed: {e}")
        return False

async def test_health_endpoint():
    """Test the actual health endpoint function."""
    print("Testing health endpoint function...")
    
    try:
        from netra_backend.app.routes.health import health
        from unittest.mock import MagicMock
        
        # Create mock request
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url = "http://testserver/health"
        mock_request.headers = {}
        mock_request.app.state = None
        
        mock_response = MagicMock()
        mock_response.headers = {}
        
        result = await health(mock_request, mock_response)
        print(f"Health endpoint result: {result}")
        
        return result.get('status') in ['healthy', 'ready']
        
    except Exception as e:
        print(f"Health endpoint test failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Run all tests to diagnose the health endpoint issue."""
    print("Starting health endpoint diagnostics...")
    
    tests = [
        ("Environment Variables", test_environment_vars),
        ("Database Manager", test_database_manager),
        ("Health Endpoint", test_health_endpoint),
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
        print(f"\n{failed_count} test(s) failed - these may be causing the 500 errors.")
        return 1
    else:
        print("\nAll tests passed.")
        return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except Exception as e:
        print(f"Script failed: {e}")
        exit(1)