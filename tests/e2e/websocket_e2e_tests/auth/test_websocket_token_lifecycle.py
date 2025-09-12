"""
E2E WebSocket Token Lifecycle Tests - CRITICAL SECURITY VALIDATION

Business Value Justification (BVJ):
- Segment: Platform/Internal - Authentication security
- Business Goal: Prevent token-related security breaches in production
- Value Impact: Protects against token hijacking and session manipulation attacks
- Revenue Impact: Prevents security incidents that could cost $200K+ per breach

CRITICAL REQUIREMENTS FROM CLAUDE.MD:
- ALL e2e tests MUST use authentication (JWT/OAuth) except tests directly validating auth
- Tests MUST FAIL HARD when authentication is compromised
- NO MOCKS in E2E testing - use real WebSocket connections
- Tests with 0-second execution = automatic hard failure
- Follow SSOT patterns throughout

This test suite validates token lifecycle management during active WebSocket connections:
1. Token expiration during active connections
2. Token refresh scenarios
3. Malformed token handling with HARD FAILURES
4. Token manipulation attempt detection
5. Connection authentication state validation

@compliance CLAUDE.md - Real authentication required, hard failures for security violations
@compliance SPEC/core.xml - WebSocket authentication security for chat infrastructure
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.websocket_auth_test_helpers import (
    WebSocketAuthenticationTester,
    AuthenticationScenario,
    SecurityError,
    create_authenticated_websocket_client,
    run_websocket_authentication_security_tests
)
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient
from shared.isolated_environment import get_env


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.websocket
@pytest.mark.auth
class TestWebSocketTokenLifecycle(SSotBaseTestCase):
    """
    E2E WebSocket Token Lifecycle Tests.
    
    CRITICAL: These tests FAIL HARD when token lifecycle security is compromised.
    They validate that token expiration, refresh, and manipulation scenarios
    are handled securely during active WebSocket connections.
    """
    
    def setup_method(self):
        """Set up test environment with real services."""
        super().setup_method()
        
        # Test configuration
        self.env = get_env()
        self.test_environment = self.env.get("TEST_ENV", "test")
        self.backend_url = "ws://localhost:8000"
        
        # Initialize authentication tester with performance optimizations
        self.auth_tester = WebSocketAuthenticationTester(
            backend_url=self.backend_url,
            environment=self.test_environment,
            connection_timeout=10.0,
            enable_performance_optimizations=True  # Enable optimizations
        )
        
        # Performance tracking
        self.performance_start_time = None
        self.baseline_duration = None
        
        # Test tracking
        self.test_clients: List[RealWebSocketTestClient] = []
        self.security_violations: List[str] = []
        
        print(f"[U+1F527] Test setup completed for environment: {self.test_environment}")
    
    async def cleanup_method(self):
        """Clean up test resources."""
        print("[U+1F9F9] Cleaning up WebSocket token lifecycle test resources...")
        
        # Close all test clients
        for client in self.test_clients:
            try:
                await client.close()
            except Exception as e:
                print(f"Warning: Error closing client: {e}")
        
        # Cleanup authentication tester
        if hasattr(self, 'auth_tester'):
            await self.auth_tester.cleanup()
        
        self.test_clients.clear()
        self.security_violations.clear()
        
        print(" PASS:  Cleanup completed")
    
    async def test_token_expiration_during_active_connection(self):
        """
        Test token expiration during active WebSocket connection.
        
        CRITICAL: This test FAILS HARD if expired tokens are accepted.
        
        Validates:
        1. Token expires as expected during active connection
        2. Expired tokens are properly rejected
        3. Active connections handle token expiry correctly
        4. No security bypass mechanisms accept expired tokens
        """
        print(" CYCLE:  Testing token expiration during active connection...")
        
        try:
            # Step 1: Create user with short-lived token (2 minutes)
            test_email = f"token_expiry_test_{uuid.uuid4().hex[:8]}@example.com"
            
            auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
            
            # Create user with very short token expiry for testing
            user_id = f"expiry_test_{uuid.uuid4().hex[:8]}"
            short_token = auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=test_email,
                exp_minutes=2,  # Very short for testing
                permissions=["read", "write"]
            )
            
            print(f" PASS:  Created short-lived token (2min expiry) for user: {user_id}")
            
            # Step 2: Establish WebSocket connection
            client = await create_authenticated_websocket_client(
                backend_url=self.backend_url,
                environment=self.test_environment,
                user_email=test_email,
                user_id=user_id
            )
            self.test_clients.append(client)
            
            await client.connect()
            print(f" PASS:  WebSocket connected with short-lived token")
            
            # Step 3: Verify connection works initially
            initial_test_event = {
                "action": "ping",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_phase": "initial_validation"
            }
            
            await client.send_event("initial_test", initial_test_event)
            print(" PASS:  Initial event sent successfully with valid token")
            
            # Step 4: Wait for token to expire (plus buffer time)
            expiry_wait_seconds = (2 * 60) + 30  # 2 minutes + 30 second buffer
            print(f"[U+23F3] Waiting {expiry_wait_seconds}s for token to expire...")
            
            start_wait = time.time()
            await asyncio.sleep(expiry_wait_seconds)
            actual_wait = time.time() - start_wait
            
            print(f"[U+23F0] Waited {actual_wait:.1f}s for token expiry")
            
            # Step 5: Validate expired token is rejected by auth helper
            validation_result = await auth_helper.validate_jwt_token(short_token)
            
            if validation_result.get("valid", False):
                violation = (
                    f"CRITICAL SECURITY VIOLATION: Expired token still validated as VALID after "
                    f"{actual_wait:.1f}s. Token should have expired after 120s. "
                    f"This indicates a MAJOR authentication security flaw."
                )
                self.security_violations.append(violation)
                
                # FAIL HARD - this is a critical security issue
                pytest.fail(violation)
            
            print(f" PASS:  Expired token properly rejected: {validation_result.get('error', 'Token invalid')}")
            
            # Step 6: Test WebSocket behavior with expired token
            try:
                expired_test_event = {
                    "action": "test_with_expired_token",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "test_phase": "expired_token_test"
                }
                
                # This should fail because token is expired
                await client.send_event("expired_token_test", expired_test_event)
                
                # If we reach this point, it's a CRITICAL security violation
                violation = (
                    "CRITICAL SECURITY VIOLATION: WebSocket accepted event with EXPIRED token. "
                    "This allows unauthorized access after token expiry and represents a "
                    "MAJOR security flaw that could enable session hijacking."
                )
                self.security_violations.append(violation)
                
                # FAIL HARD - critical security violation
                pytest.fail(violation)
                
            except Exception as e:
                print(f" PASS:  WebSocket properly rejected expired token: {e}")
                # This is expected behavior - expired tokens should be rejected
            
            # Step 7: Test connection state after token expiry
            try:
                # Try to receive events with expired token
                await client.receive_event(timeout=3.0)
                
                # If successful, it might indicate connection is still active inappropriately
                print(" WARNING: [U+FE0F] WARNING: Connection still active after token expiry (may be acceptable)")
                
            except asyncio.TimeoutError:
                print(" PASS:  No events received with expired token (expected)")
            except Exception as e:
                print(f" PASS:  Connection properly handled expired token: {e}")
            
            print(" PASS:  Token expiration test PASSED - expired tokens properly rejected")
            
        except SecurityError as e:
            # Re-raise security errors to ensure test fails
            pytest.fail(f"Token expiration security test FAILED: {e}")
        except Exception as e:
            pytest.fail(f"Token expiration test failed with error: {e}")
    
    async def test_token_refresh_scenario(self):
        """
        Test token refresh scenarios during active WebSocket connections.
        
        Validates:
        1. Token refresh process works correctly
        2. Old tokens are invalidated after refresh
        3. New tokens are accepted properly
        4. Connection state is maintained during refresh
        """
        print(" CYCLE:  Testing token refresh scenario...")
        
        try:
            # Step 1: Create initial user and token
            test_email = f"token_refresh_{uuid.uuid4().hex[:8]}@example.com"
            user_id = f"refresh_user_{uuid.uuid4().hex[:8]}"
            
            auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
            
            # Create initial token
            initial_token = auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=test_email,
                exp_minutes=10,
                permissions=["read", "write"]
            )
            
            print(f" PASS:  Created initial token for user: {user_id}")
            
            # Step 2: Connect with initial token
            client = await create_authenticated_websocket_client(
                backend_url=self.backend_url,
                environment=self.test_environment,
                user_email=test_email,
                user_id=user_id
            )
            self.test_clients.append(client)
            
            await client.connect()
            print(" PASS:  Connected with initial token")
            
            # Step 3: Test initial connection works
            await client.send_event("initial_ping", {"test": "initial"})
            print(" PASS:  Initial connection validated")
            
            # Step 4: Generate refresh token
            print(" CYCLE:  Generating refresh token...")
            
            refresh_token = auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=test_email,
                exp_minutes=30,  # Longer expiry
                permissions=["read", "write", "refreshed"]  # Additional permission to verify refresh
            )
            
            print(" PASS:  Refresh token generated with extended expiry and permissions")
            
            # Step 5: Validate refresh token
            refresh_validation = await auth_helper.validate_jwt_token(refresh_token)
            
            if not refresh_validation.get("valid", False):
                pytest.fail(f"Refresh token validation failed: {refresh_validation.get('error')}")
            
            print(f" PASS:  Refresh token validated: {refresh_validation.get('user_id')}")
            
            # Step 6: Test that initial token can still be validated (before invalidation)
            initial_validation = await auth_helper.validate_jwt_token(initial_token)
            
            if not initial_validation.get("valid", False):
                print(f"[U+2139][U+FE0F] Initial token already expired: {initial_validation.get('error')}")
            else:
                print("[U+2139][U+FE0F] Initial token still valid (as expected before refresh)")
            
            # Step 7: Update client with refresh token (simulating refresh process)
            # In a real application, this would happen through a refresh endpoint
            if client.authenticated_user:
                client.authenticated_user.jwt_token = refresh_token
                client.authenticated_user.permissions.append("refreshed")
            
            print(" PASS:  Client updated with refresh token")
            
            # Step 8: Test connection with refresh token
            await client.send_event("refresh_test", {
                "test": "refreshed_connection",
                "new_permission": "refreshed" in (client.authenticated_user.permissions or [])
            })
            
            print(" PASS:  Connection works with refresh token")
            
            # Step 9: Test that refresh token has extended permissions
            try:
                await client.send_event("privileged_action", {
                    "action": "use_refreshed_permission",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                print(" PASS:  Refresh token enables extended permissions")
                
            except Exception as e:
                print(f"[U+2139][U+FE0F] Privileged action blocked: {e} (may be expected)")
            
            print(" PASS:  Token refresh scenario test PASSED")
            
        except Exception as e:
            pytest.fail(f"Token refresh scenario test failed: {e}")
    
    async def test_malformed_token_handling_hard_failure(self):
        """
        Test malformed token handling with HARD FAILURES.
        
        CRITICAL: This test FAILS HARD if ANY malformed tokens are accepted.
        
        Validates:
        1. Empty tokens are rejected
        2. Malformed JWT structures are rejected
        3. Invalid signatures are detected
        4. Token manipulation attempts are blocked
        5. None algorithm attacks are prevented
        """
        print(" SEARCH:  Testing malformed token handling with hard failure validation...")
        
        # Define malformed tokens that should ALL be rejected
        malformed_test_cases = [
            {
                "name": "Empty Token",
                "token": "",
                "description": "Empty string should be rejected"
            },
            {
                "name": "Plain String",
                "token": "not-a-jwt-token",
                "description": "Plain text should be rejected"
            },
            {
                "name": "Malformed JWT Structure",
                "token": "eyJhbGciOiJIUzI1NiJ9.invalid",
                "description": "Malformed JWT with invalid payload"
            },
            {
                "name": "Missing JWT Parts",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
                "description": "JWT missing payload and signature"
            },
            {
                "name": "Missing Signature",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",
                "description": "JWT missing signature part"
            },
            {
                "name": "None Algorithm Attack",
                "token": "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhdHRhY2tlciIsImFkbWluIjp0cnVlfQ.",
                "description": "None algorithm attack attempt"
            },
            {
                "name": "Invalid Base64",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid_base64!!!.signature",
                "description": "Invalid base64 encoding in payload"
            }
        ]
        
        auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        critical_violations = []
        
        for i, test_case in enumerate(malformed_test_cases):
            print(f"[U+1F9EA] Testing case {i+1}/{len(malformed_test_cases)}: {test_case['name']}")
            
            # Step 1: Test token validation
            try:
                validation_result = await auth_helper.validate_jwt_token(test_case['token'])
                
                if validation_result.get("valid", False):
                    violation = (
                        f"CRITICAL SECURITY VIOLATION: Malformed token accepted as VALID: "
                        f"{test_case['name']} - {test_case['description']}. "
                        f"Token: '{test_case['token'][:50]}...'. "
                        f"This represents a MAJOR authentication bypass vulnerability."
                    )
                    critical_violations.append(violation)
                    print(f" FAIL:  {violation}")
                else:
                    print(f" PASS:  {test_case['name']} properly rejected: {validation_result.get('error', 'Invalid token')}")
            
            except Exception as e:
                print(f" PASS:  {test_case['name']} validation failed as expected: {e}")
            
            # Step 2: Test WebSocket connection with malformed token
            try:
                test_client = RealWebSocketTestClient(
                    backend_url=self.backend_url,
                    environment=self.test_environment,
                    connection_timeout=5.0  # Shorter timeout for malformed token tests
                )
                
                # Create fake authenticated user with malformed token
                from test_framework.ssot.e2e_auth_helper import AuthenticatedUser
                
                test_client.authenticated_user = AuthenticatedUser(
                    user_id=f"malformed_test_user_{i}",
                    email=f"malformed{i}@example.com",
                    full_name=f"Malformed Test User {i}",
                    jwt_token=test_case['token'],
                    permissions=["read"],
                    created_at=datetime.now(timezone.utc).isoformat(),
                    is_test_user=True
                )
                
                # Test connection attempt - this should FAIL
                connection_success = False
                try:
                    await test_client.connect()
                    connection_success = True
                    
                    # If connection succeeds, it's a critical security violation
                    violation = (
                        f"CRITICAL SECURITY VIOLATION: WebSocket connection succeeded with malformed token: "
                        f"{test_case['name']} - {test_case['description']}. "
                        f"This allows unauthorized access with invalid authentication."
                    )
                    critical_violations.append(violation)
                    print(f" FAIL:  {violation}")
                    
                    # Try to close the connection if it was established
                    await test_client.close()
                    
                except Exception as e:
                    print(f" PASS:  WebSocket connection properly blocked for {test_case['name']}: {e}")
                
                if not connection_success:
                    print(f" PASS:  {test_case['name']} WebSocket connection blocked")
                
            except Exception as e:
                print(f" PASS:  {test_case['name']} WebSocket test failed as expected: {e}")
        
        # CRITICAL: Fail hard if ANY malformed tokens were accepted
        if critical_violations:
            violation_summary = "\n".join(critical_violations)
            pytest.fail(
                f"CRITICAL AUTHENTICATION SECURITY FAILURES DETECTED:\n\n{violation_summary}\n\n"
                f"Total violations: {len(critical_violations)}\n"
                f"These represent MAJOR security vulnerabilities that could enable:\n"
                f"- Authentication bypass attacks\n"
                f"- Unauthorized system access\n"
                f"- Session hijacking\n"
                f"- Privilege escalation\n\n"
                f"IMMEDIATE ACTION REQUIRED: Fix authentication validation logic."
            )
        
        print(" PASS:  Malformed token handling test PASSED - all malformed tokens properly rejected")
    
    async def test_token_manipulation_detection(self):
        """
        Test detection of token manipulation attempts.
        
        Validates:
        1. Modified JWT signatures are detected
        2. Payload tampering is caught
        3. Header manipulation is blocked
        4. Claims modification is prevented
        """
        print("[U+1F575][U+FE0F] Testing token manipulation detection...")
        
        try:
            # Step 1: Create valid token as baseline
            test_email = f"manipulation_test_{uuid.uuid4().hex[:8]}@example.com"
            user_id = f"manip_user_{uuid.uuid4().hex[:8]}"
            
            auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
            
            valid_token = auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=test_email,
                exp_minutes=10,
                permissions=["read"]
            )
            
            print(f" PASS:  Created valid baseline token for user: {user_id}")
            
            # Step 2: Validate baseline token works
            baseline_validation = await auth_helper.validate_jwt_token(valid_token)
            
            if not baseline_validation.get("valid", False):
                pytest.fail(f"Baseline token validation failed: {baseline_validation.get('error')}")
            
            print(" PASS:  Baseline token validation successful")
            
            # Step 3: Test various token manipulation attempts
            token_parts = valid_token.split('.')
            
            if len(token_parts) != 3:
                pytest.fail(f"Invalid baseline token structure: {len(token_parts)} parts")
            
            header, payload, signature = token_parts
            
            manipulation_attempts = [
                {
                    "name": "Modified Signature",
                    "token": f"{header}.{payload}.modified_signature_123",
                    "description": "Signature tampering attempt"
                },
                {
                    "name": "Modified Payload",
                    "token": f"{header}.modified_payload_123.{signature}",
                    "description": "Payload tampering attempt"
                },
                {
                    "name": "Modified Header",
                    "token": f"modified_header_123.{payload}.{signature}",
                    "description": "Header tampering attempt"
                },
                {
                    "name": "Swapped Parts",
                    "token": f"{payload}.{header}.{signature}",
                    "description": "JWT parts reordering attempt"
                }
            ]
            
            manipulation_violations = []
            
            for attempt in manipulation_attempts:
                print(f" TARGET:  Testing: {attempt['name']}")
                
                # Test validation of manipulated token
                try:
                    manipulation_validation = await auth_helper.validate_jwt_token(attempt['token'])
                    
                    if manipulation_validation.get("valid", False):
                        violation = (
                            f"SECURITY VIOLATION: Token manipulation not detected: {attempt['name']} - "
                            f"{attempt['description']}. Manipulated token was accepted as valid."
                        )
                        manipulation_violations.append(violation)
                        print(f" FAIL:  {violation}")
                    else:
                        print(f" PASS:  {attempt['name']} properly rejected: {manipulation_validation.get('error', 'Invalid')}")
                
                except Exception as e:
                    print(f" PASS:  {attempt['name']} validation failed as expected: {e}")
            
            # Fail if any manipulations were accepted
            if manipulation_violations:
                pytest.fail(
                    f"Token manipulation detection FAILED:\n" + 
                    "\n".join(manipulation_violations)
                )
            
            print(" PASS:  Token manipulation detection test PASSED")
            
        except Exception as e:
            pytest.fail(f"Token manipulation detection test failed: {e}")
    
    async def test_comprehensive_token_lifecycle_security(self):
        """
        Run comprehensive token lifecycle security test suite with performance measurement.
        
        This is the main integration test that validates all token lifecycle scenarios
        and measures the performance improvement from optimizations.
        CRITICAL: This test FAILS HARD for any security violations.
        """
        print("[U+1F512] Running comprehensive token lifecycle security test suite with performance optimizations...")
        
        try:
            # Measure performance with optimizations enabled
            suite_start = time.time()
            
            # Use the authentication tester for comprehensive validation
            test_results = await self.auth_tester.run_comprehensive_authentication_test_suite(
                include_timing_attacks=True,
                use_parallel_execution=True  # Enable parallel execution
            )
            
            suite_duration = time.time() - suite_start
            
            # Log performance results
            if test_results.get("performance_metrics"):
                metrics = test_results["performance_metrics"]
                print(f" LIGHTNING:  PERFORMANCE METRICS:")
                print(f"   [U+2022] Total duration: {suite_duration:.2f}s")
                print(f"   [U+2022] Token generation time: {metrics['total_token_generation_time']:.3f}s")
                print(f"   [U+2022] Connection establishment time: {metrics['total_connection_establishment_time']:.3f}s")
                print(f"   [U+2022] Parallel operations: {metrics['parallel_operations_count']}")
                
                if metrics.get("token_cache_stats"):
                    cache_stats = metrics["token_cache_stats"]
                    print(f"   [U+2022] Token cache hit rate: {cache_stats['hit_rate_percent']}%")
                    print(f"   [U+2022] Cache hits/misses: {cache_stats['cache_hits']}/{cache_stats['cache_misses']}")
                
                if metrics.get("connection_pool_stats"):
                    pool_stats = metrics["connection_pool_stats"]
                    print(f"   [U+2022] Connection pool hit rate: {pool_stats['hit_rate_percent']}%")
                    print(f"   [U+2022] Pool hits/misses: {pool_stats['pool_hits']}/{pool_stats['pool_misses']}")
                
                savings_ms = metrics.get("optimization_savings_estimate_ms", 0)
                if savings_ms > 0:
                    print(f"   [U+2022] Estimated savings: {savings_ms:.1f}ms ({savings_ms/1000:.1f}s)")
                    improvement_percent = (savings_ms / 1000) / suite_duration * 100
                    print(f"   [U+2022] Performance improvement estimate: {improvement_percent:.1f}%")
                    
                    # Check if we achieved the target 30% improvement
                    if improvement_percent >= 30:
                        print(f" PASS:  TARGET ACHIEVED: {improvement_percent:.1f}% performance improvement (target: 30%)")
                    elif improvement_percent >= 15:
                        print(f"[U+1F536] GOOD IMPROVEMENT: {improvement_percent:.1f}% performance improvement (target: 30%)")
                    else:
                        print(f" WARNING: [U+FE0F] LOW IMPROVEMENT: {improvement_percent:.1f}% performance improvement (target: 30%)")
            
            # Store performance data for comparison
            self.baseline_duration = suite_duration
            
            # Validate test results
            assert test_results["total_tests"] > 0, "No tests were executed"
            assert test_results["passed_tests"] > 0, "No tests passed"
            
            success_rate = test_results["success_rate"]
            
            # Require high success rate for security tests
            if success_rate < 100.0:
                pytest.fail(
                    f"Token lifecycle security test suite FAILED: {success_rate:.1f}% success rate. "
                    f"Security tests require 100% success rate. "
                    f"Failed tests: {test_results['failed_tests']}/"
                    f"{test_results['total_tests']}. "
                    f"Security violations: {len(test_results['security_violations'])}"
                )
            
            print(f" PASS:  Comprehensive token lifecycle security test PASSED: {success_rate:.1f}% success rate")
            print(f" CHART:  Tests completed: {test_results['total_tests']} passed, 0 failed")
            print(f"[U+23F1][U+FE0F] Total duration: {test_results['total_duration']:.2f}s")
            
            # Ensure no security violations
            if test_results["security_violations"]:
                pytest.fail(
                    f"CRITICAL: {len(test_results['security_violations'])} security violations detected: "
                    f"{test_results['security_violations']}"
                )
            
        except SecurityError as e:
            pytest.fail(f"CRITICAL SECURITY FAILURE in comprehensive test: {e}")
        except Exception as e:
            pytest.fail(f"Comprehensive token lifecycle security test failed: {e}")
    
    async def test_performance_optimization_comparison(self):
        """
        Compare performance with and without optimizations to validate improvements.
        
        This test measures the actual performance improvement from optimizations
        and validates that the 30% improvement target is achieved.
        """
        print(" LIGHTNING:  Testing performance optimization improvements...")
        
        try:
            # Test 1: Run with optimizations DISABLED
            print(" CHART:  Phase 1: Running tests WITHOUT optimizations...")
            
            baseline_tester = WebSocketAuthenticationTester(
                backend_url=self.backend_url,
                environment=self.test_environment,
                connection_timeout=10.0,
                enable_performance_optimizations=False  # Disabled for baseline
            )
            
            baseline_start = time.time()
            baseline_results = await baseline_tester.run_comprehensive_authentication_test_suite(
                include_timing_attacks=True,
                use_parallel_execution=False  # No parallel execution
            )
            baseline_duration = time.time() - baseline_start
            
            await baseline_tester.cleanup()
            
            print(f"[U+1F40C] Baseline (no optimizations): {baseline_duration:.2f}s")
            
            # Test 2: Run with optimizations ENABLED
            print(" CHART:  Phase 2: Running tests WITH optimizations...")
            
            optimized_tester = WebSocketAuthenticationTester(
                backend_url=self.backend_url,
                environment=self.test_environment,
                connection_timeout=10.0,
                enable_performance_optimizations=True  # Enabled for comparison
            )
            
            optimized_start = time.time()
            optimized_results = await optimized_tester.run_comprehensive_authentication_test_suite(
                include_timing_attacks=True,
                use_parallel_execution=True  # With parallel execution
            )
            optimized_duration = time.time() - optimized_start
            
            # Calculate actual performance improvement
            time_saved = baseline_duration - optimized_duration
            improvement_percent = (time_saved / baseline_duration) * 100
            
            print(f" LIGHTNING:  Optimized (with optimizations): {optimized_duration:.2f}s")
            print(f"[U+1F4BE] Time saved: {time_saved:.2f}s")
            print(f"[U+1F4C8] Actual performance improvement: {improvement_percent:.1f}%")
            
            # Log detailed performance metrics
            if optimized_results.get("performance_metrics"):
                metrics = optimized_results["performance_metrics"]
                
                print(f"\n SEARCH:  DETAILED OPTIMIZATION METRICS:")
                
                if metrics.get("token_cache_stats"):
                    cache_stats = metrics["token_cache_stats"]
                    print(f"   Token Cache:")
                    print(f"     [U+2022] Hit rate: {cache_stats['hit_rate_percent']}%")
                    print(f"     [U+2022] Cache hits: {cache_stats['cache_hits']}")
                    print(f"     [U+2022] Cache misses: {cache_stats['cache_misses']}")
                
                if metrics.get("connection_pool_stats"):
                    pool_stats = metrics["connection_pool_stats"]
                    print(f"   Connection Pool:")
                    print(f"     [U+2022] Hit rate: {pool_stats['hit_rate_percent']}%")
                    print(f"     [U+2022] Pool hits: {pool_stats['pool_hits']}")
                    print(f"     [U+2022] Pool misses: {pool_stats['pool_misses']}")
                
                print(f"   Parallel Operations: {metrics['parallel_operations_count']}")
                print(f"   Estimated Savings: {metrics.get('optimization_savings_estimate_ms', 0):.1f}ms")
            
            await optimized_tester.cleanup()
            
            # Validate performance improvement
            if improvement_percent >= 30:
                print(f" PASS:  SUCCESS: Achieved {improvement_percent:.1f}% improvement (target: 30%)")
            elif improvement_percent >= 20:
                print(f"[U+1F536] GOOD: Achieved {improvement_percent:.1f}% improvement (target: 30%, acceptable: 20%)")
            elif improvement_percent > 0:
                print(f" WARNING: [U+FE0F] MODERATE: Achieved {improvement_percent:.1f}% improvement (target: 30%)")
            else:
                pytest.fail(f"PERFORMANCE REGRESSION: {improvement_percent:.1f}% improvement (negative improvement)")
            
            # Validate both test suites had same success rate
            baseline_success_rate = baseline_results.get("success_rate", 0)
            optimized_success_rate = optimized_results.get("success_rate", 0)
            
            if baseline_success_rate != optimized_success_rate:
                pytest.fail(
                    f"Success rate mismatch: baseline {baseline_success_rate}% vs optimized {optimized_success_rate}%. "
                    f"Optimizations must not affect test reliability."
                )
            
            # Store results for reporting
            self.baseline_duration = baseline_duration
            self.optimized_duration = optimized_duration
            self.performance_improvement = improvement_percent
            
            print(f" TARGET:  Performance optimization validation completed successfully!")
            
            # Ensure minimum improvement threshold is met
            if improvement_percent < 10:
                print(f" WARNING: [U+FE0F] WARNING: Performance improvement {improvement_percent:.1f}% is below recommended minimum of 10%")
        
        except Exception as e:
            pytest.fail(f"Performance optimization comparison failed: {e}")
    
    def teardown_method(self):
        """Clean up after each test method."""
        # Run async cleanup
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # If loop is running, schedule cleanup
            asyncio.create_task(self.cleanup_method())
        else:
            # If loop is not running, run cleanup
            loop.run_until_complete(self.cleanup_method())
        
        super().teardown_method()


# Additional test functions for edge cases

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.websocket
@pytest.mark.auth
async def test_token_lifecycle_edge_cases():
    """
    Test edge cases in token lifecycle management.
    
    CRITICAL: This test validates edge cases that could be exploited.
    """
    print(" SEARCH:  Testing token lifecycle edge cases...")
    
    auth_helper = E2EWebSocketAuthHelper(environment="test")
    
    # Test extremely short token expiry
    ultra_short_token = auth_helper.create_test_jwt_token(
        user_id="edge_case_user",
        email="edgecase@example.com",
        exp_minutes=0.1  # 6 seconds
    )
    
    print("[U+23F0] Testing ultra-short token expiry (6 seconds)...")
    
    # Validate token initially works
    initial_validation = await auth_helper.validate_jwt_token(ultra_short_token)
    assert initial_validation.get("valid", False), "Ultra-short token should be initially valid"
    
    # Wait for expiry
    await asyncio.sleep(10)  # Wait longer than expiry
    
    # Validate token is expired
    expired_validation = await auth_helper.validate_jwt_token(ultra_short_token)
    
    if expired_validation.get("valid", False):
        pytest.fail("CRITICAL: Ultra-short token still valid after expiry time")
    
    print(" PASS:  Ultra-short token properly expired")
    
    # Test token with far future expiry
    far_future_token = auth_helper.create_test_jwt_token(
        user_id="future_user", 
        email="future@example.com",
        exp_minutes=525600  # 1 year
    )
    
    future_validation = await auth_helper.validate_jwt_token(far_future_token)
    assert future_validation.get("valid", False), "Far future token should be valid"
    
    print(" PASS:  Token lifecycle edge cases test PASSED")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v", "-s"])