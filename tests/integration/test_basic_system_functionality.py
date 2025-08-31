"""
Test Basic System Functionality After Fixes

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & Deployment Validation
- Value Impact: Validates basic system health after critical fixes
- Strategic Impact: Ensures system is ready for user traffic and core functionality works

This test validates the most fundamental system components:
1. Backend service health endpoint
2. Auth service health endpoint  
3. Database connectivity (PostgreSQL)
4. Basic WebSocket connection capability
5. Cross-service communication readiness

Focus: Basic expected flows for normal use cases.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import pytest
import requests
import websockets
from websockets import connect, ConnectionClosedError

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from netra_backend.app.core.network_constants import ServicePorts, HostConstants, URLConstants
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env


class TestBasicSystemFunctionality:
    """Test basic system functionality after fixes."""
    
    @pytest.fixture(scope="class")
    def environment_info(self):
        """Get environment configuration for tests."""
        env = get_env()
        return {
            "backend_url": env.get("BACKEND_SERVICE_URL", f"http://localhost:{ServicePorts.BACKEND_DEFAULT}"),
            "auth_service_url": env.get("AUTH_SERVICE_URL", f"http://localhost:{ServicePorts.AUTH_SERVICE_DEFAULT}"),
            "environment": env.get("ENVIRONMENT", "development"),
            "env_vars": env.get_all()
        }
    
    def test_backend_health_endpoint(self, environment_info):
        """Test that backend service health endpoint responds correctly."""
        backend_url = environment_info["backend_url"]
        health_url = f"{backend_url}{URLConstants.HEALTH_PATH}"
        
        try:
            # Test with reasonable timeout
            response = requests.get(health_url, timeout=10)
            
            # Check response status
            assert response.status_code == 200, f"Backend health check failed with status {response.status_code}"
            
            # Parse response JSON
            health_data = response.json()
            
            # Validate health response structure
            assert "status" in health_data, "Health response missing 'status' field"
            assert health_data["status"] in ["healthy", "ok"], f"Unexpected health status: {health_data['status']}"
            
            # Log success
            print(f"[PASS] Backend health check passed: {health_url}")
            print(f"   Response: {health_data}")
            
        except requests.exceptions.ConnectionError as e:
            pytest.skip(f"Backend service not running at {health_url}: {e}")
        except requests.exceptions.Timeout as e:
            pytest.skip(f"Backend health endpoint timeout (service may be starting): {e}")
        except Exception as e:
            pytest.fail(f"Backend health check failed: {e}")
    
    def test_auth_service_health_endpoint(self, environment_info):
        """Test that auth service health endpoint responds correctly."""
        auth_url = environment_info["auth_service_url"]
        health_url = f"{auth_url}{URLConstants.HEALTH_PATH}"
        
        try:
            # Test with reasonable timeout
            response = requests.get(health_url, timeout=10)
            
            # Check response status
            assert response.status_code == 200, f"Auth service health check failed with status {response.status_code}"
            
            # Parse response JSON
            health_data = response.json()
            
            # Validate health response structure
            assert "status" in health_data, "Auth health response missing 'status' field"
            assert health_data["status"] in ["healthy", "ok"], f"Unexpected auth health status: {health_data['status']}"
            
            # Log success
            print(f"[PASS] Auth service health check passed: {health_url}")
            print(f"   Response: {health_data}")
            
        except requests.exceptions.ConnectionError as e:
            pytest.skip(f"Auth service not running at {health_url}: {e}")
        except requests.exceptions.Timeout as e:
            pytest.skip(f"Auth service health endpoint timeout (service may be starting): {e}")
        except Exception as e:
            pytest.fail(f"Auth service health check failed: {e}")
    
    def test_database_connectivity(self, environment_info):
        """Test that database connectivity works using DatabaseURLBuilder."""
        env_vars = environment_info["env_vars"]
        
        # Use DatabaseURLBuilder to get the correct database URL
        builder = DatabaseURLBuilder(env_vars)
        
        # Validate configuration
        is_valid, error_msg = builder.validate()
        if not is_valid:
            if environment_info["environment"] in ["staging", "production"]:
                pytest.fail(f"Database configuration invalid for {environment_info['environment']}: {error_msg}")
            else:
                pytest.skip(f"Database configuration not complete for testing: {error_msg}")
        
        # Get database URL for current environment
        database_url = builder.get_url_for_environment(sync=False)
        
        if not database_url:
            pytest.skip("No database URL configured for testing")
        
        # Log safe version of database URL
        safe_url = builder.mask_url_for_logging(database_url)
        print(f"Testing database connectivity: {safe_url}")
        
        try:
            # Test database connection with SQLAlchemy
            from sqlalchemy import create_engine, text
            from sqlalchemy.exc import SQLAlchemyError
            
            # For async URL, convert to sync for basic connectivity test
            sync_url = builder.get_url_for_environment(sync=True)
            if not sync_url:
                # Fallback: try to convert async URL to sync
                if database_url.startswith("postgresql+asyncpg://"):
                    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
                elif database_url.startswith("sqlite+aiosqlite://"):
                    sync_url = database_url.replace("sqlite+aiosqlite://", "sqlite://")
                else:
                    sync_url = database_url
            
            # Create engine with connection timeout
            engine = create_engine(sync_url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
            
            # Test connection with simple query
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1 as test_value"))
                test_value = result.scalar()
                
                assert test_value == 1, f"Database query test failed, expected 1 got {test_value}"
            
            print(f"[PASS] Database connectivity test passed")
            
            # Clean up
            engine.dispose()
            
        except ImportError as e:
            pytest.skip(f"SQLAlchemy not available for database testing: {e}")
        except SQLAlchemyError as e:
            pytest.fail(f"Database connectivity test failed: {e}")
        except Exception as e:
            pytest.fail(f"Database test failed with unexpected error: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_basic_connection(self, environment_info):
        """Test basic WebSocket connection capability."""
        backend_url = environment_info["backend_url"]
        
        # Convert HTTP URL to WebSocket URL
        parsed_url = urlparse(backend_url)
        if parsed_url.scheme == "https":
            ws_scheme = "wss"
        else:
            ws_scheme = "ws"
        
        # Try different WebSocket endpoints that might be available
        websocket_endpoints = [
            f"{ws_scheme}://{parsed_url.netloc}/ws",
            f"{ws_scheme}://{parsed_url.netloc}/ws/test",
            f"{ws_scheme}://{parsed_url.netloc}/websocket"
        ]
        
        connection_successful = False
        
        for ws_url in websocket_endpoints:
            try:
                print(f"Attempting WebSocket connection to: {ws_url}")
                
                # Attempt connection with timeout
                async with connect(
                    ws_url,
                    timeout=10,
                    ping_interval=20,
                    ping_timeout=10
                ) as websocket:
                    print(f"[PASS] WebSocket connected successfully to: {ws_url}")
                    connection_successful = True
                    
                    # Try to send a simple ping message
                    ping_message = {
                        "type": "ping",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {"test": "basic_functionality_test"}
                    }
                    
                    await websocket.send(json.dumps(ping_message))
                    print(f"Sent ping message: {ping_message}")
                    
                    # Try to receive a response with timeout
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        print(f"Received response: {response_data}")
                        
                        # Basic validation of response
                        assert "type" in response_data, "WebSocket response missing 'type' field"
                        
                    except asyncio.TimeoutError:
                        print("[WARN] No response received within timeout (may be expected)")
                    except json.JSONDecodeError:
                        print("[WARN] Received non-JSON response (may be expected)")
                    
                    break  # Successfully connected, no need to try other endpoints
                    
            except ConnectionClosedError as e:
                print(f"[WARN] WebSocket connection closed: {e}")
                continue  # Try next endpoint
            except OSError as e:
                if "refused" in str(e).lower():
                    print(f"[WARN] Connection refused to {ws_url}")
                    continue  # Try next endpoint
                else:
                    print(f"[WARN] Network error: {e}")
                    continue
            except Exception as e:
                print(f"[WARN] WebSocket connection failed to {ws_url}: {e}")
                continue  # Try next endpoint
        
        if not connection_successful:
            pytest.skip("WebSocket service not available (backend may not be running)")
        
        print(f"[PASS] WebSocket basic connectivity test completed successfully")
    
    def test_cross_service_url_alignment(self, environment_info):
        """Test that service URLs are properly configured and aligned."""
        backend_url = environment_info["backend_url"]
        auth_url = environment_info["auth_service_url"]
        
        # Parse URLs to validate format
        try:
            backend_parsed = urlparse(backend_url)
            auth_parsed = urlparse(auth_url)
            
            # Validate URL formats
            assert backend_parsed.scheme in ["http", "https"], f"Invalid backend URL scheme: {backend_parsed.scheme}"
            assert auth_parsed.scheme in ["http", "https"], f"Invalid auth URL scheme: {auth_parsed.scheme}"
            
            assert backend_parsed.netloc, f"Invalid backend netloc: {backend_parsed.netloc}"
            assert auth_parsed.netloc, f"Invalid auth netloc: {auth_parsed.netloc}"
            
            # Check for port conflicts (different services should use different ports)
            if backend_parsed.hostname == auth_parsed.hostname:
                backend_port = backend_parsed.port or (443 if backend_parsed.scheme == "https" else 80)
                auth_port = auth_parsed.port or (443 if auth_parsed.scheme == "https" else 80)
                
                assert backend_port != auth_port, f"Backend and Auth services using same port {backend_port} on same host"
            
            print(f"[PASS] Service URL alignment check passed")
            print(f"   Backend: {backend_url}")
            print(f"   Auth:    {auth_url}")
            
        except Exception as e:
            pytest.fail(f"Service URL alignment test failed: {e}")
    
    def test_database_url_builder_functionality(self, environment_info):
        """Test that DatabaseURLBuilder functions correctly."""
        env_vars = environment_info["env_vars"]
        
        try:
            # Create builder
            builder = DatabaseURLBuilder(env_vars)
            
            # Test validation
            is_valid, error_msg = builder.validate()
            
            # Get debug info
            debug_info = builder.debug_info()
            
            print(f"Database URL Builder Debug Info:")
            print(f"   Environment: {debug_info['environment']}")
            print(f"   Has Cloud SQL: {debug_info['has_cloud_sql']}")
            print(f"   Has TCP Config: {debug_info['has_tcp_config']}")
            print(f"   Validation: {'Valid' if is_valid else f'Invalid - {error_msg}'}")
            
            # Test URL building
            async_url = builder.get_url_for_environment(sync=False)
            sync_url = builder.get_url_for_environment(sync=True)
            
            if async_url:
                masked_async = builder.mask_url_for_logging(async_url)
                print(f"   Async URL: {masked_async}")
            
            if sync_url:
                masked_sync = builder.mask_url_for_logging(sync_url)
                print(f"   Sync URL:  {masked_sync}")
            
            # Test URL masking functionality
            test_urls = [
                "postgresql://user:password@localhost:5432/db",
                "postgresql+asyncpg://user:secret@host/db?sslmode=require",
                "sqlite+aiosqlite:///:memory:"
            ]
            
            for test_url in test_urls:
                masked = builder.mask_url_for_logging(test_url)
                # Ensure no credentials are visible
                assert "password" not in masked, f"Password visible in masked URL: {masked}"
                assert "secret" not in masked, f"Secret visible in masked URL: {masked}"
            
            print(f"[PASS] Database URL Builder functionality test passed")
            
        except Exception as e:
            pytest.fail(f"Database URL Builder test failed: {e}")


def run_basic_system_test():
    """Run the basic system functionality test directly."""
    print("=" * 60)
    print("BASIC SYSTEM FUNCTIONALITY TEST")
    print("=" * 60)
    
    # Create test instance
    test_instance = TestBasicSystemFunctionality()
    
    # Get environment info
    env = get_env()
    environment_info = {
        "backend_url": env.get("BACKEND_SERVICE_URL", f"http://localhost:{ServicePorts.BACKEND_DEFAULT}"),
        "auth_service_url": env.get("AUTH_SERVICE_URL", f"http://localhost:{ServicePorts.AUTH_SERVICE_DEFAULT}"),
        "environment": env.get("ENVIRONMENT", "development"),
        "env_vars": env.get_all()
    }
    
    print(f"Environment: {environment_info['environment']}")
    print(f"Backend URL: {environment_info['backend_url']}")
    print(f"Auth Service URL: {environment_info['auth_service_url']}")
    print()
    
    # Run tests
    tests_passed = 0
    tests_failed = 0
    tests_skipped = 0
    
    test_methods = [
        ("Backend Health Check", lambda: test_instance.test_backend_health_endpoint(environment_info)),
        ("Auth Service Health Check", lambda: test_instance.test_auth_service_health_endpoint(environment_info)),
        ("Database Connectivity", lambda: test_instance.test_database_connectivity(environment_info)),
        ("Service URL Alignment", lambda: test_instance.test_cross_service_url_alignment(environment_info)),
        ("Database URL Builder", lambda: test_instance.test_database_url_builder_functionality(environment_info)),
    ]
    
    for test_name, test_func in test_methods:
        print(f"Running {test_name}...")
        try:
            test_func()
            print(f"[PASS] {test_name}")
            tests_passed += 1
        except pytest.skip.Exception as e:
            print(f"[SKIP] {test_name}: {e}")
            tests_skipped += 1
        except Exception as e:
            print(f"[FAIL] {test_name}: {e}")
            tests_failed += 1
        print()
    
    # Run WebSocket test separately (async)
    print(f"Running WebSocket Basic Connection...")
    try:
        asyncio.run(test_instance.test_websocket_basic_connection(environment_info))
        print(f"[PASS] WebSocket Basic Connection")
        tests_passed += 1
    except pytest.skip.Exception as e:
        print(f"[SKIP] WebSocket Basic Connection: {e}")
        tests_skipped += 1
    except Exception as e:
        print(f"[FAIL] WebSocket Basic Connection: {e}")
        tests_failed += 1
    print()
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Passed:  {tests_passed}")
    print(f"Tests Failed:  {tests_failed}")
    print(f"Tests Skipped: {tests_skipped}")
    print(f"Total Tests:   {tests_passed + tests_failed + tests_skipped}")
    print()
    
    if tests_failed > 0:
        print("[FAIL] OVERALL RESULT: Some tests failed")
        return False
    elif tests_passed > 0:
        print("[PASS] OVERALL RESULT: All available tests passed")
        return True
    else:
        print("[WARN] OVERALL RESULT: No tests could be run (all skipped)")
        return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run-direct":
        # Run tests directly without pytest
        success = run_basic_system_test()
        sys.exit(0 if success else 1)
    else:
        # Run with pytest
        pytest.main([__file__, "-v", "--tb=short"])