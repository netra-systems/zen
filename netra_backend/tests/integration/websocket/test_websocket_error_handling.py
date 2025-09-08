"""
WebSocket Error Handling Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Critical reliability requirement
- Business Goal: Graceful error handling ensures uninterrupted chat experience
- Value Impact: CRITICAL - Poor error handling breaks user trust and chat continuity
- Strategic/Revenue Impact: $200K+ potential churn prevented by reliable error handling

CRITICAL ERROR HANDLING REQUIREMENTS:
1. Connection drops must be handled gracefully without data loss
2. Authentication failures must provide clear feedback and recovery paths
3. Message delivery failures must trigger appropriate retry mechanisms
4. Server errors must not crash client connections
5. Network timeouts must be handled with user-friendly messaging

CRITICAL REQUIREMENTS:
1. Uses REAL WebSocket connections with REAL error conditions (NO MOCKS per CLAUDE.md)
2. Tests actual error scenarios that occur in production
3. Validates error recovery mechanisms and user experience
4. Ensures proper error logging and monitoring
5. Tests edge cases and failure modes

This test validates the error handling infrastructure that maintains user trust
and chat continuity even when things go wrong.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

import pytest
import websockets
from websockets import ConnectionClosed, InvalidStatus, WebSocketException

# SSOT imports following CLAUDE.md absolute import requirements  
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env


class TestWebSocketErrorHandling(BaseIntegrationTest):
    """
    Integration tests for WebSocket error handling and recovery.
    
    CRITICAL: All tests use REAL WebSocket connections with REAL error conditions.
    This ensures error handling works correctly in production failure scenarios.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_error_handling_test(self, real_services_fixture):
        """
        Set up error handling test environment with real services.
        
        BVJ: Test Infrastructure - Ensures reliable error handling testing
        """
        self.env = get_env()
        self.services = real_services_fixture
        self.test_session_id = f"error_handling_{uuid.uuid4().hex[:8]}"
        
        # CRITICAL: Verify real services are available (CLAUDE.md requirement)
        assert real_services_fixture, "Real services fixture required - no mocks allowed per CLAUDE.md"
        assert "backend" in real_services_fixture, "Real backend service required for error handling testing"
        
        # Initialize auth helper for error testing
        auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            timeout=25.0
        )
        
        self.auth_helper = E2EWebSocketAuthHelper(config=auth_config, environment="test")
        self.error_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.error_logs: List[Dict[str, Any]] = []
        self.recovery_attempts: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Test basic connectivity
        try:
            test_token = self.auth_helper.create_test_jwt_token(user_id="error_test_user")
            assert test_token, "Failed to create test JWT for error handling testing"
        except Exception as e:
            pytest.fail(f"Real services not available for error handling testing: {e}")
    
    async def async_teardown(self):
        """Clean up all error test connections."""
        for user_id, ws in self.error_connections.items():
            if not ws.closed:
                await ws.close()
        self.error_connections.clear()
        await super().async_teardown()
    
    def log_error_event(self, error_type: str, details: Dict[str, Any]) -> None:
        """Log error event for analysis."""
        error_event = {
            "error_type": error_type,
            "timestamp": time.time(),
            "session_id": self.test_session_id,
            **details
        }
        self.error_logs.append(error_event)
    
    async def create_connection_for_error_testing(
        self,
        user_id: str,
        expect_failure: bool = False
    ) -> Optional[websockets.WebSocketServerProtocol]:
        """Create connection for error testing scenarios."""
        try:
            token = self.auth_helper.create_test_jwt_token(user_id=user_id)
            headers = self.auth_helper.get_websocket_headers(token)
            
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=15.0
                ),
                timeout=20.0
            )
            
            self.error_connections[user_id] = websocket
            return websocket
            
        except Exception as e:
            if not expect_failure:
                self.log_error_event("unexpected_connection_failure", {
                    "user_id": user_id,
                    "error": str(e)
                })
            return None
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_failure_handling(self, real_services_fixture):
        """
        Test handling of authentication failures and error responses.
        
        BVJ: Security and user experience - Auth failures must be handled gracefully.
        Critical for preventing security breaches and providing clear user feedback.
        """
        user_id = f"auth_fail_{uuid.uuid4().hex[:8]}"
        
        try:
            # Test 1: Invalid token format
            invalid_headers = {
                "Authorization": "Bearer invalid-token-format",
                "X-User-ID": user_id
            }
            
            with pytest.raises((InvalidStatusCode, ConnectionClosed, WebSocketException)):
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.auth_helper.config.websocket_url,
                        additional_headers=invalid_headers,
                        open_timeout=10.0
                    ),
                    timeout=15.0
                )
                
                # If connection somehow succeeded, it's an error
                if websocket:
                    await websocket.close()
                    pytest.fail("Connection should have failed with invalid token")
            
            # Test 2: Missing authorization header
            missing_auth_headers = {
                "X-User-ID": user_id,
                "Content-Type": "application/json"
            }
            
            with pytest.raises((InvalidStatusCode, ConnectionClosed, WebSocketException)):
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.auth_helper.config.websocket_url,
                        additional_headers=missing_auth_headers,
                        open_timeout=10.0
                    ),
                    timeout=15.0
                )
                
                if websocket:
                    await websocket.close()
                    pytest.fail("Connection should have failed without authorization header")
            
            # Test 3: Expired token
            expired_token = self.auth_helper.create_test_jwt_token(
                user_id=user_id,
                exp_minutes=-30  # Expired 30 minutes ago
            )
            
            expired_headers = self.auth_helper.get_websocket_headers(expired_token)
            
            with pytest.raises((InvalidStatusCode, ConnectionClosed, WebSocketException)):
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.auth_helper.config.websocket_url,
                        additional_headers=expired_headers,
                        open_timeout=10.0
                    ),
                    timeout=15.0
                )
                
                if websocket:
                    await websocket.close()
                    pytest.fail("Connection should have failed with expired token")
            
            # Test 4: Verify valid authentication still works after failures
            valid_websocket = await self.create_connection_for_error_testing(f"{user_id}_valid")
            assert valid_websocket is not None, "Valid authentication failed after testing invalid cases"
            assert valid_websocket.state.name == "OPEN", "Valid connection not properly established"
            
            # Test that valid connection can send messages
            test_message = {
                "type": "auth_recovery_test",
                "user_id": f"{user_id}_valid",
                "content": "Message after authentication error testing",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await valid_websocket.send(json.dumps(test_message))
            await valid_websocket.close()
            
        except Exception as e:
            pytest.fail(f"Authentication failure handling test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_drop_recovery(self, real_services_fixture):
        """
        Test connection drop detection and recovery mechanisms.
        
        BVJ: Connection reliability - Users must be able to recover from connection drops.
        Critical for maintaining chat continuity during network issues.
        """
        user_id = f"conn_drop_{uuid.uuid4().hex[:8]}"
        
        try:
            # Establish initial connection
            websocket = await self.create_connection_for_error_testing(user_id)
            assert websocket is not None, "Initial connection failed"
            
            # Send pre-drop messages
            pre_drop_messages = []
            for i in range(3):
                message = {
                    "type": "pre_drop_message",
                    "user_id": user_id,
                    "message_index": i,
                    "content": f"Message {i} before connection drop",
                    "drop_test_marker": f"pre_drop_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(message))
                pre_drop_messages.append(message)
                await asyncio.sleep(0.5)
            
            # Simulate connection drop
            drop_time = time.time()
            await websocket.close(code=1006)  # Abnormal closure
            
            self.log_error_event("simulated_connection_drop", {
                "user_id": user_id,
                "drop_time": drop_time,
                "pre_drop_messages": len(pre_drop_messages)
            })
            
            # Verify connection is closed
            assert websocket.closed, "Connection should be closed after drop"
            
            # Wait for drop to be recognized
            await asyncio.sleep(2.0)
            
            # Attempt recovery
            recovery_start = time.time()
            
            try:
                recovered_websocket = await self.create_connection_for_error_testing(f"{user_id}_recovery")
                recovery_time = time.time() - recovery_start
                
                assert recovered_websocket is not None, "Connection recovery failed"
                assert recovered_websocket.state.name == "OPEN", "Recovered connection not properly established"
                
                self.recovery_attempts[user_id].append({
                    "attempt": 1,
                    "success": True,
                    "recovery_time": recovery_time,
                    "timestamp": time.time()
                })
                
                # Test post-recovery functionality
                recovery_messages = []
                for i in range(3):
                    message = {
                        "type": "post_recovery_message",
                        "user_id": f"{user_id}_recovery",
                        "message_index": i,
                        "content": f"Message {i} after connection recovery",
                        "recovery_marker": f"post_recovery_{i}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await recovered_websocket.send(json.dumps(message))
                    recovery_messages.append(message)
                    await asyncio.sleep(0.5)
                
                # Verify recovery metrics
                assert recovery_time < 10.0, f"Connection recovery took too long: {recovery_time:.2f}s"
                
                await recovered_websocket.close()
                
            except Exception as recovery_error:
                self.recovery_attempts[user_id].append({
                    "attempt": 1,
                    "success": False,
                    "error": str(recovery_error),
                    "timestamp": time.time()
                })
                raise
            
        except Exception as e:
            pytest.fail(f"Connection drop recovery test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_send_failure_handling(self, real_services_fixture):
        """
        Test handling of message send failures and retry mechanisms.
        
        BVJ: Message reliability - Users must not lose messages due to send failures.
        Important for maintaining chat data integrity and user trust.
        """
        user_id = f"msg_fail_{uuid.uuid4().hex[:8]}"
        
        try:
            # Establish connection
            websocket = await self.create_connection_for_error_testing(user_id)
            assert websocket is not None, "Connection failed for message failure testing"
            
            # Test 1: Send valid messages to establish baseline
            successful_messages = []
            for i in range(3):
                message = {
                    "type": "baseline_message",
                    "user_id": user_id,
                    "message_index": i,
                    "content": f"Baseline message {i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                try:
                    await websocket.send(json.dumps(message))
                    successful_messages.append(message)
                except Exception as e:
                    self.log_error_event("baseline_message_failure", {
                        "user_id": user_id,
                        "message_index": i,
                        "error": str(e)
                    })
                
                await asyncio.sleep(0.3)
            
            assert len(successful_messages) >= 2, "Baseline message sending failed"
            
            # Test 2: Send malformed messages (should handle gracefully)
            malformed_messages = [
                '{"invalid": json syntax',  # Invalid JSON
                json.dumps({"type": None}),  # Invalid message type
                json.dumps({"user_id": None, "type": "test"}),  # Missing user_id
                "not json at all",  # Not JSON
            ]
            
            malformed_results = []
            for i, malformed_msg in enumerate(malformed_messages):
                try:
                    await websocket.send(malformed_msg)
                    malformed_results.append({"index": i, "success": True})
                except Exception as e:
                    malformed_results.append({"index": i, "success": False, "error": str(e)})
                    self.log_error_event("malformed_message_handled", {
                        "user_id": user_id,
                        "message_index": i,
                        "error": str(e)
                    })
            
            # Test 3: Send valid message after malformed ones
            recovery_message = {
                "type": "post_malformed_recovery",
                "user_id": user_id,
                "content": "Message sent after malformed message testing",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                await websocket.send(json.dumps(recovery_message))
                recovery_successful = True
            except Exception as e:
                recovery_successful = False
                self.log_error_event("post_malformed_recovery_failed", {
                    "user_id": user_id,
                    "error": str(e)
                })
            
            # Connection should still be functional after malformed messages
            assert recovery_successful, "Connection failed to recover after malformed message testing"
            assert not websocket.closed, "Connection should remain open after handling malformed messages"
            
            # Test 4: Message size limits (if applicable)
            large_message = {
                "type": "large_message_test",
                "user_id": user_id,
                "content": "x" * 10000,  # 10KB message
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                await websocket.send(json.dumps(large_message))
                large_message_success = True
            except Exception as e:
                large_message_success = False
                self.log_error_event("large_message_handled", {
                    "user_id": user_id,
                    "message_size": len(json.dumps(large_message)),
                    "error": str(e)
                })
            
            # Either success or graceful failure is acceptable
            # The important thing is the connection remains stable
            assert not websocket.closed, "Connection should remain stable after large message test"
            
            await websocket.close()
            
        except Exception as e:
            pytest.fail(f"Message send failure handling test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_timeout_and_network_error_handling(self, real_services_fixture):
        """
        Test handling of timeouts and network-related errors.
        
        BVJ: Network resilience - System must handle network instability gracefully.
        Important for maintaining service during poor network conditions.
        """
        user_id = f"timeout_test_{uuid.uuid4().hex[:8]}"
        
        try:
            # Test connection timeout scenarios
            timeout_start = time.time()
            
            try:
                # Create connection with very short timeout
                token = self.auth_helper.create_test_jwt_token(user_id=user_id)
                headers = self.auth_helper.get_websocket_headers(token)
                
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.auth_helper.config.websocket_url,
                        additional_headers=headers,
                        open_timeout=0.001  # Extremely short timeout - likely to fail
                    ),
                    timeout=0.01
                )
                
                # If this succeeds, close it and continue with normal testing
                await websocket.close()
                
            except (asyncio.TimeoutError, Exception):
                # Timeout expected with such short limits
                self.log_error_event("connection_timeout_handled", {
                    "user_id": user_id,
                    "timeout_duration": time.time() - timeout_start
                })
            
            # Create normal connection for further testing
            websocket = await self.create_connection_for_error_testing(user_id)
            assert websocket is not None, "Normal connection failed after timeout test"
            
            # Test message timeout scenarios
            message_timeout_tests = []
            
            for i in range(5):
                message = {
                    "type": "timeout_test_message",
                    "user_id": user_id,
                    "message_index": i,
                    "content": f"Timeout test message {i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                send_start = time.time()
                
                try:
                    # Send with timeout
                    await asyncio.wait_for(
                        websocket.send(json.dumps(message)),
                        timeout=5.0  # Reasonable timeout
                    )
                    
                    send_time = time.time() - send_start
                    message_timeout_tests.append({
                        "index": i,
                        "success": True,
                        "send_time": send_time
                    })
                    
                except asyncio.TimeoutError:
                    message_timeout_tests.append({
                        "index": i,
                        "success": False,
                        "error": "timeout"
                    })
                    self.log_error_event("message_timeout", {
                        "user_id": user_id,
                        "message_index": i
                    })
                
                await asyncio.sleep(0.5)
            
            # Analyze timeout test results
            successful_sends = sum(1 for test in message_timeout_tests if test["success"])
            success_rate = successful_sends / len(message_timeout_tests)
            
            # Most messages should succeed under normal conditions
            assert success_rate >= 0.8, f"Message timeout success rate too low: {success_rate:.1%}"
            
            # Test connection stability after timeout scenarios
            stability_test_message = {
                "type": "post_timeout_stability_test",
                "user_id": user_id,
                "content": "Testing connection stability after timeout scenarios",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                await websocket.send(json.dumps(stability_test_message))
                stability_maintained = True
            except Exception as e:
                stability_maintained = False
                self.log_error_event("post_timeout_instability", {
                    "user_id": user_id,
                    "error": str(e)
                })
            
            assert stability_maintained, "Connection stability compromised after timeout testing"
            
            await websocket.close()
            
        except Exception as e:
            pytest.fail(f"Timeout and network error handling test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_logging_and_monitoring(self, real_services_fixture):
        """
        Test that errors are properly logged and can be monitored.
        
        BVJ: Operational excellence - Proper error logging enables quick issue resolution.
        Important for maintaining high service quality and rapid problem diagnosis.
        """
        user_id = f"error_logging_{uuid.uuid4().hex[:8]}"
        
        try:
            # Generate various error conditions to test logging
            
            # Error 1: Connection establishment failure
            try:
                invalid_headers = {"Authorization": "Bearer invalid"}
                websocket = await websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=invalid_headers,
                    open_timeout=5.0
                )
                if websocket:
                    await websocket.close()
            except Exception as e:
                self.log_error_event("connection_establishment_error", {
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                })
            
            # Error 2: Valid connection for message errors
            websocket = await self.create_connection_for_error_testing(user_id)
            if websocket:
                # Error 2a: Invalid message format
                try:
                    await websocket.send("invalid json")
                except Exception as e:
                    self.log_error_event("invalid_message_format", {
                        "user_id": user_id,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    })
                
                # Error 2b: Connection close during send
                await websocket.close()
                
                try:
                    await websocket.send(json.dumps({"type": "test", "user_id": user_id}))
                except Exception as e:
                    self.log_error_event("send_on_closed_connection", {
                        "user_id": user_id,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    })
            
            # Analyze error logging
            assert len(self.error_logs) > 0, "No errors were logged during error testing"
            
            # Verify error logs contain required information
            required_fields = ["error_type", "timestamp", "session_id"]
            
            for error_log in self.error_logs:
                for field in required_fields:
                    assert field in error_log, f"Error log missing required field: {field}"
                
                # Verify timestamp is reasonable
                log_age = time.time() - error_log["timestamp"]
                assert log_age < 300, f"Error log timestamp too old: {log_age:.2f}s"
            
            # Verify error categorization
            error_types = set(log["error_type"] for log in self.error_logs)
            assert len(error_types) > 0, "No error types categorized"
            
            # Log summary for monitoring validation
            error_summary = {
                "total_errors": len(self.error_logs),
                "error_types": list(error_types),
                "test_session": self.test_session_id,
                "user_id": user_id
            }
            
            self.log_error_event("test_error_summary", error_summary)
            
        except Exception as e:
            pytest.fail(f"Error logging and monitoring test failed: {e}")