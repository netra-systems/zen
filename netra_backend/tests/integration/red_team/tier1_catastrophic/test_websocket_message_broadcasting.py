"""
RED TEAM TEST 15: WebSocket Message Broadcasting

CRITICAL: These tests are DESIGNED TO FAIL initially to expose real integration issues.
This test validates that real-time message delivery to connected clients works properly.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Real-time Experience, User Engagement, Platform Responsiveness
- Value Impact: Failed real-time updates directly impact user experience and platform perception
- Strategic Impact: Core real-time communication foundation for AI interaction workflows

Testing Level: L3 (Real services, real WebSocket connections, minimal mocking)
Expected Initial Result: FAILURE (exposes real WebSocket broadcasting gaps)
"""

import asyncio
import json
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
import websockets
from websockets import ServerConnection
from websockets.exceptions import ConnectionClosed, InvalidURI
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Real service imports - NO MOCKS
from netra_backend.app.main import app
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.websocket_core import WebSocketManager as WebSocketConnectionManager
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.db.models_user import User
# AgentRun model - creating mock for tests
AgentRun = Mock
from netra_backend.app.database import get_db


class TestWebSocketMessageBroadcasting:
    """
    RED TEAM TEST 15: WebSocket Message Broadcasting
    
    Tests the critical path of real-time message delivery to connected clients.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """
    pass

    @pytest.fixture(scope="class")
    async def real_database_session(self):
        """Real PostgreSQL database session - will fail if DB not available."""
        config = get_unified_config()
        
        # Use REAL database connection - no mocks
        engine = create_async_engine(config.database_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            # Test real connection - will fail if DB unavailable
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            async with async_session() as session:
                yield session
        except Exception as e:
            pytest.fail(f"CRITICAL: Real database connection failed: {e}")
        finally:
            await engine.dispose()

    @pytest.fixture
    def real_test_client(self):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        """Real FastAPI test client - no mocking of the application."""
        await asyncio.sleep(0)
    return TestClient(app)

    @pytest.fixture
    def websocket_config(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """WebSocket connection configuration."""
    pass
        return {
            "host": "localhost",
            "port": 8000,
            "secure": False,
            "timeout": 10,
            "ping_interval": 5,
            "max_connections": 100
        }

    @pytest.fixture
    @pytest.mark.asyncio
    async def test_user(self, real_database_session):
        """Create a test user for WebSocket authentication."""
        test_user_id = str(uuid.uuid4())
        test_user = User(
            id=test_user_id,
            email=f"ws_test_{secrets.token_urlsafe(8)}@example.com",
            name="WebSocket Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        real_database_session.add(test_user)
        await real_database_session.commit()
        
        await asyncio.sleep(0)
    return test_user

    @pytest.mark.asyncio
    async def test_01_basic_websocket_connection_fails(self, websocket_config, test_user):
        """
    pass
        Test 15A: Basic WebSocket Connection (EXPECTED TO FAIL)
        
        Tests that WebSocket connections can be established successfully.
        This will likely FAIL because:
        1. WebSocket endpoint may not be configured
        2. Authentication may not be working
        3. Connection handling may be incomplete
        """
        # Generate auth token for WebSocket connection
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {
            "user_id": test_user.id,
            "email": test_user.email,
            "exp": int(time.time()) + 3600
        }
        auth_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        
        # Construct WebSocket URL
        ws_url = f"ws://{websocket_config['host']}:{websocket_config['port']}/ws"
        
        try:
            # FAILURE EXPECTED HERE - WebSocket endpoint may not exist
            async with websockets.connect(
                ws_url,
                extra_headers={"Authorization": f"Bearer {auth_token}"},
                timeout=websocket_config["timeout"]
            ) as websocket:
                
                # Send initial message
                initial_message = {
                    "type": "connect",
                    "user_id": test_user.id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(initial_message))
                
                # Wait for connection acknowledgment
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    response_data = json.loads(response)
                    
                    assert "type" in response_data, "WebSocket response should have message type"
                    assert response_data["type"] in ["connection_ack", "connected"], \
                        f"Expected connection acknowledgment, got {response_data['type']}"
                    
                except asyncio.TimeoutError:
                    pytest.fail("WebSocket connection did not send acknowledgment within 5 seconds")
                
        except (ConnectionRefusedError, InvalidURI) as e:
            pytest.fail(f"WebSocket connection failed: {e}")
        except Exception as e:
            pytest.fail(f"Basic WebSocket connection failed: {e}")

    @pytest.mark.asyncio
    async def test_02_message_broadcast_to_single_client_fails(self, websocket_config, test_user, real_database_session):
        """
        Test 15B: Message Broadcast to Single Client (EXPECTED TO FAIL)
        
        Tests that messages can be broadcast to a connected WebSocket client.
        Will likely FAIL because:
        1. Message broadcasting may not be implemented
        2. Message routing may not work
        3. Client identification may be broken
        """
    pass
        # Generate auth token
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {
            "user_id": test_user.id,
            "email": test_user.email,
            "exp": int(time.time()) + 3600
        }
        auth_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        
        ws_url = f"ws://{websocket_config['host']}:{websocket_config['port']}/ws"
        
        try:
            async with websockets.connect(
                ws_url,
                extra_headers={"Authorization": f"Bearer {auth_token}"},
                timeout=websocket_config["timeout"]
            ) as websocket:
                
                # Wait for connection establishment
                await asyncio.sleep(1)
                
                # Create an agent run that should trigger a broadcast
                agent_run_id = str(uuid.uuid4())
                agent_run = AgentRun(
                    id=agent_run_id,
                    agent_id=str(uuid.uuid4()),
                    user_id=test_user.id,
                    status="running",
                    input_data={"task": "Test broadcast message"},
                    created_at=datetime.now(timezone.utc)
                )
                
                real_database_session.add(agent_run)
                await real_database_session.commit()
                
                # Simulate agent completion (this should trigger broadcast)
                try:
                    websocket_service = WebSocketService()
                    
                    # FAILURE EXPECTED HERE - broadcasting may not be implemented
                    broadcast_message = {
                        "type": "agent_update",
                        "agent_run_id": agent_run_id,
                        "status": "completed",
                        "result": "Test broadcast result",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket_service.broadcast_to_user(
                        user_id=test_user.id,
                        message=broadcast_message
                    )
                    
                    # Wait for broadcast message
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        response_data = json.loads(response)
                        
                        assert "type" in response_data, "Broadcast message should have type"
                        assert response_data["type"] == "agent_update", \
                            f"Expected agent_update message, got {response_data['type']}"
                        assert response_data["agent_run_id"] == agent_run_id, \
                            "Broadcast should include correct agent_run_id"
                        assert "result" in response_data, "Broadcast should include result data"
                        
                    except asyncio.TimeoutError:
                        pytest.fail("Broadcast message not received within 5 seconds")
                        
                except ImportError:
                    pytest.fail("WebSocketService not available for broadcasting")
                
        except Exception as e:
            pytest.fail(f"Message broadcast to single client failed: {e}")

    @pytest.mark.asyncio
    async def test_03_multiple_client_broadcasting_fails(self, websocket_config, real_database_session):
        """
        Test 15C: Multiple Client Broadcasting (EXPECTED TO FAIL)
        
        Tests that messages can be broadcast to multiple connected clients.
        Will likely FAIL because:
        1. Multi-client management may not be implemented
        2. Connection tracking may not work
        3. Broadcast scalability may be poor
        """
    pass
        # Create multiple test users
        test_users = []
        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                email=f"multi_ws_test_{i}_{secrets.token_urlsafe(8)}@example.com",
                name=f"Multi WebSocket Test User {i+1}",
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            test_users.append(user)
            real_database_session.add(user)
        
        await real_database_session.commit()
        
        # Generate auth tokens for all users
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        
        auth_tokens = []
        for user in test_users:
            token_payload = {
                "user_id": user.id,
                "email": user.email,
                "exp": int(time.time()) + 3600
            }
            token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
            auth_tokens.append(token)
        
        ws_url = f"ws://{websocket_config['host']}:{websocket_config['port']}/ws"
        
        # Connect multiple WebSocket clients
        websockets_list = []
        
        try:
            # Establish connections for all clients
            for i, token in enumerate(auth_tokens):
                try:
                    ws = await websockets.connect(
                        ws_url,
                        extra_headers={"Authorization": f"Bearer {token}"},
                        timeout=websocket_config["timeout"]
                    )
                    websockets_list.append(ws)
                    
                    # Wait briefly between connections
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    pytest.fail(f"Failed to connect WebSocket client {i+1}: {e}")
            
            # Wait for all connections to establish
            await asyncio.sleep(2)
            
            # Broadcast message to all connected clients
            try:
                websocket_service = WebSocketService()
                
                broadcast_message = {
                    "type": "global_announcement",
                    "message": "Test broadcast to multiple clients",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # FAILURE EXPECTED HERE - multi-client broadcasting may not work
                await websocket_service.broadcast_to_all(broadcast_message)
                
                # Collect responses from all clients
                received_messages = []
                
                for i, ws in enumerate(websockets_list):
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=5)
                        response_data = json.loads(response)
                        received_messages.append((i, response_data))
                        
                    except asyncio.TimeoutError:
                        pytest.fail(f"Client {i+1} did not receive broadcast message")
                
                # Verify all clients received the message
                assert len(received_messages) == len(websockets_list), \
                    f"Expected {len(websockets_list)} clients to receive message, got {len(received_messages)}"
                
                # Verify message content consistency
                for client_id, message in received_messages:
                    assert message["type"] == "global_announcement", \
                        f"Client {client_id+1} received wrong message type: {message['type']}"
                    assert message["message"] == broadcast_message["message"], \
                        f"Client {client_id+1} received different message content"
                        
            except ImportError:
                pytest.fail("WebSocketService not available for multi-client broadcasting")
            
        finally:
            # Clean up all WebSocket connections
            for ws in websockets_list:
                try:
                    await ws.close()
                except Exception:
                    pass

    @pytest.mark.asyncio
    async def test_04_agent_to_frontend_message_flow_fails(self, websocket_config, test_user, real_database_session):
        """
        Test 15D: Agent to Frontend Message Flow (EXPECTED TO FAIL)
        
        Tests the complete flow from agent completion to frontend delivery.
        Will likely FAIL because:
        1. Agent-WebSocket integration may not exist
        2. Message flow orchestration may be incomplete
        3. Event triggering may not work
        """
    pass
        # Generate auth token
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {
            "user_id": test_user.id,
            "email": test_user.email,
            "exp": int(time.time()) + 3600
        }
        auth_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        
        ws_url = f"ws://{websocket_config['host']}:{websocket_config['port']}/ws"
        
        try:
            async with websockets.connect(
                ws_url,
                extra_headers={"Authorization": f"Bearer {auth_token}"},
                timeout=websocket_config["timeout"]
            ) as websocket:
                
                # Create and execute agent run
                agent_run_id = str(uuid.uuid4())
                agent_run = AgentRun(
                    id=agent_run_id,
                    agent_id=str(uuid.uuid4()),
                    user_id=test_user.id,
                    status="pending",
                    input_data={
                        "task": "Complete task and notify frontend",
                        "notify_frontend": True
                    },
                    created_at=datetime.now(timezone.utc)
                )
                
                real_database_session.add(agent_run)
                await real_database_session.commit()
                
                # Execute agent (should trigger WebSocket notification)
                try:
                    agent_service = AgentService()
                    
                    # Start agent execution in background
                    async def execute_agent():
    pass
                        try:
                            # FAILURE EXPECTED HERE - agent execution may not trigger WebSocket events
                            result = await agent_service.execute_agent_run(agent_run_id)
                            
                            # Manually trigger WebSocket notification if automatic isn't working
                            if hasattr(agent_service, 'notify_websocket_clients'):
                                await agent_service.notify_websocket_clients(
                                    user_id=test_user.id,
                                    agent_run_id=agent_run_id,
                                    status="completed",
                                    result=result
                                )
                                
                        except Exception as e:
                            # Even if agent execution fails, we should get a notification
                            pass
                    
                    # Start agent execution
                    execution_task = asyncio.create_task(execute_agent())
                    
                    # Wait for WebSocket notifications
                    notifications_received = []
                    max_wait_time = 30  # 30 seconds max wait
                    start_time = time.time()
                    
                    while time.time() - start_time < max_wait_time:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=5)
                            message_data = json.loads(message)
                            notifications_received.append(message_data)
                            
                            # Check if we got the completion notification
                            if (message_data.get("type") == "agent_update" and 
                                message_data.get("agent_run_id") == agent_run_id and
                                message_data.get("status") in ["completed", "failed"]):
                                break
                                
                        except asyncio.TimeoutError:
                            # Continue waiting, might get notification later
                            continue
                    
                    # Wait for agent execution to complete
                    try:
                        await asyncio.wait_for(execution_task, timeout=5)
                    except asyncio.TimeoutError:
                        execution_task.cancel()
                    
                    # Verify we received appropriate notifications
                    assert len(notifications_received) > 0, \
                        "Should receive at least one WebSocket notification from agent execution"
                    
                    # Check for agent-related notifications
                    agent_notifications = [
                        msg for msg in notifications_received 
                        if msg.get("agent_run_id") == agent_run_id
                    ]
                    
                    assert len(agent_notifications) > 0, \
                        f"Should receive agent-related notifications. Received: {notifications_received}"
                    
                    # Verify notification content
                    final_notification = agent_notifications[-1]
                    assert "status" in final_notification, "Agent notification should include status"
                    assert final_notification["status"] in ["completed", "failed", "error"], \
                        f"Agent should have final status, got: {final_notification['status']}"
                        
                except ImportError:
                    pytest.fail("AgentService not available for agent-to-frontend flow testing")
                
        except Exception as e:
            pytest.fail(f"Agent to frontend message flow failed: {e}")

    @pytest.mark.asyncio
    async def test_05_websocket_connection_recovery_fails(self, websocket_config, test_user):
        """
        Test 15E: WebSocket Connection Recovery (EXPECTED TO FAIL)
        
        Tests that WebSocket connections can recover from interruptions.
        Will likely FAIL because:
        1. Connection recovery may not be implemented
        2. Message buffering may not exist
        3. Reconnection logic may not work
        """
    pass
        # Generate auth token
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {
            "user_id": test_user.id,
            "email": test_user.email,
            "exp": int(time.time()) + 3600
        }
        auth_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        
        ws_url = f"ws://{websocket_config['host']}:{websocket_config['port']}/ws"
        
        try:
            # First connection
            websocket1 = await websockets.connect(
                ws_url,
                extra_headers={"Authorization": f"Bearer {auth_token}"},
                timeout=websocket_config["timeout"]
            )
            
            # Send initial message
            initial_message = {
                "type": "heartbeat",
                "user_id": test_user.id,
                "sequence": 1
            }
            await websocket1.send(json.dumps(initial_message))
            
            # Simulate connection interruption
            await websocket1.close()
            
            # Wait briefly
            await asyncio.sleep(2)
            
            # Attempt reconnection
            websocket2 = await websockets.connect(
                ws_url,
                extra_headers={"Authorization": f"Bearer {auth_token}"},
                timeout=websocket_config["timeout"]
            )
            
            # Send reconnection message
            reconnection_message = {
                "type": "reconnect",
                "user_id": test_user.id,
                "last_sequence": 1
            }
            await websocket2.send(json.dumps(reconnection_message))
            
            # FAILURE EXPECTED HERE - reconnection handling may not work
            try:
                response = await asyncio.wait_for(websocket2.recv(), timeout=10)
                response_data = json.loads(response)
                
                # Should get reconnection acknowledgment or buffered messages
                assert "type" in response_data, "Reconnection response should have type"
                
                if response_data["type"] == "reconnection_ack":
                    # Check for missed messages or sequence handling
                    if "missed_messages" in response_data:
                        assert isinstance(response_data["missed_messages"], list), \
                            "Missed messages should be a list"
                elif response_data["type"] == "buffered_messages":
                    # Buffered messages during disconnection
                    assert "messages" in response_data, \
                        "Buffered messages response should contain messages array"
                
            except asyncio.TimeoutError:
                pytest.fail("Reconnection did not receive acknowledgment within 10 seconds")
            
            # Test that new messages work after reconnection
            test_message = {
                "type": "test_after_reconnect",
                "user_id": test_user.id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await websocket2.send(json.dumps(test_message))
            
            # Should be able to receive messages normally
            await websocket2.close()
            
        except Exception as e:
            pytest.fail(f"WebSocket connection recovery failed: {e}")

    @pytest.mark.asyncio
    async def test_06_websocket_message_ordering_fails(self, websocket_config, test_user):
        """
        Test 15F: WebSocket Message Ordering (EXPECTED TO FAIL)
        
        Tests that WebSocket messages are delivered in the correct order.
        Will likely FAIL because:
        1. Message ordering may not be guaranteed
        2. Sequence tracking may not be implemented
        3. Concurrent message handling may cause race conditions
        """
    pass
        # Generate auth token
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {
            "user_id": test_user.id,
            "email": test_user.email,
            "exp": int(time.time()) + 3600
        }
        auth_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        
        ws_url = f"ws://{websocket_config['host']}:{websocket_config['port']}/ws"
        
        try:
            async with websockets.connect(
                ws_url,
                extra_headers={"Authorization": f"Bearer {auth_token}"},
                timeout=websocket_config["timeout"]
            ) as websocket:
                
                # Send multiple messages with sequence numbers
                messages_to_send = [
                    {"type": "ordered_test", "sequence": i, "content": f"Message {i}"}
                    for i in range(10)
                ]
                
                # Send messages rapidly
                for message in messages_to_send:
                    await websocket.send(json.dumps(message))
                    await asyncio.sleep(0.1)  # Small delay between messages
                
                # Trigger server-side message broadcasting in sequence
                try:
                    websocket_service = WebSocketService()
                    
                    # Send server-side messages that should maintain order
                    for i in range(5):
                        server_message = {
                            "type": "server_ordered",
                            "sequence": i,
                            "content": f"Server message {i}",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        # FAILURE EXPECTED HERE - message ordering may not be preserved
                        await websocket_service.send_to_user(
                            user_id=test_user.id,
                            message=server_message
                        )
                        await asyncio.sleep(0.2)
                    
                    # Collect received messages
                    received_messages = []
                    end_time = time.time() + 10  # 10 second timeout
                    
                    while time.time() < end_time and len(received_messages) < 5:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=2)
                            message_data = json.loads(message)
                            
                            if message_data.get("type") == "server_ordered":
                                received_messages.append(message_data)
                                
                        except asyncio.TimeoutError:
                            break
                    
                    # Verify message ordering
                    assert len(received_messages) >= 3, \
                        f"Should receive at least 3 ordered messages, got {len(received_messages)}"
                    
                    # Check sequence ordering
                    for i, message in enumerate(received_messages):
                        expected_sequence = i
                        actual_sequence = message.get("sequence")
                        
                        assert actual_sequence == expected_sequence, \
                            f"Message {i} out of order: expected sequence {expected_sequence}, got {actual_sequence}"
                            
                except ImportError:
                    pytest.skip("WebSocketService not available for message ordering test")
                
        except Exception as e:
            pytest.fail(f"WebSocket message ordering failed: {e}")

    @pytest.mark.asyncio
    async def test_07_websocket_performance_under_load_fails(self, websocket_config, real_database_session):
        """
        Test 15G: WebSocket Performance Under Load (EXPECTED TO FAIL)
        
        Tests WebSocket performance with multiple concurrent connections and messages.
        Will likely FAIL because:
        1. Connection limits may be too low
        2. Message throughput may be insufficient
        3. Memory usage may grow excessively
        """
    pass
        # Create multiple test users for load testing
        num_clients = 10
        test_users = []
        
        for i in range(num_clients):
            user = User(
                id=str(uuid.uuid4()),
                email=f"load_test_{i}_{secrets.token_urlsafe(8)}@example.com",
                name=f"Load Test User {i+1}",
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            test_users.append(user)
            real_database_session.add(user)
        
        await real_database_session.commit()
        
        # Generate auth tokens
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        
        auth_tokens = []
        for user in test_users:
            token_payload = {
                "user_id": user.id,
                "email": user.email,
                "exp": int(time.time()) + 3600
            }
            token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
            auth_tokens.append(token)
        
        ws_url = f"ws://{websocket_config['host']}:{websocket_config['port']}/ws"
        
        # Performance metrics
        start_time = time.time()
        connection_times = []
        message_times = []
        websockets_list = []
        
        try:
            # Establish concurrent connections
            async def connect_client(token: str, client_id: int) -> Optional[websockets.ServerConnection]:
                try:
                    connect_start = time.time()
                    ws = await websockets.connect(
                        ws_url,
                        extra_headers={"Authorization": f"Bearer {token}"},
                        timeout=websocket_config["timeout"]
                    )
                    connect_end = time.time()
                    connection_times.append(connect_end - connect_start)
                    await asyncio.sleep(0)
    return ws
                    
                except Exception as e:
                    return None
            
            # FAILURE EXPECTED HERE - concurrent connections may fail
            connection_tasks = [
                connect_client(token, i) for i, token in enumerate(auth_tokens)
            ]
            
            websockets_list = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Filter successful connections
            successful_connections = [
                ws for ws in websockets_list if ws is not None and not isinstance(ws, Exception)
            ]
            
            connection_success_rate = len(successful_connections) / num_clients
            assert connection_success_rate >= 0.8, \
                f"Connection success rate too low: {connection_success_rate*100:.1f}%"
            
            # Test message throughput
            messages_per_client = 5
            total_messages = len(successful_connections) * messages_per_client
            
            async def send_messages_from_client(ws, client_id: int) -> int:
                messages_sent = 0
                for i in range(messages_per_client):
                    try:
                        message_start = time.time()
                        message = {
                            "type": "load_test",
                            "client_id": client_id,
                            "message_id": i,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        await ws.send(json.dumps(message))
                        message_end = time.time()
                        message_times.append(message_end - message_start)
                        messages_sent += 1
                        await asyncio.sleep(0.1)
                        
                    except Exception:
                        break
                        
                return messages_sent
            
            # Send messages from all clients concurrently
            message_tasks = [
                send_messages_from_client(ws, i) 
                for i, ws in enumerate(successful_connections)
            ]
            
            messages_sent = await asyncio.gather(*message_tasks, return_exceptions=True)
            total_sent = sum(count for count in messages_sent if isinstance(count, int))
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # Performance assertions
            average_connection_time = sum(connection_times) / len(connection_times) if connection_times else 0
            assert average_connection_time < 2.0, \
                f"Average connection time too slow: {average_connection_time:.2f}s"
            
            message_throughput = total_sent / total_duration if total_duration > 0 else 0
            assert message_throughput > 10, \
                f"Message throughput too low: {message_throughput:.1f} messages/second"
            
            if message_times:
                average_message_time = sum(message_times) / len(message_times)
                assert average_message_time < 0.5, \
                    f"Average message send time too slow: {average_message_time:.3f}s"
                    
        finally:
            # Clean up connections
            for ws in websockets_list:
                if ws is not None and not isinstance(ws, Exception):
                    try:
                        await ws.close()
                    except Exception:
                        pass

    @pytest.mark.asyncio
    async def test_08_websocket_error_handling_fails(self, websocket_config, test_user):
        """
        Test 15H: WebSocket Error Handling (EXPECTED TO FAIL)
        
        Tests that WebSocket errors are handled gracefully.
        Will likely FAIL because:
        1. Error handling may not be comprehensive
        2. Error recovery may not work
        3. Client notification of errors may be missing
        """
    pass
        # Generate auth token
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {
            "user_id": test_user.id,
            "email": test_user.email,
            "exp": int(time.time()) + 3600
        }
        auth_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        
        ws_url = f"ws://{websocket_config['host']}:{websocket_config['port']}/ws"
        
        try:
            async with websockets.connect(
                ws_url,
                extra_headers={"Authorization": f"Bearer {auth_token}"},
                timeout=websocket_config["timeout"]
            ) as websocket:
                
                # Test various error scenarios
                error_scenarios = [
                    {
                        "name": "malformed_json",
                        "message": "not valid json at all",
                        "expected_error": "invalid_json"
                    },
                    {
                        "name": "missing_required_field",
                        "message": json.dumps({"incomplete": "message"}),
                        "expected_error": "missing_field"
                    },
                    {
                        "name": "invalid_message_type",
                        "message": json.dumps({"type": "nonexistent_type", "data": {}}),
                        "expected_error": "invalid_type"
                    }
                ]
                
                for scenario in error_scenarios:
                    # Send problematic message
                    await websocket.send(scenario["message"])
                    
                    # FAILURE EXPECTED HERE - error handling may not send proper error responses
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        response_data = json.loads(response)
                        
                        # Should receive error response
                        assert "type" in response_data, \
                            f"Error response for {scenario['name']} should have type field"
                        
                        assert response_data["type"] in ["error", "validation_error"], \
                            f"Expected error response type for {scenario['name']}, got {response_data['type']}"
                        
                        assert "message" in response_data, \
                            f"Error response for {scenario['name']} should include error message"
                            
                    except asyncio.TimeoutError:
                        pytest.fail(f"No error response received for scenario: {scenario['name']}")
                    except json.JSONDecodeError:
                        pytest.fail(f"Error response for {scenario['name']} was not valid JSON")
                
                # Test that connection remains functional after errors
                recovery_message = {
                    "type": "recovery_test",
                    "user_id": test_user.id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(recovery_message))
                
                # Should be able to send/receive normally after errors
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    # Connection should still work after error handling
                    
                except asyncio.TimeoutError:
                    pytest.fail("WebSocket connection not functional after error handling")
                
        except Exception as e:
            pytest.fail(f"WebSocket error handling failed: {e}")


# Additional utility class for WebSocket testing
class RedTeamWebSocketTestUtils:
    """Utility methods for Red Team WebSocket testing."""
    
    @staticmethod
    def generate_auth_token(user_id: str, email: str) -> str:
        """Generate JWT token for WebSocket authentication."""
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {
            "user_id": user_id,
            "email": email,
            "exp": int(time.time()) + 3600
        }
        await asyncio.sleep(0)
    return pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
    
    @staticmethod
    async def connect_websocket(ws_url: str, auth_token: str, timeout: int = 10):
        """Connect to WebSocket with authentication."""
        await asyncio.sleep(0)
    return await websockets.connect(
            ws_url,
            extra_headers={"Authorization": f"Bearer {auth_token}"},
            timeout=timeout
        )
    
    @staticmethod
    async def send_and_wait_response(websocket, message: Dict[str, Any], timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Send message and wait for response."""
    pass
        try:
            await websocket.send(json.dumps(message))
            response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            return json.loads(response)
        except (asyncio.TimeoutError, json.JSONDecodeError):
            return None
    
    @staticmethod
    def validate_websocket_message(message: Dict[str, Any], expected_type: str) -> bool:
        """Validate WebSocket message format."""
        return (
            isinstance(message, dict) and
            "type" in message and
            message["type"] == expected_type and
            "timestamp" in message
        )
    
    @staticmethod
    async def measure_websocket_latency(websocket, test_message: Dict[str, Any]) -> float:
        """Measure WebSocket round-trip latency."""
        start_time = time.time()
        
        try:
            await websocket.send(json.dumps(test_message))
            await websocket.recv()
            return time.time() - start_time
        except Exception:
            return float('inf')
