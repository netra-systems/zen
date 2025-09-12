"""
E2E Tests for ToolRegistry Duplicate Registration Prevention in Staging

This module contains E2E tests that reproduce the exact "modelmetaclass already registered" 
failure from staging environment and validate fixes.

CRITICAL REQUIREMENTS:
- Tests MUST use real authentication (JWT/OAuth) as per CLAUDE.md
- Tests MUST fail in current broken state, pass after fix
- Tests MUST use real WebSocket connections to staging
- Tests MUST detect 0-second execution as failure

Business Value:
- Prevents complete chat functionality breakdown in staging
- Catches ToolRegistry duplicate registration issues in real environment
- Validates WebSocket supervisor creation with proper tool isolation

See: /Users/rindhujajohnson/Netra/GitHub/netra-apex/audit/staging/auto-solve-loop/toolregistry-duplicate-registration-20250109.md
"""

import asyncio
import json
import logging
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any

import websockets
from websockets.exceptions import ConnectionClosedError

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.base_test_case import SSotBaseTestCase
from tests.e2e.staging_config import StagingTestConfig

logger = logging.getLogger(__name__)


class ToolRegistryAuditCapture:
    """Helper to capture and analyze tool registry events during test execution."""
    
    def __init__(self):
        self.registered_tools: Set[str] = set()
        self.registration_attempts: List[Dict[str, Any]] = []
        self.duplicate_attempts: List[str] = []
        self.start_time = time.time()
        
    def record_registration_attempt(self, tool_name: str, success: bool, error: Optional[str] = None):
        """Record a tool registration attempt."""
        attempt = {
            'tool_name': tool_name,
            'timestamp': time.time() - self.start_time,
            'success': success,
            'error': error
        }
        self.registration_attempts.append(attempt)
        
        if success:
            if tool_name in self.registered_tools:
                self.duplicate_attempts.append(tool_name)
            else:
                self.registered_tools.add(tool_name)
        elif error and "already registered" in error:
            self.duplicate_attempts.append(tool_name)
            
    def has_modelmetaclass_registration(self) -> bool:
        """Check if modelmetaclass was registered (the critical error)."""
        return "modelmetaclass" in self.registered_tools or any(
            "modelmetaclass" in attempt['tool_name'] for attempt in self.registration_attempts
        )
        
    def has_duplicate_registrations(self) -> bool:
        """Check if any duplicate registrations were attempted."""
        return len(self.duplicate_attempts) > 0
        
    def get_analysis_report(self) -> Dict[str, Any]:
        """Get comprehensive analysis report."""
        return {
            'total_registrations': len(self.registration_attempts),
            'successful_registrations': len(self.registered_tools),
            'duplicate_attempts': len(self.duplicate_attempts),
            'modelmetaclass_detected': self.has_modelmetaclass_registration(),
            'tools_registered': list(self.registered_tools),
            'duplicate_tools': self.duplicate_attempts,
            'registration_timeline': self.registration_attempts
        }


