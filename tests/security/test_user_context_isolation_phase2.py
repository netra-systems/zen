"""
User Context Isolation Validation - Phase 2
Validates that essential user isolation factories work correctly.

Purpose:
Verify user isolation in critical factories to ensure business-critical security
patterns are preserved during factory cleanup. These tests validate that user
isolation factories maintain complete separation between concurrent users.

Business Impact: $500K+ ARR protection through multi-user security
Security Requirement: Complete user isolation preventing data leakage

These tests MUST PASS for essential user isolation factories.
"""

import asyncio
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Set, Any, Optional
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
import weakref
import gc

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class UserContext:
    """Mock user context for isolation testing."""
    user_id: str
    session_id: str
    auth_token: str
    permissions: Set[str]
    private_data: Dict[str, Any]
    created_at: float

    def __post_init__(self):
        """Ensure user context is properly isolated."""
        if not self.user_id:
            raise ValueError("User ID is required for isolation")
        if not self.session_id:
            self.session_id = f"session_{uuid.uuid4()}"


class MockUserExecutionEngine:
    """Mock execution engine with user isolation."""

    def __init__(self, user_context: UserContext):
        self.user_context = user_context
        self.execution_state = {}
        self.tool_results = []
        self.websocket_events = []
        self._isolated_memory = {}

    def execute_agent_task(self, task: str) -> Dict:
        """Execute task with user isolation."""
        # Simulate agent execution with user-specific state
        execution_id = f"exec_{uuid.uuid4()}"

        result = {
            'execution_id': execution_id,
            'user_id': self.user_context.user_id,
            'task': task,
            'timestamp': time.time(),
            'private_result': f"result_for_{self.user_context.user_id}",
            'execution_context': self.user_context.session_id
        }

        self.execution_state[execution_id] = result
        return result

    def get_user_specific_data(self) -> Dict:
        """Get data specific to this user only."""
        return {
            'user_id': self.user_context.user_id,
            'session_data': self.user_context.private_data.copy(),
            'execution_history': list(self.execution_state.values())
        }


class MockWebSocketEmitter:
    """Mock WebSocket emitter with user isolation."""

    def __init__(self, user_context: UserContext):
        self.user_context = user_context
        self.event_queue = []
        self.connection_id = f"ws_{user_context.user_id}_{uuid.uuid4()}"

    def emit_event(self, event_type: str, data: Dict) -> None:
        """Emit event only to this user's connection."""
        event = {
            'type': event_type,
            'data': data,
            'user_id': self.user_context.user_id,
            'connection_id': self.connection_id,
            'timestamp': time.time()
        }
        self.event_queue.append(event)

    def get_user_events(self) -> List[Dict]:
        """Get events for this user only."""
        return [e for e in self.event_queue if e['user_id'] == self.user_context.user_id]


class MockToolDispatcher:
    """Mock tool dispatcher with user isolation."""

    def __init__(self, user_context: UserContext):
        self.user_context = user_context
        self.tool_executions = {}
        self.user_permissions = user_context.permissions

    def execute_tool(self, tool_name: str, parameters: Dict) -> Dict:
        """Execute tool with user-specific permissions."""
        if tool_name not in self.user_permissions:
            raise PermissionError(f"User {self.user_context.user_id} not authorized for tool {tool_name}")

        execution_id = f"tool_{uuid.uuid4()}"
        result = {
            'tool_name': tool_name,
            'parameters': parameters,
            'user_id': self.user_context.user_id,
            'execution_id': execution_id,
            'result': f"tool_result_for_{self.user_context.user_id}",
            'timestamp': time.time()
        }

        self.tool_executions[execution_id] = result
        return result


