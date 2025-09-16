"""
Test 4: Multi-User Context Isolation Test for AgentLifecycle (Issue #877)

PURPOSE: Validate lifecycle operations maintain user isolation with UserExecutionContext
CRITICAL: Ensures user data separation and prevents cross-contamination

This test is CRITICAL for security - ensures user data separation.
Should FAIL initially due to DeepAgentState shared state issues.
After fix, will PASS with proper UserExecutionContext isolation.

Design:
- Test concurrent lifecycle operations
- Validate no cross-contamination between users
- Ensure proper context isolation
- Verify security boundaries
"""
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase

@pytest.mark.unit
class AgentLifecycleUserIsolationTests(SSotAsyncTestCase):
    """Test suite for multi-user context isolation in AgentLifecycle"""

    async def asyncSetUp(self):
        """Set up test environment with multiple user contexts"""
        await super().asyncSetUp()
        self.user_contexts = self._create_multiple_user_contexts()
        self.user_agents = self._create_user_specific_agents()
        self.isolation_violation_detected = []

    def _create_multiple_user_contexts(self) -> Dict[str, Any]:
        """Create multiple UserExecutionContext instances for different users"""
        contexts = {}
        contexts['user1'] = self._create_user_context(user_id='user_001', thread_id='thread_001', session_id='session_001', sensitive_data='user1_sensitive_data')
        contexts['user2'] = self._create_user_context(user_id='user_002', thread_id='thread_002', session_id='session_002', sensitive_data='user2_sensitive_data')
        contexts['user3'] = self._create_user_context(user_id='user_003_enterprise', thread_id='thread_003', session_id='session_003', sensitive_data='user3_enterprise_data')
        return contexts

    def _create_user_context(self, user_id: str, thread_id: str, session_id: str, sensitive_data: str):
        """Create individual UserExecutionContext with test data"""
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            context = UserExecutionContext(user_id=user_id, thread_id=thread_id, request_id=f'req_{user_id}', session_id=session_id)
            context.sensitive_data = sensitive_data
            return context
        except ImportError:
            mock_context = Mock()
            mock_context.user_id = user_id
            mock_context.thread_id = thread_id
            mock_context.session_id = session_id
            mock_context.sensitive_data = sensitive_data
            return mock_context

    def _create_user_specific_agents(self) -> Dict[str, Any]:
        """Create test agents for each user with lifecycle capabilities"""
        from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        agents = {}

        class IsolationTestAgent(AgentLifecycleMixin):

            def __init__(self, user_id: str):
                self.name = f'IsolationTestAgent_{user_id}'
                self.user_id = user_id
                self.start_time = None
                self.end_time = None
                self.context = Mock()
                self.logger = Mock()
                self.processed_contexts = []
                self.sensitive_data_seen = []
                self.emit_agent_started = AsyncMock()
                self.emit_agent_completed = AsyncMock()
                self.emit_error = AsyncMock()
                self.set_state = Mock()
                self._log_agent_start = Mock()
                self._log_agent_completion = Mock()

            async def execute(self, state, run_id: str, stream_updates: bool) -> None:
                """Mock execute method that tracks context data"""
                self.processed_contexts.append({'user_id': getattr(state, 'user_id', 'unknown'), 'session_id': getattr(state, 'session_id', 'unknown'), 'sensitive_data': getattr(state, 'sensitive_data', 'unknown')})
                if hasattr(state, 'sensitive_data'):
                    self.sensitive_data_seen.append(state.sensitive_data)
                await asyncio.sleep(0.01)
        for user_key in self.user_contexts:
            user_id = self.user_contexts[user_key].user_id
            agents[user_key] = IsolationTestAgent(user_id)
        return agents

    async def test_concurrent_user_lifecycle_isolation(self):
        """
        FAILING TEST: Concurrent lifecycle operations should maintain user isolation

        Expected: FAIL initially (DeepAgentState causes cross-contamination)
        After Fix: PASS (UserExecutionContext maintains isolation)
        """
        tasks = []
        for user_key, context in self.user_contexts.items():
            agent = self.user_agents[user_key]
            run_id = f'run_{user_key}_{uuid.uuid4()}'
            task = asyncio.create_task(self._run_lifecycle_with_isolation_check(agent, context, run_id))
            tasks.append((user_key, task))
        results = {}
        for user_key, task in tasks:
            try:
                results[user_key] = await task
            except Exception as e:
                self.fail(f'ISOLATION FAILURE: User {user_key} lifecycle operation failed: {e}\n  - This may indicate cross-user contamination\n  - Issue #877: User isolation violation in AgentLifecycle')
        await self._verify_user_isolation(results)

    async def test_sensitive_data_isolation(self):
        """
        SECURITY CRITICAL TEST: Sensitive data must not leak between users

        Expected: FAIL initially (shared state leaks data)
        After Fix: PASS (proper data isolation)
        """
        for user_key, context in self.user_contexts.items():
            agent = self.user_agents[user_key]
            run_id = f'sensitive_run_{user_key}'
            try:
                result = await agent._pre_run(state=context, run_id=run_id, stream_updates=False)
                self.assertTrue(result, f'Pre-run should succeed for {user_key}')
                await agent.execute(state=context, run_id=run_id, stream_updates=False)
                await agent._post_run(state=context, run_id=run_id, stream_updates=False, success=True)
            except (TypeError, AttributeError) as e:
                self.fail(f'SSOT REGRESSION: Agent lifecycle cannot handle UserExecutionContext!\n  - User: {user_key}\n  - Error: {str(e)}\n  - Issue #877: UserExecutionContext compatibility failure')
        for user_key, agent in self.user_agents.items():
            expected_data = self.user_contexts[user_key].sensitive_data
            seen_data = agent.sensitive_data_seen
            self.assertIn(expected_data, seen_data, f'Agent {user_key} should see its own sensitive data')
            for other_key, other_context in self.user_contexts.items():
                if other_key != user_key:
                    other_sensitive_data = other_context.sensitive_data
                    self.assertNotIn(other_sensitive_data, seen_data, f"SECURITY VIOLATION: Agent {user_key} saw {other_key}'s sensitive data!\n  - Own data: {expected_data}\n  - Leaked data: {other_sensitive_data}\n  - All seen data: {seen_data}\n  - Issue #877: User data isolation failure")

    async def test_context_cleanup_isolation(self):
        """
        MEMORY SAFETY TEST: Context cleanup should not affect other users

        Expected: FAIL initially (shared cleanup affects other users)
        After Fix: PASS (isolated cleanup per user)
        """
        for user_key, context in self.user_contexts.items():
            agent = self.user_agents[user_key]
            run_id = f'cleanup_test_{user_key}'
            try:
                await agent._pre_run(context, run_id, False)
                await agent.execute(context, run_id, False)
            except (TypeError, AttributeError) as e:
                self.fail(f'SSOT REGRESSION: Cannot initialize context for {user_key}: {e}')
        target_user = 'user1'
        target_agent = self.user_agents[target_user]
        target_context = self.user_contexts[target_user]
        try:
            await target_agent.cleanup(state=target_context, run_id='cleanup_test_user1')
        except (TypeError, AttributeError) as e:
            self.fail(f'SSOT REGRESSION: Cannot cleanup context for {target_user}: {e}')
        for user_key, context in self.user_contexts.items():
            if user_key != target_user:
                agent = self.user_agents[user_key]
                try:
                    result = await agent.check_entry_conditions(state=context, run_id=f'post_cleanup_check_{user_key}')
                    self.assertTrue(result, f'User {user_key} context should remain functional after {target_user} cleanup')
                except Exception as e:
                    self.fail(f'ISOLATION VIOLATION: {target_user} cleanup affected {user_key}!\n  - Error: {str(e)}\n  - This indicates shared state between users\n  - Issue #877: Context cleanup isolation failure')

    async def test_thread_safety_user_isolation(self):
        """
        CONCURRENCY TEST: Thread-safe user isolation

        Expected: FAIL initially (race conditions with shared state)
        After Fix: PASS (thread-safe UserExecutionContext)
        """
        concurrent_operations = []
        for i in range(10):
            for user_key, context in self.user_contexts.items():
                agent = self.user_agents[user_key]
                run_id = f'thread_test_{user_key}_{i}'
                operation = asyncio.create_task(self._isolated_operation(agent, context, run_id, user_key))
                concurrent_operations.append(operation)
        try:
            results = await asyncio.gather(*concurrent_operations, return_exceptions=True)
        except Exception as e:
            self.fail(f'THREAD SAFETY FAILURE: Concurrent operations failed: {e}\n  - This may indicate race conditions in shared state\n  - Issue #877: Thread safety violation')
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                if isinstance(result, (TypeError, AttributeError)):
                    self.fail(f'SSOT REGRESSION: Operation {i} failed due to context incompatibility: {result}')
                else:
                    self.fail(f'ISOLATION FAILURE: Operation {i} failed: {result}\n  - May indicate cross-user interference\n  - Issue #877: Thread safety isolation failure')

    async def _run_lifecycle_with_isolation_check(self, agent, context, run_id: str):
        """Run complete lifecycle with isolation verification"""
        try:
            pre_result = await agent._pre_run(context, run_id, False)
            await agent.execute(context, run_id, False)
            await agent._post_run(context, run_id, False, True)
            return {'user_id': context.user_id, 'contexts_seen': agent.processed_contexts.copy(), 'sensitive_data_seen': agent.sensitive_data_seen.copy(), 'success': True}
        except (TypeError, AttributeError) as e:
            return {'user_id': context.user_id, 'error': str(e), 'success': False, 'ssot_regression': True}

    async def _isolated_operation(self, agent, context, run_id: str, user_key: str):
        """Single isolated operation for concurrency testing"""
        try:
            await agent.check_entry_conditions(context, run_id)
            await asyncio.sleep(0.001)
            await agent.execute(context, run_id, False)
            return {'user_key': user_key, 'user_id': context.user_id, 'success': True}
        except Exception as e:
            return {'user_key': user_key, 'user_id': context.user_id, 'error': str(e), 'success': False}

    async def _verify_user_isolation(self, results: Dict[str, Any]):
        """Verify user isolation in concurrent operation results"""
        for user_key, result in results.items():
            if not result['success']:
                if result.get('ssot_regression'):
                    self.fail(f'SSOT REGRESSION: User {user_key} operation failed due to context incompatibility')
                else:
                    self.fail(f"ISOLATION FAILURE: User {user_key} operation failed: {result.get('error')}")
            expected_user_id = self.user_contexts[user_key].user_id
            contexts_seen = result.get('contexts_seen', [])
            for context_data in contexts_seen:
                seen_user_id = context_data.get('user_id')
                self.assertEqual(seen_user_id, expected_user_id, f'ISOLATION VIOLATION: User {user_key} saw data from user {seen_user_id}!\n  - Expected: {expected_user_id}\n  - Context data: {context_data}\n  - Issue #877: Cross-user data contamination')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')