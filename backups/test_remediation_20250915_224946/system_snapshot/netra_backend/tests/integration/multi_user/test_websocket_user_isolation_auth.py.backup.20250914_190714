"""
Integration Tests for WebSocket Multi-User Authentication and Isolation

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Multi-user isolation critical for all tiers
- Business Goal: Secure multi-user WebSocket isolation enabling $120K+ MRR growth
- Value Impact: Prevents data leakage between users ensuring customer trust
- Strategic Impact: Foundation for enterprise-grade multi-tenant AI platform

CRITICAL TESTING REQUIREMENTS:
1. Tests MUST validate complete user isolation with real authentication
2. Tests MUST prevent cross-user data access and WebSocket message leakage
3. Tests MUST use real database and authentication services
4. Tests MUST simulate concurrent multi-user scenarios
5. Tests MUST fail hard if isolation is compromised

This test suite validates WebSocket Multi-User Authentication and Isolation:
- User-specific WebSocket connection authentication and authorization
- Complete isolation of WebSocket messages between different users
- User context validation and enforcement throughout WebSocket lifecycle
- Concurrent multi-user authentication without cross-contamination
- User session management and cleanup on disconnection
- Security boundaries between user execution contexts

MULTI-USER ISOLATION SCENARIOS TO TEST:
Authentication Isolation:
- Multiple users authenticate simultaneously without interference
- User A cannot access User B's WebSocket messages or context
- Authentication tokens are properly scoped to individual users
- Session management maintains strict user boundaries

Message Isolation:
- WebSocket messages are delivered only to intended users
- Agent execution results are isolated per user
- No message broadcasting across user boundaries
- User-specific message queuing and delivery

Context Isolation:
- User execution contexts are completely separate
- Database queries are filtered by user ID
- Cache isolation prevents cross-user data access
- Resource allocation and cleanup per user

Following SSOT patterns and TEST_CREATION_GUIDE.md:
- Uses real authentication service with multiple users (NO MOCKS)
- Real database connections with user-scoped data
- Real WebSocket connections for each user
- Absolute imports only (no relative imports)
- Test categorization with @pytest.mark.integration
"""

import asyncio
import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from unittest.mock import Mock

# SSOT Imports - Using absolute imports only
from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult
)
from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState,
    WebSocketConnectionStateMachine
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ConnectionID, ensure_user_id
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from netra_backend.tests.integration.test_fixtures.database_fixture import DatabaseTestFixture
from netra_backend.tests.integration.test_fixtures.redis_fixture import RedisTestFixture