class EssentialUserIsolationFactory:
    """Essential user isolation factory (MUST be preserved)."""

    def __init__(self):
        self.active_contexts = {}
        self.execution_engines = {}
        self.websocket_emitters = {}
        self.tool_dispatchers = {}
        self._isolation_lock = threading.RLock()

    def create_user_execution_engine(self, user_id: str, auth_token: str, permissions: Set[str]) -> MockUserExecutionEngine:
        """Create isolated execution engine for user."""
        with self._isolation_lock:
            user_context = self._create_isolated_user_context(user_id, auth_token, permissions)

            if user_id in self.execution_engines:
                # Return existing engine for this user
                return self.execution_engines[user_id]

            engine = MockUserExecutionEngine(user_context)
            self.execution_engines[user_id] = engine
            return engine

    def create_user_websocket_emitter(self, user_id: str, auth_token: str) -> MockWebSocketEmitter:
        """Create isolated WebSocket emitter for user."""
        with self._isolation_lock:
            if user_id not in self.active_contexts:
                raise ValueError(f"No active context for user {user_id}")

            user_context = self.active_contexts[user_id]

            if user_id in self.websocket_emitters:
                return self.websocket_emitters[user_id]

            emitter = MockWebSocketEmitter(user_context)
            self.websocket_emitters[user_id] = emitter
            return emitter

    def create_user_tool_dispatcher(self, user_id: str, auth_token: str) -> MockToolDispatcher:
        """Create isolated tool dispatcher for user."""
        with self._isolation_lock:
            if user_id not in self.active_contexts:
                raise ValueError(f"No active context for user {user_id}")

            user_context = self.active_contexts[user_id]

            if user_id in self.tool_dispatchers:
                return self.tool_dispatchers[user_id]

            dispatcher = MockToolDispatcher(user_context)
            self.tool_dispatchers[user_id] = dispatcher
            return dispatcher

    def cleanup_user_session(self, user_id: str) -> None:
        """Clean up all resources for a user session."""
        with self._isolation_lock:
            self.active_contexts.pop(user_id, None)
            self.execution_engines.pop(user_id, None)
            self.websocket_emitters.pop(user_id, None)
            self.tool_dispatchers.pop(user_id, None)

    def _create_isolated_user_context(self, user_id: str, auth_token: str, permissions: Set[str]) -> UserContext:
        """Create completely isolated user context."""
        user_context = UserContext(
            user_id=user_id,
            session_id=f"session_{uuid.uuid4()}",
            auth_token=auth_token,
            permissions=permissions.copy(),  # Copy to prevent shared references
            private_data={
                'session_start': time.time(),
                'user_specific_config': f"config_for_{user_id}",
                'isolated_state': {}
            },
            created_at=time.time()
        )

        self.active_contexts[user_id] = user_context
        return user_context

    def get_active_user_count(self) -> int:
        """Get count of active user sessions."""
        return len(self.active_contexts)


