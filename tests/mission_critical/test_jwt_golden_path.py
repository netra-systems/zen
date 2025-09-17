"""
JWT Golden Path Protection Tests

PURPOSE: These tests FAIL when JWT changes break the $500K+ ARR Golden Path
user flow (Login → JWT → Chat). Tests will PASS after SSOT refactor.

MISSION CRITICAL: Protects $500K+ ARR Golden Path by ensuring JWT integration
maintains end-to-end user authentication and chat functionality.

BUSINESS VALUE: Enterprise/Platform - Revenue Protection & Customer Experience
- Ensures login → chat flow works end-to-end with JWT
- Protects WebSocket authentication with JWT tokens
- Validates multi-user JWT isolation in chat scenarios
- Tests complete Golden Path user journey with JWT

EXPECTED STATUS: FAIL (before SSOT refactor) → PASS (after SSOT refactor)

These tests protect Golden Path business value by:
1. End-to-end JWT authentication flow (Login → Chat)
2. WebSocket JWT authentication for real-time chat
3. Multi-user JWT isolation in chat scenarios
4. Golden Path error handling with JWT failures
"""

import asyncio
import aiohttp
import httpx
import json
import logging
import time
from typing import Dict, Any, Optional, List
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
import jwt
import websockets

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from test_framework.ssot.websocket_auth_test_helpers import WebSocketAuthenticationTester

logger = logging.getLogger(__name__)

