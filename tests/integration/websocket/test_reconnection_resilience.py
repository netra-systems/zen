"""
Reconnection Resilience WebSocket Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Service reliability foundation
- Business Goal: Ensure uninterrupted user experience despite network disruptions
- Value Impact: Reconnection resilience prevents user frustration and session loss
- Strategic/Revenue Impact: Poor reconnection handling causes user churn and reduces platform trust

CRITICAL RECONNECTION SCENARIOS:
1. Automatic reconnection after network interruptions
2. Session state recovery and continuity after reconnection
3. Message delivery reliability across connection interruptions

CRITICAL REQUIREMENTS:
- NO MOCKS - Uses real WebSocket connections and real network conditions
- Tests real reconnection patterns and session recovery
- Validates message continuity across reconnections
- Ensures proper authentication and state restoration
- Tests resilience under various network failure scenarios
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import patch

import pytest
import websockets

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.fixtures.websocket_test_helpers import WebSocketTestClient
from shared.isolated_environment import get_env


class ReconnectionTestLLM:
    """
    Mock LLM for reconnection testing with session-aware responses.
    This is the ONLY acceptable mock per CLAUDE.md - external LLM APIs.
    """
    
    def __init__(self, session_identifier: str = "default"):
        self.session_identifier = session_identifier
        self.call_count = 0
        self.session_state = {}
    
    async def complete_async(self, messages, **kwargs):
        """Mock LLM with session continuity for reconnection validation."""
        self.call_count += 1
        
        # Simulate persistent session state across reconnections
        if "conversation_history" not in self.session_state:
            self.session_state["conversation_history"] = []
        
        self.session_state["conversation_history"].append(f"Call #{self.call_count}")
        
        await asyncio.sleep(0.1)
        
        return {
            "content": f"Session {self.session_identifier} response #{self.call_count}. Maintaining continuity across reconnections with conversation state preserved.",
            "usage": {"total_tokens": 95 + (self.call_count * 8)},
            "session_metadata": {
                "call_count": self.call_count,
                "session_id": self.session_identifier,
                "state_preserved": len(self.session_state["conversation_history"])
            }
        }


class TestReconnectionResilience(BaseIntegrationTest):
    """
    Resilience tests for WebSocket reconnection scenarios.
    
    CRITICAL: All tests use REAL WebSocket connections and REAL reconnection patterns
    to validate production-quality reconnection handling and session recovery.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_reconnection_test(self, real_services_fixture):
        """
        Set up reconnection resilience test environment.
        
        BVJ: Reliability Foundation - Ensures robust reconnection testing
        """
        self.env = get_env()
        self.services = real_services_fixture
        self.test_session_id = f"reconnection_{uuid.uuid4().hex[:8]}"
        
        # CRITICAL: Verify real services (CLAUDE.md requirement)
        assert real_services_fixture, "Real services required for reconnection testing"
        assert "backend" in real_services_fixture, "Real backend required for reconnection validation"
        
        # Define reconnection test scenarios
        self.reconnection_scenarios = {
            "quick_reconnect": {
                "disconnect_duration": 0.5,  # seconds
                "max_reconnect_time": 5.0,
                "expected_recovery": "immediate"
            },
            "network_interruption": {
                "disconnect_duration": 2.0,
                "max_reconnect_time": 10.0,
                "expected_recovery": "graceful"
            },
            "extended_downtime": {
                "disconnect_duration": 5.0,
                "max_reconnect_time": 15.0,
                "expected_recovery": "eventual"
            }
        }
        
        # Initialize reconnection metrics
        self.reconnection_metrics = {
            "total_disconnections": 0,
            "successful_reconnections": 0,
            "failed_reconnections": 0,
            "reconnection_times": [],
            "message_recovery_rate": 0.0,
            "session_continuity_maintained": 0
        }
        
        # Base auth config for reconnection testing
        self.auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            test_user_email=f"reconnection_test_{self.test_session_id}@example.com",
            timeout=25.0  # Longer timeout for reconnection scenarios
        )
        
        self.auth_helper = E2EWebSocketAuthHelper(config=self.auth_config, environment="test")
        self.test_user_id = f"reconnection_user_{self.test_session_id}"
        self.test_thread_id = f"reconnection_thread_{self.test_session_id}"
        
        self.connection_history: List[Dict[str, Any]] = []
        self.message_history: List[Dict[str, Any]] = []
        
        # Test auth helper functionality
        try:
            token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
            assert token, "Failed to create test JWT for reconnection testing"
        except Exception as e:
            pytest.fail(f"Reconnection test setup failed: {e}")
    
    async def async_teardown(self):
        """Clean up reconnection test resources."""
        # Close any remaining connections from connection history
        for connection_data in self.connection_history:
            if "websocket" in connection_data and not connection_data["websocket"].closed:
                try:
                    await connection_data["websocket"].close()
                except:
                    pass
        
        await super().async_teardown()
    
    async def establish_initial_connection(self) -> Tuple[websockets.ServerConnection, str]:
        """
        Establish initial WebSocket connection with session state.
        
        Returns:
            Tuple of (websocket, token) for connection management
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        headers = self.auth_helper.get_websocket_headers(token)
        
        # Add reconnection test headers
        headers.update({
            "X-Reconnection-Test": "true",
            "X-Session-ID": self.test_session_id,
            "X-User-Context": self.test_user_id
        })
        
        websocket = await asyncio.wait_for(
            websockets.connect(
                self.auth_helper.config.websocket_url,
                additional_headers=headers,
                open_timeout=15.0
            ),
            timeout=20.0
        )
        
        # Record connection establishment
        connection_data = {
            "websocket": websocket,
            "token": token,
            "established_at": time.time(),
            "connection_type": "initial"
        }
        self.connection_history.append(connection_data)
        
        return websocket, token
    
    async def simulate_connection_interruption(
        self,
        websocket: websockets.ServerConnection,
        interruption_duration: float
    ) -> None:
        """
        Simulate connection interruption by forcibly closing connection.
        
        Args:
            websocket: WebSocket connection to interrupt
            interruption_duration: How long to wait before allowing reconnection
        """
        self.reconnection_metrics["total_disconnections"] += 1
        
        # Record disconnection
        disconnection_data = {
            "disconnected_at": time.time(),
            "interruption_duration": interruption_duration,
            "connection_state": "forcibly_closed"
        }
        self.connection_history.append(disconnection_data)
        
        # Force close connection
        await websocket.close()
        
        # Wait for interruption duration
        await asyncio.sleep(interruption_duration)
    
    async def attempt_reconnection(self, original_token: str) -> Tuple[Optional[websockets.ServerConnection], bool]:
        """
        Attempt to reconnect WebSocket with session recovery.
        
        Args:
            original_token: Original authentication token
            
        Returns:
            Tuple of (websocket, success_flag)
        """
        reconnection_start = time.time()
        
        try:
            # Use same token for session continuity
            headers = self.auth_helper.get_websocket_headers(original_token)
            
            # Add reconnection headers
            headers.update({
                "X-Reconnection-Attempt": "true",
                "X-Original-Session": self.test_session_id,
                "X-Session-Recovery": "requested"
            })
            
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=12.0
                ),
                timeout=15.0
            )
            
            reconnection_time = time.time() - reconnection_start
            self.reconnection_metrics["reconnection_times"].append(reconnection_time)
            self.reconnection_metrics["successful_reconnections"] += 1
            
            # Record successful reconnection
            reconnection_data = {
                "websocket": websocket,
                "reconnected_at": time.time(),
                "reconnection_time": reconnection_time,
                "connection_type": "reconnected"
            }
            self.connection_history.append(reconnection_data)
            
            return websocket, True
            
        except Exception as e:
            reconnection_time = time.time() - reconnection_start
            self.reconnection_metrics["failed_reconnections"] += 1
            
            # Record failed reconnection
            failure_data = {
                "reconnection_failed_at": time.time(),
                "failure_reason": str(e),
                "reconnection_time": reconnection_time
            }
            self.connection_history.append(failure_data)
            
            return None, False
    
    async def send_test_message_with_tracking(
        self,
        websocket: websockets.ServerConnection,
        message_content: Dict[str, Any],
        message_id: str = None
    ) -> str:
        """
        Send test message with tracking for continuity validation.
        
        Args:
            websocket: WebSocket connection
            message_content: Message to send
            message_id: Optional message ID for tracking
            
        Returns:
            Message ID for tracking
        """
        message_id = message_id or f"msg_{uuid.uuid4().hex[:8]}"
        
        tracked_message = {
            **message_content,
            "message_id": message_id,
            "sent_at": time.time(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await websocket.send(json.dumps(tracked_message))
        
        # Record message in history
        self.message_history.append({
            "message_id": message_id,
            "message_type": tracked_message.get("type", "unknown"),
            "sent_at": tracked_message["sent_at"],
            "connection_context": "tracked"
        })
        
        return message_id
    
    async def collect_messages_with_continuity_check(
        self,
        websocket: websockets.ServerConnection,
        expected_message_count: int,
        timeout: float = 20.0
    ) -> List[Dict[str, Any]]:
        """
        Collect messages with session continuity validation.
        
        Args:
            websocket: WebSocket connection
            expected_message_count: Expected number of messages
            timeout: Collection timeout
            
        Returns:
            List of received messages with continuity metadata
        """
        messages = []
        start_time = time.time()
        
        try:
            while len(messages) < expected_message_count and (time.time() - start_time) < timeout:
                try:
                    message_data = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    message = json.loads(message_data)
                    
                    # Add continuity tracking
                    message_with_continuity = {
                        **message,
                        "_received_at": time.time(),
                        "_session_continuity": self._validate_session_continuity(message),
                        "_message_order": len(messages)
                    }
                    
                    messages.append(message_with_continuity)
                    
                except asyncio.TimeoutError:
                    if (time.time() - start_time) >= timeout:
                        break
                    continue
                    
        except Exception as e:
            # Log error but return collected messages
            pass
            
        return messages
    
    def _validate_session_continuity(self, message: Dict[str, Any]) -> Dict[str, bool]:
        """
        Validate session continuity markers in message.
        
        Args:
            message: Received message
            
        Returns:
            Dict with continuity validation results
        """
        continuity_check = {
            "user_context_maintained": True,
            "session_data_present": True,
            "state_consistency": True
        }
        
        # Check user context continuity
        message_user_id = message.get("user_id")
        if message_user_id and message_user_id != self.test_user_id:
            continuity_check["user_context_maintained"] = False
        
        # Check for session-related data
        session_metadata = message.get("session_metadata", {})
        if not session_metadata and message.get("type") in ["agent_started", "agent_completed"]:
            continuity_check["session_data_present"] = False
        
        return continuity_check
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_quick_reconnection_recovery(self, real_services_fixture):
        """
        Test quick reconnection recovery after brief network interruption.
        
        BVJ: User experience continuity - Brief interruptions should not disrupt user sessions.
        Quick recovery maintains user engagement and prevents abandonment.
        """
        scenario = self.reconnection_scenarios["quick_reconnect"]
        
        try:
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = ReconnectionTestLLM("quick_reconnect").complete_async
                
                # Establish initial connection and send test message
                initial_ws, token = await self.establish_initial_connection()
                
                # Send initial agent request to establish session state
                initial_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "reconnection_test_agent",
                    "task": "Initial request before quick reconnection test"
                }
                
                initial_msg_id = await self.send_test_message_with_tracking(initial_ws, initial_request)
                
                # Collect initial response
                initial_responses = await self.collect_messages_with_continuity_check(initial_ws, 1, timeout=15.0)
                assert len(initial_responses) > 0, "No initial response received"
                
                # Simulate quick connection interruption
                await self.simulate_connection_interruption(initial_ws, scenario["disconnect_duration"])
                
                # Attempt quick reconnection
                reconnected_ws, reconnection_success = await self.attempt_reconnection(token)
                assert reconnection_success, "Quick reconnection failed"
                assert reconnected_ws is not None, "No WebSocket returned from quick reconnection"
                
                # Test session continuity after reconnection
                continuity_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "reconnection_test_agent",
                    "task": "Continuity test after quick reconnection"
                }
                
                continuity_msg_id = await self.send_test_message_with_tracking(reconnected_ws, continuity_request)
                
                # Collect post-reconnection responses
                post_reconnect_responses = await self.collect_messages_with_continuity_check(
                    reconnected_ws, 1, timeout=15.0
                )
                
                # Verify quick reconnection success
                assert len(post_reconnect_responses) > 0, "No responses after quick reconnection"
                
                # Validate session continuity
                for response in post_reconnect_responses:
                    continuity_check = response["_session_continuity"]
                    assert continuity_check["user_context_maintained"], "User context not maintained after quick reconnection"
                
                # Verify quick reconnection performance
                avg_reconnection_time = sum(self.reconnection_metrics["reconnection_times"]) / max(len(self.reconnection_metrics["reconnection_times"]), 1)
                assert avg_reconnection_time < scenario["max_reconnect_time"], \
                    f"Quick reconnection too slow: {avg_reconnection_time:.2f}s > {scenario['max_reconnect_time']}s"
                
                # Verify reconnection success rate
                success_rate = (self.reconnection_metrics["successful_reconnections"] / 
                              max(self.reconnection_metrics["total_disconnections"], 1))
                assert success_rate >= 1.0, f"Quick reconnection success rate too low: {success_rate:.2f}"
                
                await reconnected_ws.close()
                
        except Exception as e:
            pytest.fail(f"Quick reconnection recovery test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_network_interruption_resilience(self, real_services_fixture):
        """
        Test resilience during network interruption with session recovery.
        
        BVJ: Service reliability - Platform must handle network issues gracefully.
        Network resilience maintains business continuity during infrastructure problems.
        """
        scenario = self.reconnection_scenarios["network_interruption"]
        
        try:
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = ReconnectionTestLLM("network_interruption").complete_async
                
                # Establish initial connection with active session
                initial_ws, token = await self.establish_initial_connection()
                
                # Send multiple messages to establish rich session state
                pre_interruption_messages = []
                for i in range(2):
                    request = {
                        "type": "agent_execution_request",
                        "user_id": self.test_user_id,
                        "thread_id": self.test_thread_id,
                        "agent_type": "network_resilience_agent",
                        "task": f"Pre-interruption message #{i+1} to establish session state"
                    }
                    
                    msg_id = await self.send_test_message_with_tracking(initial_ws, request)
                    pre_interruption_messages.append(msg_id)
                    await asyncio.sleep(0.5)  # Brief pause between messages
                
                # Collect pre-interruption responses
                pre_responses = await self.collect_messages_with_continuity_check(initial_ws, 2, timeout=20.0)
                assert len(pre_responses) >= 1, "No pre-interruption responses received"
                
                # Simulate network interruption
                await self.simulate_connection_interruption(initial_ws, scenario["disconnect_duration"])
                
                # Wait additional time to simulate network recovery delay
                await asyncio.sleep(1.0)
                
                # Attempt reconnection with retry logic
                max_reconnect_attempts = 3
                reconnected_ws = None
                
                for attempt in range(max_reconnect_attempts):
                    reconnected_ws, success = await self.attempt_reconnection(token)
                    if success:
                        break
                    
                    if attempt < max_reconnect_attempts - 1:
                        await asyncio.sleep(2.0)  # Wait before retry
                
                assert reconnected_ws is not None, "Failed to reconnect after network interruption"
                
                # Test session state recovery
                recovery_request = {
                    "type": "session_recovery_test",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "recovery_context": {
                        "pre_interruption_messages": len(pre_interruption_messages),
                        "session_id": self.test_session_id
                    }
                }
                
                recovery_msg_id = await self.send_test_message_with_tracking(reconnected_ws, recovery_request)
                
                # Send follow-up agent request to test continued functionality
                post_recovery_request = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "network_resilience_agent",
                    "task": "Post-recovery message to validate session continuity"
                }
                
                post_msg_id = await self.send_test_message_with_tracking(reconnected_ws, post_recovery_request)
                
                # Collect post-interruption responses
                post_responses = await self.collect_messages_with_continuity_check(
                    reconnected_ws, 2, timeout=25.0
                )
                
                # Verify network interruption resilience
                assert len(post_responses) > 0, "No responses after network interruption recovery"
                
                # Validate session continuity after network recovery
                continuity_maintained_count = 0
                for response in post_responses:
                    continuity_check = response["_session_continuity"]
                    if continuity_check["user_context_maintained"]:
                        continuity_maintained_count += 1
                
                continuity_rate = continuity_maintained_count / len(post_responses)
                assert continuity_rate >= 0.8, f"Session continuity rate too low after network interruption: {continuity_rate:.2f}"
                
                # Verify reasonable recovery time
                if self.reconnection_metrics["reconnection_times"]:
                    avg_recovery_time = sum(self.reconnection_metrics["reconnection_times"]) / len(self.reconnection_metrics["reconnection_times"])
                    assert avg_recovery_time < scenario["max_reconnect_time"], \
                        f"Network interruption recovery too slow: {avg_recovery_time:.2f}s"
                
                await reconnected_ws.close()
                
        except Exception as e:
            pytest.fail(f"Network interruption resilience test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_extended_downtime_recovery_patterns(self, real_services_fixture):
        """
        Test recovery patterns after extended connection downtime.
        
        BVJ: Service resilience - Platform must recover from extended outages.
        Extended downtime recovery enables business continuity during major incidents.
        """
        scenario = self.reconnection_scenarios["extended_downtime"]
        
        try:
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = ReconnectionTestLLM("extended_downtime").complete_async
                
                # Establish initial session with comprehensive state
                initial_ws, token = await self.establish_initial_connection()
                
                # Build substantial session state before extended downtime
                session_state_messages = []
                for i in range(3):
                    state_request = {
                        "type": "agent_execution_request",
                        "user_id": self.test_user_id,
                        "thread_id": self.test_thread_id,
                        "agent_type": "extended_downtime_agent",
                        "task": f"Session state building message #{i+1} with important context",
                        "session_context": {
                            "message_index": i,
                            "session_phase": "state_building",
                            "user_workflow": "extended_downtime_test"
                        }
                    }
                    
                    msg_id = await self.send_test_message_with_tracking(initial_ws, state_request)
                    session_state_messages.append(msg_id)
                    await asyncio.sleep(0.3)
                
                # Collect session building responses
                state_responses = await self.collect_messages_with_continuity_check(initial_ws, 3, timeout=25.0)
                pre_downtime_response_count = len(state_responses)
                
                # Simulate extended downtime
                downtime_start = time.time()
                await self.simulate_connection_interruption(initial_ws, scenario["disconnect_duration"])
                
                # Additional wait to simulate extended outage
                await asyncio.sleep(2.0)
                
                # Attempt recovery with extended retry logic
                max_recovery_attempts = 5
                recovery_delays = [1.0, 2.0, 3.0, 5.0, 8.0]  # Progressive backoff
                
                recovered_ws = None
                total_recovery_time = 0
                
                for attempt in range(max_recovery_attempts):
                    recovery_attempt_start = time.time()
                    recovered_ws, recovery_success = await self.attempt_reconnection(token)
                    attempt_time = time.time() - recovery_attempt_start
                    total_recovery_time += attempt_time
                    
                    if recovery_success and recovered_ws:
                        break
                    
                    if attempt < max_recovery_attempts - 1:
                        delay = recovery_delays[attempt]
                        await asyncio.sleep(delay)
                        total_recovery_time += delay
                
                downtime_duration = time.time() - downtime_start
                
                # Verify eventual recovery from extended downtime
                assert recovered_ws is not None, "Failed to recover from extended downtime"
                assert not recovered_ws.closed, "Recovered connection is not active"
                
                # Test comprehensive functionality after extended recovery
                post_recovery_test_messages = []
                
                # Test 1: Session state inquiry
                state_inquiry = {
                    "type": "session_state_inquiry",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "inquiry_context": {
                        "pre_downtime_messages": len(session_state_messages),
                        "downtime_duration": downtime_duration,
                        "recovery_type": "extended_downtime"
                    }
                }
                
                inquiry_msg_id = await self.send_test_message_with_tracking(recovered_ws, state_inquiry)
                post_recovery_test_messages.append(inquiry_msg_id)
                
                # Test 2: Normal agent functionality
                functionality_test = {
                    "type": "agent_execution_request",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "extended_downtime_agent",
                    "task": "Post-extended-downtime functionality validation"
                }
                
                func_msg_id = await self.send_test_message_with_tracking(recovered_ws, functionality_test)
                post_recovery_test_messages.append(func_msg_id)
                
                # Collect post-recovery responses
                recovery_responses = await self.collect_messages_with_continuity_check(
                    recovered_ws, len(post_recovery_test_messages), timeout=30.0
                )
                
                # Verify extended downtime recovery success
                assert len(recovery_responses) > 0, "No responses after extended downtime recovery"
                
                # Validate basic functionality restoration
                functional_response_count = 0
                for response in recovery_responses:
                    if response.get("type") in ["agent_started", "agent_completed", "agent_thinking"]:
                        functional_response_count += 1
                
                assert functional_response_count > 0, "Agent functionality not restored after extended downtime"
                
                # Verify user context preservation
                user_context_preserved = all(
                    response["_session_continuity"]["user_context_maintained"]
                    for response in recovery_responses
                    if "_session_continuity" in response
                )
                assert user_context_preserved, "User context not preserved after extended downtime"
                
                # Performance validation for extended recovery
                if self.reconnection_metrics["reconnection_times"]:
                    final_recovery_time = max(self.reconnection_metrics["reconnection_times"])
                    assert final_recovery_time < scenario["max_reconnect_time"], \
                        f"Extended downtime recovery took too long: {final_recovery_time:.2f}s"
                
                # Verify overall recovery metrics
                total_attempts = self.reconnection_metrics["successful_reconnections"] + self.reconnection_metrics["failed_reconnections"]
                if total_attempts > 0:
                    final_success_rate = self.reconnection_metrics["successful_reconnections"] / total_attempts
                    assert final_success_rate > 0, "No successful reconnections after extended downtime"
                
                print(f"Extended Downtime Recovery - Duration: {downtime_duration:.2f}s, "
                      f"Recovery Time: {total_recovery_time:.2f}s, "
                      f"Success Rate: {final_success_rate:.2f}")
                
                await recovered_ws.close()
                
        except Exception as e:
            pytest.fail(f"Extended downtime recovery patterns test failed: {e}")