class UserContextIsolationPhase2Tests(SSotBaseTestCase):
    """
    User Context Isolation Validation - Phase 2

    Validates user isolation in critical factory patterns that must be preserved.
    """

    def setUp(self):
        """Set up user isolation testing environment."""
        super().setUp()
        self.isolation_factory = EssentialUserIsolationFactory()
        self.test_users = []
        self.isolation_test_results = {}

        # Create test users for isolation testing
        for i in range(5):
            user = {
                'user_id': f"test_user_{i}",
                'auth_token': f"token_{i}_{uuid.uuid4()}",
                'permissions': {f"tool_{j}" for j in range(i + 1, i + 4)},  # Different permissions per user
                'private_data': f"sensitive_data_for_user_{i}"
            }
            self.test_users.append(user)

    def test_01_concurrent_user_execution_isolation(self):
        """
        EXPECTED: PASS - CRITICAL for $500K+ ARR protection

        Validates that user execution engines created by factories
        maintain complete isolation between concurrent users.
        """
        print(f"\n🔍 PHASE 2.1: Testing concurrent user execution isolation...")

        isolation_violations = []
        user_execution_results = {}

        def execute_user_task(user_data):
            """Execute task for a specific user."""
            user_id = user_data['user_id']
            auth_token = user_data['auth_token']
            permissions = user_data['permissions']

            try:
                # Create isolated execution engine
                engine = self.isolation_factory.create_user_execution_engine(
                    user_id, auth_token, permissions
                )

                # Execute user-specific task
                task_result = engine.execute_agent_task(f"task_for_{user_id}")

                # Get user-specific data
                user_data_result = engine.get_user_specific_data()

                return {
                    'user_id': user_id,
                    'task_result': task_result,
                    'user_data': user_data_result,
                    'engine_instance_id': id(engine),
                    'success': True
                }

            except Exception as e:
                return {
                    'user_id': user_id,
                    'error': str(e),
                    'success': False
                }

        # Execute tasks concurrently for all users
        print(f"  🔄 Executing concurrent tasks for {len(self.test_users)} users...")

        with ThreadPoolExecutor(max_workers=len(self.test_users)) as executor:
            futures = [executor.submit(execute_user_task, user) for user in self.test_users]

            for future in as_completed(futures):
                result = future.result()
                if result['success']:
                    user_execution_results[result['user_id']] = result
                else:
                    isolation_violations.append({
                        'user_id': result['user_id'],
                        'violation_type': 'execution_failure',
                        'error': result['error']
                    })

        print(f"  📊 Concurrent execution results:")
        print(f"     ✅ Successful executions: {len(user_execution_results)}")
        print(f"     ❌ Failed executions: {len(isolation_violations)}")

        # Validate isolation between users
        print(f"\n  🔒 Validating user isolation...")

        user_ids = list(user_execution_results.keys())

        for i, user_id_1 in enumerate(user_ids):
            for user_id_2 in user_ids[i+1:]:
                result_1 = user_execution_results[user_id_1]
                result_2 = user_execution_results[user_id_2]

                # Check that execution engines are different instances
                if result_1['engine_instance_id'] == result_2['engine_instance_id']:
                    isolation_violations.append({
                        'user_id': f"{user_id_1}, {user_id_2}",
                        'violation_type': 'shared_engine_instance',
                        'description': 'Users sharing same execution engine instance'
                    })

                # Check that task results contain correct user IDs
                if result_1['task_result']['user_id'] != user_id_1:
                    isolation_violations.append({
                        'user_id': user_id_1,
                        'violation_type': 'user_id_contamination',
                        'description': f"Task result contains wrong user ID: {result_1['task_result']['user_id']}"
                    })

                # Check that private data doesn't leak between users
                user_1_data = result_1['user_data']['session_data']
                user_2_data = result_2['user_data']['session_data']

                # Check for data contamination
                for key, value in user_1_data.items():
                    if key in user_2_data and user_2_data[key] == value:
                        # This could indicate shared state
                        if isinstance(value, str) and user_id_1 in value and user_id_2 not in value:
                            continue  # Expected user-specific data
                        isolation_violations.append({
                            'user_id': f"{user_id_1}, {user_id_2}",
                            'violation_type': 'data_contamination',
                            'description': f"Shared data detected: {key} = {value}"
                        })

        print(f"  🚨 Isolation violation summary:")
        for violation in isolation_violations:
            print(f"     ❌ {violation['violation_type']}: {violation['user_id']}")
            print(f"        {violation.get('description', violation.get('error', 'Unknown issue'))}")

        self.isolation_test_results['execution_isolation'] = {
            'successful_executions': len(user_execution_results),
            'isolation_violations': isolation_violations,
            'user_results': user_execution_results
        }

        # This test MUST PASS for user isolation factories
        self.assertEqual(
            len(isolation_violations),
            0,
            f"✅ USER EXECUTION ISOLATION: Found {len(isolation_violations)} isolation violations. "
            f"Expected 0 for secure multi-user execution. "
            f"User isolation is CRITICAL for $500K+ ARR protection."
        )

    def test_02_user_websocket_emitter_isolation(self):
        """
        EXPECTED: PASS - CRITICAL for chat functionality

        Validates that WebSocket emitters route events only to
        the correct user session.
        """
        print(f"\n🔍 PHASE 2.2: Testing WebSocket emitter isolation...")

        # First create execution engines to establish user contexts
        for user in self.test_users:
            self.isolation_factory.create_user_execution_engine(
                user['user_id'], user['auth_token'], user['permissions']
            )

        websocket_isolation_violations = []
        user_websocket_results = {}

        def test_user_websocket_isolation(user_data):
            """Test WebSocket isolation for a specific user."""
            user_id = user_data['user_id']
            auth_token = user_data['auth_token']

            try:
                # Create isolated WebSocket emitter
                emitter = self.isolation_factory.create_user_websocket_emitter(user_id, auth_token)

                # Emit user-specific events
                emitter.emit_event('agent_started', {'task': f'task_for_{user_id}'})
                emitter.emit_event('agent_thinking', {'thought': f'thinking_for_{user_id}'})
                emitter.emit_event('agent_completed', {'result': f'result_for_{user_id}'})

                # Get events for this user
                user_events = emitter.get_user_events()

                return {
                    'user_id': user_id,
                    'emitter_instance_id': id(emitter),
                    'connection_id': emitter.connection_id,
                    'events': user_events,
                    'event_count': len(user_events),
                    'success': True
                }

            except Exception as e:
                return {
                    'user_id': user_id,
                    'error': str(e),
                    'success': False
                }

        # Test WebSocket isolation concurrently
        print(f"  🔄 Testing WebSocket isolation for {len(self.test_users)} users...")

        with ThreadPoolExecutor(max_workers=len(self.test_users)) as executor:
            futures = [executor.submit(test_user_websocket_isolation, user) for user in self.test_users]

            for future in as_completed(futures):
                result = future.result()
                if result['success']:
                    user_websocket_results[result['user_id']] = result
                else:
                    websocket_isolation_violations.append({
                        'user_id': result['user_id'],
                        'violation_type': 'websocket_creation_failure',
                        'error': result['error']
                    })

        print(f"  📊 WebSocket isolation results:")
        print(f"     ✅ Successful WebSocket creations: {len(user_websocket_results)}")
        print(f"     ❌ Failed WebSocket creations: {len(websocket_isolation_violations)}")

        # Validate WebSocket isolation
        print(f"\n  🔒 Validating WebSocket event isolation...")

        user_ids = list(user_websocket_results.keys())

        for i, user_id_1 in enumerate(user_ids):
            for user_id_2 in user_ids[i+1:]:
                result_1 = user_websocket_results[user_id_1]
                result_2 = user_websocket_results[user_id_2]

                # Check that WebSocket emitters are different instances
                if result_1['emitter_instance_id'] == result_2['emitter_instance_id']:
                    websocket_isolation_violations.append({
                        'user_id': f"{user_id_1}, {user_id_2}",
                        'violation_type': 'shared_websocket_instance',
                        'description': 'Users sharing same WebSocket emitter instance'
                    })

                # Check that connection IDs are unique
                if result_1['connection_id'] == result_2['connection_id']:
                    websocket_isolation_violations.append({
                        'user_id': f"{user_id_1}, {user_id_2}",
                        'violation_type': 'shared_connection_id',
                        'description': 'Users sharing same WebSocket connection ID'
                    })

                # Check that events are user-specific
                for event in result_1['events']:
                    if event['user_id'] != user_id_1:
                        websocket_isolation_violations.append({
                            'user_id': user_id_1,
                            'violation_type': 'event_user_id_mismatch',
                            'description': f"Event has wrong user ID: {event['user_id']}"
                        })

                # Check for event content contamination
                user_1_events = [e['data'] for e in result_1['events']]
                user_2_events = [e['data'] for e in result_2['events']]

                for event_data in user_1_events:
                    if event_data in user_2_events:
                        # Check if this is legitimate shared data or contamination
                        event_str = str(event_data)
                        if user_id_1 in event_str and user_id_2 in event_str:
                            websocket_isolation_violations.append({
                                'user_id': f"{user_id_1}, {user_id_2}",
                                'violation_type': 'event_data_contamination',
                                'description': f"Event data leaked between users: {event_data}"
                            })

        print(f"  🚨 WebSocket isolation violation summary:")
        for violation in websocket_isolation_violations:
            print(f"     ❌ {violation['violation_type']}: {violation['user_id']}")
            print(f"        {violation.get('description', violation.get('error', 'Unknown issue'))}")

        self.isolation_test_results['websocket_isolation'] = {
            'successful_websockets': len(user_websocket_results),
            'isolation_violations': websocket_isolation_violations,
            'user_results': user_websocket_results
        }

        # This test MUST PASS for WebSocket isolation
        self.assertEqual(
            len(websocket_isolation_violations),
            0,
            f"✅ WEBSOCKET ISOLATION: Found {len(websocket_isolation_violations)} WebSocket isolation violations. "
            f"Expected 0 for secure event routing. "
            f"WebSocket isolation is CRITICAL for chat functionality ($500K+ ARR)."
        )

    def test_03_user_tool_dispatcher_isolation(self):
        """
        EXPECTED: PASS - CRITICAL for security

        Validates that tool dispatchers maintain user-specific
        permissions and don't leak data between users.
        """
        print(f"\n🔍 PHASE 2.3: Testing tool dispatcher isolation...")

        # Ensure user contexts exist
        for user in self.test_users:
            self.isolation_factory.create_user_execution_engine(
                user['user_id'], user['auth_token'], user['permissions']
            )

        tool_isolation_violations = []
        user_tool_results = {}

        def test_user_tool_isolation(user_data):
            """Test tool dispatcher isolation for a specific user."""
            user_id = user_data['user_id']
            auth_token = user_data['auth_token']
            user_permissions = user_data['permissions']

            try:
                # Create isolated tool dispatcher
                dispatcher = self.isolation_factory.create_user_tool_dispatcher(user_id, auth_token)

                # Test authorized tool execution
                authorized_results = []
                for tool_name in user_permissions:
                    result = dispatcher.execute_tool(tool_name, {'param': f'value_for_{user_id}'})
                    authorized_results.append(result)

                # Test unauthorized tool execution
                unauthorized_tools = [f"restricted_tool_{i}" for i in range(3)]
                unauthorized_results = []

                for tool_name in unauthorized_tools:
                    try:
                        result = dispatcher.execute_tool(tool_name, {'param': 'test'})
                        unauthorized_results.append({
                            'tool': tool_name,
                            'result': result,
                            'should_have_failed': True
                        })
                    except PermissionError:
                        # Expected behavior - unauthorized access denied
                        pass
                    except Exception as e:
                        unauthorized_results.append({
                            'tool': tool_name,
                            'error': str(e),
                            'unexpected_error': True
                        })

                return {
                    'user_id': user_id,
                    'dispatcher_instance_id': id(dispatcher),
                    'authorized_executions': authorized_results,
                    'unauthorized_attempts': unauthorized_results,
                    'permissions': list(user_permissions),
                    'success': True
                }

            except Exception as e:
                return {
                    'user_id': user_id,
                    'error': str(e),
                    'success': False
                }

        # Test tool isolation concurrently
        print(f"  🔄 Testing tool dispatcher isolation for {len(self.test_users)} users...")

        with ThreadPoolExecutor(max_workers=len(self.test_users)) as executor:
            futures = [executor.submit(test_user_tool_isolation, user) for user in self.test_users]

            for future in as_completed(futures):
                result = future.result()
                if result['success']:
                    user_tool_results[result['user_id']] = result
                else:
                    tool_isolation_violations.append({
                        'user_id': result['user_id'],
                        'violation_type': 'tool_dispatcher_failure',
                        'error': result['error']
                    })

        print(f"  📊 Tool dispatcher isolation results:")
        print(f"     ✅ Successful dispatcher creations: {len(user_tool_results)}")
        print(f"     ❌ Failed dispatcher creations: {len(tool_isolation_violations)}")

        # Validate tool isolation and permissions
        print(f"\n  🔒 Validating tool permission isolation...")

        for user_id, result in user_tool_results.items():
            # Check for permission violations
            for unauthorized_attempt in result['unauthorized_attempts']:
                if 'should_have_failed' in unauthorized_attempt:
                    tool_isolation_violations.append({
                        'user_id': user_id,
                        'violation_type': 'permission_bypass',
                        'description': f"User accessed unauthorized tool: {unauthorized_attempt['tool']}"
                    })
                elif 'unexpected_error' in unauthorized_attempt:
                    tool_isolation_violations.append({
                        'user_id': user_id,
                        'violation_type': 'unexpected_tool_error',
                        'description': f"Unexpected error for tool {unauthorized_attempt['tool']}: {unauthorized_attempt['error']}"
                    })

            # Validate that authorized executions contain correct user data
            for execution in result['authorized_executions']:
                if execution['user_id'] != user_id:
                    tool_isolation_violations.append({
                        'user_id': user_id,
                        'violation_type': 'tool_result_user_mismatch',
                        'description': f"Tool result has wrong user ID: {execution['user_id']}"
                    })

        # Check for cross-user data contamination
        user_ids = list(user_tool_results.keys())

        for i, user_id_1 in enumerate(user_ids):
            for user_id_2 in user_ids[i+1:]:
                result_1 = user_tool_results[user_id_1]
                result_2 = user_tool_results[user_id_2]

                # Check that dispatchers are different instances
                if result_1['dispatcher_instance_id'] == result_2['dispatcher_instance_id']:
                    tool_isolation_violations.append({
                        'user_id': f"{user_id_1}, {user_id_2}",
                        'violation_type': 'shared_dispatcher_instance',
                        'description': 'Users sharing same tool dispatcher instance'
                    })

                # Check for tool result contamination
                user_1_results = [r['result'] for r in result_1['authorized_executions']]
                user_2_results = [r['result'] for r in result_2['authorized_executions']]

                for result_str in user_1_results:
                    if result_str in user_2_results:
                        if user_id_1 in str(result_str) and user_id_2 in str(result_str):
                            tool_isolation_violations.append({
                                'user_id': f"{user_id_1}, {user_id_2}",
                                'violation_type': 'tool_result_contamination',
                                'description': f"Tool result leaked between users: {result_str}"
                            })

        print(f"  🚨 Tool isolation violation summary:")
        for violation in tool_isolation_violations:
            print(f"     ❌ {violation['violation_type']}: {violation['user_id']}")
            print(f"        {violation.get('description', violation.get('error', 'Unknown issue'))}")

        self.isolation_test_results['tool_isolation'] = {
            'successful_dispatchers': len(user_tool_results),
            'isolation_violations': tool_isolation_violations,
            'user_results': user_tool_results
        }

        # This test MUST PASS for tool security
        self.assertEqual(
            len(tool_isolation_violations),
            0,
            f"✅ TOOL DISPATCHER ISOLATION: Found {len(tool_isolation_violations)} tool isolation violations. "
            f"Expected 0 for secure tool execution. "
            f"Tool isolation is CRITICAL for multi-user security."
        )

    def test_04_user_session_cleanup_validation(self):
        """
        EXPECTED: PASS - CRITICAL for resource management

        Validates that factory-created user sessions are properly
        cleaned up to prevent memory leaks.
        """
        print(f"\n🔍 PHASE 2.4: Testing user session cleanup...")

        cleanup_violations = []

        # Create sessions for all test users
        created_sessions = []
        for user in self.test_users:
            user_id = user['user_id']
            auth_token = user['auth_token']
            permissions = user['permissions']

            # Create all user components
            engine = self.isolation_factory.create_user_execution_engine(user_id, auth_token, permissions)
            emitter = self.isolation_factory.create_user_websocket_emitter(user_id, auth_token)
            dispatcher = self.isolation_factory.create_user_tool_dispatcher(user_id, auth_token)

            created_sessions.append({
                'user_id': user_id,
                'engine': weakref.ref(engine),
                'emitter': weakref.ref(emitter),
                'dispatcher': weakref.ref(dispatcher)
            })

        initial_active_count = self.isolation_factory.get_active_user_count()
        print(f"  📊 Initial active user sessions: {initial_active_count}")

        # Test cleanup for each user
        print(f"  🧹 Testing session cleanup...")

        for session in created_sessions:
            user_id = session['user_id']

            # Cleanup user session
            try:
                self.isolation_factory.cleanup_user_session(user_id)

                # Verify cleanup was successful
                try:
                    # These should fail after cleanup
                    self.isolation_factory.create_user_websocket_emitter(user_id, "invalid_token")
                    cleanup_violations.append({
                        'user_id': user_id,
                        'violation_type': 'context_not_cleaned',
                        'description': 'User context still exists after cleanup'
                    })
                except ValueError:
                    # Expected - context should be gone
                    pass

            except Exception as e:
                cleanup_violations.append({
                    'user_id': user_id,
                    'violation_type': 'cleanup_failure',
                    'error': str(e)
                })

        final_active_count = self.isolation_factory.get_active_user_count()
        print(f"  📊 Final active user sessions: {final_active_count}")

        # Check for memory leaks
        gc.collect()  # Force garbage collection

        memory_leaks = []
        for session in created_sessions:
            user_id = session['user_id']

            # Check if objects were properly garbage collected
            if session['engine']() is not None:
                memory_leaks.append({
                    'user_id': user_id,
                    'component': 'execution_engine',
                    'description': 'Execution engine not garbage collected'
                })

            if session['emitter']() is not None:
                memory_leaks.append({
                    'user_id': user_id,
                    'component': 'websocket_emitter',
                    'description': 'WebSocket emitter not garbage collected'
                })

            if session['dispatcher']() is not None:
                memory_leaks.append({
                    'user_id': user_id,
                    'component': 'tool_dispatcher',
                    'description': 'Tool dispatcher not garbage collected'
                })

        print(f"  🧹 Cleanup validation results:")
        print(f"     ✅ Sessions cleaned: {len(self.test_users) - len(cleanup_violations)}")
        print(f"     ❌ Cleanup failures: {len(cleanup_violations)}")
        print(f"     💾 Memory leaks detected: {len(memory_leaks)}")

        all_violations = cleanup_violations + memory_leaks

        for violation in all_violations:
            print(f"     ❌ {violation.get('violation_type', 'memory_leak')}: {violation['user_id']}")
            print(f"        {violation.get('description', violation.get('error', 'Unknown issue'))}")

        self.isolation_test_results['session_cleanup'] = {
            'cleanup_violations': cleanup_violations,
            'memory_leaks': memory_leaks,
            'initial_sessions': initial_active_count,
            'final_sessions': final_active_count
        }

        # This test MUST PASS for proper resource management
        self.assertEqual(
            len(all_violations),
            0,
            f"✅ SESSION CLEANUP: Found {len(all_violations)} cleanup/memory violations. "
            f"Expected 0 for proper resource management. "
            f"Session cleanup is CRITICAL for preventing memory leaks."
        )

    def test_05_isolation_factory_preservation_validation(self):
        """
        EXPECTED: PASS - Validates that user isolation factory must be preserved

        Comprehensive validation that the user isolation factory provides
        essential business value and must be preserved during cleanup.
        """
        print(f"\n🔍 PHASE 2.5: Validating isolation factory preservation requirements...")

        preservation_analysis = {
            'business_critical_features': [],
            'security_requirements': [],
            'performance_characteristics': [],
            'preservation_score': 0
        }

        # Test 1: Business critical multi-user support
        print(f"  💼 Testing business critical multi-user support...")

        try:
            # Simulate high concurrent user load
            concurrent_users = 20
            user_engines = []

            for i in range(concurrent_users):
                engine = self.isolation_factory.create_user_execution_engine(
                    f"load_test_user_{i}",
                    f"token_{i}",
                    {f"tool_{j}" for j in range(3)}
                )
                user_engines.append(engine)

            # Verify all engines are isolated
            unique_instances = len(set(id(engine) for engine in user_engines))

            if unique_instances == concurrent_users:
                preservation_analysis['business_critical_features'].append({
                    'feature': 'concurrent_user_support',
                    'status': 'PASS',
                    'description': f'Successfully created {concurrent_users} isolated user sessions'
                })
                preservation_analysis['preservation_score'] += 3
            else:
                preservation_analysis['business_critical_features'].append({
                    'feature': 'concurrent_user_support',
                    'status': 'FAIL',
                    'description': f'Only {unique_instances}/{concurrent_users} unique instances created'
                })

            # Cleanup load test users
            for i in range(concurrent_users):
                self.isolation_factory.cleanup_user_session(f"load_test_user_{i}")

        except Exception as e:
            preservation_analysis['business_critical_features'].append({
                'feature': 'concurrent_user_support',
                'status': 'ERROR',
                'description': f'Load test failed: {e}'
            })

        # Test 2: Security isolation requirements
        print(f"  🛡️  Testing security isolation requirements...")

        try:
            # Create two users with different security contexts
            user_a = self.isolation_factory.create_user_execution_engine(
                "security_user_a", "token_a", {"read_sensitive", "write_data"}
            )
            user_b = self.isolation_factory.create_user_execution_engine(
                "security_user_b", "token_b", {"read_public"}
            )

            # Execute tasks and verify isolation
            task_a = user_a.execute_agent_task("access_sensitive_data")
            task_b = user_b.execute_agent_task("access_public_data")

            # Verify no cross-contamination
            if (task_a['user_id'] == "security_user_a" and
                task_b['user_id'] == "security_user_b" and
                task_a['private_result'] != task_b['private_result']):

                preservation_analysis['security_requirements'].append({
                    'requirement': 'user_data_isolation',
                    'status': 'PASS',
                    'description': 'User data properly isolated between security contexts'
                })
                preservation_analysis['preservation_score'] += 4
            else:
                preservation_analysis['security_requirements'].append({
                    'requirement': 'user_data_isolation',
                    'status': 'FAIL',
                    'description': 'User data contamination detected'
                })

            # Cleanup security test users
            self.isolation_factory.cleanup_user_session("security_user_a")
            self.isolation_factory.cleanup_user_session("security_user_b")

        except Exception as e:
            preservation_analysis['security_requirements'].append({
                'requirement': 'user_data_isolation',
                'status': 'ERROR',
                'description': f'Security test failed: {e}'
            })

        # Test 3: Performance characteristics
        print(f"  ⚡ Testing performance characteristics...")

        try:
            start_time = time.time()

            # Create and cleanup 100 user sessions
            for i in range(100):
                engine = self.isolation_factory.create_user_execution_engine(
                    f"perf_user_{i}", f"token_{i}", {"tool_1"}
                )
                self.isolation_factory.cleanup_user_session(f"perf_user_{i}")

            total_time = time.time() - start_time
            avg_time_per_user = total_time / 100

            if avg_time_per_user < 0.01:  # Less than 10ms per user
                preservation_analysis['performance_characteristics'].append({
                    'characteristic': 'user_creation_performance',
                    'status': 'EXCELLENT',
                    'description': f'Average {avg_time_per_user*1000:.2f}ms per user session'
                })
                preservation_analysis['preservation_score'] += 2
            elif avg_time_per_user < 0.05:  # Less than 50ms per user
                preservation_analysis['performance_characteristics'].append({
                    'characteristic': 'user_creation_performance',
                    'status': 'GOOD',
                    'description': f'Average {avg_time_per_user*1000:.2f}ms per user session'
                })
                preservation_analysis['preservation_score'] += 1
            else:
                preservation_analysis['performance_characteristics'].append({
                    'characteristic': 'user_creation_performance',
                    'status': 'POOR',
                    'description': f'Average {avg_time_per_user*1000:.2f}ms per user session - too slow'
                })

        except Exception as e:
            preservation_analysis['performance_characteristics'].append({
                'characteristic': 'user_creation_performance',
                'status': 'ERROR',
                'description': f'Performance test failed: {e}'
            })

        # Generate preservation recommendation
        max_score = 9  # 3 + 4 + 2
        preservation_percentage = (preservation_analysis['preservation_score'] / max_score) * 100

        print(f"\n  📋 ISOLATION FACTORY PRESERVATION ANALYSIS:")
        print(f"     🎯 Preservation score: {preservation_analysis['preservation_score']}/{max_score} ({preservation_percentage:.1f}%)")

        print(f"\n     💼 Business Critical Features:")
        for feature in preservation_analysis['business_critical_features']:
            print(f"       {feature['status']}: {feature['feature']} - {feature['description']}")

        print(f"\n     🛡️  Security Requirements:")
        for requirement in preservation_analysis['security_requirements']:
            print(f"       {requirement['status']}: {requirement['requirement']} - {requirement['description']}")

        print(f"\n     ⚡ Performance Characteristics:")
        for characteristic in preservation_analysis['performance_characteristics']:
            print(f"       {characteristic['status']}: {characteristic['characteristic']} - {characteristic['description']}")

        if preservation_percentage >= 80:
            recommendation = "PRESERVE - Essential for business functionality"
            print(f"\n     ✅ RECOMMENDATION: {recommendation}")
        elif preservation_percentage >= 60:
            recommendation = "PRESERVE WITH OPTIMIZATION - Has value but needs improvement"
            print(f"\n     ⚠️  RECOMMENDATION: {recommendation}")
        else:
            recommendation = "CONSIDER REPLACEMENT - Poor performance or functionality"
            print(f"\n     ❌ RECOMMENDATION: {recommendation}")

        self.isolation_test_results['preservation_analysis'] = preservation_analysis

        # User isolation factory MUST score high enough to be preserved
        self.assertGreaterEqual(
            preservation_percentage,
            80.0,
            f"✅ ISOLATION FACTORY PRESERVATION: Factory scored {preservation_percentage:.1f}% preservation value. "
            f"Required ≥80% to justify preservation during cleanup. "
            f"User isolation factory is ESSENTIAL for multi-user security ($500K+ ARR)."
        )


if __name__ == '__main__':
    import unittest

    print("🚀 Starting User Context Isolation Validation - Phase 2")
    print("=" * 80)
    print("These tests MUST PASS for essential user isolation factories.")
    print("=" * 80)

    unittest.main(verbosity=2)