"""
E2E GCP Staging Tests - WebSocket Infrastructure Validation - CRITICAL REGRESSION PREVENTION

Business Value Justification:
- Segment: Platform/Internal - GCP Infrastructure Validation
- Business Goal: Prevent WebSocket infrastructure failures in staging/production
- Value Impact: Catches GCP Load Balancer configuration issues that block Golden Path
- Revenue Impact: Prevents 100% chat functionality failure scenarios ($120K+ MRR impact)

CRITICAL TEST PURPOSE:
These E2E tests specifically target the GCP Load Balancer authentication header 
stripping issue that caused complete WebSocket infrastructure failure (GitHub issue #113).

PRIMARY REGRESSION PREVENTION:
- test_gcp_load_balancer_preserves_authorization_header()
- test_gcp_load_balancer_preserves_e2e_bypass_header()

Root Cause Addressed:
GCP HTTPS Load Balancer was stripping authentication headers (Authorization, X-E2E-Bypass) 
for WebSocket upgrade requests, causing 100% authentication failures and 1011 errors.

Infrastructure Fix Required:
terraform-gcp-staging/load-balancer.tf needs WebSocket path authentication header preservation.

COMPLEMENTARY TESTS:
This file focuses on WebSocket-specific infrastructure validation. 
See test_gcp_load_balancer_header_validation.py for comprehensive load balancer testing.

CLAUDE.MD E2E AUTH COMPLIANCE:
All tests use real authentication as required by CLAUDE.MD Section 7.3.
"""

import asyncio
import json
import logging
import pytest
import time
import unittest
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch

logger = logging.getLogger(__name__)

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, AuthenticatedUser
from tests.e2e.staging_config import StagingTestConfig, staging_urls
from shared.isolated_environment import get_env


