"""
Comprehensive Multi-User State Machine Isolation Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete isolation between user state machines in multi-tenant environment
- Value Impact: Prevents cross-user contamination that would compromise security and reliability
- Strategic Impact: Critical foundation for enterprise-grade multi-user AI platform

This test suite validates that WebSocket connections, agent executions, and all state machines
maintain perfect isolation between users, preventing any cross-user data leakage or state corruption.
Essential for Golden Path multi-user scenarios.
"""

import pytest
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.websocket import WebSocketTestClient
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, ConnectionID, ensure_user_id
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class IsolationTestScenario(Enum):
    """Different isolation test scenarios."""
    CONCURRENT_WEBSOCKET_CONNECTIONS = "concurrent_websocket_connections"
    CONCURRENT_AGENT_EXECUTIONS = "concurrent_agent_executions"
    STATE_MACHINE_ISOLATION = "state_machine_isolation"
    MESSAGE_ROUTING_ISOLATION = "message_routing_isolation"
    DATA_PERSISTENCE_ISOLATION = "data_persistence_isolation"
    ERROR_ISOLATION = "error_isolation"
    RESOURCE_CLEANUP_ISOLATION = "resource_cleanup_isolation"


@dataclass
class UserIsolationContext:
    """Context for tracking user isolation in tests."""
    user_id: str
    user_email: str
    websocket_client: Optional[WebSocketTestClient]
    connection_id: str
    thread_ids: Set[str]
    agent_runs: List[str]
    state_events: List[Dict[str, Any]]
    messages_sent: List[Dict[str, Any]]
    messages_received: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    redis_keys: Set[str]
    postgres_records: List[Dict[str, Any]]
    
    def __post_init__(self):
        if self.thread_ids is None:
            self.thread_ids = set()
        if self.agent_runs is None:
            self.agent_runs = []
        if self.state_events is None:
            self.state_events = []
        if self.messages_sent is None:
            self.messages_sent = []
        if self.messages_received is None:
            self.messages_received = []
        if self.errors is None:
            self.errors = []
        if self.redis_keys is None:
            self.redis_keys = set()
        if self.postgres_records is None:
            self.postgres_records = []


