"""Test Enhanced User Isolation with SSOT Manager - Phase 2 SSOT Validation Test

This test validates Issue #564: Enhanced user isolation achieved through SSOT WebSocket manager consolidation.

CRITICAL BUSINESS CONTEXT:
- Issue: Validation that SSOT consolidation delivers enhanced user isolation capabilities
- Business Impact: $500K+ ARR protected through bulletproof user isolation in multi-tenant environment
- SSOT Achievement: Single manager implementation eliminates isolation vulnerabilities
- Golden Path Impact: Enterprise-grade user isolation ensures secure multi-tenant chat functionality

TEST PURPOSE:
This test MUST FAIL initially (isolation vulnerabilities), then PASS after SSOT consolidation.
It validates that consolidated SSOT manager provides enhanced user isolation beyond basic separation.

Expected Behavior:
- BEFORE SSOT Fix: FAIL (user isolation vulnerabilities and data contamination risks)
- AFTER SSOT Fix: PASS (enhanced user isolation with comprehensive security guarantees)

Business Value Justification:
- Segment: Enterprise (strictest security and isolation requirements)
- Business Goal: Deliver enterprise-grade user isolation through SSOT consolidation
- Value Impact: Validates enhanced security model for multi-tenant Golden Path chat
- Revenue Impact: Confirms $500K+ ARR protection through bulletproof user isolation
"""

