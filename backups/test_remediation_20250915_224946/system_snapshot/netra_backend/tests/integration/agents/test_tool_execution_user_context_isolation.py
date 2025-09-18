"""Integration tests for tool execution user context isolation.

These tests validate that tool execution maintains strict user boundaries 
during concurrent operations and prevents cross-user data leakage.

Business Value: Platform/Internal - Security & Data Privacy
Ensures multi-user tool execution maintains isolation and prevents data breaches.

Test Coverage:
- Concurrent tool execution by different users
- User context boundary enforcement  
- Session isolation during tool operations
- WebSocket event isolation per user
- Tool state isolation and cleanup
- Error boundary isolation
"""
import asyncio
import pytest
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher, UnifiedToolDispatcherFactory, create_request_scoped_dispatcher
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus
from langchain_core.tools import BaseTool

class UserIsolationWebSocketManager:
    """Mock WebSocket manager that tracks events per user for isolation testing."""

    def __init__(self):
        self.user_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.connection_states: Dict[str, bool] = defaultdict(lambda: True)
        self.cross_user_violations: List[Dict[str, Any]] = []

    async def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Send event and track user isolation."""
        user_id = data.get('user_id')
        thread_id = data.get('thread_id')
        if not user_id:
            self.cross_user_violations.append({'violation_type': 'missing_user_id', 'event_type': event_type, 'data': data, 'timestamp': time.time()})
            return False
        if not self.connection_states[user_id]:
            return False
        event_record = {'event_type': event_type, 'data': data.copy(), 'timestamp': time.time(), 'user_id': user_id, 'thread_id': thread_id}
        self.user_events[user_id].append(event_record)
        return True

    def get_user_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Get events for specific user."""
        return self.user_events[user_id]

    def get_cross_user_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Get events that may have leaked from other users."""
        cross_user_events = []
        for other_user_id, events in self.user_events.items():
            if other_user_id != user_id:
                for event in events:
                    if event['data'].get('user_id') == user_id:
                        cross_user_events.append({'source_user': other_user_id, 'target_user': user_id, 'event': event})
        return cross_user_events

    def disconnect_user(self, user_id: str):
        """Simulate user disconnection."""
        self.connection_states[user_id] = False

    def clear_events(self):
        """Clear all tracked events."""
        self.user_events.clear()
        self.cross_user_violations.clear()

class IsolatedUserTool(BaseTool):
    """Tool that tracks user-specific execution state for isolation testing."""
    name: str = 'user_state_tool'
    description: str = 'Tool that maintains user-specific state'

    def __init__(self):
        super().__init__()
        self.user_executions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.user_data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.execution_count = 0
        self.cross_user_access_attempts = []

    def _run(self, operation: str, user_data: str=None, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(operation, user_data, **kwargs))

    async def _arun(self, operation: str, user_data: str=None, **kwargs) -> str:
        """Asynchronous execution with user state tracking."""
        self.execution_count += 1
        context = kwargs.get('context')
        user_id = context.user_id if context else 'unknown'
        execution_record = {'operation': operation, 'user_data': user_data, 'timestamp': time.time(), 'execution_id': self.execution_count, 'thread_id': context.thread_id if context else None}
        self.user_executions[user_id].append(execution_record)
        if operation == 'store_data':
            self.user_data[user_id][f'data_{len(self.user_data[user_id])}'] = user_data
            result = f'Stored data for user {user_id}: {user_data}'
        elif operation == 'get_data':
            user_stored_data = self.user_data[user_id]
            result = f'User {user_id} data: {list(user_stored_data.values())}'
        elif operation == 'cross_user_access':
            target_user = user_data
            if target_user in self.user_data and target_user != user_id:
                self.cross_user_access_attempts.append({'accessing_user': user_id, 'target_user': target_user, 'timestamp': time.time()})
                result = f'ERROR: Cross-user access blocked for user {user_id} -> {target_user}'
            else:
                result = f'No cross-user access attempted by {user_id}'
        else:
            result = f"Unknown operation '{operation}' for user {user_id}"
        await asyncio.sleep(0.001)
        return result

    def get_user_execution_count(self, user_id: str) -> int:
        """Get execution count for specific user."""
        return len(self.user_executions[user_id])

    def has_cross_user_violations(self) -> bool:
        """Check if any cross-user access attempts occurred."""
        return len(self.cross_user_access_attempts) > 0

class ToolExecutionUserContextIsolationTests(SSotAsyncTestCase):
    """Integration tests for user context isolation in tool execution."""

    def setUp(self):
        """Set up test environment with multiple user contexts."""
        super().setUp()
        self.user1_context = UserExecutionContext(user_id='isolation_user_001', run_id=f'run_001_{int(time.time() * 1000)}', thread_id='thread_001_isolation', agent_context={'plan_tier': 'early', 'roles': ['user'], 'tenant': 'company_a'})
        self.user2_context = UserExecutionContext(user_id='isolation_user_002', run_id=f'run_002_{int(time.time() * 1000)}', thread_id='thread_002_isolation', agent_context={'plan_tier': 'mid', 'roles': ['user'], 'tenant': 'company_b'})
        self.user3_context = UserExecutionContext(user_id='isolation_user_003', run_id=f'run_003_{int(time.time() * 1000)}', thread_id='thread_003_isolation', agent_context={'plan_tier': 'enterprise', 'roles': ['admin', 'user'], 'tenant': 'company_c'})
        self.websocket_manager = UserIsolationWebSocketManager()
        self.isolation_tool = IsolatedUserTool()

    async def tearDown(self):
        """Clean up user dispatchers."""
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user1_context.user_id)
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user2_context.user_id)
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user3_context.user_id)
        await super().tearDown()

    async def test_concurrent_user_tool_execution_isolation(self):
        """Test that concurrent tool execution by different users maintains isolation."""
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(user_context=self.user1_context, websocket_bridge=self.websocket_manager, tools=[self.isolation_tool])
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(user_context=self.user2_context, websocket_bridge=self.websocket_manager, tools=[self.isolation_tool])
        dispatcher3 = await UnifiedToolDispatcher.create_for_user(user_context=self.user3_context, websocket_bridge=self.websocket_manager, tools=[self.isolation_tool])
        tasks = [dispatcher1.execute_tool('user_state_tool', {'operation': 'store_data', 'user_data': 'sensitive_user1_data'}), dispatcher2.execute_tool('user_state_tool', {'operation': 'store_data', 'user_data': 'confidential_user2_info'}), dispatcher3.execute_tool('user_state_tool', {'operation': 'store_data', 'user_data': 'admin_user3_secrets'})]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            self.assertNotIsInstance(result, Exception)
            self.assertTrue(result.success)
        self.assertEqual(self.isolation_tool.get_user_execution_count(self.user1_context.user_id), 1)
        self.assertEqual(self.isolation_tool.get_user_execution_count(self.user2_context.user_id), 1)
        self.assertEqual(self.isolation_tool.get_user_execution_count(self.user3_context.user_id), 1)
        self.assertFalse(self.isolation_tool.has_cross_user_violations())
        self.assertIn('sensitive_user1_data', results[0].result)
        self.assertIn('confidential_user2_info', results[1].result)
        self.assertIn('admin_user3_secrets', results[2].result)
        self.assertNotIn('confidential_user2_info', results[0].result)
        self.assertNotIn('admin_user3_secrets', results[0].result)
        self.assertNotIn('sensitive_user1_data', results[1].result)
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
        await dispatcher3.cleanup()

    async def test_websocket_event_user_isolation(self):
        """Test that WebSocket events are properly isolated per user."""
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(user_context=self.user1_context, websocket_bridge=self.websocket_manager, tools=[self.isolation_tool])
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(user_context=self.user2_context, websocket_bridge=self.websocket_manager, tools=[self.isolation_tool])
        self.websocket_manager.clear_events()
        await dispatcher1.execute_tool('user_state_tool', {'operation': 'get_data'})
        await dispatcher2.execute_tool('user_state_tool', {'operation': 'get_data'})
        user1_events = self.websocket_manager.get_user_events(self.user1_context.user_id)
        user2_events = self.websocket_manager.get_user_events(self.user2_context.user_id)
        self.assertGreater(len(user1_events), 0)
        self.assertGreater(len(user2_events), 0)
        user1_cross_events = self.websocket_manager.get_cross_user_events(self.user1_context.user_id)
        user2_cross_events = self.websocket_manager.get_cross_user_events(self.user2_context.user_id)
        self.assertEqual(len(user1_cross_events), 0, "User 1 should not receive User 2's events")
        self.assertEqual(len(user2_cross_events), 0, "User 2 should not receive User 1's events")
        self.assertEqual(len(self.websocket_manager.cross_user_violations), 0)
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()

    async def test_user_session_boundary_enforcement(self):
        """Test that user session boundaries are properly enforced."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=self.user1_context, websocket_bridge=self.websocket_manager, tools=[self.isolation_tool])
        result = await dispatcher.execute_tool('user_state_tool', {'operation': 'store_data', 'user_data': f'session_data_{self.user1_context.session_id}'})
        self.assertTrue(result.success)
        user_executions = self.isolation_tool.user_executions[self.user1_context.user_id]
        self.assertEqual(len(user_executions), 1)
        execution_record = user_executions[0]
        self.assertIn(self.user1_context.session_id, execution_record['user_data'])
        await dispatcher.cleanup()

    async def test_error_boundary_isolation(self):
        """Test that errors in one user's tools don't affect other users."""

        class FailingTool(BaseTool):
            name: str = 'failing_tool'
            description: str = 'Tool that always fails'

            def _run(self, **kwargs):
                return asyncio.run(self._arun(**kwargs))

            async def _arun(self, **kwargs):
                raise RuntimeError('Simulated tool failure')
        failing_tool = FailingTool()
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(user_context=self.user1_context, websocket_bridge=self.websocket_manager, tools=[failing_tool])
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(user_context=self.user2_context, websocket_bridge=self.websocket_manager, tools=[self.isolation_tool])
        task1 = asyncio.create_task(dispatcher1.execute_tool('failing_tool', {}))
        task2 = asyncio.create_task(dispatcher2.execute_tool('user_state_tool', {'operation': 'store_data', 'user_data': 'successful_execution_despite_other_user_error'}))
        results = await asyncio.gather(task1, task2, return_exceptions=True)
        result1 = results[0]
        self.assertFalse(result1.success)
        self.assertIn('Simulated tool failure', result1.error)
        result2 = results[1]
        self.assertTrue(result2.success)
        self.assertIn('successful_execution_despite_other_user_error', result2.result)
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()

    async def test_high_concurrency_user_isolation(self):
        """Test user isolation under high concurrency load."""
        num_users = 10
        operations_per_user = 5
        user_contexts = []
        dispatchers = []
        for i in range(num_users):
            context = UserExecutionContext(user_id=f'load_user_{i:03d}', run_id=f'load_run_{i:03d}_{int(time.time() * 1000)}', thread_id=f'load_thread_{i:03d}', agent_context={'load_test': True, 'user_index': i})
            user_contexts.append(context)
            dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=context, websocket_bridge=self.websocket_manager, tools=[self.isolation_tool])
            dispatchers.append(dispatcher)
        all_tasks = []
        for i, dispatcher in enumerate(dispatchers):
            for op_num in range(operations_per_user):
                task = dispatcher.execute_tool('user_state_tool', {'operation': 'store_data', 'user_data': f'user_{i}_operation_{op_num}_data'})
                all_tasks.append((i, op_num, task))
        results = await asyncio.gather(*[task for _, _, task in all_tasks], return_exceptions=True)
        success_count = 0
        for result in results:
            if not isinstance(result, Exception) and result.success:
                success_count += 1
        expected_operations = num_users * operations_per_user
        self.assertEqual(success_count, expected_operations, f'Expected {expected_operations} successful operations, got {success_count}')
        for i, context in enumerate(user_contexts):
            user_execution_count = self.isolation_tool.get_user_execution_count(context.user_id)
            self.assertEqual(user_execution_count, operations_per_user, f'User {i} should have {operations_per_user} executions, got {user_execution_count}')
        self.assertFalse(self.isolation_tool.has_cross_user_violations())
        for dispatcher in dispatchers:
            await dispatcher.cleanup()

    async def test_user_disconnect_isolation(self):
        """Test that user disconnection doesn't affect other users' tool execution."""
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(user_context=self.user1_context, websocket_bridge=self.websocket_manager, tools=[self.isolation_tool])
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(user_context=self.user2_context, websocket_bridge=self.websocket_manager, tools=[self.isolation_tool])
        result1 = await dispatcher1.execute_tool('user_state_tool', {'operation': 'store_data', 'user_data': 'before_disconnect'})
        self.assertTrue(result1.success)
        self.websocket_manager.disconnect_user(self.user1_context.user_id)
        result2 = await dispatcher2.execute_tool('user_state_tool', {'operation': 'store_data', 'user_data': 'after_user1_disconnect'})
        self.assertTrue(result2.success)
        result1_after = await dispatcher1.execute_tool('user_state_tool', {'operation': 'get_data'})
        self.assertTrue(result1_after.success)
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')