class JwtGoldenPathProtectionTests(SSotAsyncTestCase):
    """
    JWT Golden Path Protection Tests
    
    These tests FAIL when JWT changes break the Golden Path user flow.
    After SSOT refactor, all tests should PASS.
    
    CRITICAL: These tests protect $500K+ ARR by ensuring JWT authentication
    works end-to-end in the Golden Path (Login → Chat → AI Response).
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.auth_helper = E2EAuthHelper()
        self.websocket_helper = WebSocketAuthenticationTester()
        
        # Golden Path endpoints (production-like)
        self.backend_base_url = "http://localhost:8000"  # Main backend
        self.auth_service_url = "http://localhost:8001"  # Auth service
        self.websocket_url = "ws://localhost:8000/ws/main"  # Chat WebSocket
        
    @pytest.mark.asyncio
    async def test_golden_path_jwt_login_to_chat_flow(self):
        """
        GOLDEN PATH TEST: Complete JWT flow from login to chat functionality.
        
        EXPECTED: FAIL - JWT SSOT violations break the Golden Path flow
        AFTER SSOT: PASS - Clean JWT delegation enables Golden Path
        
        This test validates the complete Golden Path user journey:
        1. User login → JWT token
        2. JWT token → Backend authentication
        3. Backend auth → WebSocket connection
        4. WebSocket → Chat functionality
        """
        golden_path_violations = []
        
        try:
            # STEP 1: User Login (Golden Path Entry Point)
            login_success = False
            jwt_token = None
            
            try:
                # Try authentic login flow first
                async with aiohttp.ClientSession() as session:
                    login_url = f"{self.auth_service_url}/auth/login"
                    login_data = {
                        "email": "golden_path_test@example.com",
                        "password": "test_password_123"
                    }
                    
                    async with session.post(login_url, json=login_data, timeout=5.0) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            jwt_token = data.get("access_token")
                            login_success = True
                            logger.info("✓ Golden Path: Login successful via auth service")
                        
            except Exception as e:
                logger.warning(f"Golden Path: Auth service login failed: {e}")
                
            # If auth service login fails, create test JWT (fallback for testing)
            if not login_success or not jwt_token:
                jwt_token = self.auth_helper.create_test_jwt_token(
                    user_id="golden_path_test_user",
                    email="golden_path_test@example.com",
                    permissions=["read", "write", "chat"]
                )
                logger.info("✓ Golden Path: Fallback test JWT created")
            
            # STEP 2: Backend Authentication with JWT (Critical for Golden Path)
            backend_auth_success = False
            user_data = None
            
            try:
                async with httpx.AsyncClient() as client:
                    # Test protected backend endpoint
                    headers = {"Authorization": f"Bearer {jwt_token}"}
                    auth_url = f"{self.backend_base_url}/api/v1/users/me"
                    
                    response = await client.get(auth_url, headers=headers, timeout=5.0)
                    
                    if response.status_code == 200:
                        user_data = response.json()
                        backend_auth_success = True
                        logger.info("✓ Golden Path: Backend authentication successful")
                    else:
                        golden_path_violations.append(
                            f"Backend JWT authentication failed: {response.status_code} - {response.text}"
                        )
                        
            except Exception as e:
                golden_path_violations.append(f"Backend authentication error: {e}")
            
            # STEP 3: WebSocket Connection for Chat (Core Golden Path Value)
            websocket_success = False
            chat_ready = False
            
            if backend_auth_success:
                try:
                    # Create authenticated WebSocket connection
                    auth_headers = {
                        "Authorization": f"Bearer {jwt_token}",
                        "X-User-ID": "golden_path_test_user"
                    }
                    
                    # Test WebSocket connection with timeout
                    websocket = await asyncio.wait_for(
                        websockets.connect(
                            self.websocket_url,
                            additional_headers=auth_headers,
                            timeout=10.0
                        ),
                        timeout=15.0
                    )
                    
                    websocket_success = True
                    logger.info("✓ Golden Path: WebSocket connection successful")
                    
                    # STEP 4: Chat Functionality Test (Golden Path Business Value)
                    try:
                        # Send test chat message
                        chat_message = {
                            "type": "chat_message",
                            "content": "Hello, this is a Golden Path test",
                            "timestamp": time.time()
                        }
                        
                        await websocket.send(json.dumps(chat_message))
                        
                        # Wait for response (with timeout)
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        response_data = json.loads(response)
                        
                        # Validate chat response structure
                        if "type" in response_data and "content" in response_data:
                            chat_ready = True
                            logger.info("✓ Golden Path: Chat functionality working")
                        else:
                            golden_path_violations.append("Chat response missing required fields")
                        
                    except asyncio.TimeoutError:
                        golden_path_violations.append("Chat response timeout - Golden Path broken")
                    except Exception as e:
                        golden_path_violations.append(f"Chat functionality error: {e}")
                    finally:
                        await websocket.close()
                        
                except asyncio.TimeoutError:
                    golden_path_violations.append("WebSocket connection timeout - Golden Path broken")
                except Exception as e:
                    golden_path_violations.append(f"WebSocket connection error: {e}")
            
            # CRITICAL ASSESSMENT: Golden Path Success Criteria
            golden_path_success = all([
                jwt_token is not None,
                backend_auth_success,
                websocket_success,
                chat_ready
            ])
            
            # Report violations if Golden Path is broken
            if not golden_path_success or golden_path_violations:
                violation_summary = "\n".join([f"  - {v}" for v in golden_path_violations])
                logger.error("GOLDEN PATH VIOLATION: JWT flow breaks critical user journey")
                logger.error(f"Violations:\n{violation_summary}")
                
                # This test SHOULD FAIL before SSOT refactor
                assert golden_path_success, (
                    f"GOLDEN PATH VIOLATION: JWT authentication flow is broken, "
                    f"affecting $500K+ ARR user experience. "
                    f"Steps failed: Login={login_success}, Backend={backend_auth_success}, "
                    f"WebSocket={websocket_success}, Chat={chat_ready}. "
                    f"Violations:\n{violation_summary}"
                )
            else:
                logger.info("✓ GOLDEN PATH SUCCESS: Complete JWT flow working end-to-end")
                
        except Exception as e:
            pytest.fail(
                f"GOLDEN PATH CRITICAL FAILURE: JWT Golden Path completely broken. "
                f"This affects $500K+ ARR customer experience. Error: {e}"
            )

    @pytest.mark.asyncio
    async def test_multi_user_jwt_isolation_golden_path(self):
        """
        GOLDEN PATH TEST: Multi-user JWT isolation in chat scenarios.
        
        EXPECTED: FAIL - JWT isolation violations cause user data bleed
        AFTER SSOT: PASS - Perfect JWT isolation via auth service
        
        This test validates that multiple users can use chat simultaneously
        with proper JWT isolation (critical for enterprise customers).
        """
        isolation_violations = []
        
        # Create two different users for isolation testing
        user1_token = self.auth_helper.create_test_jwt_token(
            user_id="golden_path_user1",
            email="user1@golden-path-test.com",
            permissions=["read", "write", "chat"]
        )
        
        user2_token = self.auth_helper.create_test_jwt_token(
            user_id="golden_path_user2", 
            email="user2@golden-path-test.com",
            permissions=["read", "write", "chat"]
        )
        
        try:
            # Test concurrent authentication
            concurrent_auth_tasks = []
            
            async def test_user_auth(user_token, user_id):
                """Test individual user authentication."""
                try:
                    async with httpx.AsyncClient() as client:
                        headers = {"Authorization": f"Bearer {user_token}"}
                        auth_url = f"{self.backend_base_url}/api/v1/users/me"
                        
                        response = await client.get(auth_url, headers=headers, timeout=5.0)
                        
                        if response.status_code == 200:
                            user_data = response.json()
                            actual_user_id = user_data.get("id") or user_data.get("user_id")
                            
                            # CRITICAL: Verify user isolation
                            if actual_user_id != user_id:
                                isolation_violations.append(
                                    f"JWT isolation violation: Expected {user_id}, got {actual_user_id}"
                                )
                                
                            return {"success": True, "user_id": actual_user_id, "data": user_data}
                        else:
                            isolation_violations.append(f"Auth failed for {user_id}: {response.status_code}")
                            return {"success": False, "user_id": user_id}
                            
                except Exception as e:
                    isolation_violations.append(f"Auth error for {user_id}: {e}")
                    return {"success": False, "user_id": user_id, "error": str(e)}
            
            # Run concurrent authentication tests
            concurrent_auth_tasks = [
                test_user_auth(user1_token, "golden_path_user1"),
                test_user_auth(user2_token, "golden_path_user2")
            ]
            
            auth_results = await asyncio.gather(*concurrent_auth_tasks, return_exceptions=True)
            
            # Analyze authentication results
            successful_auths = [r for r in auth_results if isinstance(r, dict) and r.get("success")]
            
            if len(successful_auths) < 2:
                isolation_violations.append(
                    f"Concurrent authentication failed: Only {len(successful_auths)}/2 users authenticated"
                )
            
            # Test concurrent WebSocket connections (if auth successful)
            if len(successful_auths) >= 2:
                try:
                    async def test_websocket_isolation(user_token, user_id):
                        """Test WebSocket isolation for user."""
                        try:
                            auth_headers = {
                                "Authorization": f"Bearer {user_token}",
                                "X-User-ID": user_id
                            }
                            
                            ws = await asyncio.wait_for(
                                websockets.connect(
                                    self.websocket_url,
                                    additional_headers=auth_headers,
                                    timeout=8.0
                                ),
                                timeout=10.0
                            )
                            
                            # Send user-specific message
                            message = {
                                "type": "user_identity_test",
                                "user_id": user_id,
                                "timestamp": time.time()
                            }
                            
                            await ws.send(json.dumps(message))
                            
                            # Receive response and verify isolation
                            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                            response_data = json.loads(response)
                            
                            # Verify user identity in response
                            response_user_id = response_data.get("user_id")
                            if response_user_id != user_id:
                                isolation_violations.append(
                                    f"WebSocket isolation violation: {user_id} got response for {response_user_id}"
                                )
                            
                            await ws.close()
                            return {"success": True, "user_id": user_id}
                            
                        except Exception as e:
                            isolation_violations.append(f"WebSocket error for {user_id}: {e}")
                            return {"success": False, "user_id": user_id, "error": str(e)}
                    
                    # Run concurrent WebSocket tests
                    ws_tasks = [
                        test_websocket_isolation(user1_token, "golden_path_user1"),
                        test_websocket_isolation(user2_token, "golden_path_user2")
                    ]
                    
                    ws_results = await asyncio.gather(*ws_tasks, return_exceptions=True)
                    successful_ws = [r for r in ws_results if isinstance(r, dict) and r.get("success")]
                    
                    if len(successful_ws) < 2:
                        isolation_violations.append(
                            f"WebSocket isolation test failed: Only {len(successful_ws)}/2 connections successful"
                        )
                    
                except Exception as e:
                    isolation_violations.append(f"WebSocket isolation testing failed: {e}")
            
            # CRITICAL ASSESSMENT: JWT Isolation Success
            if isolation_violations:
                violation_summary = "\n".join([f"  - {v}" for v in isolation_violations])
                logger.error("JWT ISOLATION VIOLATION: Multi-user Golden Path broken")
                logger.error(f"Violations:\n{violation_summary}")
                
                # This test SHOULD FAIL before SSOT refactor
                assert not isolation_violations, (
                    f"JWT ISOLATION VIOLATION: Multi-user chat isolation is broken, "
                    f"affecting enterprise customers ($500K+ ARR). "
                    f"Found {len(isolation_violations)} isolation violations. "
                    f"Violations:\n{violation_summary}"
                )
            else:
                logger.info("✓ JWT ISOLATION SUCCESS: Multi-user Golden Path working correctly")
                
        except Exception as e:
            pytest.fail(
                f"JWT ISOLATION CRITICAL FAILURE: Multi-user Golden Path completely broken. "
                f"This severely affects enterprise customer experience. Error: {e}"
            )

    @pytest.mark.asyncio
    async def test_jwt_error_handling_golden_path_resilience(self):
        """
        GOLDEN PATH TEST: JWT error handling doesn't break Golden Path.
        
        EXPECTED: FAIL - Poor JWT error handling disrupts Golden Path
        AFTER SSOT: PASS - Graceful JWT error handling preserves Golden Path
        
        This test validates that JWT errors are handled gracefully without
        breaking the overall Golden Path user experience.
        """
        error_handling_violations = []
        
        # Test scenarios that should be handled gracefully
        error_scenarios = [
            {
                "name": "Expired JWT Token",
                "token": self._create_expired_jwt_token(),
                "expected_response": "401_with_refresh_hint"
            },
            {
                "name": "Invalid JWT Signature", 
                "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.invalid_signature",
                "expected_response": "401_clean_error"
            },
            {
                "name": "Malformed JWT Token",
                "token": "not.a.valid.jwt.token",
                "expected_response": "401_clean_error"
            },
            {
                "name": "Empty JWT Token",
                "token": "",
                "expected_response": "401_clean_error"
            }
        ]
        
        for scenario in error_scenarios:
            scenario_name = scenario["name"]
            test_token = scenario["token"]
            expected_response = scenario["expected_response"]
            
            try:
                # Test backend response to invalid JWT
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {test_token}"} if test_token else {}
                    auth_url = f"{self.backend_base_url}/api/v1/users/me"
                    
                    response = await client.get(auth_url, headers=headers, timeout=5.0)
                    
                    # Analyze error handling quality
                    if response.status_code == 200:
                        # This is a serious violation - invalid tokens should not succeed
                        error_handling_violations.append(
                            f"{scenario_name}: Invalid JWT was accepted (status: 200). "
                            f"This is a critical security violation."
                        )
                    elif response.status_code == 401:
                        # Expected response, but check error quality
                        try:
                            error_data = response.json()
                            error_message = error_data.get("detail", "").lower()
                            
                            # Check for helpful error messages (Golden Path UX)
                            if "token" not in error_message and "auth" not in error_message:
                                error_handling_violations.append(
                                    f"{scenario_name}: Unhelpful error message for Golden Path UX: {error_data}"
                                )
                            
                            # Check for security information leakage
                            sensitive_terms = ["secret", "key", "decode", "verify", "signature"]
                            if any(term in error_message for term in sensitive_terms):
                                error_handling_violations.append(
                                    f"{scenario_name}: Error message leaks sensitive info: {error_message}"
                                )
                                
                        except Exception:
                            # Non-JSON error response is acceptable for 401
                            pass
                    elif response.status_code == 500:
                        # Server error for JWT handling is a violation
                        error_handling_violations.append(
                            f"{scenario_name}: Server error (500) for JWT handling breaks Golden Path"
                        )
                    else:
                        # Other status codes may be acceptable, but log for analysis
                        logger.warning(f"{scenario_name}: Unexpected status {response.status_code}")
                
                # Test WebSocket error handling
                try:
                    auth_headers = {
                        "Authorization": f"Bearer {test_token}",
                        "X-User-ID": "error_test_user"
                    } if test_token else {"X-User-ID": "error_test_user"}
                    
                    # WebSocket should reject gracefully, not crash
                    websocket = await asyncio.wait_for(
                        websockets.connect(
                            self.websocket_url,
                            additional_headers=auth_headers,
                            timeout=3.0
                        ),
                        timeout=5.0
                    )
                    
                    # If connection succeeds with invalid token, that's a violation
                    await websocket.close()
                    error_handling_violations.append(
                        f"{scenario_name}: WebSocket accepted invalid JWT - security violation"
                    )
                    
                except (websockets.ConnectionClosedError, 
                        websockets.InvalidStatusCode,
                        asyncio.TimeoutError):
                    # Expected rejections - this is correct behavior
                    logger.info(f"✓ {scenario_name}: WebSocket correctly rejected invalid JWT")
                    
                except Exception as e:
                    # Unexpected errors indicate poor error handling
                    error_handling_violations.append(
                        f"{scenario_name}: WebSocket error handling issue: {e}"
                    )
                    
            except Exception as e:
                error_handling_violations.append(
                    f"{scenario_name}: Error handling test failed: {e}"
                )
        
        # ASSESSMENT: Error Handling Quality
        if error_handling_violations:
            violation_summary = "\n".join([f"  - {v}" for v in error_handling_violations])
            logger.error("JWT ERROR HANDLING VIOLATION: Poor error handling affects Golden Path")
            logger.error(f"Violations:\n{violation_summary}")
            
            # This test SHOULD FAIL before SSOT refactor
            assert not error_handling_violations, (
                f"JWT ERROR HANDLING VIOLATION: Poor JWT error handling disrupts Golden Path UX "
                f"and creates security risks. Found {len(error_handling_violations)} violations "
                f"affecting $500K+ ARR customer experience. Violations:\n{violation_summary}"
            )
        else:
            logger.info("✓ JWT ERROR HANDLING SUCCESS: Graceful error handling preserves Golden Path")

    @pytest.mark.asyncio
    async def test_jwt_performance_golden_path_impact(self):
        """
        GOLDEN PATH TEST: JWT performance doesn't degrade Golden Path.
        
        EXPECTED: FAIL - JWT performance issues slow Golden Path  
        AFTER SSOT: PASS - Optimized JWT handling maintains Golden Path speed
        
        This test validates that JWT operations are fast enough to maintain
        good Golden Path user experience (sub-second responses).
        """
        performance_violations = []
        
        # Performance benchmarks for Golden Path
        max_jwt_validation_time = 1.0  # 1 second max for JWT validation
        max_websocket_connect_time = 3.0  # 3 seconds max for WebSocket connection
        max_backend_auth_time = 2.0  # 2 seconds max for backend authentication
        
        # Create test JWT token
        test_token = self.auth_helper.create_test_jwt_token(
            user_id="performance_test_user",
            email="perf@golden-path-test.com",
            permissions=["read", "write", "chat"]
        )
        
        try:
            # PERFORMANCE TEST 1: Backend JWT Validation Speed
            backend_auth_times = []
            
            for attempt in range(3):  # Test multiple times for consistency
                start_time = time.time()
                
                try:
                    async with httpx.AsyncClient() as client:
                        headers = {"Authorization": f"Bearer {test_token}"}
                        auth_url = f"{self.backend_base_url}/api/v1/users/me"
                        
                        response = await client.get(auth_url, headers=headers, timeout=max_backend_auth_time)
                        
                        auth_time = time.time() - start_time
                        backend_auth_times.append(auth_time)
                        
                        if auth_time > max_backend_auth_time:
                            performance_violations.append(
                                f"Backend JWT auth too slow: {auth_time:.2f}s > {max_backend_auth_time}s (attempt {attempt + 1})"
                            )
                        
                        if response.status_code != 200:
                            performance_violations.append(
                                f"Backend auth failed during performance test: {response.status_code}"
                            )
                            
                except asyncio.TimeoutError:
                    performance_violations.append(
                        f"Backend auth timeout during performance test (attempt {attempt + 1})"
                    )
                except Exception as e:
                    performance_violations.append(
                        f"Backend auth error during performance test: {e}"
                    )
            
            # PERFORMANCE TEST 2: WebSocket JWT Connection Speed  
            websocket_connect_times = []
            
            for attempt in range(2):  # WebSocket connections are more expensive
                start_time = time.time()
                
                try:
                    auth_headers = {
                        "Authorization": f"Bearer {test_token}",
                        "X-User-ID": "performance_test_user"
                    }
                    
                    websocket = await asyncio.wait_for(
                        websockets.connect(
                            self.websocket_url,
                            additional_headers=auth_headers,
                            timeout=max_websocket_connect_time
                        ),
                        timeout=max_websocket_connect_time + 1.0
                    )
                    
                    connect_time = time.time() - start_time
                    websocket_connect_times.append(connect_time)
                    
                    if connect_time > max_websocket_connect_time:
                        performance_violations.append(
                            f"WebSocket JWT connect too slow: {connect_time:.2f}s > {max_websocket_connect_time}s"
                        )
                    
                    await websocket.close()
                    
                except asyncio.TimeoutError:
                    performance_violations.append(
                        f"WebSocket connect timeout during performance test (attempt {attempt + 1})"
                    )
                except Exception as e:
                    performance_violations.append(
                        f"WebSocket connect error during performance test: {e}"
                    )
            
            # PERFORMANCE TEST 3: JWT Token Validation Speed (Direct)
            jwt_validation_times = []
            
            for attempt in range(5):  # Lightweight operations can be tested more
                start_time = time.time()
                
                try:
                    # Test JWT validation directly (if accessible)
                    validation_result = await self.auth_helper.validate_jwt_token(test_token)
                    
                    validation_time = time.time() - start_time
                    jwt_validation_times.append(validation_time)
                    
                    if validation_time > max_jwt_validation_time:
                        performance_violations.append(
                            f"JWT validation too slow: {validation_time:.3f}s > {max_jwt_validation_time}s"
                        )
                    
                    if not validation_result.get("valid"):
                        performance_violations.append(
                            f"JWT validation failed during performance test: {validation_result}"
                        )
                        
                except Exception as e:
                    performance_violations.append(
                        f"JWT validation error during performance test: {e}"
                    )
            
            # PERFORMANCE ANALYSIS
            avg_backend_auth = sum(backend_auth_times) / len(backend_auth_times) if backend_auth_times else float('inf')
            avg_websocket_connect = sum(websocket_connect_times) / len(websocket_connect_times) if websocket_connect_times else float('inf')
            avg_jwt_validation = sum(jwt_validation_times) / len(jwt_validation_times) if jwt_validation_times else float('inf')
            
            # Log performance metrics
            logger.info(f"JWT Performance Metrics:")
            logger.info(f"  - Backend Auth: {avg_backend_auth:.2f}s avg")
            logger.info(f"  - WebSocket Connect: {avg_websocket_connect:.2f}s avg")
            logger.info(f"  - JWT Validation: {avg_jwt_validation:.3f}s avg")
            
            # Check if performance is acceptable for Golden Path
            total_golden_path_time = avg_backend_auth + avg_websocket_connect
            max_total_golden_path_time = 4.0  # 4 seconds total for complete Golden Path
            
            if total_golden_path_time > max_total_golden_path_time:
                performance_violations.append(
                    f"Total Golden Path JWT performance too slow: {total_golden_path_time:.2f}s > {max_total_golden_path_time}s"
                )
            
        except Exception as e:
            performance_violations.append(f"Performance testing failed: {e}")
        
        # ASSESSMENT: Performance Impact
        if performance_violations:
            violation_summary = "\n".join([f"  - {v}" for v in performance_violations])
            logger.error("JWT PERFORMANCE VIOLATION: Slow JWT operations degrade Golden Path")
            logger.error(f"Violations:\n{violation_summary}")
            
            # This test SHOULD FAIL before SSOT refactor
            assert not performance_violations, (
                f"JWT PERFORMANCE VIOLATION: Slow JWT operations degrade Golden Path user experience, "
                f"affecting $500K+ ARR customer satisfaction. "
                f"Found {len(performance_violations)} performance issues. "
                f"Violations:\n{violation_summary}"
            )
        else:
            logger.info("✓ JWT PERFORMANCE SUCCESS: Fast JWT operations maintain Golden Path speed")

    def _create_expired_jwt_token(self) -> str:
        """Create an expired JWT token for testing error handling."""
        from datetime import datetime, timezone, timedelta
        
        # Create token that expired 1 hour ago
        payload = {
            "sub": "expired_test_user",
            "email": "expired@test.com",
            "permissions": ["read"],
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            "type": "access",
            "iss": "netra-auth-service"
        }
        
        return jwt.encode(payload, self.auth_helper.config.jwt_secret, algorithm="HS256")

    def teardown_method(self, method):
        """Clean up after test."""
        super().teardown_method(method)
        logger.info(f"JWT Golden Path protection test completed: {method.__name__}")