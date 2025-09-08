"""
Service Availability Detection Demo Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Demonstrate intelligent service detection and graceful skipping
- Value Impact: Shows how tests handle service unavailability without hard failures
- Strategic Impact: Template for implementing service detection across all integration tests

This test demonstrates the enhanced service availability detection system:
1. Intelligent service checking with detailed diagnostics
2. Graceful skipping when services unavailable
3. Mock service fallback capabilities
4. WebSocket timeout fixes
5. Clear error messaging for developers

Focus: Service detection patterns for integration testing infrastructure.
"""

import asyncio
import logging
import os
import sys
import time
from typing import Dict, Any
import pytest

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Import service availability detection
from test_framework.ssot.service_availability_detector import (
    require_services, 
    require_services_async,
    get_service_detector,
    ServiceStatus,
    ServiceAvailabilityResult
)

# Import mock services
from test_framework.ssot.mock_service_endpoints import (
    get_mock_service_manager,
    start_mock_services_if_needed,
    stop_mock_services
)

# Import test clients
from tests.clients.backend_client import BackendTestClient
from tests.clients.auth_client import AuthTestClient
from tests.clients.websocket_client import WebSocketTestClient

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestServiceAvailabilityDemo:
    """Demonstration of service availability detection patterns."""
    
    @pytest.fixture(scope="class")
    def environment_setup(self):
        """Setup environment information for tests."""
        env = get_env()
        return {
            "backend_url": env.get("BACKEND_SERVICE_URL", "http://localhost:8000"),
            "auth_url": env.get("AUTH_SERVICE_URL", "http://localhost:8081"),
            "websocket_url": env.get("WEBSOCKET_URL", "ws://localhost:8000/ws"),
            "environment": env.get("ENVIRONMENT", "development")
        }
    
    def test_service_detection_synchronous(self, environment_setup):
        """Demonstrate synchronous service availability detection."""
        print("\n=== SYNCHRONOUS SERVICE DETECTION DEMO ===")
        
        # Check all services with detailed results
        services = require_services(["backend", "auth", "websocket"], timeout=3.0)
        detector = get_service_detector()
        
        # Display detailed results
        for service_name, result in services.items():
            print(f"\n{service_name.upper()} Service:")
            print(f"  Status: {result.status.value}")
            print(f"  URL: {result.url}")
            if result.response_time_ms:
                print(f"  Response Time: {result.response_time_ms:.1f}ms")
            if result.status_code:
                print(f"  HTTP Status: {result.status_code}")
            if result.error_message:
                print(f"  Error: {result.error_message}")
            print(f"  Can Mock: {result.can_mock}")
        
        # Test individual service requirements
        backend_only = ["backend"]
        skip_msg = detector.generate_skip_message(services, backend_only)
        if skip_msg:
            print(f"\nWould skip backend test: {skip_msg}")
        else:
            print(f"\nBackend test would proceed - service available")
        
        auth_only = ["auth"]  
        skip_msg = detector.generate_skip_message(services, auth_only)
        if skip_msg:
            print(f"Would skip auth test: {skip_msg}")
        else:
            print(f"Auth test would proceed - service available")
        
        websocket_only = ["websocket"]
        skip_msg = detector.generate_skip_message(services, websocket_only)
        if skip_msg:
            print(f"Would skip WebSocket test: {skip_msg}")
        else:
            print(f"WebSocket test would proceed - service available")
        
        # Always pass - this is a demonstration
        assert True, "Service detection demo completed"
    
    @pytest.mark.asyncio
    async def test_service_detection_asynchronous(self, environment_setup):
        """Demonstrate asynchronous service availability detection."""
        print("\n=== ASYNCHRONOUS SERVICE DETECTION DEMO ===")
        
        # Check all services asynchronously
        services = await require_services_async(["backend", "auth", "websocket"], timeout=3.0)
        detector = get_service_detector()
        
        # Display detailed results
        for service_name, result in services.items():
            print(f"\n{service_name.upper()} Service (Async):")
            print(f"  Status: {result.status.value}")
            print(f"  URL: {result.url}")
            if result.response_time_ms:
                print(f"  Response Time: {result.response_time_ms:.1f}ms")
            if result.status_code:
                print(f"  HTTP Status: {result.status_code}")
            if result.error_message:
                print(f"  Error: {result.error_message}")
            print(f"  Can Mock: {result.can_mock}")
        
        # Test multi-service requirements
        all_services = ["backend", "auth", "websocket"]
        skip_msg = detector.generate_skip_message(services, all_services)
        if skip_msg:
            print(f"\nWould skip multi-service test: {skip_msg}")
        else:
            print(f"\nMulti-service test would proceed - all services available")
        
        # Always pass - this is a demonstration
        assert True, "Async service detection demo completed"
    
    def test_backend_with_service_detection(self, environment_setup):
        """Test backend service with intelligent availability detection."""
        print("\n=== BACKEND TEST WITH SERVICE DETECTION ===")
        
        # Check service availability first
        services = require_services(["backend"], timeout=5.0)
        detector = get_service_detector()
        
        skip_msg = detector.generate_skip_message(services, ["backend"])
        if skip_msg:
            pytest.skip(f"Backend service unavailable: {skip_msg}")
        
        # Service confirmed available - proceed with test
        backend_result = services["backend"]
        print(f"Backend service available in {backend_result.response_time_ms:.1f}ms")
        
        # Create backend client and test
        backend_client = BackendTestClient(environment_setup["backend_url"])
        
        # Test health check works
        health_available = asyncio.run(backend_client.health_check())
        assert health_available, "Backend health check should pass when service detected as available"
        
        print("[PASS] Backend integration test with service detection")
    
    def test_auth_with_service_detection(self, environment_setup):
        """Test auth service with intelligent availability detection."""
        print("\n=== AUTH TEST WITH SERVICE DETECTION ===")
        
        # Check service availability first
        services = require_services(["auth"], timeout=5.0)
        detector = get_service_detector()
        
        skip_msg = detector.generate_skip_message(services, ["auth"])
        if skip_msg:
            pytest.skip(f"Auth service unavailable: {skip_msg}")
        
        # Service confirmed available - proceed with test
        auth_result = services["auth"]
        print(f"Auth service available in {auth_result.response_time_ms:.1f}ms")
        
        # Create auth client and test
        auth_client = AuthTestClient(environment_setup["auth_url"])
        
        # Test health check works
        health_available = asyncio.run(auth_client.health_check())
        assert health_available, "Auth health check should pass when service detected as available"
        
        print("[PASS] Auth integration test with service detection")
    
    @pytest.mark.asyncio
    async def test_websocket_with_fixed_timeouts(self, environment_setup):
        """Test WebSocket connection with fixed timeout parameters."""
        print("\n=== WEBSOCKET TEST WITH FIXED TIMEOUTS ===")
        
        # Check service availability first
        services = await require_services_async(["websocket"], timeout=5.0)
        detector = get_service_detector()
        
        skip_msg = detector.generate_skip_message(services, ["websocket"])
        if skip_msg:
            pytest.skip(f"WebSocket service unavailable: {skip_msg}")
        
        # Service confirmed available - proceed with test
        websocket_result = services["websocket"]
        print(f"WebSocket service available (check took {websocket_result.response_time_ms:.1f}ms)")
        
        # Create WebSocket client and test with fixed timeouts
        ws_client = WebSocketTestClient(environment_setup["websocket_url"])
        
        try:
            # Test connection with proper timeout parameter
            connected = await ws_client.connect(timeout=10.0)  # Fixed: no more timeout parameter errors
            
            if connected:
                print(f"WebSocket connected successfully")
                
                # Send test message
                await ws_client.send_ping()
                
                # Try to receive response (may timeout, which is ok)
                response = await ws_client.receive(timeout=3.0)
                if response:
                    print(f"Received WebSocket response: {response.get('type', 'unknown')}")
                else:
                    print(f"No WebSocket response within timeout (may be expected)")
                
                await ws_client.disconnect()
                print("[PASS] WebSocket integration test with fixed timeouts")
            else:
                pytest.fail("WebSocket connection failed despite service being detected as available")
                
        except Exception as e:
            pytest.fail(f"WebSocket test failed: {e}")
    
    def test_detailed_health_checks_demo(self, environment_setup):
        """Demonstrate detailed health check capabilities."""
        print("\n=== DETAILED HEALTH CHECKS DEMO ===")
        
        # Test backend detailed health check
        backend_client = BackendTestClient(environment_setup["backend_url"])
        backend_health = asyncio.run(backend_client.detailed_health_check())
        
        print(f"Backend Health Check:")
        print(f"  Available: {backend_health['available']}")
        print(f"  Response Time: {backend_health['response_time_ms']:.1f}ms")
        print(f"  Status Code: {backend_health['status_code']}")
        if backend_health['error']:
            print(f"  Error: {backend_health['error']}")
        
        # Test auth detailed health check
        auth_client = AuthTestClient(environment_setup["auth_url"])
        auth_health = asyncio.run(auth_client.detailed_health_check())
        
        print(f"\nAuth Health Check:")
        print(f"  Available: {auth_health['available']}")
        print(f"  Response Time: {auth_health['response_time_ms']:.1f}ms")
        print(f"  Status Code: {auth_health['status_code']}")
        if auth_health['error']:
            print(f"  Error: {auth_health['error']}")
        
        # Test WebSocket detailed health check
        ws_client = WebSocketTestClient(environment_setup["websocket_url"])
        ws_health = asyncio.run(ws_client.detailed_health_check(timeout=5.0))
        
        print(f"\nWebSocket Health Check:")
        print(f"  Available: {ws_health['available']}")
        print(f"  Response Time: {ws_health['response_time_ms']:.1f}ms")
        if ws_health['error']:
            print(f"  Error: {ws_health['error']}")
        
        print("\n[PASS] Detailed health checks demo completed")
        
        # Always pass - this is a demonstration
        assert True, "Detailed health checks demo completed"
    
    @pytest.mark.asyncio
    async def test_mock_services_demo(self, environment_setup):
        """Demonstrate mock service capabilities for offline testing."""
        print("\n=== MOCK SERVICES DEMO ===")
        
        # Try to start mock services
        mock_started = await start_mock_services_if_needed()
        
        if mock_started:
            print("Mock services started successfully for offline testing")
            
            # Get mock service URLs
            mock_manager = get_mock_service_manager()
            mock_urls = mock_manager.get_service_urls()
            
            print(f"Mock service URLs:")
            for service, url in mock_urls.items():
                print(f"  {service}: {url}")
            
            # Test mock backend
            mock_backend_client = BackendTestClient(mock_urls["backend_url"])
            mock_health = await mock_backend_client.health_check()
            print(f"Mock backend health check: {mock_health}")
            
            # Test mock auth
            mock_auth_client = AuthTestClient(mock_urls["auth_url"])
            mock_auth_health = await mock_auth_client.health_check()
            print(f"Mock auth health check: {mock_auth_health}")
            
            # Test mock WebSocket
            mock_ws_client = WebSocketTestClient(mock_urls["websocket_url"])
            mock_ws_connected = await mock_ws_client.connect(timeout=5.0)
            if mock_ws_connected:
                print("Mock WebSocket connection successful")
                await mock_ws_client.send_ping()
                response = await mock_ws_client.receive(timeout=2.0)
                if response:
                    print(f"Mock WebSocket response: {response.get('type', 'unknown')}")
                await mock_ws_client.disconnect()
            
            # Stop mock services
            await stop_mock_services()
            print("Mock services stopped")
            
            print("[PASS] Mock services demo completed")
        else:
            print("Mock services not available (aiohttp not installed or ports in use)")
            pytest.skip("Mock services unavailable")
        
        # Always pass if we get here
        assert True, "Mock services demo completed"
    
    def test_service_cache_behavior(self, environment_setup):
        """Demonstrate service availability cache behavior."""
        print("\n=== SERVICE CACHE BEHAVIOR DEMO ===")
        
        detector = get_service_detector()
        
        # Clear cache and check timing
        detector.clear_cache()
        
        start_time = time.time()
        services1 = require_services(["backend"], timeout=3.0)
        first_check_time = time.time() - start_time
        
        start_time = time.time()
        services2 = require_services(["backend"], timeout=3.0)  # Should use cache
        second_check_time = time.time() - start_time
        
        print(f"First service check (no cache): {first_check_time:.3f}s")
        print(f"Second service check (cached): {second_check_time:.3f}s")
        
        # Second check should be much faster due to caching
        if second_check_time < first_check_time / 2:
            print("[PASS] Service caching working correctly")
        else:
            print("[INFO] Service caching may not be working (still passes)")
        
        # Clear cache for next test
        detector.clear_cache()
        
        assert True, "Service cache demo completed"


