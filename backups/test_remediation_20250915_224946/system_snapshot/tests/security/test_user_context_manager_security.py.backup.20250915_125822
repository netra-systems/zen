"""Security Tests for UserContextManager - TDD Implementation

This test suite validates the critical security isolation mechanisms required for
UserContextManager, following Test-Driven Development principles.

These tests are designed to FAIL initially (UserContextManager does not exist yet)
and then PASS once the implementation is created with proper security boundaries.

Business Value Justification (BVJ):
- Segment: Enterprise (highest security requirements)
- Business Goal: Prevent data leakage between users ($500K+ ARR protection)
- Value Impact: Validates multi-tenant isolation preventing security breaches
- Revenue Impact: Critical for compliance requirements enabling enterprise sales

Test Categories:
1. Multi-User Isolation - Prevent cross-contamination
2. Memory Isolation - Prevent shared state
3. Context Lifecycle - Proper cleanup
4. Error Handling - Fail-safe patterns
5. Audit Trail - Compliance tracking
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List
try:
    from netra_backend.app.services.user_execution_context import UserContextManager
    USERCONTEXTMANAGER_EXISTS = True
except ImportError as e:
    USERCONTEXTMANAGER_EXISTS = False
    UserContextManager = None
    IMPORT_ERROR = str(e)
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError, ContextIsolationError, create_isolated_execution_context
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestUserContextManagerSecurity(SSotBaseTestCase):
    """Security-focused tests for UserContextManager implementation.
    
    These tests validate that UserContextManager provides complete isolation
    between different user contexts, preventing any form of data leakage.
    """

    def setup_method(self, method=None):
        """Set up test fixtures."""
        super().setup_method(method)
        if not USERCONTEXTMANAGER_EXISTS:
            self.skipTest(f'UserContextManager not implemented yet. Import error: {IMPORT_ERROR}')
        self.user_a = 'user_a_security_test_123'
        self.user_b = 'user_b_security_test_456'
        self.user_c = 'user_c_security_test_789'
        self.thread_a = 'thread_a_security'
        self.thread_b = 'thread_b_security'
        self.run_a = 'run_a_security'
        self.run_b = 'run_b_security'

    def test_user_context_manager_initialization(self):
        """Test that UserContextManager initializes with proper security defaults."""
        manager = UserContextManager()
        self.assertIsNotNone(manager)
        self.assertTrue(hasattr(manager, 'get_context'))
        self.assertTrue(hasattr(manager, 'set_context'))
        self.assertTrue(hasattr(manager, 'clear_context'))
        self.assertTrue(hasattr(manager, 'validate_isolation'))
        active_contexts = manager.get_active_contexts()
        self.assertIsInstance(active_contexts, dict)
        self.assertEqual(len(active_contexts), 0)

    def test_context_isolation_between_users(self):
        """Test complete isolation between different user contexts."""
        manager = UserContextManager()
        context_a = UserExecutionContext.from_request(user_id=self.user_a, thread_id=self.thread_a, run_id=self.run_a, agent_context={'sensitive_data': 'user_a_secret'})
        context_b = UserExecutionContext.from_request(user_id=self.user_b, thread_id=self.thread_b, run_id=self.run_b, agent_context={'sensitive_data': 'user_b_secret'})
        manager.set_context(self.user_a, context_a)
        manager.set_context(self.user_b, context_b)
        retrieved_a = manager.get_context(self.user_a)
        retrieved_b = manager.get_context(self.user_b)
        self.assertEqual(retrieved_a.user_id, self.user_a)
        self.assertEqual(retrieved_b.user_id, self.user_b)
        self.assertNotEqual(retrieved_a.agent_context, retrieved_b.agent_context)
        self.assertEqual(retrieved_a.agent_context['sensitive_data'], 'user_a_secret')
        self.assertEqual(retrieved_b.agent_context['sensitive_data'], 'user_b_secret')

    def test_memory_isolation_validation(self):
        """Test that contexts don't share memory references."""
        manager = UserContextManager()
        shared_data = {'counter': 0, 'items': []}
        context_a = UserExecutionContext.from_request(user_id=self.user_a, thread_id=self.thread_a, run_id=self.run_a, agent_context={'shared_data': shared_data})
        manager.set_context(self.user_a, context_a)
        retrieved = manager.get_context(self.user_a)
        retrieved.agent_context['shared_data']['counter'] = 42
        retrieved.agent_context['shared_data']['items'].append('test')
        context_a2 = UserExecutionContext.from_request(user_id=self.user_a, thread_id='thread_a2', run_id='run_a2', agent_context={'shared_data': {'counter': 0, 'items': []}})
        manager.set_context(f'{self.user_a}_req2', context_a2)
        retrieved_a2 = manager.get_context(f'{self.user_a}_req2')
        self.assertEqual(retrieved_a2.agent_context['shared_data']['counter'], 0)
        self.assertEqual(len(retrieved_a2.agent_context['shared_data']['items']), 0)

    def test_context_cleanup_prevents_leakage(self):
        """Test that context cleanup prevents memory leaks and data persistence."""
        manager = UserContextManager()
        sensitive_context = UserExecutionContext.from_request(user_id=self.user_a, thread_id=self.thread_a, run_id=self.run_a, agent_context={'api_key': 'secret_key_123', 'user_data': {'ssn': '123-45-6789', 'credit_card': '1234-5678-9012'}})
        manager.set_context(self.user_a, sensitive_context)
        self.assertIsNotNone(manager.get_context(self.user_a))
        manager.clear_context(self.user_a)
        with self.assertRaises((KeyError, ValueError, ContextIsolationError)):
            manager.get_context(self.user_a)
        active_contexts = manager.get_active_contexts()
        self.assertNotIn(self.user_a, active_contexts)

    def test_concurrent_access_isolation(self):
        """Test isolation under concurrent access patterns."""
        manager = UserContextManager()
        results = {}
        errors = []

        async def user_operation(user_id: str, operation_id: int):
            """Simulate concurrent user operations."""
            try:
                context = UserExecutionContext.from_request(user_id=user_id, thread_id=f'thread_{user_id}_{operation_id}', run_id=f'run_{user_id}_{operation_id}', agent_context={'operation_id': operation_id, 'user_secret': f'secret_{user_id}'})
                manager.set_context(f'{user_id}_{operation_id}', context)
                await asyncio.sleep(0.01)
                retrieved = manager.get_context(f'{user_id}_{operation_id}')
                results[f'{user_id}_{operation_id}'] = retrieved.agent_context['operation_id']
                manager.clear_context(f'{user_id}_{operation_id}')
            except Exception as e:
                errors.append(f'Error in {user_id}_{operation_id}: {e}')

        async def run_concurrent_test():
            """Run concurrent operations for multiple users."""
            tasks = []
            for user_id in [self.user_a, self.user_b, self.user_c]:
                for op_id in range(5):
                    tasks.append(user_operation(user_id, op_id))
            await asyncio.gather(*tasks)
        asyncio.run(run_concurrent_test())
        self.assertEqual(len(errors), 0, f'Concurrent errors: {errors}')
        self.assertEqual(len(results), 15)
        for user_id in [self.user_a, self.user_b, self.user_c]:
            for op_id in range(5):
                key = f'{user_id}_{op_id}'
                self.assertEqual(results[key], op_id)

    def test_invalid_context_rejection(self):
        """Test that invalid contexts are properly rejected."""
        manager = UserContextManager()
        with self.assertRaises((ValueError, InvalidContextError)):
            manager.set_context(self.user_a, None)
        with self.assertRaises((ValueError, InvalidContextError)):
            invalid_context = UserExecutionContext.from_request(user_id='', thread_id=self.thread_a, run_id=self.run_a)
            manager.set_context('', invalid_context)
        with self.assertRaises(InvalidContextError):
            placeholder_context = UserExecutionContext.from_request(user_id='placeholder', thread_id=self.thread_a, run_id=self.run_a)
            manager.set_context('placeholder', placeholder_context)

    def test_audit_trail_security(self):
        """Test that audit trails are maintained securely."""
        manager = UserContextManager()
        context = UserExecutionContext.from_request(user_id=self.user_a, thread_id=self.thread_a, run_id=self.run_a, audit_metadata={'security_level': 'high', 'compliance_required': True})
        manager.set_context(self.user_a, context)
        self.assertTrue(hasattr(manager, 'get_audit_trail'))
        audit_trail = manager.get_audit_trail(self.user_a)
        self.assertIn('context_set_at', audit_trail)
        self.assertIn('user_id', audit_trail)
        self.assertIn('security_level', audit_trail)
        self.assertEqual(audit_trail['security_level'], 'high')
        audit_b = manager.get_audit_trail(self.user_b)
        self.assertIsNone(audit_b)

    def test_context_validation_enforcement(self):
        """Test that context validation is enforced at all entry points."""
        manager = UserContextManager()
        valid_context = UserExecutionContext.from_request(user_id=self.user_a, thread_id=self.thread_a, run_id=self.run_a)
        with patch.object(valid_context, 'verify_isolation', side_effect=ContextIsolationError('Test isolation failure')):
            with self.assertRaises(ContextIsolationError):
                manager.set_context(self.user_a, valid_context)

    def test_resource_limits_enforcement(self):
        """Test that UserContextManager enforces resource limits."""
        manager = UserContextManager()
        max_contexts = getattr(manager, 'MAX_CONTEXTS_PER_USER', 10)
        for i in range(max_contexts):
            context = UserExecutionContext.from_request(user_id=self.user_a, thread_id=f'thread_{i}', run_id=f'run_{i}')
            manager.set_context(f'{self.user_a}_{i}', context)
        with self.assertRaises((ValueError, RuntimeError)):
            excess_context = UserExecutionContext.from_request(user_id=self.user_a, thread_id='thread_excess', run_id='run_excess')
            manager.set_context(f'{self.user_a}_excess', excess_context)

    def test_context_expiration_security(self):
        """Test that contexts expire and are cleaned up automatically."""
        manager = UserContextManager()
        context = UserExecutionContext.from_request(user_id=self.user_a, thread_id=self.thread_a, run_id=self.run_a)
        manager.set_context(self.user_a, context, ttl_seconds=0.1)
        self.assertIsNotNone(manager.get_context(self.user_a))
        import time
        time.sleep(0.2)
        with self.assertRaises((KeyError, ValueError)):
            manager.get_context(self.user_a)

    @pytest.mark.security
    def test_no_cross_user_contamination(self):
        """Critical security test: Verify absolutely no cross-user data contamination."""
        manager = UserContextManager()
        users = [f'user_security_{i}' for i in range(10)]
        contexts = {}
        for i, user_id in enumerate(users):
            context = UserExecutionContext.from_request(user_id=user_id, thread_id=f'thread_{i}', run_id=f'run_{i}', agent_context={'user_index': i, 'secret_data': f'secret_for_user_{i}', 'shared_key': 'common_value', 'permissions': [f'perm_{i}', f'perm_{i + 1}']})
            contexts[user_id] = context
            manager.set_context(user_id, context)
        for i, user_id in enumerate(users):
            retrieved = manager.get_context(user_id)
            self.assertEqual(retrieved.user_id, user_id)
            self.assertEqual(retrieved.agent_context['user_index'], i)
            self.assertEqual(retrieved.agent_context['secret_data'], f'secret_for_user_{i}')
            self.assertIn(f'perm_{i}', retrieved.agent_context['permissions'])
            for j, other_user in enumerate(users):
                if i != j:
                    self.assertNotIn(f'secret_for_user_{j}', str(retrieved.agent_context))

