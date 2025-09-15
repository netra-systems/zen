"""
Singleton Enforcement Tests for AgentExecutionTracker SSOT Consolidation

This test validates that AgentExecutionTracker enforces proper singleton 
pattern usage and prevents direct instantiation that bypasses SSOT.

Business Value:
- Segment: Platform/Internal
- Goal: Stability & User Isolation
- Value Impact: Prevents state corruption in $500K+ ARR chat functionality
- Strategic Impact: Essential for multi-user system reliability
"""
import pytest
import threading
import asyncio
import time
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestSingletonEnforcement(SSotBaseTestCase):
    """
    Test singleton enforcement for AgentExecutionTracker.
    
    These tests ensure proper factory pattern usage and prevent
    direct instantiation that would bypass SSOT compliance.
    """

    def test_direct_instantiation_should_fail(self):
        """
        Should FAIL - Direct AgentExecutionTracker() instantiation should be blocked.
        
        CURRENT EXPECTED RESULT: FAIL (Direct instantiation allowed)
        POST-CONSOLIDATION EXPECTED: PASS (Direct instantiation blocked)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            try:
                tracker = AgentExecutionTracker()
                pytest.fail('SSOT VIOLATION: Direct AgentExecutionTracker() instantiation is allowed. Should only be accessible through get_execution_tracker() factory method to ensure singleton behavior and user isolation.')
            except (TypeError, RuntimeError, ValueError) as e:
                if 'factory' in str(e).lower() or 'singleton' in str(e).lower():
                    pass
                else:
                    pytest.fail(f'AgentExecutionTracker blocked instantiation but with wrong error: {e}')
        except ImportError:
            pytest.fail('AgentExecutionTracker not available for singleton testing')

    def test_factory_method_should_work(self):
        """
        Should PASS - get_execution_tracker() factory method should work.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Factory method not implemented)
        POST-CONSOLIDATION EXPECTED: PASS (Factory method provides proper access)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
            tracker = get_execution_tracker()
            assert tracker is not None, 'Factory method should return tracker instance'
            tracker2 = get_execution_tracker()
            assert tracker is tracker2, 'Factory method should return same singleton instance'
        except ImportError:
            pytest.fail('get_execution_tracker factory method not available. This should be the only way to access AgentExecutionTracker.')

    def test_factory_provides_user_isolated_instances(self):
        """
        Should PASS - Factory should provide user-isolated tracker instances.
        
        CURRENT EXPECTED RESULT: MAY FAIL (User isolation not implemented)
        POST-CONSOLIDATION EXPECTED: PASS (Proper user isolation through factory)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
            user1_tracker = get_execution_tracker(user_context={'user_id': 'user1'})
            user2_tracker = get_execution_tracker(user_context={'user_id': 'user2'})
            assert user1_tracker is not None
            assert user2_tracker is not None
            if hasattr(user1_tracker, 'create_execution') and hasattr(user2_tracker, 'create_execution'):
                exec1 = user1_tracker.create_execution(agent_name='test_agent', thread_id='thread1', user_id='user1')
                exec2 = user2_tracker.create_execution(agent_name='test_agent', thread_id='thread2', user_id='user2')
                if hasattr(user1_tracker, 'get_user_executions'):
                    user1_executions = user1_tracker.get_user_executions('user1')
                    user2_executions = user2_tracker.get_user_executions('user2')
                    assert exec1 in user1_executions, 'User1 should see their execution'
                    assert exec2 not in user1_executions, "User1 should not see User2's execution"
                    assert exec2 in user2_executions, 'User2 should see their execution'
                    assert exec1 not in user2_executions, "User2 should not see User1's execution"
        except ImportError:
            pytest.fail('Factory method with user context not available')

    def test_singleton_behavior_across_threads(self):
        """
        Test singleton behavior is maintained across multiple threads.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Thread safety not guaranteed)
        POST-CONSOLIDATION EXPECTED: PASS (Thread-safe singleton behavior)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
        except ImportError:
            self.skip('get_execution_tracker not available for thread testing')
        tracker_instances = []
        errors = []

        def get_tracker_in_thread():
            try:
                tracker = get_execution_tracker()
                tracker_instances.append(id(tracker))
            except Exception as e:
                errors.append(str(e))
        threads = []
        for i in range(10):
            thread = threading.Thread(target=get_tracker_in_thread)
            threads.append(thread)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        if errors:
            pytest.fail(f'Thread safety errors: {errors}')
        unique_instances = set(tracker_instances)
        if len(unique_instances) != 1:
            pytest.fail(f'Singleton violation: {len(unique_instances)} different instances created across threads. Should be exactly 1 singleton instance.')

    def test_no_global_state_leakage_between_users(self):
        """
        Test that singleton doesn't leak state between users.
        
        CURRENT EXPECTED RESULT: MAY FAIL (State leakage exists)
        POST-CONSOLIDATION EXPECTED: PASS (No state leakage)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
        except ImportError:
            self.skip('get_execution_tracker not available for isolation testing')
        tracker = get_execution_tracker(user_context={'user_id': 'user1'})
        if hasattr(tracker, 'create_execution'):
            exec1 = tracker.create_execution(agent_name='isolation_test', thread_id='user1_thread', user_id='user1')
            tracker2 = get_execution_tracker(user_context={'user_id': 'user2'})
            if hasattr(tracker2, 'get_execution'):
                try:
                    user2_view = tracker2.get_execution(exec1)
                    if user2_view is not None:
                        pytest.fail("ISOLATION VIOLATION: User2 can access User1's execution. Singleton pattern must enforce user isolation.")
                except (KeyError, ValueError, PermissionError):
                    pass

    def test_constructor_privacy_enforcement(self):
        """
        Test that AgentExecutionTracker constructor is properly private.
        
        CURRENT EXPECTED RESULT: FAIL (Constructor is public)
        POST-CONSOLIDATION EXPECTED: PASS (Constructor is private/protected)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            init_method = AgentExecutionTracker.__init__
            import inspect
            source = inspect.getsource(init_method)
            privacy_indicators = ['raise RuntimeError', 'raise TypeError', 'raise ValueError', 'factory', 'get_execution_tracker', 'private', 'singleton']
            has_privacy_enforcement = any((indicator in source for indicator in privacy_indicators))
            if not has_privacy_enforcement:
                pytest.fail('SSOT VIOLATION: AgentExecutionTracker constructor does not enforce privacy. Should prevent direct instantiation to ensure singleton pattern.')
        except ImportError:
            pytest.fail('AgentExecutionTracker not available for constructor privacy testing')

    def test_factory_method_parameter_validation(self):
        """
        Test that factory method properly validates parameters.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Parameter validation incomplete)
        POST-CONSOLIDATION EXPECTED: PASS (Proper parameter validation)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
        except ImportError:
            self.skip('get_execution_tracker not available for parameter testing')
        validation_issues = []
        try:
            tracker = get_execution_tracker(user_context='invalid_string')
            validation_issues.append('Factory accepts invalid user_context string')
        except (TypeError, ValueError):
            pass
        try:
            tracker = get_execution_tracker(user_context={'invalid': 'context'})
            if hasattr(tracker, 'create_execution'):
                tracker.create_execution(agent_name='test', thread_id='test', user_id='test')
                validation_issues.append('Factory allows operations with invalid user context')
        except (KeyError, ValueError, RuntimeError):
            pass
        try:
            tracker = get_execution_tracker(user_context=None)
        except Exception:
            pass
        if validation_issues:
            pytest.fail(f"Factory parameter validation issues: {', '.join(validation_issues)}")

    @pytest.mark.asyncio
    async def test_async_singleton_consistency(self):
        """
        Test singleton consistency in async environment.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Async consistency issues)
        POST-CONSOLIDATION EXPECTED: PASS (Async-safe singleton)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
        except ImportError:
            self.skip('get_execution_tracker not available for async testing')
        tracker_instances = []
        errors = []

        async def get_tracker_async():
            try:
                tracker = get_execution_tracker()
                tracker_instances.append(id(tracker))
                await asyncio.sleep(0.01)
            except Exception as e:
                errors.append(str(e))
        tasks = [get_tracker_async() for _ in range(20)]
        await asyncio.gather(*tasks)
        if errors:
            pytest.fail(f'Async singleton errors: {errors}')
        unique_instances = set(tracker_instances)
        if len(unique_instances) != 1:
            pytest.fail(f'Async singleton violation: {len(unique_instances)} different instances created. Should be exactly 1 singleton instance.')

    def test_factory_caching_behavior(self):
        """
        Test that factory properly caches instances per user context.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Caching not optimized)
        POST-CONSOLIDATION EXPECTED: PASS (Efficient caching)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
        except ImportError:
            self.skip('get_execution_tracker not available for caching testing')
        user_context = {'user_id': 'cache_test_user'}
        start_time = time.time()
        tracker1 = get_execution_tracker(user_context=user_context)
        first_call_time = time.time() - start_time
        start_time = time.time()
        tracker2 = get_execution_tracker(user_context=user_context)
        second_call_time = time.time() - start_time
        assert tracker1 is tracker2, 'Same user context should return cached instance'
        if second_call_time > first_call_time * 2:
            pytest.fail(f'Factory caching inefficient: second call ({second_call_time:.6f}s) slower than expected vs first call ({first_call_time:.6f}s)')

    def test_memory_cleanup_on_user_session_end(self):
        """
        Test that singleton properly cleans up user-specific data.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Memory cleanup not implemented)
        POST-CONSOLIDATION EXPECTED: PASS (Proper memory management)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
        except ImportError:
            self.skip('get_execution_tracker not available for cleanup testing')
        tracker = get_execution_tracker(user_context={'user_id': 'cleanup_test'})
        if hasattr(tracker, 'create_execution'):
            exec_id = tracker.create_execution(agent_name='cleanup_test', thread_id='cleanup_thread', user_id='cleanup_test')
            if hasattr(tracker, 'cleanup_user_data'):
                initial_memory = self._get_tracker_memory_usage(tracker)
                tracker.cleanup_user_data('cleanup_test')
                final_memory = self._get_tracker_memory_usage(tracker)
                if hasattr(tracker, 'get_user_executions'):
                    remaining_executions = tracker.get_user_executions('cleanup_test')
                    if remaining_executions:
                        pytest.fail('User data not properly cleaned up after cleanup_user_data call')

    def _get_tracker_memory_usage(self, tracker) -> int:
        """Helper to estimate tracker memory usage."""
        if hasattr(tracker, '_executions'):
            return len(getattr(tracker, '_executions', {}))
        elif hasattr(tracker, 'get_all_executions'):
            return len(tracker.get_all_executions())
        else:
            return 0
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')