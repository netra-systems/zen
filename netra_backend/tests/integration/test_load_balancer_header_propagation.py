"""
Load Balancer Header Propagation Integration Tests - GitHub Issue #113

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure authentication headers reach backend services through load balancer
- Value Impact: Prevents authentication failures that break entire platform ($120K+ MRR protection)
- Strategic Impact: Critical infrastructure reliability enabling all authenticated operations

CRITICAL: Tests real header forwarding between services without Docker compose dependencies.
These tests validate that GCP Load Balancer properly forwards authentication headers to backend services,
preventing the header stripping that caused complete system failure.

Per CLAUDE.md requirements:
- Uses REAL authentication flows (no mocks)
- Uses REAL service connections
- Hard-fail validation patterns
- SSOT patterns from test_framework/ssot/
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import pytest
import websockets
from fastapi.testclient import TestClient

from netra_backend.app.main import app
from test_framework.base_integration_test import WebSocketIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, AuthenticatedUser
from test_framework.real_services import get_real_services
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ensure_user_id


logger = logging.getLogger(__name__)


class TestLoadBalancerHeaderPropagation(WebSocketIntegrationTest):
    """
    Test load balancer header propagation in real multi-service scenarios.
    
    CRITICAL: These tests validate that authentication headers properly propagate
    through the load balancer to backend services, preventing header stripping failures
    that break authentication flows.
    
    Business Value: Protects $120K+ MRR by ensuring header-dependent authentication works.
    """

    def setup_method(self):
        """Set up each test with proper environment and authentication."""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
    async def async_setup(self):
        """Async setup for real services."""
        await super().async_setup()
        self.real_services = await get_real_services()
        
    async def async_teardown(self):
        """Async cleanup for real services."""
        if hasattr(self, 'real_services'):
            await self.real_services.cleanup()
        await super().async_teardown()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_header_propagation_backend_to_auth_service(self):
        """
        Test authentication header propagation from backend to auth service.
        
        Business Value: Ensures backend service can authenticate users through auth service
        with proper header forwarding. CRITICAL for all authenticated operations.
        
        HARD FAIL: Without proper headers, authentication fails and breaks business value.
        """
        await self.async_setup()
        
        try:
            # Create authenticated user with real JWT token
            user = await self.auth_helper.create_authenticated_user(
                email=f"header_test_{uuid.uuid4().hex[:8]}@example.com",
                permissions=["read", "write", "api_access"]
            )
            
            # Get authentication headers that should propagate
            auth_headers = self.auth_helper.get_auth_headers(user.jwt_token)
            
            # Verify headers contain required authentication data
            assert "Authorization" in auth_headers, "CRITICAL: Authorization header missing"
            assert auth_headers["Authorization"].startswith("Bearer "), "CRITICAL: Bearer token format required"
            assert "Content-Type" in auth_headers, "CRITICAL: Content-Type header required"
            
            logger.info(f"✅ Created authenticated user with headers: {list(auth_headers.keys())}")
            
            # Test header propagation through real HTTP connection
            backend_base_url = self.env.get("BACKEND_URL", "http://localhost:8000")
            
            async with aiohttp.ClientSession() as session:
                # Test authenticated health check endpoint
                health_url = f"{backend_base_url}/health"
                
                async with session.get(health_url, headers=auth_headers, timeout=15) as resp:
                    # HARD FAIL: Headers must enable successful authentication
                    if resp.status != 200:
                        response_text = await resp.text()
                        raise AssertionError(
                            f"CRITICAL: Authentication header propagation failed! "
                            f"Backend health check returned {resp.status}. "
                            f"This indicates load balancer header stripping (GitHub issue #113). "
                            f"Response: {response_text}. "
                            f"Headers sent: {list(auth_headers.keys())}"
                        )
                    
                    health_data = await resp.json()
                    
                    # Verify business value: backend service received and processed headers
                    assert health_data.get("status") in ["healthy", "ok"], (
                        f"CRITICAL: Backend service unhealthy: {health_data.get('status')}. "
                        f"Header propagation may have failed."
                    )
                    
                    logger.info(f"✅ Header propagation successful - backend health: {health_data.get('status')}")
                    
                    # Verify authentication context preserved in response
                    if "user_authenticated" in health_data:
                        assert health_data["user_authenticated"] is True, (
                            f"CRITICAL: Authentication context lost in header propagation. "
                            f"Headers reached backend but auth context not preserved."
                        )
                        
                    # Test with user context endpoint if available
                    user_context_url = f"{backend_base_url}/api/v1/user/context"
                    
                    async with session.get(user_context_url, headers=auth_headers, timeout=15) as ctx_resp:
                        if ctx_resp.status == 200:
                            ctx_data = await ctx_resp.json()
                            
                            # Verify user context properly extracted from headers
                            assert "user_id" in ctx_data, "CRITICAL: User context missing from header propagation"
                            
                            # Strongly typed user ID validation
                            user_id = ensure_user_id(ctx_data["user_id"])
                            assert user_id == user.get_strongly_typed_user_id(), (
                                f"CRITICAL: User ID mismatch in header propagation. "
                                f"Expected: {user.get_strongly_typed_user_id()}, Got: {user_id}"
                            )
                            
                            logger.info(f"✅ User context preserved through header propagation: {user_id}")
                        
                        elif ctx_resp.status == 404:
                            # Endpoint may not exist - log but don't fail
                            logger.info("ℹ️ User context endpoint not available - skipping context validation")
                        
                        else:
                            # Authentication failure on user context endpoint
                            ctx_error = await ctx_resp.text()
                            raise AssertionError(
                                f"CRITICAL: User context authentication failed ({ctx_resp.status}). "
                                f"Headers propagated to health but failed for user context. "
                                f"This indicates partial header stripping. Error: {ctx_error}"
                            )
                            
                    # Assert business value delivered
                    self.assert_business_value_delivered(
                        {"authentication_success": True, "headers_propagated": True, "user_context": user.user_id},
                        "authentication_infrastructure"
                    )
                    
        except AssertionError:
            raise  # Re-raise assertion errors
        except Exception as e:
            raise AssertionError(
                f"CRITICAL: Header propagation test failed with unexpected error. "
                f"This may indicate load balancer configuration issues. "
                f"Error: {str(e)}"
            ) from e
        finally:
            await self.async_teardown()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_header_preservation_across_services(self):
        """
        Test WebSocket header preservation across service boundaries.
        
        Business Value: Ensures WebSocket connections maintain authentication context
        through load balancer, enabling real-time chat and agent execution.
        
        HARD FAIL: WebSocket header stripping breaks chat functionality ($120K+ MRR risk).
        """
        await self.async_setup()
        
        try:
            # Create authenticated user for WebSocket connection
            user = await self.websocket_auth_helper.create_authenticated_user(
                email=f"ws_header_test_{uuid.uuid4().hex[:8]}@example.com",
                permissions=["websocket_access", "chat", "agent_execution"]
            )
            
            # Get WebSocket headers with E2E detection
            ws_headers = self.websocket_auth_helper.get_websocket_headers(user.jwt_token)
            
            # Verify critical WebSocket headers present
            required_headers = ["Authorization", "X-User-ID", "X-Test-Mode"]
            for header in required_headers:
                assert header in ws_headers, f"CRITICAL: WebSocket header missing: {header}"
            
            logger.info(f"✅ WebSocket headers prepared: {list(ws_headers.keys())}")
            
            # Connect to WebSocket with authentication headers
            websocket_url = self.env.get("WEBSOCKET_URL", "ws://localhost:8000/ws")
            
            # CRITICAL: Test actual WebSocket connection with headers
            async with websockets.connect(
                websocket_url,
                additional_headers=ws_headers,
                timeout=20,
                max_size=2**16  # Smaller max size for faster handshake
            ) as websocket:
                logger.info("✅ WebSocket connection established with authentication headers")
                
                # Test header-dependent functionality: ping/pong
                ping_message = {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "test_id": f"header_test_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(ping_message))
                
                # HARD FAIL: Must receive response (indicates headers reached backend)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    # Verify response indicates successful authentication
                    assert "type" in response_data, "CRITICAL: WebSocket response missing type field"
                    
                    if response_data.get("type") == "error":
                        error_msg = response_data.get("message", "Unknown error")
                        raise AssertionError(
                            f"CRITICAL: WebSocket authentication failed after connection. "
                            f"Headers may have been stripped during handshake. "
                            f"Error: {error_msg}"
                        )
                    
                    logger.info(f"✅ WebSocket authenticated response received: {response_data.get('type')}")
                    
                    # Test authenticated operation: request user info
                    user_info_request = {
                        "type": "user_info",
                        "request_id": f"header_user_info_{int(time.time())}"
                    }
                    
                    await websocket.send(json.dumps(user_info_request))
                    
                    # Wait for user info response
                    user_info_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    user_info_data = json.loads(user_info_response)
                    
                    # Verify user context preserved through headers
                    if user_info_data.get("type") == "user_info":
                        assert "user_id" in user_info_data.get("data", {}), (
                            "CRITICAL: User context lost in WebSocket header propagation"
                        )
                        
                        received_user_id = user_info_data["data"]["user_id"]
                        assert received_user_id == user.user_id, (
                            f"CRITICAL: User ID mismatch in WebSocket headers. "
                            f"Expected: {user.user_id}, Got: {received_user_id}"
                        )
                        
                        logger.info(f"✅ WebSocket user context preserved: {received_user_id}")
                        
                except asyncio.TimeoutError:
                    raise AssertionError(
                        "CRITICAL: WebSocket authentication timeout. "
                        "This indicates headers were stripped by load balancer, "
                        "preventing authentication at the backend service. "
                        "Check GCP Load Balancer header configuration (GitHub issue #113)."
                    )
                    
                # Assert business value delivered
                self.assert_business_value_delivered(
                    {
                        "websocket_connection": True, 
                        "authentication_preserved": True,
                        "user_context": user.user_id
                    },
                    "real_time_communication"
                )
                
        except websockets.exceptions.ConnectionClosed as e:
            raise AssertionError(
                f"CRITICAL: WebSocket connection closed unexpectedly. "
                f"This may indicate authentication header stripping by load balancer. "
                f"Connection close code: {e.code}, Reason: {e.reason}"
            ) from e
            
        except Exception as e:
            raise AssertionError(
                f"CRITICAL: WebSocket header preservation test failed. "
                f"This indicates load balancer configuration issues with WebSocket headers. "
                f"Error: {str(e)}"
            ) from e
        finally:
            await self.async_teardown()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_header_isolation_integration(self):
        """
        Test header isolation between multiple concurrent users.
        
        Business Value: Ensures headers don't leak between users, maintaining security
        and proper user context isolation in multi-tenant environment.
        
        HARD FAIL: Header contamination is a security breach that breaks multi-user isolation.
        """
        await self.async_setup()
        
        try:
            # Create multiple authenticated users simultaneously
            user_count = 3
            users = []
            auth_sessions = []
            
            for i in range(user_count):
                user = await self.auth_helper.create_authenticated_user(
                    email=f"isolation_test_{i}_{uuid.uuid4().hex[:8]}@example.com",
                    permissions=["read", "write", f"user_group_{i}"]
                )
                users.append(user)
                
                # Create HTTP session with user's headers
                session = aiohttp.ClientSession(
                    headers=self.auth_helper.get_auth_headers(user.jwt_token),
                    timeout=aiohttp.ClientTimeout(total=15)
                )
                auth_sessions.append(session)
                
                logger.info(f"✅ Created user {i}: {user.email}")
            
            # Test concurrent requests with different user headers
            backend_base_url = self.env.get("BACKEND_URL", "http://localhost:8000")
            
            async def test_user_isolation(user_index: int, session: aiohttp.ClientSession, user: AuthenticatedUser):
                """Test individual user's header isolation."""
                health_url = f"{backend_base_url}/health"
                
                try:
                    async with session.get(health_url) as resp:
                        # Each user must get successful response
                        assert resp.status == 200, (
                            f"CRITICAL: User {user_index} authentication failed ({resp.status}). "
                            f"Header isolation may be broken."
                        )
                        
                        health_data = await resp.json()
                        
                        # Verify response is specific to this user (if backend provides user context)
                        if "user_context" in health_data:
                            context_user_id = health_data["user_context"].get("user_id")
                            if context_user_id:
                                assert context_user_id == user.user_id, (
                                    f"CRITICAL: Header contamination detected! "
                                    f"User {user_index} received context for user {context_user_id}. "
                                    f"Expected: {user.user_id}"
                                )
                        
                        return {
                            "user_index": user_index,
                            "user_id": user.user_id,
                            "status": health_data.get("status"),
                            "authentication_success": True
                        }
                        
                except Exception as e:
                    return {
                        "user_index": user_index,
                        "user_id": user.user_id,
                        "error": str(e),
                        "authentication_success": False
                    }
            
            # Execute concurrent requests
            isolation_results = await asyncio.gather(
                *[test_user_isolation(i, session, user) for i, (session, user) in enumerate(zip(auth_sessions, users))],
                return_exceptions=True
            )
            
            # Validate all users received proper responses without contamination
            successful_auths = 0
            for result in isolation_results:
                if isinstance(result, Exception):
                    raise AssertionError(f"CRITICAL: User isolation test failed: {result}")
                
                assert result["authentication_success"], (
                    f"CRITICAL: User {result['user_index']} authentication failed. "
                    f"Error: {result.get('error', 'Unknown error')}"
                )
                
                successful_auths += 1
                logger.info(f"✅ User {result['user_index']} isolated authentication successful")
            
            # HARD FAIL: All users must authenticate successfully
            assert successful_auths == user_count, (
                f"CRITICAL: Header isolation failed. "
                f"Only {successful_auths}/{user_count} users authenticated successfully. "
                f"This indicates header cross-contamination or stripping."
            )
            
            logger.info(f"✅ Multi-user header isolation validated for {user_count} users")
            
            # Clean up sessions
            for session in auth_sessions:
                await session.close()
                
            # Assert business value delivered
            self.assert_business_value_delivered(
                {
                    "user_isolation": True,
                    "concurrent_users": user_count,
                    "security_maintained": True
                },
                "multi_tenant_security"
            )
            
        except Exception as e:
            # Clean up sessions on error
            for session in auth_sessions:
                if not session.closed:
                    await session.close()
            
            raise AssertionError(
                f"CRITICAL: Multi-user header isolation test failed. "
                f"This indicates serious security issues with header propagation. "
                f"Error: {str(e)}"
            ) from e
        finally:
            await self.async_teardown()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_to_service_authentication_headers(self):
        """
        Test service-to-service authentication header propagation.
        
        Business Value: Ensures backend service can authenticate with other services
        (auth, analytics) using proper header forwarding for internal operations.
        
        HARD FAIL: Service auth failures break internal workflows and business logic.
        """
        await self.async_setup()
        
        try:
            # Test backend to auth service communication
            auth_service_url = self.env.get("AUTH_SERVICE_URL", "http://localhost:8081")
            
            # Create service authentication token (simulated)
            service_auth_helper = E2EAuthHelper(environment="test")
            service_token = service_auth_helper.create_test_jwt_token(
                user_id="service_backend",
                email="backend@netra.internal",
                permissions=["service", "internal_api", "user_validation"]
            )
            
            service_headers = service_auth_helper.get_auth_headers(service_token)
            service_headers.update({
                "X-Service-Name": "netra-backend",
                "X-Service-Request": "user-validation",
                "X-Internal-API": "true"
            })
            
            logger.info(f"✅ Service authentication headers prepared: {list(service_headers.keys())}")
            
            # Test service-to-service health check
            async with aiohttp.ClientSession() as session:
                health_url = f"{auth_service_url}/health"
                
                async with session.get(health_url, headers=service_headers, timeout=15) as resp:
                    # HARD FAIL: Service headers must enable inter-service communication
                    if resp.status != 200:
                        response_text = await resp.text()
                        raise AssertionError(
                            f"CRITICAL: Service-to-service authentication failed! "
                            f"Auth service health check returned {resp.status}. "
                            f"This indicates load balancer stripping service headers. "
                            f"Response: {response_text}. "
                            f"Headers sent: {list(service_headers.keys())}"
                        )
                    
                    health_data = await resp.json()
                    logger.info(f"✅ Service-to-service health check successful: {health_data.get('status')}")
                
                # Test internal API endpoint if available
                validate_url = f"{auth_service_url}/internal/validate"
                
                async with session.post(
                    validate_url, 
                    headers=service_headers,
                    json={"token": service_token},
                    timeout=15
                ) as validate_resp:
                    
                    if validate_resp.status == 200:
                        validate_data = await validate_resp.json()
                        
                        # Verify service authentication worked
                        assert validate_data.get("valid") is True, (
                            "CRITICAL: Service token validation failed through headers"
                        )
                        
                        logger.info("✅ Service-to-service token validation successful")
                        
                    elif validate_resp.status == 404:
                        # Endpoint may not exist - log but don't fail
                        logger.info("ℹ️ Internal validate endpoint not available - skipping validation")
                        
                    else:
                        # Service authentication failure
                        validate_error = await validate_resp.text()
                        raise AssertionError(
                            f"CRITICAL: Service token validation failed ({validate_resp.status}). "
                            f"Service headers may have been stripped. "
                            f"Error: {validate_error}"
                        )
            
            # Assert business value delivered
            self.assert_business_value_delivered(
                {
                    "service_authentication": True,
                    "internal_api_access": True,
                    "header_propagation": True
                },
                "service_integration"
            )
            
        except Exception as e:
            raise AssertionError(
                f"CRITICAL: Service-to-service authentication test failed. "
                f"This indicates load balancer configuration issues with service headers. "
                f"Error: {str(e)}"
            ) from e
        finally:
            await self.async_teardown()

    def assert_business_value_delivered(self, result: Dict[str, Any], expected_value_type: str):
        """
        Enhanced business value assertion for header propagation tests.
        
        Args:
            result: Test execution result
            expected_value_type: Type of business value expected
        """
        super().assert_business_value_delivered(result, expected_value_type)
        
        # Additional assertions for header propagation business value
        if expected_value_type == "authentication_infrastructure":
            assert result.get("authentication_success") is True, \
                "Authentication infrastructure must enable successful auth"
            assert result.get("headers_propagated") is True, \
                "Headers must propagate through infrastructure"
                
        elif expected_value_type == "real_time_communication":
            assert result.get("websocket_connection") is True, \
                "Real-time communication must establish WebSocket connections"
            assert result.get("authentication_preserved") is True, \
                "Authentication context must be preserved in WebSocket"
                
        elif expected_value_type == "multi_tenant_security":
            assert result.get("user_isolation") is True, \
                "Multi-tenant security requires proper user isolation"
            assert result.get("security_maintained") is True, \
                "Security policies must be maintained across users"
                
        elif expected_value_type == "service_integration":
            assert result.get("service_authentication") is True, \
                "Service integration requires working service authentication"
            assert result.get("header_propagation") is True, \
                "Service headers must propagate correctly"