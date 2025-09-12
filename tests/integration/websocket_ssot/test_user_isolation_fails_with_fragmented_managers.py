"""Test User Isolation Failures with Fragmented WebSocket Managers - Phase 1 Reproduction Test

This test validates Issue #564: User isolation failures due to WebSocket manager fragmentation.

CRITICAL BUSINESS CONTEXT:
- Issue: Multiple WebSocket manager instances cause user data contamination
- Business Impact: $500K+ ARR at risk due to enterprise customer data leakage
- SSOT Violation: Fragmented managers create separate user context stores
- Golden Path Impact: Multi-tenant chat environment compromised by user data cross-contamination

TEST PURPOSE:
This test MUST FAIL initially to prove user isolation violations exist, then PASS after SSOT consolidation.
It demonstrates that fragmented managers allow user data to leak between isolated contexts.

Expected Behavior:
- BEFORE SSOT Fix: FAIL (user data contamination between different manager instances)
- AFTER SSOT Fix: PASS (perfect user isolation with consolidated SSOT manager)

Business Value Justification:
- Segment: Enterprise (highest security requirements)
- Business Goal: Ensure user data isolation for multi-tenant Golden Path
- Value Impact: Protects enterprise customer trust and regulatory compliance
- Revenue Impact: Prevents user data contamination affecting $500K+ ARR enterprise accounts
"""