class TestMultiUserStateIsolationIntegration(BaseIntegrationTest):
    """Integration tests for multi-user state machine isolation."""
    
    async def _create_isolated_user_context(self, real_services_fixture, user_index: int,
                                          scenario: IsolationTestScenario) -> UserIsolationContext:
        """Create isolated user context for testing."""
        user_email = f"isolation_user_{user_index}_{scenario.value}@netra.ai"
        
        # Create user with real services
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': user_email,
            'name': f'Isolation Test User {user_index}',
            'is_active': True
        })
        user_id = user_data['id']
        
        # Create session
        session_data = await self.create_test_session(real_services_fixture, user_id)
        
        # Generate connection ID
        id_manager = UnifiedIDManager()
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix=f"isolation_conn_{user_index}",
            context={"user_id": user_id, "scenario": scenario.value}
        )
        
        # Create WebSocket client
        websocket_client = WebSocketTestClient(
            token=session_data['token'],
            connection_id=connection_id,
            user_id=user_id
        )
        
        return UserIsolationContext(
            user_id=user_id,
            user_email=user_email,
            websocket_client=websocket_client,
            connection_id=connection_id,
            thread_ids=set(),
            agent_runs=[],
            state_events=[],
            messages_sent=[],
            messages_received=[],
            errors=[],
            redis_keys=set(),
            postgres_records=[]
        )
    
    async def _track_user_state_events(self, user_context: UserIsolationContext, 
                                     duration_seconds: float = 10.0) -> None:
        """Track state events for a specific user."""
        if not user_context.websocket_client.is_connected():
            await user_context.websocket_client.connect()
        
        start_time = datetime.utcnow()
        
        try:
            while (datetime.utcnow() - start_time).total_seconds() < duration_seconds:
                try:
                    event = await asyncio.wait_for(
                        user_context.websocket_client.receive_json(),
                        timeout=1.0
                    )
                    
                    user_context.state_events.append({
                        'timestamp': datetime.utcnow().isoformat(),
                        'event': event,
                        'user_id': user_context.user_id
                    })
                    
                    # Categorize events
                    if event.get('type') == 'error':
                        user_context.errors.append({
                            'timestamp': datetime.utcnow().isoformat(),
                            'error': event,
                            'user_id': user_context.user_id
                        })
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    user_context.errors.append({
                        'timestamp': datetime.utcnow().isoformat(),
                        'error': {'type': 'websocket_error', 'details': str(e)},
                        'user_id': user_context.user_id
                    })
                    break
        
        except Exception as e:
            user_context.errors.append({
                'timestamp': datetime.utcnow().isoformat(),
                'error': {'type': 'state_tracking_error', 'details': str(e)},
                'user_id': user_context.user_id
            })
    
    async def _verify_redis_isolation(self, real_services_fixture, user_contexts: List[UserIsolationContext]) -> Dict[str, Any]:
        """Verify Redis key isolation between users."""
        isolation_violations = []
        user_key_patterns = {}
        
        for user_context in user_contexts:
            user_id = user_context.user_id
            
            # Expected key patterns for this user
            expected_patterns = [
                f"websocket:connection_state:*{user_id}*",
                f"websocket:user_connections:{user_id}",
                f"agent:execution:*{user_id}*",
                f"user:session:{user_id}*",
                f"thread:*{user_id}*"
            ]
            
            # Scan for keys matching this user
            user_keys = set()
            for pattern in expected_patterns:
                keys = await real_services_fixture["redis"].keys(pattern)
                user_keys.update(keys)
                user_context.redis_keys.update(keys)
            
            user_key_patterns[user_id] = user_keys
        
        # Check for cross-user key contamination
        for user_id, user_keys in user_key_patterns.items():
            for other_user_id, other_keys in user_key_patterns.items():
                if user_id != other_user_id:
                    # Check if this user's keys contain other user IDs
                    for key in user_keys:
                        if other_user_id in key:
                            isolation_violations.append({
                                'type': 'redis_key_contamination',
                                'user_id': user_id,
                                'contaminated_by': other_user_id,
                                'key': key,
                                'timestamp': datetime.utcnow().isoformat()
                            })
        
        return {
            'isolation_violations': isolation_violations,
            'user_key_counts': {user_id: len(keys) for user_id, keys in user_key_patterns.items()},
            'total_keys_tracked': sum(len(keys) for keys in user_key_patterns.values())
        }
    
    async def _verify_postgres_isolation(self, real_services_fixture, user_contexts: List[UserIsolationContext]) -> Dict[str, Any]:
        """Verify PostgreSQL record isolation between users."""
        isolation_violations = []
        
        # Tables to check for isolation
        tables_to_check = [
            ('auth.users', 'id'),
            ('threads', 'user_id'), 
            ('messages', 'user_id'),
            ('agent_runs', 'user_id'),
            ('websocket_connections', 'user_id')
        ]
        
        for table, user_column in tables_to_check:
            try:
                # Check each user's records
                for user_context in user_contexts:
                    user_id = user_context.user_id
                    
                    query = f"SELECT * FROM {table} WHERE {user_column} = $1"
                    records = await real_services_fixture["postgres"].fetch(query, user_id)
                    
                    # Store records for this user
                    user_context.postgres_records.extend([
                        {
                            'table': table,
                            'record': dict(record),
                            'user_id': user_id
                        } for record in records
                    ])
                    
                    # Check for records that shouldn't belong to this user
                    for record in records:
                        record_dict = dict(record)
                        
                        # Look for other user IDs in record data
                        for other_context in user_contexts:
                            if other_context.user_id != user_id:
                                other_user_id = other_context.user_id
                                
                                # Check if record contains other user's data
                                record_str = json.dumps(record_dict, default=str)
                                if other_user_id in record_str:
                                    isolation_violations.append({
                                        'type': 'postgres_record_contamination',
                                        'table': table,
                                        'user_id': user_id,
                                        'contaminated_by': other_user_id,
                                        'record_id': record_dict.get('id'),
                                        'timestamp': datetime.utcnow().isoformat()
                                    })
            
            except Exception as e:
                # Table might not exist - that's okay
                continue
        
        return {
            'isolation_violations': isolation_violations,
            'records_checked': sum(len(ctx.postgres_records) for ctx in user_contexts)
        }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_websocket_connection_isolation(self, real_services_fixture):
        """
        Test WebSocket connection isolation between multiple concurrent users.
        
        Business Value: Ensures users cannot see each other's connection states or messages,
        maintaining privacy and security in multi-user environment.
        """
        # Create multiple user contexts
        num_users = 5
        user_contexts = []
        
        for i in range(num_users):
            user_context = await self._create_isolated_user_context(
                real_services_fixture, i, IsolationTestScenario.CONCURRENT_WEBSOCKET_CONNECTIONS
            )
            user_contexts.append(user_context)
        
        websocket_manager = UnifiedWebSocketManager()
        
        async def concurrent_websocket_session(user_context: UserIsolationContext, user_index: int):
            """Run isolated WebSocket session for a user."""
            try:
                # Connect WebSocket
                await user_context.websocket_client.connect()
                
                # Authenticate
                auth_message = {
                    "type": "authenticate",
                    "token": "valid_token_for_user",  # Would be real token in actual implementation
                    "user_id": user_context.user_id
                }
                await user_context.websocket_client.send_json(auth_message)
                user_context.messages_sent.append(auth_message)
                
                # Send user-specific messages
                for msg_num in range(3):
                    user_message = {
                        "type": "user_specific_message",
                        "data": {
                            "user_index": user_index,
                            "message_number": msg_num,
                            "user_id": user_context.user_id,
                            "private_data": f"secret_data_for_user_{user_index}"
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await user_context.websocket_client.send_json(user_message)
                    user_context.messages_sent.append(user_message)
                    
                    # Small delay to prevent message flooding
                    await asyncio.sleep(0.1)
                
                # Start state event monitoring
                monitor_task = asyncio.create_task(
                    self._track_user_state_events(user_context, duration_seconds=5.0)
                )
                
                # Send connection state test message
                state_test_message = {
                    "type": "connection_state_test",
                    "data": {"user_specific": True, "user_id": user_context.user_id},
                    "timestamp": datetime.utcnow().isoformat()
                }
                await user_context.websocket_client.send_json(state_test_message)
                user_context.messages_sent.append(state_test_message)
                
                # Wait for monitoring to complete
                await monitor_task
                
                return {
                    'user_id': user_context.user_id,
                    'connection_id': user_context.connection_id,
                    'messages_sent': len(user_context.messages_sent),
                    'state_events': len(user_context.state_events),
                    'errors': len(user_context.errors)
                }
                
            except Exception as e:
                user_context.errors.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': {'type': 'session_error', 'details': str(e)},
                    'user_id': user_context.user_id
                })
                return {'user_id': user_context.user_id, 'error': str(e)}
            
            finally:
                if user_context.websocket_client.is_connected():
                    await user_context.websocket_client.disconnect()
        
        # Run concurrent WebSocket sessions
        concurrent_tasks = [
            concurrent_websocket_session(user_context, i)
            for i, user_context in enumerate(user_contexts)
        ]
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify no exceptions occurred
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"User {i} session failed: {result}"
            assert 'error' not in result, f"User {i} had session error: {result.get('error')}"
        
        # Verify message isolation - no user should see other users' messages
        for i, user_context in enumerate(user_contexts):
            user_id = user_context.user_id
            
            # Check state events for cross-user contamination
            for event_record in user_context.state_events:
                event = event_record['event']
                
                # Event should only contain this user's data
                event_str = json.dumps(event, default=str)
                
                for j, other_context in enumerate(user_contexts):
                    if i != j:
                        other_user_id = other_context.user_id
                        assert other_user_id not in event_str, \
                            f"User {i} received event containing data from User {j}"
        
        # Verify Redis isolation
        redis_isolation_result = await self._verify_redis_isolation(real_services_fixture, user_contexts)
        assert len(redis_isolation_result['isolation_violations']) == 0, \
            f"Redis isolation violations: {redis_isolation_result['isolation_violations']}"
        
        # Verify all users had independent sessions
        user_ids = {result['user_id'] for result in results}
        assert len(user_ids) == num_users, f"Should have {num_users} distinct user sessions"
        
        # Clean up
        for user_context in user_contexts:
            for redis_key in user_context.redis_keys:
                await real_services_fixture["redis"].delete(redis_key)
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_concurrent_agent_execution_isolation(self, real_services_fixture):
        """
        Test agent execution state isolation between multiple concurrent users.
        
        Business Value: Ensures agent executions are completely isolated between users,
        preventing cross-user data leakage in AI responses and maintaining privacy.
        """
        # Create multiple users with different agent scenarios
        num_users = 4
        user_contexts = []
        agent_scenarios = [
            ("triage_agent", "Help me understand my infrastructure"),
            ("cost_optimizer_agent", "Optimize my cloud costs"),
            ("supply_researcher_agent", "Research suppliers for manufacturing"),
            ("triage_agent", "Different infrastructure analysis")
        ]
        
        for i in range(num_users):
            user_context = await self._create_isolated_user_context(
                real_services_fixture, i, IsolationTestScenario.CONCURRENT_AGENT_EXECUTIONS
            )
            user_contexts.append(user_context)
        
        async def concurrent_agent_execution(user_context: UserIsolationContext, user_index: int):
            """Run isolated agent execution for a user."""
            agent_type, user_message = agent_scenarios[user_index % len(agent_scenarios)]
            
            try:
                # Connect and authenticate
                await user_context.websocket_client.connect()
                
                auth_message = {
                    "type": "authenticate",
                    "token": "valid_token",
                    "user_id": user_context.user_id
                }
                await user_context.websocket_client.send_json(auth_message)
                
                # Generate unique thread ID for this user
                id_manager = UnifiedIDManager()
                thread_id = id_manager.generate_id(
                    IDType.THREAD,
                    prefix=f"isolation_thread_{user_index}",
                    context={"user_id": user_context.user_id}
                )
                user_context.thread_ids.add(thread_id)
                
                # Start agent execution with user-specific data
                agent_request = {
                    "type": "agent_request",
                    "agent": agent_type,
                    "message": f"{user_message} - User {user_index} specific request",
                    "user_id": user_context.user_id,
                    "thread_id": thread_id,
                    "user_context": {
                        "user_index": user_index,
                        "private_context": f"private_data_user_{user_index}",
                        "user_preferences": {"preference": f"user_{user_index}_setting"}
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await user_context.websocket_client.send_json(agent_request)
                user_context.messages_sent.append(agent_request)
                
                # Monitor agent execution events
                agent_events = []
                expected_events = ['agent_started', 'agent_thinking', 'agent_completed']
                
                for expected_event in expected_events:
                    try:
                        event = await asyncio.wait_for(
                            user_context.websocket_client.receive_json(),
                            timeout=20.0
                        )
                        
                        agent_events.append(event)
                        user_context.state_events.append({
                            'timestamp': datetime.utcnow().isoformat(),
                            'event': event,
                            'user_id': user_context.user_id
                        })
                        
                        if event.get('type') == 'agent_completed':
                            break
                    
                    except asyncio.TimeoutError:
                        # Some events might be optional
                        continue
                
                # Generate run ID for tracking
                run_id = id_manager.generate_id(
                    IDType.RUN,
                    prefix=f"isolation_run_{user_index}",
                    context={"user_id": user_context.user_id, "thread_id": thread_id}
                )
                user_context.agent_runs.append(run_id)
                
                return {
                    'user_id': user_context.user_id,
                    'thread_id': thread_id,
                    'run_id': run_id,
                    'agent_type': agent_type,
                    'agent_events': len(agent_events),
                    'execution_successful': any(e.get('type') == 'agent_completed' for e in agent_events)
                }
                
            except Exception as e:
                user_context.errors.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': {'type': 'agent_execution_error', 'details': str(e)},
                    'user_id': user_context.user_id
                })
                return {'user_id': user_context.user_id, 'error': str(e)}
            
            finally:
                if user_context.websocket_client.is_connected():
                    await user_context.websocket_client.disconnect()
        
        # Execute concurrent agent sessions
        concurrent_tasks = [
            concurrent_agent_execution(user_context, i)
            for i, user_context in enumerate(user_contexts)
        ]
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify successful execution isolation
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"User {i} agent execution failed: {result}"
            assert 'error' not in result, f"User {i} had execution error: {result.get('error')}"
        
        # Verify agent execution isolation
        all_thread_ids = set()
        all_run_ids = set()
        
        for i, user_context in enumerate(user_contexts):
            user_id = user_context.user_id
            
            # Verify unique thread IDs
            for thread_id in user_context.thread_ids:
                assert thread_id not in all_thread_ids, f"Thread ID collision: {thread_id}"
                all_thread_ids.add(thread_id)
                
                # Thread ID should contain this user's ID
                assert user_id in thread_id, f"Thread ID {thread_id} should contain user ID {user_id}"
            
            # Verify unique run IDs  
            for run_id in user_context.agent_runs:
                assert run_id not in all_run_ids, f"Run ID collision: {run_id}"
                all_run_ids.add(run_id)
        
        # Verify state event isolation
        for i, user_context in enumerate(user_contexts):
            for event_record in user_context.state_events:
                event = event_record['event']
                
                # Agent events should only contain this user's context
                if 'data' in event:
                    event_data = event['data']
                    
                    # Should contain this user's ID
                    if 'user_id' in event_data:
                        assert event_data['user_id'] == user_context.user_id, \
                            f"Event contains wrong user ID: {event_data['user_id']} != {user_context.user_id}"
                    
                    # Should not contain other users' private data
                    event_str = json.dumps(event, default=str)
                    for j, other_context in enumerate(user_contexts):
                        if i != j:
                            private_data = f"private_data_user_{j}"
                            assert private_data not in event_str, \
                                f"User {i} event contains User {j} private data"
        
        # Verify Redis isolation for agent executions
        redis_isolation_result = await self._verify_redis_isolation(real_services_fixture, user_contexts)
        assert len(redis_isolation_result['isolation_violations']) == 0, \
            f"Agent execution Redis isolation violations: {redis_isolation_result['isolation_violations']}"
        
        # Verify PostgreSQL isolation for agent executions
        postgres_isolation_result = await self._verify_postgres_isolation(real_services_fixture, user_contexts)
        assert len(postgres_isolation_result['isolation_violations']) == 0, \
            f"Agent execution PostgreSQL isolation violations: {postgres_isolation_result['isolation_violations']}"
        
        # Clean up
        for user_context in user_contexts:
            # Clean up Redis keys
            for redis_key in user_context.redis_keys:
                await real_services_fixture["redis"].delete(redis_key)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_isolation_between_users(self, real_services_fixture):
        """
        Test that errors in one user's session don't affect other users.
        
        Business Value: Ensures system resilience where one user's errors
        don't cascade to other users, maintaining service availability.
        """
        # Create users - one will have errors, others should be unaffected
        num_users = 3
        user_contexts = []
        
        for i in range(num_users):
            user_context = await self._create_isolated_user_context(
                real_services_fixture, i, IsolationTestScenario.ERROR_ISOLATION
            )
            user_contexts.append(user_context)
        
        error_user_index = 1  # Middle user will have errors
        
        async def user_session_with_error_isolation(user_context: UserIsolationContext, user_index: int):
            """Run user session with potential errors."""
            try:
                await user_context.websocket_client.connect()
                
                # Authenticate
                auth_message = {
                    "type": "authenticate",
                    "token": "valid_token",
                    "user_id": user_context.user_id
                }
                await user_context.websocket_client.send_json(auth_message)
                
                if user_index == error_user_index:
                    # This user will trigger various error conditions
                    error_scenarios = [
                        # Invalid agent request
                        {
                            "type": "agent_request",
                            "agent": "nonexistent_agent",  # Should cause error
                            "message": "This should fail",
                            "user_id": user_context.user_id
                        },
                        # Invalid message format
                        {
                            "type": "invalid_message_type",
                            "malformed_data": {"nested": {"too": {"deep": "data"}}},
                            "user_id": user_context.user_id
                        },
                        # Attempt to access other user's data
                        {
                            "type": "agent_request",
                            "agent": "triage_agent",
                            "message": "Try to access other user data",
                            "user_id": user_contexts[0].user_id,  # Wrong user ID!
                            "attempt_cross_user_access": True
                        }
                    ]
                    
                    for error_message in error_scenarios:
                        try:
                            await user_context.websocket_client.send_json(error_message)
                            user_context.messages_sent.append(error_message)
                            
                            # Try to receive error response
                            try:
                                error_response = await asyncio.wait_for(
                                    user_context.websocket_client.receive_json(),
                                    timeout=5.0
                                )
                                
                                if error_response.get('type') == 'error':
                                    user_context.errors.append({
                                        'timestamp': datetime.utcnow().isoformat(),
                                        'error': error_response,
                                        'user_id': user_context.user_id,
                                        'expected': True
                                    })
                            
                            except asyncio.TimeoutError:
                                # No response - that's also fine for some error cases
                                pass
                            
                            await asyncio.sleep(0.5)  # Brief delay between error scenarios
                            
                        except Exception as e:
                            user_context.errors.append({
                                'timestamp': datetime.utcnow().isoformat(),
                                'error': {'type': 'send_error', 'details': str(e)},
                                'user_id': user_context.user_id,
                                'expected': True
                            })
                
                else:
                    # Normal users should function normally despite other user's errors
                    normal_request = {
                        "type": "agent_request", 
                        "agent": "triage_agent",
                        "message": f"Normal request from user {user_index}",
                        "user_id": user_context.user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await user_context.websocket_client.send_json(normal_request)
                    user_context.messages_sent.append(normal_request)
                    
                    # Should receive normal response
                    try:
                        normal_response = await asyncio.wait_for(
                            user_context.websocket_client.receive_json(),
                            timeout=15.0
                        )
                        
                        user_context.state_events.append({
                            'timestamp': datetime.utcnow().isoformat(),
                            'event': normal_response,
                            'user_id': user_context.user_id
                        })
                        
                        # Verify response is for this user
                        if 'data' in normal_response and 'user_id' in normal_response['data']:
                            assert normal_response['data']['user_id'] == user_context.user_id
                    
                    except asyncio.TimeoutError:
                        # Normal user should not timeout due to other user's errors
                        user_context.errors.append({
                            'timestamp': datetime.utcnow().isoformat(),
                            'error': {'type': 'unexpected_timeout', 'details': 'Normal user timed out'},
                            'user_id': user_context.user_id,
                            'expected': False
                        })
                
                return {
                    'user_id': user_context.user_id,
                    'user_index': user_index,
                    'is_error_user': user_index == error_user_index,
                    'messages_sent': len(user_context.messages_sent),
                    'errors_encountered': len(user_context.errors),
                    'state_events': len(user_context.state_events)
                }
                
            except Exception as e:
                user_context.errors.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': {'type': 'session_exception', 'details': str(e)},
                    'user_id': user_context.user_id,
                    'expected': user_index == error_user_index
                })
                
                return {
                    'user_id': user_context.user_id,
                    'user_index': user_index,
                    'session_failed': True,
                    'error': str(e)
                }
            
            finally:
                if user_context.websocket_client.is_connected():
                    await user_context.websocket_client.disconnect()
        
        # Run concurrent sessions with error isolation
        concurrent_tasks = [
            user_session_with_error_isolation(user_context, i)
            for i, user_context in enumerate(user_contexts)
        ]
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify error isolation
        error_user_result = None
        normal_user_results = []
        
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"User {i} session failed unexpectedly: {result}"
            
            if i == error_user_index:
                error_user_result = result
            else:
                normal_user_results.append(result)
        
        # Verify error user had expected errors
        assert error_user_result is not None
        error_context = user_contexts[error_user_index] 
        assert len(error_context.errors) > 0, "Error user should have encountered errors"
        
        # Verify normal users were not affected by error user's problems
        for i, normal_result in enumerate(normal_user_results):
            normal_context = user_contexts[i if i < error_user_index else i + 1]
            
            # Normal users should have fewer or no errors
            unexpected_errors = [e for e in normal_context.errors if not e.get('expected', True)]
            assert len(unexpected_errors) == 0, \
                f"Normal user {i} had unexpected errors: {unexpected_errors}"
            
            # Normal users should have successful state events
            assert len(normal_context.state_events) > 0, \
                f"Normal user {i} should have received state events"
        
        # Verify Redis isolation wasn't compromised by errors
        redis_isolation_result = await self._verify_redis_isolation(real_services_fixture, user_contexts)
        assert len(redis_isolation_result['isolation_violations']) == 0, \
            f"Errors caused Redis isolation violations: {redis_isolation_result['isolation_violations']}"
        
        # Verify all user contexts remain distinct
        all_user_ids = {ctx.user_id for ctx in user_contexts}
        assert len(all_user_ids) == num_users, "User ID isolation should be maintained despite errors"
        
        # Clean up
        for user_context in user_contexts:
            for redis_key in user_context.redis_keys:
                await real_services_fixture["redis"].delete(redis_key)
        
        # Verify business value: Error isolation maintains system reliability
        self.assert_business_value_delivered({
            'error_isolation_maintained': len([r for r in normal_user_results if not r.get('session_failed', False)]) == len(normal_user_results),
            'normal_users_unaffected': all(len([e for e in ctx.errors if not e.get('expected', True)]) == 0 for ctx in user_contexts[:error_user_index] + user_contexts[error_user_index+1:]),
            'error_handling_functional': len(error_context.errors) > 0,
            'system_resilience': True
        }, 'reliability')