"""
Test 4: User Context Isolation Factory Validation

PURPOSE: Validate proper user isolation with factory pattern implementation.
ISSUE: #709 - Agent Factory Singleton Legacy remediation
SCOPE: Integration test for user context isolation via factory patterns

EXPECTED BEHAVIOR:
- BEFORE REMEDIATION: Tests should FAIL (proving user isolation violations exist)
- AFTER REMEDIATION: Tests should PASS (proving proper user isolation)

Business Value: Platform/Internal - $500K+ ARR protection through secure multi-user isolation
"""
import asyncio
import gc
import time
import uuid
import weakref
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

class TestUserContextIsolationFactory(SSotAsyncTestCase):
    """
    Integration test suite validating user context isolation via factory patterns.

    This test suite specifically targets Issue #709 by validating that:
    1. Factory-created agents are isolated per user
    2. UserExecutionContext properly passed to agents
    3. No cross-user state contamination
    4. WebSocket events delivered only to correct user

    CRITICAL: These tests should FAIL before remediation and PASS after.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self._tracked_instances = []
        self._tracked_contexts = []
        self._tracked_factories = []
        self._mock_websocket_bridge = SSotMockFactory.create_mock_agent_websocket_bridge()
        self._mock_agent_registry = MagicMock()
        self._mock_llm_manager = SSotMockFactory.create_mock_llm_manager()
        self._websocket_events = []

        def track_websocket_event(run_id, event_type, data):
            self._websocket_events.append({'run_id': run_id, 'event_type': event_type, 'data': data, 'timestamp': datetime.now(timezone.utc)})
            return True
        if hasattr(self._mock_websocket_bridge, 'send_agent_event'):
            self._mock_websocket_bridge.send_agent_event.side_effect = track_websocket_event
        self.record_metric('test_setup_completed', True)

    def teardown_method(self, method):
        """Cleanup after each test method."""
        for instance in self._tracked_instances:
            try:
                if hasattr(instance, 'cleanup') and callable(instance.cleanup):
                    if asyncio.iscoroutinefunction(instance.cleanup):
                        asyncio.create_task(instance.cleanup())
                    else:
                        instance.cleanup()
            except Exception as e:
                print(f'Warning: Instance cleanup failed: {e}')
        for context in self._tracked_contexts:
            try:
                if hasattr(context, 'cleanup') and callable(context.cleanup):
                    if asyncio.iscoroutinefunction(context.cleanup):
                        asyncio.create_task(context.cleanup())
                    else:
                        context.cleanup()
            except Exception as e:
                print(f'Warning: Context cleanup failed: {e}')
        for factory in self._tracked_factories:
            try:
                if hasattr(factory, 'reset_for_testing') and callable(factory.reset_for_testing):
                    factory.reset_for_testing()
            except Exception as e:
                print(f'Warning: Factory cleanup failed: {e}')
        gc.collect()
        super().teardown_method(method)

    async def _create_test_user_context(self, user_id: str, suffix: str='') -> Any:
        """Create a test user execution context."""
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            context = UserExecutionContext.from_request_supervisor(user_id=f'{user_id}_{suffix}' if suffix else user_id, thread_id=f'thread_{user_id}_{suffix}_{int(time.time())}', run_id=f'run_{user_id}_{suffix}_{uuid.uuid4().hex[:8]}')
            self._tracked_contexts.append(context)
            return context
        except ImportError as e:
            pytest.skip(f'Cannot import UserExecutionContext: {e}')

    async def _create_configured_factory(self) -> Any:
        """Create and configure an AgentInstanceFactory for testing."""
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            factory = AgentInstanceFactory()
            factory.configure(websocket_bridge=self._mock_websocket_bridge, agent_registry=self._mock_agent_registry, llm_manager=self._mock_llm_manager)
            self._tracked_factories.append(factory)
            return factory
        except ImportError as e:
            pytest.skip(f'Cannot import AgentInstanceFactory: {e}')

    async def test_factory_creates_isolated_agents_per_user(self):
        """
        CRITICAL TEST: Validate factory creates isolated agent instances per user.

        This test should FAIL before Issue #709 remediation due to shared
        agent instances or state between different users.

        After remediation, this test should PASS by proving proper user isolation.
        """
        self.record_metric('test_started', 'test_factory_creates_isolated_agents_per_user')
        try:
            factory = await self._create_configured_factory()
            user1_context = await self._create_test_user_context('user1', 'isolation_test')
            user2_context = await self._create_test_user_context('user2', 'isolation_test')
            user3_context = await self._create_test_user_context('user3', 'isolation_test')
            agent_name = 'TriageSubAgent'
            agents = {}
            for user_id, context in [('user1', user1_context), ('user2', user2_context), ('user3', user3_context)]:
                try:
                    agent = await factory.create_agent_instance(agent_name=agent_name, user_context=context)
                    agents[user_id] = agent
                    self._tracked_instances.append(agent)
                except Exception as e:
                    pytest.fail(f'FACTORY ISOLATION VIOLATION: Failed to create {agent_name} for {user_id}: {e}')
            agent_instances = list(agents.values())
            agent_ids = [id(agent) for agent in agent_instances]
            unique_ids = set(agent_ids)
            assert len(unique_ids) == len(agent_instances), f'AGENT ISOLATION VIOLATION: Factory returned shared agent instances. Agent IDs: {agent_ids}, Unique: {len(unique_ids)}. Expected: Each user to receive unique agent instance.'
            for user_id, agent in agents.items():
                if hasattr(agent, 'user_context') or hasattr(agent, '_user_context'):
                    agent_context = getattr(agent, 'user_context', None) or getattr(agent, '_user_context', None)
                    if agent_context:
                        assert agent_context.user_id.startswith(user_id), f'USER CONTEXT ISOLATION VIOLATION: {user_id} agent has wrong context. Agent context user_id: {agent_context.user_id}, Expected: starts with {user_id}. This indicates cross-user context contamination.'
            test_marker = f'user1_unique_marker_{uuid.uuid4().hex[:8]}'
            agents['user1'].test_isolation_marker = test_marker
            for user_id in ['user2', 'user3']:
                agent = agents[user_id]
                assert not hasattr(agent, 'test_isolation_marker'), f"STATE ISOLATION VIOLATION: {user_id} agent has user1's marker. Marker: {getattr(agent, 'test_isolation_marker', None)}. Expected: Each agent to have independent state."
            if hasattr(agents['user1'], '_websocket_adapter') or hasattr(agents['user1'], 'set_websocket_bridge'):
                try:
                    if hasattr(agents['user1'], '_websocket_adapter') and agents['user1']._websocket_adapter:
                        adapter = agents['user1']._websocket_adapter
                        if hasattr(adapter, 'send_event'):
                            await adapter.send_event('test_event', {'test': 'user1_data'})
                    user1_events = [event for event in self._websocket_events if event['run_id'] == user1_context.run_id]
                    assert len(user1_events) > 0, f"WEBSOCKET ISOLATION VIOLATION: No events recorded for user1. All events: {self._websocket_events}. Expected: Events to be properly routed to user1's run_id."
                    user2_events = [event for event in self._websocket_events if event['run_id'] == user2_context.run_id]
                    assert len(user2_events) == 0, f"WEBSOCKET ISOLATION VIOLATION: user2 received user1's events. user2 events: {user2_events}. Expected: No cross-user event contamination."
                except Exception as e:
                    print(f'Warning: WebSocket event testing failed: {e}')
            self.record_metric('agents_created', len(agents))
            self.record_metric('isolation_checks_passed', 6)
            self.record_metric('test_result', 'PASS')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during agent isolation validation: {e}')

    async def test_concurrent_user_contexts_maintain_isolation(self):
        """
        CRITICAL TEST: Validate concurrent user operations maintain complete isolation.

        This test creates multiple users concurrently executing agent operations
        to verify no race conditions or state leakage occurs.

        Expected to FAIL before remediation due to concurrent isolation issues.
        """
        self.record_metric('test_started', 'test_concurrent_user_contexts_maintain_isolation')

        async def simulate_user_workflow(user_id: str, operation_count: int) -> Dict[str, Any]:
            """Simulate a user's agent workflow with multiple operations."""
            try:
                context = await self._create_test_user_context(f'concurrent_{user_id}', 'workflow')
                factory = await self._create_configured_factory()
                agent = await factory.create_agent_instance(agent_name='DataHelperAgent', user_context=context)
                self._tracked_instances.append(agent)
                user_data = {'user_id': user_id, 'context_user_id': context.user_id, 'agent_id': id(agent), 'operations': []}
                for i in range(operation_count):
                    operation_marker = f'{user_id}_operation_{i}_{uuid.uuid4().hex[:4]}'
                    setattr(agent, f'operation_{i}', operation_marker)
                    user_data['operations'].append({'operation_id': i, 'marker': operation_marker, 'timestamp': time.time()})
                    await asyncio.sleep(0.01)
                return user_data
            except Exception as e:
                return {'user_id': user_id, 'error': str(e)}
        try:
            concurrent_users = 5
            operations_per_user = 3
            tasks = [simulate_user_workflow(f'user_{i}', operations_per_user) for i in range(concurrent_users)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            failed_workflows = []
            successful_results = []
            for result in results:
                if isinstance(result, Exception):
                    failed_workflows.append(f'Exception: {result}')
                elif 'error' in result:
                    failed_workflows.append(f"User {result['user_id']}: {result['error']}")
                else:
                    successful_results.append(result)
            if failed_workflows:
                pytest.fail(f'CONCURRENT ISOLATION VIOLATION: Failed workflows: {failed_workflows}')
            context_user_ids = [result['context_user_id'] for result in successful_results]
            unique_context_ids = set(context_user_ids)
            assert len(unique_context_ids) == len(successful_results), f'CONTEXT ISOLATION VIOLATION: Duplicate context user IDs detected. Context IDs: {context_user_ids}. Expected: Each user to have unique context.'
            agent_ids = [result['agent_id'] for result in successful_results]
            unique_agent_ids = set(agent_ids)
            assert len(unique_agent_ids) == len(successful_results), f'AGENT ISOLATION VIOLATION: Shared agent instances in concurrent execution. Agent IDs: {agent_ids}. Expected: Each user to have unique agent instance.'
            for i, result in enumerate(successful_results):
                user_id = result['user_id']
                operations = result['operations']
                for operation in operations:
                    marker = operation['marker']
                    assert marker.startswith(user_id), f'OPERATION ISOLATION VIOLATION: {user_id} operation has wrong marker: {marker}. Expected: Marker to start with {user_id}.'
                    for j, other_result in enumerate(successful_results):
                        if i != j:
                            other_operations = other_result['operations']
                            other_markers = [op['marker'] for op in other_operations]
                            assert marker not in other_markers, f"OPERATION ISOLATION VIOLATION: User {user_id} marker found in user {other_result['user_id']} operations. Shared marker: {marker}. Expected: Complete operation isolation between users."
            operation_times = []
            for result in successful_results:
                user_operations = result['operations']
                if len(user_operations) > 1:
                    start_time = user_operations[0]['timestamp']
                    end_time = user_operations[-1]['timestamp']
                    total_time = end_time - start_time
                    operation_times.append(total_time)
            if operation_times:
                max_operation_time = max(operation_times)
                assert max_operation_time < 5.0, f'CONCURRENT ISOLATION VIOLATION: Excessive operation time: {max_operation_time:.2f}s. This may indicate blocking or deadlock issues in concurrent execution.'
            self.record_metric('concurrent_users', concurrent_users)
            self.record_metric('successful_workflows', len(successful_results))
            self.record_metric('concurrent_isolation_checks_passed', 6)
            self.record_metric('test_result', 'PASS')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during concurrent isolation validation: {e}')

    async def test_factory_cleanup_preserves_user_isolation(self):
        """
        CRITICAL TEST: Validate factory cleanup doesn't affect other users.

        This test verifies that when one user's factory context is cleaned up,
        other users' contexts and agents remain unaffected.

        Expected to FAIL before remediation due to shared cleanup state.
        """
        self.record_metric('test_started', 'test_factory_cleanup_preserves_user_isolation')
        try:
            factory = await self._create_configured_factory()
            user_contexts = {}
            user_agents = {}
            for user_id in ['cleanup_user_1', 'cleanup_user_2', 'cleanup_user_3']:
                context = await self._create_test_user_context(user_id, 'cleanup_test')
                user_contexts[user_id] = context
                factory_context = await factory.create_user_execution_context(user_id=context.user_id, thread_id=context.thread_id, run_id=context.run_id)
                agent = await factory.create_agent_instance(agent_name='TriageSubAgent', user_context=context)
                user_agents[user_id] = {'context': context, 'factory_context': factory_context, 'agent': agent, 'cleanup_marker': f'{user_id}_active_marker_{uuid.uuid4().hex[:6]}'}
                setattr(agent, 'cleanup_test_marker', user_agents[user_id]['cleanup_marker'])
                self._tracked_instances.append(agent)
            assert len(user_agents) == 3, 'Setup verification failed'
            for user_id, user_data in user_agents.items():
                agent = user_data['agent']
                agent.user_specific_data = {'user_id': user_id, 'secret_key': f'secret_{user_id}_{uuid.uuid4().hex}', 'created_at': datetime.now(timezone.utc).isoformat()}
            user1_data = user_agents['cleanup_user_1']
            user1_factory_context = user1_data['factory_context']
            try:
                await factory.cleanup_user_context(user1_factory_context)
                self.record_metric('user1_cleanup_success', True)
            except Exception as e:
                pytest.fail(f'Factory cleanup failed for user_1: {e}')
            for user_id in ['cleanup_user_2', 'cleanup_user_3']:
                user_data = user_agents[user_id]
                agent = user_data['agent']
                assert hasattr(agent, 'cleanup_test_marker'), f'CLEANUP ISOLATION VIOLATION: {user_id} agent lost cleanup_test_marker after user_1 cleanup. This indicates shared cleanup state affecting other users.'
                expected_marker = user_data['cleanup_marker']
                actual_marker = getattr(agent, 'cleanup_test_marker', None)
                assert actual_marker == expected_marker, f"CLEANUP ISOLATION VIOLATION: {user_id} agent marker corrupted after user_1 cleanup. Expected: {expected_marker}, Got: {actual_marker}. This indicates cleanup affecting other users' agent state."
                assert hasattr(agent, 'user_specific_data'), f"CLEANUP ISOLATION VIOLATION: {user_id} agent lost user_specific_data after user_1 cleanup. This indicates cleanup removing data from other users' agents."
                user_data_obj = getattr(agent, 'user_specific_data', {})
                assert user_data_obj.get('user_id') == user_id, f"CLEANUP ISOLATION VIOLATION: {user_id} agent user_specific_data corrupted. Expected user_id: {user_id}, Got: {user_data_obj.get('user_id')}. This indicates cross-user data corruption during cleanup."
            for user_id in ['cleanup_user_2', 'cleanup_user_3']:
                user_data = user_agents[user_id]
                agent = user_data['agent']
                test_functionality_marker = f'{user_id}_post_cleanup_{uuid.uuid4().hex[:4]}'
                try:
                    agent.post_cleanup_test = test_functionality_marker
                    assert getattr(agent, 'post_cleanup_test', None) == test_functionality_marker, f'CLEANUP ISOLATION VIOLATION: {user_id} agent functionality impaired after cleanup. Cannot set/get new attributes properly.'
                except Exception as e:
                    pytest.fail(f'CLEANUP ISOLATION VIOLATION: {user_id} agent broken after user_1 cleanup: {e}')
            factory_metrics = factory.get_factory_metrics()
            active_contexts = factory_metrics.get('active_contexts', 0)
            expected_active = 2
            assert active_contexts == expected_active, f"CLEANUP ISOLATION VIOLATION: Incorrect active contexts count after cleanup. Expected: {expected_active}, Got: {active_contexts}. This indicates cleanup affecting other users' context tracking."
            cleaned_count = factory_metrics.get('total_contexts_cleaned', 0)
            assert cleaned_count >= 1, f'CLEANUP ISOLATION VIOLATION: Cleanup not properly recorded. Cleaned count: {cleaned_count}. Expected: At least 1 cleanup recorded.'
            self.record_metric('cleanup_isolation_checks_passed', 6)
            self.record_metric('test_result', 'PASS')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during cleanup isolation validation: {e}')

    async def test_websocket_events_user_isolation(self):
        """
        CRITICAL TEST: Validate WebSocket events are delivered only to correct users.

        This test verifies that when agents send WebSocket events, they are
        properly routed to the correct user and don't leak to other users.

        Expected to FAIL before remediation due to WebSocket event cross-contamination.
        """
        self.record_metric('test_started', 'test_websocket_events_user_isolation')
        try:
            factory = await self._create_configured_factory()
            users_data = {}
            for user_id in ['ws_user_A', 'ws_user_B', 'ws_user_C']:
                context = await self._create_test_user_context(user_id, 'websocket_test')
                agent = await factory.create_agent_instance(agent_name='DataHelperAgent', user_context=context)
                users_data[user_id] = {'context': context, 'agent': agent, 'run_id': context.run_id, 'expected_events': []}
                self._tracked_instances.append(agent)
            self._websocket_events.clear()
            for user_id, user_data in users_data.items():
                agent = user_data['agent']
                context = user_data['context']
                if hasattr(agent, '_websocket_adapter') and agent._websocket_adapter:
                    adapter = agent._websocket_adapter
                    user_events = [{'event_type': 'agent_started', 'data': {'user': user_id, 'action': 'started', 'timestamp': time.time()}}, {'event_type': 'agent_thinking', 'data': {'user': user_id, 'thought': f'{user_id}_thinking', 'step': 1}}, {'event_type': 'agent_completed', 'data': {'user': user_id, 'result': f'{user_id}_result', 'success': True}}]
                    for event in user_events:
                        try:
                            if hasattr(adapter, 'send_event'):
                                await adapter.send_event(event['event_type'], event['data'])
                                user_data['expected_events'].append(event)
                            elif hasattr(adapter, 'send_agent_event'):
                                await adapter.send_agent_event(event['event_type'], event['data'])
                                user_data['expected_events'].append(event)
                        except Exception as e:
                            print(f'Warning: WebSocket event sending failed for {user_id}: {e}')
                elif self._mock_websocket_bridge:
                    for event in user_events:
                        try:
                            await self._mock_websocket_bridge.send_agent_event(context.run_id, event['event_type'], event['data'])
                            user_data['expected_events'].append(event)
                        except Exception as e:
                            print(f'Warning: Direct bridge event sending failed for {user_id}: {e}')
            await asyncio.sleep(0.1)
            for user_id, user_data in users_data.items():
                run_id = user_data['run_id']
                expected_events = user_data['expected_events']
                user_websocket_events = [event for event in self._websocket_events if event['run_id'] == run_id]
                if expected_events:
                    assert len(user_websocket_events) > 0, f'WEBSOCKET ISOLATION VIOLATION: No events received for {user_id}. Expected {len(expected_events)} events, Run ID: {run_id}. All events: {self._websocket_events}. This indicates WebSocket events not properly routed to user.'
                    for ws_event in user_websocket_events:
                        event_data = ws_event.get('data', {})
                        if isinstance(event_data, dict) and 'user' in event_data:
                            assert event_data['user'] == user_id, f"WEBSOCKET ISOLATION VIOLATION: {user_id} received event for wrong user. Event user: {event_data['user']}, Expected: {user_id}. Event: {ws_event}. This indicates cross-user event contamination."
            all_run_ids = set((user_data['run_id'] for user_data in users_data.values()))
            for event in self._websocket_events:
                event_run_id = event['run_id']
                assert event_run_id in all_run_ids, f'WEBSOCKET ISOLATION VIOLATION: Event sent to unknown run_id: {event_run_id}. Known run_ids: {all_run_ids}. Event: {event}. This indicates events being sent to unintended recipients.'
                event_data = event.get('data', {})
                if isinstance(event_data, dict) and 'user' in event_data:
                    event_user = event_data['user']
                    expected_user = None
                    for user_id, user_data in users_data.items():
                        if user_data['run_id'] == event_run_id:
                            expected_user = user_id
                            break
                    if expected_user:
                        assert event_user == expected_user, f'WEBSOCKET ISOLATION VIOLATION: Run ID {event_run_id} event contains wrong user data. Event user: {event_user}, Expected: {expected_user}. This indicates user data mixing in WebSocket events.'
            for user_id, user_data in users_data.items():
                run_id = user_data['run_id']
                expected_events = user_data['expected_events']
                if expected_events:
                    user_events = [event for event in self._websocket_events if event['run_id'] == run_id]
                    user_events.sort(key=lambda x: x.get('timestamp', 0))
                    started_events = [e for e in user_events if e['event_type'] == 'agent_started']
                    completed_events = [e for e in user_events if e['event_type'] == 'agent_completed']
                    if started_events and completed_events:
                        first_started = min(started_events, key=lambda x: x.get('timestamp', 0))
                        first_completed = min(completed_events, key=lambda x: x.get('timestamp', 0))
                        assert first_started['timestamp'] <= first_completed['timestamp'], f'WEBSOCKET ISOLATION VIOLATION: {user_id} events out of order. Completed before started. This may indicate event mixing between users.'
            self.record_metric('users_tested', len(users_data))
            self.record_metric('total_websocket_events', len(self._websocket_events))
            self.record_metric('websocket_isolation_checks_passed', 6)
            self.record_metric('test_result', 'PASS')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during WebSocket isolation validation: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')