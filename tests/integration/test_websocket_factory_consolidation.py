"""WebSocket Factory Pattern Consolidation Test Suite

PURPOSE: Verify unified factory pattern behavior for Issue #1182 WebSocket Manager SSOT Migration
BUSINESS VALUE: Protects $500K+ ARR Golden Path by ensuring consistent factory behavior

This test suite MUST FAIL with current inconsistent factory implementations and PASS after consolidation.

CRITICAL: These tests follow claude.md requirements:
- NO Docker dependencies (integration without docker)
- Real services focus
- Factory pattern validation
- User isolation verification
"""

import asyncio
import unittest
from typing import Dict, List, Set, Any, Optional
from unittest.mock import AsyncMock, patch
import concurrent.futures
import threading
import time

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import UserID, ThreadID, ensure_user_id

logger = get_logger(__name__)


class TestWebSocketFactoryConsolidation(SSotAsyncTestCase):
    """Test WebSocket factory pattern consolidation and consistency.
    
    These tests MUST FAIL with current inconsistent factory implementations.
    After SSOT consolidation, they MUST PASS with unified factory behavior.
    """

    def setUp(self):
        """Set up test environment for factory pattern testing."""
        super().setUp()
        self.created_managers = []
        self.factory_inconsistencies = []
        self.user_isolation_violations = []
        
    async def asyncSetUp(self):
        """Async setup for factory testing."""
        await super().asyncSetUp()
        self.test_user_contexts = await self._create_test_user_contexts()
        
    async def _create_test_user_contexts(self) -> List[Any]:
        """Create multiple test user contexts for isolation testing."""
        user_contexts = []
        
        for i in range(3):
            try:
                # Try to create proper user execution contexts
                from netra_backend.app.services.user_execution_context import UserExecutionContext, UserContextManager
                from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
                
                id_manager = UnifiedIDManager()
                user_id = ensure_user_id(id_manager.generate_id(IDType.USER, prefix=f"test_factory_{i}"))
                
                # Create isolated user context
                context = type('TestUserContext', (), {
                    'user_id': user_id,
                    'thread_id': id_manager.generate_id(IDType.THREAD, prefix=f"test_factory_{i}"),
                    'request_id': id_manager.generate_id(IDType.REQUEST, prefix=f"test_factory_{i}"),
                    'is_test': True,
                    'factory_test_index': i
                })()
                
                user_contexts.append(context)
                logger.info(f"Created test user context {i}: {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to create user context {i}: {e}")
                # Fallback minimal context
                context = type('MinimalTestContext', (), {
                    'user_id': f"test_factory_user_{i}",
                    'is_test': True,
                    'factory_test_index': i
                })()
                user_contexts.append(context)
        
        return user_contexts

    async def test_websocket_manager_factory_consistency(self):
        """
        CRITICAL TEST: Verify all factory methods produce consistent manager types
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Different factory methods create different manager types
        - MUST PASS (after SSOT): All factory methods create same manager type
        """
        logger.info("Testing WebSocket manager factory consistency...")
        
        factory_methods_to_test = [
            ("netra_backend.app.websocket_core.websocket_manager", "get_websocket_manager"),
            ("netra_backend.app.websocket_core.manager", "WebSocketManager"),  # Direct instantiation
            ("netra_backend.app.websocket_core.websocket_manager", "WebSocketManager"),  # Class access
        ]
        
        created_manager_types = {}
        factory_errors = []
        
        for module_path, factory_name in factory_methods_to_test:
            try:
                import importlib
                module = importlib.import_module(module_path)
                
                if factory_name.startswith('get_'):
                    # Factory function
                    factory_func = getattr(module, factory_name)
                    if asyncio.iscoroutinefunction(factory_func):
                        manager = await factory_func(user_context=self.test_user_contexts[0])
                    else:
                        manager = factory_func(user_context=self.test_user_contexts[0])
                else:
                    # Direct class instantiation
                    manager_class = getattr(module, factory_name)
                    manager = manager_class(
                        user_context=self.test_user_contexts[0],
                        _ssot_authorization_token="test_token_123"
                    )
                
                manager_type = type(manager)
                created_manager_types[f"{module_path}.{factory_name}"] = manager_type
                self.created_managers.append(manager)
                
                logger.info(f"Factory {module_path}.{factory_name} created: {manager_type}")
                
            except Exception as e:
                factory_errors.append(f"{module_path}.{factory_name}: {e}")
                logger.error(f"Factory method {module_path}.{factory_name} failed: {e}")
        
        # Check for consistency across all factory methods
        unique_manager_types = set(created_manager_types.values())
        
        if len(unique_manager_types) > 1:
            for factory_path, manager_type in created_manager_types.items():
                self.factory_inconsistencies.append(f"  - {factory_path}: {manager_type}")
        
        # ASSERTION: This MUST FAIL currently (proving factory inconsistencies)
        # After SSOT consolidation, this MUST PASS (consistent factory behavior)
        self.assertEqual(len(unique_manager_types), 1,
                        f"FACTORY INCONSISTENCY: Found {len(unique_manager_types)} different manager types from factories. "
                        f"Types: {unique_manager_types}. "
                        f"Factory errors: {factory_errors}. "
                        f"Inconsistencies: {self.factory_inconsistencies}")

    async def test_websocket_manager_user_isolation_enforcement(self):
        """
        CRITICAL TEST: Verify factory creates properly isolated manager instances per user
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Shared state between users (singleton contamination)
        - MUST PASS (after SSOT): Complete user isolation with factory pattern
        """
        logger.info("Testing WebSocket manager user isolation enforcement...")
        
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            
            # Create managers for different users
            user_managers = {}
            shared_state_violations = []
            
            for i, user_context in enumerate(self.test_user_contexts):
                manager = await get_websocket_manager(user_context=user_context)
                user_managers[user_context.user_id] = manager
                
                # Test that each manager has isolated state
                manager_id = id(manager)
                manager_user_id = getattr(manager, 'user_context', {}).get('user_id', 'unknown')
                
                logger.info(f"Created manager {manager_id} for user {user_context.user_id} (manager thinks it's for: {manager_user_id})")
                
                # Check for shared instance violations
                for existing_user_id, existing_manager in user_managers.items():
                    if existing_user_id != user_context.user_id and id(existing_manager) == manager_id:
                        shared_state_violations.append(f"Same manager instance {manager_id} shared between users {existing_user_id} and {user_context.user_id}")
            
            # Test concurrent access isolation
            isolation_violations = await self._test_concurrent_user_isolation(user_managers)
            
            # Combine all violations
            total_violations = shared_state_violations + isolation_violations
            
            # ASSERTION: This MUST FAIL currently (proving isolation violations)
            # After SSOT consolidation, this MUST PASS (proper user isolation)
            self.assertEqual(len(total_violations), 0,
                           f"USER ISOLATION VIOLATIONS: Found {len(total_violations)} violations. "
                           f"Shared state violations: {shared_state_violations}. "
                           f"Isolation violations: {isolation_violations}")
                           
        except Exception as e:
            self.fail(f"Failed to test user isolation: {e}")

    async def _test_concurrent_user_isolation(self, user_managers: Dict[str, Any]) -> List[str]:
        """Test that concurrent operations don't contaminate user data."""
        isolation_violations = []
        
        async def user_operation(user_id: str, manager: Any, operation_id: str) -> Dict[str, Any]:
            """Simulate user-specific operation."""
            try:
                # Set user-specific data
                test_data = f"data_for_{user_id}_{operation_id}"
                
                # Try to access user context from manager
                if hasattr(manager, 'user_context'):
                    manager_user_id = getattr(manager.user_context, 'user_id', 'unknown')
                    if manager_user_id != user_id:
                        return {
                            'violation': f"Manager for {user_id} has wrong user context: {manager_user_id}",
                            'user_id': user_id,
                            'operation_id': operation_id
                        }
                
                # Simulate some async work
                await asyncio.sleep(0.01)
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'operation_id': operation_id,
                    'test_data': test_data
                }
                
            except Exception as e:
                return {
                    'error': str(e),
                    'user_id': user_id,
                    'operation_id': operation_id
                }
        
        # Run concurrent operations for all users
        tasks = []
        for user_id, manager in user_managers.items():
            for op_id in range(3):  # Multiple operations per user
                task = user_operation(user_id, manager, f"op_{op_id}")
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results for isolation violations
        for result in results:
            if isinstance(result, dict):
                if 'violation' in result:
                    isolation_violations.append(result['violation'])
                elif 'error' in result:
                    isolation_violations.append(f"User {result['user_id']} operation failed: {result['error']}")
        
        return isolation_violations

    async def test_websocket_manager_factory_thread_safety(self):
        """
        CRITICAL TEST: Verify factory is thread-safe under concurrent access
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Race conditions in factory creation
        - MUST PASS (after SSOT): Thread-safe factory with proper locking
        """
        logger.info("Testing WebSocket manager factory thread safety...")
        
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            
            # Test concurrent factory calls
            thread_results = {}
            thread_errors = []
            race_condition_violations = []
            
            def create_manager_in_thread(thread_id: int, user_context: Any) -> Dict[str, Any]:
                """Create manager in separate thread."""
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    manager = loop.run_until_complete(get_websocket_manager(user_context=user_context))
                    manager_id = id(manager)
                    manager_type = type(manager).__name__
                    
                    loop.close()
                    
                    return {
                        'thread_id': thread_id,
                        'manager_id': manager_id,
                        'manager_type': manager_type,
                        'user_id': getattr(user_context, 'user_id', 'unknown'),
                        'success': True
                    }
                    
                except Exception as e:
                    return {
                        'thread_id': thread_id,
                        'error': str(e),
                        'success': False
                    }
            
            # Create multiple threads creating managers concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for i in range(10):  # 10 concurrent factory calls
                    user_context = self.test_user_contexts[i % len(self.test_user_contexts)]
                    future = executor.submit(create_manager_in_thread, i, user_context)
                    futures.append(future)
                
                # Collect results
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    thread_id = result.get('thread_id', 'unknown')
                    
                    if result.get('success'):
                        thread_results[thread_id] = result
                    else:
                        thread_errors.append(f"Thread {thread_id}: {result.get('error', 'Unknown error')}")
            
            # Analyze results for race conditions
            manager_types = set(r['manager_type'] for r in thread_results.values())
            if len(manager_types) > 1:
                race_condition_violations.append(f"Different manager types created concurrently: {manager_types}")
            
            # Check for unexpected failures
            if len(thread_errors) > 0:
                race_condition_violations.extend(thread_errors)
            
            # ASSERTION: This MUST FAIL currently (proving race conditions)
            # After SSOT consolidation, this MUST PASS (thread-safe factory)
            self.assertEqual(len(race_condition_violations), 0,
                           f"THREAD SAFETY VIOLATIONS: Found {len(race_condition_violations)} race conditions. "
                           f"Violations: {race_condition_violations}. "
                           f"Thread results: {len(thread_results)} successful, {len(thread_errors)} failed.")
                           
        except Exception as e:
            self.fail(f"Failed to test thread safety: {e}")

    async def test_websocket_manager_factory_memory_isolation(self):
        """
        CRITICAL TEST: Verify factory prevents memory leaks and cross-user contamination
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Memory shared between user contexts
        - MUST PASS (after SSOT): Complete memory isolation per user
        """
        logger.info("Testing WebSocket manager factory memory isolation...")
        
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            
            memory_violations = []
            created_managers_memory = []
            
            # Create managers and modify their state
            for i, user_context in enumerate(self.test_user_contexts):
                manager = await get_websocket_manager(user_context=user_context)
                
                # Try to set some state that shouldn't leak between users
                test_state_key = f"test_state_{user_context.user_id}"
                test_state_value = f"secret_data_for_user_{i}"
                
                # Try different ways to set state that might be shared
                if hasattr(manager, '_user_state'):
                    setattr(manager._user_state, test_state_key, test_state_value)
                elif hasattr(manager, '__dict__'):
                    manager.__dict__[test_state_key] = test_state_value
                
                created_managers_memory.append((manager, test_state_key, test_state_value, user_context.user_id))
            
            # Check for memory contamination between users
            for i, (manager1, key1, value1, user_id1) in enumerate(created_managers_memory):
                for j, (manager2, key2, value2, user_id2) in enumerate(created_managers_memory):
                    if i != j:  # Different managers
                        # Check if manager1 has state from manager2
                        if hasattr(manager1, '_user_state') and hasattr(getattr(manager1, '_user_state', None), key2):
                            contamination_value = getattr(manager1._user_state, key2, None)
                            if contamination_value == value2:
                                memory_violations.append(f"Manager for {user_id1} has contaminated state from {user_id2}: {key2}={contamination_value}")
                        
                        # Check direct attribute contamination
                        if hasattr(manager1, key2) and getattr(manager1, key2, None) == value2:
                            memory_violations.append(f"Manager for {user_id1} has direct attribute contamination from {user_id2}: {key2}={value2}")
            
            # ASSERTION: This MUST FAIL currently (proving memory contamination)
            # After SSOT consolidation, this MUST PASS (complete memory isolation)
            self.assertEqual(len(memory_violations), 0,
                           f"MEMORY ISOLATION VIOLATIONS: Found {len(memory_violations)} memory contamination issues. "
                           f"Violations: {memory_violations}")
                           
        except Exception as e:
            self.fail(f"Failed to test memory isolation: {e}")

    async def asyncTearDown(self):
        """Clean up created managers and resources."""
        for manager in self.created_managers:
            try:
                if hasattr(manager, 'cleanup') and callable(manager.cleanup):
                    await manager.cleanup()
                elif hasattr(manager, 'close') and callable(manager.close):
                    await manager.close()
            except Exception as e:
                logger.warning(f"Failed to cleanup manager {manager}: {e}")
        
        await super().asyncTearDown()
        
    def tearDown(self):
        """Clean up after factory pattern tests."""
        super().tearDown()
        logger.info(f"Factory test completed. Inconsistencies found: {len(self.factory_inconsistencies)}")
        logger.info(f"User isolation violations found: {len(self.user_isolation_violations)}")


if __name__ == '__main__':
    unittest.main()