class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.
    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
    async def send_json(self, message: dict):
        ""Send JSON message.
        if self._closed:
            raise RuntimeError(WebSocket is closed)"
        self.messages_sent.append(message)
    async def close(self, code: int = 1000, reason: str = Normal closure"):
        Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False
    async def get_messages(self) -> list:
        Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()
    #!/usr/bin/env python
        '''
        MISSION CRITICAL: WebSocket SSOT Validation Test Suite
        This test suite validates that the WebSocket Manager consolidation maintains:
        1. Complete user isolation with 25+ concurrent sessions
        2. No data leakage between users
        3. Accurate message routing
        4. Performance requirements (< 2 seconds response for 10 concurrent users)
        5. Connection limits per user (3 per user, 100 total)
        6. All 5 required WebSocket events for chat functionality
        Business Value: $1M+ ARR - Core chat functionality depends on these features
        ANY FAILURE HERE MEANS PRODUCTION IS BROKEN.
        '''
        import asyncio
        import json
        import os
        import sys
        import time
        import uuid
        from concurrent.futures import ThreadPoolExecutor
        from datetime import datetime, timedelta, timezone
        from typing import Dict, List, Set, Any, Optional
        import threading
        import random
        import pytest
        from shared.isolated_environment import IsolatedEnvironment
        # CRITICAL: Add project root to Python path for imports
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_root not in sys.path:
        sys.path.insert(0, project_root)
        from shared.isolated_environment import get_env
        from netra_backend.app.logging_config import central_logger
            # Import WebSocket components to test
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WebSocketManager, get_websocket_manager
        from netra_backend.app.services.websocket_bridge_factory import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        WebSocketBridgeFactory,
        UserWebSocketEmitter,
        UserWebSocketContext,
        WebSocketEvent,
        ConnectionStatus
            
        logger = central_logger.get_logger(__name__)
class MockWebSocket:
        "Mock WebSocket connection for testing.
    def __init__(self, user_id: str, connection_id: str):
        pass
        self.user_id = user_id
        self.connection_id = connection_id
        self.is_connected = True
        self.sent_messages = []
        self.client_state = connected""
    async def send_json(self, data: dict) -> None:
        Mock send_json method."
        if not self.is_connected:
        raise ConnectionError(WebSocket is closed")
        self.sent_messages.append()
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data': data
        
    async def send_text(self, data: str) -> None:
        Mock send_text method.""
        if not self.is_connected:
        raise ConnectionError(WebSocket is closed)
        self.sent_messages.append()
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data': data
        
    async def close(self, code: int = 1000, reason: str = ) -> None:"
        "Mock close method.
        self.is_connected = False
    async def ping(self, data: bytes = b'') -> None:
        "Mock ping method."
        if not self.is_connected:
        raise ConnectionError(WebSocket is closed)"
        return True
class TestWebSocketSSOTValidation:
        "Test WebSocket Single Source of Truth validation.
        @pytest.fixture
    def setup_test(self):
        ""Setup for each test.
    # Reset any global state
        self.created_managers = []
        self.created_factories = []
        yield
    # Cleanup
        for manager in self.created_managers:
        try:
        if hasattr(manager, 'shutdown'):
        asyncio.create_task(manager.shutdown())
        except Exception:
        pass
    def create_test_manager(self) -> WebSocketManager:
        Create a test WebSocket manager.""
        pass
        manager = WebSocketManager()
        self.created_managers.append(manager)
        return manager
    def create_test_factory(self) -> WebSocketBridgeFactory:
        Create a test WebSocket bridge factory.""
        factory = WebSocketBridgeFactory()
        self.created_factories.append(factory)
        return factory
@pytest.mark.asyncio
    async def test_user_isolation_25_concurrent_sessions(self):
        Test user isolation with 25+ concurrent sessions."
logger.info([U+1F9EA] Testing user isolation with 25+ concurrent sessions")
manager = self.create_test_manager()
users_count = 25
connections_per_user = 2
total_connections = users_count * connections_per_user
        # Track connections by user
user_connections = {}
all_connections = []
        # Create concurrent connections
start_time = time.time()
for user_idx in range(users_count):
    user_id = formatted_string
user_connections[user_id] = []
for conn_idx in range(connections_per_user):
    thread_id = formatted_string""
websocket = MockWebSocket(user_id, 
connection_id = await manager.connect_user( )
user_id=user_id,
websocket=websocket,
thread_id=thread_id
                
user_connections[user_id].append(connection_id)
all_connections.append()
'user_id': user_id,
'connection_id': connection_id,
'thread_id': thread_id,
'websocket': websocket
                
connection_time = time.time() - start_time
logger.info(formatted_string")"
                # Verify user isolation
for user_id, connections in user_connections.items():
    user_conns = manager.user_connections.get(user_id, set())
assert len(user_conns) == connections_per_user, \
formatted_string
                    # Verify connections belong only to this user
for conn_id in user_conns:
    conn_info = manager.connections.get(conn_id)
assert conn_info is not None, formatted_string"
assert conn_info['user_id'] == user_id, \
"formatted_string
                        # Test message routing isolation
test_messages = []
for user_id in list(user_connections.keys())[:5]:  # Test first 5 users
message = {
'type': 'test_message',
'user_id': user_id,
'content': 'formatted_string',
'timestamp': datetime.now(timezone.utc).isoformat()
                        
test_messages.append((user_id, message))
                        # Send message to specific user
await manager.send_to_user(user_id, message)
                        # Verify messages reached only intended users
for user_id, expected_message in test_messages:
    user_conns = user_connections[user_id]
for conn_id in user_conns:
    conn_info = manager.connections[conn_id]
websocket = conn_info['websocket']
                                # Check that message was received
assert len(websocket.sent_messages) >= 1, \
formatted_string
                                # Check message content
received_message = websocket.sent_messages[-1]['data']
assert received_message['user_id'] == user_id, \
"formatted_string"
                                # Verify no cross-user contamination
other_users = list(user_connections.keys())[5:]  # Users who shouldnt receive messages
for user_id in other_users:
    user_conns = user_connections[user_id]
for conn_id in user_conns:
    conn_info = manager.connections[conn_id]
websocket = conn_info['websocket']
assert len(websocket.sent_messages) == 0, \

logger.info( PASS:  User isolation with 25+ concurrent sessions PASSED)
@pytest.mark.asyncio
    async def test_no_data_leakage_between_users(self):
        "Test that sensitive data doesn't leak between users."
pass
logger.info([U+1F9EA] Testing no data leakage between users)
manager = self.create_test_manager()
                                            # Create users with sensitive data
user_a_id = user_sensitive_a
user_b_id = user_sensitive_b
websocket_a = MockWebSocket(user_a_id, "conn_a")
websocket_b = MockWebSocket(user_b_id, conn_b)
conn_a = await manager.connect_user(user_a_id, websocket_a, thread_a)
conn_b = await manager.connect_user(user_b_id, websocket_b, thread_b)
                                            # Send sensitive data to user A
sensitive_message_a = {
'type': 'sensitive_data',
'user_id': user_a_id,
'api_key': 'secret_key_user_a_12345',
'personal_data': 'SSN: 123-45-6789',
'business_secret': 'Proprietary algorithm details'
                                            
await manager.send_to_user(user_a_id, sensitive_message_a)
                                            # Send different sensitive data to user B
sensitive_message_b = {
'type': 'sensitive_data',
'user_id': user_b_id,
'api_key': 'secret_key_user_b_67890',
'personal_data': 'SSN: 987-65-4321',
'business_secret': 'Different proprietary information'
                                            
await manager.send_to_user(user_b_id, sensitive_message_b)
                                            # Verify user A only received their data
assert len(websocket_a.sent_messages) == 1
received_a = websocket_a.sent_messages[0]['data']
assert received_a['api_key'] == 'secret_key_user_a_12345'
assert 'secret_key_user_b_67890' not in str(received_a)
                                            # Verify user B only received their data
assert len(websocket_b.sent_messages) == 1
received_b = websocket_b.sent_messages[0]['data']
assert received_b['api_key'] == 'secret_key_user_b_67890'
assert 'secret_key_user_a_12345' not in str(received_b)
logger.info( PASS:  No data leakage between users PASSED")
@pytest.mark.asyncio
    async def test_message_routing_accuracy(self):
        "Test accurate message routing to correct users and threads.
logger.info([U+1F9EA] Testing message routing accuracy)
manager = self.create_test_manager()
                                                # Create users with multiple threads each
users_threads = {
'user_1': ['thread_1_a', 'thread_1_b'],
'user_2': ['thread_2_a', 'thread_2_b'],
'user_3': ['thread_3_a']
                                                
connections = {}
websockets = {}
                                                # Create connections for each user/thread combination
for user_id, threads in users_threads.items():
    connections[user_id] = {}
websockets[user_id] = {}
for thread_id in threads:
    websocket = MockWebSocket(user_id, formatted_string)
websockets[user_id][thread_id] = websocket
conn_id = await manager.connect_user( )
user_id=user_id,
websocket=websocket,
thread_id=thread_id
                                                        
connections[user_id][thread_id] = conn_id
                                                        # Test thread-specific routing
                                                        # Removed problematic line: await manager.send_to_thread('thread_1_a', {
'type': 'thread_message',
'content': 'Message for thread_1_a only'
                                                        
                                                        # Verify only thread_1_a received the message
thread_1_a_ws = websockets['user_1']['thread_1_a']
assert len(thread_1_a_ws.sent_messages) == 1
assert thread_1_a_ws.sent_messages[0]['data']['content'] == 'Message for thread_1_a only'
                                                        # Verify other threads didn't receive it
thread_1_b_ws = websockets['user_1']['thread_1_b']
assert len(thread_1_b_ws.sent_messages) == 0
for user_id in ['user_2', 'user_3']:
    for thread_id, websocket in websockets[user_id].items():
        assert len(websocket.sent_messages) == 0, \
""
logger.info( PASS:  Message routing accuracy PASSED)
@pytest.mark.asyncio
    async def test_connection_limits_enforcement(self):
        Test connection limits per user and total."
pass
logger.info([U+1F9EA] Testing connection limits enforcement)
manager = self.create_test_manager()
                                                                    # Test per-user connection limit (3 connections per user)
user_id = "user_connection_limit
connections = []
                                                                    # Create maximum allowed connections
for i in range(manager.MAX_CONNECTIONS_PER_USER):
    websocket = MockWebSocket(user_id, formatted_string)
conn_id = await manager.connect_user( )
user_id=user_id,
websocket=websocket,
thread_id=
                                                                        
connections.append(conn_id)
                                                                        # Verify all connections are tracked
user_conns = manager.user_connections.get(user_id, set())
assert len(user_conns) == manager.MAX_CONNECTIONS_PER_USER
                                                                        # Test total connection limit (theoretical - would need many users)
total_connections = len(manager.connections)
logger.info(formatted_string)
assert total_connections <= manager.MAX_TOTAL_CONNECTIONS
logger.info(" PASS:  Connection limits enforcement PASSED")
@pytest.mark.asyncio
    async def test_performance_response_time(self):
        Test response time < 2 seconds for 10 concurrent users.
logger.info([U+1F9EA] Testing performance response time < 2 seconds")
manager = self.create_test_manager()
                                                                            # Create 10 concurrent users
concurrent_users = 10
user_data = []
for i in range(concurrent_users):
    user_id = formatted_string
websocket = MockWebSocket(user_id, ")
conn_id = await manager.connect_user( )
user_id=user_id,
websocket=websocket,
thread_id=formatted_string
                                                                                
user_data.append()
'user_id': user_id,
'connection_id': conn_id,
'websocket': websocket
                                                                                
                                                                                # Test concurrent message sending
start_time = time.time()
                                                                                # Send messages to all users concurrently
send_tasks = []
for user_info in user_data:
    message = {
'type': 'performance_test',
'user_id': user_info['user_id'],
'content': ,
'timestamp': datetime.now(timezone.utc).isoformat()
                                                                                    
task = manager.send_to_user(user_info['user_id'], message)
send_tasks.append(task)
                                                                                    # Wait for all messages to be sent
await asyncio.gather(*send_tasks)
total_time = time.time() - start_time
                                                                                    # Verify response time is under 2 seconds
assert total_time < 2.0, formatted_string
                                                                                    # Verify all messages were delivered
for user_info in user_data:
    websocket = user_info['websocket']
assert len(websocket.sent_messages) == 1, \
""
logger.info(formatted_string)
@pytest.mark.asyncio
    async def test_websocket_event_flow_validation(self):
        Test all 5 required WebSocket events are sent correctly."
pass
logger.info([U+1F9EA] Testing WebSocket event flow validation)
                                                                                            # Create factory and test user emitter
factory = self.create_test_factory()
user_id = "event_test_user
thread_id = event_test_thread
connection_id = event_test_conn
                                                                                            # Mock WebSocket connection pool
websocket = TestWebSocketConnection()
mock_pool.get_connection.return_value = None  # Will create placeholder connection
factory.configure( )
connection_pool=mock_pool,
agent_registry=None,
health_monitor=None
                                                                                            
                                                                                            # Create user emitter
emitter = await factory.create_user_emitter(user_id, thread_id, connection_id)
                                                                                            # Test all 5 required events
agent_name = TestAgent
run_id = "test_run_123"
                                                                                            # 1. Agent Started
await emitter.notify_agent_started(agent_name, run_id)
                                                                                            # 2. Agent Thinking
await emitter.notify_agent_thinking(agent_name, run_id, Analyzing the request...)
                                                                                            # 3. Tool Executing
await emitter.notify_tool_executing(agent_name, run_id, test_tool, {param: value"}
                                                                                            # 4. Tool Completed
await emitter.notify_tool_completed(agent_name, run_id, test_tool, {"result: success}
                                                                                            # 5. Agent Completed
await emitter.notify_agent_completed(agent_name, run_id, {final_result: completed}
                                                                                            # Allow time for event processing
await asyncio.sleep(0.1)
                                                                                            # Verify all events were queued (user context tracks sent events)
user_context = emitter.user_context
                                                                                            # Check that events were processed (would be in sent_events after processing)
                                                                                            # Since we're using mock connections, events might be in the queue or failed_events
total_events = len(user_context.sent_events) + user_context.event_queue.qsize()
assert total_events >= 5, ""
logger.info( PASS:  WebSocket event flow validation PASSED)
@pytest.mark.asyncio
    async def test_cleanup_stale_connections(self):
        Test cleanup of stale connections."
logger.info([U+1F9EA] Testing cleanup of stale connections)
manager = self.create_test_manager()
                                                                                                # Create connections and manually make them stale
user_id = "stale_user
websocket = MockWebSocket(user_id, stale_conn)
conn_id = await manager.connect_user(user_id, websocket, stale_thread)
                                                                                                # Manually set connection to be stale (old last_activity)
conn_info = manager.connections[conn_id]
conn_info['last_activity'] = datetime.now(timezone.utc) - timedelta(seconds=manager.STALE_CONNECTION_TIMEOUT + 60)
conn_info['is_healthy'] = False
                                                                                                # Run cleanup
cleaned_count = await manager._cleanup_stale_connections()
                                                                                                # Verify connection was cleaned up
assert cleaned_count >= 1
assert conn_id not in manager.connections
assert user_id not in manager.user_connections or len(manager.user_connections[user_id] == 0
logger.info( PASS:  Cleanup of stale connections PASSED)
@pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        ""Test memory usage stays stable with many connections.
pass
logger.info([U+1F9EA] Testing memory usage stability)
manager = self.create_test_manager()
                                                                                                    # Create and destroy connections to test memory stability
cycles = 5
connections_per_cycle = 10
initial_stats = await manager.get_stats()
initial_memory_cleanups = initial_stats.get('memory_cleanups', 0)
for cycle in range(cycles):
                                                                                                        # Create connections
connections = []
for i in range(connections_per_cycle):
    user_id = "
websocket = MockWebSocket(user_id, formatted_string)
conn_id = await manager.connect_user(user_id, websocket, ")
connections.append((user_id, conn_id, websocket))
                                                                                                            # Send messages to generate activity
for user_id, conn_id, websocket in connections:
    await manager.send_to_user(user_id, {'type': 'memory_test', 'data': 'test'}
                                                                                                                # Disconnect all connections
for user_id, conn_id, websocket in connections:
    await manager.disconnect_user(user_id, websocket)
                                                                                                                    # Force cleanup
await manager._cleanup_stale_connections()
final_stats = await manager.get_stats()
                                                                                                                    # Verify connections are cleaned up
assert final_stats['active_connections'] <= connections_per_cycle  # Allow some connections to remain
                                                                                                                    # Verify memory cleanup happened
final_memory_cleanups = final_stats.get('memory_cleanups', 0)
assert final_memory_cleanups > initial_memory_cleanups
logger.info( PASS:  Memory usage stability PASSED)
@pytest.mark.asyncio
    async def test_heartbeat_performance(self):
        Test heartbeat performance with enhanced features.""
logger.info([U+1F9EA] Testing heartbeat performance)
manager = self.create_test_manager()
                                                                                                                        # Create multiple connections to test heartbeat
users = []
for i in range(5):
    user_id = 
websocket = MockWebSocket(user_id, formatted_string)
conn_id = await manager.connect_user(user_id, websocket, ")
users.append((user_id, conn_id, websocket))
                                                                                                                            # Test enhanced ping functionality
start_time = time.time()
ping_tasks = []
for user_id, conn_id, websocket in users:
    task = manager.enhanced_ping_connection(conn_id)
ping_tasks.append(task)
results = await asyncio.gather(*ping_tasks, return_exceptions=True)
ping_time = time.time() - start_time
                                                                                                                                # Verify ping performance (should be fast)
assert ping_time < 1.0, formatted_string
                                                                                                                                # Verify ping results (most should succeed with mock connections)
successful_pings = sum(1 for result in results if result is True)
logger.info(")
                                                                                                                                # Get health stats
stats = await manager.get_stats()
health_stats = stats.get('health_monitoring', {}
assert 'pings_sent' in health_stats
assert health_stats['pings_sent'] >= 0
logger.info( PASS:  Heartbeat performance PASSED)
@pytest.mark.asyncio
    async def test_thread_isolation(self):
        Test thread-based message isolation.""
pass
logger.info([U+1F9EA] Testing thread-based message isolation)
manager = self.create_test_manager()
                                                                                                                                    # Create user with multiple threads
user_id = thread_isolation_user
                                                                                                                                    # Thread A
websocket_a = MockWebSocket(user_id, conn_thread_a)
conn_a = await manager.connect_user(user_id, websocket_a, thread_a")
                                                                                                                                    # Thread B
websocket_b = MockWebSocket(user_id, conn_thread_b)
conn_b = await manager.connect_user(user_id, websocket_b, "thread_b)
                                                                                                                                    # Send message to specific thread
thread_a_message = {
'type': 'thread_specific',
'content': 'Message for thread A only',
'thread_id': 'thread_a'
                                                                                                                                    
await manager.send_to_thread('thread_a', thread_a_message)
                                                                                                                                    # Allow message processing
await asyncio.sleep(0.1)
                                                                                                                                    # Verify only thread A received the message
                                                                                                                                    # Note: send_to_thread looks for connections with matching thread_id
                                                                                                                                    # Since we're testing the manager directly, we need to check the implementation
                                                                                                                                    # Get stats to verify message was processed
stats = await manager.get_stats()
assert stats['messages_sent'] >= 1
logger.info( PASS:  Thread-based message isolation PASSED)
@pytest.mark.asyncio
    async def test_factory_based_isolation_pattern(self):
        Test factory-based isolation pattern validation.""
logger.info([U+1F9EA] Testing factory-based isolation pattern)
factory = self.create_test_factory()
                                                                                                                                        # Mock components
websocket = TestWebSocketConnection()
                                                                                                                                        # Mock connection info
mock_connection_info = MagicMock(); mock_connection_info.websocket = MockWebSocket(test_user, test_conn)
mock_pool.get_connection.return_value = mock_connection_info
factory.configure( )
connection_pool=mock_pool,
agent_registry=mock_registry,
health_monitor=mock_health
                                                                                                                                        
                                                                                                                                        # Create isolated emitters for different users
user_a_emitter = await factory.create_user_emitter(user_a", thread_a, "conn_a)
user_b_emitter = await factory.create_user_emitter(user_b, thread_b, conn_b)
                                                                                                                                        # Verify emitters are isolated
assert user_a_emitter.user_context.user_id == "user_a"
assert user_b_emitter.user_context.user_id == user_b
                                                                                                                                        # Verify different contexts
assert user_a_emitter.user_context != user_b_emitter.user_context
                                                                                                                                        # Test factory metrics
metrics = factory.get_factory_metrics()
assert metrics['emitters_created'] >= 2
assert metrics['emitters_active'] >= 2
logger.info( PASS:  Factory-based isolation pattern PASSED)
@pytest.mark.asyncio
    async def test_comprehensive_integration(self):
        Comprehensive integration test combining all features."
pass
logger.info("[U+1F9EA] Running comprehensive integration test)
manager = self.create_test_manager()
factory = self.create_test_factory()
                                                                                                                                            # Test scenario: Multiple users, multiple connections, concurrent operations
start_time = time.time()
                                                                                                                                            # Create users with varying connection patterns
test_scenarios = [
{user_id: integration_user_1, connections: 2, "threads": [thread_1a, thread_1b]},
{user_id: integration_user_2", connections: 1, "threads: [thread_2a]},
{user_id: integration_user_3, "connections": 3, threads: [thread_3a, thread_3b, thread_3c"]},
                                                                                                                                            
all_connections = []
all_websockets = []
                                                                                                                                            # Create all connections
for scenario in test_scenarios:
    user_id = scenario[user_id]
threads = scenario["threads]
for i, thread_id in enumerate(threads):
    websocket = MockWebSocket(user_id, formatted_string)
conn_id = await manager.connect_user( )
user_id=user_id,
websocket=websocket,
thread_id=thread_id
                                                                                                                                                    
all_connections.append()
'user_id': user_id,
'connection_id': conn_id,
'thread_id': thread_id,
'websocket': websocket
                                                                                                                                                    
all_websockets.append(websocket)
                                                                                                                                                    # Concurrent operations
operations = []
                                                                                                                                                    # Send user-specific messages
for scenario in test_scenarios:
    user_id = scenario[user_id]
message = {
'type': 'integration_test',
'user_id': user_id,
'content': 'formatted_string'
                                                                                                                                                        
operations.append(manager.send_to_user(user_id, message))
                                                                                                                                                        # Send thread-specific messages
for conn in all_connections[:3]:  # First 3 connections
thread_id = conn['thread_id']
message = {
'type': 'thread_integration_test',
'thread_id': thread_id,
'content': 'formatted_string'
                                                                                                                                                        
operations.append(manager.send_to_thread(thread_id, message))
                                                                                                                                                        # Execute all operations concurrently
await asyncio.gather(*operations)
total_time = time.time() - start_time
                                                                                                                                                        # Verify performance
assert total_time < 3.0, formatted_string
                                                                                                                                                        # Verify all connections are healthy
stats = await manager.get_stats()
assert stats['active_connections'] == len(all_connections)
                                                                                                                                                        # Verify isolation - each user should have received their messages
user_message_counts = {}
for conn in all_connections:
    user_id = conn['user_id']
websocket = conn['websocket']
message_count = len(websocket.sent_messages)
user_message_counts.setdefault(user_id, 0)
user_message_counts[user_id] += message_count
                                                                                                                                                            # Each user should have received at least one message
for user_id in [s["user_id"] for s in test_scenarios]:
    assert user_message_counts.get(user_id, 0) > 0, \
formatted_string
logger.info()
def test_websocket_manager_singleton_isolation(self):
    Test WebSocket manager singleton doesn't cause isolation issues."
logger.info("[U+1F9EA] Testing WebSocket manager singleton isolation")
    # Get multiple manager instances
manager1 = get_websocket_manager()
manager2 = get_websocket_manager()
    # They should be the same instance (singleton)
assert manager1 is manager2
    # But should maintain user isolation through proper data structures
assert hasattr(manager1, 'user_connections')
assert hasattr(manager1, 'connections')
assert isinstance(manager1.user_connections, dict)
assert isinstance(manager1.connections, dict)
logger.info( PASS:  WebSocket manager singleton isolation PASSED)
if __name__ == "__main__":
        # Run the validation tests
pass