@pytest.mark.e2e
@pytest.mark.staging
@pytest.mark.toolregistry
class TestToolRegistryDuplicatePreventionStaging(SSotBaseTestCase):
    """
    E2E tests for ToolRegistry duplicate registration prevention in staging environment.
    
    These tests reproduce the exact staging failure scenario and validate fixes.
    CRITICAL: Tests are designed to FAIL in current state, PASS after fix.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up class-level fixtures for staging tests."""
        super().setup_class()
        cls.staging_config = StagingTestConfig()
        cls.auth_helper = E2EAuthHelper(environment="staging")
        cls.ws_auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
        # Track test execution timing to ensure real execution
        cls.test_start_times = {}
        
    def setup_method(self, method):
        """Set up method-level fixtures."""
        super().setup_method(method)
        self.test_start_times[method.__name__] = time.time()
        self.audit_capture = ToolRegistryAuditCapture()
        
        # Log test initialization
        logger.info(f"[U+1F9EA] Starting E2E staging test: {method.__name__}")
        logger.info(f" TARGET:  Staging config: {self.staging_config.urls.backend_url}")
        
    def teardown_method(self, method):
        """Validate test execution and cleanup."""
        super().teardown_method(method)
        
        # CRITICAL: Validate test actually executed (not 0-second execution)
        execution_time = time.time() - self.test_start_times.get(method.__name__, time.time())
        if execution_time < 0.1:  # Less than 100ms indicates test was skipped/mocked
            pytest.fail(f" ALERT:  CRITICAL FAILURE: E2E test {method.__name__} executed in {execution_time:.3f}s. "
                      f"This indicates the test was skipped, mocked, or not actually connecting to real services. "
                      f"E2E tests MUST take meaningful time to connect to staging services.")
        
        # Log test completion with audit results
        logger.info(f" PASS:  Completed E2E staging test: {method.__name__} ({execution_time:.3f}s)")
        if hasattr(self, 'audit_capture'):
            audit_report = self.audit_capture.get_analysis_report()
            logger.info(f" CHART:  Tool registry audit: {audit_report}")
            
    async def test_websocket_supervisor_creation_prevents_duplicates(self):
        """
        E2E test that reproduces the exact staging failure scenario.
        
        CRITICAL: This test MUST fail in current state with "modelmetaclass already registered" error.
        After fix, it should pass without duplicate registration errors.
        
        Test Flow:
        1. User connects to staging WebSocket (authenticated)
        2. Supervisor factory creates WebSocket-scoped supervisor
        3. Tool registration happens during supervisor creation
        4. Second connection from same user should not cause duplicates
        5. Audit tool registrations to catch "modelmetaclass" issue
        
        Expected Failure (Current State):
        - WebSocket context validation failed: modelmetaclass already registered
        - TimeoutError during supervisor creation
        - 400 errors in agent message handling
        
        Expected Success (After Fix):
        - WebSocket connections succeed without duplicate registration errors
        - No "modelmetaclass" registration attempts detected
        - Multiple connections work without conflicts
        """
        logger.info("[U+1F680] Testing WebSocket supervisor creation duplicate prevention in staging")
        
        try:
            # Step 1: Get staging authentication token with E2E detection
            logger.info("[U+1F510] Getting staging authentication token...")
            token = await self.ws_auth_helper.get_staging_token_async()
            assert token, "Failed to get staging authentication token"
            logger.info(" PASS:  Got staging token for E2E WebSocket test")
            
            # Step 2: Connect to staging WebSocket with auth and E2E headers
            logger.info("[U+1F50C] Connecting to staging WebSocket...")
            logger.info(f" TARGET:  WebSocket URL: {self.ws_auth_helper.config.websocket_url}")
            
            # CRITICAL: This connection attempt will reproduce the staging failure
            websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=20.0)
            logger.info(" PASS:  Initial WebSocket connection successful")
            
            # Step 3: Send test message to trigger supervisor creation
            test_message = {
                "type": "agent_request",
                "agent": "test_agent",  # Minimal agent to trigger tool registration
                "message": "Test supervisor creation",
                "user_id": self._extract_user_id_from_token(token)
            }
            
            logger.info("[U+1F4E4] Sending test message to trigger supervisor creation...")
            await websocket.send(json.dumps(test_message))
            
            # Step 4: Wait for response and capture any registration errors
            try:
                response_raw = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                response = json.loads(response_raw)
                logger.info(f"[U+1F4E5] Received response: {response.get('type', 'unknown')}")
                
                # Check if response contains registration errors
                if response.get("type") == "error":
                    error_message = response.get("message", "")
                    if "modelmetaclass already registered" in error_message:
                        self.audit_capture.record_registration_attempt(
                            "modelmetaclass", False, error_message
                        )
                        logger.error(f" ALERT:  DETECTED: modelmetaclass duplicate registration error: {error_message}")
                        # This is the expected failure - the test should fail here in current state
                        pytest.fail(f"REPRODUCED STAGING BUG: {error_message}")
                    elif "already registered" in error_message:
                        logger.error(f" ALERT:  DETECTED: General duplicate registration error: {error_message}")
                        pytest.fail(f"Duplicate registration error detected: {error_message}")
                        
            except asyncio.TimeoutError:
                # Timeout might indicate the supervisor creation is stuck due to registration error
                logger.error("[U+23F0] TIMEOUT: WebSocket response timed out - may indicate supervisor creation failure")
                pytest.fail("WebSocket supervisor creation timed out - likely due to tool registration conflict")
                
            # Step 5: Test second connection to check for cross-connection conflicts
            logger.info(" CYCLE:  Testing second WebSocket connection...")
            try:
                websocket2 = await self.ws_auth_helper.connect_authenticated_websocket(timeout=15.0)
                logger.info(" PASS:  Second WebSocket connection successful")
                
                # Send test message on second connection
                await websocket2.send(json.dumps(test_message))
                response2_raw = await asyncio.wait_for(websocket2.recv(), timeout=10.0)
                response2 = json.loads(response2_raw)
                
                if response2.get("type") == "error" and "already registered" in response2.get("message", ""):
                    logger.error(f" ALERT:  DETECTED: Cross-connection registration conflict")
                    pytest.fail(f"Cross-connection duplicate registration: {response2.get('message')}")
                
                await websocket2.close()
                
            except Exception as e:
                logger.error(f" FAIL:  Second connection failed: {e}")
                # This might be the expected behavior in broken state
                if "already registered" in str(e) or "modelmetaclass" in str(e):
                    pytest.fail(f"REPRODUCED: Cross-connection duplicate registration error: {e}")
                
            await websocket.close()
            
            # Step 6: Validate audit results
            audit_report = self.audit_capture.get_analysis_report()
            logger.info(f" CHART:  Final audit report: {audit_report}")
            
            # CRITICAL: If we reach here without failures, the bug might be fixed
            if audit_report['modelmetaclass_detected']:
                pytest.fail("modelmetaclass registration detected in audit - bug still present")
            if audit_report['duplicate_attempts']:
                pytest.fail(f"Duplicate registration attempts detected: {audit_report['duplicate_tools']}")
                
            logger.info(" PASS:  Test completed successfully - no duplicate registration issues detected")
            
        except ConnectionClosedError as e:
            logger.error(f" FAIL:  WebSocket connection closed unexpectedly: {e}")
            # Check if error message indicates registration issue
            if hasattr(e, 'reason') and e.reason:
                if "already registered" in str(e.reason) or "modelmetaclass" in str(e.reason):
                    pytest.fail(f"REPRODUCED: WebSocket closed due to registration error: {e.reason}")
            raise
        except Exception as e:
            logger.error(f" FAIL:  Unexpected error in staging WebSocket test: {e}")
            # Check if error indicates the staging bug
            if "modelmetaclass already registered" in str(e):
                pytest.fail(f"REPRODUCED STAGING BUG: {e}")
            raise
            
    async def test_multi_user_concurrent_websocket_tool_registration(self):
        """
        Test multiple users connecting simultaneously to staging WebSocket.
        Should catch race conditions in tool registration.
        
        CRITICAL: Uses real auth, real WebSocket connections to staging.
        This test validates multi-user isolation and concurrent access patterns.
        """
        logger.info("[U+1F680] Testing multi-user concurrent WebSocket tool registration in staging")
        
        # Create multiple user contexts
        user_contexts = []
        for i in range(3):  # Test with 3 concurrent users
            user_email = f"e2e_concurrent_user_{i}_{int(time.time())}@staging.test"
            auth_helper = E2EWebSocketAuthHelper(environment="staging")
            token = await auth_helper.get_staging_token_async(email=user_email)
            user_contexts.append({
                'user_id': f"concurrent_user_{i}",
                'email': user_email,
                'token': token,
                'auth_helper': auth_helper
            })
        
        logger.info(f"[U+1F465] Created {len(user_contexts)} concurrent user contexts")
        
        # Define concurrent connection task
        async def connect_user(user_ctx: dict, user_index: int):
            """Connect a single user and test tool registration."""
            try:
                logger.info(f"[U+1F50C] User {user_index} connecting...")
                websocket = await user_ctx['auth_helper'].connect_authenticated_websocket(timeout=15.0)
                
                # Send test message to trigger tool registration
                test_message = {
                    "type": "agent_request",
                    "agent": "test_agent",
                    "message": f"Concurrent test from user {user_index}",
                    "user_id": user_ctx['user_id']
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response_raw = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response = json.loads(response_raw)
                
                logger.info(f" PASS:  User {user_index} got response: {response.get('type')}")
                
                # Check for registration errors
                if response.get("type") == "error":
                    error_msg = response.get("message", "")
                    if "already registered" in error_msg or "modelmetaclass" in error_msg:
                        return {
                            'user_index': user_index,
                            'success': False, 
                            'error': error_msg,
                            'registration_conflict': True
                        }
                
                await websocket.close()
                return {
                    'user_index': user_index,
                    'success': True,
                    'error': None,
                    'registration_conflict': False
                }
                
            except Exception as e:
                logger.error(f" FAIL:  User {user_index} failed: {e}")
                return {
                    'user_index': user_index,
                    'success': False,
                    'error': str(e),
                    'registration_conflict': "already registered" in str(e) or "modelmetaclass" in str(e)
                }
        
        # Execute concurrent connections
        logger.info(" LIGHTNING:  Executing concurrent WebSocket connections...")
        start_time = time.time()
        
        tasks = [connect_user(ctx, i) for i, ctx in enumerate(user_contexts)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        execution_time = time.time() - start_time
        logger.info(f"[U+23F1][U+FE0F] Concurrent connections completed in {execution_time:.3f}s")
        
        # Analyze results
        successful_connections = 0
        registration_conflicts = 0
        errors = []
        
        for result in results:
            if isinstance(result, Exception):
                errors.append(f"Exception: {result}")
                if "already registered" in str(result) or "modelmetaclass" in str(result):
                    registration_conflicts += 1
            elif isinstance(result, dict):
                if result['success']:
                    successful_connections += 1
                else:
                    errors.append(f"User {result['user_index']}: {result['error']}")
                    if result.get('registration_conflict'):
                        registration_conflicts += 1
        
        # Log analysis
        logger.info(f" CHART:  Concurrent test results:")
        logger.info(f"    PASS:  Successful connections: {successful_connections}/{len(user_contexts)}")
        logger.info(f"    FAIL:  Registration conflicts: {registration_conflicts}")
        logger.info(f"    ALERT:  Total errors: {len(errors)}")
        
        # CRITICAL: Detect if we reproduced the staging issue
        if registration_conflicts > 0:
            conflict_errors = [err for err in errors if "already registered" in err or "modelmetaclass" in err]
            logger.error(f" ALERT:  REPRODUCED: Multi-user registration conflicts detected")
            pytest.fail(f"REPRODUCED STAGING BUG: Multi-user tool registration conflicts: {conflict_errors}")
        
        # Validate at least some connections succeeded (test effectiveness)
        if successful_connections == 0:
            pytest.fail(f"No connections succeeded - test may not be working properly. Errors: {errors}")
            
        logger.info(" PASS:  Multi-user concurrent test completed successfully")
        
    async def test_basemodel_exclusion_in_staging(self):
        """
        Verify that BaseModel classes are NOT registered as tools in staging.
        Should catch the "modelmetaclass" registration attempt.
        
        This test connects to staging and analyzes the actual tool registration
        process to detect if BaseModel classes are being treated as tools.
        """
        logger.info("[U+1F680] Testing BaseModel exclusion in staging tool registration")
        
        # Get staging token and connect
        token = await self.ws_auth_helper.get_staging_token_async()
        websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=15.0)
        
        # Send a message that would trigger tool discovery and registration
        # Use a special test message that requests tool introspection
        introspection_message = {
            "type": "tool_introspection_request",
            "message": "Request tool registry analysis",
            "user_id": self._extract_user_id_from_token(token),
            "include_registry_state": True
        }
        
        logger.info(" SEARCH:  Sending tool introspection request...")
        await websocket.send(json.dumps(introspection_message))
        
        try:
            # Wait for response with tool registry information
            response_raw = await asyncio.wait_for(websocket.recv(), timeout=15.0)
            response = json.loads(response_raw)
            
            logger.info(f"[U+1F4E5] Received introspection response: {response.get('type')}")
            
            # Check if response contains error about BaseModel registration
            if response.get("type") == "error":
                error_message = response.get("message", "")
                
                # CRITICAL: Check for the specific "modelmetaclass" error
                if "modelmetaclass already registered" in error_message:
                    self.audit_capture.record_registration_attempt(
                        "modelmetaclass", False, error_message
                    )
                    logger.error(" ALERT:  DETECTED: modelmetaclass registration attempt (BaseModel being treated as tool)")
                    pytest.fail(f"REPRODUCED STAGING BUG: BaseModel class registered as tool - {error_message}")
                
                # Check for other BaseModel-related registration issues
                basemodel_indicators = [
                    "modelmetaclass",
                    "basemodel", 
                    "pydantic",
                    "__class__.__name__.lower()"
                ]
                
                for indicator in basemodel_indicators:
                    if indicator in error_message.lower():
                        logger.error(f" ALERT:  DETECTED: BaseModel indicator '{indicator}' in error message")
                        pytest.fail(f"BaseModel registration issue detected: {error_message}")
            
            # If we got a successful response, analyze the registered tools
            elif response.get("type") == "tool_registry_state":
                registered_tools = response.get("registered_tools", [])
                
                logger.info(f"[U+1F527] Found {len(registered_tools)} registered tools")
                
                # Check for suspicious tool names that indicate BaseModel registration
                suspicious_tools = []
                for tool_name in registered_tools:
                    tool_name_lower = tool_name.lower()
                    if any(indicator in tool_name_lower for indicator in ["modelmetaclass", "basemodel", "pydantic"]):
                        suspicious_tools.append(tool_name)
                        
                if suspicious_tools:
                    logger.error(f" ALERT:  DETECTED: Suspicious tool names indicating BaseModel registration: {suspicious_tools}")
                    pytest.fail(f"BaseModel classes registered as tools: {suspicious_tools}")
            
            await websocket.close()
            
            # Final audit analysis
            audit_report = self.audit_capture.get_analysis_report()
            if audit_report['modelmetaclass_detected']:
                pytest.fail("modelmetaclass registration detected - BaseModel exclusion failed")
                
            logger.info(" PASS:  BaseModel exclusion test completed - no BaseModel classes registered as tools")
            
        except asyncio.TimeoutError:
            logger.error("[U+23F0] Tool introspection request timed out")
            # Timeout might indicate the system is stuck due to registration issues
            pytest.fail("Tool introspection timed out - may indicate BaseModel registration blocking the system")
            
    def _extract_user_id_from_token(self, token: str) -> str:
        """Extract user ID from JWT token for test messages."""
        try:
            import jwt
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded.get("sub", "unknown-user")
        except Exception:
            return "test-user-staging"
            
    def _capture_websocket_errors(self, websocket, duration: float = 5.0) -> List[str]:
        """Capture WebSocket errors for a specified duration."""
        # This would be implemented to monitor WebSocket for error messages
        # For now, return empty list as placeholder
        return []


@pytest.mark.e2e
@pytest.mark.staging 
@pytest.mark.mission_critical
class TestWebSocketToolRegistryCleanup(SSotBaseTestCase):
    """
    Mission critical tests for WebSocket connection cleanup and tool registry lifecycle.
    
    These tests validate that tool registries are properly cleaned up when WebSocket
    connections are closed, preventing resource leaks and cross-connection pollution.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up class-level fixtures."""
        super().setup_class()
        cls.ws_auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
    async def test_websocket_disconnect_registry_cleanup(self):
        """
        Test that tool registries are cleaned up when WebSocket disconnects.
        Should catch resource leak scenarios that lead to duplicate registration.
        
        CRITICAL: This test validates proper lifecycle management.
        """
        logger.info("[U+1F680] Testing WebSocket disconnect registry cleanup")
        
        # Step 1: Connect and trigger tool registration
        token = await self.ws_auth_helper.get_staging_token_async()
        websocket = await self.ws_auth_helper.connect_authenticated_websocket()
        
        test_message = {
            "type": "agent_request", 
            "agent": "cleanup_test_agent",
            "message": "Test registry lifecycle",
            "user_id": self._extract_user_id_from_token(token)
        }
        
        await websocket.send(json.dumps(test_message))
        
        # Wait for initial response
        try:
            response_raw = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            logger.info(" PASS:  Initial connection and tool registration successful")
        except asyncio.TimeoutError:
            logger.warning(" WARNING: [U+FE0F] Initial response timed out - continuing with cleanup test")
        
        # Step 2: Close connection explicitly
        await websocket.close()
        logger.info("[U+1F50C] Closed WebSocket connection")
        
        # Step 3: Wait a moment for cleanup to occur
        await asyncio.sleep(2.0)
        
        # Step 4: Connect again and verify no duplicate registration errors
        logger.info(" CYCLE:  Reconnecting to test cleanup effectiveness...")
        websocket2 = await self.ws_auth_helper.connect_authenticated_websocket()
        
        # Send same message - should not cause duplicate registration
        await websocket2.send(json.dumps(test_message))
        
        try:
            response2_raw = await asyncio.wait_for(websocket2.recv(), timeout=10.0)
            response2 = json.loads(response2_raw)
            
            # Check for registration errors
            if response2.get("type") == "error":
                error_msg = response2.get("message", "")
                if "already registered" in error_msg or "modelmetaclass" in error_msg:
                    pytest.fail(f"Registry cleanup failed - duplicate registration after reconnection: {error_msg}")
                    
            logger.info(" PASS:  Reconnection successful - no duplicate registration errors")
            
        except asyncio.TimeoutError:
            pytest.fail("Reconnection timed out - registry cleanup may have failed")
            
        finally:
            await websocket2.close()
            
    def _extract_user_id_from_token(self, token: str) -> str:
        """Extract user ID from JWT token."""
        try:
            import jwt
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded.get("sub", "unknown-user")
        except Exception:
            return "test-user-cleanup"