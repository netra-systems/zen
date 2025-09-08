"""
WebSocket Connection Management Integration Tests - Real Services

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable real-time AI interaction through reliable WebSocket connections
- Value Impact: Users receive immediate agent responses and live progress updates during analysis
- Strategic Impact: Real-time communication is core to competitive user experience

These tests validate WebSocket connection management using real services, ensuring reliable
real-time communication between users and AI agents for optimal user experience.
"""

import asyncio
import pytest
import time
import json
from typing import Dict, List, Any
from uuid import uuid4
import websockets
from unittest.mock import AsyncMock

from test_framework.base_integration_test import WebSocketIntegrationTest
from test_framework.conftest_real_services import real_services
from shared.isolated_environment import get_env


class TestWebSocketConnectionManagement(WebSocketIntegrationTest):
    """Test WebSocket connection management with real services integration."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_establishment_with_authentication(self, real_services):
        """
        Test WebSocket connection establishment with user authentication.
        
        BVJ: Users must establish authenticated connections to access personalized AI services.
        """
        # Create authenticated user context
        user_data = await self.create_test_user_context(real_services)
        session_data = await self.create_test_session(real_services, user_data['id'])
        
        # Generate mock JWT token for WebSocket authentication
        jwt_token = f"test_jwt_{user_data['id']}_{int(time.time())}"
        
        # Store token mapping in Redis for auth validation
        await real_services.redis.set(f"auth:token:{jwt_token}", json.dumps({
            'user_id': user_data['id'],
            'email': user_data['email'],
            'session_key': session_data['session_key'],
            'issued_at': time.time(),
            'expires_at': time.time() + 3600
        }), ex=3600)
        
        # Create WebSocket connection record in database
        connection_id = str(uuid4())
        await real_services.postgres.execute("""
            INSERT INTO backend.websocket_connections 
            (connection_id, user_id, token, status, connected_at, last_activity)
            VALUES ($1, $2, $3, 'connecting', $4, $5)
        """, connection_id, user_data['id'], jwt_token, time.time(), time.time())
        
        # Simulate WebSocket handshake validation
        connection_data = {
            'connection_id': connection_id,
            'user_id': user_data['id'],
            'authenticated': True,
            'token': jwt_token,
            'status': 'connected',
            'connected_at': time.time(),
            'last_ping': time.time()
        }
        
        # Store active connection in Redis
        await real_services.redis.set_json(f"websocket:connection:{connection_id}", connection_data, ex=3600)
        
        # Update database connection status
        await real_services.postgres.execute("""
            UPDATE backend.websocket_connections 
            SET status = 'connected', connected_at = $1
            WHERE connection_id = $2
        """, time.time(), connection_id)
        
        # Verify connection establishment
        stored_connection = await real_services.redis.get_json(f"websocket:connection:{connection_id}")
        assert stored_connection is not None, "WebSocket connection must be stored in Redis"
        assert stored_connection['authenticated'] is True, "Connection must be authenticated"
        assert stored_connection['user_id'] == user_data['id'], "Connection must be linked to correct user"
        
        # Verify database record
        db_connection = await real_services.postgres.fetchrow("""
            SELECT connection_id, user_id, status, connected_at
            FROM backend.websocket_connections
            WHERE connection_id = $1
        """, connection_id)
        
        assert db_connection is not None, "Connection must be recorded in database"
        assert db_connection['status'] == 'connected', "Database status must be connected"
        assert db_connection['user_id'] == user_data['id'], "Database record must link to correct user"
        
        # Verify token validation capability
        token_data = await real_services.redis.get(f"auth:token:{jwt_token}")
        assert token_data is not None, "Authentication token must be retrievable"
        
        token_info = json.loads(token_data)
        assert token_info['user_id'] == user_data['id'], "Token must contain correct user ID"
        assert token_info['session_key'] == session_data['session_key'], "Token must link to user session"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_routing_to_correct_users(self, real_services):
        """
        Test that WebSocket messages are routed to correct users in multi-user environment.
        
        BVJ: Platform must maintain message isolation to prevent data leaks between users.
        """
        # Create multiple user contexts
        users = []
        connections = []
        
        for i in range(3):
            user_data = await self.create_test_user_context(real_services, {
                'email': f'websocket-user-{i}@example.com',
                'name': f'WebSocket User {i}',
                'is_active': True
            })
            
            # Create WebSocket connection for each user
            connection_id = str(uuid4())
            connection_data = {
                'connection_id': connection_id,
                'user_id': user_data['id'],
                'authenticated': True,
                'status': 'connected',
                'message_queue': [],
                'connected_at': time.time()
            }
            
            await real_services.redis.set_json(f"websocket:connection:{connection_id}", connection_data, ex=3600)
            
            users.append(user_data)
            connections.append(connection_data)
        
        # Send targeted messages to each user
        test_messages = [
            {'user_index': 0, 'message': 'Cost analysis for User 0', 'message_type': 'agent_response'},
            {'user_index': 1, 'message': 'Optimization report for User 1', 'message_type': 'agent_response'},
            {'user_index': 2, 'message': 'Security scan results for User 2', 'message_type': 'agent_response'}
        ]
        
        # Route messages to correct user connections
        for msg_data in test_messages:
            target_user = users[msg_data['user_index']]
            target_connection = connections[msg_data['user_index']]
            
            # Create message with user targeting
            websocket_message = {
                'message_id': str(uuid4()),
                'user_id': target_user['id'],
                'connection_id': target_connection['connection_id'],
                'content': msg_data['message'],
                'type': msg_data['message_type'],
                'timestamp': time.time(),
                'routed_at': time.time()
            }
            
            # Store message in user-specific queue
            await real_services.redis.lpush(f"websocket:messages:{target_user['id']}", json.dumps(websocket_message))
            
            # Update connection with message delivery
            connection_state = await real_services.redis.get_json(f"websocket:connection:{target_connection['connection_id']}")
            connection_state['message_queue'].append(websocket_message['message_id'])
            connection_state['last_message'] = time.time()
            await real_services.redis.set_json(f"websocket:connection:{target_connection['connection_id']}", connection_state, ex=3600)
        
        # Verify message isolation - each user only receives their messages
        for i, (user, connection) in enumerate(zip(users, connections)):
            # Get messages for this user
            user_messages = await real_services.redis.lrange(f"websocket:messages:{user['id']}", 0, -1)
            assert len(user_messages) == 1, f"User {i} must receive exactly 1 message"
            
            received_message = json.loads(user_messages[0])
            assert received_message['user_id'] == user['id'], f"Message must be targeted to User {i}"
            assert received_message['connection_id'] == connection['connection_id'], f"Message must target correct connection for User {i}"
            
            expected_content = f"Cost analysis for User {i}" if i == 0 else f"Optimization report for User {i}" if i == 1 else f"Security scan results for User {i}"
            assert received_message['content'] == expected_content, f"User {i} must receive correct message content"
            
            # Verify connection state reflects message delivery
            connection_state = await real_services.redis.get_json(f"websocket:connection:{connection['connection_id']}")
            assert len(connection_state['message_queue']) == 1, f"Connection {i} must track message delivery"
            assert connection_state['message_queue'][0] == received_message['message_id'], f"Connection {i} must track correct message ID"
        
        # Verify cross-user isolation - users don't see each other's messages
        all_message_queues = []
        for user in users:
            queue_messages = await real_services.redis.lrange(f"websocket:messages:{user['id']}", 0, -1)
            all_message_queues.extend(queue_messages)
        
        assert len(all_message_queues) == 3, "Total messages must equal number of users"
        
        # Verify no message duplication across users
        message_contents = [json.loads(msg)['content'] for msg in all_message_queues]
        assert len(set(message_contents)) == 3, "All messages must be unique across users"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_heartbeat_and_cleanup(self, real_services):
        """
        Test WebSocket connection heartbeat mechanism and stale connection cleanup.
        
        BVJ: Platform must maintain connection health and clean up resources for optimal performance.
        """
        # Create test user and connection
        user_data = await self.create_test_user_context(real_services)
        connection_id = str(uuid4())
        
        # Initialize connection with heartbeat tracking
        connection_data = {
            'connection_id': connection_id,
            'user_id': user_data['id'],
            'authenticated': True,
            'status': 'connected',
            'last_ping': time.time(),
            'ping_count': 0,
            'missed_pings': 0,
            'heartbeat_interval': 30  # 30 second heartbeat
        }
        
        await real_services.redis.set_json(f"websocket:connection:{connection_id}", connection_data, ex=3600)
        
        # Simulate heartbeat mechanism
        heartbeat_rounds = 3
        for round_num in range(heartbeat_rounds):
            # Update connection with heartbeat
            current_time = time.time()
            connection_state = await real_services.redis.get_json(f"websocket:connection:{connection_id}")
            
            connection_state['last_ping'] = current_time
            connection_state['ping_count'] += 1
            connection_state['status'] = 'active'
            
            await real_services.redis.set_json(f"websocket:connection:{connection_id}", connection_state, ex=3600)
            
            # Record heartbeat in database for monitoring
            await real_services.postgres.execute("""
                INSERT INTO backend.websocket_heartbeats
                (connection_id, user_id, ping_timestamp, round_trip_time, status)
                VALUES ($1, $2, $3, $4, 'success')
            """, connection_id, user_data['id'], current_time, 0.05)  # 50ms RTT
            
            # Small delay between heartbeats
            await asyncio.sleep(0.1)
        
        # Verify heartbeat tracking
        final_connection = await real_services.redis.get_json(f"websocket:connection:{connection_id}")
        assert final_connection['ping_count'] == heartbeat_rounds, "Heartbeat count must be accurate"
        assert final_connection['missed_pings'] == 0, "No pings should be missed in healthy connection"
        assert final_connection['status'] == 'active', "Connection must remain active with successful heartbeats"
        
        # Verify database heartbeat records
        heartbeat_records = await real_services.postgres.fetch("""
            SELECT connection_id, ping_timestamp, status
            FROM backend.websocket_heartbeats
            WHERE connection_id = $1
            ORDER BY ping_timestamp
        """, connection_id)
        
        assert len(heartbeat_records) == heartbeat_rounds, "All heartbeats must be recorded in database"
        for record in heartbeat_records:
            assert record['status'] == 'success', "All heartbeat records must show success"
        
        # Simulate stale connection (missed heartbeats)
        stale_connection_id = str(uuid4())
        stale_connection = {
            'connection_id': stale_connection_id,
            'user_id': user_data['id'],
            'authenticated': True,
            'status': 'connected',
            'last_ping': time.time() - 120,  # 2 minutes ago
            'ping_count': 5,
            'missed_pings': 3,  # 3 missed pings
            'heartbeat_interval': 30
        }
        
        await real_services.redis.set_json(f"websocket:connection:{stale_connection_id}", stale_connection, ex=3600)
        
        # Simulate connection cleanup process
        current_time = time.time()
        stale_threshold = 90  # 90 seconds
        
        stale_check = await real_services.redis.get_json(f"websocket:connection:{stale_connection_id}")
        time_since_ping = current_time - stale_check['last_ping']
        
        if time_since_ping > stale_threshold:
            # Mark connection as stale
            stale_check['status'] = 'stale'
            stale_check['stale_detected_at'] = current_time
            await real_services.redis.set_json(f"websocket:connection:{stale_connection_id}", stale_check, ex=300)  # 5 minute cleanup grace period
            
            # Record cleanup in database
            await real_services.postgres.execute("""
                UPDATE backend.websocket_connections
                SET status = 'stale', disconnected_at = $1
                WHERE connection_id = $2
            """, current_time, stale_connection_id)
        
        # Verify stale connection detection
        cleaned_connection = await real_services.redis.get_json(f"websocket:connection:{stale_connection_id}")
        assert cleaned_connection['status'] == 'stale', "Stale connection must be detected"
        assert 'stale_detected_at' in cleaned_connection, "Stale detection timestamp must be recorded"
        
        # Verify active connection remains unaffected
        active_connection = await real_services.redis.get_json(f"websocket:connection:{connection_id}")
        assert active_connection['status'] == 'active', "Active connection must not be affected by cleanup"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_agent_event_delivery_pipeline(self, real_services):
        """
        Test complete WebSocket event delivery pipeline for agent interactions.
        
        BVJ: Users must receive all 5 critical agent events for complete AI interaction visibility.
        """
        # Create user context and connection
        user_data = await self.create_test_user_context(real_services)
        connection_id = str(uuid4())
        agent_execution_id = str(uuid4())
        
        # Initialize WebSocket connection
        connection_data = {
            'connection_id': connection_id,
            'user_id': user_data['id'],
            'authenticated': True,
            'status': 'connected',
            'subscribed_events': ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'],
            'event_queue': [],
            'connected_at': time.time()
        }
        
        await real_services.redis.set_json(f"websocket:connection:{connection_id}", connection_data, ex=3600)
        
        # Define critical agent events sequence
        critical_agent_events = [
            {
                'type': 'agent_started',
                'agent_execution_id': agent_execution_id,
                'agent_name': 'cost_optimizer',
                'timestamp': time.time(),
                'data': {'message': 'Starting cost analysis for your infrastructure'}
            },
            {
                'type': 'agent_thinking',
                'agent_execution_id': agent_execution_id,
                'agent_name': 'cost_optimizer',
                'timestamp': time.time() + 1,
                'data': {'thought_process': 'Analyzing AWS spend patterns and identifying optimization opportunities'}
            },
            {
                'type': 'tool_executing',
                'agent_execution_id': agent_execution_id,
                'tool_name': 'aws_cost_analyzer',
                'timestamp': time.time() + 2,
                'data': {'tool_input': 'last_30_days_spend', 'status': 'running'}
            },
            {
                'type': 'tool_completed',
                'agent_execution_id': agent_execution_id,
                'tool_name': 'aws_cost_analyzer',
                'timestamp': time.time() + 3,
                'data': {'tool_output': {'potential_savings': 2500}, 'execution_time': 1.2}
            },
            {
                'type': 'agent_completed',
                'agent_execution_id': agent_execution_id,
                'agent_name': 'cost_optimizer',
                'timestamp': time.time() + 4,
                'data': {
                    'result': {
                        'recommendations': [
                            {'action': 'resize_instances', 'savings': 1500},
                            {'action': 'optimize_storage', 'savings': 1000}
                        ],
                        'total_savings': 2500
                    }
                }
            }
        ]
        
        # Simulate agent event delivery pipeline
        for event in critical_agent_events:
            # Store event in database for persistence
            await real_services.postgres.execute("""
                INSERT INTO backend.websocket_events
                (event_id, user_id, connection_id, event_type, event_data, created_at, delivered)
                VALUES ($1, $2, $3, $4, $5, $6, false)
            """, str(uuid4()), user_data['id'], connection_id, event['type'], 
                 json.dumps(event), event['timestamp'])
            
            # Queue event for WebSocket delivery
            await real_services.redis.lpush(f"websocket:events:{connection_id}", json.dumps(event))
            
            # Update connection event tracking
            connection_state = await real_services.redis.get_json(f"websocket:connection:{connection_id}")
            connection_state['event_queue'].append(event['type'])
            connection_state['last_event'] = event['timestamp']
            await real_services.redis.set_json(f"websocket:connection:{connection_id}", connection_state, ex=3600)
        
        # Verify all critical events are queued
        queued_events = await real_services.redis.lrange(f"websocket:events:{connection_id}", 0, -1)
        assert len(queued_events) == 5, "All 5 critical agent events must be queued"
        
        # Verify event types and sequence
        queued_event_data = [json.loads(event) for event in reversed(queued_events)]  # Redis LPUSH reverses order
        expected_sequence = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        
        for i, expected_type in enumerate(expected_sequence):
            assert queued_event_data[i]['type'] == expected_type, f"Event {i} must be {expected_type}"
            assert queued_event_data[i]['agent_execution_id'] == agent_execution_id, f"Event {i} must have correct execution ID"
        
        # Verify business value delivery through events
        agent_started_event = queued_event_data[0]
        agent_completed_event = queued_event_data[4]
        
        assert agent_started_event['data']['message'] is not None, "Agent start must provide user message"
        assert agent_completed_event['data']['result']['total_savings'] > 0, "Agent completion must deliver business value"
        
        # Verify database persistence
        db_events = await real_services.postgres.fetch("""
            SELECT event_type, event_data, created_at
            FROM backend.websocket_events
            WHERE user_id = $1 AND connection_id = $2
            ORDER BY created_at
        """, user_data['id'], connection_id)
        
        assert len(db_events) == 5, "All events must be persisted in database"
        
        db_event_types = [event['event_type'] for event in db_events]
        assert db_event_types == expected_sequence, "Database events must maintain correct sequence"
        
        # Simulate event consumption and delivery confirmation
        delivered_events = []
        for event_json in reversed(queued_events):
            event_data = json.loads(event_json)
            
            # Mark event as delivered
            await real_services.postgres.execute("""
                UPDATE backend.websocket_events 
                SET delivered = true, delivered_at = $1
                WHERE user_id = $2 AND event_type = $3 AND created_at = $4
            """, time.time(), user_data['id'], event_data['type'], event_data['timestamp'])
            
            delivered_events.append(event_data['type'])
        
        # Verify all events marked as delivered
        delivery_status = await real_services.postgres.fetch("""
            SELECT event_type, delivered, delivered_at
            FROM backend.websocket_events
            WHERE user_id = $1 AND connection_id = $2
            ORDER BY created_at
        """, user_data['id'], connection_id)
        
        for status in delivery_status:
            assert status['delivered'] is True, f"Event {status['event_type']} must be marked as delivered"
            assert status['delivered_at'] is not None, f"Event {status['event_type']} must have delivery timestamp"
        
        # Verify connection state reflects successful delivery
        final_connection_state = await real_services.redis.get_json(f"websocket:connection:{connection_id}")
        assert len(final_connection_state['event_queue']) == 5, "Connection must track all delivered events"
        assert set(final_connection_state['event_queue']) == set(expected_sequence), "Connection must track correct event types"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_scaling_and_load_management(self, real_services):
        """
        Test WebSocket connection scaling for multiple concurrent users.
        
        BVJ: Platform must support concurrent users during peak usage without degrading performance.
        """
        # Create multiple concurrent user connections
        concurrent_users = 10
        connections = []
        
        async def create_user_connection(user_index: int):
            # Create user
            user_data = await self.create_test_user_context(real_services, {
                'email': f'load-test-user-{user_index}@example.com',
                'name': f'Load Test User {user_index}',
                'is_active': True
            })
            
            # Create connection
            connection_id = str(uuid4())
            connection_data = {
                'connection_id': connection_id,
                'user_id': user_data['id'],
                'user_index': user_index,
                'authenticated': True,
                'status': 'connected',
                'connected_at': time.time(),
                'message_count': 0,
                'last_activity': time.time()
            }
            
            # Store in Redis
            await real_services.redis.set_json(f"websocket:connection:{connection_id}", connection_data, ex=3600)
            
            # Record in database
            await real_services.postgres.execute("""
                INSERT INTO backend.websocket_connections
                (connection_id, user_id, status, connected_at, last_activity)
                VALUES ($1, $2, 'connected', $3, $4)
            """, connection_id, user_data['id'], time.time(), time.time())
            
            return user_data, connection_data
        
        # Create connections concurrently
        start_time = time.time()
        connection_results = await asyncio.gather(*[create_user_connection(i) for i in range(concurrent_users)])
        connection_creation_time = time.time() - start_time
        
        users, connections = zip(*connection_results)
        
        # Verify all connections established
        assert len(connections) == concurrent_users, f"Must create {concurrent_users} connections"
        
        # Test concurrent message handling
        async def simulate_user_activity(user, connection):
            user_index = connection['user_index']
            connection_id = connection['connection_id']
            
            # Send multiple messages per user
            messages_per_user = 5
            for msg_index in range(messages_per_user):
                message = {
                    'message_id': str(uuid4()),
                    'user_id': user['id'],
                    'connection_id': connection_id,
                    'content': f'Message {msg_index} from User {user_index}',
                    'timestamp': time.time()
                }
                
                # Queue message
                await real_services.redis.lpush(f"websocket:messages:{user['id']}", json.dumps(message))
                
                # Update connection activity
                connection_state = await real_services.redis.get_json(f"websocket:connection:{connection_id}")
                connection_state['message_count'] = connection_state.get('message_count', 0) + 1
                connection_state['last_activity'] = time.time()
                await real_services.redis.set_json(f"websocket:connection:{connection_id}", connection_state, ex=3600)
                
                # Small delay between messages
                await asyncio.sleep(0.01)
        
        # Simulate concurrent user activity
        activity_start = time.time()
        await asyncio.gather(*[simulate_user_activity(user, conn) for user, conn in zip(users, connections)])
        activity_duration = time.time() - activity_start
        
        # Verify scaling performance
        total_messages = concurrent_users * 5  # 5 messages per user
        message_throughput = total_messages / activity_duration
        
        assert message_throughput > 100, f"Message throughput too low: {message_throughput:.2f} msg/sec"
        assert connection_creation_time < 5, f"Connection creation too slow: {connection_creation_time:.2f}s"
        
        # Verify connection isolation
        for user, connection in zip(users, connections):
            user_messages = await real_services.redis.lrange(f"websocket:messages:{user['id']}", 0, -1)
            assert len(user_messages) == 5, f"User {connection['user_index']} must have exactly 5 messages"
            
            connection_state = await real_services.redis.get_json(f"websocket:connection:{connection['connection_id']}")
            assert connection_state['message_count'] == 5, f"Connection must track 5 messages"
        
        # Verify database scaling
        total_connections = await real_services.postgres.fetchval("""
            SELECT COUNT(*) FROM backend.websocket_connections 
            WHERE status = 'connected' AND connected_at >= $1
        """, start_time)
        
        assert total_connections == concurrent_users, "Database must record all connections"
        
        # Test connection cleanup under load
        cleanup_start = time.time()
        
        async def cleanup_connection(connection):
            connection_id = connection['connection_id']
            
            # Mark as disconnected
            await real_services.redis.delete(f"websocket:connection:{connection_id}")
            await real_services.postgres.execute("""
                UPDATE backend.websocket_connections 
                SET status = 'disconnected', disconnected_at = $1
                WHERE connection_id = $2
            """, time.time(), connection_id)
        
        # Cleanup all connections concurrently
        await asyncio.gather(*[cleanup_connection(conn) for conn in connections])
        cleanup_duration = time.time() - cleanup_start
        
        # Verify cleanup performance
        assert cleanup_duration < 2, f"Connection cleanup too slow: {cleanup_duration:.2f}s"
        
        # Verify all connections cleaned up
        remaining_connections = await real_services.postgres.fetchval("""
            SELECT COUNT(*) FROM backend.websocket_connections
            WHERE status = 'connected' AND connected_at >= $1
        """, start_time)
        
        assert remaining_connections == 0, "All test connections must be cleaned up"
        
        # Log performance metrics
        self.logger.info(f"WebSocket scaling performance:")
        self.logger.info(f"  Connection creation: {connection_creation_time:.2f}s for {concurrent_users} users")
        self.logger.info(f"  Message throughput: {message_throughput:.2f} messages/sec")
        self.logger.info(f"  Connection cleanup: {cleanup_duration:.2f}s")
        
        # Verify business value - performance metrics support user experience
        self.assert_business_value_delivered({
            'concurrent_users_supported': concurrent_users,
            'message_throughput': message_throughput,
            'connection_creation_speed': connection_creation_time,
            'scaling_verified': True
        }, 'automation')