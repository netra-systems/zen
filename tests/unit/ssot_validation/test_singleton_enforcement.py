#!/usr/bin/env python3
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
            
            # This should fail after consolidation - direct instantiation should be blocked
            try:
                tracker = AgentExecutionTracker()
                
                # If we can create it directly, that's a SSOT violation
                self.fail(
                    "SSOT VIOLATION: Direct AgentExecutionTracker() instantiation is allowed. "
                    "Should only be accessible through get_execution_tracker() factory method "
                    "to ensure singleton behavior and user isolation."
                )
                
            except (TypeError, RuntimeError, ValueError) as e:
                # This is expected after consolidation - direct instantiation should be blocked
                if "factory" in str(e).lower() or "singleton" in str(e).lower():
                    pass  # Good - factory enforcement working
                else:
                    self.fail(f"AgentExecutionTracker blocked instantiation but with wrong error: {e}")
                    
        except ImportError:
            self.fail("AgentExecutionTracker not available for singleton testing")

    def test_factory_method_should_work(self):
        """
        Should PASS - get_execution_tracker() factory method should work.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Factory method not implemented)
        POST-CONSOLIDATION EXPECTED: PASS (Factory method provides proper access)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
            
            # Factory method should work
            tracker = get_execution_tracker()
            assert tracker is not None, "Factory method should return tracker instance"
            
            # Multiple calls should return same instance (singleton behavior)
            tracker2 = get_execution_tracker()
            assert tracker is tracker2, "Factory method should return same singleton instance"
            
        except ImportError:
            self.fail(
                "get_execution_tracker factory method not available. "
                "This should be the only way to access AgentExecutionTracker."
            )

    def test_factory_provides_user_isolated_instances(self):
        """
        Should PASS - Factory should provide user-isolated tracker instances.
        
        CURRENT EXPECTED RESULT: MAY FAIL (User isolation not implemented)
        POST-CONSOLIDATION EXPECTED: PASS (Proper user isolation through factory)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
            
            # Test user isolation through factory
            user1_tracker = get_execution_tracker(user_context={'user_id': 'user1'})
            user2_tracker = get_execution_tracker(user_context={'user_id': 'user2'})
            
            # Should be same singleton but with different user contexts
            assert user1_tracker is not None
            assert user2_tracker is not None
            
            # Test isolation by creating executions
            if hasattr(user1_tracker, 'create_execution') and hasattr(user2_tracker, 'create_execution'):
                exec1 = user1_tracker.create_execution(
                    agent_name='test_agent', 
                    thread_id='thread1',
                    user_id='user1'
                )
                exec2 = user2_tracker.create_execution(
                    agent_name='test_agent',
                    thread_id='thread2', 
                    user_id='user2'
                )
                
                # Executions should be isolated per user
                if hasattr(user1_tracker, 'get_user_executions'):
                    user1_executions = user1_tracker.get_user_executions('user1')
                    user2_executions = user2_tracker.get_user_executions('user2')
                    
                    assert exec1 in user1_executions, "User1 should see their execution"
                    assert exec2 not in user1_executions, "User1 should not see User2's execution"
                    assert exec2 in user2_executions, "User2 should see their execution"
                    assert exec1 not in user2_executions, "User2 should not see User1's execution"
                    
        except ImportError:
            self.fail("Factory method with user context not available")

    def test_singleton_behavior_across_threads(self):
        """
        Test singleton behavior is maintained across multiple threads.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Thread safety not guaranteed)
        POST-CONSOLIDATION EXPECTED: PASS (Thread-safe singleton behavior)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
        except ImportError:
            self.skip("get_execution_tracker not available for thread testing")
            
        tracker_instances = []
        errors = []
        
        def get_tracker_in_thread():
            try:
                tracker = get_execution_tracker()
                tracker_instances.append(id(tracker))
            except Exception as e:
                errors.append(str(e))
                
        # Create multiple threads accessing tracker
        threads = []
        for i in range(10):
            thread = threading.Thread(target=get_tracker_in_thread)
            threads.append(thread)
            
        # Start all threads
        for thread in threads:
            thread.start()
            
        # Wait for completion
        for thread in threads:
            thread.join()
            
        # Check results
        if errors:
            self.fail(f"Thread safety errors: {errors}")
            
        # All threads should get the same singleton instance
        unique_instances = set(tracker_instances)
        if len(unique_instances) != 1:
            self.fail(
                f"Singleton violation: {len(unique_instances)} different instances created across threads. "
                f"Should be exactly 1 singleton instance."
            )

    def test_no_global_state_leakage_between_users(self):
        """
        Test that singleton doesn't leak state between users.
        
        CURRENT EXPECTED RESULT: MAY FAIL (State leakage exists)
        POST-CONSOLIDATION EXPECTED: PASS (No state leakage)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
        except ImportError:
            self.skip("get_execution_tracker not available for isolation testing")
            
        # Create tracker for user1
        tracker = get_execution_tracker(user_context={'user_id': 'user1'})
        
        if hasattr(tracker, 'create_execution'):
            # Create execution for user1
            exec1 = tracker.create_execution(
                agent_name='isolation_test',
                thread_id='user1_thread',
                user_id='user1'
            )
            
            # Switch to user2 context
            tracker2 = get_execution_tracker(user_context={'user_id': 'user2'})
            
            # User2 should not see user1's execution
            if hasattr(tracker2, 'get_execution'):
                try:
                    user2_view = tracker2.get_execution(exec1)
                    if user2_view is not None:
                        self.fail(
                            "ISOLATION VIOLATION: User2 can access User1's execution. "
                            "Singleton pattern must enforce user isolation."
                        )
                except (KeyError, ValueError, PermissionError):
                    # This is expected - user2 should not access user1's execution
                    pass

    def test_constructor_privacy_enforcement(self):
        """
        Test that AgentExecutionTracker constructor is properly private.
        
        CURRENT EXPECTED RESULT: FAIL (Constructor is public)
        POST-CONSOLIDATION EXPECTED: PASS (Constructor is private/protected)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            
            # Check if constructor has privacy enforcement
            init_method = AgentExecutionTracker.__init__
            
            # Check for privacy indicators in constructor
            import inspect
            source = inspect.getsource(init_method)
            
            privacy_indicators = [
                'raise RuntimeError',
                'raise TypeError', 
                'raise ValueError',
                'factory',
                'get_execution_tracker',
                'private',
                'singleton'
            ]
            
            has_privacy_enforcement = any(indicator in source for indicator in privacy_indicators)
            
            if not has_privacy_enforcement:
                self.fail(
                    "SSOT VIOLATION: AgentExecutionTracker constructor does not enforce privacy. "
                    "Should prevent direct instantiation to ensure singleton pattern."
                )
                
        except ImportError:
            self.fail("AgentExecutionTracker not available for constructor privacy testing")

    def test_factory_method_parameter_validation(self):
        """
        Test that factory method properly validates parameters.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Parameter validation incomplete)
        POST-CONSOLIDATION EXPECTED: PASS (Proper parameter validation)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
        except ImportError:
            self.skip("get_execution_tracker not available for parameter testing")
            
        validation_issues = []
        
        # Test invalid user context
        try:
            tracker = get_execution_tracker(user_context="invalid_string")
            validation_issues.append("Factory accepts invalid user_context string")
        except (TypeError, ValueError):
            # Expected - should validate user_context type
            pass
            
        # Test missing required user_id in context
        try:
            tracker = get_execution_tracker(user_context={'invalid': 'context'})
            if hasattr(tracker, 'create_execution'):
                # Should fail when trying to create execution without valid user context
                tracker.create_execution(
                    agent_name='test',
                    thread_id='test',
                    user_id='test'
                )
                validation_issues.append("Factory allows operations with invalid user context")
        except (KeyError, ValueError, RuntimeError):
            # Expected - should validate user context structure
            pass
            
        # Test None user context (should use default or fail gracefully)
        try:
            tracker = get_execution_tracker(user_context=None)
            # This might be allowed for system-level operations
        except Exception:
            # This is also acceptable if None context is not allowed
            pass
            
        if validation_issues:
            self.fail(f"Factory parameter validation issues: {', '.join(validation_issues)}")

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
            self.skip("get_execution_tracker not available for async testing")
            
        tracker_instances = []
        errors = []
        
        async def get_tracker_async():
            try:
                tracker = get_execution_tracker()
                tracker_instances.append(id(tracker))
                await asyncio.sleep(0.01)  # Small delay to test race conditions
            except Exception as e:
                errors.append(str(e))
                
        # Create multiple async tasks
        tasks = [get_tracker_async() for _ in range(20)]
        await asyncio.gather(*tasks)
        
        # Check results
        if errors:
            self.fail(f"Async singleton errors: {errors}")
            
        # All async tasks should get the same singleton instance
        unique_instances = set(tracker_instances)
        if len(unique_instances) != 1:
            self.fail(
                f"Async singleton violation: {len(unique_instances)} different instances created. "
                f"Should be exactly 1 singleton instance."
            )

    def test_factory_caching_behavior(self):
        """
        Test that factory properly caches instances per user context.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Caching not optimized)
        POST-CONSOLIDATION EXPECTED: PASS (Efficient caching)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
        except ImportError:
            self.skip("get_execution_tracker not available for caching testing")
            
        # Test caching for same user context
        user_context = {'user_id': 'cache_test_user'}
        
        start_time = time.time()
        tracker1 = get_execution_tracker(user_context=user_context)
        first_call_time = time.time() - start_time
        
        start_time = time.time()
        tracker2 = get_execution_tracker(user_context=user_context)
        second_call_time = time.time() - start_time
        
        # Should be same instance (cached)
        assert tracker1 is tracker2, "Same user context should return cached instance"
        
        # Second call should be faster (cached)
        if second_call_time > first_call_time * 2:
            self.fail(
                f"Factory caching inefficient: second call ({second_call_time:.6f}s) "
                f"slower than expected vs first call ({first_call_time:.6f}s)"
            )

    def test_memory_cleanup_on_user_session_end(self):
        """
        Test that singleton properly cleans up user-specific data.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Memory cleanup not implemented)
        POST-CONSOLIDATION EXPECTED: PASS (Proper memory management)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
        except ImportError:
            self.skip("get_execution_tracker not available for cleanup testing")
            
        tracker = get_execution_tracker(user_context={'user_id': 'cleanup_test'})
        
        # Create some user data
        if hasattr(tracker, 'create_execution'):
            exec_id = tracker.create_execution(
                agent_name='cleanup_test',
                thread_id='cleanup_thread',
                user_id='cleanup_test'
            )
            
            # Test cleanup functionality
            if hasattr(tracker, 'cleanup_user_data'):
                initial_memory = self._get_tracker_memory_usage(tracker)
                
                tracker.cleanup_user_data('cleanup_test')
                
                final_memory = self._get_tracker_memory_usage(tracker)
                
                # Should have cleaned up user data
                if hasattr(tracker, 'get_user_executions'):
                    remaining_executions = tracker.get_user_executions('cleanup_test')
                    if remaining_executions:
                        self.fail("User data not properly cleaned up after cleanup_user_data call")
                        
    def _get_tracker_memory_usage(self, tracker) -> int:
        """Helper to estimate tracker memory usage."""
        # Simple heuristic - count tracked executions
        if hasattr(tracker, '_executions'):
            return len(getattr(tracker, '_executions', {}))
        elif hasattr(tracker, 'get_all_executions'):
            return len(tracker.get_all_executions())
        else:
            return 0


if __name__ == "__main__":
    """
    Run singleton enforcement validation tests.
    
    These tests ensure AgentExecutionTracker uses proper singleton patterns
    that prevent SSOT violations while maintaining user isolation.
    """
    pytest.main([__file__, "-v", "--tb=short", "-x"])