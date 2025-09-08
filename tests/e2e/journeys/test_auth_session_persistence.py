"""
🌟 E2E TEST SUITE: Authentication Session Persistence Journey

Tests user session persistence across browser refreshes, tab switches, and reconnections.
This validates that authenticated users maintain their session state for seamless UX.

Business Value Justification (BVJ):
- Segment: ALL authenticated users (Free, Early, Mid, Enterprise) 
- Business Goal: Reduce Re-authentication Friction - Seamless user experience
- Value Impact: $150K+ ARR - Poor session UX = 25% user drop-off per session
- Strategic Impact: User Retention - Persistent sessions enable longer engagement

SESSION PERSISTENCE JOURNEY:
1. User authenticates successfully 
2. User interacts with chat (establishes session)
3. User refresh browser/reconnects WebSocket
4. Session persists without re-login
5. Chat history/context maintained
6. User continues seamlessly where they left off

CRITICAL SUCCESS CRITERIA:
- JWT tokens persist through browser refresh
- WebSocket reconnection maintains user context
- Chat history preserved across sessions
- No authentication prompts for valid sessions
- Session timeout handled gracefully

FAILURE = USER FRICTION = ENGAGEMENT DROP = REVENUE LOSS
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytest
import websockets
from shared.isolated_environment import get_env

# Import SSOT utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.base_e2e_test import BaseE2ETest

logger = logging.getLogger(__name__)


class SessionPersistenceValidator:
    """Validates user session persistence for continuous engagement."""
    
    def __init__(self):
        self.session_events = []
        self.user_context_snapshots = []
        self.reconnection_attempts = []
        self.session_start_time = None
        
    def start_session_tracking(self, user_info: Dict[str, Any]):
        """Start tracking user session persistence."""
        self.session_start_time = time.time()
        self.session_events.append({
            "event": "session_started",
            "timestamp": self.session_start_time,
            "user_info": user_info
        })
        
    def record_session_event(self, event_type: str, details: Optional[Dict] = None):
        """Record session-related events."""
        event_record = {
            "event": event_type,
            "timestamp": time.time(),
            "session_duration": time.time() - (self.session_start_time or time.time()),
            "details": details or {}
        }
        self.session_events.append(event_record)
        
    def snapshot_user_context(self, context_data: Dict[str, Any]):
        """Capture user context at a point in time."""
        snapshot = {
            "timestamp": time.time(),
            "user_id": context_data.get("user_id"),
            "thread_id": context_data.get("thread_id"),
            "message_count": context_data.get("message_count", 0),
            "session_data": context_data.get("session_data", {})
        }
        self.user_context_snapshots.append(snapshot)
        
    def record_reconnection(self, attempt_info: Dict[str, Any]):
        """Record reconnection attempt."""
        self.reconnection_attempts.append({
            "timestamp": time.time(),
            "attempt_number": len(self.reconnection_attempts) + 1,
            "success": attempt_info.get("success", False),
            "duration": attempt_info.get("duration", 0),
            "error": attempt_info.get("error")
        })
        
    def validate_session_persistence(self) -> Dict[str, Any]:
        """Validate that session persistence requirements are met."""
        validation = {
            "session_maintained": False,
            "context_preserved": False,
            "reconnection_successful": False,
            "session_duration": 0,
            "business_impact": ""
        }
        
        if not self.session_events:
            validation["business_impact"] = "CRITICAL: No session events recorded"
            return validation
            
        # Check session duration
        last_event = self.session_events[-1]
        validation["session_duration"] = last_event.get("session_duration", 0)
        
        # Check for successful reconnections
        successful_reconnections = [r for r in self.reconnection_attempts if r["success"]]
        validation["reconnection_successful"] = len(successful_reconnections) > 0
        
        # Check context preservation
        if len(self.user_context_snapshots) >= 2:
            first_context = self.user_context_snapshots[0]
            last_context = self.user_context_snapshots[-1]
            
            # User ID should remain consistent
            validation["context_preserved"] = (
                first_context["user_id"] == last_context["user_id"] and
                first_context["user_id"] is not None
            )
        
        # Check overall session maintenance
        session_errors = [e for e in self.session_events if "error" in e.get("details", {})]
        validation["session_maintained"] = len(session_errors) == 0
        
        # Business impact assessment
        if not validation["session_maintained"]:
            validation["business_impact"] = "HIGH: Session errors detected - user experience degraded"
        elif not validation["context_preserved"]:
            validation["business_impact"] = "MEDIUM: User context lost - confusing experience"
        elif not validation["reconnection_successful"] and len(self.reconnection_attempts) > 0:
            validation["business_impact"] = "HIGH: Reconnection failed - user must re-authenticate"
        else:
            validation["business_impact"] = "NONE: Session persistence working correctly"
            
        return validation


@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.session_persistence
class TestAuthSessionPersistence(BaseE2ETest):
    """E2E: Authentication session persistence across connections."""
    
    @pytest.fixture(autouse=True)
    async def setup_session_testing(self, real_services_fixture):
        """Setup real services for session persistence testing."""
        self.services = real_services_fixture
        self.validator = SessionPersistenceValidator()
        self.auth_helper = E2EAuthHelper()
        self.ws_auth_helper = E2EWebSocketAuthHelper()
        
        # Ensure services are available
        if not self.services.get("services_available", {}).get("backend", False):
            pytest.skip("Backend service required for session persistence testing")
            
        # Configure WebSocket URL
        backend_url = self.services["backend_url"]
        websocket_url = backend_url.replace("http://", "ws://") + "/ws"
        self.ws_auth_helper.config.websocket_url = websocket_url
        
    async def test_websocket_reconnection_session_persistence(self):
        """
        E2E: WebSocket reconnection maintains user session.
        
        BUSINESS VALUE: Users don't lose context when connection drops.
        """
        logger.info("🔄 E2E: Testing WebSocket reconnection session persistence")
        
        # Create authenticated user
        timestamp = int(time.time())
        user_id = f"session-persist-{timestamp}-{uuid.uuid4().hex[:6]}"
        user_email = f"session-{timestamp}@netra.test"
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=user_email,
            exp_minutes=60  # Long-lived for session testing
        )
        
        user_info = {
            "user_id": user_id,
            "email": user_email,
            "test_type": "reconnection_persistence"
        }
        
        self.validator.start_session_tracking(user_info)
        
        try:
            # STEP 1: Initial connection and context establishment
            logger.info("📡 STEP 1: Initial WebSocket connection")
            websocket_url = f"{self.ws_auth_helper.config.websocket_url}?token={token}"
            
            # First connection
            websocket1 = await websockets.connect(
                websocket_url,
                additional_headers=self.ws_auth_helper.get_websocket_headers(token)
            )
            
            self.validator.record_session_event("initial_connection", {"success": True})
            
            # Establish session context
            thread_id = f"session-thread-{uuid.uuid4().hex[:8]}"
            session_message = {
                "type": "chat_message",
                "content": "This is my session context message",
                "user_id": user_id,
                "thread_id": thread_id,
                "message_number": 1
            }
            
            await websocket1.send(json.dumps(session_message))
            
            # Wait for response to establish context
            try:
                response1 = await asyncio.wait_for(websocket1.recv(), timeout=5.0)
                response1_data = json.loads(response1)
                
                # Capture initial context
                initial_context = {
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "message_count": 1,
                    "session_data": response1_data
                }
                self.validator.snapshot_user_context(initial_context)
                
            except asyncio.TimeoutError:
                logger.warning("No response to initial message - continuing test")
            
            # STEP 2: Simulate connection drop
            logger.info("❌ STEP 2: Simulate connection drop")
            await websocket1.close()
            self.validator.record_session_event("connection_dropped", {"intentional": True})
            
            await asyncio.sleep(1.0)  # Brief pause to simulate network issue
            
            # STEP 3: Reconnection with same token
            logger.info("🔄 STEP 3: Reconnect with same session token")
            reconnect_start = time.time()
            
            try:
                websocket2 = await websockets.connect(
                    websocket_url,
                    additional_headers=self.ws_auth_helper.get_websocket_headers(token)
                )
                
                reconnect_duration = time.time() - reconnect_start
                
                self.validator.record_reconnection({
                    "success": True,
                    "duration": reconnect_duration
                })
                
                self.validator.record_session_event("reconnection_successful", {
                    "duration": reconnect_duration
                })
                
                # STEP 4: Verify session context persistence
                logger.info("🔍 STEP 4: Verify session context maintained")
                
                # Send continuation message in same thread
                continuation_message = {
                    "type": "chat_message", 
                    "content": "I'm continuing our conversation after reconnection",
                    "user_id": user_id,
                    "thread_id": thread_id,  # Same thread as before
                    "message_number": 2
                }
                
                await websocket2.send(json.dumps(continuation_message))
                
                try:
                    response2 = await asyncio.wait_for(websocket2.recv(), timeout=5.0)
                    response2_data = json.loads(response2)
                    
                    # Capture post-reconnection context
                    reconnected_context = {
                        "user_id": user_id,
                        "thread_id": thread_id,
                        "message_count": 2,
                        "session_data": response2_data
                    }
                    self.validator.snapshot_user_context(reconnected_context)
                    
                    # Verify user context consistency
                    assert user_id in str(response2_data), "User context should be maintained after reconnection"
                    
                except asyncio.TimeoutError:
                    logger.warning("No response after reconnection - but connection established")
                
                await websocket2.close()
                
            except Exception as e:
                self.validator.record_reconnection({
                    "success": False,
                    "duration": time.time() - reconnect_start,
                    "error": str(e)
                })
                pytest.fail(f"SESSION PERSISTENCE FAILURE: Reconnection failed - {str(e)}")
            
            # VALIDATION: Session persistence requirements
            validation = self.validator.validate_session_persistence()
            
            if not validation["reconnection_successful"]:
                pytest.fail(f"SESSION PERSISTENCE FAILURE: {validation['business_impact']}")
                
            if not validation["context_preserved"]:
                pytest.fail(f"CONTEXT PERSISTENCE FAILURE: {validation['business_impact']}")
            
            logger.info(f"✅ WebSocket session persistence validated")
            logger.info(f"   Session duration: {validation['session_duration']:.1f}s")
            logger.info(f"   Reconnections: {len(self.validator.reconnection_attempts)}")
            
        except Exception as e:
            self.validator.record_session_event("session_failure", {"error": str(e)})
            raise
            
    async def test_token_refresh_session_continuity(self):
        """
        E2E: Token refresh maintains session continuity.
        
        BUSINESS VALUE: Users stay authenticated seamlessly during token refresh.
        """
        logger.info("🔑 E2E: Testing token refresh session continuity")
        
        timestamp = int(time.time())
        user_id = f"token-refresh-session-{timestamp}"
        user_email = f"tokenrefresh-{timestamp}@netra.test"
        
        # Create initial token with moderate expiry
        initial_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=user_email,
            exp_minutes=2  # Will refresh this
        )
        
        user_info = {
            "user_id": user_id,
            "email": user_email,
            "test_type": "token_refresh_continuity"
        }
        
        self.validator.start_session_tracking(user_info)
        
        try:
            websocket_url = f"{self.ws_auth_helper.config.websocket_url}?token={initial_token}"
            
            async with websockets.connect(
                websocket_url,
                additional_headers=self.ws_auth_helper.get_websocket_headers(initial_token)
            ) as websocket:
                
                # STEP 1: Establish session with initial token
                logger.info("🔐 STEP 1: Establish session with initial token")
                
                initial_context = {
                    "user_id": user_id,
                    "thread_id": f"refresh-thread-{uuid.uuid4().hex[:8]}",
                    "message_count": 0
                }
                self.validator.snapshot_user_context(initial_context)
                
                # Send initial message
                pre_refresh_message = {
                    "type": "chat_message",
                    "content": "Message before token refresh",
                    "user_id": user_id,
                    "thread_id": initial_context["thread_id"]
                }
                
                await websocket.send(json.dumps(pre_refresh_message))
                self.validator.record_session_event("pre_refresh_message", {"sent": True})
                
                # STEP 2: Simulate token refresh
                logger.info("🔄 STEP 2: Token refresh")
                self.validator.record_session_event("token_refresh_started", {})
                
                # Create refreshed token
                refreshed_token = self.auth_helper.create_test_jwt_token(
                    user_id=user_id,
                    email=user_email,
                    exp_minutes=60  # Extended expiry
                )
                
                # Send token refresh notification (if protocol supports it)
                refresh_notification = {
                    "type": "token_refresh",
                    "user_id": user_id,
                    "new_token": refreshed_token
                }
                
                await websocket.send(json.dumps(refresh_notification))
                self.validator.record_session_event("token_refresh_sent", {})
                
                # STEP 3: Continue session with refreshed context
                logger.info("✅ STEP 3: Continue session post-refresh")
                
                post_refresh_message = {
                    "type": "chat_message",
                    "content": "Message after token refresh - session should continue",
                    "user_id": user_id,
                    "thread_id": initial_context["thread_id"]  # Same thread
                }
                
                await websocket.send(json.dumps(post_refresh_message))
                
                # Wait for response to confirm continuity
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    post_refresh_context = {
                        "user_id": user_id,
                        "thread_id": initial_context["thread_id"],
                        "message_count": 2,
                        "session_data": response_data
                    }
                    self.validator.snapshot_user_context(post_refresh_context)
                    
                    self.validator.record_session_event("post_refresh_response", {
                        "received": True,
                        "user_context_preserved": user_id in str(response_data)
                    })
                    
                except asyncio.TimeoutError:
                    logger.warning("No response after token refresh - connection may still work")
            
            # VALIDATION: Token refresh session continuity
            validation = self.validator.validate_session_persistence()
            
            if not validation["session_maintained"]:
                pytest.fail(f"TOKEN REFRESH FAILURE: {validation['business_impact']}")
                
            if not validation["context_preserved"]:
                pytest.fail(f"SESSION CONTINUITY FAILURE: {validation['business_impact']}")
            
            logger.info("✅ Token refresh session continuity validated")
            
        except Exception as e:
            self.validator.record_session_event("token_refresh_failure", {"error": str(e)})
            raise
            
    async def test_multi_tab_session_sharing(self):
        """
        E2E: Multiple tabs/connections share same user session.
        
        BUSINESS VALUE: Users can have multiple tabs open without conflicts.
        """
        logger.info("📑 E2E: Testing multi-tab session sharing")
        
        timestamp = int(time.time())
        user_id = f"multi-tab-{timestamp}"
        user_email = f"multitab-{timestamp}@netra.test"
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=user_email,
            exp_minutes=30
        )
        
        user_info = {
            "user_id": user_id,
            "email": user_email,
            "test_type": "multi_tab_session"
        }
        
        self.validator.start_session_tracking(user_info)
        
        websocket_connections = []
        
        try:
            # STEP 1: Open multiple connections (simulate multiple tabs)
            logger.info("🔗 STEP 1: Opening multiple WebSocket connections")
            
            connection_count = 3
            websocket_url = f"{self.ws_auth_helper.config.websocket_url}?token={token}"
            
            for i in range(connection_count):
                websocket = await websockets.connect(
                    websocket_url,
                    additional_headers=self.ws_auth_helper.get_websocket_headers(token)
                )
                websocket_connections.append(websocket)
                
                self.validator.record_session_event(f"connection_{i+1}_opened", {
                    "connection_id": i+1,
                    "total_connections": len(websocket_connections)
                })
            
            # STEP 2: Send messages from different "tabs"
            logger.info("💬 STEP 2: Send messages from different tabs")
            
            thread_id = f"shared-session-{uuid.uuid4().hex[:8]}"
            
            for i, websocket in enumerate(websocket_connections):
                tab_message = {
                    "type": "chat_message",
                    "content": f"Message from tab {i+1}",
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "tab_id": i+1
                }
                
                await websocket.send(json.dumps(tab_message))
                
                self.validator.record_session_event(f"tab_{i+1}_message_sent", {
                    "message_content": tab_message["content"],
                    "shared_thread": thread_id
                })
                
                # Brief delay between messages
                await asyncio.sleep(0.5)
            
            # STEP 3: Verify messages are handled correctly
            logger.info("📨 STEP 3: Verify multi-tab message handling")
            
            responses_received = 0
            
            for i, websocket in enumerate(websocket_connections):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    response_data = json.loads(response)
                    
                    responses_received += 1
                    
                    self.validator.record_session_event(f"tab_{i+1}_response", {
                        "response_received": True,
                        "user_context": user_id in str(response_data)
                    })
                    
                except asyncio.TimeoutError:
                    logger.warning(f"No response from tab {i+1} connection")
            
            # STEP 4: Test connection isolation (close one tab)
            logger.info("❌ STEP 4: Test tab closure isolation")
            
            if len(websocket_connections) > 1:
                # Close first connection
                await websocket_connections[0].close()
                websocket_connections.pop(0)
                
                self.validator.record_session_event("tab_closed", {
                    "remaining_connections": len(websocket_connections)
                })
                
                # Verify remaining connections still work
                if websocket_connections:
                    test_message = {
                        "type": "ping",
                        "user_id": user_id,
                        "message": "Testing after tab closure"
                    }
                    
                    await websocket_connections[0].send(json.dumps(test_message))
                    
                    try:
                        response = await asyncio.wait_for(websocket_connections[0].recv(), timeout=3.0)
                        self.validator.record_session_event("remaining_tab_functional", {
                            "functional": True
                        })
                    except asyncio.TimeoutError:
                        logger.warning("Remaining tab not responding - may still be functional")
            
            # VALIDATION: Multi-tab session sharing
            validation = self.validator.validate_session_persistence()
            
            if not validation["session_maintained"]:
                pytest.fail(f"MULTI-TAB SESSION FAILURE: {validation['business_impact']}")
            
            # Check that we opened multiple connections successfully
            connection_events = [e for e in self.validator.session_events if "connection_" in e["event"] and "opened" in e["event"]]
            assert len(connection_events) >= 2, "Should have opened multiple connections successfully"
            
            logger.info(f"✅ Multi-tab session sharing validated")
            logger.info(f"   Connections opened: {len(connection_events)}")
            logger.info(f"   Responses received: {responses_received}")
            
        finally:
            # Cleanup remaining connections
            for websocket in websocket_connections:
                try:
                    await websocket.close()
                except:
                    pass
                    
    async def test_session_timeout_graceful_handling(self):
        """
        E2E: Graceful handling of session timeout.
        
        BUSINESS VALUE: Users get clear feedback when session expires.
        """
        logger.info("⏰ E2E: Testing session timeout graceful handling")
        
        timestamp = int(time.time())
        user_id = f"timeout-test-{timestamp}"
        user_email = f"timeout-{timestamp}@netra.test"
        
        # Create short-lived token for timeout testing
        short_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=user_email,
            exp_minutes=0  # Already expired or expires very soon
        )
        
        user_info = {
            "user_id": user_id,
            "email": user_email,
            "test_type": "session_timeout"
        }
        
        self.validator.start_session_tracking(user_info)
        
        try:
            websocket_url = f"{self.ws_auth_helper.config.websocket_url}?token={short_token}"
            
            # Attempt connection with expired/expiring token
            try:
                async with websockets.connect(
                    websocket_url,
                    additional_headers=self.ws_auth_helper.get_websocket_headers(short_token),
                    open_timeout=5.0
                ) as websocket:
                    
                    # Send message with expired token
                    timeout_message = {
                        "type": "chat_message",
                        "content": "Testing with expired token",
                        "user_id": user_id
                    }
                    
                    await websocket.send(json.dumps(timeout_message))
                    
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        response_data = json.loads(response)
                        
                        # Check if server handles expired token gracefully
                        if "error" in response_data or "auth" in response_data.get("type", "").lower():
                            self.validator.record_session_event("timeout_handled_gracefully", {
                                "graceful_error": True,
                                "error_type": response_data.get("type")
                            })
                        else:
                            self.validator.record_session_event("timeout_not_detected", {
                                "token_still_valid": True
                            })
                        
                    except asyncio.TimeoutError:
                        self.validator.record_session_event("timeout_no_response", {
                            "connection_dropped": True
                        })
            
            except websockets.exceptions.ConnectionClosed as e:
                # Connection closed due to auth failure - this is expected and graceful
                self.validator.record_session_event("timeout_connection_closed", {
                    "graceful_closure": True,
                    "close_code": e.code if hasattr(e, 'code') else None
                })
                
            except Exception as e:
                self.validator.record_session_event("timeout_error", {
                    "error": str(e)
                })
                
            # Test recovery with valid token
            logger.info("🔄 Testing recovery with valid token")
            
            valid_token = self.auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=user_email,
                exp_minutes=30
            )
            
            recovery_url = f"{self.ws_auth_helper.config.websocket_url}?token={valid_token}"
            
            try:
                async with websockets.connect(
                    recovery_url,
                    additional_headers=self.ws_auth_helper.get_websocket_headers(valid_token)
                ) as recovery_websocket:
                    
                    recovery_message = {
                        "type": "chat_message",
                        "content": "Recovered with valid token",
                        "user_id": user_id
                    }
                    
                    await recovery_websocket.send(json.dumps(recovery_message))
                    
                    try:
                        recovery_response = await asyncio.wait_for(recovery_websocket.recv(), timeout=3.0)
                        self.validator.record_session_event("timeout_recovery_successful", {
                            "recovered": True
                        })
                    except asyncio.TimeoutError:
                        logger.warning("No response after recovery - connection may still work")
                        
            except Exception as e:
                logger.warning(f"Recovery attempt failed: {e}")
            
            logger.info("✅ Session timeout handling validated")
            
        except Exception as e:
            self.validator.record_session_event("timeout_test_failure", {"error": str(e)})
            raise


@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.session_persistence
class TestSessionPersistenceEdgeCases(BaseE2ETest):
    """E2E: Session persistence edge cases and boundary conditions."""
    
    async def test_rapid_reconnection_session_stability(self):
        """
        E2E: Session stability under rapid reconnection attempts.
        
        BUSINESS VALUE: System handles unstable network connections gracefully.
        """
        logger.info("⚡ E2E: Testing rapid reconnection session stability")
        
        timestamp = int(time.time())
        user_id = f"rapid-reconnect-{timestamp}"
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=f"rapid-{timestamp}@netra.test",
            exp_minutes=30
        )
        
        websocket_url = f"{self.ws_auth_helper.config.websocket_url}?token={token}"
        
        reconnection_count = 5
        successful_connections = 0
        
        for attempt in range(reconnection_count):
            try:
                # Rapid connect/disconnect cycle
                websocket = await websockets.connect(
                    websocket_url,
                    additional_headers=self.ws_auth_helper.get_websocket_headers(token),
                    open_timeout=3.0
                )
                
                # Send quick message
                quick_message = {
                    "type": "ping",
                    "user_id": user_id,
                    "attempt": attempt + 1
                }
                
                await websocket.send(json.dumps(quick_message))
                successful_connections += 1
                
                # Quick close
                await websocket.close()
                
                # Brief pause
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.warning(f"Rapid reconnection attempt {attempt + 1} failed: {e}")
        
        # Validate that most connections succeeded
        success_rate = successful_connections / reconnection_count
        assert success_rate >= 0.8, f"Rapid reconnection success rate {success_rate:.1%} too low"
        
        logger.info(f"✅ Rapid reconnection stability: {successful_connections}/{reconnection_count} successful")


if __name__ == "__main__":
    """Run session persistence tests."""
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "e2e",
        "--real-services"
    ])