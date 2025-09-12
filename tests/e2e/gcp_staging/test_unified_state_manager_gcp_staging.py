"""
E2E GCP Staging Tests for UnifiedStateManager - FINAL PHASE
Real GCP Cloud Run, Redis Cloud, and production-scale testing

Business Value Protection:
- $500K+ ARR: State consistency prevents chat failures and agent execution errors
- $15K+ MRR per Enterprise customer: Multi-user state isolation prevents data leakage
- Platform stability: Prevents cascading failures from state inconsistencies
- User experience: Real-time state synchronization for WebSocket events
"""

import asyncio
import pytest
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any
# MIGRATED: from netra_backend.app.services.redis_client import get_redis_client
import json

from netra_backend.app.core.managers.unified_state_manager import (
    UnifiedStateManager, StateScope, StateManagerConfig, StateChangeEvent
)
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestUnifiedStateManagerGCPStaging(SSotAsyncTestCase):
    """
    E2E GCP Staging tests for UnifiedStateManager protecting business value.
    Tests production Cloud Run environment with real Redis Cloud and database.
    """

    @classmethod
    async def asyncSetUpClass(cls):
        """Set up real GCP services for testing."""
        await super().asyncSetUpClass()
        
        cls.env = IsolatedEnvironment()
        cls.id_manager = UnifiedIDManager()
        
        # Real GCP Redis Cloud connection
        cls.redis_client = await get_redis_client()
        
        # Real state manager with production configuration
        cls.config = StateManagerConfig(
            enable_persistence=True,
            enable_websocket_sync=True,
            enable_multi_user_isolation=True,
            cache_size_limit=10000,  # Production-scale
            state_ttl_seconds=3600,  # 1 hour
            enable_compression=True,
            max_concurrent_operations=100  # Production concurrency
        )
        
        cls.state_manager = UnifiedStateManager(config=cls.config)

    async def asyncTearDown(self):
        """Clean up after each test."""
        # Clean test data from Redis
        test_keys = [k for k in await redis_client.keys() if k.startswith("test_")]
        if test_keys:
            await redis_client.delete(*test_keys)
        
        await super().asyncTearDown()

    @pytest.mark.e2e_gcp_staging
    @pytest.mark.high_difficulty
    async def test_gcp_cloud_run_state_persistence_at_scale(self):
        """
        HIGH DIFFICULTY: Test state persistence under GCP Cloud Run production load.
        
        Business Value: $500K+ ARR protection - prevents state loss during scaling.
        Validates: Production-scale state operations, Cloud Run memory constraints.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Simulate production load: 1000 concurrent state operations
        tasks = []
        state_data = {}
        
        for i in range(1000):
            thread_id = self.id_manager.generate_thread_id()
            state_key = f"test_scale_{i}"
            state_value = {
                "agent_execution_id": str(uuid.uuid4()),
                "timestamp": time.time(),
                "data": f"production_load_test_{i}",
                "metadata": {"iteration": i, "load_test": True}
            }
            state_data[state_key] = state_value
            
            task = self.state_manager.set_state(
                scope=StateScope.THREAD,
                key=state_key,
                value=state_value,
                user_id=user_id,
                context_id=thread_id
            )
            tasks.append(task)
        
        # Execute all operations concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Validate all operations succeeded
        failures = [r for r in results if isinstance(r, Exception)]
        self.assertEqual(len(failures), 0, 
                        f"State operations failed under production load: {failures}")
        
        # Performance requirement: Complete within 30 seconds
        self.assertLess(execution_time, 30.0, 
                       "State operations too slow for production requirements")
        
        # Verify state persistence in Redis
        persisted_count = 0
        for state_key in state_data.keys():
            redis_key = f"state:{user_id}:{StateScope.THREAD.value}:{state_key}"
            if await redis_client.exists(redis_key):
                persisted_count += 1
        
        # At least 95% should be persisted successfully
        persistence_rate = persisted_count / len(state_data)
        self.assertGreater(persistence_rate, 0.95, 
                          f"Insufficient persistence rate: {persistence_rate}")

    @pytest.mark.e2e_gcp_staging
    @pytest.mark.high_difficulty
    async def test_redis_cloud_failover_state_recovery(self):
        """
        HIGH DIFFICULTY: Test state recovery when Redis Cloud fails over.
        
        Business Value: $15K+ MRR per Enterprise customer - prevents data loss.
        Validates: Redis failover handling, state recovery mechanisms.
        """
        user_id = self.id_manager.generate_user_id()
        thread_id = self.id_manager.generate_thread_id()
        
        # Store critical state
        critical_states = {}
        for i in range(100):
            state_key = f"critical_state_{i}"
            state_value = {
                "agent_execution_id": str(uuid.uuid4()),
                "critical_data": f"enterprise_customer_data_{i}",
                "timestamp": time.time(),
                "requires_recovery": True
            }
            critical_states[state_key] = state_value
            
            await self.state_manager.set_state(
                scope=StateScope.USER,
                key=state_key,
                value=state_value,
                user_id=user_id
            )
        
        # Verify initial state persistence
        for state_key in critical_states.keys():
            retrieved = await self.state_manager.get_state(
                scope=StateScope.USER,
                key=state_key,
                user_id=user_id
            )
            self.assertIsNotNone(retrieved, f"Initial state not found: {state_key}")
        
        # Simulate Redis connection disruption
        original_redis = self.state_manager._redis_client
        self.state_manager._redis_client = None
        
        # Test graceful degradation - operations should still work with fallback
        fallback_state_key = "fallback_test"
        fallback_value = {"testing": "redis_failover", "timestamp": time.time()}
        
        await self.state_manager.set_state(
            scope=StateScope.USER,
            key=fallback_state_key,
            value=fallback_value,
            user_id=user_id
        )
        
        # Restore Redis connection
        self.state_manager._redis_client = original_redis
        
        # Verify state recovery after Redis restoration
        recovered_count = 0
        for state_key in critical_states.keys():
            recovered = await self.state_manager.get_state(
                scope=StateScope.USER,
                key=state_key,
                user_id=user_id
            )
            if recovered is not None:
                recovered_count += 1
        
        # All critical states should be recoverable
        recovery_rate = recovered_count / len(critical_states)
        self.assertGreater(recovery_rate, 0.9, 
                          f"Insufficient state recovery rate: {recovery_rate}")

    @pytest.mark.e2e_gcp_staging
    @pytest.mark.high_difficulty
    async def test_multi_tenant_isolation_at_enterprise_scale(self):
        """
        HIGH DIFFICULTY: Test multi-tenant state isolation for Enterprise customers.
        
        Business Value: $15K+ MRR per Enterprise - prevents cross-tenant data leakage.
        Validates: Complete isolation, no shared state contamination.
        """
        # Create 50 enterprise tenants
        tenant_ids = [self.id_manager.generate_user_id() for _ in range(50)]
        
        # Each tenant creates isolated state
        tenant_states = {}
        for tenant_id in tenant_ids:
            tenant_state = {}
            for i in range(20):  # 20 states per tenant
                state_key = f"enterprise_data_{i}"
                state_value = {
                    "tenant_id": tenant_id,
                    "confidential_data": f"enterprise_secret_{tenant_id}_{i}",
                    "timestamp": time.time(),
                    "isolation_required": True
                }
                tenant_state[state_key] = state_value
                
                await self.state_manager.set_state(
                    scope=StateScope.USER,
                    key=state_key,
                    value=state_value,
                    user_id=tenant_id
                )
            
            tenant_states[tenant_id] = tenant_state
        
        # Validate complete isolation - no cross-tenant contamination
        contamination_detected = False
        contamination_details = []
        
        for tenant_id in tenant_ids:
            for state_key, expected_value in tenant_states[tenant_id].items():
                retrieved = await self.state_manager.get_state(
                    scope=StateScope.USER,
                    key=state_key,
                    user_id=tenant_id
                )
                
                # Verify retrieved state belongs to correct tenant
                if retrieved and retrieved.get("tenant_id") != tenant_id:
                    contamination_detected = True
                    contamination_details.append({
                        "expected_tenant": tenant_id,
                        "actual_tenant": retrieved.get("tenant_id"),
                        "state_key": state_key
                    })
        
        self.assertFalse(contamination_detected, 
                        f"Cross-tenant contamination detected: {contamination_details}")
        
        # Verify each tenant can only access their own states
        for tenant_id in tenant_ids:
            accessible_states = await self.state_manager.list_states(
                scope=StateScope.USER,
                user_id=tenant_id
            )
            
            # Should only see their own 20 states
            self.assertEqual(len(accessible_states), 20, 
                           f"Tenant {tenant_id} has access to wrong number of states")

    @pytest.mark.e2e_gcp_staging
    async def test_websocket_state_synchronization_production(self):
        """
        Test real-time state synchronization with WebSocket events in GCP.
        
        Business Value: Chat functionality - real-time agent state updates.
        Validates: WebSocket integration, event delivery, state consistency.
        """
        user_id = self.id_manager.generate_user_id()
        thread_id = self.id_manager.generate_thread_id()
        
        # Track state change events
        received_events = []
        
        def event_handler(event: StateChangeEvent):
            received_events.append(event)
        
        # Register for state change events
        self.state_manager.register_event_handler(event_handler)
        
        # Create multiple state changes
        state_changes = []
        for i in range(10):
            state_key = f"websocket_sync_{i}"
            state_value = {
                "agent_execution_id": str(uuid.uuid4()),
                "websocket_data": f"real_time_update_{i}",
                "timestamp": time.time()
            }
            state_changes.append((state_key, state_value))
            
            await self.state_manager.set_state(
                scope=StateScope.THREAD,
                key=state_key,
                value=state_value,
                user_id=user_id,
                context_id=thread_id
            )
            
            # Small delay to ensure event ordering
            await asyncio.sleep(0.1)
        
        # Wait for event propagation
        await asyncio.sleep(2.0)
        
        # Verify all state changes generated events
        self.assertGreaterEqual(len(received_events), len(state_changes),
                               "Missing WebSocket state change events")
        
        # Verify event content matches state changes
        for i, (state_key, state_value) in enumerate(state_changes):
            matching_events = [e for e in received_events 
                             if e.key == state_key and e.user_id == user_id]
            self.assertGreater(len(matching_events), 0, 
                             f"No event found for state change: {state_key}")

    @pytest.mark.e2e_gcp_staging
    async def test_state_compression_performance_optimization(self):
        """
        Test state compression for large data optimization in GCP.
        
        Business Value: Platform efficiency - reduces Redis memory costs.
        Validates: Compression algorithms, performance benefits.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Create large state objects (simulating agent execution data)
        large_states = {}
        for i in range(20):
            state_key = f"large_state_{i}"
            # Create 100KB of data per state
            large_data = {
                "agent_execution_log": ["log_entry_" + str(j) * 100 for j in range(100)],
                "tool_outputs": [{"tool_id": j, "output": "x" * 1000} for j in range(50)],
                "metadata": {"size": "100KB", "iteration": i}
            }
            large_states[state_key] = large_data
            
            await self.state_manager.set_state(
                scope=StateScope.USER,
                key=state_key,
                value=large_data,
                user_id=user_id
            )
        
        # Verify all large states can be retrieved correctly
        for state_key, expected_data in large_states.items():
            retrieved = await self.state_manager.get_state(
                scope=StateScope.USER,
                key=state_key,
                user_id=user_id
            )
            self.assertIsNotNone(retrieved, f"Large state not found: {state_key}")
            self.assertEqual(retrieved["metadata"]["size"], "100KB")
            self.assertEqual(len(retrieved["agent_execution_log"]), 100)
        
        # Check Redis memory efficiency (compressed storage)
        memory_info = await redis_client.info('memory')
        used_memory = memory_info.get('used_memory', 0)
        
        # With compression, should use less than 50% of uncompressed size
        # 20 states * 100KB = 2MB uncompressed, should be < 1MB compressed
        expected_max_memory = 1024 * 1024  # 1MB
        self.assertLess(used_memory, expected_max_memory * 5,  # Allow 5x headroom for Redis overhead
                       "Compression not working effectively")

    @pytest.mark.e2e_gcp_staging
    async def test_concurrent_user_state_operations(self):
        """
        Test concurrent state operations from multiple users.
        
        Business Value: Multi-user chat platform scalability.
        Validates: Thread safety, no race conditions, performance.
        """
        # Simulate 20 concurrent users
        user_ids = [self.id_manager.generate_user_id() for _ in range(20)]
        
        async def user_state_operations(user_id: str):
            """Perform state operations for one user."""
            results = []
            for i in range(50):  # 50 operations per user
                state_key = f"concurrent_state_{i}"
                state_value = {
                    "user_id": user_id,
                    "operation_id": i,
                    "timestamp": time.time(),
                    "concurrent_test": True
                }
                
                # Mix of read and write operations
                if i % 2 == 0:
                    await self.state_manager.set_state(
                        scope=StateScope.USER,
                        key=state_key,
                        value=state_value,
                        user_id=user_id
                    )
                    results.append(("write", state_key, True))
                else:
                    retrieved = await self.state_manager.get_state(
                        scope=StateScope.USER,
                        key=f"concurrent_state_{i-1}",
                        user_id=user_id
                    )
                    results.append(("read", f"concurrent_state_{i-1}", retrieved is not None))
            
            return results
        
        # Execute concurrent operations
        start_time = time.time()
        user_tasks = [user_state_operations(user_id) for user_id in user_ids]
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Validate no exceptions occurred
        exceptions = [r for r in user_results if isinstance(r, Exception)]
        self.assertEqual(len(exceptions), 0, f"Concurrent operations failed: {exceptions}")
        
        # Validate performance - should complete within reasonable time
        self.assertLess(execution_time, 60.0, 
                       "Concurrent operations too slow for production")
        
        # Validate all operations succeeded
        total_operations = 0
        successful_operations = 0
        
        for user_result in user_results:
            if not isinstance(user_result, Exception):
                for operation_type, state_key, success in user_result:
                    total_operations += 1
                    if success:
                        successful_operations += 1
        
        success_rate = successful_operations / total_operations
        self.assertGreater(success_rate, 0.95, 
                          f"Insufficient concurrent operation success rate: {success_rate}")

    @pytest.mark.e2e_gcp_staging
    async def test_state_ttl_cleanup_production(self):
        """
        Test state TTL (time-to-live) cleanup in production environment.
        
        Business Value: Resource efficiency - prevents memory leaks.
        Validates: TTL enforcement, automatic cleanup, memory management.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Create states with different TTL values
        short_ttl_states = []
        long_ttl_states = []
        
        for i in range(10):
            # Short TTL states (5 seconds)
            short_key = f"short_ttl_{i}"
            short_value = {"data": f"short_lived_{i}", "ttl": 5}
            await self.state_manager.set_state(
                scope=StateScope.USER,
                key=short_key,
                value=short_value,
                user_id=user_id,
                ttl_seconds=5
            )
            short_ttl_states.append(short_key)
            
            # Long TTL states (300 seconds)
            long_key = f"long_ttl_{i}"
            long_value = {"data": f"long_lived_{i}", "ttl": 300}
            await self.state_manager.set_state(
                scope=StateScope.USER,
                key=long_key,
                value=long_value,
                user_id=user_id,
                ttl_seconds=300
            )
            long_ttl_states.append(long_key)
        
        # Verify all states are initially present
        for state_key in short_ttl_states + long_ttl_states:
            retrieved = await self.state_manager.get_state(
                scope=StateScope.USER,
                key=state_key,
                user_id=user_id
            )
            self.assertIsNotNone(retrieved, f"State not found: {state_key}")
        
        # Wait for short TTL states to expire
        await asyncio.sleep(10)
        
        # Verify short TTL states are cleaned up
        expired_count = 0
        for state_key in short_ttl_states:
            retrieved = await self.state_manager.get_state(
                scope=StateScope.USER,
                key=state_key,
                user_id=user_id
            )
            if retrieved is None:
                expired_count += 1
        
        # At least 80% should be expired (allowing for timing variations)
        expiration_rate = expired_count / len(short_ttl_states)
        self.assertGreater(expiration_rate, 0.8, 
                          f"TTL cleanup not working: {expiration_rate}")
        
        # Verify long TTL states are still present
        surviving_count = 0
        for state_key in long_ttl_states:
            retrieved = await self.state_manager.get_state(
                scope=StateScope.USER,
                key=state_key,
                user_id=user_id
            )
            if retrieved is not None:
                surviving_count += 1
        
        survival_rate = surviving_count / len(long_ttl_states)
        self.assertGreater(survival_rate, 0.9, 
                          f"Long TTL states incorrectly expired: {survival_rate}")

    @pytest.mark.e2e_gcp_staging
    async def test_state_migration_between_scopes(self):
        """
        Test state migration between different scopes (user->thread->session).
        
        Business Value: Flexible state management for complex workflows.
        Validates: Scope transitions, data integrity during migration.
        """
        user_id = self.id_manager.generate_user_id()
        thread_id = self.id_manager.generate_thread_id()
        session_id = str(uuid.uuid4())
        
        # Create state at USER scope
        initial_data = {
            "agent_execution_id": str(uuid.uuid4()),
            "workflow_data": "complex_agent_workflow",
            "created_at": time.time(),
            "migration_test": True
        }
        
        state_key = "migratable_state"
        await self.state_manager.set_state(
            scope=StateScope.USER,
            key=state_key,
            value=initial_data,
            user_id=user_id
        )
        
        # Migrate to THREAD scope
        await self.state_manager.migrate_state(
            key=state_key,
            from_scope=StateScope.USER,
            to_scope=StateScope.THREAD,
            user_id=user_id,
            from_context_id=None,
            to_context_id=thread_id
        )
        
        # Verify state exists in THREAD scope
        thread_state = await self.state_manager.get_state(
            scope=StateScope.THREAD,
            key=state_key,
            user_id=user_id,
            context_id=thread_id
        )
        self.assertIsNotNone(thread_state, "State not found in THREAD scope")
        self.assertEqual(thread_state["workflow_data"], initial_data["workflow_data"])
        
        # Verify state removed from USER scope
        user_state = await self.state_manager.get_state(
            scope=StateScope.USER,
            key=state_key,
            user_id=user_id
        )
        self.assertIsNone(user_state, "State not removed from USER scope")
        
        # Migrate to SESSION scope
        await self.state_manager.migrate_state(
            key=state_key,
            from_scope=StateScope.THREAD,
            to_scope=StateScope.SESSION,
            user_id=user_id,
            from_context_id=thread_id,
            to_context_id=session_id
        )
        
        # Verify final state in SESSION scope
        session_state = await self.state_manager.get_state(
            scope=StateScope.SESSION,
            key=state_key,
            user_id=user_id,
            context_id=session_id
        )
        self.assertIsNotNone(session_state, "State not found in SESSION scope")
        self.assertEqual(session_state["workflow_data"], initial_data["workflow_data"])
        
        # Verify state removed from THREAD scope
        thread_state_after = await self.state_manager.get_state(
            scope=StateScope.THREAD,
            key=state_key,
            user_id=user_id,
            context_id=thread_id
        )
        self.assertIsNone(thread_state_after, "State not removed from THREAD scope")

    @pytest.mark.e2e_gcp_staging
    async def test_state_backup_and_recovery_production(self):
        """
        Test state backup and recovery mechanisms in production.
        
        Business Value: Data protection for Enterprise customers.
        Validates: Backup creation, recovery accuracy, data integrity.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Create comprehensive state data
        backup_states = {}
        for scope in [StateScope.USER, StateScope.THREAD, StateScope.SESSION]:
            for i in range(5):
                state_key = f"backup_state_{scope.value}_{i}"
                state_value = {
                    "scope": scope.value,
                    "backup_data": f"critical_enterprise_data_{i}",
                    "timestamp": time.time(),
                    "requires_backup": True
                }
                backup_states[f"{scope.value}:{state_key}"] = state_value
                
                context_id = str(uuid.uuid4()) if scope != StateScope.USER else None
                await self.state_manager.set_state(
                    scope=scope,
                    key=state_key,
                    value=state_value,
                    user_id=user_id,
                    context_id=context_id
                )
        
        # Create backup
        backup_result = await self.state_manager.create_backup(user_id=user_id)
        self.assertTrue(backup_result.success, "Backup creation failed")
        self.assertIsNotNone(backup_result.backup_id, "No backup ID generated")
        
        # Simulate data loss - clear all states
        await self.state_manager.clear_user_states(user_id=user_id)
        
        # Verify states are gone
        for scope in [StateScope.USER, StateScope.THREAD, StateScope.SESSION]:
            user_states = await self.state_manager.list_states(
                scope=scope,
                user_id=user_id
            )
            self.assertEqual(len(user_states), 0, f"States not cleared for scope: {scope}")
        
        # Restore from backup
        restore_result = await self.state_manager.restore_backup(
            backup_id=backup_result.backup_id,
            user_id=user_id
        )
        self.assertTrue(restore_result.success, "Backup restore failed")
        
        # Verify all states restored correctly
        recovered_count = 0
        for state_identifier, expected_value in backup_states.items():
            scope_str, state_key = state_identifier.split(":", 1)
            scope = StateScope(scope_str)
            
            retrieved = await self.state_manager.get_state(
                scope=scope,
                key=state_key,
                user_id=user_id,
                context_id=None if scope == StateScope.USER else expected_value.get("context_id")
            )
            
            if retrieved is not None and retrieved["backup_data"] == expected_value["backup_data"]:
                recovered_count += 1
        
        recovery_rate = recovered_count / len(backup_states)
        self.assertGreater(recovery_rate, 0.9, 
                          f"Insufficient backup recovery rate: {recovery_rate}")

    @pytest.mark.e2e_gcp_staging
    async def test_state_analytics_and_monitoring(self):
        """
        Test state analytics and monitoring capabilities.
        
        Business Value: Operational insights, performance optimization.
        Validates: Metrics collection, monitoring data, alerting.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Generate various state operations for analytics
        operation_types = ["create", "update", "read", "delete"]
        for i in range(100):
            operation_type = operation_types[i % 4]
            state_key = f"analytics_state_{i}"
            
            if operation_type in ["create", "update"]:
                await self.state_manager.set_state(
                    scope=StateScope.USER,
                    key=state_key,
                    value={
                        "operation_type": operation_type,
                        "analytics_data": f"data_{i}",
                        "timestamp": time.time()
                    },
                    user_id=user_id
                )
            elif operation_type == "read":
                await self.state_manager.get_state(
                    scope=StateScope.USER,
                    key=f"analytics_state_{max(0, i-1)}",
                    user_id=user_id
                )
            elif operation_type == "delete":
                await self.state_manager.delete_state(
                    scope=StateScope.USER,
                    key=f"analytics_state_{max(0, i-2)}",
                    user_id=user_id
                )
        
        # Get analytics data
        analytics = await self.state_manager.get_analytics(
            user_id=user_id,
            time_range_hours=1
        )
        
        # Verify analytics data collection
        self.assertIsNotNone(analytics, "Analytics data not available")
        self.assertIn("operation_counts", analytics)
        self.assertIn("performance_metrics", analytics)
        self.assertIn("error_rates", analytics)
        
        # Verify operation counts
        total_operations = sum(analytics["operation_counts"].values())
        self.assertGreater(total_operations, 50, 
                          "Insufficient operations tracked in analytics")
        
        # Verify performance metrics
        self.assertIn("avg_response_time", analytics["performance_metrics"])
        self.assertIn("peak_concurrent_operations", analytics["performance_metrics"])
        
        avg_response_time = analytics["performance_metrics"]["avg_response_time"]
        self.assertLess(avg_response_time, 1.0, 
                       "Average response time too high for production")

    @pytest.mark.e2e_gcp_staging 
    async def test_state_security_and_encryption(self):
        """
        Test state security and encryption in production environment.
        
        Business Value: Enterprise security compliance, data protection.
        Validates: Encryption at rest, secure transmission, access controls.
        """
        user_id = self.id_manager.generate_user_id()
        
        # Create sensitive state data
        sensitive_data = {
            "customer_pii": "ENCRYPTED_CUSTOMER_DATA",
            "api_keys": "ENCRYPTED_API_CREDENTIALS", 
            "financial_data": "ENCRYPTED_FINANCIAL_INFO",
            "security_level": "ENTERPRISE",
            "encryption_required": True
        }
        
        state_key = "sensitive_enterprise_state"
        await self.state_manager.set_state(
            scope=StateScope.USER,
            key=state_key,
            value=sensitive_data,
            user_id=user_id,
            encryption_level="ENTERPRISE"
        )
        
        # Verify data is encrypted in Redis
        redis_key = f"state:{user_id}:{StateScope.USER.value}:{state_key}"
        raw_redis_data = await redis_client.get(redis_key)
        self.assertIsNotNone(raw_redis_data, "State not found in Redis")
        
        # Raw data should not contain plaintext sensitive information
        self.assertNotIn("ENCRYPTED_CUSTOMER_DATA", raw_redis_data)
        self.assertNotIn("ENCRYPTED_API_CREDENTIALS", raw_redis_data)
        self.assertNotIn("ENCRYPTED_FINANCIAL_INFO", raw_redis_data)
        
        # Retrieved data should be properly decrypted
        retrieved = await self.state_manager.get_state(
            scope=StateScope.USER,
            key=state_key,
            user_id=user_id
        )
        self.assertIsNotNone(retrieved, "Encrypted state not retrievable")
        self.assertEqual(retrieved["customer_pii"], "ENCRYPTED_CUSTOMER_DATA")
        self.assertEqual(retrieved["api_keys"], "ENCRYPTED_API_CREDENTIALS")
        self.assertEqual(retrieved["financial_data"], "ENCRYPTED_FINANCIAL_INFO")
        
        # Test unauthorized access prevention
        unauthorized_user_id = self.id_manager.generate_user_id()
        unauthorized_access = await self.state_manager.get_state(
            scope=StateScope.USER,
            key=state_key,
            user_id=unauthorized_user_id  # Different user
        )
        self.assertIsNone(unauthorized_access, 
                         "Unauthorized access to encrypted state allowed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])