class TestUserContextManagerIntegrationSecurity(SSotBaseTestCase):
    """Integration security tests with UserExecutionContext."""

    async def test_websocket_isolation_security(self):
        """Test WebSocket connection isolation through UserContextManager."""
        manager = UserContextManager()
        context_a = UserExecutionContext.from_request(user_id=self.user_a, thread_id='thread_ws_a', run_id='run_ws_a', websocket_client_id='ws_client_a')
        context_b = UserExecutionContext.from_request(user_id=self.user_b, thread_id='thread_ws_b', run_id='run_ws_b', websocket_client_id='ws_client_b')
        manager.set_context(self.user_a, context_a)
        manager.set_context(self.user_b, context_b)
        retrieved_a = manager.get_context(self.user_a)
        retrieved_b = manager.get_context(self.user_b)
        self.assertEqual(retrieved_a.websocket_client_id, 'ws_client_a')
        self.assertEqual(retrieved_b.websocket_client_id, 'ws_client_b')
        self.assertNotEqual(retrieved_a.websocket_client_id, retrieved_b.websocket_client_id)

    async def test_database_session_isolation(self):
        """Test database session isolation through UserContextManager."""
        manager = UserContextManager()
        db_session_a = AsyncMock()
        db_session_a.user_id = self.user_a
        db_session_b = AsyncMock()
        db_session_b.user_id = self.user_b
        context_a = UserExecutionContext.from_request(user_id=self.user_a, thread_id='thread_db_a', run_id='run_db_a', db_session=db_session_a)
        context_b = UserExecutionContext.from_request(user_id=self.user_b, thread_id='thread_db_b', run_id='run_db_b', db_session=db_session_b)
        manager.set_context(self.user_a, context_a)
        manager.set_context(self.user_b, context_b)
        retrieved_a = manager.get_context(self.user_a)
        retrieved_b = manager.get_context(self.user_b)
        self.assertEqual(retrieved_a.db_session.user_id, self.user_a)
        self.assertEqual(retrieved_b.db_session.user_id, self.user_b)
        self.assertNotEqual(id(retrieved_a.db_session), id(retrieved_b.db_session))

    def test_factory_integration_security(self):
        """Test integration with UserExecutionContext factory methods."""
        manager = UserContextManager()
        with patch('netra_backend.app.services.user_execution_context.create_isolated_execution_context') as mock_factory:
            mock_context = UserExecutionContext.from_request(user_id=self.user_a, thread_id='factory_thread', run_id='factory_run')
            mock_factory.return_value = mock_context
            self.assertTrue(hasattr(manager, 'create_managed_context'))
            managed_context = manager.create_managed_context(user_id=self.user_a, request_id='factory_request')
            self.assertEqual(managed_context.user_id, self.user_a)
            mock_factory.assert_called_once()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')