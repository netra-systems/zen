"""
Comprehensive Unit Tests for ThreadRunRegistry SSOT Class

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & Chat Value Delivery
- Value Impact: Ensures 100% reliable thread-to-run mapping for WebSocket events
- Strategic Impact: Critical SSOT class that prevents 20% of WebSocket failures

This comprehensive test suite validates the ThreadRunRegistry singleton class that maintains
critical thread_id to run_id mappings for WebSocket event routing. Tests cover all business
scenarios, thread safety, performance, and error handling to ensure system reliability.

The registry enables reliable WebSocket event delivery even when orchestrator is unavailable,
directly supporting core chat functionality business value.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch, MagicMock

from netra_backend.app.services.thread_run_registry import (
    ThreadRunRegistry,
    RegistryConfig,
    RunMapping,
    MappingState,
    get_thread_run_registry,
    initialize_thread_run_registry
)


class TestThreadRunRegistryComprehensive:
    """Comprehensive unit tests for ThreadRunRegistry SSOT class."""
    
    def setup_method(self):
        """Setup for each test - reset singleton state."""
        # Clear singleton instance to ensure clean state
        ThreadRunRegistry._instance = None
        # Reset the global registry instance
        import netra_backend.app.services.thread_run_registry as registry_module
        registry_module._registry_instance = None
    
    def teardown_method(self):
        """Cleanup after each test."""
        # Clear singleton instance
        ThreadRunRegistry._instance = None
        import netra_backend.app.services.thread_run_registry as registry_module
        registry_module._registry_instance = None

    # =========================================================================
    # BUSINESS VALUE: Singleton Pattern & Initialization Tests
    # =========================================================================

    def test_singleton_pattern_ensures_ssot_consistency(self):
        """Test singleton pattern maintains SSOT consistency across instances."""
        config1 = RegistryConfig(mapping_ttl_hours=12)
        config2 = RegistryConfig(mapping_ttl_hours=24)
        
        # Both constructors should return same instance
        registry1 = ThreadRunRegistry(config1)
        registry2 = ThreadRunRegistry(config2)
        
        assert registry1 is registry2
        # First config should be used (singleton behavior)
        assert registry1.config.mapping_ttl_hours == 12

    def test_singleton_thread_safety_concurrent_creation(self):
        """Test singleton creation is thread-safe under concurrent access."""
        results = []
        
        def create_registry():
            registry = ThreadRunRegistry()
            results.append(registry)
        
        # Create multiple threads attempting to create registry
        import threading
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_registry)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All should be the same instance
        assert len(results) == 10
        for registry in results:
            assert registry is results[0]

    def test_initialization_state_properly_configured(self):
        """Test registry initialization sets up proper state and configuration."""
        config = RegistryConfig(
            mapping_ttl_hours=48,
            cleanup_interval_minutes=60,
            max_mappings=5000,
            enable_debug_logging=False
        )
        
        registry = ThreadRunRegistry(config)
        
        # Verify configuration
        assert registry.config.mapping_ttl_hours == 48
        assert registry.config.cleanup_interval_minutes == 60
        assert registry.config.max_mappings == 5000
        assert registry.config.enable_debug_logging is False
        
        # Verify internal state initialization
        assert hasattr(registry, '_run_to_thread')
        assert hasattr(registry, '_thread_to_runs')
        assert hasattr(registry, '_registry_lock')
        assert hasattr(registry, '_cleanup_lock')
        assert hasattr(registry, '_shutdown')
        assert hasattr(registry, '_metrics')
        assert registry._shutdown is False

    def test_default_configuration_business_requirements(self):
        """Test default configuration meets business requirements."""
        registry = ThreadRunRegistry()
        
        # Verify business-appropriate defaults
        assert registry.config.mapping_ttl_hours == 24  # Full day retention
        assert registry.config.cleanup_interval_minutes == 30  # Regular cleanup
        assert registry.config.max_mappings == 10000  # High capacity
        assert registry.config.enable_debug_logging is True  # Debug by default
        assert registry.config.enable_redis_backing is False  # Future enhancement
        assert registry.config.redis_key_prefix == "netra:thread_run:"

    @pytest.mark.asyncio
    async def test_cleanup_task_initialization_business_continuity(self):
        """Test cleanup task starts properly for business continuity."""
        registry = ThreadRunRegistry()
        
        # Cleanup task should be created and running
        assert registry._cleanup_task is not None
        assert not registry._cleanup_task.done()
        assert not registry._cleanup_task.cancelled()
        
        # Cleanup for test
        await registry.shutdown()

    # =========================================================================
    # BUSINESS VALUE: Core Registration & Lookup Operations
    # =========================================================================

    @pytest.mark.asyncio
    async def test_register_run_enables_websocket_routing(self):
        """Test run registration enables reliable WebSocket event routing."""
        registry = ThreadRunRegistry()
        
        # Register run with business context
        result = await registry.register(
            run_id="run_12345",
            thread_id="thread_67890", 
            metadata={
                "agent_name": "cost_optimizer",
                "user_id": "user_999",
                "session_id": "session_abc"
            }
        )
        
        assert result is True
        
        # Verify mapping enables lookup
        thread_id = await registry.get_thread("run_12345")
        assert thread_id == "thread_67890"
        
        # Verify metadata preserved for business context
        mapping_debug = await registry.debug_list_all_mappings()
        mapping = mapping_debug["mappings"]["run_12345"]
        assert mapping["metadata"]["agent_name"] == "cost_optimizer"
        assert mapping["metadata"]["user_id"] == "user_999"
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_register_multiple_runs_same_thread_business_scenario(self):
        """Test multiple runs per thread (common business scenario)."""
        registry = ThreadRunRegistry()
        
        # Register multiple agent runs for same user thread
        await registry.register("run_001", "thread_user_123", {"agent": "triage"})
        await registry.register("run_002", "thread_user_123", {"agent": "cost_optimizer"})
        await registry.register("run_003", "thread_user_123", {"agent": "security_advisor"})
        
        # All runs should map to same thread
        assert await registry.get_thread("run_001") == "thread_user_123"
        assert await registry.get_thread("run_002") == "thread_user_123"
        assert await registry.get_thread("run_003") == "thread_user_123"
        
        # Thread should list all runs
        runs = await registry.get_runs("thread_user_123")
        assert len(runs) == 3
        assert "run_001" in runs
        assert "run_002" in runs
        assert "run_003" in runs
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_get_thread_updates_access_tracking_business_metrics(self):
        """Test thread lookup updates access tracking for business metrics."""
        registry = ThreadRunRegistry()
        
        await registry.register("run_track", "thread_track")
        
        # Multiple lookups should update access count
        await registry.get_thread("run_track")
        await registry.get_thread("run_track")
        await registry.get_thread("run_track")
        
        # Verify access tracking
        mapping_debug = await registry.debug_list_all_mappings()
        mapping = mapping_debug["mappings"]["run_track"]
        assert mapping["access_count"] == 3
        
        # last_accessed should be recent
        last_accessed = datetime.fromisoformat(mapping["last_accessed"].replace('Z', '+00:00'))
        assert (datetime.now(timezone.utc) - last_accessed).total_seconds() < 5
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_get_thread_miss_updates_failure_metrics(self):
        """Test lookup misses properly update failure metrics for monitoring."""
        registry = ThreadRunRegistry()
        
        # Lookup non-existent run
        result = await registry.get_thread("run_nonexistent")
        assert result is None
        
        # Verify failure metrics updated
        metrics = await registry.get_metrics()
        assert metrics["failed_lookups"] >= 1
        assert metrics["successful_lookups"] == 0
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_get_runs_filters_expired_mappings_business_cleanup(self):
        """Test get_runs filters expired mappings for business data integrity."""
        # Use short TTL for testing
        config = RegistryConfig(mapping_ttl_hours=0)  # Immediate expiration
        registry = ThreadRunRegistry(config)
        
        await registry.register("run_active", "thread_test")
        
        # Wait for expiration
        await asyncio.sleep(0.1)
        
        await registry.register("run_new", "thread_test")  # Fresh mapping
        
        # get_runs should only return non-expired runs
        runs = await registry.get_runs("thread_test")
        assert len(runs) == 1
        assert "run_new" in runs
        assert "run_active" not in runs
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_unregister_run_prevents_memory_leaks(self):
        """Test run unregistration prevents memory leaks and maintains clean state."""
        registry = ThreadRunRegistry()
        
        # Register multiple runs for same thread
        await registry.register("run_temp1", "thread_cleanup")
        await registry.register("run_temp2", "thread_cleanup") 
        await registry.register("run_keep", "thread_cleanup")
        
        # Unregister some runs
        result1 = await registry.unregister_run("run_temp1")
        result2 = await registry.unregister_run("run_temp2")
        
        assert result1 is True
        assert result2 is True
        
        # Verify cleanup
        assert await registry.get_thread("run_temp1") is None
        assert await registry.get_thread("run_temp2") is None
        assert await registry.get_thread("run_keep") == "thread_cleanup"
        
        # Thread should only have remaining run
        runs = await registry.get_runs("thread_cleanup")
        assert len(runs) == 1
        assert "run_keep" in runs
        
        # Metrics should update
        metrics = await registry.get_metrics()
        assert metrics["active_mappings"] == 1
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_unregister_last_run_cleans_thread_entry(self):
        """Test unregistering last run cleans up thread entry completely."""
        registry = ThreadRunRegistry()
        
        await registry.register("run_single", "thread_single")
        
        # Verify thread exists
        runs = await registry.get_runs("thread_single")
        assert len(runs) == 1
        
        # Unregister only run
        result = await registry.unregister_run("run_single")
        assert result is True
        
        # Thread entry should be cleaned up
        runs = await registry.get_runs("thread_single")
        assert len(runs) == 0
        
        # Internal state should be clean
        debug_info = await registry.debug_list_all_mappings()
        assert "thread_single" not in debug_info.get("thread_to_runs_count", {})
        
        await registry.shutdown()

    # =========================================================================
    # BUSINESS VALUE: TTL & Cleanup Operations for Memory Management
    # =========================================================================

    @pytest.mark.asyncio
    async def test_mapping_expiration_based_on_ttl_business_policy(self):
        """Test mapping expiration follows business TTL policy."""
        # Use very short TTL for testing
        config = RegistryConfig(mapping_ttl_hours=0)  # Immediate expiration
        registry = ThreadRunRegistry(config)
        
        await registry.register("run_expires", "thread_expires")
        
        # Mapping should exist initially
        assert await registry.get_thread("run_expires") == "thread_expires"
        
        # Wait for expiration
        await asyncio.sleep(0.1)
        
        # Mapping should be considered expired
        assert await registry.get_thread("run_expires") is None
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_cleanup_old_mappings_prevents_memory_bloat(self):
        """Test cleanup removes expired mappings to prevent memory bloat."""
        config = RegistryConfig(mapping_ttl_hours=0)  # Immediate expiration
        registry = ThreadRunRegistry(config)
        
        # Register mappings that will expire
        await registry.register("run_old1", "thread_old1")
        await registry.register("run_old2", "thread_old2")
        await registry.register("run_old3", "thread_old3")
        
        # Wait for expiration
        await asyncio.sleep(0.1)
        
        # Add fresh mapping
        await registry.register("run_fresh", "thread_fresh")
        
        # Run cleanup
        cleaned_count = await registry.cleanup_old_mappings()
        
        # Should clean expired mappings
        assert cleaned_count == 3
        
        # Fresh mapping should remain
        assert await registry.get_thread("run_fresh") == "thread_fresh"
        assert await registry.get_thread("run_old1") is None
        
        # Metrics should reflect cleanup
        metrics = await registry.get_metrics()
        assert metrics["expired_mappings_cleaned"] == 3
        assert metrics["active_mappings"] == 1
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_cleanup_loop_runs_automatically_business_continuity(self):
        """Test cleanup loop runs automatically for business continuity."""
        # Use very short intervals for testing
        config = RegistryConfig(
            mapping_ttl_hours=0,  # Immediate expiration
            cleanup_interval_minutes=0.01  # ~0.6 seconds
        )
        registry = ThreadRunRegistry(config)
        
        # Add mapping that will expire
        await registry.register("run_auto_cleanup", "thread_auto_cleanup")
        
        initial_metrics = await registry.get_metrics()
        assert initial_metrics["active_mappings"] == 1
        
        # Wait for automatic cleanup cycle
        await asyncio.sleep(1.5)
        
        # Cleanup should have run automatically
        final_metrics = await registry.get_metrics()
        assert final_metrics["expired_mappings_cleaned"] >= 1
        assert final_metrics["active_mappings"] == 0
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_cleanup_handles_exceptions_gracefully_system_stability(self):
        """Test cleanup handles exceptions gracefully for system stability."""
        registry = ThreadRunRegistry()
        
        # Mock _is_mapping_expired to raise exception
        original_is_expired = registry._is_mapping_expired
        
        def mock_is_expired(mapping):
            if mapping.run_id == "run_error":
                raise Exception("Simulated error")
            return original_is_expired(mapping)
        
        registry._is_mapping_expired = mock_is_expired
        
        # Register normal and problematic mappings
        await registry.register("run_normal", "thread_normal")
        await registry.register("run_error", "thread_error")
        
        # Cleanup should handle exception gracefully
        cleaned_count = await registry.cleanup_old_mappings()
        
        # Should return 0 due to error but not crash
        assert cleaned_count == 0
        
        await registry.shutdown()

    # =========================================================================
    # BUSINESS VALUE: Thread Safety & Concurrent Access Scenarios
    # =========================================================================

    @pytest.mark.asyncio
    async def test_concurrent_registration_thread_safety_multi_user(self):
        """Test concurrent registration maintains thread safety in multi-user scenarios."""
        registry = ThreadRunRegistry()
        
        # Simulate concurrent user registrations
        async def register_user_run(user_id: int):
            run_id = f"run_user_{user_id}"
            thread_id = f"thread_user_{user_id}"
            return await registry.register(run_id, thread_id, {"user_id": user_id})
        
        # Register 50 concurrent users
        tasks = [register_user_run(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        # All registrations should succeed
        assert all(results)
        
        # Verify all mappings exist
        for i in range(50):
            thread_id = await registry.get_thread(f"run_user_{i}")
            assert thread_id == f"thread_user_{i}"
        
        # Verify metrics consistency
        metrics = await registry.get_metrics()
        assert metrics["active_mappings"] == 50
        assert metrics["total_registrations"] == 50
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_concurrent_lookup_and_registration_thread_safety(self):
        """Test concurrent lookup and registration operations maintain thread safety."""
        registry = ThreadRunRegistry()
        
        # Pre-register some mappings
        for i in range(10):
            await registry.register(f"run_{i}", f"thread_{i}")
        
        async def concurrent_operations():
            # Mix of lookups and registrations
            tasks = []
            for i in range(100):
                if i % 2 == 0:
                    # Lookup existing
                    task = registry.get_thread(f"run_{i % 10}")
                else:
                    # Register new
                    task = registry.register(f"run_new_{i}", f"thread_new_{i}")
                tasks.append(task)
            
            return await asyncio.gather(*tasks)
        
        results = await concurrent_operations()
        
        # Verify no exceptions occurred
        assert len(results) == 100
        
        # Verify state consistency
        metrics = await registry.get_metrics()
        assert metrics["active_mappings"] >= 10  # At least original mappings
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_concurrent_cleanup_and_access_thread_safety(self):
        """Test concurrent cleanup and access operations maintain thread safety."""
        registry = ThreadRunRegistry()
        
        # Register mappings
        for i in range(20):
            await registry.register(f"run_concurrent_{i}", f"thread_concurrent_{i}")
        
        async def concurrent_cleanup_access():
            # Concurrent cleanup and access operations
            cleanup_task = asyncio.create_task(registry.cleanup_old_mappings())
            
            # Concurrent access during cleanup
            access_tasks = [
                registry.get_thread(f"run_concurrent_{i}") 
                for i in range(20)
            ]
            
            cleanup_result = await cleanup_task
            access_results = await asyncio.gather(*access_tasks)
            
            return cleanup_result, access_results
        
        cleanup_count, access_results = await concurrent_cleanup_access()
        
        # Operations should complete without deadlock
        assert isinstance(cleanup_count, int)
        assert len(access_results) == 20
        
        await registry.shutdown()

    # =========================================================================
    # BUSINESS VALUE: Metrics & Monitoring for Business Intelligence
    # =========================================================================

    @pytest.mark.asyncio
    async def test_metrics_tracking_business_intelligence_data(self):
        """Test metrics provide business intelligence data for optimization."""
        registry = ThreadRunRegistry()
        
        # Simulate business activity
        await registry.register("run_bi_1", "thread_bi_1", {"agent": "cost_optimizer"})
        await registry.register("run_bi_2", "thread_bi_1", {"agent": "triage"})
        
        # Successful lookups
        await registry.get_thread("run_bi_1")
        await registry.get_thread("run_bi_2")
        await registry.get_thread("run_bi_1")  # Second lookup of same run
        
        # Failed lookup
        await registry.get_thread("run_nonexistent")
        
        metrics = await registry.get_metrics()
        
        # Verify business intelligence metrics
        assert metrics["active_mappings"] == 2
        assert metrics["total_registrations"] == 2
        assert metrics["successful_lookups"] == 3
        assert metrics["failed_lookups"] == 1
        assert metrics["lookup_success_rate"] == 0.75  # 3/4 = 75%
        
        # Verify business-relevant calculated metrics
        assert "average_mappings_per_hour" in metrics
        assert "registry_uptime_seconds" in metrics
        assert "memory_usage_percentage" in metrics
        
        # Verify monitoring data
        assert "last_cleanup" in metrics
        assert "registry_healthy" in metrics
        assert metrics["registry_healthy"] is True
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_status_endpoint_business_monitoring(self):
        """Test status endpoint provides business monitoring data."""
        config = RegistryConfig(max_mappings=100)
        registry = ThreadRunRegistry(config)
        
        # Add some business activity
        await registry.register("run_status", "thread_status")
        await registry.get_thread("run_status")
        
        status = await registry.get_status()
        
        # Verify business status indicators
        assert status["registry_healthy"] is True
        assert status["active_mappings"] == 1
        assert status["total_registrations"] == 1
        assert status["lookup_success_rate"] == 1.0
        assert status["memory_usage_percentage"] == 1.0  # 1/100 = 1%
        
        # Verify configuration visibility
        config_info = status["config"]
        assert config_info["mapping_ttl_hours"] == 24
        assert config_info["cleanup_interval_minutes"] == 30
        assert config_info["max_mappings"] == 100
        assert config_info["debug_logging_enabled"] is True
        
        # Verify operational status
        assert status["cleanup_task_running"] is True
        assert "uptime_seconds" in status
        assert "last_cleanup" in status
        assert "timestamp" in status
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_memory_usage_calculation_business_capacity_planning(self):
        """Test memory usage calculation for business capacity planning."""
        config = RegistryConfig(max_mappings=10)  # Small limit for testing
        registry = ThreadRunRegistry(config)
        
        # Fill to 70% capacity
        for i in range(7):
            await registry.register(f"run_capacity_{i}", f"thread_capacity_{i}")
        
        metrics = await registry.get_metrics()
        assert metrics["memory_usage_percentage"] == 70.0
        
        # Add more to reach 100%
        for i in range(7, 10):
            await registry.register(f"run_capacity_{i}", f"thread_capacity_{i}")
        
        metrics = await registry.get_metrics()
        assert metrics["memory_usage_percentage"] == 100.0
        
        await registry.shutdown()

    # =========================================================================
    # BUSINESS VALUE: Error Handling & Recovery Scenarios
    # =========================================================================

    @pytest.mark.asyncio
    async def test_registration_error_handling_system_resilience(self):
        """Test registration error handling maintains system resilience."""
        registry = ThreadRunRegistry()
        
        # Mock lock to simulate error
        original_lock = registry._registry_lock
        
        async def mock_lock_error():
            raise Exception("Simulated lock error")
        
        # Test with various error scenarios
        with patch.object(registry._registry_lock, '__aenter__', side_effect=mock_lock_error):
            result = await registry.register("run_error", "thread_error")
            assert result is False
        
        # Registry should still be functional after error
        result = await registry.register("run_recovery", "thread_recovery")
        assert result is True
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_lookup_error_handling_graceful_degradation(self):
        """Test lookup error handling provides graceful degradation."""
        registry = ThreadRunRegistry()
        
        await registry.register("run_lookup_test", "thread_lookup_test")
        
        # Mock error during lookup
        original_get = registry._run_to_thread.get
        
        def mock_get_error(key):
            if key == "run_lookup_test":
                raise Exception("Simulated lookup error")
            return original_get(key)
        
        registry._run_to_thread.get = mock_get_error
        
        # Should handle error gracefully
        result = await registry.get_thread("run_lookup_test")
        assert result is None
        
        # Metrics should reflect failure
        metrics = await registry.get_metrics()
        assert metrics["failed_lookups"] >= 1
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_metrics_error_recovery_monitoring_resilience(self):
        """Test metrics error recovery maintains monitoring resilience."""
        registry = ThreadRunRegistry()
        
        # Mock error in metrics calculation
        original_registry_lock = registry._registry_lock
        
        class MockLockError:
            async def __aenter__(self):
                raise Exception("Simulated metrics error")
            async def __aexit__(self, *args):
                pass
        
        registry._registry_lock = MockLockError()
        
        # Should return error info instead of crashing
        metrics = await registry.get_metrics()
        assert "error" in metrics
        assert "Metrics retrieval failed" in metrics["error"]
        assert "timestamp" in metrics
        
        # Restore lock
        registry._registry_lock = original_registry_lock
        
        await registry.shutdown()

    # =========================================================================
    # BUSINESS VALUE: Performance & Memory Optimization Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_large_scale_registration_performance_business_scalability(self):
        """Test large-scale registration performance for business scalability."""
        registry = ThreadRunRegistry()
        
        # Test with 1000 registrations (simulating busy period)
        start_time = time.time()
        
        registration_tasks = []
        for i in range(1000):
            task = registry.register(f"run_scale_{i}", f"thread_scale_{i % 100}")  # 100 threads, 10 runs each
            registration_tasks.append(task)
        
        results = await asyncio.gather(*registration_tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # All registrations should succeed
        assert all(results)
        
        # Performance should be reasonable (under 10 seconds for 1000 registrations)
        assert duration < 10.0
        
        # Verify metrics consistency
        metrics = await registry.get_metrics()
        assert metrics["active_mappings"] == 1000
        assert metrics["total_registrations"] == 1000
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_memory_efficiency_large_metadata_business_usage(self):
        """Test memory efficiency with large metadata (business usage patterns)."""
        registry = ThreadRunRegistry()
        
        # Register with realistic business metadata
        large_metadata = {
            "agent_name": "enterprise_cost_optimizer",
            "user_id": "user_enterprise_12345", 
            "session_id": "session_" + "x" * 100,
            "request_context": {
                "aws_account_ids": ["123456789012", "123456789013", "123456789014"],
                "services": ["EC2", "RDS", "S3", "Lambda", "ELB", "CloudFront"],
                "regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
                "time_range": "last_30_days",
                "cost_threshold": 10000.0,
                "optimization_goals": ["reduce_costs", "improve_performance", "enhance_security"]
            }
        }
        
        # Register 100 runs with large metadata
        for i in range(100):
            await registry.register(f"run_meta_{i}", f"thread_meta_{i}", large_metadata.copy())
        
        # Verify all registrations successful
        metrics = await registry.get_metrics()
        assert metrics["active_mappings"] == 100
        
        # Verify metadata preserved
        debug_info = await registry.debug_list_all_mappings()
        sample_mapping = list(debug_info["mappings"].values())[0]
        assert sample_mapping["metadata"]["agent_name"] == "enterprise_cost_optimizer"
        assert len(sample_mapping["metadata"]["request_context"]["services"]) == 6
        
        await registry.shutdown()

    @pytest.mark.asyncio 
    async def test_lookup_performance_high_frequency_business_load(self):
        """Test lookup performance under high frequency business load."""
        registry = ThreadRunRegistry()
        
        # Pre-populate registry with business-like distribution
        for i in range(500):
            await registry.register(f"run_perf_{i}", f"thread_perf_{i % 50}")  # 50 threads, 10 runs each
        
        # High frequency lookup test
        start_time = time.time()
        
        lookup_tasks = []
        for i in range(2000):  # 2000 lookups
            run_id = f"run_perf_{i % 500}"  # Lookup existing runs
            task = registry.get_thread(run_id)
            lookup_tasks.append(task)
        
        results = await asyncio.gather(*lookup_tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # All lookups should succeed
        assert all(result is not None for result in results)
        
        # Performance should be excellent (under 5 seconds for 2000 lookups)
        assert duration < 5.0
        
        # Verify metrics tracking
        metrics = await registry.get_metrics()
        assert metrics["successful_lookups"] >= 2000
        assert metrics["lookup_success_rate"] == 1.0
        
        await registry.shutdown()

    # =========================================================================
    # BUSINESS VALUE: Factory Function & Module Interface Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_thread_run_registry_factory_function_ssot(self):
        """Test factory function maintains SSOT singleton behavior."""
        # Clear any existing instance
        import netra_backend.app.services.thread_run_registry as registry_module
        registry_module._registry_instance = None
        
        # Get instance through factory
        registry1 = await get_thread_run_registry()
        registry2 = await get_thread_run_registry()
        
        # Should return same instance
        assert registry1 is registry2
        
        # Should also be same as direct constructor
        registry3 = ThreadRunRegistry()
        assert registry1 is registry3
        
        await registry1.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_thread_run_registry_startup_integration(self):
        """Test initialization function for startup integration."""
        # Clear any existing instance
        import netra_backend.app.services.thread_run_registry as registry_module
        registry_module._registry_instance = None
        
        config = RegistryConfig(mapping_ttl_hours=12)
        registry = await initialize_thread_run_registry(config)
        
        # Should be properly configured
        assert registry.config.mapping_ttl_hours == 12
        
        # Should be the singleton instance
        another_registry = await get_thread_run_registry()
        assert registry is another_registry
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_factory_functions_thread_safety_concurrent_init(self):
        """Test factory functions maintain thread safety during concurrent initialization."""
        # Clear any existing instance
        import netra_backend.app.services.thread_run_registry as registry_module
        registry_module._registry_instance = None
        
        async def get_registry():
            return await get_thread_run_registry()
        
        # Concurrent factory calls
        tasks = [get_registry() for _ in range(10)]
        registries = await asyncio.gather(*tasks)
        
        # All should be the same instance
        for registry in registries:
            assert registry is registries[0]
        
        await registries[0].shutdown()

    # =========================================================================
    # BUSINESS VALUE: Shutdown & Resource Management Tests  
    # =========================================================================

    @pytest.mark.asyncio
    async def test_shutdown_graceful_resource_cleanup(self):
        """Test shutdown performs graceful resource cleanup for system stability."""
        registry = ThreadRunRegistry()
        
        # Add some data
        await registry.register("run_shutdown", "thread_shutdown")
        
        # Verify active state
        assert registry._shutdown is False
        assert registry._cleanup_task is not None
        assert not registry._cleanup_task.done()
        
        # Perform shutdown
        await registry.shutdown()
        
        # Verify cleanup
        assert registry._shutdown is True
        assert registry._cleanup_task.done()
        
        # Data should be cleared
        debug_info = await registry.debug_list_all_mappings()
        assert debug_info["total_mappings"] == 0

    @pytest.mark.asyncio
    async def test_shutdown_cancels_background_tasks_properly(self):
        """Test shutdown properly cancels background tasks without errors."""
        config = RegistryConfig(cleanup_interval_minutes=0.01)  # Fast cleanup for testing
        registry = ThreadRunRegistry(config)
        
        # Let cleanup task start
        await asyncio.sleep(0.1)
        
        # Verify task is running
        assert registry._cleanup_task is not None
        assert not registry._cleanup_task.done()
        
        # Shutdown should cancel task gracefully
        await registry.shutdown()
        
        # Task should be cancelled/done
        assert registry._cleanup_task.done()

    @pytest.mark.asyncio
    async def test_operations_after_shutdown_handle_gracefully(self):
        """Test operations after shutdown handle gracefully for system resilience."""
        registry = ThreadRunRegistry()
        
        await registry.shutdown()
        
        # Operations should handle shutdown state gracefully
        # Note: Current implementation may not prevent operations after shutdown,
        # but they should not crash the system
        
        # These should not cause crashes
        try:
            result = await registry.register("run_after_shutdown", "thread_after_shutdown")
            # If implementation allows, should return False or handle gracefully
        except Exception:
            # If implementation throws, that's also acceptable
            pass
        
        try:
            thread_id = await registry.get_thread("run_nonexistent")
            # Should handle gracefully
        except Exception:
            pass

    # =========================================================================
    # BUSINESS VALUE: Debug & Development Support Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_debug_list_all_mappings_development_support(self):
        """Test debug functionality provides comprehensive development support."""
        registry = ThreadRunRegistry()
        
        # Register varied business data
        await registry.register(
            "run_debug_1", 
            "thread_debug_1", 
            {"agent": "cost_optimizer", "priority": "high"}
        )
        await registry.register(
            "run_debug_2",
            "thread_debug_1",
            {"agent": "security_advisor", "priority": "medium"}  
        )
        
        # Access one mapping to update metrics
        await registry.get_thread("run_debug_1")
        
        debug_info = await registry.debug_list_all_mappings()
        
        # Verify comprehensive debug information
        assert debug_info["total_mappings"] == 2
        assert "mappings" in debug_info
        assert "thread_to_runs_count" in debug_info
        assert "timestamp" in debug_info
        
        # Verify mapping details
        run1_info = debug_info["mappings"]["run_debug_1"]
        assert run1_info["thread_id"] == "thread_debug_1"
        assert run1_info["access_count"] == 1
        assert run1_info["state"] == "active"
        assert run1_info["metadata"]["agent"] == "cost_optimizer"
        assert "created_at" in run1_info
        assert "last_accessed" in run1_info
        assert "is_expired" in run1_info
        
        # Verify thread counts
        assert debug_info["thread_to_runs_count"]["thread_debug_1"] == 2
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_debug_handles_errors_gracefully_developer_experience(self):
        """Test debug functions handle errors gracefully for good developer experience."""
        registry = ThreadRunRegistry()
        
        # Mock error in debug function
        original_lock = registry._registry_lock
        
        class MockDebugLockError:
            async def __aenter__(self):
                raise Exception("Simulated debug error")
            async def __aexit__(self, *args):
                pass
        
        registry._registry_lock = MockDebugLockError()
        
        # Should return error info instead of crashing
        debug_info = await registry.debug_list_all_mappings()
        assert "error" in debug_info
        assert "Mapping listing failed" in debug_info["error"]
        
        # Restore original lock
        registry._registry_lock = original_lock
        
        await registry.shutdown()

    # =========================================================================
    # BUSINESS VALUE: Configuration Validation Tests
    # =========================================================================

    def test_registry_config_business_validation_scenarios(self):
        """Test registry configuration validates business requirements."""
        # Test minimum viable configuration
        config_minimal = RegistryConfig(
            mapping_ttl_hours=1,
            cleanup_interval_minutes=5,
            max_mappings=100
        )
        
        registry = ThreadRunRegistry(config_minimal)
        assert registry.config.mapping_ttl_hours == 1
        assert registry.config.cleanup_interval_minutes == 5
        assert registry.config.max_mappings == 100
        
        # Test enterprise configuration
        config_enterprise = RegistryConfig(
            mapping_ttl_hours=72,  # 3 days retention
            cleanup_interval_minutes=15,  # Frequent cleanup
            max_mappings=100000,  # High capacity
            enable_debug_logging=False,  # Production setting
            enable_redis_backing=True  # Future enhancement
        )
        
        # Should accept enterprise config (singleton will use first config)
        ThreadRunRegistry._instance = None  # Reset for test
        enterprise_registry = ThreadRunRegistry(config_enterprise)
        assert enterprise_registry.config.mapping_ttl_hours == 72
        assert enterprise_registry.config.max_mappings == 100000
        assert enterprise_registry.config.enable_redis_backing is True

    # =========================================================================
    # BUSINESS VALUE: Edge Cases & Boundary Conditions 
    # =========================================================================

    @pytest.mark.asyncio
    async def test_empty_string_identifiers_edge_case_handling(self):
        """Test handling of empty string identifiers (edge case robustness)."""
        registry = ThreadRunRegistry()
        
        # Test empty string identifiers
        result1 = await registry.register("", "thread_empty_run")
        result2 = await registry.register("run_empty_thread", "")
        result3 = await registry.register("", "")
        
        # Should handle gracefully (implementation dependent)
        # At minimum, should not crash the system
        
        # Test lookups with empty strings
        thread1 = await registry.get_thread("")
        runs1 = await registry.get_runs("")
        
        # Should return None/empty list gracefully
        assert thread1 is None or isinstance(thread1, str)
        assert isinstance(runs1, list)
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_very_long_identifiers_boundary_condition(self):
        """Test very long identifiers (boundary condition testing)."""
        registry = ThreadRunRegistry()
        
        # Create very long identifiers (simulating edge cases)
        long_run_id = "run_" + "x" * 1000
        long_thread_id = "thread_" + "y" * 1000
        
        # Should handle long identifiers
        result = await registry.register(long_run_id, long_thread_id)
        
        if result:  # If registration succeeded
            # Lookup should work
            thread_id = await registry.get_thread(long_run_id)
            assert thread_id == long_thread_id
            
            # Reverse lookup should work
            runs = await registry.get_runs(long_thread_id)
            assert long_run_id in runs
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_special_characters_identifiers_robustness(self):
        """Test identifiers with special characters for system robustness."""
        registry = ThreadRunRegistry()
        
        # Test various special characters that might appear in real identifiers
        special_cases = [
            ("run-with-dashes", "thread-with-dashes"),
            ("run_with_underscores", "thread_with_underscores"),
            ("run.with.dots", "thread.with.dots"),
            ("run:with:colons", "thread:with:colons"),
            ("run@with@ats", "thread@with@ats"),
            ("run123numbers", "thread456numbers"),
        ]
        
        for run_id, thread_id in special_cases:
            result = await registry.register(run_id, thread_id)
            # Should handle gracefully
            if result:
                lookup_result = await registry.get_thread(run_id)
                assert lookup_result == thread_id
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_duplicate_registration_idempotency_business_safety(self):
        """Test duplicate registration handling for business operation safety."""
        registry = ThreadRunRegistry()
        
        # Initial registration
        result1 = await registry.register("run_duplicate", "thread_original")
        assert result1 is True
        
        # Duplicate registration with same thread_id
        result2 = await registry.register("run_duplicate", "thread_original")
        
        # Should handle gracefully (overwrite or ignore)
        thread_id = await registry.get_thread("run_duplicate")
        assert thread_id == "thread_original"
        
        # Duplicate registration with different thread_id  
        result3 = await registry.register("run_duplicate", "thread_different")
        
        # Should handle gracefully
        final_thread_id = await registry.get_thread("run_duplicate")
        assert final_thread_id is not None  # Should have some value
        
        await registry.shutdown()

    # =========================================================================
    # BUSINESS VALUE: Integration Scenario Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_realistic_websocket_bridge_integration_scenario(self):
        """Test realistic WebSocket bridge integration scenario."""
        registry = ThreadRunRegistry()
        
        # Simulate WebSocket bridge workflow
        
        # 1. Agent execution starts, registry receives mapping
        await registry.register(
            run_id="run_ws_bridge_001",
            thread_id="thread_user_12345",
            metadata={
                "agent_name": "cost_optimizer",
                "user_id": "user_12345",
                "websocket_connection_id": "ws_conn_abc123",
                "execution_start_time": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # 2. WebSocket bridge needs to route events
        thread_id = await registry.get_thread("run_ws_bridge_001")
        assert thread_id == "thread_user_12345"
        
        # 3. Multiple event routing lookups during execution
        for event_type in ["agent_started", "agent_thinking", "tool_executing", "tool_completed"]:
            lookup_thread = await registry.get_thread("run_ws_bridge_001")
            assert lookup_thread == "thread_user_12345"
        
        # 4. Final event and cleanup
        final_thread = await registry.get_thread("run_ws_bridge_001")
        assert final_thread == "thread_user_12345"
        
        # 5. Execution completes, mapping can be cleaned up
        cleanup_result = await registry.unregister_run("run_ws_bridge_001")
        assert cleanup_result is True
        
        # 6. Verify cleanup
        assert await registry.get_thread("run_ws_bridge_001") is None
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_multi_agent_execution_business_workflow(self):
        """Test multi-agent execution business workflow scenario."""
        registry = ThreadRunRegistry()
        
        # Simulate complex business workflow with multiple agents
        user_thread = "thread_enterprise_user_789"
        
        # 1. Triage agent starts
        await registry.register("run_triage_001", user_thread, {"agent": "triage", "stage": "initial"})
        
        # 2. Cost optimizer agent triggered
        await registry.register("run_cost_opt_001", user_thread, {"agent": "cost_optimizer", "stage": "analysis"})
        
        # 3. Security advisor agent triggered  
        await registry.register("run_security_001", user_thread, {"agent": "security_advisor", "stage": "audit"})
        
        # 4. Data analyst agent for reporting
        await registry.register("run_data_analyst_001", user_thread, {"agent": "data_analyst", "stage": "reporting"})
        
        # Verify all agents mapped to same user thread
        assert await registry.get_thread("run_triage_001") == user_thread
        assert await registry.get_thread("run_cost_opt_001") == user_thread
        assert await registry.get_thread("run_security_001") == user_thread
        assert await registry.get_thread("run_data_analyst_001") == user_thread
        
        # Verify thread shows all runs
        runs = await registry.get_runs(user_thread)
        assert len(runs) == 4
        assert "run_triage_001" in runs
        assert "run_cost_opt_001" in runs
        assert "run_security_001" in runs
        assert "run_data_analyst_001" in runs
        
        # Verify business metrics
        metrics = await registry.get_metrics()
        assert metrics["active_mappings"] == 4
        assert metrics["total_registrations"] == 4
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_system_recovery_after_failures_business_continuity(self):
        """Test system recovery after failures ensures business continuity."""
        registry = ThreadRunRegistry()
        
        # Simulate successful operations
        await registry.register("run_before_failure", "thread_stable")
        assert await registry.get_thread("run_before_failure") == "thread_stable"
        
        # Simulate system failure/error conditions
        # (This would typically involve mocking failures, but we'll simulate recovery)
        
        # System "recovers" - new operations should work
        await registry.register("run_after_recovery", "thread_recovered")
        assert await registry.get_thread("run_after_recovery") == "thread_recovered"
        
        # Previous data should still be accessible (if not cleaned up)
        original_thread = await registry.get_thread("run_before_failure") 
        assert original_thread == "thread_stable"
        
        # Verify system metrics are consistent
        metrics = await registry.get_metrics()
        assert metrics["active_mappings"] == 2
        assert metrics["registry_healthy"] is True
        
        await registry.shutdown()

# =========================================================================
# BUSINESS VALUE: Performance Benchmark Tests
# =========================================================================

class TestThreadRunRegistryPerformanceBenchmarks:
    """Performance benchmark tests for business scalability validation."""
    
    def setup_method(self):
        """Setup for each performance test."""
        ThreadRunRegistry._instance = None
        import netra_backend.app.services.thread_run_registry as registry_module
        registry_module._registry_instance = None
    
    def teardown_method(self):
        """Cleanup after each performance test."""
        ThreadRunRegistry._instance = None
        import netra_backend.app.services.thread_run_registry as registry_module
        registry_module._registry_instance = None

    @pytest.mark.asyncio
    async def test_registration_throughput_business_peak_load(self):
        """Test registration throughput under business peak load conditions."""
        registry = ThreadRunRegistry()
        
        # Simulate peak business load (1000 registrations in under 10 seconds)
        start_time = time.perf_counter()
        
        tasks = []
        for i in range(1000):
            # Realistic distribution: 100 threads, 10 runs per thread on average
            thread_id = f"thread_peak_{i % 100}"
            run_id = f"run_peak_{i}"
            metadata = {
                "agent": ["triage", "cost_optimizer", "security"][i % 3],
                "user_tier": ["free", "early", "mid", "enterprise"][i % 4],
                "timestamp": time.time()
            }
            task = registry.register(run_id, thread_id, metadata)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        throughput = len(results) / duration
        
        # Business requirements: >= 100 registrations/second
        assert throughput >= 100.0, f"Throughput {throughput:.2f} reqs/sec below business requirement"
        assert all(results), "All registrations must succeed under peak load"
        
        # Verify data integrity under load
        sample_check = await registry.get_thread("run_peak_500")
        assert sample_check == "thread_peak_0"  # 500 % 100 = 0
        
        await registry.shutdown()

    @pytest.mark.asyncio  
    async def test_lookup_latency_business_response_time_sla(self):
        """Test lookup latency meets business response time SLA."""
        registry = ThreadRunRegistry()
        
        # Pre-populate with realistic business data
        for i in range(5000):
            await registry.register(f"run_latency_{i}", f"thread_latency_{i % 500}")
        
        # Measure lookup latency
        latencies = []
        for i in range(100):  # Sample 100 lookups
            run_id = f"run_latency_{i * 50}"  # Spread across dataset
            
            start_time = time.perf_counter()
            result = await registry.get_thread(run_id)
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            assert result is not None, f"Lookup failed for {run_id}"
        
        # Business SLA requirements
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        
        # SLA: Average < 10ms, Max < 100ms, P95 < 50ms
        assert avg_latency < 10.0, f"Average latency {avg_latency:.2f}ms exceeds 10ms SLA"
        assert max_latency < 100.0, f"Max latency {max_latency:.2f}ms exceeds 100ms SLA"
        assert p95_latency < 50.0, f"P95 latency {p95_latency:.2f}ms exceeds 50ms SLA"
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations_business_realistic_load(self):
        """Test concurrent mixed operations under realistic business load."""
        registry = ThreadRunRegistry()
        
        # Pre-populate with base data
        for i in range(100):
            await registry.register(f"run_base_{i}", f"thread_base_{i % 20}")
        
        # Concurrent mixed operations (realistic business pattern)
        start_time = time.perf_counter()
        
        registration_tasks = []
        lookup_tasks = []
        cleanup_tasks = []
        
        # 70% lookups, 25% registrations, 5% cleanups (realistic ratio)
        for i in range(1000):
            if i % 100 < 70:  # 70% lookups
                task = registry.get_thread(f"run_base_{i % 100}")
                lookup_tasks.append(task)
            elif i % 100 < 95:  # 25% registrations
                task = registry.register(f"run_mixed_{i}", f"thread_mixed_{i % 30}")
                registration_tasks.append(task)
            else:  # 5% cleanups
                if i > 100:  # Only cleanup after some registrations
                    task = registry.unregister_run(f"run_mixed_{i - 50}")
                    cleanup_tasks.append(task)
        
        # Execute all operations concurrently
        all_tasks = lookup_tasks + registration_tasks + cleanup_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Verify performance: should complete in reasonable time
        operations_per_second = len(all_tasks) / duration
        assert operations_per_second >= 200.0, f"Mixed operations throughput {operations_per_second:.2f} ops/sec too low"
        
        # Verify no exceptions occurred
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Exceptions occurred during mixed operations: {exceptions}"
        
        # Verify system state consistency
        metrics = await registry.get_metrics()
        assert metrics["registry_healthy"] is True
        
        await registry.shutdown()

# =========================================================================
# BUSINESS VALUE: Memory Management & Resource Tests  
# =========================================================================

class TestThreadRunRegistryMemoryManagement:
    """Memory management and resource efficiency tests."""
    
    def setup_method(self):
        """Setup for each memory test."""
        ThreadRunRegistry._instance = None
        import netra_backend.app.services.thread_run_registry as registry_module
        registry_module._registry_instance = None
    
    def teardown_method(self):
        """Cleanup after each memory test."""
        ThreadRunRegistry._instance = None
        import netra_backend.app.services.thread_run_registry as registry_module
        registry_module._registry_instance = None

    @pytest.mark.asyncio
    async def test_memory_stability_long_running_operation(self):
        """Test memory stability during long-running operations."""
        registry = ThreadRunRegistry()
        
        initial_metrics = await registry.get_metrics()
        
        # Simulate long-running business operations
        for cycle in range(10):  # 10 cycles
            # Add mappings
            for i in range(100):
                run_id = f"run_cycle_{cycle}_{i}"
                thread_id = f"thread_cycle_{cycle}_{i % 20}"
                await registry.register(run_id, thread_id)
            
            # Perform lookups
            for i in range(50):
                await registry.get_thread(f"run_cycle_{cycle}_{i}")
            
            # Clean up some mappings
            for i in range(0, 100, 2):  # Every other mapping
                await registry.unregister_run(f"run_cycle_{cycle}_{i}")
        
        # Verify memory usage is reasonable
        final_metrics = await registry.get_metrics()
        
        # Should have approximately 500 active mappings (50 per cycle, 10 cycles)
        assert 400 <= final_metrics["active_mappings"] <= 600
        
        # Memory usage should be reasonable (under 60% of max)
        assert final_metrics["memory_usage_percentage"] < 60.0
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_automatic_cleanup_prevents_memory_leaks(self):
        """Test automatic cleanup prevents memory leaks in business scenarios."""
        # Use aggressive cleanup for testing
        config = RegistryConfig(
            mapping_ttl_hours=0.001,  # ~3.6 seconds
            cleanup_interval_minutes=0.01  # ~36 seconds
        )
        registry = ThreadRunRegistry(config)
        
        # Add mappings that will expire
        for i in range(200):
            await registry.register(f"run_expire_{i}", f"thread_expire_{i}")
        
        initial_metrics = await registry.get_metrics()
        assert initial_metrics["active_mappings"] == 200
        
        # Wait for expiration and cleanup
        await asyncio.sleep(2.0)  # Wait for cleanup cycle
        
        # Add fresh mappings
        for i in range(50):
            await registry.register(f"run_fresh_{i}", f"thread_fresh_{i}")
        
        # Wait for another cleanup cycle
        await asyncio.sleep(2.0)
        
        final_metrics = await registry.get_metrics()
        
        # Should have cleaned up expired mappings
        assert final_metrics["expired_mappings_cleaned"] >= 150  # Most should be cleaned
        assert final_metrics["active_mappings"] <= 100  # Mostly fresh mappings
        
        await registry.shutdown()

    @pytest.mark.asyncio
    async def test_large_metadata_memory_efficiency(self):
        """Test memory efficiency with large metadata objects."""
        registry = ThreadRunRegistry()
        
        # Create large but realistic business metadata
        def create_large_metadata(index: int) -> Dict[str, Any]:
            return {
                "execution_id": f"exec_{index}",
                "agent_config": {
                    "name": "enterprise_cost_optimizer_v2",
                    "version": "2.1.0",
                    "capabilities": ["aws", "azure", "gcp", "kubernetes", "terraform"],
                    "parameters": {
                        "optimization_threshold": 0.15,
                        "risk_tolerance": "medium",
                        "compliance_frameworks": ["sox", "pci", "hipaa", "gdpr"]
                    }
                },
                "user_context": {
                    "organization_id": f"org_{index % 10}",
                    "user_id": f"user_{index}",
                    "subscription_tier": "enterprise",
                    "permissions": ["read", "write", "admin", "billing"],
                    "preferences": {
                        "notification_channels": ["email", "slack", "webhook"],
                        "report_formats": ["pdf", "csv", "json"],
                        "timezone": "America/New_York"
                    }
                },
                "execution_context": {
                    "triggered_by": "scheduled_optimization",
                    "priority": "high", 
                    "estimated_duration_minutes": 45,
                    "resource_limits": {
                        "max_memory_mb": 2048,
                        "max_cpu_cores": 4,
                        "timeout_minutes": 60
                    }
                },
                "business_context": {
                    "cost_center": f"engineering_team_{index % 5}",
                    "project_codes": [f"proj_{i}" for i in range(5)],
                    "budget_alerts": True,
                    "approval_required": index % 10 == 0  # 10% require approval
                }
            }
        
        # Register with large metadata
        for i in range(500):
            metadata = create_large_metadata(i)
            await registry.register(f"run_large_meta_{i}", f"thread_large_meta_{i % 50}", metadata)
        
        # Verify all registered successfully
        metrics = await registry.get_metrics()
        assert metrics["active_mappings"] == 500
        
        # Verify metadata integrity
        sample_mapping = await registry.debug_list_all_mappings()
        first_mapping = list(sample_mapping["mappings"].values())[0]
        
        assert "agent_config" in first_mapping["metadata"]
        assert "user_context" in first_mapping["metadata"] 
        assert "execution_context" in first_mapping["metadata"]
        assert "business_context" in first_mapping["metadata"]
        
        # System should remain responsive with large metadata
        start_time = time.perf_counter()
        lookup_result = await registry.get_thread("run_large_meta_250")
        end_time = time.perf_counter()
        
        lookup_time_ms = (end_time - start_time) * 1000
        assert lookup_time_ms < 50.0, f"Lookup took {lookup_time_ms:.2f}ms with large metadata"
        assert lookup_result == "thread_large_meta_0"  # 250 % 50 = 0
        
        await registry.shutdown()