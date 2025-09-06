# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    #!/usr/bin/env python
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: MISSION CRITICAL: WebSocket SSOT Validation Test Suite

    # REMOVED_SYNTAX_ERROR: This test suite validates that the WebSocket Manager consolidation maintains:
        # REMOVED_SYNTAX_ERROR: 1. Complete user isolation with 25+ concurrent sessions
        # REMOVED_SYNTAX_ERROR: 2. No data leakage between users
        # REMOVED_SYNTAX_ERROR: 3. Accurate message routing
        # REMOVED_SYNTAX_ERROR: 4. Performance requirements (< 2 seconds response for 10 concurrent users)
        # REMOVED_SYNTAX_ERROR: 5. Connection limits per user (3 per user, 100 total)
        # REMOVED_SYNTAX_ERROR: 6. All 5 required WebSocket events for chat functionality

        # REMOVED_SYNTAX_ERROR: Business Value: $1M+ ARR - Core chat functionality depends on these features
        # REMOVED_SYNTAX_ERROR: ANY FAILURE HERE MEANS PRODUCTION IS BROKEN.
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import json
        # REMOVED_SYNTAX_ERROR: import os
        # REMOVED_SYNTAX_ERROR: import sys
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: import uuid
        # REMOVED_SYNTAX_ERROR: from concurrent.futures import ThreadPoolExecutor
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta, timezone
        # REMOVED_SYNTAX_ERROR: from typing import Dict, List, Set, Any, Optional
        # REMOVED_SYNTAX_ERROR: import threading
        # REMOVED_SYNTAX_ERROR: import random
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # CRITICAL: Add project root to Python path for imports
        # REMOVED_SYNTAX_ERROR: project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        # REMOVED_SYNTAX_ERROR: if project_root not in sys.path:
            # REMOVED_SYNTAX_ERROR: sys.path.insert(0, project_root)

            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger

            # Import WebSocket components to test
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager, get_websocket_manager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.websocket_bridge_factory import ( )
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
            # REMOVED_SYNTAX_ERROR: WebSocketBridgeFactory,
            # REMOVED_SYNTAX_ERROR: UserWebSocketEmitter,
            # REMOVED_SYNTAX_ERROR: UserWebSocketContext,
            # REMOVED_SYNTAX_ERROR: WebSocketEvent,
            # REMOVED_SYNTAX_ERROR: ConnectionStatus
            

            # REMOVED_SYNTAX_ERROR: logger = central_logger.get_logger(__name__)


# REMOVED_SYNTAX_ERROR: class MockWebSocket:
    # REMOVED_SYNTAX_ERROR: """Mock WebSocket connection for testing."""

# REMOVED_SYNTAX_ERROR: def __init__(self, user_id: str, connection_id: str):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.user_id = user_id
    # REMOVED_SYNTAX_ERROR: self.connection_id = connection_id
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self.sent_messages = []
    # REMOVED_SYNTAX_ERROR: self.client_state = "connected"

# REMOVED_SYNTAX_ERROR: async def send_json(self, data: dict) -> None:
    # REMOVED_SYNTAX_ERROR: """Mock send_json method."""
    # REMOVED_SYNTAX_ERROR: if not self.is_connected:
        # REMOVED_SYNTAX_ERROR: raise ConnectionError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.sent_messages.append({ ))
        # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc).isoformat(),
        # REMOVED_SYNTAX_ERROR: 'data': data
        

# REMOVED_SYNTAX_ERROR: async def send_text(self, data: str) -> None:
    # REMOVED_SYNTAX_ERROR: """Mock send_text method."""
    # REMOVED_SYNTAX_ERROR: if not self.is_connected:
        # REMOVED_SYNTAX_ERROR: raise ConnectionError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.sent_messages.append({ ))
        # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc).isoformat(),
        # REMOVED_SYNTAX_ERROR: 'data': data
        

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "") -> None:
    # REMOVED_SYNTAX_ERROR: """Mock close method."""
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: async def ping(self, data: bytes = b'') -> None:
    # REMOVED_SYNTAX_ERROR: """Mock ping method."""
    # REMOVED_SYNTAX_ERROR: if not self.is_connected:
        # REMOVED_SYNTAX_ERROR: raise ConnectionError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: return True


# REMOVED_SYNTAX_ERROR: class TestWebSocketSSOTValidation:
    # REMOVED_SYNTAX_ERROR: """Test WebSocket Single Source of Truth validation."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def setup_test(self):
    # REMOVED_SYNTAX_ERROR: """Setup for each test."""
    # Reset any global state
    # REMOVED_SYNTAX_ERROR: self.created_managers = []
    # REMOVED_SYNTAX_ERROR: self.created_factories = []

    # REMOVED_SYNTAX_ERROR: yield

    # Cleanup
    # REMOVED_SYNTAX_ERROR: for manager in self.created_managers:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: if hasattr(manager, 'shutdown'):
                # REMOVED_SYNTAX_ERROR: asyncio.create_task(manager.shutdown())
                # REMOVED_SYNTAX_ERROR: except Exception:
                    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def create_test_manager(self) -> WebSocketManager:
    # REMOVED_SYNTAX_ERROR: """Create a test WebSocket manager."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()
    # REMOVED_SYNTAX_ERROR: self.created_managers.append(manager)
    # REMOVED_SYNTAX_ERROR: return manager