import pytest
import asyncio
import uuid
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestUserIsolationFailsWithFragmentedManagers(SSotAsyncTestCase):
    """Phase 1 Reproduction Test: Prove user isolation fails with fragmented managers."""
    
    def setup_method(self, method):
        """Set up test environment with multiple isolated user contexts."""
        super().setup_method(method)
        logger.info(f"Setting up user isolation test: {method.__name__}")
        
        # Create isolated user contexts for testing
        self.user_context_1 = type('UserContext1', (), {
            'user_id': f'enterprise_user_1_{uuid.uuid4().hex[:8]}',
            'thread_id': f'thread_1_{uuid.uuid4().hex[:8]}',
            'request_id': f'request_1_{uuid.uuid4().hex[:8]}',
            'is_test': True,
            'tenant_id': 'enterprise_tenant_alpha'
        })()
        
        self.user_context_2 = type('UserContext2', (), {
            'user_id': f'enterprise_user_2_{uuid.uuid4().hex[:8]}',
            'thread_id': f'thread_2_{uuid.uuid4().hex[:8]}',
            'request_id': f'request_2_{uuid.uuid4().hex[:8]}',
            'is_test': True,
            'tenant_id': 'enterprise_tenant_beta'
        })()
        
        logger.info(f"Created isolated contexts: User1={self.user_context_1.user_id}, User2={self.user_context_2.user_id}")
        
    async def test_fragmented_managers_allow_user_data_contamination(self):
        """
        CRITICAL REPRODUCTION TEST: Prove fragmented managers allow user data to leak between contexts.
        
        SSOT VIOLATION: Each user should have completely isolated data contexts. Fragmented
        managers create separate storage systems that can be accidentally cross-referenced.
        
        Expected Results:
        - BEFORE SSOT Fix: This test FAILS (user data contamination detected)
        - AFTER SSOT Fix: This test PASSES (perfect user isolation maintained)
        """
        logger.info("Testing user data isolation with potentially fragmented managers")
        
        # Import different manager implementations to test isolation
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager as factory1
        from netra_backend.app.websocket_core.manager import WebSocketManager as DirectManager
        from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode, UnifiedWebSocketManager
        
        try:
            # Create managers for each user via different import paths
            manager1 = await factory1(user_context=self.user_context_1, mode=WebSocketManagerMode.UNIFIED)
            manager2 = DirectManager(mode=WebSocketManagerMode.UNIFIED, user_context=self.user_context_2)
            
            logger.info(f"Created Manager1 for User1: {type(manager1)}")
            logger.info(f"Created Manager2 for User2: {type(manager2)}")
            
            # Add user-specific connections to test isolation
            # This simulates real WebSocket connections for each user
            test_connection_1 = type('MockConnection1', (), {
                'connection_id': f'conn_1_{uuid.uuid4().hex[:8]}',
                'user_id': self.user_context_1.user_id,
                'thread_id': self.user_context_1.thread_id,
                'websocket': None,  # Mock WebSocket object
                'is_active': True,
                'tenant_data': {'sensitive_data': 'user1_confidential_info'}
            })()
            
            test_connection_2 = type('MockConnection2', (), {
                'connection_id': f'conn_2_{uuid.uuid4().hex[:8]}',
                'user_id': self.user_context_2.user_id,
                'thread_id': self.user_context_2.thread_id,
                'websocket': None,  # Mock WebSocket object
                'is_active': True,
                'tenant_data': {'sensitive_data': 'user2_confidential_info'}
            })()
            
            # Add connections to respective managers
            await manager1.add_connection(test_connection_1)
            await manager2.add_connection(test_connection_2)
            
            logger.info("Added user-specific connections to respective managers")
            
            # CRITICAL USER ISOLATION TEST: Each manager should only see its own user's data
            
            # Test 1: Manager1 should only have User1's connections
            manager1_connections = await self._get_user_connections(manager1, self.user_context_1.user_id)
            logger.info(f"Manager1 connections count: {len(manager1_connections)}")
            
            # Check that Manager1 contains User1's connection
            user1_connection_found = any(
                conn.user_id == self.user_context_1.user_id 
                for conn in manager1_connections
            )
            assert user1_connection_found, (
                f"ISOLATION FAILURE: Manager1 missing User1's connection. "
                f"Expected User1 connection with user_id={self.user_context_1.user_id}. "
                f"Business Impact: User cannot access their own connections."
            )
            
            # CRITICAL TEST: Manager1 should NOT contain User2's connection (isolation check)
            user2_connection_in_manager1 = any(
                conn.user_id == self.user_context_2.user_id
                for conn in manager1_connections
            )
            
            if user2_connection_in_manager1:
                logger.error("❌ CRITICAL USER ISOLATION VIOLATION: Manager1 contains User2's connection!")
                logger.error(f"User1 manager can access User2's data: {self.user_context_2.user_id}")
                logger.error("This represents a severe security breach in multi-tenant environment")
                
                # Log sensitive data exposure
                for conn in manager1_connections:
                    if conn.user_id == self.user_context_2.user_id:
                        logger.error(f"EXPOSED DATA: {getattr(conn, 'tenant_data', 'No tenant data')}")
                
                pytest.fail(
                    f"USER ISOLATION VIOLATION DETECTED: Manager1 (User1) can access Manager2 (User2) connections. "
                    f"This proves SSOT fragmentation allows cross-user data contamination. "
                    f"BUSINESS IMPACT: Enterprise customer data leakage violating security requirements, "
                    f"potentially affecting $500K+ ARR from enterprise accounts requiring strict isolation."
                )
            
            logger.info("✅ User1 manager properly isolated from User2 data")
            
            # Test 2: Manager2 should only have User2's connections  
            manager2_connections = await self._get_user_connections(manager2, self.user_context_2.user_id)
            logger.info(f"Manager2 connections count: {len(manager2_connections)}")
            
            # Check that Manager2 contains User2's connection
            user2_connection_found = any(
                conn.user_id == self.user_context_2.user_id
                for conn in manager2_connections  
            )
            assert user2_connection_found, (
                f"ISOLATION FAILURE: Manager2 missing User2's connection. "
                f"Expected User2 connection with user_id={self.user_context_2.user_id}. "
                f"Business Impact: User cannot access their own connections."
            )
            
            # CRITICAL TEST: Manager2 should NOT contain User1's connection (isolation check)
            user1_connection_in_manager2 = any(
                conn.user_id == self.user_context_1.user_id
                for conn in manager2_connections
            )
            
            if user1_connection_in_manager2:
                logger.error("❌ CRITICAL USER ISOLATION VIOLATION: Manager2 contains User1's connection!")
                logger.error(f"User2 manager can access User1's data: {self.user_context_1.user_id}")
                
                pytest.fail(
                    f"USER ISOLATION VIOLATION DETECTED: Manager2 (User2) can access Manager1 (User1) connections. "
                    f"This proves SSOT fragmentation creates bidirectional data contamination. "
                    f"BUSINESS IMPACT: Enterprise multi-tenant isolation completely compromised."
                )
                
            logger.info("✅ User2 manager properly isolated from User1 data")
            
            # Test 3: Cross-manager state verification
            await self._verify_cross_manager_isolation(manager1, manager2)
            
            logger.info("✅ User isolation test PASSED - managers properly isolated")
            
        except Exception as e:
            logger.error(f"❌ USER ISOLATION TEST FAILED: {e}")
            raise
    
    async def _get_user_connections(self, manager, user_id):
        """Get connections for a specific user from a manager."""
        try:
            # Try different methods to get connections based on manager interface
            if hasattr(manager, 'get_connections_for_user'):
                return await manager.get_connections_for_user(user_id)
            elif hasattr(manager, 'get_user_connections'):
                return await manager.get_user_connections(user_id)
            elif hasattr(manager, 'connections') and hasattr(manager.connections, 'get'):
                # Handle dictionary-based connection storage
                user_connections = manager.connections.get(user_id, [])
                return user_connections if isinstance(user_connections, list) else [user_connections]
            elif hasattr(manager, '_connections'):
                # Handle private connection storage
                all_connections = manager._connections
                return [conn for conn in all_connections if getattr(conn, 'user_id', None) == user_id]
            else:
                logger.warning(f"Manager {type(manager)} has unknown connection interface")
                return []
        except Exception as e:
            logger.error(f"Failed to get connections for user {user_id}: {e}")
            return []
    
    async def _verify_cross_manager_isolation(self, manager1, manager2):
        """Verify that managers don't share internal state."""
        logger.info("Verifying cross-manager state isolation")
        
        # Test that managers have independent internal state
        try:
            # Check if managers share the same connection storage
            if hasattr(manager1, 'connections') and hasattr(manager2, 'connections'):
                manager1_storage_id = id(manager1.connections)
                manager2_storage_id = id(manager2.connections)
                
                if manager1_storage_id == manager2_storage_id:
                    logger.error("❌ SHARED STATE VIOLATION: Managers share connection storage!")
                    pytest.fail(
                        f"SHARED STATE DETECTED: Manager1 and Manager2 share connection storage "
                        f"(storage_id={manager1_storage_id}). "
                        f"SSOT Violation: Fragmented managers should have isolated state storage. "
                        f"Business Impact: Shared state creates cross-contamination risk."
                    )
                
                logger.info(f"✅ Managers have independent connection storage: {manager1_storage_id} != {manager2_storage_id}")
            
            # Check if managers are the same instance (should be different for proper isolation)
            manager1_instance_id = id(manager1)
            manager2_instance_id = id(manager2)
            
            if manager1_instance_id == manager2_instance_id:
                logger.error("❌ INSTANCE SHARING VIOLATION: Same manager instance used for different users!")
                pytest.fail(
                    f"INSTANCE SHARING DETECTED: Same manager instance ({manager1_instance_id}) used for "
                    f"different user contexts. "
                    f"SSOT Violation: User isolation requires separate manager instances. "
                    f"Business Impact: Single instance shared between users creates contamination risk."
                )
            
            logger.info(f"✅ Managers are properly isolated instances: {manager1_instance_id} != {manager2_instance_id}")
            
        except Exception as e:
            logger.error(f"Cross-manager isolation verification failed: {e}")
            raise
    
    async def test_concurrent_user_operations_isolation(self):
        """
        REPRODUCTION TEST: Verify concurrent operations maintain user isolation.
        
        SSOT VIOLATION: Concurrent operations on fragmented managers may cause
        race conditions that break user isolation boundaries.
        """
        logger.info("Testing concurrent user operations isolation")
        
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
        
        try:
            # Create managers for concurrent testing
            manager1 = await get_websocket_manager(user_context=self.user_context_1)
            manager2 = await get_websocket_manager(user_context=self.user_context_2)
            
            # Create concurrent operations for each user
            async def user1_operations():
                """Simulate User1's WebSocket operations."""
                for i in range(10):
                    connection = type('ConcurrentConnection1', (), {
                        'connection_id': f'concurrent_1_{i}_{uuid.uuid4().hex[:4]}',
                        'user_id': self.user_context_1.user_id,
                        'operation_data': f'user1_operation_{i}'
                    })()
                    
                    await manager1.add_connection(connection)
                    await asyncio.sleep(0.01)  # Small delay to create concurrency
                    
            async def user2_operations():
                """Simulate User2's WebSocket operations."""
                for i in range(10):
                    connection = type('ConcurrentConnection2', (), {
                        'connection_id': f'concurrent_2_{i}_{uuid.uuid4().hex[:4]}',
                        'user_id': self.user_context_2.user_id,
                        'operation_data': f'user2_operation_{i}'
                    })()
                    
                    await manager2.add_connection(connection)
                    await asyncio.sleep(0.01)  # Small delay to create concurrency
            
            # Execute concurrent operations
            await asyncio.gather(user1_operations(), user2_operations())
            
            # Verify isolation after concurrent operations
            user1_connections = await self._get_user_connections(manager1, self.user_context_1.user_id)
            user2_connections = await self._get_user_connections(manager2, self.user_context_2.user_id)
            
            logger.info(f"After concurrent ops - User1: {len(user1_connections)}, User2: {len(user2_connections)}")
            
            # Check for cross-contamination in concurrent scenario
            user2_data_in_user1 = any(
                getattr(conn, 'operation_data', '').startswith('user2_')
                for conn in user1_connections
            )
            
            user1_data_in_user2 = any(
                getattr(conn, 'operation_data', '').startswith('user1_')
                for conn in user2_connections
            )
            
            if user2_data_in_user1 or user1_data_in_user2:
                logger.error("❌ CONCURRENT ISOLATION VIOLATION: User data mixed during concurrent operations!")
                pytest.fail(
                    f"CONCURRENT ISOLATION FAILURE: User data contamination detected during concurrent operations. "
                    f"User2 data in User1: {user2_data_in_user1}, User1 data in User2: {user1_data_in_user2}. "
                    f"SSOT Violation: Fragmented managers create race conditions that break isolation. "
                    f"Business Impact: Concurrent user operations cause data contamination in enterprise environment."
                )
            
            logger.info("✅ Concurrent operations maintained proper user isolation")
            
        except Exception as e:
            logger.error(f"❌ CONCURRENT ISOLATION TEST FAILED: {e}")
            raise

    def teardown_method(self, method):
        """Clean up test environment."""
        logger.info(f"Tearing down user isolation test: {method.__name__}")
        super().teardown_method(method)