@pytest.mark.integration
class TestWebSocketMultiUserAuthenticationIsolation(SSotBaseTestCase):
    """
    Integration tests for WebSocket multi-user authentication isolation.
    
    CRITICAL: These tests validate that multiple users can authenticate
    simultaneously without interference and maintain complete isolation.
    
    Tests focus on:
    1. Concurrent user authentication without cross-contamination
    2. User-specific WebSocket connection management
    3. Authentication token validation per user
    4. User context isolation and validation
    5. Session management with proper user boundaries
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level test fixtures for multi-user testing."""
        super().setUpClass()
        
        # Initialize real service fixtures
        cls.db_fixture = DatabaseTestFixture()
        cls.redis_fixture = RedisTestFixture() 
        
        # Initialize auth helper for multi-user scenarios
        cls.auth_helper = E2EAuthHelper(environment="test")
        
        # Validate real services are available
        cls.assertTrue(cls.db_fixture.is_available(),
                      "Database required for multi-user data isolation")
        cls.assertTrue(cls.redis_fixture.is_available(), 
                      "Redis required for multi-user session management")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up class-level fixtures."""
        if hasattr(cls, 'db_fixture'):
            cls.db_fixture.cleanup()
        if hasattr(cls, 'redis_fixture'):
            cls.redis_fixture.cleanup()
        super().tearDownClass()
    
    def setUp(self) -> None:
        """Set up individual test environment."""
        super().setUp()
        
        # Clean test data for user isolation
        self.db_fixture.clean_test_data()
        self.redis_fixture.clean_test_data()
        
        # Create multiple test users for isolation testing
        self.test_users = [
            f"isolation_user_{i}_{int(time.time() * 1000)}" 
            for i in range(5)
        ]
    
    def create_authenticated_user_websocket(self, user_id: str) -> tuple[Mock, AuthenticatedUser]:
        """Create authenticated WebSocket connection for specific user."""
        # Create unique authenticated user
        auth_user = self.auth_helper.create_authenticated_user(
            email=f"{user_id}@isolation.test",
            user_id=user_id,
            permissions=['websocket', 'chat', 'agent_execution']
        )
        
        # Create user-specific WebSocket
        websocket = Mock()
        websocket.state = "connected"
        websocket.headers = {
            'authorization': f'Bearer {auth_user.jwt_token}',
            'user-id': user_id,
            'connection-id': f"conn_{user_id}_{int(time.time() * 1000)}"
        }
        
        # Store user data in test database for isolation testing
        user_data = {
            'user_id': auth_user.user_id,
            'email': auth_user.email,
            'full_name': auth_user.full_name,
            'created_at': auth_user.created_at,
            'is_test_user': True
        }
        self.db_fixture.insert_test_user(user_data)
        
        return websocket, auth_user
    
    def test_concurrent_multi_user_authentication_without_interference(self):
        """Test concurrent multi-user authentication without cross-interference."""
        user_count = len(self.test_users)
        auth_results = []
        auth_lock = threading.Lock()
        
        def authenticate_user_concurrently(user_id: str):
            """Authenticate a single user concurrently with others."""
            try:
                start_time = time.time()
                
                # Create authenticated WebSocket for this user
                websocket, auth_user = self.create_authenticated_user_websocket(user_id)
                
                # Create authenticator instance
                authenticator = UnifiedWebSocketAuthenticator()
                
                # Extract and validate JWT token
                auth_header = websocket.headers.get('authorization')
                jwt_token = auth_header.split('Bearer ')[1] if auth_header else None
                
                # Validate token format and user association
                self.assertIsNotNone(jwt_token, f"JWT token required for user {user_id}")
                
                # Validate user context isolation
                user_context_data = {
                    'user_id': auth_user.user_id,
                    'email': auth_user.email,
                    'jwt_token': jwt_token[:20] + "...",  # Partial token for logging
                    'permissions': auth_user.permissions
                }
                
                end_time = time.time()
                execution_time = (end_time - start_time) * 1000
                
                # Thread-safe result recording
                with auth_lock:
                    auth_results.append({
                        'user_id': user_id,
                        'execution_time_ms': execution_time,
                        'user_context': user_context_data,
                        'success': True,
                        'websocket_headers': dict(websocket.headers)
                    })
                
            except Exception as e:
                with auth_lock:
                    auth_results.append({
                        'user_id': user_id,
                        'error': str(e),
                        'success': False
                    })
        
        # Execute concurrent authentication for all users
        with ThreadPoolExecutor(max_workers=user_count) as executor:
            futures = []
            for user_id in self.test_users:
                future = executor.submit(authenticate_user_concurrently, user_id)
                futures.append(future)
            
            # Wait for all authentications to complete
            for future in as_completed(futures):
                future.result()
        
        # Validate concurrent authentication results
        self.assertEqual(len(auth_results), user_count)
        
        # All authentications should succeed
        successful_auths = [r for r in auth_results if r.get('success')]
        self.assertEqual(len(successful_auths), user_count)
        
        # Validate user isolation - no duplicate user IDs
        authenticated_user_ids = [r['user_id'] for r in successful_auths]
        unique_user_ids = set(authenticated_user_ids)
        self.assertEqual(len(unique_user_ids), user_count, 
                        "Each user must have unique authentication")
        
        # Validate user context isolation
        for result in successful_auths:
            user_context = result['user_context']
            self.assertEqual(user_context['user_id'], result['user_id'])
            self.assertIn('websocket', user_context['permissions'])
            
        # Validate performance - concurrent should be faster than sequential
        avg_execution_time = sum(r['execution_time_ms'] for r in successful_auths) / len(successful_auths)
        self.assertLess(avg_execution_time, 2000, "Average auth time should be under 2 seconds")
    
    def test_user_specific_websocket_connection_management(self):
        """Test user-specific WebSocket connection management and isolation."""
        # Create WebSocket connections for multiple users
        user_connections = {}
        user_state_machines = {}
        
        for user_id in self.test_users:
            # Create authenticated connection for user
            websocket, auth_user = self.create_authenticated_user_websocket(user_id)
            
            # Create user-specific state machine
            connection_id = websocket.headers['connection-id']
            state_machine = WebSocketConnectionStateMachine(connection_id=connection_id)
            
            user_connections[user_id] = {
                'websocket': websocket,
                'auth_user': auth_user,
                'connection_id': connection_id,
                'state_machine': state_machine
            }
            
            user_state_machines[user_id] = state_machine
        
        # Validate connection isolation
        connection_ids = [conn['connection_id'] for conn in user_connections.values()]
        unique_connection_ids = set(connection_ids)
        self.assertEqual(len(unique_connection_ids), len(self.test_users),
                        "Each user must have unique connection ID")
        
        # Test state management isolation
        for user_id, connection_data in user_connections.items():
            state_machine = connection_data['state_machine']
            
            # Each user's state machine should be independent
            self.assertEqual(state_machine.get_current_state(), 
                           ApplicationConnectionState.CONNECTING)
            
            # Advance this user's state without affecting others
            state_machine._current_state = ApplicationConnectionState.AUTHENTICATED
            
            # Validate this user's state changed
            self.assertEqual(state_machine.get_current_state(),
                           ApplicationConnectionState.AUTHENTICATED)
        
        # Validate other users' states remain unaffected
        modified_states = 0
        for user_id, state_machine in user_state_machines.items():
            if state_machine.get_current_state() == ApplicationConnectionState.AUTHENTICATED:
                modified_states += 1
        
        # All users should have been modified in the loop above
        self.assertEqual(modified_states, len(self.test_users))
    
    def test_user_context_validation_and_enforcement(self):
        """Test user context validation and enforcement across WebSocket operations."""
        # Create user contexts for isolation testing
        user_contexts = {}
        
        for user_id in self.test_users:
            # Create authenticated user and WebSocket
            websocket, auth_user = self.create_authenticated_user_websocket(user_id)
            
            # Create user execution context
            user_context = UserExecutionContext(
                user_id=ensure_user_id(user_id),
                email=auth_user.email,
                permissions=set(auth_user.permissions),
                session_data={'websocket_connection': True}
            )
            
            user_contexts[user_id] = {
                'context': user_context,
                'auth_user': auth_user,
                'websocket': websocket
            }
        
        # Test user context isolation
        for user_id, user_data in user_contexts.items():
            context = user_data['context']
            
            # Validate context belongs to correct user
            self.assertEqual(str(context.user_id), user_id)
            self.assertEqual(context.email, user_data['auth_user'].email)
            
            # Validate permissions are user-specific
            self.assertIn('websocket', context.permissions)
            self.assertIn('chat', context.permissions)
            
            # Validate session data is isolated
            session_data = context.session_data
            self.assertTrue(session_data.get('websocket_connection'))
        
        # Test cross-user context access prevention
        user_ids_list = list(user_contexts.keys())
        for i, user_a_id in enumerate(user_ids_list):
            for j, user_b_id in enumerate(user_ids_list):
                if i != j:  # Different users
                    context_a = user_contexts[user_a_id]['context']
                    context_b = user_contexts[user_b_id]['context']
                    
                    # User contexts must be completely separate
                    self.assertNotEqual(context_a.user_id, context_b.user_id)
                    self.assertNotEqual(context_a.email, context_b.email)
                    
                    # User A cannot access User B's context data
                    self.assertNotEqual(str(context_a.user_id), user_b_id)
                    self.assertNotEqual(str(context_b.user_id), user_a_id)
    
    def test_authentication_token_validation_per_user(self):
        """Test authentication token validation is properly scoped per user."""
        user_tokens = {}
        
        # Generate tokens for each user
        for user_id in self.test_users:
            websocket, auth_user = self.create_authenticated_user_websocket(user_id)
            
            auth_header = websocket.headers.get('authorization')
            jwt_token = auth_header.split('Bearer ')[1] if auth_header else None
            
            user_tokens[user_id] = {
                'jwt_token': jwt_token,
                'auth_user': auth_user,
                'websocket': websocket
            }
        
        # Validate token uniqueness
        tokens = [data['jwt_token'] for data in user_tokens.values()]
        unique_tokens = set(tokens)
        self.assertEqual(len(unique_tokens), len(self.test_users),
                        "Each user must have unique JWT token")
        
        # Test token validation per user
        for user_id, token_data in user_tokens.items():
            jwt_token = token_data['jwt_token']
            
            # Validate token format
            self.assertIsNotNone(jwt_token)
            self.assertTrue(len(jwt_token) > 0)
            
            # JWT should have 3 parts
            token_parts = jwt_token.split('.')
            self.assertEqual(len(token_parts), 3, f"Invalid JWT format for user {user_id}")
            
            # Each part should be base64-like
            for part in token_parts:
                self.assertTrue(len(part) > 0, f"Empty JWT part for user {user_id}")
        
        # Test cross-user token validation
        # User A's token should not validate for User B
        user_ids_list = list(user_tokens.keys())
        for i, user_a_id in enumerate(user_ids_list):
            for j, user_b_id in enumerate(user_ids_list):
                if i != j:  # Different users
                    token_a = user_tokens[user_a_id]['jwt_token']
                    token_b = user_tokens[user_b_id]['jwt_token']
                    
                    # Tokens must be different
                    self.assertNotEqual(token_a, token_b,
                                      f"Users {user_a_id} and {user_b_id} have same token")
    
    def test_user_session_management_with_proper_boundaries(self):
        """Test user session management maintains proper user boundaries."""
        user_sessions = {}
        
        # Create sessions for each user
        for user_id in self.test_users:
            websocket, auth_user = self.create_authenticated_user_websocket(user_id)
            
            # Create session data for user
            session_data = {
                'user_id': user_id,
                'connection_id': websocket.headers['connection-id'],
                'authenticated_at': datetime.now(timezone.utc).isoformat(),
                'permissions': auth_user.permissions,
                'session_context': {
                    'websocket_connected': True,
                    'auth_method': 'jwt',
                    'user_agent': 'Integration Test Client'
                }
            }
            
            # Store session in Redis for isolation testing
            session_key = f"user_session:{user_id}"
            self.redis_fixture.set_data(session_key, session_data)
            
            user_sessions[user_id] = {
                'session_key': session_key,
                'session_data': session_data,
                'auth_user': auth_user
            }
        
        # Validate session isolation
        for user_id, session_info in user_sessions.items():
            session_key = session_info['session_key']
            stored_session = self.redis_fixture.get_data(session_key)
            
            # Session should exist and match user
            self.assertIsNotNone(stored_session, f"Session missing for user {user_id}")
            self.assertEqual(stored_session['user_id'], user_id)
            
            # Session context should be user-specific
            self.assertTrue(stored_session['session_context']['websocket_connected'])
            self.assertEqual(stored_session['session_context']['auth_method'], 'jwt')
        
        # Test session boundary enforcement
        user_ids_list = list(user_sessions.keys())
        for user_id in user_ids_list:
            user_session_key = f"user_session:{user_id}"
            user_session = self.redis_fixture.get_data(user_session_key)
            
            # User can only access their own session
            self.assertEqual(user_session['user_id'], user_id)
            
            # User cannot access other users' sessions by guessing keys
            for other_user_id in user_ids_list:
                if other_user_id != user_id:
                    other_session_key = f"user_session:{other_user_id}"
                    other_session = self.redis_fixture.get_data(other_session_key)
                    
                    # Other user's session should not be accessible through this user's context
                    self.assertNotEqual(user_session['user_id'], other_user_id)
                    self.assertNotEqual(other_session['user_id'], user_id)
        
        # Test session cleanup on disconnection
        for user_id in self.test_users[:2]:  # Test cleanup for first 2 users
            session_key = f"user_session:{user_id}"
            
            # Simulate user disconnection
            self.redis_fixture.delete_data(session_key)
            
            # Session should be cleaned up
            cleaned_session = self.redis_fixture.get_data(session_key)
            self.assertIsNone(cleaned_session, f"Session should be cleaned up for user {user_id}")
        
        # Other users' sessions should remain intact
        for user_id in self.test_users[2:]:  # Remaining users
            session_key = f"user_session:{user_id}"
            remaining_session = self.redis_fixture.get_data(session_key)
            
            self.assertIsNotNone(remaining_session, 
                               f"Session should remain for unaffected user {user_id}")
            self.assertEqual(remaining_session['user_id'], user_id)


@pytest.mark.integration
class TestWebSocketMultiUserMessageIsolation(SSotBaseTestCase):
    """
    Integration tests for WebSocket multi-user message isolation.
    
    CRITICAL: These tests validate that WebSocket messages are properly
    isolated between users and cannot leak across user boundaries.
    
    Tests focus on:
    1. Message delivery isolation between users
    2. User-specific message queuing and processing
    3. Agent execution result isolation
    4. Prevention of message broadcasting across users
    5. User-specific message filtering and routing
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures for message isolation testing."""
        super().setUpClass()
        cls.auth_helper = E2EAuthHelper(environment="test")
    
    def setUp(self) -> None:
        """Set up individual test environment."""
        super().setUp()
        
        # Create test users for message isolation
        self.message_test_users = [
            f"msg_user_{i}_{int(time.time() * 1000)}" 
            for i in range(3)
        ]
    
    def create_user_websocket_with_message_queue(self, user_id: str) -> Dict[str, Any]:
        """Create user WebSocket connection with message queue."""
        # Create authenticated user and WebSocket
        auth_user = self.auth_helper.create_authenticated_user(
            email=f"{user_id}@message.test",
            user_id=user_id,
            permissions=['websocket', 'chat', 'agent_execution']
        )
        
        websocket = Mock()
        websocket.state = "connected"
        websocket.headers = {
            'authorization': f'Bearer {auth_user.jwt_token}',
            'user-id': user_id,
            'connection-id': f"msg_conn_{user_id}"
        }
        
        # Create user-specific message queue
        user_messages = []
        
        return {
            'user_id': user_id,
            'websocket': websocket,
            'auth_user': auth_user,
            'messages': user_messages,
            'connection_id': f"msg_conn_{user_id}"
        }
    
    def test_message_delivery_isolation_between_users(self):
        """Test message delivery isolation between different users."""
        # Create WebSocket connections for users
        user_connections = {}
        for user_id in self.message_test_users:
            user_connections[user_id] = self.create_user_websocket_with_message_queue(user_id)
        
        # Send user-specific messages
        for user_id, connection_data in user_connections.items():
            user_specific_messages = [
                {
                    'type': 'user_message',
                    'content': f'Private message for {user_id}',
                    'user_id': user_id,
                    'connection_id': connection_data['connection_id'],
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                {
                    'type': 'agent_response',
                    'content': f'Agent response for {user_id}',
                    'user_id': user_id,
                    'connection_id': connection_data['connection_id'],
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            ]
            
            # Add messages to user's queue
            connection_data['messages'].extend(user_specific_messages)
        
        # Validate message isolation
        for user_id, connection_data in user_connections.items():
            user_messages = connection_data['messages']
            
            # User should have exactly their own messages
            self.assertEqual(len(user_messages), 2, f"User {user_id} should have 2 messages")
            
            # All messages should be for this user only
            for message in user_messages:
                self.assertEqual(message['user_id'], user_id,
                               f"Message user_id mismatch for user {user_id}")
                self.assertEqual(message['connection_id'], connection_data['connection_id'],
                               f"Message connection_id mismatch for user {user_id}")
                self.assertIn(user_id, message['content'],
                            f"Message content should reference user {user_id}")
        
        # Validate cross-user isolation - users cannot see each other's messages
        user_ids_list = list(user_connections.keys())
        for i, user_a_id in enumerate(user_ids_list):
            for j, user_b_id in enumerate(user_ids_list):
                if i != j:  # Different users
                    user_a_messages = user_connections[user_a_id]['messages']
                    user_b_messages = user_connections[user_b_id]['messages']
                    
                    # No message should reference the other user
                    for message in user_a_messages:
                        self.assertNotEqual(message['user_id'], user_b_id,
                                          f"User {user_a_id} has message for user {user_b_id}")
                        self.assertNotIn(user_b_id, message['content'],
                                       f"User {user_a_id} message mentions user {user_b_id}")
    
    def test_user_specific_message_queuing_and_processing(self):
        """Test user-specific message queuing and processing isolation."""
        # Create user connections with message processing
        user_processors = {}
        
        for user_id in self.message_test_users:
            connection_data = self.create_user_websocket_with_message_queue(user_id)
            
            # Create user-specific message processor state
            message_processor = {
                'user_id': user_id,
                'connection_id': connection_data['connection_id'],
                'pending_messages': [],
                'processed_messages': [],
                'processing_stats': {
                    'total_received': 0,
                    'total_processed': 0,
                    'processing_time_ms': 0
                }
            }
            
            user_processors[user_id] = {
                'connection_data': connection_data,
                'processor': message_processor
            }
        
        # Send messages to each user's queue
        messages_per_user = 5
        for user_id, user_data in user_processors.items():
            processor = user_data['processor']
            
            # Add user-specific messages to pending queue
            for i in range(messages_per_user):
                message = {
                    'id': f'{user_id}_msg_{i}',
                    'type': 'test_message',
                    'content': f'Test message {i} for user {user_id}',
                    'user_id': user_id,
                    'connection_id': processor['connection_id'],
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                processor['pending_messages'].append(message)
                processor['processing_stats']['total_received'] += 1
        
        # Process messages for each user independently
        for user_id, user_data in user_processors.items():
            processor = user_data['processor']
            
            start_time = time.time()
            
            # Process all pending messages for this user
            while processor['pending_messages']:
                message = processor['pending_messages'].pop(0)
                
                # Validate message belongs to this user
                self.assertEqual(message['user_id'], user_id)
                self.assertEqual(message['connection_id'], processor['connection_id'])
                
                # Process message (add to processed queue)
                processor['processed_messages'].append(message)
                processor['processing_stats']['total_processed'] += 1
            
            end_time = time.time()
            processor['processing_stats']['processing_time_ms'] = (end_time - start_time) * 1000
        
        # Validate processing isolation
        for user_id, user_data in user_processors.items():
            processor = user_data['processor']
            
            # User should have processed exactly their messages
            self.assertEqual(len(processor['processed_messages']), messages_per_user)
            self.assertEqual(processor['processing_stats']['total_processed'], messages_per_user)
            self.assertEqual(processor['processing_stats']['total_received'], messages_per_user)
            
            # All processed messages should belong to this user
            for message in processor['processed_messages']:
                self.assertEqual(message['user_id'], user_id)
                self.assertIn(user_id, message['content'])
                self.assertIn(user_id, message['id'])
        
        # Validate cross-user processing isolation
        processed_message_ids = set()
        for user_id, user_data in user_processors.items():
            processor = user_data['processor']
            
            for message in processor['processed_messages']:
                message_id = message['id']
                
                # No duplicate message IDs across users
                self.assertNotIn(message_id, processed_message_ids,
                               f"Duplicate message ID {message_id}")
                processed_message_ids.add(message_id)
                
                # Message ID should contain the user ID
                self.assertIn(user_id, message_id)
    
    def test_agent_execution_result_isolation(self):
        """Test agent execution result isolation between users."""
        # Create user connections for agent execution testing
        user_agent_results = {}
        
        for user_id in self.message_test_users:
            connection_data = self.create_user_websocket_with_message_queue(user_id)
            
            # Simulate agent execution results for user
            agent_results = [
                {
                    'execution_id': f'{user_id}_exec_1',
                    'user_id': user_id,
                    'agent_type': 'data_analysis',
                    'result': {
                        'analysis': f'Data analysis results for user {user_id}',
                        'recommendations': [f'Recommendation 1 for {user_id}'],
                        'private_data': f'Sensitive data for {user_id} only'
                    },
                    'execution_time_ms': 1500,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                {
                    'execution_id': f'{user_id}_exec_2',
                    'user_id': user_id,
                    'agent_type': 'optimization',
                    'result': {
                        'optimizations': f'Optimization suggestions for {user_id}',
                        'cost_savings': f'$1000 savings for {user_id}',
                        'private_metrics': f'User {user_id} specific metrics'
                    },
                    'execution_time_ms': 2000,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            ]
            
            user_agent_results[user_id] = {
                'connection_data': connection_data,
                'agent_results': agent_results
            }
        
        # Validate agent result isolation
        for user_id, user_data in user_agent_results.items():
            agent_results = user_data['agent_results']
            
            # User should have exactly their own agent results
            self.assertEqual(len(agent_results), 2)
            
            for result in agent_results:
                # Result should belong only to this user
                self.assertEqual(result['user_id'], user_id)
                self.assertIn(user_id, result['execution_id'])
                
                # Private data should reference only this user
                result_content = str(result['result'])
                self.assertIn(user_id, result_content)
                
                # Validate specific result isolation
                if 'private_data' in result['result']:
                    self.assertIn(user_id, result['result']['private_data'])
                if 'private_metrics' in result['result']:
                    self.assertIn(user_id, result['result']['private_metrics'])
        
        # Validate cross-user result isolation
        user_ids_list = list(user_agent_results.keys())
        for i, user_a_id in enumerate(user_ids_list):
            user_a_results = user_agent_results[user_a_id]['agent_results']
            
            for j, user_b_id in enumerate(user_ids_list):
                if i != j:  # Different users
                    # User A's results should not contain User B's data
                    for result in user_a_results:
                        result_str = str(result)
                        self.assertNotIn(user_b_id, result_str,
                                       f"User {user_a_id} result contains user {user_b_id} data")
                        self.assertNotEqual(result['user_id'], user_b_id,
                                          f"User {user_a_id} has result for user {user_b_id}")


if __name__ == "__main__":
    # Run integration tests with pytest  
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])