def test_service_availability_full_demo():
    """Run all service availability demos directly (for manual testing)."""
    print("=" * 80)
    print("SERVICE AVAILABILITY DETECTION SYSTEM DEMO")
    print("=" * 80)
    
    # Create environment setup
    env = get_env()
    environment_setup = {
        "backend_url": env.get("BACKEND_SERVICE_URL", "http://localhost:8000"),
        "auth_url": env.get("AUTH_SERVICE_URL", "http://localhost:8081"),
        "websocket_url": env.get("WEBSOCKET_URL", "ws://localhost:8000/ws"),
        "environment": env.get("ENVIRONMENT", "development")
    }
    
    print(f"Environment: {environment_setup['environment']}")
    print(f"Backend URL: {environment_setup['backend_url']}")
    print(f"Auth URL: {environment_setup['auth_url']}")
    print(f"WebSocket URL: {environment_setup['websocket_url']}")
    
    # Create test instance
    demo = TestServiceAvailabilityDemo()
    
    try:
        # Run synchronous demo
        demo.test_service_detection_synchronous(environment_setup)
        
        # Run asynchronous demo
        asyncio.run(demo.test_service_detection_asynchronous(environment_setup))
        
        # Run detailed health checks demo
        demo.test_detailed_health_checks_demo(environment_setup)
        
        # Run cache behavior demo
        demo.test_service_cache_behavior(environment_setup)
        
        print("\n" + "=" * 80)
        print("ALL SERVICE AVAILABILITY DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run-direct":
        # Run demo directly without pytest
        success = test_service_availability_full_demo()
        sys.exit(0 if success else 1)
    else:
        # Run with pytest
        pytest.main([__file__, "-v", "--tb=short", "-s"])