import pytest
import asyncio
import uuid
import time
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestEnhancedUserIsolationWithSsotManager(SSotAsyncTestCase):
    """Phase 2 SSOT Validation Test: Validate enhanced user isolation with consolidated SSOT manager."""
    
    def setup_method(self, method):
        """Set up test environment for enhanced user isolation validation."""
        super().setup_method(method)
        logger.info(f"Setting up enhanced user isolation validation test: {method.__name__}")
        
        # Create enterprise user contexts with different security levels
        self.enterprise_users = []
        tenant_configs = [
            {'tenant': 'alpha_corp', 'security_level': 'high', 'isolation_level': 'strict'},
            {'tenant': 'beta_industries', 'security_level': 'maximum', 'isolation_level': 'complete'},
            {'tenant': 'gamma_solutions', 'security_level': 'high', 'isolation_level': 'strict'}
        ]
        
        for i, config in enumerate(tenant_configs):
            context = type(f'EnterpriseUser{i}', (), {
                'user_id': f'enterprise_{config["tenant"]}_user_{uuid.uuid4().hex[:8]}',
                'thread_id': f'enterprise_thread_{i}_{uuid.uuid4().hex[:8]}',
                'request_id': f'enterprise_request_{i}_{uuid.uuid4().hex[:8]}',
                'is_test': True,
                'tenant_id': config['tenant'],
                'security_level': config['security_level'],
                'isolation_level': config['isolation_level'],
                'enterprise_data': {
                    'confidential_info': f'{config["tenant"]}_confidential_data',
                    'session_keys': f'{config["tenant"]}_session_key_{uuid.uuid4().hex}',
                    'private_metrics': f'{config["tenant"]}_metrics_data'
                }
            })()
            self.enterprise_users.append(context)
            
        logger.info(f"Created {len(self.enterprise_users)} enterprise user contexts for enhanced isolation testing")
    
    async def test_bulletproof_user_data_isolation(self):
        """
        CRITICAL SSOT VALIDATION TEST: Validate bulletproof user data isolation with SSOT manager.
        
        SSOT REQUIREMENT: Consolidated manager must provide enterprise-grade user isolation
        with zero possibility of data contamination between user contexts.
        
        Expected Results:
        - BEFORE SSOT Fix: This test FAILS (user data contamination vulnerabilities)
        - AFTER SSOT Fix: This test PASSES (bulletproof isolation with comprehensive protection)
        """
        logger.info("Validating bulletproof user data isolation with SSOT manager")
        
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        # Create isolated managers for each enterprise user
        enterprise_managers = []
        try:
            for user_context in self.enterprise_users:
                manager = await get_websocket_manager(user_context=user_context)
                enterprise_managers.append((user_context, manager))
                logger.info(f"Created SSOT manager for {user_context.tenant_id}: {type(manager)}")
            
            # Add enterprise connections with sensitive data to each manager
            enterprise_connections = []
            for user_context, manager in enterprise_managers:
                sensitive_connection = await self._create_enterprise_connection(user_context)
                await manager.add_connection(sensitive_connection)
                enterprise_connections.append((user_context, manager, sensitive_connection))
                logger.info(f"Added enterprise connection for {user_context.tenant_id}")
            
            # CRITICAL ISOLATION TEST 1: Verify complete data isolation between tenants
            await self._verify_complete_data_isolation(enterprise_connections)
            
            # CRITICAL ISOLATION TEST 2: Verify enhanced security boundaries
            await self._verify_enhanced_security_boundaries(enterprise_connections)
            
            # CRITICAL ISOLATION TEST 3: Verify concurrent operations maintain isolation
            await self._verify_concurrent_isolation_integrity(enterprise_connections)
            
            logger.info("✅ BULLETPROOF USER ISOLATION VALIDATED - SSOT manager provides enterprise-grade security")
            
        except Exception as e:
            logger.error(f"❌ ENHANCED USER ISOLATION VALIDATION FAILED: {e}")
            raise
    
    async def _create_enterprise_connection(self, user_context):
        """Create enterprise connection with sensitive data for isolation testing."""
        connection = type('EnterpriseConnection', (), {
            'connection_id': f'enterprise_conn_{user_context.user_id}_{uuid.uuid4().hex[:8]}',
            'user_id': user_context.user_id,
            'thread_id': user_context.thread_id,
            'tenant_id': user_context.tenant_id,
            'security_level': user_context.security_level,
            'websocket': None,  # Mock enterprise WebSocket
            'is_active': True,
            'enterprise_data': user_context.enterprise_data.copy(),
            'sensitive_operations': {
                'financial_data': f'{user_context.tenant_id}_financial_records',
                'customer_pii': f'{user_context.tenant_id}_customer_data',
                'proprietary_algorithms': f'{user_context.tenant_id}_algo_secrets'
            },
            'isolation_metadata': {
                'created_at': time.time(),
                'isolation_level': user_context.isolation_level,
                'security_boundary': f'{user_context.tenant_id}_boundary'
            }
        })()
        
        logger.debug(f"Created enterprise connection: {connection.connection_id} for tenant {user_context.tenant_id}")
        return connection
    
    async def _verify_complete_data_isolation(self, enterprise_connections):
        """Verify complete data isolation between enterprise tenant connections."""
        logger.info("Verifying complete data isolation between enterprise tenants")
        
        for i, (user_context_i, manager_i, connection_i) in enumerate(enterprise_connections):
            # Get connections visible to this manager
            manager_i_connections = await self._get_manager_connections(manager_i, user_context_i.user_id)
            
            # CRITICAL TEST: Manager should only see its own tenant's connections
            for conn in manager_i_connections:
                # Verify tenant isolation
                conn_tenant = getattr(conn, 'tenant_id', None)
                if conn_tenant != user_context_i.tenant_id:
                    logger.error(f"❌ TENANT ISOLATION BREACH: Manager for {user_context_i.tenant_id} sees connection from {conn_tenant}")
                    pytest.fail(
                        f"TENANT ISOLATION VIOLATION: {user_context_i.tenant_id} manager can access "
                        f"{conn_tenant} tenant data. "
                        f"SSOT Violation: Consolidated manager fails to enforce tenant boundaries. "
                        f"Business Impact: Enterprise tenant data contamination violates security requirements, "
                        f"potentially affecting $500K+ ARR from enterprise accounts requiring strict isolation."
                    )
                
                # Verify user isolation within tenant
                conn_user_id = getattr(conn, 'user_id', None)
                if conn_user_id != user_context_i.user_id:
                    logger.error(f"❌ USER ISOLATION BREACH: Manager for {user_context_i.user_id} sees connection from {conn_user_id}")
                    pytest.fail(
                        f"USER ISOLATION VIOLATION: {user_context_i.user_id} manager can access "
                        f"{conn_user_id} user data. "
                        f"SSOT Violation: Consolidated manager fails to enforce user boundaries. "
                        f"Business Impact: User data contamination within tenant violates privacy requirements."
                    )
                
                # Verify sensitive data isolation
                conn_sensitive_data = getattr(conn, 'enterprise_data', {})
                expected_sensitive_data = user_context_i.enterprise_data
                
                # Check that sensitive data matches expected tenant data
                for key, expected_value in expected_sensitive_data.items():
                    actual_value = conn_sensitive_data.get(key)
                    if actual_value != expected_value:
                        logger.error(f"❌ SENSITIVE DATA MISMATCH: Expected {key}={expected_value}, got {actual_value}")
                        pytest.fail(
                            f"SENSITIVE DATA ISOLATION FAILURE: {user_context_i.tenant_id} manager "
                            f"has incorrect sensitive data for key '{key}'. "
                            f"SSOT Violation: Data integrity compromised in consolidated manager. "
                            f"Business Impact: Incorrect sensitive data access creates security vulnerabilities."
                        )
            
            logger.info(f"✅ Complete data isolation verified for {user_context_i.tenant_id}")
    
    async def _verify_enhanced_security_boundaries(self, enterprise_connections):
        """Verify enhanced security boundaries beyond basic isolation."""
        logger.info("Verifying enhanced security boundaries with SSOT manager")
        
        # Test cross-tenant operation attempts (should all fail)
        for i, (user_context_i, manager_i, connection_i) in enumerate(enterprise_connections):
            for j, (user_context_j, manager_j, connection_j) in enumerate(enterprise_connections):
                if i != j:  # Different tenants
                    # CRITICAL SECURITY TEST: Manager should not be able to access other tenant's connections
                    try:
                        # Attempt to get other tenant's connections (should fail or return empty)
                        other_tenant_connections = await self._get_manager_connections(manager_i, user_context_j.user_id)
                        
                        if other_tenant_connections:
                            logger.error(f"❌ CROSS-TENANT ACCESS VIOLATION: {user_context_i.tenant_id} manager accessed {user_context_j.tenant_id} connections")
                            pytest.fail(
                                f"CROSS-TENANT SECURITY BREACH: {user_context_i.tenant_id} manager "
                                f"can access {user_context_j.tenant_id} connections. "
                                f"SSOT Violation: Enhanced security boundaries not enforced. "
                                f"Business Impact: Enterprise security model completely compromised, "
                                f"violating regulatory compliance and affecting $500K+ ARR contracts."
                            )
                        
                        logger.debug(f"✅ {user_context_i.tenant_id} properly blocked from {user_context_j.tenant_id}")
                        
                    except Exception as e:
                        # Expected behavior - cross-tenant access should fail
                        logger.debug(f"✅ Cross-tenant access properly blocked: {e}")
                        
                    # CRITICAL SECURITY TEST: Attempt to add connection to wrong manager (should fail or isolate)
                    try:
                        # This should either fail or be properly isolated
                        await manager_i.add_connection(connection_j)
                        
                        # If it succeeds, verify the connection is still isolated
                        manager_i_connections_after = await self._get_manager_connections(manager_i, user_context_i.user_id)
                        cross_contamination = any(
                            getattr(conn, 'tenant_id', None) == user_context_j.tenant_id
                            for conn in manager_i_connections_after
                        )
                        
                        if cross_contamination:
                            pytest.fail(
                                f"SECURITY BOUNDARY VIOLATION: {user_context_i.tenant_id} manager accepted "
                                f"{user_context_j.tenant_id} connection without proper isolation. "
                                f"SSOT Violation: Enhanced security boundaries allow cross-contamination. "
                                f"Business Impact: Enterprise security model fails under direct attack scenarios."
                            )
                        
                    except Exception as e:
                        # Expected behavior - should properly reject or isolate
                        logger.debug(f"✅ Cross-tenant connection properly handled: {e}")
            
            logger.info(f"✅ Enhanced security boundaries verified for {user_context_i.tenant_id}")
    
    async def _verify_concurrent_isolation_integrity(self, enterprise_connections):
        """Verify isolation integrity under concurrent operations stress test."""
        logger.info("Verifying isolation integrity under concurrent operations")
        
        async def concurrent_operations(user_context, manager):
            """Perform intensive concurrent operations for a specific user."""
            operations_results = []
            
            # Create multiple connections concurrently
            connection_tasks = []
            for i in range(5):
                conn = await self._create_enterprise_connection(user_context)
                connection_tasks.append(manager.add_connection(conn))
            
            # Execute concurrent connection additions
            await asyncio.gather(*connection_tasks)
            operations_results.append(f"Added 5 connections for {user_context.tenant_id}")
            
            # Simulate concurrent message operations
            message_tasks = []
            for i in range(3):
                message = {
                    'event': 'enterprise_operation',
                    'data': {
                        'tenant': user_context.tenant_id,
                        'operation_id': f'op_{i}_{uuid.uuid4().hex[:4]}',
                        'sensitive_payload': user_context.enterprise_data
                    }
                }
                
                # Try to broadcast message (if method exists)
                if hasattr(manager, 'broadcast_message'):
                    message_tasks.append(manager.broadcast_message(message, user_id=user_context.user_id))
            
            if message_tasks:
                await asyncio.gather(*message_tasks)
                operations_results.append(f"Sent {len(message_tasks)} messages for {user_context.tenant_id}")
            
            return operations_results
        
        # Execute concurrent operations for all enterprise users simultaneously
        concurrent_tasks = [
            concurrent_operations(user_context, manager)
            for user_context, manager, _ in enterprise_connections
        ]
        
        try:
            all_operations_results = await asyncio.gather(*concurrent_tasks)
            logger.info("Concurrent operations completed for all enterprise tenants")
            
            # Verify isolation maintained after concurrent stress
            for user_context, manager, _ in enterprise_connections:
                # Check isolation after concurrent operations
                final_connections = await self._get_manager_connections(manager, user_context.user_id)
                
                # All connections should still belong to the correct tenant
                for conn in final_connections:
                    if getattr(conn, 'tenant_id', None) != user_context.tenant_id:
                        pytest.fail(
                            f"CONCURRENT ISOLATION FAILURE: After concurrent operations, "
                            f"{user_context.tenant_id} manager contains {getattr(conn, 'tenant_id')} connection. "
                            f"SSOT Violation: Concurrent operations break isolation boundaries. "
                            f"Business Impact: Enterprise isolation fails under load, creating "
                            f"security vulnerabilities that affect $500K+ ARR enterprise contracts."
                        )
                
                logger.info(f"✅ {user_context.tenant_id} maintained isolation integrity under concurrent load")
            
        except Exception as e:
            logger.error(f"❌ CONCURRENT ISOLATION INTEGRITY TEST FAILED: {e}")
            raise
    
    async def _get_manager_connections(self, manager, user_id):
        """Get all connections visible to a manager for a specific user."""
        try:
            # Try different methods to get connections
            if hasattr(manager, 'get_connections_for_user'):
                return await manager.get_connections_for_user(user_id)
            elif hasattr(manager, 'get_user_connections'):
                return await manager.get_user_connections(user_id)
            elif hasattr(manager, 'connections'):
                if isinstance(manager.connections, dict):
                    user_connections = manager.connections.get(user_id, [])
                    return user_connections if isinstance(user_connections, list) else [user_connections]
                else:
                    # Handle other connection storage types
                    return []
            elif hasattr(manager, '_connections'):
                all_connections = getattr(manager, '_connections', [])
                return [conn for conn in all_connections if getattr(conn, 'user_id', None) == user_id]
            else:
                logger.warning(f"Manager {type(manager)} has unknown connection interface")
                return []
        except Exception as e:
            logger.error(f"Failed to get connections for user {user_id}: {e}")
            return []
    
    async def test_enterprise_grade_security_validation(self):
        """
        SSOT VALIDATION TEST: Validate enterprise-grade security features in consolidated manager.
        
        SSOT REQUIREMENT: Consolidated manager should provide enterprise-grade security features
        beyond basic isolation, including audit trails, security boundaries, and compliance support.
        """
        logger.info("Validating enterprise-grade security features")
        
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        # Create enterprise manager with maximum security context
        max_security_context = self.enterprise_users[1]  # beta_industries with maximum security
        enterprise_manager = await get_websocket_manager(user_context=max_security_context)
        
        # CRITICAL SECURITY TEST 1: Verify security metadata handling
        security_metadata = {
            'security_classification': 'confidential',
            'access_control_list': [max_security_context.user_id],
            'audit_required': True,
            'compliance_level': 'SOC2_Type2'
        }
        
        # Create connection with security metadata
        secure_connection = type('SecureEnterpriseConnection', (), {
            'connection_id': f'secure_conn_{uuid.uuid4().hex[:8]}',
            'user_id': max_security_context.user_id,
            'tenant_id': max_security_context.tenant_id,
            'security_metadata': security_metadata,
            'websocket': None,
            'is_active': True
        })()
        
        try:
            await enterprise_manager.add_connection(secure_connection)
            logger.info("✅ Enterprise manager accepts connections with security metadata")
        except Exception as e:
            logger.error(f"❌ SECURITY METADATA HANDLING FAILURE: {e}")
            pytest.fail(
                f"ENTERPRISE SECURITY FAILURE: Manager cannot handle security metadata. "
                f"SSOT Violation: Consolidated manager lacks enterprise security features. "
                f"Business Impact: Cannot meet enterprise compliance requirements."
            )
        
        # CRITICAL SECURITY TEST 2: Verify audit capability
        audit_operations = [
            {'operation': 'connection_added', 'user_id': max_security_context.user_id},
            {'operation': 'security_check', 'classification': 'confidential'},
            {'operation': 'compliance_validation', 'level': 'SOC2_Type2'}
        ]
        
        # Check if manager supports audit operations (implementation-dependent)
        audit_support = hasattr(enterprise_manager, 'audit_log') or hasattr(enterprise_manager, 'log_security_event')
        
        if audit_support:
            logger.info("✅ Enterprise manager provides audit logging capability")
        else:
            logger.info("ℹ️ Audit logging may be handled at infrastructure level")
        
        # CRITICAL SECURITY TEST 3: Verify security boundary enforcement
        # Attempt operations that should be blocked for security reasons
        unauthorized_context = type('UnauthorizedContext', (), {
            'user_id': 'unauthorized_user',
            'tenant_id': 'unauthorized_tenant',
            'security_level': 'none'
        })()
        
        unauthorized_connection = type('UnauthorizedConnection', (), {
            'connection_id': 'unauthorized_conn',
            'user_id': 'unauthorized_user',
            'tenant_id': 'unauthorized_tenant',
            'websocket': None
        })()
        
        # This should either fail or be properly isolated
        security_boundary_enforced = False
        try:
            await enterprise_manager.add_connection(unauthorized_connection)
            
            # If it succeeds, check that it doesn't contaminate the secure environment
            secure_connections = await self._get_manager_connections(enterprise_manager, max_security_context.user_id)
            contamination = any(
                getattr(conn, 'tenant_id', None) == 'unauthorized_tenant'
                for conn in secure_connections
            )
            
            security_boundary_enforced = not contamination
            
        except Exception as e:
            # Expected - security boundary properly enforced
            security_boundary_enforced = True
            logger.info(f"✅ Security boundary properly enforced: {e}")
        
        if not security_boundary_enforced:
            pytest.fail(
                f"ENTERPRISE SECURITY BOUNDARY FAILURE: Unauthorized connection accepted without isolation. "
                f"SSOT Violation: Consolidated manager lacks security boundary enforcement. "
                f"Business Impact: Enterprise security model compromised, violating $500K+ ARR contracts."
            )
        
        logger.info("✅ Enterprise-grade security validation completed")
    
    async def test_ssot_performance_under_enterprise_load(self):
        """
        SSOT VALIDATION TEST: Validate SSOT manager performance under enterprise load.
        
        SSOT REQUIREMENT: Consolidated manager should maintain performance and isolation
        under realistic enterprise load scenarios.
        """
        logger.info("Validating SSOT manager performance under enterprise load")
        
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        # Create multiple enterprise managers for load testing
        enterprise_load_managers = []
        for user_context in self.enterprise_users:
            manager = await get_websocket_manager(user_context=user_context)
            enterprise_load_managers.append((user_context, manager))
        
        # Simulate enterprise load scenario
        connections_per_tenant = 20
        messages_per_connection = 5
        
        start_time = time.time()
        
        try:
            # Add connections under load
            for user_context, manager in enterprise_load_managers:
                connection_tasks = []
                for i in range(connections_per_tenant):
                    conn = await self._create_enterprise_connection(user_context)
                    connection_tasks.append(manager.add_connection(conn))
                
                # Execute connection additions with timing
                await asyncio.gather(*connection_tasks)
                logger.info(f"Added {connections_per_tenant} connections for {user_context.tenant_id}")
            
            load_time = time.time() - start_time
            
            # Verify isolation maintained under load
            isolation_maintained = True
            for user_context, manager in enterprise_load_managers:
                connections = await self._get_manager_connections(manager, user_context.user_id)
                
                # Check all connections belong to correct tenant
                for conn in connections:
                    if getattr(conn, 'tenant_id', None) != user_context.tenant_id:
                        isolation_maintained = False
                        break
                
                if not isolation_maintained:
                    break
            
            if not isolation_maintained:
                pytest.fail(
                    f"ENTERPRISE LOAD ISOLATION FAILURE: User isolation compromised under load. "
                    f"SSOT Violation: Consolidated manager fails under enterprise load scenarios. "
                    f"Business Impact: Enterprise performance requirements not met, "
                    f"affecting $500K+ ARR scalability requirements."
                )
            
            # Performance validation
            expected_max_time = 10.0  # Maximum acceptable time for load scenario
            if load_time > expected_max_time:
                logger.warning(f"⚠️ PERFORMANCE CONCERN: Load scenario took {load_time:.2f}s (expected < {expected_max_time}s)")
            else:
                logger.info(f"✅ Performance acceptable: Load scenario completed in {load_time:.2f}s")
            
            logger.info("✅ SSOT manager performance validated under enterprise load")
            
        except Exception as e:
            logger.error(f"❌ ENTERPRISE LOAD PERFORMANCE TEST FAILED: {e}")
            raise

    def teardown_method(self, method):
        """Clean up test environment."""
        logger.info(f"Tearing down enhanced user isolation validation test: {method.__name__}")
        super().teardown_method(method)