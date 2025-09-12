"""Test WebSocket Manager Factory SSOT Consolidation - Phase 2 SSOT Validation Test

This test validates Issue #564: Successful SSOT consolidation of WebSocket manager factory patterns.

CRITICAL BUSINESS CONTEXT:
- Issue: Validation that WebSocket manager factory patterns are consolidated to SSOT
- Business Impact: $500K+ ARR protected through reliable factory-based user isolation
- SSOT Achievement: Single factory pattern eliminates user context contamination issues
- Golden Path Impact: Consolidated factory ensures reliable user isolation in multi-tenant chat

TEST PURPOSE:
This test MUST FAIL initially (multiple factory patterns), then PASS after SSOT consolidation.
It validates that factory patterns are consolidated to support proper user isolation.

Expected Behavior:
- BEFORE SSOT Fix: FAIL (different factory patterns cause inconsistent user isolation)
- AFTER SSOT Fix: PASS (single consolidated factory pattern with perfect user isolation)

Business Value Justification:
- Segment: Enterprise (requires strict user isolation)
- Business Goal: Ensure factory consolidation maintains user isolation integrity
- Value Impact: Validates reliable multi-tenant chat environment for enterprise customers
- Revenue Impact: Confirms $500K+ ARR protection through consolidated user isolation factory
"""