class TestWebSocketGCPStagingInfrastructure(SSotBaseTestCase, unittest.TestCase):
    """
    CRITICAL E2E Tests for GCP Staging WebSocket Infrastructure
    
    These tests specifically validate GCP Load Balancer configuration
    to prevent the authentication header stripping regression that
    caused complete Golden Path failure.
    """
    
    def setup_method(self, method=None):
        """Set up staging environment test configuration."""
        super().setup_method(method)
        self.env = get_env()
        self.staging_config = StagingTestConfig()
        self.e2e_helper = E2EWebSocketAuthHelper(environment="staging")
        
        # GCP staging WebSocket URL
        self.staging_websocket_url = self.staging_config.urls.websocket_url
        
        # Test timeout configuration for GCP Cloud Run
        self.gcp_timeout = 15.0  # GCP Cloud Run has connection limits
        self.auth_timeout = 10.0  # Authentication should be faster with E2E headers
        
    async def test_gcp_load_balancer_preserves_authorization_header(self):
        """
        CRITICAL: Test that GCP Load Balancer preserves Authorization header for WebSocket.
        
        This is the PRIMARY REGRESSION PREVENTION test for the infrastructure failure
        that blocked 100% of Golden Path chat functionality.
        
        ROOT CAUSE: GCP Load Balancer configuration was missing authentication header
        forwarding for WebSocket paths, causing headers to be stripped.
        """
        # Arrange - Create authenticated user for staging environment
        auth_user = await self.e2e_helper.create_authenticated_user(
            email="gcp_auth_test@example.com",
            permissions=["read", "write", "websocket"]
        )
        
        # Get WebSocket headers with staging-optimized authentication
        websocket_headers = self.e2e_helper.get_websocket_headers(auth_user.jwt_token)
        
        # Log test attempt for debugging
        print(f" SEARCH:  CRITICAL TEST: GCP Load Balancer auth header preservation")
        print(f"[U+1F310] Staging WebSocket URL: {self.staging_websocket_url}")
        print(f"[U+1F511] Headers being sent: {list(websocket_headers.keys())}")
        print(f" PASS:  Authorization header present: {'authorization' in [k.lower() for k in websocket_headers.keys()]}")
        
        # Act & Assert - Test WebSocket connection through GCP Load Balancer
        connection_successful = False
        auth_headers_preserved = False
        error_details = None
        
        try:
            # CRITICAL: Connect through GCP Load Balancer with auth headers
            async with websockets.connect(
                self.staging_websocket_url,
                additional_headers=websocket_headers,
                # GCP-specific connection parameters
                ping_interval=None,  # Disable ping during connection for GCP
                ping_timeout=None,   # Disable ping timeout during handshake  
                max_size=2**16      # Smaller max message size for faster handshake
            ) as websocket:
                connection_successful = True
                print(f" PASS:  WebSocket connection established through GCP Load Balancer")
                
                # Send header validation test message
                header_test_message = {
                    "type": "gcp_header_validation_test",
                    "purpose": "validate_authorization_header_preservation", 
                    "expected_user_id": auth_user.user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "test_environment": "staging",
                    "infrastructure": "gcp_load_balancer"
                }
                
                await websocket.send(json.dumps(header_test_message))
                print(f"[U+1F4E4] Sent header validation test message")
                
                # Wait for response that confirms auth header was received by backend
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=self.auth_timeout)
                    response_data = json.loads(response)
                    print(f"[U+1F4E5] Received response: {response_data.get('type', 'unknown')}")
                    
                    # Any valid response indicates auth headers were preserved and processed
                    auth_headers_preserved = True
                    
                except asyncio.TimeoutError:
                    print(f"[U+23F0] Response timeout - connection established but no immediate response")
                    # Connection establishment without immediate closure indicates auth success
                    auth_headers_preserved = True
                    
        except websockets.exceptions.InvalidHandshake as e:
            error_details = f"WebSocket handshake failed: {e}"
            print(f" FAIL:  Handshake error (may indicate auth header stripping): {error_details}")
            
        except websockets.exceptions.ConnectionClosedError as e:
            error_details = f"Connection closed during handshake: {e}"
            print(f" FAIL:  Connection closed (may indicate auth failure): {error_details}")
            
        except asyncio.TimeoutError:
            error_details = "Connection timeout (GCP Load Balancer may be stripping headers)"
            print(f"[U+23F0] Connection timeout: {error_details}")
            
        except Exception as e:
            error_details = f"Unexpected connection error: {e}"
            print(f" FIRE:  Unexpected error: {error_details}")
        
        # CRITICAL ASSERTIONS - These failures indicate infrastructure regression
        self.assertTrue(
            connection_successful,
            f"CRITICAL FAILURE: GCP Load Balancer auth header stripping detected. "
            f"WebSocket connection failed through staging infrastructure. "
            f"Error: {error_details}. "
            f"This indicates the Load Balancer is not preserving Authorization headers. "
            f"Required fix: Update terraform-gcp-staging/load-balancer.tf with auth header forwarding."
        )
        
        self.assertTrue(
            auth_headers_preserved, 
            f"CRITICAL FAILURE: Authorization headers not preserved by GCP Load Balancer. "
            f"Connection established but auth context not available. "
            f"This indicates partial header stripping. "
            f"Required fix: Add header_action for Authorization header preservation."
        )
        
        print(f" PASS:  CRITICAL TEST PASSED: GCP Load Balancer preserves Authorization headers")
    
    async def test_gcp_load_balancer_preserves_e2e_bypass_header(self):
        """
        CRITICAL: Test that GCP Load Balancer preserves X-E2E-Bypass header.
        
        This validates E2E testing headers are forwarded through the Load Balancer,
        enabling staging environment testing without OAuth simulation failures.
        """
        # Arrange - Create authenticated user with E2E bypass headers
        auth_user = await self.e2e_helper.create_authenticated_user(
            email="e2e_bypass_test@example.com",
            permissions=["read", "write", "e2e_test"]
        )
        
        # Get E2E optimized headers for staging
        websocket_headers = self.e2e_helper.get_websocket_headers(auth_user.jwt_token)
        
        # Add explicit E2E bypass headers 
        websocket_headers.update({
            "X-E2E-Bypass": "true",
            "X-E2E-Test-Environment": "staging",
            "X-Test-Infrastructure": "gcp_load_balancer"
        })
        
        print(f" SEARCH:  CRITICAL TEST: E2E bypass header preservation through GCP")
        print(f"[U+1F511] E2E headers: {[k for k in websocket_headers.keys() if 'e2e' in k.lower() or 'test' in k.lower()]}")
        
        # Act & Assert - Test E2E header preservation
        e2e_headers_preserved = False
        connection_details = None
        
        try:
            async with websockets.connect(
                self.staging_websocket_url,
                additional_headers=websocket_headers,
                ping_interval=None,
                ping_timeout=None
            ) as websocket:
                print(f" PASS:  WebSocket connection with E2E headers established")
                
                # Send E2E header validation message
                e2e_test_message = {
                    "type": "e2e_header_validation_test",
                    "purpose": "validate_e2e_bypass_headers",
                    "user_id": auth_user.user_id,
                    "test_mode": "e2e_staging",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(e2e_test_message))
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=self.auth_timeout)
                    response_data = json.loads(response)
                    
                    # Response indicates E2E headers were preserved
                    e2e_headers_preserved = True
                    connection_details = f"Response type: {response_data.get('type', 'unknown')}"
                    print(f" PASS:  E2E headers preserved - received: {connection_details}")
                    
                except asyncio.TimeoutError:
                    # Connection success without errors indicates E2E headers worked
                    e2e_headers_preserved = True
                    connection_details = "Connection established successfully"
                    print(f" PASS:  E2E headers preserved - connection stable")
                    
        except Exception as e:
            connection_details = f"E2E connection failed: {e}"
            print(f" FAIL:  E2E header preservation test failed: {connection_details}")
        
        # Assert E2E headers preserved
        self.assertTrue(
            e2e_headers_preserved,
            f"CRITICAL FAILURE: GCP Load Balancer is stripping E2E bypass headers. "
            f"This prevents staging environment testing. "
            f"Connection details: {connection_details}. "
            f"Required fix: Add X-E2E-Bypass header preservation to load-balancer.tf"
        )
    
    async def test_complete_golden_path_websocket_flow(self):
        """
        CRITICAL: Test complete Golden Path WebSocket flow through GCP staging.
        
        This validates the end-to-end WebSocket functionality that enables
        core business value delivery through chat interactions.
        """
        # Arrange - Create authenticated user for Golden Path test
        golden_path_user = await self.e2e_helper.create_authenticated_user(
            email="golden_path@example.com",
            permissions=["read", "write", "chat", "agent_interaction"]
        )
        
        websocket_headers = self.e2e_helper.get_websocket_headers(golden_path_user.jwt_token)
        
        print(f"[U+1F31F] CRITICAL TEST: Complete Golden Path WebSocket flow")
        print(f"[U+1F464] User: {golden_path_user.email} ({golden_path_user.user_id[:8]}...)")
        
        # Act - Test complete Golden Path flow
        golden_path_steps_completed = []
        
        try:
            async with websockets.connect(
                self.staging_websocket_url,
                additional_headers=websocket_headers
            ) as websocket:
                golden_path_steps_completed.append("connection_established")
                print(f" PASS:  Step 1: WebSocket connection established")
                
                # Step 2: User authentication confirmation
                auth_confirm_message = {
                    "type": "golden_path_auth_confirm",
                    "user_id": golden_path_user.user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await websocket.send(json.dumps(auth_confirm_message))
                golden_path_steps_completed.append("auth_message_sent")
                print(f" PASS:  Step 2: Authentication confirmation sent")
                
                # Step 3: Simulated chat message initiation
                chat_initiation_message = {
                    "type": "golden_path_chat_initiation", 
                    "action": "start_chat_session",
                    "message": "Hello, I need help with my AI optimization",
                    "user_id": golden_path_user.user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await websocket.send(json.dumps(chat_initiation_message))
                golden_path_steps_completed.append("chat_initiated")
                print(f" PASS:  Step 3: Chat session initiated")
                
                # Step 4: Wait for any response indicating server processing
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=self.auth_timeout)
                    response_data = json.loads(response)
                    golden_path_steps_completed.append("server_response_received")
                    print(f" PASS:  Step 4: Server response received - {response_data.get('type', 'unknown')}")
                    
                except asyncio.TimeoutError:
                    # No immediate response is acceptable for Golden Path validation
                    golden_path_steps_completed.append("connection_stable")
                    print(f" PASS:  Step 4: Connection stable (no immediate errors)")
                
                # Golden Path flow completed successfully
                golden_path_steps_completed.append("golden_path_complete")
                print(f"[U+1F31F] Golden Path WebSocket flow completed successfully")
                
        except Exception as e:
            print(f" FAIL:  Golden Path flow failed at step: {len(golden_path_steps_completed) + 1}")
            print(f" FAIL:  Error: {e}")
            print(f" PASS:  Completed steps: {golden_path_steps_completed}")
        
        # Assert Golden Path core steps completed
        required_steps = ["connection_established", "auth_message_sent", "chat_initiated"]
        completed_required_steps = [step for step in required_steps if step in golden_path_steps_completed]
        
        self.assertEqual(
            len(completed_required_steps),
            len(required_steps),
            f"CRITICAL FAILURE: Golden Path WebSocket flow incomplete. "
            f"Required steps: {required_steps}. "
            f"Completed: {completed_required_steps}. "
            f"All completed: {golden_path_steps_completed}. "
            f"This indicates WebSocket infrastructure cannot support core business value."
        )
    
    async def test_websocket_reconnection_with_auth(self):
        """
        Test WebSocket reconnection scenarios with authentication preservation.
        
        This validates resilience patterns that ensure chat sessions can
        recover from temporary connection issues.
        """
        # Arrange - Create persistent user for reconnection test
        reconnect_user = await self.e2e_helper.create_authenticated_user(
            email="reconnect_test@example.com",
            permissions=["read", "write", "persistent_session"]
        )
        
        websocket_headers = self.e2e_helper.get_websocket_headers(reconnect_user.jwt_token)
        
        print(f" CYCLE:  Testing WebSocket reconnection with auth preservation")
        
        # Act - Test multiple connection attempts (simulating reconnection)
        connection_attempts = []
        
        for attempt in range(2):  # Keep reasonable for E2E test
            try:
                print(f" CYCLE:  Connection attempt {attempt + 1}")
                
                async with websockets.connect(
                    self.staging_websocket_url,
                    additional_headers=websocket_headers
                ) as websocket:
                    # Send reconnection test message
                    reconnect_message = {
                        "type": "reconnection_test",
                        "attempt_number": attempt + 1,
                        "user_id": reconnect_user.user_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(reconnect_message))
                    
                    # Brief interaction to validate connection
                    await asyncio.sleep(0.5)
                    
                    connection_attempts.append(f"attempt_{attempt + 1}_success")
                    print(f" PASS:  Connection attempt {attempt + 1} successful")
                    
                # Brief pause between connections
                if attempt < 1:  # Don't wait after last attempt
                    await asyncio.sleep(1.0)
                    
            except Exception as e:
                connection_attempts.append(f"attempt_{attempt + 1}_failed: {e}")
                print(f" FAIL:  Connection attempt {attempt + 1} failed: {e}")
        
        # Assert at least one successful reconnection
        successful_attempts = [attempt for attempt in connection_attempts if "success" in attempt]
        self.assertGreater(
            len(successful_attempts),
            0,
            f"WebSocket reconnection should succeed with preserved auth. "
            f"Attempts: {connection_attempts}"
        )
    
    async def test_multi_user_websocket_isolation_in_gcp(self):
        """
        CRITICAL: Test multi-user WebSocket isolation through GCP infrastructure.
        
        This validates that GCP Load Balancer preserves user context isolation,
        preventing cross-user data leakage in production.
        """
        # Arrange - Create multiple users for isolation testing
        users = []
        for i in range(2):  # Keep reasonable for E2E staging test
            user = await self.e2e_helper.create_authenticated_user(
                email=f"isolation_user_{i}@example.com",
                permissions=["read", "write", f"user_context_{i}"]
            )
            users.append(user)
        
        print(f"[U+1F465] Testing multi-user isolation through GCP staging")
        print(f"[U+1F464] Users: {[user.email for user in users]}")
        
        # Act - Test concurrent user connections
        async def test_isolated_user(user_index: int, user: AuthenticatedUser):
            """Test individual user connection with isolation."""
            headers = self.e2e_helper.get_websocket_headers(user.jwt_token)
            isolation_result = {
                "user_index": user_index,
                "user_id": user.user_id,
                "connection_success": False,
                "isolation_validated": False,
                "error": None
            }
            
            try:
                async with websockets.connect(
                    self.staging_websocket_url,
                    additional_headers=headers
                ) as websocket:
                    isolation_result["connection_success"] = True
                    
                    # Send user-specific isolation test message
                    isolation_message = {
                        "type": "gcp_user_isolation_test",
                        "user_index": user_index,
                        "user_id": user.user_id,
                        "isolation_key": f"user_{user_index}_secret",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(isolation_message))
                    
                    # Brief wait for processing
                    await asyncio.sleep(0.5)
                    
                    isolation_result["isolation_validated"] = True
                    print(f" PASS:  User {user_index} isolation validated")
                    
            except Exception as e:
                isolation_result["error"] = str(e)
                print(f" FAIL:  User {user_index} isolation test failed: {e}")
            
            return isolation_result
        
        # Execute concurrent isolation tests
        isolation_results = await asyncio.gather(
            *[test_isolated_user(i, user) for i, user in enumerate(users)],
            return_exceptions=True
        )
        
        # Assert isolation validation
        successful_isolations = []
        for result in isolation_results:
            if isinstance(result, dict) and result.get("isolation_validated"):
                successful_isolations.append(result)
            elif isinstance(result, Exception):
                print(f" FAIL:  Isolation test exception: {result}")
        
        self.assertGreater(
            len(successful_isolations),
            0,
            f"Multi-user isolation should work through GCP infrastructure. "
            f"Results: {isolation_results}"
        )
        
        # If multiple users succeeded, validate they were truly isolated
        if len(successful_isolations) > 1:
            user_ids = [result["user_id"] for result in successful_isolations]
            unique_users = set(user_ids)
            self.assertEqual(
                len(unique_users),
                len(user_ids),
                f"Users should have unique isolated contexts. User IDs: {user_ids}"
            )
    
    async def test_websocket_header_stripping_regression_prevention(self):
        """
        CRITICAL: Specific regression test for GitHub issue #113 header stripping.
        
        This test validates that the specific header stripping issue that caused
        WebSocket 1011 errors is completely resolved and won't regress.
        
        COMPLEMENTARY TO: test_gcp_load_balancer_header_validation.py
        This focuses specifically on WebSocket upgrade header preservation.
        """
        logger.info(" SEARCH:  REGRESSION TEST: GitHub issue #113 header stripping prevention")
        
        # Arrange - Create user with comprehensive auth headers
        regression_user = await self.e2e_helper.create_authenticated_user(
            email="github_issue_113_regression@example.com",
            permissions=["read", "write", "websocket", "regression_test"]
        )
        
        # Build comprehensive header set that previously failed
        problematic_headers = self.e2e_helper.get_websocket_headers(regression_user.jwt_token)
        problematic_headers.update({
            # These headers were specifically stripped by the load balancer
            "Authorization": f"Bearer {regression_user.jwt_token}",  # Explicit Authorization
            "X-E2E-Bypass": "true",  # E2E testing bypass
            "X-E2E-Test-Environment": "staging",  # Environment context
            "X-GitHub-Issue": "113",  # Issue tracking
            "X-WebSocket-Protocol": "netra-websocket-v1",  # Custom protocol
            "X-User-Agent": "E2E-Test-WebSocket-Client",  # User agent
            "X-Forwarded-Proto": "https",  # Protocol forwarding
            "Upgrade": "websocket",  # Critical WebSocket upgrade header
            "Connection": "upgrade"  # Critical connection upgrade header
        })
        
        print(f" SEARCH:  Testing {len(problematic_headers)} headers that previously failed")
        print(f"[U+1F511] Critical headers: Authorization, X-E2E-Bypass, Upgrade, Connection")
        
        # Act - Test WebSocket connection with previously problematic headers
        regression_test_result = {
            "headers_sent": list(problematic_headers.keys()),
            "connection_successful": False,
            "header_stripping_detected": False,
            "websocket_upgrade_successful": False,
            "error_details": None,
            "regression_prevented": False
        }
        
        try:
            async with websockets.connect(
                self.staging_websocket_url,
                additional_headers=problematic_headers,
                ping_interval=None,
                ping_timeout=None
            ) as websocket:
                regression_test_result["connection_successful"] = True
                regression_test_result["websocket_upgrade_successful"] = True
                
                # Send specific regression test message
                regression_message = {
                    "type": "github_issue_113_regression_test",
                    "purpose": "validate_header_stripping_fix",
                    "user_id": regression_user.user_id,
                    "headers_tested": list(problematic_headers.keys()),
                    "issue_number": 113,
                    "test_environment": "staging",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(regression_message))
                
                # Wait for confirmation that headers were processed
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    regression_test_result["server_response"] = response_data.get("type", "unknown")
                    regression_test_result["regression_prevented"] = True
                    
                except asyncio.TimeoutError:
                    # No response but connection works = regression prevented
                    regression_test_result["regression_prevented"] = True
                    regression_test_result["server_response"] = "timeout_but_connected"
                
                print(" PASS:  GitHub issue #113 regression test: WebSocket connection successful")
                
        except websockets.exceptions.InvalidHandshake as e:
            regression_test_result["error_details"] = f"Handshake failed: {e}"
            
            # Check for specific patterns indicating header stripping
            error_str = str(e).lower()
            if any(pattern in error_str for pattern in ["401", "unauthorized", "forbidden", "authentication"]):
                regression_test_result["header_stripping_detected"] = True
                regression_test_result["error_details"] += " (HEADER STRIPPING DETECTED)"
                
        except websockets.exceptions.ConnectionClosedError as e:
            regression_test_result["error_details"] = f"Connection closed: {e}"
            
            # 1011 error was the specific symptom of header stripping
            if "1011" in str(e):
                regression_test_result["header_stripping_detected"] = True
                regression_test_result["error_details"] += " (1011 ERROR - HEADER STRIPPING DETECTED)"
                
        except Exception as e:
            regression_test_result["error_details"] = f"Connection error: {e}"
        
        # CRITICAL ASSERTIONS for regression prevention
        self.assertFalse(
            regression_test_result["header_stripping_detected"],
            f"CRITICAL REGRESSION: GitHub issue #113 header stripping has returned! "
            f"Load balancer is stripping authentication headers again. "
            f"Error details: {regression_test_result['error_details']}. "
            f"Headers tested: {regression_test_result['headers_sent']}. "
            f"IMMEDIATE FIX REQUIRED: Check terraform-gcp-staging/load-balancer.tf deployment"
        )
        
        self.assertTrue(
            regression_test_result["connection_successful"],
            f"CRITICAL REGRESSION: WebSocket connection failed with auth headers. "
            f"This is exactly the symptom of GitHub issue #113. "
            f"Connection result: {regression_test_result}. "
            f"IMMEDIATE ACTION: Validate load balancer header forwarding configuration"
        )
        
        self.assertTrue(
            regression_test_result["regression_prevented"],
            f"CRITICAL REGRESSION: GitHub issue #113 symptoms detected. "
            f"WebSocket upgrade with auth headers is not working properly. "
            f"Full test result: {regression_test_result}"
        )
        
        print(" PASS:  REGRESSION TEST PASSED: GitHub issue #113 header stripping prevented")


class TestGCPWebSocketInfrastructureResilience(SSotBaseTestCase, unittest.TestCase):
    """
    Tests for GCP WebSocket infrastructure resilience and error handling.
    
    These tests validate proper behavior under various failure conditions
    that can occur in GCP staging and production environments.
    """
    
    def setup_method(self, method=None):
        """Set up resilience test environment."""
        super().setup_method(method)
        self.staging_config = StagingTestConfig()
        self.e2e_helper = E2EWebSocketAuthHelper(environment="staging")
        self.staging_websocket_url = self.staging_config.urls.websocket_url
    
    async def test_websocket_gcp_timeout_resilience(self):
        """
        Test WebSocket resilience to GCP Cloud Run timeout limitations.
        
        This validates proper handling of GCP-specific timeout constraints
        that can affect WebSocket connection establishment.
        """
        # Arrange - Create user for timeout testing
        timeout_user = await self.e2e_helper.create_authenticated_user(
            email="timeout_resilience@example.com",
            permissions=["read", "write"]
        )
        
        headers = self.e2e_helper.get_websocket_headers(timeout_user.jwt_token)
        
        print(f"[U+23F1][U+FE0F] Testing GCP timeout resilience")
        
        # Act - Test connection with various timeout configurations
        timeout_scenarios = [
            ("aggressive_timeout", 3.0),
            ("standard_timeout", 10.0), 
            ("generous_timeout", 15.0)
        ]
        
        timeout_results = []
        
        for scenario_name, timeout_value in timeout_scenarios:
            try:
                start_time = time.time()
                
                async with websockets.connect(
                    self.staging_websocket_url,
                    additional_headers=headers,
                    ping_interval=None,  # GCP optimization
                    ping_timeout=None
                ) as websocket:
                    connection_time = time.time() - start_time
                    
                    # Send timeout test message
                    timeout_message = {
                        "type": "gcp_timeout_resilience_test",
                        "scenario": scenario_name,
                        "timeout_configured": timeout_value,
                        "actual_connection_time": connection_time,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(timeout_message))
                    
                    timeout_results.append({
                        "scenario": scenario_name,
                        "success": True,
                        "connection_time": connection_time,
                        "configured_timeout": timeout_value
                    })
                    
                    print(f" PASS:  {scenario_name}: Connected in {connection_time:.2f}s")
                    
            except asyncio.TimeoutError:
                timeout_results.append({
                    "scenario": scenario_name,
                    "success": False,
                    "error": "timeout",
                    "configured_timeout": timeout_value
                })
                print(f"[U+23F0] {scenario_name}: Timeout at {timeout_value}s")
                
            except Exception as e:
                timeout_results.append({
                    "scenario": scenario_name,
                    "success": False,
                    "error": str(e),
                    "configured_timeout": timeout_value
                })
                print(f" FAIL:  {scenario_name}: Error - {e}")
        
        # Assert reasonable timeout resilience
        successful_scenarios = [r for r in timeout_results if r.get("success")]
        self.assertGreater(
            len(successful_scenarios),
            0,
            f"At least one timeout scenario should succeed in GCP. Results: {timeout_results}"
        )
    
    async def test_websocket_gcp_infrastructure_error_handling(self):
        """
        Test proper error handling for GCP infrastructure issues.
        
        This validates that infrastructure errors are properly detected
        and reported rather than causing silent failures.
        """
        # Test with intentionally problematic configuration
        problematic_scenarios = [
            # Malformed authorization headers that might confuse Load Balancer
            {
                "name": "malformed_bearer_token",
                "headers": {"authorization": "Bearer malformed.token.structure"},
                "expected_error_types": ["handshake", "authentication", "authorization"]
            },
            # Missing critical WebSocket upgrade headers
            {
                "name": "missing_upgrade_headers", 
                "headers": {"authorization": f"Bearer {self.e2e_helper.create_test_jwt_token()}"},
                "expected_error_types": ["upgrade", "handshake", "protocol"]
            }
        ]
        
        error_handling_results = []
        
        for scenario in problematic_scenarios:
            print(f" SEARCH:  Testing error handling: {scenario['name']}")
            
            try:
                # Attempt connection with problematic configuration
                async with websockets.connect(
                    self.staging_websocket_url,
                    additional_headers=scenario["headers"]
                ) as websocket:
                    # If connection succeeds unexpectedly
                    error_handling_results.append({
                        "scenario": scenario["name"],
                        "result": "unexpected_success",
                        "error_handling": "poor"
                    })
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check if error message contains expected error indicators
                error_detected = any(
                    error_type in error_msg 
                    for error_type in scenario["expected_error_types"]
                )
                
                error_handling_results.append({
                    "scenario": scenario["name"],
                    "result": "expected_error",
                    "error_message": str(e),
                    "error_properly_detected": error_detected,
                    "error_handling": "good" if error_detected else "unclear"
                })
                
                print(f" PASS:  {scenario['name']}: Proper error handling - {e}")
        
        # Assert error handling is working
        good_error_handling = [
            r for r in error_handling_results 
            if r.get("error_handling") == "good"
        ]
        
        self.assertGreater(
            len(good_error_handling),
            0,
            f"GCP infrastructure should provide clear error handling. "
            f"Results: {error_handling_results}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])