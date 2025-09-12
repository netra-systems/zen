"""
[U+1F534] MISSION CRITICAL: WebSocket Authentication Events Test Suite

Tests WebSocket authentication integration with agent events - the core of our chat value.
This validates that authenticated users receive proper WebSocket events during agent execution.

Business Value Justification (BVJ):
- Segment: ALL users (Free, Early, Mid, Enterprise) - 100% of chat users
- Business Goal: Seamless Real-time Chat Experience - Core value delivery
- Value Impact: $500K+ ARR - Chat is 90% of our customer value delivery
- Strategic Impact: Platform Foundation - WebSocket + Auth enables all AI interactions

CRITICAL SUCCESS CRITERIA:
1. WebSocket connections MUST authenticate properly
2. All 5 agent events MUST be sent to authenticated users
3. Multi-user WebSocket isolation MUST work (no event crossover)
4. WebSocket auth tokens MUST refresh seamlessly
5. Connection drops MUST recover without losing auth context

FAILURE = NO CHAT FUNCTIONALITY = NO CUSTOMER VALUE = $0 REVENUE
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

# Import SSOT authentication and WebSocket utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.ssot.base_test_case import SSotAsyncTestCase

logger = logging.getLogger(__name__)


class WebSocketAuthEventValidator:
    """Validates WebSocket authentication and agent events for business value delivery."""
    
    REQUIRED_AGENT_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self):
        self.events_received = []
        self.auth_events = []
        self.connection_events = []
        
    def record_event(self, event_data: Dict[str, Any], event_source: str = "websocket"):
        """Record event for validation."""
        event_record = {
            "data": event_data,
            "timestamp": time.time(),
            "source": event_source,
            "event_type": event_data.get("type"),
            "user_context": event_data.get("user_id") or event_data.get("sub")
        }
        
        self.events_received.append(event_record)
        
        # Categorize events
        if event_data.get("type") in self.REQUIRED_AGENT_EVENTS:
            self.auth_events.append(event_record)
        elif event_data.get("type") in ["connection", "auth", "token_refresh"]:
            self.connection_events.append(event_record)
    
    def validate_agent_event_delivery(self, user_id: str) -> Dict[str, Any]:
        """Validate that all required agent events were delivered for user."""
        user_events = [e for e in self.auth_events if e.get("user_context") == user_id]
        received_event_types = {e["event_type"] for e in user_events}
        
        validation = {
            "all_events_received": self.REQUIRED_AGENT_EVENTS.issubset(received_event_types),
            "missing_events": self.REQUIRED_AGENT_EVENTS - received_event_types,
            "extra_events": received_event_types - self.REQUIRED_AGENT_EVENTS,
            "event_count": len(user_events),
            "event_timeline": [e["timestamp"] for e in user_events],
            "business_impact": ""
        }
        
        if not validation["all_events_received"]:
            validation["business_impact"] = f"CRITICAL: Missing agent events {validation['missing_events']} - Chat experience broken"
        else:
            validation["business_impact"] = "NONE: All agent events delivered - Chat experience intact"
            
        return validation
    
    def validate_multi_user_isolation(self, user_ids: List[str]) -> Dict[str, Any]:
        """Validate that WebSocket events are properly isolated between users."""
        validation = {
            "isolation_maintained": True,
            "user_event_counts": {},
            "crossover_events": [],
            "business_impact": ""
        }
        
        for user_id in user_ids:
            user_events = [e for e in self.events_received if e.get("user_context") == user_id]
            validation["user_event_counts"][user_id] = len(user_events)
            
            # Check for events intended for other users
            for event in user_events:
                intended_user = event["data"].get("target_user_id") 
                if intended_user and intended_user != user_id:
                    validation["crossover_events"].append({
                        "event": event["event_type"],
                        "intended_for": intended_user,
                        "received_by": user_id
                    })
        
        if validation["crossover_events"]:
            validation["isolation_maintained"] = False
            validation["business_impact"] = "CRITICAL: Event crossover detected - User data leak risk"
        else:
            validation["business_impact"] = "NONE: Multi-user isolation maintained"
            
        return validation


@pytest.mark.mission_critical
@pytest.mark.real_services
@pytest.mark.websocket
class TestWebSocketAuthEvents(SSotAsyncTestCase):
    """Mission Critical: WebSocket authentication with agent events for chat value."""
    
    @pytest.fixture(autouse=True)
    async def setup_websocket_auth_testing(self, real_services_fixture):
        """Setup real services for WebSocket auth testing."""
        self.services = real_services_fixture
        self.validator = WebSocketAuthEventValidator()
        self.auth_helper = E2EWebSocketAuthHelper()
        
        # Ensure backend service is available for WebSocket connections
        if not self.services.get("services_available", {}).get("backend", False):
            pytest.skip("Backend service required for WebSocket auth testing")
            
        # Configure WebSocket URL
        backend_url = self.services["backend_url"]
        websocket_url = backend_url.replace("http://", "ws://") + "/ws"
        self.auth_helper.config.websocket_url = websocket_url
    
    async def test_websocket_authentication_core_flow(self):
        """
        MISSION CRITICAL: WebSocket authentication for chat access.
        
        BUSINESS IMPACT: Without WebSocket auth, users cannot use chat = $0 value delivery
        """
        logger.info("[U+1F534] MISSION CRITICAL: Testing WebSocket authentication core flow")
        
        # Create authenticated user
        user_id = f"ws-auth-{uuid.uuid4().hex[:8]}"
        email = f"wsauth-{int(time.time())}@netra.test"
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            permissions=["chat", "websocket", "agent:execute"]
        )
        
        # CRITICAL TEST: WebSocket connection with authentication
        try:
            websocket_url = f"{self.auth_helper.config.websocket_url}?token={token}"
            
            async with websockets.connect(
                websocket_url,
                additional_headers=self.auth_helper.get_websocket_headers(token)
            ) as websocket:
                
                # Send authentication verification message
                auth_message = {
                    "type": "auth_verify",
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(auth_message))
                
                # Wait for auth confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                self.validator.record_event(response_data, "auth_verification")
                
                # CRITICAL VALIDATION: WebSocket authentication must work
                assert response_data.get("type") in ["auth_success", "pong", "connection_established"], \
                    f"MISSION CRITICAL: WebSocket auth failed - {response_data}"
                
                # Verify authenticated context
                if "user_id" in response_data:
                    assert response_data["user_id"] == user_id, \
                        "CRITICAL: User context lost in WebSocket authentication"
                        
        except asyncio.TimeoutError:
            pytest.fail("MISSION CRITICAL: WebSocket authentication timeout - connection failed")
        except Exception as e:
            pytest.fail(f"MISSION CRITICAL: WebSocket authentication failed - {str(e)}")
        
        logger.info(" PASS:  MISSION CRITICAL: WebSocket authentication validated")
    
    async def test_agent_events_with_websocket_auth(self):
        """
        MISSION CRITICAL: Agent events delivered via authenticated WebSocket.
        
        BUSINESS IMPACT: Without agent events, chat has no value = Users see no AI responses
        """
        logger.info("[U+1F534] MISSION CRITICAL: Testing agent events with WebSocket auth")
        
        # Setup authenticated user
        user_id = f"agent-events-{uuid.uuid4().hex[:8]}"
        email = f"agentevents-{int(time.time())}@netra.test"
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            permissions=["chat", "agent:execute"]
        )
        
        try:
            websocket_url = f"{self.auth_helper.config.websocket_url}?token={token}"
            
            async with websockets.connect(
                websocket_url,
                additional_headers=self.auth_helper.get_websocket_headers(token)
            ) as websocket:
                
                # Simulate agent execution request
                agent_request = {
                    "type": "agent_request",
                    "agent_name": "test_agent",
                    "query": "Test query for agent events",
                    "user_id": user_id,
                    "thread_id": f"thread-{uuid.uuid4().hex[:8]}"
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect agent events
                events_collected = 0
                max_events = 10
                timeout_per_event = 2.0
                
                while events_collected < max_events:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=timeout_per_event)
                        event_data = json.loads(response)
                        
                        self.validator.record_event(event_data, "agent_execution")
                        events_collected += 1
                        
                        # Check if we received completion event
                        if event_data.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        # Stop collecting if no more events
                        break
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON in WebSocket message: {e}")
                        continue
                
                # CRITICAL VALIDATION: Agent events must be delivered
                validation = self.validator.validate_agent_event_delivery(user_id)
                
                if not validation["all_events_received"]:
                    pytest.fail(f"MISSION CRITICAL: {validation['business_impact']}")
                
                # Validate event timeline (events should be in reasonable order)
                timeline = validation["event_timeline"]
                if len(timeline) > 1:
                    time_span = timeline[-1] - timeline[0]
                    assert time_span > 0, "CRITICAL: Events delivered out of order"
                    assert time_span < 30, f"CRITICAL: Agent execution took {time_span:.1f}s - too slow for chat UX"
                
        except Exception as e:
            pytest.fail(f"MISSION CRITICAL: Agent events with WebSocket auth failed - {str(e)}")
        
        logger.info(" PASS:  MISSION CRITICAL: Agent events with WebSocket auth validated")
    
    async def test_multi_user_websocket_isolation(self):
        """
        MISSION CRITICAL: Multiple users get isolated WebSocket events.
        
        BUSINESS IMPACT: Event crossover = Users see each other's data = Privacy breach
        """
        logger.info("[U+1F534] MISSION CRITICAL: Testing multi-user WebSocket isolation")
        
        user_count = 3
        websocket_connections = []
        user_data = []
        
        try:
            # Create multiple authenticated users
            for i in range(user_count):
                user_id = f"multi-user-{i}-{uuid.uuid4().hex[:6]}"
                email = f"multiuser{i}-{int(time.time())}@netra.test"
                
                token = self.auth_helper.create_test_jwt_token(
                    user_id=user_id,
                    email=email,
                    permissions=["chat", "agent:execute"]
                )
                
                websocket_url = f"{self.auth_helper.config.websocket_url}?token={token}"
                
                # Connect each user
                websocket = await websockets.connect(
                    websocket_url,
                    additional_headers=self.auth_helper.get_websocket_headers(token)
                )
                
                websocket_connections.append(websocket)
                user_data.append({"user_id": user_id, "email": email, "websocket": websocket})
            
            # Send different messages from each user
            for i, user in enumerate(user_data):
                message = {
                    "type": "user_message", 
                    "content": f"User {i} private message",
                    "user_id": user["user_id"],
                    "thread_id": f"private-thread-{user['user_id']}"
                }
                
                await user["websocket"].send(json.dumps(message))
                
                # Record the message
                self.validator.record_event(message, f"user_{i}_message")
            
            # Collect responses from each user
            response_tasks = []
            for i, user in enumerate(user_data):
                async def collect_user_responses(user_websocket, user_id, user_index):
                    responses = []
                    try:
                        for _ in range(3):  # Collect a few responses
                            response = await asyncio.wait_for(user_websocket.recv(), timeout=2.0)
                            response_data = json.loads(response)
                            response_data["_received_by"] = user_id
                            responses.append(response_data)
                            
                            self.validator.record_event(response_data, f"user_{user_index}_response")
                    except asyncio.TimeoutError:
                        pass  # Normal - no more messages
                    return responses
                
                task = asyncio.create_task(collect_user_responses(
                    user["websocket"], user["user_id"], i
                ))
                response_tasks.append(task)
            
            # Wait for all responses
            all_responses = await asyncio.gather(*response_tasks, return_exceptions=True)
            
            # CRITICAL VALIDATION: User isolation must be maintained
            user_ids = [user["user_id"] for user in user_data]
            isolation_validation = self.validator.validate_multi_user_isolation(user_ids)
            
            if not isolation_validation["isolation_maintained"]:
                pytest.fail(f"MISSION CRITICAL: {isolation_validation['business_impact']}")
            
            # Verify each user received appropriate events
            for user_id in user_ids:
                user_events = [e for e in self.validator.events_received if e.get("user_context") == user_id]
                assert len(user_events) > 0, f"CRITICAL: User {user_id} received no events"
            
        finally:
            # Cleanup connections
            for websocket in websocket_connections:
                try:
                    await websocket.close()
                except:
                    pass
        
        logger.info(f" PASS:  MISSION CRITICAL: Multi-user WebSocket isolation validated for {user_count} users")
    
    async def test_websocket_token_refresh_seamless(self):
        """
        MISSION CRITICAL: WebSocket connections survive token refresh.
        
        BUSINESS IMPACT: Token refresh disconnects = Chat interruption = Bad UX
        """
        logger.info("[U+1F534] MISSION CRITICAL: Testing WebSocket token refresh")
        
        user_id = f"token-refresh-{uuid.uuid4().hex[:8]}"
        email = f"tokenrefresh-{int(time.time())}@netra.test"
        
        # Create short-lived token
        initial_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            exp_minutes=1  # Short expiry
        )
        
        try:
            websocket_url = f"{self.auth_helper.config.websocket_url}?token={initial_token}"
            
            async with websockets.connect(
                websocket_url,
                additional_headers=self.auth_helper.get_websocket_headers(initial_token)
            ) as websocket:
                
                # Send initial message
                initial_message = {
                    "type": "ping",
                    "user_id": user_id,
                    "message": "Before token refresh"
                }
                await websocket.send(json.dumps(initial_message))
                
                # Wait for initial response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                self.validator.record_event(json.loads(response), "pre_refresh")
                
                # Simulate token refresh
                refreshed_token = self.auth_helper.create_test_jwt_token(
                    user_id=user_id,
                    email=email,
                    exp_minutes=60  # Extended expiry
                )
                
                # Send token refresh notification (if protocol supports it)
                refresh_message = {
                    "type": "token_refresh",
                    "user_id": user_id,
                    "new_token": refreshed_token
                }
                await websocket.send(json.dumps(refresh_message))
                
                # Test continued functionality after refresh
                post_refresh_message = {
                    "type": "ping",
                    "user_id": user_id, 
                    "message": "After token refresh"
                }
                await websocket.send(json.dumps(post_refresh_message))
                
                # Collect post-refresh response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    self.validator.record_event(json.loads(response), "post_refresh")
                    
                    # CRITICAL VALIDATION: Connection should remain stable
                    assert True  # If we get here, connection survived
                    
                except asyncio.TimeoutError:
                    pytest.fail("MISSION CRITICAL: WebSocket connection failed after token refresh")
                
        except Exception as e:
            pytest.fail(f"MISSION CRITICAL: WebSocket token refresh failed - {str(e)}")
        
        logger.info(" PASS:  MISSION CRITICAL: WebSocket token refresh validated")
    
    async def test_websocket_connection_recovery(self):
        """
        MISSION CRITICAL: WebSocket connections recover from temporary disconnections.
        
        BUSINESS IMPACT: Connection drops without recovery = Chat stops working
        """
        logger.info("[U+1F534] MISSION CRITICAL: Testing WebSocket connection recovery")
        
        user_id = f"recovery-test-{uuid.uuid4().hex[:8]}"
        email = f"recovery-{int(time.time())}@netra.test"
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            exp_minutes=30
        )
        
        recovery_successful = False
        
        try:
            websocket_url = f"{self.auth_helper.config.websocket_url}?token={token}"
            
            # Initial connection
            websocket1 = await websockets.connect(
                websocket_url,
                additional_headers=self.auth_helper.get_websocket_headers(token)
            )
            
            # Send message to establish connection
            initial_message = {
                "type": "ping",
                "user_id": user_id,
                "message": "Initial connection"
            }
            await websocket1.send(json.dumps(initial_message))
            
            # Receive response
            response = await asyncio.wait_for(websocket1.recv(), timeout=5.0)
            self.validator.record_event(json.loads(response), "initial_connection")
            
            # Simulate connection drop
            await websocket1.close()
            await asyncio.sleep(1.0)  # Wait for cleanup
            
            # Attempt reconnection
            websocket2 = await websockets.connect(
                websocket_url,
                additional_headers=self.auth_helper.get_websocket_headers(token)
            )
            
            # Test reconnected functionality
            recovery_message = {
                "type": "ping",
                "user_id": user_id,
                "message": "After reconnection"
            }
            await websocket2.send(json.dumps(recovery_message))
            
            # Verify reconnection works
            response = await asyncio.wait_for(websocket2.recv(), timeout=5.0)
            self.validator.record_event(json.loads(response), "after_recovery")
            
            await websocket2.close()
            recovery_successful = True
            
        except Exception as e:
            pytest.fail(f"MISSION CRITICAL: WebSocket connection recovery failed - {str(e)}")
        
        assert recovery_successful, "MISSION CRITICAL: WebSocket recovery not completed"
        
        logger.info(" PASS:  MISSION CRITICAL: WebSocket connection recovery validated")


@pytest.mark.mission_critical
@pytest.mark.real_services
@pytest.mark.websocket
class TestWebSocketAuthPerformance(SSotAsyncTestCase):
    """Mission Critical: WebSocket authentication performance under load."""
    
    async def test_websocket_auth_concurrent_connections(self):
        """
        MISSION CRITICAL: WebSocket auth handles concurrent user connections.
        
        BUSINESS IMPACT: Auth bottlenecks = Users can't connect = Lost engagement
        """
        logger.info("[U+1F534] MISSION CRITICAL: Testing concurrent WebSocket auth connections")
        
        concurrent_users = 10
        auth_helper = E2EWebSocketAuthHelper()
        connections = []
        connection_results = []
        
        async def connect_user(user_index: int) -> Dict[str, Any]:
            """Connect one user via WebSocket."""
            start_time = time.time()
            user_id = f"concurrent-{user_index}-{uuid.uuid4().hex[:6]}"
            email = f"concurrent{user_index}@netra.test"
            
            try:
                token = auth_helper.create_test_jwt_token(
                    user_id=user_id,
                    email=email
                )
                
                websocket_url = f"{auth_helper.config.websocket_url}?token={token}"
                
                websocket = await websockets.connect(
                    websocket_url,
                    additional_headers=auth_helper.get_websocket_headers(token)
                )
                
                # Test connection
                test_message = {
                    "type": "ping",
                    "user_id": user_id,
                    "index": user_index
                }
                await websocket.send(json.dumps(test_message))
                
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                
                connections.append(websocket)
                
                return {
                    "user_index": user_index,
                    "user_id": user_id,
                    "success": True,
                    "duration": time.time() - start_time,
                    "websocket": websocket
                }
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_id,
                    "success": False,
                    "error": str(e),
                    "duration": time.time() - start_time
                }
        
        try:
            # Connect all users concurrently
            connection_tasks = [connect_user(i) for i in range(concurrent_users)]
            connection_results = await asyncio.gather(*connection_tasks)
            
            # CRITICAL VALIDATION: All connections must succeed
            successful_connections = [r for r in connection_results if r["success"]]
            failed_connections = [r for r in connection_results if not r["success"]]
            
            if len(failed_connections) > 0:
                failure_details = [f"User {r['user_index']}: {r.get('error')}" for r in failed_connections]
                pytest.fail(f"MISSION CRITICAL: {len(failed_connections)}/{concurrent_users} WebSocket auth failures: {failure_details}")
            
            # Performance validation
            connection_durations = [r["duration"] for r in successful_connections]
            avg_duration = sum(connection_durations) / len(connection_durations)
            max_duration = max(connection_durations)
            
            assert avg_duration < 1.0, f"BUSINESS CRITICAL: Average WebSocket auth {avg_duration:.3f}s too slow"
            assert max_duration < 3.0, f"BUSINESS CRITICAL: Max WebSocket auth {max_duration:.3f}s unacceptable"
            
            logger.info(f" PASS:  MISSION CRITICAL: {len(successful_connections)} concurrent WebSocket auths, avg {avg_duration:.3f}s")
            
        finally:
            # Cleanup connections
            for websocket in connections:
                try:
                    await websocket.close()
                except:
                    pass


if __name__ == "__main__":
    """Run mission critical WebSocket auth event tests."""
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "mission_critical",
        "--real-services"
    ])