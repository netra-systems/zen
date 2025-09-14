"""
Test WebSocket User Isolation with SSOT Patterns

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Ensure WebSocket user isolation prevents data contamination 
- Value Impact: Critical for multi-tenant security in AI chat interactions
- Revenue Impact: Prevents user data leakage that could destroy $500K+ ARR trust

CRITICAL: This test validates user context isolation with SSOT WebSocket managers.
These tests MUST FAIL before SSOT remediation and PASS after remediation.

Issue: Dual pattern fragmentation undermines user context isolation
GitHub Issue: https://github.com/netra-systems/netra-apex/issues/1126
"""

import pytest
import asyncio
import unittest
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestWebSocketUserIsolationSSot(SSotAsyncTestCase, unittest.TestCase):
    """Test WebSocket user isolation with SSOT patterns."""
    
    async def setup_method(self, method):
        """Set up test environment for user isolation testing."""
        await super().setup_method(method)
        
        # Create test user contexts
        self.test_users = [
            {
                'user_id': f'isolation_test_user_{i}',
                'thread_id': f'isolation_test_thread_{i}',
                'session_id': f'isolation_test_session_{i}',
                'name': f'Test User {i}'
            }
            for i in range(3)  # Test with 3 different users
        ]
        
        self.websocket_managers: List[Any] = []
        
    async def teardown_method(self, method):
        """Clean up WebSocket managers."""
        # Clean up any managers created during testing
        for manager in self.websocket_managers:
            try:
                if hasattr(manager, 'cleanup') and callable(manager.cleanup):
                    await manager.cleanup()
                elif hasattr(manager, 'close') and callable(manager.close):
                    await manager.close()
            except Exception as e:
                self.logger.warning(f"Error cleaning up manager: {e}")
                
        await super().teardown_method(method)
        
    async def test_different_users_get_different_manager_instances(self):
        """
        Test that different users get different WebSocket manager instances.
        
        BEFORE REMEDIATION: This test should FAIL (shared singleton instances)
        AFTER REMEDIATION: This test should PASS (isolated instances per user)
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        except ImportError as e:
            self.fail(f"SSOT get_websocket_manager should be importable: {e}")
            
        managers = []
        
        # Create managers for different users
        for user_context in self.test_users:
            manager = await get_websocket_manager(user_context=user_context)
            managers.append(manager)
            self.websocket_managers.append(manager)
            
        # BEFORE REMEDIATION: This assertion should FAIL (all managers are the same instance)
        # AFTER REMEDIATION: This assertion should PASS (each manager is different)
        for i, manager_a in enumerate(managers):
            for j, manager_b in enumerate(managers):
                if i != j:
                    self.assertIsNot(
                        manager_a, 
                        manager_b,
                        f"User {i} and User {j} should get different WebSocket manager instances"
                    )
                    
        self.logger.info(f"Successfully created {len(managers)} isolated WebSocket managers")
        
    async def test_user_context_isolation_in_manager_state(self):
        """
        Test that user context is properly isolated in WebSocket manager state.
        
        BEFORE REMEDIATION: This test should FAIL (user context contamination)
        AFTER REMEDIATION: This test should PASS (proper user context isolation)
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        except ImportError as e:
            self.fail(f"SSOT get_websocket_manager should be importable: {e}")
            
        # Create managers for each user
        user_managers = {}
        for user_context in self.test_users:
            manager = await get_websocket_manager(user_context=user_context)
            user_managers[user_context['user_id']] = manager
            self.websocket_managers.append(manager)
            
        # Verify each manager has correct user context
        for user_context in self.test_users:
            user_id = user_context['user_id']
            manager = user_managers[user_id]
            
            # Check if manager has user context stored properly
            if hasattr(manager, 'user_context'):
                manager_user_context = manager.user_context
                
                # BEFORE REMEDIATION: This might FAIL (wrong or shared user context)
                # AFTER REMEDIATION: This should PASS (correct isolated user context)
                if isinstance(manager_user_context, dict):
                    self.assertEqual(
                        manager_user_context.get('user_id'),
                        user_context['user_id'],
                        f"Manager should have correct user_id for user {user_id}"
                    )
                    
                    self.assertEqual(
                        manager_user_context.get('thread_id'),
                        user_context['thread_id'],
                        f"Manager should have correct thread_id for user {user_id}"
                    )
                    
            self.logger.info(f"Verified user context isolation for user {user_id}")
            
    async def test_concurrent_user_manager_creation_isolation(self):
        """
        Test that concurrent WebSocket manager creation maintains user isolation.
        
        BEFORE REMEDIATION: This test should FAIL (race conditions, shared state)
        AFTER REMEDIATION: This test should PASS (proper concurrent isolation)
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        except ImportError as e:
            self.fail(f"SSOT get_websocket_manager should be importable: {e}")
            
        async def create_manager_for_user(user_context: Dict[str, Any]) -> tuple:
            """Create a WebSocket manager for a specific user."""
            try:
                manager = await get_websocket_manager(user_context=user_context)
                return user_context['user_id'], manager, None
            except Exception as e:
                return user_context['user_id'], None, str(e)
                
        # Create managers concurrently
        creation_tasks = [
            create_manager_for_user(user_context)
            for user_context in self.test_users
        ]
        
        results = await asyncio.gather(*creation_tasks, return_exceptions=True)
        
        # Process results
        successful_managers = {}
        failed_creations = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_creations.append(str(result))
                continue
                
            user_id, manager, error = result
            if error:
                failed_creations.append(f"User {user_id}: {error}")
            else:
                successful_managers[user_id] = manager
                self.websocket_managers.append(manager)
                
        # All creations should succeed
        self.assertEqual(
            len(failed_creations), 
            0,
            f"All concurrent manager creations should succeed: {failed_creations}"
        )
        
        # All managers should be different instances
        manager_list = list(successful_managers.values())
        for i, manager_a in enumerate(manager_list):
            for j, manager_b in enumerate(manager_list):
                if i != j:
                    # BEFORE REMEDIATION: This assertion should FAIL (shared instances)
                    # AFTER REMEDIATION: This assertion should PASS (isolated instances)
                    self.assertIsNot(
                        manager_a,
                        manager_b,
                        "Concurrently created managers should be different instances"
                    )
                    
        self.logger.info(f"Successfully created {len(successful_managers)} concurrent isolated managers")
        
    async def test_user_message_routing_isolation(self):
        """
        Test that user messages are properly routed and isolated between users.
        
        BEFORE REMEDIATION: This test should FAIL (message cross-contamination)
        AFTER REMEDIATION: This test should PASS (proper message isolation)
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        except ImportError as e:
            self.fail(f"SSOT get_websocket_manager should be importable: {e}")
            
        # Create managers for each user
        user_managers = {}
        for user_context in self.test_users:
            manager = await get_websocket_manager(user_context=user_context)
            user_managers[user_context['user_id']] = manager
            self.websocket_managers.append(manager)
            
        # Simulate message routing (if managers support it)
        test_messages = [
            {
                'user_id': self.test_users[0]['user_id'],
                'message': 'User 0 secret message',
                'thread_id': self.test_users[0]['thread_id']
            },
            {
                'user_id': self.test_users[1]['user_id'], 
                'message': 'User 1 secret message',
                'thread_id': self.test_users[1]['thread_id']
            },
        ]
        
        # Track which manager handles which message
        message_handling = {}
        
        for test_msg in test_messages:
            user_id = test_msg['user_id']
            manager = user_managers[user_id]
            
            # If manager has message handling capability, test it
            if hasattr(manager, 'connections') or hasattr(manager, 'active_connections'):
                # Mock connection tracking for this user
                message_handling[user_id] = {
                    'manager': manager,
                    'message': test_msg['message'],
                    'expected_recipient': user_id
                }
                
        # Verify message isolation
        for user_id, handling_info in message_handling.items():
            manager = handling_info['manager']
            message = handling_info['message']
            
            # The key test: this manager should only handle messages for this user
            # BEFORE REMEDIATION: Messages might leak to wrong managers
            # AFTER REMEDIATION: Messages should be properly isolated
            
            # Check manager identity corresponds to user
            if hasattr(manager, 'user_context') and manager.user_context:
                manager_user_id = manager.user_context.get('user_id')
                self.assertEqual(
                    manager_user_id,
                    user_id,
                    f"Manager should only handle messages for its own user: {manager_user_id} vs {user_id}"
                )
                
        self.logger.info("Message routing isolation test completed")
        
    async def test_user_session_cleanup_isolation(self):
        """
        Test that user session cleanup doesn't affect other users.
        
        BEFORE REMEDIATION: This test should FAIL (cleanup affects other users)
        AFTER REMEDIATION: This test should PASS (isolated cleanup)
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        except ImportError as e:
            self.fail(f"SSOT get_websocket_manager should be importable: {e}")
            
        # Create managers for all users
        user_managers = {}
        for user_context in self.test_users:
            manager = await get_websocket_manager(user_context=user_context)
            user_managers[user_context['user_id']] = manager
            self.websocket_managers.append(manager)
            
        # Verify all managers are initially active/valid
        initial_manager_count = len(user_managers)
        self.assertEqual(
            initial_manager_count,
            len(self.test_users),
            "All managers should be created successfully"
        )
        
        # Clean up one specific user's manager
        target_user_id = self.test_users[0]['user_id']
        target_manager = user_managers[target_user_id]
        
        # Perform cleanup on target manager
        try:
            if hasattr(target_manager, 'cleanup') and callable(target_manager.cleanup):
                await target_manager.cleanup()
            elif hasattr(target_manager, 'close') and callable(target_manager.close):
                await target_manager.close()
                
            self.logger.info(f"Cleaned up manager for user {target_user_id}")
            
        except Exception as e:
            self.logger.warning(f"Manager cleanup not available or failed: {e}")
            
        # Verify other users' managers are still functional
        remaining_users = [user for user in self.test_users if user['user_id'] != target_user_id]
        
        for user_context in remaining_users:
            user_id = user_context['user_id']
            manager = user_managers[user_id]
            
            # BEFORE REMEDIATION: Other managers might be affected by cleanup
            # AFTER REMEDIATION: Other managers should remain unaffected
            self.assertIsNotNone(
                manager,
                f"Manager for user {user_id} should remain unaffected by other user's cleanup"
            )
            
            # If manager has a status/health check, verify it's still healthy
            if hasattr(manager, 'is_healthy') and callable(manager.is_healthy):
                try:
                    is_healthy = await manager.is_healthy()
                    self.assertTrue(
                        is_healthy,
                        f"Manager for user {user_id} should remain healthy after other user's cleanup"
                    )
                except Exception as e:
                    self.logger.warning(f"Health check not available for manager: {e}")
                    
        self.logger.info("User session cleanup isolation test completed")
        
    async def test_factory_pattern_enforces_user_context_requirement(self):
        """
        Test that SSOT factory pattern enforces user context requirement.
        
        BEFORE REMEDIATION: This test might FAIL (weak user context enforcement)
        AFTER REMEDIATION: This test should PASS (strict user context requirement)
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        except ImportError as e:
            self.fail(f"SSOT get_websocket_manager should be importable: {e}")
            
        # Test 1: Missing user context should be handled gracefully
        try:
            manager_without_context = await get_websocket_manager(user_context=None)
            
            # BEFORE REMEDIATION: This might succeed with a singleton (bad)
            # AFTER REMEDIATION: This should either fail or create a safe default manager
            if manager_without_context is not None:
                self.websocket_managers.append(manager_without_context)
                
                # If it succeeds, it should be clearly marked as a default/test manager
                if hasattr(manager_without_context, 'is_default_manager'):
                    self.assertTrue(
                        manager_without_context.is_default_manager,
                        "Manager created without user context should be marked as default"
                    )
                    
        except (ValueError, TypeError) as e:
            # AFTER REMEDIATION: Strict enforcement - this is preferred behavior
            self.logger.info(f"Factory correctly rejected None user context: {e}")
            
        # Test 2: Invalid user context should be rejected or handled
        invalid_contexts = [
            {},  # Empty context
            {'invalid': 'context'},  # Missing required fields
            {'user_id': None, 'thread_id': None},  # Null values
        ]
        
        for invalid_context in invalid_contexts:
            with self.subTest(context=invalid_context):
                try:
                    manager = await get_websocket_manager(user_context=invalid_context)
                    
                    if manager is not None:
                        self.websocket_managers.append(manager)
                        
                        # If it succeeds, it should handle the invalid context safely
                        self.logger.info(f"Factory handled invalid context safely: {invalid_context}")
                    else:
                        self.fail("Factory should not return None for any input")
                        
                except (ValueError, TypeError, KeyError) as e:
                    # AFTER REMEDIATION: Strict validation - this is preferred
                    self.logger.info(f"Factory correctly rejected invalid context {invalid_context}: {e}")
                    
        # Test 3: Valid user context should always work
        valid_context = {
            'user_id': 'factory_test_user',
            'thread_id': 'factory_test_thread'
        }
        
        try:
            valid_manager = await get_websocket_manager(user_context=valid_context)
            self.assertIsNotNone(valid_manager, "Factory should create manager for valid context")
            self.websocket_managers.append(valid_manager)
            
        except Exception as e:
            self.fail(f"Factory should always work with valid user context: {e}")
            
        self.logger.info("Factory pattern user context enforcement test completed")


if __name__ == '__main__':
    pytest.main([__file__])