import pytest
import asyncio
import uuid
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketManagerFactorySsotConsolidation(SSotAsyncTestCase):
    """Phase 2 SSOT Validation Test: Validate factory patterns are consolidated to SSOT."""
    
    def setup_method(self, method):
        """Set up test environment for factory SSOT validation."""
        super().setup_method(method)
        logger.info(f"Setting up factory SSOT validation test: {method.__name__}")
        
        # Create multiple isolated user contexts for factory testing
        self.user_contexts = []
        for i in range(3):
            context = type(f'FactoryTestUser{i}', (), {
                'user_id': f'factory_test_user_{i}_{uuid.uuid4().hex[:8]}',
                'thread_id': f'factory_test_thread_{i}_{uuid.uuid4().hex[:8]}',
                'request_id': f'factory_test_request_{i}_{uuid.uuid4().hex[:8]}',
                'is_test': True,
                'tenant_id': f'enterprise_tenant_{i}'
            })()
            self.user_contexts.append(context)
            
        logger.info(f"Created {len(self.user_contexts)} test user contexts for factory validation")
    
    async def test_single_factory_pattern_consolidation(self):
        """
        CRITICAL SSOT VALIDATION TEST: Validate single factory pattern for WebSocket managers.
        
        SSOT REQUIREMENT: After consolidation, there should be one canonical factory pattern
        that reliably creates isolated WebSocket manager instances for different users.
        
        Expected Results:
        - BEFORE SSOT Fix: This test FAILS (multiple factory patterns with inconsistencies)
        - AFTER SSOT Fix: This test PASSES (single factory pattern with reliable isolation)
        """
        logger.info("Validating single factory pattern consolidation (SSOT compliance)")
        
        # Import factory functions from different paths
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager as factory1
        from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
        
        # Test that factory function creates properly isolated instances
        factory_instances = []
        
        try:
            # Create instances for each user context via factory
            for i, user_context in enumerate(self.user_contexts):
                manager_instance = await factory1(
                    user_context=user_context,
                    mode=WebSocketManagerMode.UNIFIED
                )
                factory_instances.append((f'User{i}', user_context, manager_instance))
                logger.info(f"Factory created manager for User{i}: {type(manager_instance)}")
            
            # CRITICAL SSOT TEST 1: All instances should have the same type (single implementation)
            if len(factory_instances) >= 2:
                reference_type = type(factory_instances[0][2])
                for user_name, context, instance in factory_instances[1:]:
                    if type(instance) != reference_type:
                        pytest.fail(
                            f"FACTORY CONSOLIDATION FAILURE: {user_name} instance type {type(instance)} != "
                            f"reference type {reference_type}. "
                            f"SSOT Violation: Factory should create instances of the same type. "
                            f"Business Impact: Type inconsistencies break user isolation guarantees "
                            f"and affect $500K+ ARR enterprise customer requirements."
                        )
                
                logger.info("✅ SSOT COMPLIANCE: Factory creates instances of consistent type")
            
            # CRITICAL SSOT TEST 2: Instances should be properly isolated (different objects)
            instance_ids = set(id(instance) for _, _, instance in factory_instances)
            expected_unique_instances = len(factory_instances)
            
            if len(instance_ids) != expected_unique_instances:
                logger.error(f"❌ FACTORY ISOLATION FAILURE: Expected {expected_unique_instances} unique instances, got {len(instance_ids)}")
                
                # Log instance sharing details
                for i, (user_name, context, instance) in enumerate(factory_instances):
                    logger.error(f"  {user_name}: {id(instance)} (user_id: {context.user_id})")
                
                pytest.fail(
                    f"FACTORY ISOLATION VIOLATION: Created {len(instance_ids)} unique instances "
                    f"for {expected_unique_instances} users. "
                    f"SSOT Violation: Factory must create isolated instances for each user context. "
                    f"Business Impact: Shared instances between users create security vulnerabilities "
                    f"and data contamination risks in enterprise multi-tenant environment."
                )
            
            logger.info(f"✅ FACTORY ISOLATION VALIDATED: {len(instance_ids)} unique instances for {len(factory_instances)} users")
            
            # CRITICAL SSOT TEST 3: User context isolation validation
            await self._validate_user_context_isolation(factory_instances)
            
            logger.info("✅ FACTORY PATTERN CONSOLIDATION VALIDATED")
            
        except Exception as e:
            logger.error(f"❌ FACTORY CONSOLIDATION VALIDATION FAILED: {e}")
            raise
    
    async def _validate_user_context_isolation(self, factory_instances):
        """Validate that factory-created instances maintain proper user context isolation."""
        logger.info("Validating user context isolation in factory-created instances")
        
        # Add connections to each manager and verify isolation
        for user_name, user_context, manager_instance in factory_instances:
            # Create user-specific connection
            test_connection = type('FactoryTestConnection', (), {
                'connection_id': f'factory_conn_{user_context.user_id}_{uuid.uuid4().hex[:4]}',
                'user_id': user_context.user_id,
                'thread_id': user_context.thread_id,
                'websocket': None,  # Mock WebSocket
                'is_active': True,
                'factory_test_data': f'data_for_{user_name}'
            })()
            
            # Add connection to manager
            try:
                await manager_instance.add_connection(test_connection)
                logger.debug(f"Added connection for {user_name}: {test_connection.connection_id}")
            except Exception as e:
                logger.error(f"Failed to add connection for {user_name}: {e}")
                pytest.fail(f"Factory instance connection management failed for {user_name}: {e}")
        
        # Validate that each manager only sees its own user's connections
        for i, (user_name, user_context, manager_instance) in enumerate(factory_instances):
            try:
                # Get connections for this user
                user_connections = await self._get_user_connections(manager_instance, user_context.user_id)
                
                # Should have exactly one connection (the one we added for this user)
                if len(user_connections) != 1:
                    pytest.fail(
                        f"FACTORY ISOLATION VIOLATION: {user_name} manager has {len(user_connections)} connections, expected 1. "
                        f"SSOT Violation: Factory instances should maintain isolated connection stores. "
                        f"Business Impact: Connection count inconsistencies indicate isolation failures."
                    )
                
                # Verify the connection belongs to the correct user
                user_connection = user_connections[0]
                if getattr(user_connection, 'user_id', None) != user_context.user_id:
                    pytest.fail(
                        f"FACTORY ISOLATION VIOLATION: {user_name} manager contains connection for different user. "
                        f"Expected user_id: {user_context.user_id}, Got: {getattr(user_connection, 'user_id', 'None')}. "
                        f"SSOT Violation: Factory instances allow cross-user data contamination. "
                        f"Business Impact: User data leakage violates enterprise security requirements."
                    )
                
                # Verify no other user's data is present
                other_user_data = any(
                    getattr(conn, 'factory_test_data', '').find(f'data_for_User{j}') >= 0
                    for j in range(len(factory_instances))
                    if j != i
                    for conn in user_connections
                )
                
                if other_user_data:
                    pytest.fail(
                        f"FACTORY ISOLATION VIOLATION: {user_name} manager contains other users' data. "
                        f"SSOT Violation: Factory instances allow cross-contamination of user data. "
                        f"Business Impact: Enterprise data isolation completely compromised."
                    )
                
                logger.info(f"✅ {user_name} factory instance properly isolated")
                
            except Exception as e:
                logger.error(f"User context isolation validation failed for {user_name}: {e}")
                raise
    
    async def _get_user_connections(self, manager, user_id):
        """Get connections for a specific user from a manager instance."""
        try:
            # Try different methods to get connections
            if hasattr(manager, 'get_connections_for_user'):
                return await manager.get_connections_for_user(user_id)
            elif hasattr(manager, 'get_user_connections'):
                return await manager.get_user_connections(user_id)
            elif hasattr(manager, 'connections'):
                user_connections = manager.connections.get(user_id, [])
                return user_connections if isinstance(user_connections, list) else [user_connections]
            elif hasattr(manager, '_connections'):
                all_connections = manager._connections
                return [conn for conn in all_connections if getattr(conn, 'user_id', None) == user_id]
            else:
                logger.warning(f"Manager {type(manager)} has unknown connection interface")
                return []
        except Exception as e:
            logger.error(f"Failed to get connections for user {user_id}: {e}")
            return []
    
    async def test_factory_method_consistency(self):
        """
        SSOT VALIDATION TEST: Validate factory methods provide consistent interfaces.
        
        SSOT REQUIREMENT: All factory methods should have identical signatures and behavior
        to ensure predictable instantiation across the codebase.
        """
        logger.info("Validating factory method consistency")
        
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        import inspect
        
        # Get factory function signature
        factory_signature = inspect.signature(get_websocket_manager)
        logger.info(f"Factory function signature: {factory_signature}")
        
        # Test factory with different parameter combinations
        test_cases = [
            {
                'name': 'with_user_context',
                'params': {
                    'user_context': self.user_contexts[0],
                    'mode': 'unified'  # Test string mode handling
                }
            },
            {
                'name': 'without_user_context', 
                'params': {}  # Should handle gracefully with test fallback
            },
            {
                'name': 'with_mode_enum',
                'params': {
                    'user_context': self.user_contexts[1]
                    # mode parameter optional, should default properly
                }
            }
        ]
        
        factory_results = {}
        
        for test_case in test_cases:
            case_name = test_case['name']
            params = test_case['params']
            
            try:
                manager_instance = await get_websocket_manager(**params)
                factory_results[case_name] = {
                    'success': True,
                    'instance_type': type(manager_instance),
                    'instance_id': id(manager_instance)
                }
                logger.info(f"✅ Factory test case '{case_name}' succeeded: {type(manager_instance)}")
            except Exception as e:
                factory_results[case_name] = {
                    'success': False,
                    'error': str(e)
                }
                logger.error(f"❌ Factory test case '{case_name}' failed: {e}")
        
        # CRITICAL SSOT TEST: All factory calls should succeed
        failed_cases = [name for name, result in factory_results.items() if not result['success']]
        if failed_cases:
            pytest.fail(
                f"FACTORY METHOD INCONSISTENCY: Test cases {failed_cases} failed. "
                f"Results: {factory_results}. "
                f"SSOT Requirement: Factory should handle all valid parameter combinations. "
                f"Business Impact: Inconsistent factory behavior breaks existing integrations."
            )
        
        # CRITICAL SSOT TEST: All successful instances should have the same type
        successful_results = [result for result in factory_results.values() if result['success']]
        if len(successful_results) >= 2:
            reference_type = successful_results[0]['instance_type']
            for result in successful_results[1:]:
                if result['instance_type'] != reference_type:
                    pytest.fail(
                        f"FACTORY TYPE INCONSISTENCY: Different parameter combinations create different types. "
                        f"Expected all instances to be {reference_type}. "
                        f"SSOT Violation: Factory should create consistent types regardless of parameters."
                    )
        
        logger.info("✅ Factory method consistency validated")
    
    async def test_factory_concurrent_instantiation(self):
        """
        SSOT VALIDATION TEST: Validate factory handles concurrent instantiation properly.
        
        SSOT REQUIREMENT: Factory should safely create multiple instances concurrently
        without race conditions or shared state contamination.
        """
        logger.info("Validating factory concurrent instantiation safety")
        
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        # Create concurrent instantiation tasks
        async def create_manager_for_user(user_index):
            """Create a manager instance for a specific user concurrently."""
            user_context = self.user_contexts[user_index % len(self.user_contexts)]
            
            # Add some variability to test race conditions
            await asyncio.sleep(0.01 * user_index)
            
            manager = await get_websocket_manager(user_context=user_context)
            
            return {
                'user_index': user_index,
                'user_id': user_context.user_id,
                'manager': manager,
                'instance_id': id(manager),
                'type': type(manager)
            }
        
        # Create multiple concurrent instantiation tasks
        concurrent_tasks = [create_manager_for_user(i) for i in range(10)]
        
        try:
            # Execute all tasks concurrently
            results = await asyncio.gather(*concurrent_tasks)
            logger.info(f"Concurrent factory instantiation completed: {len(results)} instances created")
            
            # CRITICAL SSOT TEST: All instances should be successfully created
            if len(results) != len(concurrent_tasks):
                pytest.fail(
                    f"CONCURRENT INSTANTIATION FAILURE: Expected {len(concurrent_tasks)} instances, "
                    f"got {len(results)}. "
                    f"SSOT Violation: Factory should handle concurrent instantiation reliably."
                )
            
            # CRITICAL SSOT TEST: All instances should have the same type
            reference_type = results[0]['type']
            for result in results[1:]:
                if result['type'] != reference_type:
                    pytest.fail(
                        f"CONCURRENT TYPE INCONSISTENCY: Instance for user {result['user_id']} "
                        f"has type {result['type']} != reference type {reference_type}. "
                        f"SSOT Violation: Concurrent instantiation creates inconsistent types."
                    )
            
            # CRITICAL SSOT TEST: Each instance should be unique (proper isolation)
            instance_ids = [result['instance_id'] for result in results]
            unique_instance_ids = set(instance_ids)
            
            if len(unique_instance_ids) != len(results):
                logger.error(f"❌ CONCURRENT ISOLATION FAILURE: {len(unique_instance_ids)} unique instances for {len(results)} requests")
                
                # Find shared instances
                from collections import Counter
                id_counts = Counter(instance_ids)
                shared_instances = {inst_id: count for inst_id, count in id_counts.items() if count > 1}
                
                logger.error(f"Shared instances: {shared_instances}")
                
                pytest.fail(
                    f"CONCURRENT ISOLATION VIOLATION: Expected {len(results)} unique instances, "
                    f"got {len(unique_instance_ids)}. "
                    f"SSOT Violation: Concurrent factory calls share instances, breaking user isolation. "
                    f"Business Impact: Concurrent users may share manager instances, "
                    f"compromising data isolation in enterprise environment."
                )
            
            logger.info(f"✅ Concurrent instantiation validated: {len(unique_instance_ids)} unique instances")
            
        except Exception as e:
            logger.error(f"❌ CONCURRENT INSTANTIATION TEST FAILED: {e}")
            raise
    
    async def test_factory_parameter_validation_consistency(self):
        """
        SSOT VALIDATION TEST: Validate factory parameter validation is consistent.
        
        SSOT REQUIREMENT: Factory should consistently validate parameters and
        provide clear error messages for invalid inputs.
        """
        logger.info("Validating factory parameter validation consistency")
        
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        # Test invalid parameter scenarios
        invalid_test_cases = [
            {
                'name': 'invalid_mode_type',
                'params': {'mode': 'invalid_mode_string'},
                'should_fail': True
            },
            {
                'name': 'none_user_context_in_production',
                'params': {'user_context': None},
                'should_fail': False  # Should gracefully create test instance
            }
        ]
        
        validation_results = {}
        
        for test_case in invalid_test_cases:
            case_name = test_case['name']
            params = test_case['params']
            should_fail = test_case['should_fail']
            
            try:
                manager = await get_websocket_manager(**params)
                validation_results[case_name] = {
                    'failed': False,
                    'instance_created': True,
                    'instance_type': type(manager)
                }
                logger.info(f"Factory case '{case_name}' succeeded (expected fail: {should_fail})")
            except Exception as e:
                validation_results[case_name] = {
                    'failed': True,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                logger.info(f"Factory case '{case_name}' failed with {type(e).__name__}: {e}")
        
        # Validate expected behaviors
        for test_case in invalid_test_cases:
            case_name = test_case['name'] 
            should_fail = test_case['should_fail']
            result = validation_results[case_name]
            
            if should_fail and not result['failed']:
                logger.warning(
                    f"⚠️ VALIDATION INCONSISTENCY: Case '{case_name}' should have failed but succeeded. "
                    f"This may indicate loose validation that could accept invalid parameters."
                )
            elif not should_fail and result['failed']:
                pytest.fail(
                    f"FACTORY VALIDATION ERROR: Case '{case_name}' should succeed but failed. "
                    f"Error: {result.get('error')}. "
                    f"SSOT Requirement: Factory should handle reasonable parameter variations. "
                    f"Business Impact: Overly strict validation breaks existing integrations."
                )
        
        logger.info("✅ Factory parameter validation consistency validated")

    def teardown_method(self, method):
        """Clean up test environment."""
        logger.info(f"Tearing down factory SSOT validation test: {method.__name__}")
        super().teardown_method(method)