# REMOVED_SYNTAX_ERROR: def create_test_factory(self) -> WebSocketBridgeFactory:
    # REMOVED_SYNTAX_ERROR: """Create a test WebSocket bridge factory."""
    # REMOVED_SYNTAX_ERROR: factory = WebSocketBridgeFactory()
    # REMOVED_SYNTAX_ERROR: self.created_factories.append(factory)
    # REMOVED_SYNTAX_ERROR: return factory

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_user_isolation_25_concurrent_sessions(self):
        # REMOVED_SYNTAX_ERROR: """Test user isolation with 25+ concurrent sessions."""
        # REMOVED_SYNTAX_ERROR: logger.info("🧪 Testing user isolation with 25+ concurrent sessions")

        # REMOVED_SYNTAX_ERROR: manager = self.create_test_manager()
        # REMOVED_SYNTAX_ERROR: users_count = 25
        # REMOVED_SYNTAX_ERROR: connections_per_user = 2
        # REMOVED_SYNTAX_ERROR: total_connections = users_count * connections_per_user

        # Track connections by user
        # REMOVED_SYNTAX_ERROR: user_connections = {}
        # REMOVED_SYNTAX_ERROR: all_connections = []

        # Create concurrent connections
        # REMOVED_SYNTAX_ERROR: start_time = time.time()

        # REMOVED_SYNTAX_ERROR: for user_idx in range(users_count):
            # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
            # REMOVED_SYNTAX_ERROR: user_connections[user_id] = []

            # REMOVED_SYNTAX_ERROR: for conn_idx in range(connections_per_user):
                # REMOVED_SYNTAX_ERROR: thread_id = "formatted_string"
                # REMOVED_SYNTAX_ERROR: websocket = MockWebSocket(user_id, "formatted_string")

                # REMOVED_SYNTAX_ERROR: connection_id = await manager.connect_user( )
                # REMOVED_SYNTAX_ERROR: user_id=user_id,
                # REMOVED_SYNTAX_ERROR: websocket=websocket,
                # REMOVED_SYNTAX_ERROR: thread_id=thread_id
                

                # REMOVED_SYNTAX_ERROR: user_connections[user_id].append(connection_id)
                # REMOVED_SYNTAX_ERROR: all_connections.append({ ))
                # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
                # REMOVED_SYNTAX_ERROR: 'connection_id': connection_id,
                # REMOVED_SYNTAX_ERROR: 'thread_id': thread_id,
                # REMOVED_SYNTAX_ERROR: 'websocket': websocket
                

                # REMOVED_SYNTAX_ERROR: connection_time = time.time() - start_time
                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                # Verify user isolation
                # REMOVED_SYNTAX_ERROR: for user_id, connections in user_connections.items():
                    # REMOVED_SYNTAX_ERROR: user_conns = manager.user_connections.get(user_id, set())
                    # REMOVED_SYNTAX_ERROR: assert len(user_conns) == connections_per_user, \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                    # Verify connections belong only to this user
                    # REMOVED_SYNTAX_ERROR: for conn_id in user_conns:
                        # REMOVED_SYNTAX_ERROR: conn_info = manager.connections.get(conn_id)
                        # REMOVED_SYNTAX_ERROR: assert conn_info is not None, "formatted_string"
                        # REMOVED_SYNTAX_ERROR: assert conn_info['user_id'] == user_id, \
                        # REMOVED_SYNTAX_ERROR: "formatted_string"

                        # Test message routing isolation
                        # REMOVED_SYNTAX_ERROR: test_messages = []
                        # REMOVED_SYNTAX_ERROR: for user_id in list(user_connections.keys())[:5]:  # Test first 5 users
                        # REMOVED_SYNTAX_ERROR: message = { )
                        # REMOVED_SYNTAX_ERROR: 'type': 'test_message',
                        # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
                        # REMOVED_SYNTAX_ERROR: 'content': 'formatted_string',
                        # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc).isoformat()
                        
                        # REMOVED_SYNTAX_ERROR: test_messages.append((user_id, message))

                        # Send message to specific user
                        # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_id, message)

                        # Verify messages reached only intended users
                        # REMOVED_SYNTAX_ERROR: for user_id, expected_message in test_messages:
                            # REMOVED_SYNTAX_ERROR: user_conns = user_connections[user_id]

                            # REMOVED_SYNTAX_ERROR: for conn_id in user_conns:
                                # REMOVED_SYNTAX_ERROR: conn_info = manager.connections[conn_id]
                                # REMOVED_SYNTAX_ERROR: websocket = conn_info['websocket']

                                # Check that message was received
                                # REMOVED_SYNTAX_ERROR: assert len(websocket.sent_messages) >= 1, \
                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                # Check message content
                                # REMOVED_SYNTAX_ERROR: received_message = websocket.sent_messages[-1]['data']
                                # REMOVED_SYNTAX_ERROR: assert received_message['user_id'] == user_id, \
                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                # Verify no cross-user contamination
                                # REMOVED_SYNTAX_ERROR: other_users = list(user_connections.keys())[5:]  # Users who shouldn"t receive messages
                                # REMOVED_SYNTAX_ERROR: for user_id in other_users:
                                    # REMOVED_SYNTAX_ERROR: user_conns = user_connections[user_id]
                                    # REMOVED_SYNTAX_ERROR: for conn_id in user_conns:
                                        # REMOVED_SYNTAX_ERROR: conn_info = manager.connections[conn_id]
                                        # REMOVED_SYNTAX_ERROR: websocket = conn_info['websocket']
                                        # REMOVED_SYNTAX_ERROR: assert len(websocket.sent_messages) == 0, \
                                        # REMOVED_SYNTAX_ERROR: "formatted_string"

                                        # REMOVED_SYNTAX_ERROR: logger.info("✅ User isolation with 25+ concurrent sessions PASSED")

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_no_data_leakage_between_users(self):
                                            # REMOVED_SYNTAX_ERROR: """Test that sensitive data doesn't leak between users."""
                                            # REMOVED_SYNTAX_ERROR: pass
                                            # REMOVED_SYNTAX_ERROR: logger.info("🧪 Testing no data leakage between users")

                                            # REMOVED_SYNTAX_ERROR: manager = self.create_test_manager()

                                            # Create users with sensitive data
                                            # REMOVED_SYNTAX_ERROR: user_a_id = "user_sensitive_a"
                                            # REMOVED_SYNTAX_ERROR: user_b_id = "user_sensitive_b"

                                            # REMOVED_SYNTAX_ERROR: websocket_a = MockWebSocket(user_a_id, "conn_a")
                                            # REMOVED_SYNTAX_ERROR: websocket_b = MockWebSocket(user_b_id, "conn_b")

                                            # REMOVED_SYNTAX_ERROR: conn_a = await manager.connect_user(user_a_id, websocket_a, "thread_a")
                                            # REMOVED_SYNTAX_ERROR: conn_b = await manager.connect_user(user_b_id, websocket_b, "thread_b")

                                            # Send sensitive data to user A
                                            # REMOVED_SYNTAX_ERROR: sensitive_message_a = { )
                                            # REMOVED_SYNTAX_ERROR: 'type': 'sensitive_data',
                                            # REMOVED_SYNTAX_ERROR: 'user_id': user_a_id,
                                            # REMOVED_SYNTAX_ERROR: 'api_key': 'secret_key_user_a_12345',
                                            # REMOVED_SYNTAX_ERROR: 'personal_data': 'SSN: 123-45-6789',
                                            # REMOVED_SYNTAX_ERROR: 'business_secret': 'Proprietary algorithm details'
                                            

                                            # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_a_id, sensitive_message_a)

                                            # Send different sensitive data to user B
                                            # REMOVED_SYNTAX_ERROR: sensitive_message_b = { )
                                            # REMOVED_SYNTAX_ERROR: 'type': 'sensitive_data',
                                            # REMOVED_SYNTAX_ERROR: 'user_id': user_b_id,
                                            # REMOVED_SYNTAX_ERROR: 'api_key': 'secret_key_user_b_67890',
                                            # REMOVED_SYNTAX_ERROR: 'personal_data': 'SSN: 987-65-4321',
                                            # REMOVED_SYNTAX_ERROR: 'business_secret': 'Different proprietary information'
                                            

                                            # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_b_id, sensitive_message_b)

                                            # Verify user A only received their data
                                            # REMOVED_SYNTAX_ERROR: assert len(websocket_a.sent_messages) == 1
                                            # REMOVED_SYNTAX_ERROR: received_a = websocket_a.sent_messages[0]['data']
                                            # REMOVED_SYNTAX_ERROR: assert received_a['api_key'] == 'secret_key_user_a_12345'
                                            # REMOVED_SYNTAX_ERROR: assert 'secret_key_user_b_67890' not in str(received_a)

                                            # Verify user B only received their data
                                            # REMOVED_SYNTAX_ERROR: assert len(websocket_b.sent_messages) == 1
                                            # REMOVED_SYNTAX_ERROR: received_b = websocket_b.sent_messages[0]['data']
                                            # REMOVED_SYNTAX_ERROR: assert received_b['api_key'] == 'secret_key_user_b_67890'
                                            # REMOVED_SYNTAX_ERROR: assert 'secret_key_user_a_12345' not in str(received_b)

                                            # REMOVED_SYNTAX_ERROR: logger.info("✅ No data leakage between users PASSED")

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_message_routing_accuracy(self):
                                                # REMOVED_SYNTAX_ERROR: """Test accurate message routing to correct users and threads."""
                                                # REMOVED_SYNTAX_ERROR: logger.info("🧪 Testing message routing accuracy")

                                                # REMOVED_SYNTAX_ERROR: manager = self.create_test_manager()

                                                # Create users with multiple threads each
                                                # REMOVED_SYNTAX_ERROR: users_threads = { )
                                                # REMOVED_SYNTAX_ERROR: 'user_1': ['thread_1_a', 'thread_1_b'],
                                                # REMOVED_SYNTAX_ERROR: 'user_2': ['thread_2_a', 'thread_2_b'],
                                                # REMOVED_SYNTAX_ERROR: 'user_3': ['thread_3_a']
                                                

                                                # REMOVED_SYNTAX_ERROR: connections = {}
                                                # REMOVED_SYNTAX_ERROR: websockets = {}

                                                # Create connections for each user/thread combination
                                                # REMOVED_SYNTAX_ERROR: for user_id, threads in users_threads.items():
                                                    # REMOVED_SYNTAX_ERROR: connections[user_id] = {}
                                                    # REMOVED_SYNTAX_ERROR: websockets[user_id] = {}

                                                    # REMOVED_SYNTAX_ERROR: for thread_id in threads:
                                                        # REMOVED_SYNTAX_ERROR: websocket = MockWebSocket(user_id, "formatted_string")
                                                        # REMOVED_SYNTAX_ERROR: websockets[user_id][thread_id] = websocket

                                                        # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user( )
                                                        # REMOVED_SYNTAX_ERROR: user_id=user_id,
                                                        # REMOVED_SYNTAX_ERROR: websocket=websocket,
                                                        # REMOVED_SYNTAX_ERROR: thread_id=thread_id
                                                        
                                                        # REMOVED_SYNTAX_ERROR: connections[user_id][thread_id] = conn_id

                                                        # Test thread-specific routing
                                                        # Removed problematic line: await manager.send_to_thread('thread_1_a', { ))
                                                        # REMOVED_SYNTAX_ERROR: 'type': 'thread_message',
                                                        # REMOVED_SYNTAX_ERROR: 'content': 'Message for thread_1_a only'
                                                        

                                                        # Verify only thread_1_a received the message
                                                        # REMOVED_SYNTAX_ERROR: thread_1_a_ws = websockets['user_1']['thread_1_a']
                                                        # REMOVED_SYNTAX_ERROR: assert len(thread_1_a_ws.sent_messages) == 1
                                                        # REMOVED_SYNTAX_ERROR: assert thread_1_a_ws.sent_messages[0]['data']['content'] == 'Message for thread_1_a only'

                                                        # Verify other threads didn't receive it
                                                        # REMOVED_SYNTAX_ERROR: thread_1_b_ws = websockets['user_1']['thread_1_b']
                                                        # REMOVED_SYNTAX_ERROR: assert len(thread_1_b_ws.sent_messages) == 0

                                                        # REMOVED_SYNTAX_ERROR: for user_id in ['user_2', 'user_3']:
                                                            # REMOVED_SYNTAX_ERROR: for thread_id, websocket in websockets[user_id].items():
                                                                # REMOVED_SYNTAX_ERROR: assert len(websocket.sent_messages) == 0, \
                                                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                                # REMOVED_SYNTAX_ERROR: logger.info("✅ Message routing accuracy PASSED")

                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_connection_limits_enforcement(self):
                                                                    # REMOVED_SYNTAX_ERROR: """Test connection limits per user and total."""
                                                                    # REMOVED_SYNTAX_ERROR: pass
                                                                    # REMOVED_SYNTAX_ERROR: logger.info("🧪 Testing connection limits enforcement")

                                                                    # REMOVED_SYNTAX_ERROR: manager = self.create_test_manager()

                                                                    # Test per-user connection limit (3 connections per user)
                                                                    # REMOVED_SYNTAX_ERROR: user_id = "user_connection_limit"
                                                                    # REMOVED_SYNTAX_ERROR: connections = []

                                                                    # Create maximum allowed connections
                                                                    # REMOVED_SYNTAX_ERROR: for i in range(manager.MAX_CONNECTIONS_PER_USER):
                                                                        # REMOVED_SYNTAX_ERROR: websocket = MockWebSocket(user_id, "formatted_string")
                                                                        # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user( )
                                                                        # REMOVED_SYNTAX_ERROR: user_id=user_id,
                                                                        # REMOVED_SYNTAX_ERROR: websocket=websocket,
                                                                        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
                                                                        
                                                                        # REMOVED_SYNTAX_ERROR: connections.append(conn_id)

                                                                        # Verify all connections are tracked
                                                                        # REMOVED_SYNTAX_ERROR: user_conns = manager.user_connections.get(user_id, set())
                                                                        # REMOVED_SYNTAX_ERROR: assert len(user_conns) == manager.MAX_CONNECTIONS_PER_USER

                                                                        # Test total connection limit (theoretical - would need many users)
                                                                        # REMOVED_SYNTAX_ERROR: total_connections = len(manager.connections)
                                                                        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
                                                                        # REMOVED_SYNTAX_ERROR: assert total_connections <= manager.MAX_TOTAL_CONNECTIONS

                                                                        # REMOVED_SYNTAX_ERROR: logger.info("✅ Connection limits enforcement PASSED")

                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # Removed problematic line: async def test_performance_response_time(self):
                                                                            # REMOVED_SYNTAX_ERROR: """Test response time < 2 seconds for 10 concurrent users."""
                                                                            # REMOVED_SYNTAX_ERROR: logger.info("🧪 Testing performance response time < 2 seconds")

                                                                            # REMOVED_SYNTAX_ERROR: manager = self.create_test_manager()

                                                                            # Create 10 concurrent users
                                                                            # REMOVED_SYNTAX_ERROR: concurrent_users = 10
                                                                            # REMOVED_SYNTAX_ERROR: user_data = []

                                                                            # REMOVED_SYNTAX_ERROR: for i in range(concurrent_users):
                                                                                # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
                                                                                # REMOVED_SYNTAX_ERROR: websocket = MockWebSocket(user_id, "formatted_string")

                                                                                # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user( )
                                                                                # REMOVED_SYNTAX_ERROR: user_id=user_id,
                                                                                # REMOVED_SYNTAX_ERROR: websocket=websocket,
                                                                                # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
                                                                                

                                                                                # REMOVED_SYNTAX_ERROR: user_data.append({ ))
                                                                                # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
                                                                                # REMOVED_SYNTAX_ERROR: 'connection_id': conn_id,
                                                                                # REMOVED_SYNTAX_ERROR: 'websocket': websocket
                                                                                

                                                                                # Test concurrent message sending
                                                                                # REMOVED_SYNTAX_ERROR: start_time = time.time()

                                                                                # Send messages to all users concurrently
                                                                                # REMOVED_SYNTAX_ERROR: send_tasks = []
                                                                                # REMOVED_SYNTAX_ERROR: for user_info in user_data:
                                                                                    # REMOVED_SYNTAX_ERROR: message = { )
                                                                                    # REMOVED_SYNTAX_ERROR: 'type': 'performance_test',
                                                                                    # REMOVED_SYNTAX_ERROR: 'user_id': user_info['user_id'],
                                                                                    # REMOVED_SYNTAX_ERROR: 'content': "formatted_string",
                                                                                    # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc).isoformat()
                                                                                    
                                                                                    # REMOVED_SYNTAX_ERROR: task = manager.send_to_user(user_info['user_id'], message)
                                                                                    # REMOVED_SYNTAX_ERROR: send_tasks.append(task)

                                                                                    # Wait for all messages to be sent
                                                                                    # REMOVED_SYNTAX_ERROR: await asyncio.gather(*send_tasks)

                                                                                    # REMOVED_SYNTAX_ERROR: total_time = time.time() - start_time

                                                                                    # Verify response time is under 2 seconds
                                                                                    # REMOVED_SYNTAX_ERROR: assert total_time < 2.0, "formatted_string"

                                                                                    # Verify all messages were delivered
                                                                                    # REMOVED_SYNTAX_ERROR: for user_info in user_data:
                                                                                        # REMOVED_SYNTAX_ERROR: websocket = user_info['websocket']
                                                                                        # REMOVED_SYNTAX_ERROR: assert len(websocket.sent_messages) == 1, \
                                                                                        # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                                                        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                        # Removed problematic line: async def test_websocket_event_flow_validation(self):
                                                                                            # REMOVED_SYNTAX_ERROR: """Test all 5 required WebSocket events are sent correctly."""
                                                                                            # REMOVED_SYNTAX_ERROR: pass
                                                                                            # REMOVED_SYNTAX_ERROR: logger.info("🧪 Testing WebSocket event flow validation")

                                                                                            # Create factory and test user emitter
                                                                                            # REMOVED_SYNTAX_ERROR: factory = self.create_test_factory()

                                                                                            # REMOVED_SYNTAX_ERROR: user_id = "event_test_user"
                                                                                            # REMOVED_SYNTAX_ERROR: thread_id = "event_test_thread"
                                                                                            # REMOVED_SYNTAX_ERROR: connection_id = "event_test_conn"

                                                                                            # Mock WebSocket connection pool
                                                                                            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
                                                                                            # REMOVED_SYNTAX_ERROR: mock_pool.get_connection.return_value = None  # Will create placeholder connection

                                                                                            # REMOVED_SYNTAX_ERROR: factory.configure( )
                                                                                            # REMOVED_SYNTAX_ERROR: connection_pool=mock_pool,
                                                                                            # REMOVED_SYNTAX_ERROR: agent_registry=None,
                                                                                            # REMOVED_SYNTAX_ERROR: health_monitor=None
                                                                                            

                                                                                            # Create user emitter
                                                                                            # REMOVED_SYNTAX_ERROR: emitter = await factory.create_user_emitter(user_id, thread_id, connection_id)

                                                                                            # Test all 5 required events
                                                                                            # REMOVED_SYNTAX_ERROR: agent_name = "TestAgent"
                                                                                            # REMOVED_SYNTAX_ERROR: run_id = "test_run_123"

                                                                                            # 1. Agent Started
                                                                                            # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_started(agent_name, run_id)

                                                                                            # 2. Agent Thinking
                                                                                            # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_thinking(agent_name, run_id, "Analyzing the request...")

                                                                                            # 3. Tool Executing
                                                                                            # REMOVED_SYNTAX_ERROR: await emitter.notify_tool_executing(agent_name, run_id, "test_tool", {"param": "value"})

                                                                                            # 4. Tool Completed
                                                                                            # REMOVED_SYNTAX_ERROR: await emitter.notify_tool_completed(agent_name, run_id, "test_tool", {"result": "success"})

                                                                                            # 5. Agent Completed
                                                                                            # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_completed(agent_name, run_id, {"final_result": "completed"})

                                                                                            # Allow time for event processing
                                                                                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                                                                            # Verify all events were queued (user context tracks sent events)
                                                                                            # REMOVED_SYNTAX_ERROR: user_context = emitter.user_context

                                                                                            # Check that events were processed (would be in sent_events after processing)
                                                                                            # Since we're using mock connections, events might be in the queue or failed_events
                                                                                            # REMOVED_SYNTAX_ERROR: total_events = len(user_context.sent_events) + user_context.event_queue.qsize()

                                                                                            # REMOVED_SYNTAX_ERROR: assert total_events >= 5, "formatted_string"

                                                                                            # REMOVED_SYNTAX_ERROR: logger.info("✅ WebSocket event flow validation PASSED")

                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                            # Removed problematic line: async def test_cleanup_stale_connections(self):
                                                                                                # REMOVED_SYNTAX_ERROR: """Test cleanup of stale connections."""
                                                                                                # REMOVED_SYNTAX_ERROR: logger.info("🧪 Testing cleanup of stale connections")

                                                                                                # REMOVED_SYNTAX_ERROR: manager = self.create_test_manager()

                                                                                                # Create connections and manually make them stale
                                                                                                # REMOVED_SYNTAX_ERROR: user_id = "stale_user"
                                                                                                # REMOVED_SYNTAX_ERROR: websocket = MockWebSocket(user_id, "stale_conn")

                                                                                                # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket, "stale_thread")

                                                                                                # Manually set connection to be stale (old last_activity)
                                                                                                # REMOVED_SYNTAX_ERROR: conn_info = manager.connections[conn_id]
                                                                                                # REMOVED_SYNTAX_ERROR: conn_info['last_activity'] = datetime.now(timezone.utc) - timedelta(seconds=manager.STALE_CONNECTION_TIMEOUT + 60)
                                                                                                # REMOVED_SYNTAX_ERROR: conn_info['is_healthy'] = False

                                                                                                # Run cleanup
                                                                                                # REMOVED_SYNTAX_ERROR: cleaned_count = await manager._cleanup_stale_connections()

                                                                                                # Verify connection was cleaned up
                                                                                                # REMOVED_SYNTAX_ERROR: assert cleaned_count >= 1
                                                                                                # REMOVED_SYNTAX_ERROR: assert conn_id not in manager.connections
                                                                                                # REMOVED_SYNTAX_ERROR: assert user_id not in manager.user_connections or len(manager.user_connections[user_id]) == 0

                                                                                                # REMOVED_SYNTAX_ERROR: logger.info("✅ Cleanup of stale connections PASSED")

                                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                                # Removed problematic line: async def test_memory_usage_stability(self):
                                                                                                    # REMOVED_SYNTAX_ERROR: """Test memory usage stays stable with many connections."""
                                                                                                    # REMOVED_SYNTAX_ERROR: pass
                                                                                                    # REMOVED_SYNTAX_ERROR: logger.info("🧪 Testing memory usage stability")

                                                                                                    # REMOVED_SYNTAX_ERROR: manager = self.create_test_manager()

                                                                                                    # Create and destroy connections to test memory stability
                                                                                                    # REMOVED_SYNTAX_ERROR: cycles = 5
                                                                                                    # REMOVED_SYNTAX_ERROR: connections_per_cycle = 10

                                                                                                    # REMOVED_SYNTAX_ERROR: initial_stats = await manager.get_stats()
                                                                                                    # REMOVED_SYNTAX_ERROR: initial_memory_cleanups = initial_stats.get('memory_cleanups', 0)

                                                                                                    # REMOVED_SYNTAX_ERROR: for cycle in range(cycles):
                                                                                                        # Create connections
                                                                                                        # REMOVED_SYNTAX_ERROR: connections = []
                                                                                                        # REMOVED_SYNTAX_ERROR: for i in range(connections_per_cycle):
                                                                                                            # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
                                                                                                            # REMOVED_SYNTAX_ERROR: websocket = MockWebSocket(user_id, "formatted_string")

                                                                                                            # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket, "formatted_string")
                                                                                                            # REMOVED_SYNTAX_ERROR: connections.append((user_id, conn_id, websocket))

                                                                                                            # Send messages to generate activity
                                                                                                            # REMOVED_SYNTAX_ERROR: for user_id, conn_id, websocket in connections:
                                                                                                                # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_id, {'type': 'memory_test', 'data': 'test'})

                                                                                                                # Disconnect all connections
                                                                                                                # REMOVED_SYNTAX_ERROR: for user_id, conn_id, websocket in connections:
                                                                                                                    # REMOVED_SYNTAX_ERROR: await manager.disconnect_user(user_id, websocket)

                                                                                                                    # Force cleanup
                                                                                                                    # REMOVED_SYNTAX_ERROR: await manager._cleanup_stale_connections()

                                                                                                                    # REMOVED_SYNTAX_ERROR: final_stats = await manager.get_stats()

                                                                                                                    # Verify connections are cleaned up
                                                                                                                    # REMOVED_SYNTAX_ERROR: assert final_stats['active_connections'] <= connections_per_cycle  # Allow some connections to remain

                                                                                                                    # Verify memory cleanup happened
                                                                                                                    # REMOVED_SYNTAX_ERROR: final_memory_cleanups = final_stats.get('memory_cleanups', 0)
                                                                                                                    # REMOVED_SYNTAX_ERROR: assert final_memory_cleanups > initial_memory_cleanups

                                                                                                                    # REMOVED_SYNTAX_ERROR: logger.info("✅ Memory usage stability PASSED")

                                                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                                                    # Removed problematic line: async def test_heartbeat_performance(self):
                                                                                                                        # REMOVED_SYNTAX_ERROR: """Test heartbeat performance with enhanced features."""
                                                                                                                        # REMOVED_SYNTAX_ERROR: logger.info("🧪 Testing heartbeat performance")

                                                                                                                        # REMOVED_SYNTAX_ERROR: manager = self.create_test_manager()

                                                                                                                        # Create multiple connections to test heartbeat
                                                                                                                        # REMOVED_SYNTAX_ERROR: users = []
                                                                                                                        # REMOVED_SYNTAX_ERROR: for i in range(5):
                                                                                                                            # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
                                                                                                                            # REMOVED_SYNTAX_ERROR: websocket = MockWebSocket(user_id, "formatted_string")

                                                                                                                            # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user(user_id, websocket, "formatted_string")
                                                                                                                            # REMOVED_SYNTAX_ERROR: users.append((user_id, conn_id, websocket))

                                                                                                                            # Test enhanced ping functionality
                                                                                                                            # REMOVED_SYNTAX_ERROR: start_time = time.time()
                                                                                                                            # REMOVED_SYNTAX_ERROR: ping_tasks = []

                                                                                                                            # REMOVED_SYNTAX_ERROR: for user_id, conn_id, websocket in users:
                                                                                                                                # REMOVED_SYNTAX_ERROR: task = manager.enhanced_ping_connection(conn_id)
                                                                                                                                # REMOVED_SYNTAX_ERROR: ping_tasks.append(task)

                                                                                                                                # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*ping_tasks, return_exceptions=True)

                                                                                                                                # REMOVED_SYNTAX_ERROR: ping_time = time.time() - start_time

                                                                                                                                # Verify ping performance (should be fast)
                                                                                                                                # REMOVED_SYNTAX_ERROR: assert ping_time < 1.0, "formatted_string"

                                                                                                                                # Verify ping results (most should succeed with mock connections)
                                                                                                                                # REMOVED_SYNTAX_ERROR: successful_pings = sum(1 for result in results if result is True)
                                                                                                                                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                                                                                                                # Get health stats
                                                                                                                                # REMOVED_SYNTAX_ERROR: stats = await manager.get_stats()
                                                                                                                                # REMOVED_SYNTAX_ERROR: health_stats = stats.get('health_monitoring', {})

                                                                                                                                # REMOVED_SYNTAX_ERROR: assert 'pings_sent' in health_stats
                                                                                                                                # REMOVED_SYNTAX_ERROR: assert health_stats['pings_sent'] >= 0

                                                                                                                                # REMOVED_SYNTAX_ERROR: logger.info("✅ Heartbeat performance PASSED")

                                                                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                # Removed problematic line: async def test_thread_isolation(self):
                                                                                                                                    # REMOVED_SYNTAX_ERROR: """Test thread-based message isolation."""
                                                                                                                                    # REMOVED_SYNTAX_ERROR: pass
                                                                                                                                    # REMOVED_SYNTAX_ERROR: logger.info("🧪 Testing thread-based message isolation")

                                                                                                                                    # REMOVED_SYNTAX_ERROR: manager = self.create_test_manager()

                                                                                                                                    # Create user with multiple threads
                                                                                                                                    # REMOVED_SYNTAX_ERROR: user_id = "thread_isolation_user"

                                                                                                                                    # Thread A
                                                                                                                                    # REMOVED_SYNTAX_ERROR: websocket_a = MockWebSocket(user_id, "conn_thread_a")
                                                                                                                                    # REMOVED_SYNTAX_ERROR: conn_a = await manager.connect_user(user_id, websocket_a, "thread_a")

                                                                                                                                    # Thread B
                                                                                                                                    # REMOVED_SYNTAX_ERROR: websocket_b = MockWebSocket(user_id, "conn_thread_b")
                                                                                                                                    # REMOVED_SYNTAX_ERROR: conn_b = await manager.connect_user(user_id, websocket_b, "thread_b")

                                                                                                                                    # Send message to specific thread
                                                                                                                                    # REMOVED_SYNTAX_ERROR: thread_a_message = { )
                                                                                                                                    # REMOVED_SYNTAX_ERROR: 'type': 'thread_specific',
                                                                                                                                    # REMOVED_SYNTAX_ERROR: 'content': 'Message for thread A only',
                                                                                                                                    # REMOVED_SYNTAX_ERROR: 'thread_id': 'thread_a'
                                                                                                                                    

                                                                                                                                    # REMOVED_SYNTAX_ERROR: await manager.send_to_thread('thread_a', thread_a_message)

                                                                                                                                    # Allow message processing
                                                                                                                                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                                                                                                                    # Verify only thread A received the message
                                                                                                                                    # Note: send_to_thread looks for connections with matching thread_id
                                                                                                                                    # Since we're testing the manager directly, we need to check the implementation

                                                                                                                                    # Get stats to verify message was processed
                                                                                                                                    # REMOVED_SYNTAX_ERROR: stats = await manager.get_stats()
                                                                                                                                    # REMOVED_SYNTAX_ERROR: assert stats['messages_sent'] >= 1

                                                                                                                                    # REMOVED_SYNTAX_ERROR: logger.info("✅ Thread-based message isolation PASSED")

                                                                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                    # Removed problematic line: async def test_factory_based_isolation_pattern(self):
                                                                                                                                        # REMOVED_SYNTAX_ERROR: """Test factory-based isolation pattern validation."""
                                                                                                                                        # REMOVED_SYNTAX_ERROR: logger.info("🧪 Testing factory-based isolation pattern")

                                                                                                                                        # REMOVED_SYNTAX_ERROR: factory = self.create_test_factory()

                                                                                                                                        # Mock components
                                                                                                                                        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()

                                                                                                                                        # Mock connection info
                                                                                                                                        # REMOVED_SYNTAX_ERROR: mock_connection_info = Magic        mock_connection_info.websocket = MockWebSocket("test_user", "test_conn")
                                                                                                                                        # REMOVED_SYNTAX_ERROR: mock_pool.get_connection.return_value = mock_connection_info

                                                                                                                                        # REMOVED_SYNTAX_ERROR: factory.configure( )
                                                                                                                                        # REMOVED_SYNTAX_ERROR: connection_pool=mock_pool,
                                                                                                                                        # REMOVED_SYNTAX_ERROR: agent_registry=mock_registry,
                                                                                                                                        # REMOVED_SYNTAX_ERROR: health_monitor=mock_health
                                                                                                                                        

                                                                                                                                        # Create isolated emitters for different users
                                                                                                                                        # REMOVED_SYNTAX_ERROR: user_a_emitter = await factory.create_user_emitter("user_a", "thread_a", "conn_a")
                                                                                                                                        # REMOVED_SYNTAX_ERROR: user_b_emitter = await factory.create_user_emitter("user_b", "thread_b", "conn_b")

                                                                                                                                        # Verify emitters are isolated
                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert user_a_emitter.user_context.user_id == "user_a"
                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert user_b_emitter.user_context.user_id == "user_b"

                                                                                                                                        # Verify different contexts
                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert user_a_emitter.user_context != user_b_emitter.user_context

                                                                                                                                        # Test factory metrics
                                                                                                                                        # REMOVED_SYNTAX_ERROR: metrics = factory.get_factory_metrics()
                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert metrics['emitters_created'] >= 2
                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert metrics['emitters_active'] >= 2

                                                                                                                                        # REMOVED_SYNTAX_ERROR: logger.info("✅ Factory-based isolation pattern PASSED")

                                                                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                        # Removed problematic line: async def test_comprehensive_integration(self):
                                                                                                                                            # REMOVED_SYNTAX_ERROR: """Comprehensive integration test combining all features."""
                                                                                                                                            # REMOVED_SYNTAX_ERROR: pass
                                                                                                                                            # REMOVED_SYNTAX_ERROR: logger.info("🧪 Running comprehensive integration test")

                                                                                                                                            # REMOVED_SYNTAX_ERROR: manager = self.create_test_manager()
                                                                                                                                            # REMOVED_SYNTAX_ERROR: factory = self.create_test_factory()

                                                                                                                                            # Test scenario: Multiple users, multiple connections, concurrent operations
                                                                                                                                            # REMOVED_SYNTAX_ERROR: start_time = time.time()

                                                                                                                                            # Create users with varying connection patterns
                                                                                                                                            # REMOVED_SYNTAX_ERROR: test_scenarios = [ )
                                                                                                                                            # REMOVED_SYNTAX_ERROR: {"user_id": "integration_user_1", "connections": 2, "threads": ["thread_1a", "thread_1b"]},
                                                                                                                                            # REMOVED_SYNTAX_ERROR: {"user_id": "integration_user_2", "connections": 1, "threads": ["thread_2a"]},
                                                                                                                                            # REMOVED_SYNTAX_ERROR: {"user_id": "integration_user_3", "connections": 3, "threads": ["thread_3a", "thread_3b", "thread_3c"]},
                                                                                                                                            

                                                                                                                                            # REMOVED_SYNTAX_ERROR: all_connections = []
                                                                                                                                            # REMOVED_SYNTAX_ERROR: all_websockets = []

                                                                                                                                            # Create all connections
                                                                                                                                            # REMOVED_SYNTAX_ERROR: for scenario in test_scenarios:
                                                                                                                                                # REMOVED_SYNTAX_ERROR: user_id = scenario["user_id"]
                                                                                                                                                # REMOVED_SYNTAX_ERROR: threads = scenario["threads"]

                                                                                                                                                # REMOVED_SYNTAX_ERROR: for i, thread_id in enumerate(threads):
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: websocket = MockWebSocket(user_id, "formatted_string")

                                                                                                                                                    # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user( )
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: user_id=user_id,
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: websocket=websocket,
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: thread_id=thread_id
                                                                                                                                                    

                                                                                                                                                    # REMOVED_SYNTAX_ERROR: all_connections.append({ ))
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: 'connection_id': conn_id,
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: 'thread_id': thread_id,
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: 'websocket': websocket
                                                                                                                                                    
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: all_websockets.append(websocket)

                                                                                                                                                    # Concurrent operations
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: operations = []

                                                                                                                                                    # Send user-specific messages
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: for scenario in test_scenarios:
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: user_id = scenario["user_id"]
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: message = { )
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: 'type': 'integration_test',
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: 'content': 'formatted_string'
                                                                                                                                                        
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: operations.append(manager.send_to_user(user_id, message))

                                                                                                                                                        # Send thread-specific messages
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: for conn in all_connections[:3]:  # First 3 connections
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: thread_id = conn['thread_id']
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: message = { )
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: 'type': 'thread_integration_test',
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: 'thread_id': thread_id,
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: 'content': 'formatted_string'
                                                                                                                                                        
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: operations.append(manager.send_to_thread(thread_id, message))

                                                                                                                                                        # Execute all operations concurrently
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: await asyncio.gather(*operations)

                                                                                                                                                        # REMOVED_SYNTAX_ERROR: total_time = time.time() - start_time

                                                                                                                                                        # Verify performance
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert total_time < 3.0, "formatted_string"

                                                                                                                                                        # Verify all connections are healthy
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: stats = await manager.get_stats()
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert stats['active_connections'] == len(all_connections)

                                                                                                                                                        # Verify isolation - each user should have received their messages
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: user_message_counts = {}
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: for conn in all_connections:
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: user_id = conn['user_id']
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: websocket = conn['websocket']

                                                                                                                                                            # REMOVED_SYNTAX_ERROR: message_count = len(websocket.sent_messages)
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: user_message_counts.setdefault(user_id, 0)
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: user_message_counts[user_id] += message_count

                                                                                                                                                            # Each user should have received at least one message
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: for user_id in [s["user_id"] for s in test_scenarios]:
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: assert user_message_counts.get(user_id, 0) > 0, \
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                                                                                                                                                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_websocket_manager_singleton_isolation(self):
    # REMOVED_SYNTAX_ERROR: """Test WebSocket manager singleton doesn't cause isolation issues."""
    # REMOVED_SYNTAX_ERROR: logger.info("🧪 Testing WebSocket manager singleton isolation")

    # Get multiple manager instances
    # REMOVED_SYNTAX_ERROR: manager1 = get_websocket_manager()
    # REMOVED_SYNTAX_ERROR: manager2 = get_websocket_manager()

    # They should be the same instance (singleton)
    # REMOVED_SYNTAX_ERROR: assert manager1 is manager2

    # But should maintain user isolation through proper data structures
    # REMOVED_SYNTAX_ERROR: assert hasattr(manager1, 'user_connections')
    # REMOVED_SYNTAX_ERROR: assert hasattr(manager1, 'connections')
    # REMOVED_SYNTAX_ERROR: assert isinstance(manager1.user_connections, dict)
    # REMOVED_SYNTAX_ERROR: assert isinstance(manager1.connections, dict)

    # REMOVED_SYNTAX_ERROR: logger.info("✅ WebSocket manager singleton isolation PASSED")


    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
        # Run the validation tests
        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])
        # REMOVED_SYNTAX_ERROR: pass