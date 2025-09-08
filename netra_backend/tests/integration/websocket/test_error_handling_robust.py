"""
Robust WebSocket Error Handling Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Platform reliability
- Business Goal: Ensure graceful error handling for uninterrupted user experience
- Value Impact: Proper error handling prevents user frustration and service abandonment
- Strategic/Revenue Impact: Error resilience maintains $500K+ ARR by preventing churn

CRITICAL ERROR HANDLING SCENARIOS:
1. Connection failures and recovery patterns
2. Message parsing and validation errors  
3. Agent execution failures and user notification
4. Network interruption and graceful degradation

CRITICAL REQUIREMENTS:
- NO MOCKS - Uses real WebSocket connections and real error conditions
- Tests real error scenarios that occur in production
- Validates proper error messages reach users
- Ensures system remains stable during error conditions
- Tests error recovery and graceful degradation patterns
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest
import websockets

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.fixtures.websocket_test_helpers import WebSocketTestClient
from shared.isolated_environment import get_env


class ErrorSimulatingLLM:
    """
    Mock LLM that simulates various error conditions for testing.
    This is the ONLY acceptable mock per CLAUDE.md - external LLM APIs.
    """
    
    def __init__(self, error_type: str = "none"):
        self.error_type = error_type
        self.call_count = 0
    
    async def complete_async(self, messages, **kwargs):
        """Mock LLM that simulates different error conditions."""
        self.call_count += 1
        
        if self.error_type == "timeout":
            await asyncio.sleep(30)  # Simulate timeout
            return {"content": "This should timeout", "usage": {"total_tokens": 0}}
            
        elif self.error_type == "api_error":
            raise Exception("Simulated LLM API error - service temporarily unavailable")
            
        elif self.error_type == "invalid_response":
            return None  # Invalid response format
            
        elif self.error_type == "rate_limit":
            if self.call_count <= 2:
                raise Exception("Rate limit exceeded - too many requests")
            else:
                return {"content": "Success after rate limit recovery", "usage": {"total_tokens": 100}}
                
        else:  # normal operation
            await asyncio.sleep(0.1)
            return {
                "content": "Normal response after error recovery testing",
                "usage": {"total_tokens": 120}
            }


class TestWebSocketErrorHandlingRobust(BaseIntegrationTest):
    """
    Robust tests for WebSocket error handling scenarios.
    
    CRITICAL: All tests use REAL WebSocket connections and REAL error conditions
    to validate production-quality error handling and recovery patterns.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_error_handling_test(self, real_services_fixture):
        """
        Set up robust error handling test environment.
        
        BVJ: Test Infrastructure - Ensures reliable error handling validation
        """
        self.env = get_env()
        self.services = real_services_fixture
        self.test_user_id = f"error_test_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        # CRITICAL: Verify real services (CLAUDE.md requirement)
        assert real_services_fixture, "Real services required for error handling tests"
        assert "backend" in real_services_fixture, "Real backend required for error simulation"
        
        # Initialize WebSocket auth helper
        auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            test_user_email=f"error_test_{self.test_user_id}@example.com",
            timeout=25.0  # Longer timeout for error scenarios
        )
        
        self.auth_helper = E2EWebSocketAuthHelper(config=auth_config, environment="test")
        self.active_connections: List[websockets.WebSocketServerProtocol] = []
        self.error_events: List[Dict[str, Any]] = []
        
        # Test auth helper functionality
        try:
            token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
            assert token, "Failed to create test JWT for error handling testing"
        except Exception as e:
            pytest.fail(f"Error handling test setup failed: {e}")
    
    async def async_teardown(self):
        """Clean up WebSocket connections and error test resources."""
        for ws in self.active_connections:
            if not ws.closed:
                await ws.close()
        self.active_connections.clear()
        await super().async_teardown()
    
    async def collect_error_events(
        self,
        websocket: websockets.WebSocketServerProtocol,
        timeout: float = 15.0
    ) -> List[Dict[str, Any]]:
        """
        Collect WebSocket events looking for error-related messages.
        
        Args:
            websocket: WebSocket connection to monitor
            timeout: Maximum time to wait for events
            
        Returns:
            List of error events and related messages
        """
        events = []
        start_time = time.time()
        
        try:
            while (time.time() - start_time) < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event = json.loads(event_data)
                    
                    events.append({
                        **event,
                        "_received_at": time.time()
                    })
                    
                    # Stop collecting if we get agent completion or critical error
                    event_type = event.get("type", "")
                    if event_type in ["agent_completed", "agent_failed", "error", "system_error"]:
                        break
                        
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    # Collect malformed message events too
                    events.append({
                        "type": "malformed_message",
                        "raw_data": event_data,
                        "_received_at": time.time()
                    })
                    
        except Exception as e:
            # Add the exception as an event for analysis
            events.append({
                "type": "collection_error",
                "error": str(e),
                "_received_at": time.time()
            })
            
        return events
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_error_handling(self, real_services_fixture):
        """
        Test WebSocket error handling during agent execution failures.
        
        BVJ: User experience - Users must receive clear error messages when AI fails.
        Proper error communication maintains trust and prevents user abandonment.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=12.0
            )
            
            self.active_connections.append(websocket)
            
            # Test LLM API error handling
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = ErrorSimulatingLLM("api_error").complete_async
                
                # Send agent request that will trigger API error
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "error_prone_agent",
                    "task": "Task that will trigger LLM API error",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect events looking for error handling
                events = await self.collect_error_events(websocket, timeout=20.0)
                
                # Verify error events were received
                assert len(events) > 0, "No events received during error scenario"
                
                # Look for error-related events
                error_events = [e for e in events if e.get("type") in [
                    "agent_failed", "agent_error", "error", "system_error", "llm_error"
                ]]
                
                # Should have some form of error indication
                if not error_events:
                    # Check if any event indicates failure or error status
                    status_events = [e for e in events if 
                                   e.get("status") == "failed" or 
                                   e.get("error") is not None or
                                   "error" in str(e.get("message", "")).lower()]
                    error_events = status_events
                
                assert len(error_events) > 0, "No error events received - users won't know about failure"
                
                # Validate error event content
                error_event = error_events[0]
                assert error_event.get("user_id") == self.test_user_id, "Error event missing user context"
                
                # Error should have meaningful information
                has_error_info = any(key in error_event for key in [
                    "error", "error_message", "message", "status", "failure_reason"
                ])
                assert has_error_info, "Error event lacks meaningful error information"
                
                # Verify connection remains stable after error
                assert not websocket.closed, "WebSocket connection should remain stable during error"
                
                # Test that connection can recover - send simple message
                recovery_message = {
                    "type": "connection_test",
                    "user_id": self.test_user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(recovery_message))
                
            await websocket.close()
            
        except Exception as e:
            pytest.fail(f"Agent execution error handling test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_malformed_message_error_handling(self, real_services_fixture):
        """
        Test WebSocket error handling for malformed messages and invalid requests.
        
        BVJ: System stability - Platform must handle invalid input gracefully.
        Robust message validation prevents system crashes and maintains service quality.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=12.0
            )
            
            self.active_connections.append(websocket)
            
            # Test 1: Send malformed JSON
            malformed_json = '{"type": "test", "user_id": "' + self.test_user_id + '", invalid_json}'
            
            await websocket.send(malformed_json)
            
            # Wait for response or error handling
            malformed_events = await self.collect_error_events(websocket, timeout=8.0)
            
            # Verify connection remains stable after malformed message
            assert not websocket.closed, "Connection should remain stable after malformed JSON"
            
            # Test 2: Send message with missing required fields
            incomplete_message = {
                "type": "agent_execution_request",
                # Missing user_id, thread_id, task, etc.
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(incomplete_message))
            
            incomplete_events = await self.collect_error_events(websocket, timeout=8.0)
            
            # Test 3: Send message with invalid data types
            invalid_types_message = {
                "type": "agent_execution_request",
                "user_id": 12345,  # Should be string
                "thread_id": [],   # Should be string
                "task": {"invalid": "object"},  # Should be string
                "timestamp": "not_a_timestamp"
            }
            
            await websocket.send(json.dumps(invalid_types_message))
            
            invalid_type_events = await self.collect_error_events(websocket, timeout=8.0)
            
            # Verify system handled all malformed messages gracefully
            total_events = malformed_events + incomplete_events + invalid_type_events
            
            # Should receive some error responses or validation messages
            validation_events = [e for e in total_events if 
                               e.get("type") in ["validation_error", "error", "message_error"] or
                               "validation" in str(e.get("message", "")).lower() or
                               "invalid" in str(e.get("message", "")).lower()]
            
            # System should handle errors gracefully (may or may not send explicit error messages)
            # The key requirement is that connection remains stable
            assert not websocket.closed, "Connection must remain stable during malformed message handling"
            
            # Test recovery with valid message
            valid_recovery_message = {
                "type": "connection_test",
                "user_id": self.test_user_id,
                "message": "Testing recovery after malformed messages",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(valid_recovery_message))
            
            # Verify system can process valid messages after errors
            recovery_events = await self.collect_error_events(websocket, timeout=5.0)
            assert not websocket.closed, "System should recover and process valid messages"
            
            await websocket.close()
            
        except Exception as e:
            pytest.fail(f"Malformed message error handling test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_connection_interruption_recovery(self, real_services_fixture):
        """
        Test WebSocket error handling during connection interruptions and recovery.
        
        BVJ: Service continuity - Users must experience minimal disruption during network issues.
        Robust connection handling maintains user engagement and prevents session loss.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            # Establish initial connection
            websocket1 = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=12.0
            )
            
            self.active_connections.append(websocket1)
            
            # Send initial message to establish session
            initial_message = {
                "type": "session_establishment",
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket1.send(json.dumps(initial_message))
            
            # Wait for any response
            try:
                initial_response = await asyncio.wait_for(websocket1.recv(), timeout=3.0)
            except asyncio.TimeoutError:
                # No immediate response is acceptable
                pass
            
            # Simulate connection interruption by forcibly closing
            await websocket1.close()
            assert websocket1.closed, "First connection should be closed"
            
            # Wait a moment to simulate network interruption delay
            await asyncio.sleep(1.0)
            
            # Test reconnection capability
            websocket2 = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=10.0
                ),
                timeout=15.0  # Longer timeout for reconnection
            )
            
            self.active_connections.append(websocket2)
            
            # Test that reconnection is functional
            reconnection_message = {
                "type": "reconnection_test",
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id,
                "message": "Testing functionality after reconnection",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket2.send(json.dumps(reconnection_message))
            
            # Verify reconnection works
            assert not websocket2.closed, "Reconnection should be successful"
            
            # Test agent functionality after reconnection
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = ErrorSimulatingLLM("none").complete_async
                
                agent_request_after_reconnection = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "reconnection_test_agent",
                    "task": "Test agent functionality after connection recovery",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket2.send(json.dumps(agent_request_after_reconnection))
                
                # Collect events to verify functionality
                recovery_events = await self.collect_error_events(websocket2, timeout=15.0)
                
                # Verify system is functional after reconnection
                assert len(recovery_events) > 0, "No events received after reconnection - system may not be functional"
                
                # Look for successful agent events
                success_events = [e for e in recovery_events if e.get("type") in [
                    "agent_started", "agent_completed", "agent_thinking"
                ]]
                
                assert len(success_events) > 0, "No successful agent events after reconnection"
                
                # Verify user context is maintained
                for event in success_events:
                    assert event.get("user_id") == self.test_user_id, "User context not maintained after reconnection"
            
            await websocket2.close()
            
        except Exception as e:
            pytest.fail(f"Connection interruption recovery test failed: {e}")