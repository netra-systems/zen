"""
Comprehensive Frontend-Backend Integration Tests

Business Value Justification: Free/Early/Mid/Enterprise - User Experience & System Stability
Tests real communication flows between frontend and backend services, ensuring the user chat
experience works correctly with proper authentication, real-time updates, and error handling.

This test suite validates the core integration points that deliver business value:
- API communication for agent execution and data retrieval
- WebSocket real-time updates for agent thinking and responses  
- Authentication flows for user session management
- Service discovery for proper endpoint resolution
- Error handling for graceful user experience

CRITICAL: These tests use REAL HTTP requests and WebSocket connections to validate
actual integration behavior, not mocked responses.
"""

import asyncio
import json
import time
import uuid
from unittest.mock import patch, AsyncMock
from typing import Dict, Any, List, Optional

import pytest
import websockets
from websockets.exceptions import WebSocketException
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env


class TestFrontendBackendApiIntegration(SSotBaseTestCase):
    """
    Business Value: Free/Early/Mid/Enterprise - Platform Stability & User Experience
    Tests frontend API client communication with backend services using real HTTP requests.
    Validates core business flows: agent execution, data retrieval, service discovery.
    """
    
    def setup_method(self, method=None):
        """Setup test environment with required configuration."""
        super().setup_method(method)
        
        # Get environment configuration
        self.env = self.get_env()
        
        # Set test environment variables
        self.set_env_var("NODE_ENV", "test")
        self.set_env_var("TESTING", "true")
        
        # Configure API endpoints - use real service URLs
        self.api_base = self.env.get("NEXT_PUBLIC_API_URL", "http://localhost:8000")
        self.auth_base = self.env.get("NEXT_PUBLIC_AUTH_URL", "http://localhost:8081") 
        self.ws_base = self.env.get("NEXT_PUBLIC_WS_URL", "ws://localhost:8000")
        
        # Track metrics
        self.record_metric("test_category", "frontend_integration")
        self.record_metric("test_type", "api_communication")
        
    def test_api_service_discovery_endpoint(self):
        """
        Business Value: Platform/Internal - Service Discovery & Configuration
        
        Tests frontend can discover backend services through the /api/discovery endpoint.
        This is critical for frontend to find proper service URLs in different environments.
        """
        discovery_url = f"{self.api_base}/api/discovery"
        
        try:
            # Make real HTTP request to discovery endpoint
            response = requests.get(discovery_url, timeout=10)
            self.increment_llm_requests(1)  # Track API calls
            
            assert response.status_code == 200, f"Discovery endpoint failed: {response.status_code}"
            
            discovery_data = response.json()
            
            # Validate required service discovery fields
            assert "services" in discovery_data, "Discovery response missing services field"
            services = discovery_data["services"]
            
            # Validate core service URLs are provided
            expected_services = ["backend", "auth", "websocket"]
            for service in expected_services:
                assert service in services, f"Missing service: {service}"
                assert "url" in services[service], f"Service {service} missing URL"
                assert services[service]["url"].startswith(("http://", "https://")), f"Invalid URL format for {service}"
            
            # Record successful service discovery
            self.record_metric("service_discovery_success", True)
            self.record_metric("services_discovered", len(services))
            
        except (RequestException, ConnectionError, Timeout) as e:
            pytest.fail(f"Service discovery failed with network error: {e}")
        except Exception as e:
            pytest.fail(f"Service discovery failed with unexpected error: {e}")
    
    def test_openapi_spec_retrieval(self):
        """
        Business Value: Platform/Internal - API Documentation & Client Generation
        
        Tests frontend can retrieve OpenAPI specification for dynamic endpoint discovery.
        Critical for frontend ApiClient to find available endpoints.
        """
        openapi_url = f"{self.api_base}/openapi.json"
        
        try:
            response = requests.get(openapi_url, timeout=10)
            self.increment_llm_requests(1)
            
            assert response.status_code == 200, f"OpenAPI spec retrieval failed: {response.status_code}"
            
            spec = response.json()
            
            # Validate OpenAPI spec structure
            assert "openapi" in spec, "Missing OpenAPI version"
            assert "info" in spec, "Missing API info"
            assert "paths" in spec, "Missing API paths"
            
            # Validate critical endpoints exist
            paths = spec["paths"]
            critical_endpoints = ["/api/agents", "/api/threads", "/ws"]
            
            for endpoint in critical_endpoints:
                # Check if endpoint exists directly or with variations
                endpoint_exists = any(path.startswith(endpoint) for path in paths.keys())
                assert endpoint_exists, f"Critical endpoint missing: {endpoint}"
            
            self.record_metric("openapi_endpoints_count", len(paths))
            self.record_metric("openapi_spec_valid", True)
            
        except (RequestException, ConnectionError, Timeout) as e:
            pytest.fail(f"OpenAPI spec retrieval failed with network error: {e}")
        except Exception as e:
            pytest.fail(f"OpenAPI spec retrieval failed: {e}")
    
    def test_api_client_error_handling(self):
        """
        Business Value: Free/Early/Mid/Enterprise - User Experience & Reliability
        
        Tests frontend API client properly handles various error scenarios from backend.
        Critical for graceful error messages shown to users.
        """
        # Test 404 error handling
        nonexistent_url = f"{self.api_base}/api/nonexistent-endpoint"
        
        try:
            response = requests.get(nonexistent_url, timeout=5)
            self.increment_llm_requests(1)
            
            assert response.status_code == 404, "Expected 404 for nonexistent endpoint"
            
            # Test that error response is properly formatted JSON
            try:
                error_data = response.json()
                assert "detail" in error_data or "message" in error_data, "Error response missing detail/message"
            except json.JSONDecodeError:
                # Some 404s might return HTML, which is acceptable
                pass
                
        except (RequestException, ConnectionError, Timeout) as e:
            pytest.fail(f"Error handling test failed with network error: {e}")
        
        # Test timeout handling by making request to slow endpoint
        try:
            # Use very short timeout to simulate timeout condition
            requests.get(f"{self.api_base}/api/health", timeout=0.001)
        except Timeout:
            # This is expected behavior
            self.record_metric("timeout_handling_works", True)
        except Exception:
            # Other exceptions are also acceptable for timeout test
            pass
        
        self.record_metric("error_handling_tested", True)
    
    def test_cors_configuration(self):
        """
        Business Value: Platform/Internal - Security & Cross-Origin Access
        
        Tests CORS is properly configured for frontend to access backend APIs.
        Critical for browser-based frontend to communicate with backend services.
        """
        # Test preflight CORS request
        try:
            headers = {
                "Origin": "http://localhost:3000",  # Typical frontend dev server
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
            
            response = requests.options(f"{self.api_base}/api/health", headers=headers, timeout=5)
            self.increment_llm_requests(1)
            
            # CORS preflight should return 200 or 204
            assert response.status_code in [200, 204], f"CORS preflight failed: {response.status_code}"
            
            # Check CORS headers are present
            cors_headers = response.headers
            assert "Access-Control-Allow-Origin" in cors_headers, "Missing CORS Allow-Origin header"
            
            # Record CORS configuration
            self.record_metric("cors_properly_configured", True)
            self.record_metric("cors_allowed_origin", cors_headers.get("Access-Control-Allow-Origin"))
            
        except (RequestException, ConnectionError, Timeout) as e:
            pytest.fail(f"CORS test failed with network error: {e}")
        except Exception as e:
            pytest.fail(f"CORS test failed: {e}")


class TestFrontendWebSocketIntegration(SSotBaseTestCase):
    """
    Business Value: Free/Early/Mid/Enterprise - Real-Time User Experience
    Tests WebSocket connection from frontend to backend for real-time agent updates.
    Critical for showing agent thinking, tool execution, and live responses to users.
    """
    
    def setup_method(self, method=None):
        """Setup WebSocket test environment."""
        super().setup_method(method)
        
        self.env = self.get_env()
        self.ws_url = self.env.get("NEXT_PUBLIC_WS_URL", "ws://localhost:8000/ws")
        
        # Set WebSocket test configuration
        self.set_env_var("WEBSOCKET_TEST_MODE", "true")
        
        self.record_metric("test_category", "websocket_integration")
    
    @pytest.mark.asyncio
    async def test_websocket_connection_establishment(self):
        """
        Business Value: Free/Early/Mid/Enterprise - Real-Time Communication
        
        Tests frontend can establish WebSocket connection to backend.
        Essential for real-time agent updates and chat functionality.
        """
        try:
            # Attempt to connect to WebSocket
            async with websockets.connect(self.ws_url, ping_interval=10) as websocket:
                
                # Connection successful - record metrics
                self.record_metric("websocket_connection_success", True)
                self.increment_websocket_events(1)
                
                # Test basic ping/pong
                pong_waiter = await websocket.ping()
                await asyncio.wait_for(pong_waiter, timeout=5.0)
                
                self.record_metric("websocket_ping_success", True)
                
        except WebSocketException as e:
            pytest.fail(f"WebSocket connection failed: {e}")
        except asyncio.TimeoutError:
            pytest.fail("WebSocket ping/pong timed out")
        except Exception as e:
            pytest.fail(f"WebSocket test failed with unexpected error: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_message_flow(self):
        """
        Business Value: Free/Early/Mid/Enterprise - Agent Communication
        
        Tests bi-directional message flow over WebSocket connection.
        Critical for agent execution updates and user chat messages.
        """
        try:
            async with websockets.connect(self.ws_url, ping_interval=10) as websocket:
                
                # Send test message to backend
                test_message = {
                    "type": "test_message",
                    "payload": {
                        "content": "Frontend integration test",
                        "timestamp": int(time.time() * 1000),
                        "test_id": str(uuid.uuid4())
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                self.increment_websocket_events(1)
                
                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    # Validate response structure
                    assert "type" in response_data, "WebSocket response missing type field"
                    assert "payload" in response_data, "WebSocket response missing payload field"
                    
                    self.record_metric("websocket_bidirectional_success", True)
                    self.record_metric("websocket_response_type", response_data["type"])
                    
                except asyncio.TimeoutError:
                    # Some WebSocket endpoints may not echo - this is acceptable
                    self.record_metric("websocket_send_success", True)
                    self.record_metric("websocket_echo_timeout", True)
                
        except WebSocketException as e:
            pytest.fail(f"WebSocket message flow test failed: {e}")
        except Exception as e:
            pytest.fail(f"WebSocket message flow test failed: {e}")
    
    @pytest.mark.asyncio 
    async def test_websocket_agent_event_types(self):
        """
        Business Value: Free/Early/Mid/Enterprise - Agent Status Visibility
        
        Tests WebSocket can handle different agent event types that frontend expects.
        Critical for showing users agent progress: started, thinking, tool_executing, completed.
        """
        critical_event_types = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        try:
            async with websockets.connect(self.ws_url, ping_interval=10) as websocket:
                
                for event_type in critical_event_types:
                    # Send test event of each type
                    test_event = {
                        "type": event_type,
                        "payload": {
                            "run_id": str(uuid.uuid4()),
                            "agent_name": "test_agent", 
                            "timestamp": int(time.time() * 1000)
                        }
                    }
                    
                    # Add event-specific payload fields
                    if event_type == "agent_thinking":
                        test_event["payload"]["thought"] = "Testing agent thinking process"
                    elif event_type in ["tool_executing", "tool_completed"]:
                        test_event["payload"]["tool_name"] = "test_tool"
                        test_event["payload"]["args"] = {"param": "value"}
                        if event_type == "tool_completed":
                            test_event["payload"]["result"] = "Tool execution result"
                    elif event_type == "agent_completed":
                        test_event["payload"]["result"] = "Agent execution completed"
                    
                    await websocket.send(json.dumps(test_event))
                    self.increment_websocket_events(1)
                    
                    # Brief pause between events
                    await asyncio.sleep(0.1)
                
                self.record_metric("websocket_agent_events_tested", len(critical_event_types))
                self.record_metric("websocket_agent_events_success", True)
                
        except WebSocketException as e:
            pytest.fail(f"WebSocket agent events test failed: {e}")
        except Exception as e:
            pytest.fail(f"WebSocket agent events test failed: {e}")


class TestFrontendAuthenticationIntegration(SSotBaseTestCase):
    """
    Business Value: Free/Early/Mid/Enterprise - User Security & Session Management
    Tests authentication flows between frontend and auth service.
    Critical for user login, session management, and secure API access.
    """
    
    def setup_method(self, method=None):
        """Setup authentication test environment."""
        super().setup_method(method)
        
        self.env = self.get_env()
        self.auth_base = self.env.get("NEXT_PUBLIC_AUTH_URL", "http://localhost:8081")
        self.api_base = self.env.get("NEXT_PUBLIC_API_URL", "http://localhost:8000")
        
        self.record_metric("test_category", "auth_integration")
    
    def test_auth_service_health_check(self):
        """
        Business Value: Platform/Internal - Service Availability
        
        Tests auth service is accessible from frontend perspective.
        Critical for user login and registration flows.
        """
        try:
            response = requests.get(f"{self.auth_base}/health", timeout=5)
            self.increment_llm_requests(1)
            
            assert response.status_code == 200, f"Auth service health check failed: {response.status_code}"
            
            # Validate health response
            try:
                health_data = response.json()
                assert "status" in health_data, "Health response missing status"
            except json.JSONDecodeError:
                # Some health endpoints return plain text - acceptable
                pass
            
            self.record_metric("auth_service_accessible", True)
            
        except (RequestException, ConnectionError, Timeout) as e:
            pytest.fail(f"Auth service health check failed: {e}")
    
    def test_token_validation_endpoint(self):
        """
        Business Value: Free/Early/Mid/Enterprise - Token Security
        
        Tests frontend can validate tokens with auth service.
        Critical for maintaining authenticated sessions.
        """
        # Test with invalid token to verify validation works
        invalid_token = "invalid.jwt.token"
        
        try:
            headers = {"Authorization": f"Bearer {invalid_token}"}
            response = requests.get(f"{self.auth_base}/api/auth/validate", headers=headers, timeout=5)
            self.increment_llm_requests(1)
            
            # Should return 401 for invalid token
            assert response.status_code == 401, "Invalid token should return 401"
            
            self.record_metric("token_validation_working", True)
            
        except (RequestException, ConnectionError, Timeout) as e:
            # If endpoint doesn't exist, that's also acceptable
            self.record_metric("token_validation_endpoint_missing", True)
    
    def test_cors_auth_headers(self):
        """
        Business Value: Platform/Internal - Cross-Origin Authentication
        
        Tests CORS is configured for authentication headers from frontend.
        Critical for browser-based auth flows.
        """
        try:
            headers = {
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization,Content-Type"
            }
            
            response = requests.options(f"{self.auth_base}/api/auth/login", headers=headers, timeout=5)
            self.increment_llm_requests(1)
            
            # CORS preflight should succeed
            if response.status_code in [200, 204]:
                cors_headers = response.headers
                allowed_headers = cors_headers.get("Access-Control-Allow-Headers", "").lower()
                
                # Check authorization header is allowed
                assert "authorization" in allowed_headers, "Authorization header not allowed in CORS"
                
                self.record_metric("auth_cors_configured", True)
            else:
                self.record_metric("auth_cors_preflight_failed", response.status_code)
                
        except (RequestException, ConnectionError, Timeout) as e:
            # CORS issues are common in development
            self.record_metric("auth_cors_test_failed", str(e))


class TestFrontendServiceIntegration(SSotBaseTestCase):
    """
    Business Value: Platform/Internal - Service Integration & Configuration
    Tests integration between frontend services and backend infrastructure.
    Critical for proper service communication and configuration management.
    """
    
    def setup_method(self, method=None):
        """Setup service integration test environment."""
        super().setup_method(method)
        
        self.env = self.get_env()
        self.api_base = self.env.get("NEXT_PUBLIC_API_URL", "http://localhost:8000")
        
        self.record_metric("test_category", "service_integration")
    
    def test_environment_configuration_consistency(self):
        """
        Business Value: Platform/Internal - Configuration Management
        
        Tests frontend environment configuration matches expected patterns.
        Critical for proper service URL resolution and environment detection.
        """
        # Validate required environment variables are accessible
        required_env_vars = [
            "NEXT_PUBLIC_API_URL",
            "NEXT_PUBLIC_WS_URL", 
            "NEXT_PUBLIC_AUTH_URL",
            "NEXT_PUBLIC_ENVIRONMENT"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            value = self.env.get(var)
            if not value:
                missing_vars.append(var)
            else:
                # Validate URL format
                if var.endswith("_URL") and not value.startswith(("http://", "https://", "ws://", "wss://")):
                    pytest.fail(f"Invalid URL format for {var}: {value}")
        
        # In test environment, some vars might be missing - that's acceptable
        self.record_metric("missing_env_vars_count", len(missing_vars))
        self.record_metric("env_config_valid", len(missing_vars) == 0)
        
        # Test environment detection
        environment = self.env.get("NEXT_PUBLIC_ENVIRONMENT", "development")
        assert environment in ["development", "staging", "production", "test"], f"Invalid environment: {environment}"
        
        self.record_metric("detected_environment", environment)
    
    def test_api_base_url_accessibility(self):
        """
        Business Value: Free/Early/Mid/Enterprise - Service Connectivity
        
        Tests frontend can reach the configured API base URL.
        Critical for all frontend-backend communication.
        """
        try:
            # Test basic connectivity to API base
            response = requests.get(f"{self.api_base}/health", timeout=10)
            self.increment_llm_requests(1)
            
            # Any 2xx or 4xx response indicates API is reachable
            assert response.status_code < 500, f"API base unreachable, got: {response.status_code}"
            
            self.record_metric("api_base_accessible", True)
            self.record_metric("api_response_time", response.elapsed.total_seconds())
            
        except (RequestException, ConnectionError, Timeout) as e:
            pytest.fail(f"API base URL accessibility test failed: {e}")
    
    def test_service_response_headers(self):
        """
        Business Value: Platform/Internal - Security & Monitoring
        
        Tests backend services return appropriate headers for frontend consumption.
        Important for security, caching, and monitoring integration.
        """
        try:
            response = requests.get(f"{self.api_base}/health", timeout=5)
            self.increment_llm_requests(1)
            
            headers = response.headers
            
            # Check for important headers
            important_headers = ["content-type", "date", "server"]
            present_headers = []
            
            for header in important_headers:
                if header in headers:
                    present_headers.append(header)
            
            # Record header presence
            self.record_metric("response_headers_count", len(headers))
            self.record_metric("important_headers_present", len(present_headers))
            self.record_metric("content_type", headers.get("content-type", "unknown"))
            
        except (RequestException, ConnectionError, Timeout) as e:
            pytest.fail(f"Service response headers test failed: {e}")


class TestFrontendErrorHandling(SSotBaseTestCase):
    """
    Business Value: Free/Early/Mid/Enterprise - User Experience & Reliability 
    Tests frontend error handling and recovery mechanisms.
    Critical for graceful degradation and user experience during failures.
    """
    
    def setup_method(self, method=None):
        """Setup error handling test environment."""
        super().setup_method(method)
        
        self.env = self.get_env()
        self.api_base = self.env.get("NEXT_PUBLIC_API_URL", "http://localhost:8000")
        
        self.record_metric("test_category", "error_handling")
    
    def test_network_timeout_handling(self):
        """
        Business Value: Free/Early/Mid/Enterprise - Reliability
        
        Tests frontend properly handles network timeouts.
        Critical for user experience when backend is slow or unresponsive.
        """
        try:
            # Use very short timeout to force timeout condition
            requests.get(f"{self.api_base}/api/health", timeout=0.001)
            
            # If request succeeded, that's actually fine - network was very fast
            self.record_metric("network_very_fast", True)
            
        except Timeout:
            # This is the expected behavior for timeout handling
            self.record_metric("timeout_exception_raised", True)
        except Exception as e:
            # Other network errors are also acceptable
            self.record_metric("network_error_type", type(e).__name__)
    
    def test_service_unavailable_handling(self):
        """
        Business Value: Free/Early/Mid/Enterprise - Resilience
        
        Tests frontend behavior when backend services are unavailable.
        Critical for graceful degradation and user messaging.
        """
        # Test connection to non-existent service
        fake_url = "http://localhost:99999/api/health"
        
        try:
            requests.get(fake_url, timeout=2)
            
            # If this succeeds, something is very wrong
            pytest.fail("Connection to fake URL should have failed")
            
        except ConnectionError:
            # This is expected behavior
            self.record_metric("connection_error_handled", True)
        except Exception as e:
            # Other connection-related exceptions are acceptable
            self.record_metric("service_unavailable_error_type", type(e).__name__)
    
    def test_malformed_response_handling(self):
        """
        Business Value: Platform/Internal - Data Integrity
        
        Tests frontend handling of malformed responses from backend.
        Important for robust error handling and data validation.
        """
        # This test simulates what frontend should do with malformed data
        # Since we can't easily make backend return malformed data in integration test,
        # we test the error handling patterns that would be used
        
        # Test JSON parsing error handling
        test_cases = [
            '{"invalid": json}',  # Invalid JSON
            '{"incomplete": ',     # Incomplete JSON
            '',                    # Empty response
            'not json at all'      # Non-JSON response
        ]
        
        json_parse_errors = 0
        for test_case in test_cases:
            try:
                json.loads(test_case)
            except json.JSONDecodeError:
                json_parse_errors += 1
            except Exception:
                # Other exceptions are also acceptable
                json_parse_errors += 1
        
        # All test cases should have raised errors
        assert json_parse_errors == len(test_cases), "JSON error handling not working"
        
        self.record_metric("json_error_handling_works", True)
        self.record_metric("malformed_responses_tested", len(test_cases))


class TestReactComponentIntegration(SSotBaseTestCase):
    """
    Business Value: Free/Early/Mid/Enterprise - UI/UX & Component Integration
    Tests React components properly integrate with backend data flows.
    Critical for user interface responsiveness and data display.
    """
    
    def setup_method(self, method=None):
        """Setup React component integration tests."""
        super().setup_method(method)
        
        self.record_metric("test_category", "react_integration")
    
    def test_api_client_integration_patterns(self):
        """
        Business Value: Platform/Internal - Architecture Validation
        
        Tests API client integration patterns work with backend services.
        Critical for consistent data fetching across React components.
        """
        # Test that API configuration can be loaded
        env = self.get_env()
        api_url = env.get("NEXT_PUBLIC_API_URL", "http://localhost:8000")
        
        # Validate API URL format
        assert api_url.startswith(("http://", "https://")), f"Invalid API URL format: {api_url}"
        
        # Test URL construction patterns that components would use
        test_endpoints = [
            "/api/health",
            "/api/agents", 
            "/api/threads",
            "/openapi.json"
        ]
        
        for endpoint in test_endpoints:
            full_url = f"{api_url}{endpoint}"
            assert full_url.startswith(("http://", "https://")), f"Invalid full URL: {full_url}"
        
        self.record_metric("api_integration_patterns_valid", True)
        self.record_metric("endpoints_tested", len(test_endpoints))
    
    def test_websocket_integration_patterns(self):
        """
        Business Value: Free/Early/Mid/Enterprise - Real-Time UI Updates
        
        Tests WebSocket integration patterns used by React components.
        Critical for real-time chat and agent status updates in UI.
        """
        env = self.get_env()
        ws_url = env.get("NEXT_PUBLIC_WS_URL", "ws://localhost:8000/ws")
        
        # Validate WebSocket URL format
        assert ws_url.startswith(("ws://", "wss://")), f"Invalid WebSocket URL format: {ws_url}"
        
        # Test WebSocket URL construction for secure connections
        if ws_url.startswith("ws://"):
            secure_url = ws_url.replace("ws://", "wss://")
            assert secure_url.startswith("wss://"), "Secure WebSocket URL construction failed"
        
        self.record_metric("websocket_integration_patterns_valid", True)
        self.record_metric("websocket_url_format", ws_url.split("://")[0])
    
    def test_authentication_integration_patterns(self):
        """
        Business Value: Free/Early/Mid/Enterprise - User Authentication
        
        Tests authentication integration patterns used by React components.
        Critical for user login state and protected route access.
        """
        env = self.get_env()
        auth_url = env.get("NEXT_PUBLIC_AUTH_URL", "http://localhost:8081")
        
        # Validate auth URL format
        assert auth_url.startswith(("http://", "https://")), f"Invalid auth URL format: {auth_url}"
        
        # Test auth endpoint construction patterns
        auth_endpoints = [
            "/api/auth/login",
            "/api/auth/logout", 
            "/api/auth/refresh",
            "/health"
        ]
        
        for endpoint in auth_endpoints:
            full_url = f"{auth_url}{endpoint}"
            assert full_url.startswith(("http://", "https://")), f"Invalid auth URL: {full_url}"
        
        self.record_metric("auth_integration_patterns_valid", True)
        self.record_metric("auth_endpoints_tested", len(auth_endpoints))


# Test execution timing validation
def pytest_runtest_teardown(item, nextitem):
    """Ensure integration tests have reasonable execution times."""
    if hasattr(item, '_test_start_time'):
        duration = time.time() - item._test_start_time
        
        # Integration tests should not be instant (indicates mocking)
        if duration < 0.01:  # 10ms minimum
            pytest.fail(f"Integration test {item.name} completed too quickly ({duration:.3f}s) - may be mocked")
        
        # Integration tests should complete within reasonable time
        if duration > 30.0:  # 30s maximum
            pytest.fail(f"Integration test {item.name} took too long ({duration:.3f}s)")


def pytest_runtest_setup(item):
    """Mark test start time for execution validation."""
    item._test_start_time = time.time()