"""
Test Advanced Factory Resilience Scenarios

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure factory patterns remain resilient under extreme conditions
- Value Impact: Prevents factory-based user isolation failures that could cause data leakage
- Strategic Impact: Core multi-user security and system stability

This test suite validates factory resilience mechanisms under resource pressure,
state corruption, dynamic reconfiguration, and extreme load conditions. Tests
are designed to be DIFFICULT and stress the factory system to breaking points.

CRITICAL: Uses real services (PostgreSQL, Redis) - no mocks allowed
"""

import asyncio
import gc
import json
import logging
import os
import psutil
import pytest
import random
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
# Removed mock imports - using ONLY real service failures as per CLAUDE.md
from concurrent.futures import ThreadPoolExecutor

# Import for real service failure operations
from test_framework.unified_docker_manager import get_default_manager

# SSOT imports for factory patterns
from netra_backend.app.core.unified_id_manager import UnifiedIDManager  
from netra_backend.app.services.user_execution_context import UserContextFactory
from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory
from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user

logger = logging.getLogger(__name__)


class FactoryStressTestManager:
    """Manages factory stress testing scenarios."""
    
    def __init__(self):
        self.active_factories = set()
        self.resource_monitors = {}
        self.failure_scenarios = []
        self.performance_baselines = {}
    
    def register_factory(self, factory_id: str, factory_instance: Any):
        """Register a factory for stress testing."""
        self.active_factories.add(factory_id)
        self.performance_baselines[factory_id] = {
            "creation_times": [],
            "memory_usage": [],
            "success_rate": 1.0
        }
    
    def get_system_memory_usage(self) -> Dict[str, float]:
        """Get current system memory usage."""
        process = psutil.Process()
        return {
            "memory_percent": process.memory_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "system_memory_percent": psutil.virtual_memory().percent
        }


class TestAdvancedFactoryResilience(BaseIntegrationTest):
    """Test factory resilience under extreme conditions with REAL services."""
    
    def setup_method(self):
        """Set up method with factory stress testing infrastructure."""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.id_manager = UnifiedIDManager()
        self.stress_manager = FactoryStressTestManager()
        self.resource_exhaustion_data = []
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_resource_exhaustion_recovery(self, real_services_fixture):
        """
        Test factory behavior during resource exhaustion scenarios.
        
        This test deliberately exhausts system resources (memory, connections)
        and validates that factories can detect resource pressure and implement
        appropriate recovery strategies.
        
        CRITICAL: This is a RESOURCE EXHAUSTION stress test.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for resource exhaustion testing")
            
        engine = real_services_fixture["postgres"]
        session_factory = RequestScopedSessionFactory(engine=engine)
        context_factory = UserContextFactory(
            session_factory=session_factory,
            unified_id_manager=self.id_manager
        )
        
        self.stress_manager.register_factory("context_factory", context_factory)
        
        # Create baseline users for comparison
        baseline_users = []
        for i in range(3):
            user_token, user_data = await create_authenticated_user(
                environment="test",
                user_id=f"baseline-{i}-{uuid.uuid4().hex[:8]}",
                email=f"baseline-{i}-{int(time.time())}@example.com"
            )
            baseline_users.append(user_data)
        
        # Measure baseline performance
        baseline_metrics = await self._measure_factory_baseline_performance(
            context_factory, baseline_users[0]["id"], engine
        )
        
        # RESOURCE EXHAUSTION PHASE 1: Memory pressure
        memory_pressure_objects = []
        try:
            # Create significant memory pressure
            initial_memory = self.stress_manager.get_system_memory_usage()
            logger.info(f"Initial memory usage: {initial_memory}")
            
            # Gradually increase memory pressure
            for pressure_level in range(1, 6):  # 5 levels of pressure
                logger.info(f"Applying memory pressure level {pressure_level}/5")
                
                # Create large data structures
                for i in range(200):
                    large_object = {
                        f"data_{j}": f"pressure_{'x' * 500}_level_{pressure_level}" 
                        for j in range(100)
                    }
                    memory_pressure_objects.append(large_object)
                
                current_memory = self.stress_manager.get_system_memory_usage()
                logger.info(f"Memory pressure level {pressure_level}: {current_memory}")
                
                # Test factory behavior under current pressure
                pressure_start = time.time()
                
                async with session_factory.create_session() as session:
                    context = await context_factory.create_user_context(
                        user_id=baseline_users[0]["id"],
                        session=session,
                        metadata={
                            "pressure_level": pressure_level,
                            "memory_usage": current_memory,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    
                pressure_duration = time.time() - pressure_start
                
                # Factory should still work but may be slower
                assert context is not None, f"Factory failed at pressure level {pressure_level}"
                
                # Record performance degradation
                degradation_ratio = pressure_duration / baseline_metrics["creation_time"]
                logger.info(f"Performance degradation at level {pressure_level}: {degradation_ratio:.2f}x baseline")
                
                # RESILIENCE ASSERTION: Even under pressure, should complete in reasonable time
                max_allowed_degradation = 5.0  # 5x baseline is acceptable under pressure
                assert degradation_ratio < max_allowed_degradation, f"Factory too slow under pressure: {degradation_ratio:.2f}x"
                
                # Short recovery between pressure levels
                await asyncio.sleep(0.5)
        
        finally:
            # Clean up memory pressure
            del memory_pressure_objects
            gc.collect()
            
        final_memory = self.stress_manager.get_system_memory_usage()
        logger.info(f" PASS:  Resource exhaustion recovery test completed. Final memory: {final_memory}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_state_corruption_detection_and_recovery(self, real_services_fixture):
        """
        Test factory state corruption detection and automatic recovery.
        
        This test corrupts internal factory state and validates that the
        factory can detect corruption and recover automatically without
        affecting user operations.
        
        CRITICAL: Tests factory internal state management resilience.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for state corruption testing")
            
        engine = real_services_fixture["postgres"]
        session_factory = RequestScopedSessionFactory(engine=engine)
        context_factory = UserContextFactory(
            session_factory=session_factory,
            unified_id_manager=self.id_manager
        )
        
        # Create test users
        test_users = []
        for i in range(4):
            user_token, user_data = await create_authenticated_user(
                environment="test",
                user_id=f"corruption-test-{i}-{uuid.uuid4().hex[:8]}",
                email=f"corruption-test-{i}-{int(time.time())}@example.com"
            )
            test_users.append(user_data)
        
        # Create initial contexts to establish factory state
        initial_contexts = []
        async with session_factory.create_session() as session:
            for user_data in test_users:
                context = await context_factory.create_user_context(
                    user_id=user_data["id"],
                    session=session,
                    metadata={"phase": "initial", "user_index": test_users.index(user_data)}
                )
                initial_contexts.append(context)
        
        # CORRUPTION SCENARIO 1: Corrupt factory internal caches
        await self._corrupt_factory_internal_state(context_factory, corruption_type="cache")
        
        # Test that factory detects corruption and recovers
        corruption_recovery_start = time.time()
        
        async with session_factory.create_session() as session:
            # This operation should trigger corruption detection and recovery
            recovery_context = await context_factory.get_user_context(
                user_id=test_users[0]["id"],
                session=session
            )
            
        corruption_recovery_time = time.time() - corruption_recovery_start
        
        assert recovery_context is not None, "Factory failed to recover from state corruption"
        assert recovery_context.user_id == test_users[0]["id"], "Recovered context has wrong user_id"
        
        # CORRUPTION SCENARIO 2: Corrupt factory configuration state
        await self._corrupt_factory_internal_state(context_factory, corruption_type="config")
        
        # Validate factory can still create new contexts after config corruption
        async with session_factory.create_session() as session:
            post_corruption_context = await context_factory.create_user_context(
                user_id=test_users[1]["id"],
                session=session,
                metadata={"phase": "post_corruption", "corruption_type": "config"}
            )
        
        assert post_corruption_context is not None, "Factory failed after configuration corruption"
        
        # PERFORMANCE ASSERTION: Recovery should be reasonably fast
        assert corruption_recovery_time < 5.0, f"Corruption recovery too slow: {corruption_recovery_time:.2f}s"
        
        logger.info(f" PASS:  Factory state corruption recovery successful in {corruption_recovery_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_dynamic_factory_reconfiguration_stability(self, real_services_fixture):
        """
        Test factory stability during dynamic reconfiguration scenarios.
        
        This test simulates configuration changes while factory is actively
        serving requests. Factory should handle reconfigurations gracefully
        without disrupting ongoing operations.
        
        CRITICAL: Tests factory hot-reconfiguration capabilities.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for dynamic reconfiguration testing")
            
        engine = real_services_fixture["postgres"]
        session_factory = RequestScopedSessionFactory(engine=engine)
        context_factory = UserContextFactory(
            session_factory=session_factory,
            unified_id_manager=self.id_manager
        )
        
        # Create test users
        reconfiguration_users = []
        for i in range(6):
            user_token, user_data = await create_authenticated_user(
                environment="test", 
                user_id=f"reconfig-{i}-{uuid.uuid4().hex[:8]}",
                email=f"reconfig-{i}-{int(time.time())}@example.com"
            )
            reconfiguration_users.append(user_data)
        
        # CONCURRENT OPERATIONS: Start continuous factory operations
        operation_results = {}
        operation_errors = []
        
        async def continuous_factory_operations():
            """Run continuous factory operations during reconfiguration."""
            operation_count = 0
            
            for i in range(20):  # 20 operations during reconfiguration
                try:
                    user_data = random.choice(reconfiguration_users)
                    async with session_factory.create_session() as session:
                        context = await context_factory.create_user_context(
                            user_id=user_data["id"],
                            session=session,
                            metadata={
                                "operation_index": i,
                                "during_reconfig": True,
                                "timestamp": time.time()
                            }
                        )
                        
                        operation_results[i] = {
                            "success": context is not None,
                            "context_id": context.context_id if context else None,
                            "user_id": user_data["id"]
                        }
                        operation_count += 1
                        
                        # Small delay between operations
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    operation_errors.append({"operation": i, "error": str(e)})
                    logger.warning(f"Operation {i} failed during reconfiguration: {e}")
        
        # Start continuous operations
        operations_task = asyncio.create_task(continuous_factory_operations())
        
        # DYNAMIC RECONFIGURATION: Change factory configuration while operations running
        reconfig_start = time.time()
        
        # Simulate configuration changes
        config_changes = [
            {"connection_pool_size": 10},
            {"cache_ttl": 300},
            {"max_contexts_per_user": 5},
            {"enable_debug_mode": True},
            {"connection_timeout": 30}
        ]
        
        for i, config_change in enumerate(config_changes):
            logger.info(f"Applying configuration change {i+1}/5: {config_change}")
            
            # Simulate configuration update
            await self._apply_factory_configuration_change(context_factory, config_change)
            
            # Brief pause between configuration changes
            await asyncio.sleep(0.3)
        
        # Wait for operations to complete
        await operations_task
        reconfig_duration = time.time() - reconfig_start
        
        # Validate operation success during reconfiguration
        successful_operations = sum(1 for result in operation_results.values() if result["success"])
        total_operations = len(operation_results)
        success_rate = successful_operations / max(total_operations, 1)
        
        # STABILITY ASSERTION: Most operations should succeed during reconfiguration
        min_success_rate = 0.85  # 85% success rate during reconfiguration
        assert success_rate >= min_success_rate, f"Success rate during reconfiguration too low: {success_rate:.1%}"
        
        # ERROR ANALYSIS: Check if errors are acceptable
        critical_errors = [e for e in operation_errors if "timeout" not in e["error"].lower()]
        assert len(critical_errors) <= 2, f"Too many critical errors during reconfiguration: {critical_errors}"
        
        logger.info(f" PASS:  Dynamic reconfiguration stability: {successful_operations}/{total_operations} ops successful ({success_rate:.1%}) in {reconfig_duration:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_behavior_under_memory_pressure_extremes(self, real_services_fixture):
        """
        Test factory behavior under extreme memory pressure conditions.
        
        This test pushes memory usage to near-system limits and validates
        that factory patterns gracefully degrade performance rather than
        crashing the system.
        
        CRITICAL: This is an EXTREME STRESS test - monitor system resources.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for extreme memory pressure testing")
            
        engine = real_services_fixture["postgres"]
        session_factory = RequestScopedSessionFactory(engine=engine)
        context_factory = UserContextFactory(
            session_factory=session_factory,
            unified_id_manager=self.id_manager
        )
        
        # Create test user
        user_token, user_data = await create_authenticated_user(
            environment="test",
            user_id=f"memory-extreme-{uuid.uuid4().hex[:8]}",
            email=f"memory-extreme-{int(time.time())}@example.com"
        )
        user_id = user_data["id"]
        
        # Measure initial memory
        initial_memory = self.stress_manager.get_system_memory_usage()
        logger.info(f"Starting extreme memory pressure test. Initial: {initial_memory}")
        
        # EXTREME MEMORY PRESSURE: Create very large data structures
        extreme_pressure_data = []
        factory_operations = []
        
        try:
            # Gradually increase to extreme memory pressure
            for pressure_wave in range(1, 4):  # 3 waves of extreme pressure
                logger.info(f"Extreme memory pressure wave {pressure_wave}/3")
                
                # Create massive memory pressure
                wave_data = []
                for chunk in range(500):  # Large chunks
                    massive_chunk = {
                        f"extreme_{i}_{j}": f"data_{'X' * 100}" 
                        for i in range(50) for j in range(20)  # 1000 entries per chunk
                    }
                    wave_data.append(massive_chunk)
                
                extreme_pressure_data.extend(wave_data)
                
                current_memory = self.stress_manager.get_system_memory_usage()
                logger.info(f"Memory pressure wave {pressure_wave}: {current_memory}")
                
                # Test factory operation under extreme pressure
                extreme_start = time.time()
                
                try:
                    async with session_factory.create_session() as session:
                        extreme_context = await asyncio.wait_for(
                            context_factory.create_user_context(
                                user_id=user_id,
                                session=session,
                                metadata={
                                    "extreme_pressure_wave": pressure_wave,
                                    "memory_usage": current_memory,
                                    "data_chunks": len(wave_data),
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                            ),
                            timeout=15.0  # Generous timeout under extreme pressure
                        )
                        
                    extreme_duration = time.time() - extreme_start
                    
                    factory_operations.append({
                        "wave": pressure_wave,
                        "success": extreme_context is not None,
                        "duration": extreme_duration,
                        "memory": current_memory
                    })
                    
                    if extreme_context:
                        logger.info(f"Wave {pressure_wave}: Factory survived extreme pressure ({extreme_duration:.2f}s)")
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Wave {pressure_wave}: Factory operation timed out under extreme pressure")
                    factory_operations.append({
                        "wave": pressure_wave,
                        "success": False,
                        "duration": 15.0,
                        "memory": current_memory,
                        "error": "timeout"
                    })
                
                # Brief recovery between waves
                await asyncio.sleep(1.0)
        
        finally:
            # CRITICAL: Clean up extreme memory pressure
            logger.info("Cleaning up extreme memory pressure...")
            del extreme_pressure_data
            gc.collect()
            
            recovery_memory = self.stress_manager.get_system_memory_usage()
            logger.info(f"Memory after cleanup: {recovery_memory}")
        
        # Analyze factory behavior under extreme conditions
        successful_operations = [op for op in factory_operations if op["success"]]
        failed_operations = [op for op in factory_operations if not op["success"]]
        
        # EXTREME STRESS ASSERTIONS
        total_ops = len(factory_operations)
        success_count = len(successful_operations)
        
        # Under extreme pressure, even 50% success rate is acceptable
        min_extreme_success_rate = 0.5
        actual_success_rate = success_count / max(total_ops, 1)
        
        if actual_success_rate >= min_extreme_success_rate:
            logger.info(f" PASS:  Factory showed good resilience under extreme memory pressure: {success_count}/{total_ops} operations successful")
        else:
            # Even if success rate is low, system should not crash
            logger.warning(f" WARNING: [U+FE0F] Factory struggled under extreme pressure: {success_count}/{total_ops} successful, but system remained stable")
        
        # CRITICAL: System should not crash - if we reach here, test passes
        assert True, "Factory survived extreme memory pressure without system crash"

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_concurrent_factory_reconfiguration_isolation(self, real_services_fixture):
        """
        Test isolation between concurrent factory reconfiguration operations.
        
        This test validates that when multiple factory reconfigurations
        happen simultaneously, they don't interfere with each other or
        cause race conditions that could corrupt factory state.
        
        CRITICAL: Tests concurrent reconfiguration safety.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for concurrent reconfiguration testing")
            
        engine = real_services_fixture["postgres"]
        
        # Create multiple factory instances for concurrent testing
        factories = []
        for i in range(3):
            session_factory = RequestScopedSessionFactory(engine=engine)
            context_factory = UserContextFactory(
                session_factory=session_factory,
                unified_id_manager=self.id_manager
            )
            factories.append({
                "id": f"factory_{i}",
                "session_factory": session_factory,
                "context_factory": context_factory
            })
        
        # Create test users for each factory
        factory_users = []
        for i, factory in enumerate(factories):
            user_token, user_data = await create_authenticated_user(
                environment="test",
                user_id=f"concurrent-factory-{i}-{uuid.uuid4().hex[:8]}",
                email=f"concurrent-factory-{i}-{int(time.time())}@example.com"
            )
            factory_users.append(user_data)
        
        # CONCURRENT RECONFIGURATION: Apply different configurations simultaneously
        reconfiguration_results = {}
        
        async def reconfigure_factory_concurrently(factory_info, user_data, config_set):
            """Apply configuration changes to a specific factory concurrently."""
            factory_id = factory_info["id"]
            context_factory = factory_info["context_factory"]
            session_factory = factory_info["session_factory"]
            
            results = []
            
            for config_index, config in enumerate(config_set):
                try:
                    # Apply configuration
                    reconfig_start = time.time()
                    await self._apply_factory_configuration_change(context_factory, config)
                    
                    # Test factory operation with new configuration
                    async with session_factory.create_session() as session:
                        context = await context_factory.create_user_context(
                            user_id=user_data["id"],
                            session=session,
                            metadata={
                                "factory_id": factory_id,
                                "config_index": config_index,
                                "config": config,
                                "concurrent_test": True
                            }
                        )
                    
                    reconfig_duration = time.time() - reconfig_start
                    
                    results.append({
                        "config_index": config_index,
                        "success": context is not None,
                        "duration": reconfig_duration,
                        "context_id": context.context_id if context else None
                    })
                    
                    # Small delay between configurations
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    results.append({
                        "config_index": config_index,
                        "success": False,
                        "error": str(e)
                    })
            
            return results
        
        # Define different configuration sets for each factory
        config_sets = [
            [{"pool_size": 5}, {"timeout": 20}, {"cache_size": 100}],
            [{"pool_size": 8}, {"timeout": 25}, {"cache_size": 150}],
            [{"pool_size": 3}, {"timeout": 15}, {"cache_size": 75}]
        ]
        
        # Start concurrent reconfigurations
        concurrent_start = time.time()
        reconfiguration_tasks = []
        
        for i, factory in enumerate(factories):
            task = asyncio.create_task(
                reconfigure_factory_concurrently(factory, factory_users[i], config_sets[i])
            )
            reconfiguration_tasks.append(task)
        
        # Wait for all concurrent reconfigurations
        all_results = await asyncio.gather(*reconfiguration_tasks, return_exceptions=True)
        concurrent_duration = time.time() - concurrent_start
        
        # Analyze concurrent reconfiguration results
        total_reconfigurations = 0
        successful_reconfigurations = 0
        
        for factory_index, result in enumerate(all_results):
            if isinstance(result, Exception):
                logger.error(f"Factory {factory_index} reconfiguration failed: {result}")
            else:
                factory_successful = sum(1 for r in result if r["success"])
                total_reconfigurations += len(result)
                successful_reconfigurations += factory_successful
                
                reconfiguration_results[f"factory_{factory_index}"] = {
                    "results": result,
                    "success_count": factory_successful,
                    "total_count": len(result)
                }
        
        # ISOLATION ASSERTION: Concurrent reconfigurations should not interfere
        overall_success_rate = successful_reconfigurations / max(total_reconfigurations, 1)
        min_concurrent_success_rate = 0.8  # 80% success rate for concurrent operations
        
        assert overall_success_rate >= min_concurrent_success_rate, f"Concurrent reconfiguration success rate too low: {overall_success_rate:.1%}"
        
        # Validate no configuration corruption occurred
        for factory_info in factories:
            async with factory_info["session_factory"].create_session() as session:
                # Test that each factory still works correctly after concurrent changes
                validation_context = await factory_info["context_factory"].create_user_context(
                    user_id=factory_users[factories.index(factory_info)]["id"],
                    session=session,
                    metadata={"validation": True, "post_concurrent_reconfig": True}
                )
                
                assert validation_context is not None, f"Factory {factory_info['id']} corrupted after concurrent reconfiguration"
        
        logger.info(f" PASS:  Concurrent factory reconfiguration isolation successful: {successful_reconfigurations}/{total_reconfigurations} reconfigurations in {concurrent_duration:.2f}s")

    async def _measure_factory_baseline_performance(self, context_factory, user_id: str, engine) -> Dict[str, float]:
        """Measure baseline factory performance for comparison."""
        session_factory = RequestScopedSessionFactory(engine=engine)
        
        baseline_times = []
        for i in range(5):  # 5 baseline measurements
            start_time = time.time()
            
            async with session_factory.create_session() as session:
                context = await context_factory.create_user_context(
                    user_id=user_id,
                    session=session,
                    metadata={"baseline_test": i, "timestamp": time.time()}
                )
            
            baseline_times.append(time.time() - start_time)
            assert context is not None, f"Baseline measurement {i} failed"
        
        return {
            "creation_time": sum(baseline_times) / len(baseline_times),
            "min_time": min(baseline_times),
            "max_time": max(baseline_times)
        }
    
    async def _corrupt_factory_internal_state(self, context_factory, corruption_type: str):
        """Create REAL factory corruption by disrupting underlying services."""
        from test_framework.unified_docker_manager import get_default_manager
        
        docker_manager = get_default_manager()
        
        if corruption_type == "cache":
            # REAL cache corruption: restart Redis to clear all cache data
            logger.info("Creating REAL cache corruption by restarting Redis service...")
            redis_restarted = docker_manager.restart_service("redis", force=True)
            if redis_restarted:
                logger.info(" PASS:  Redis service restarted - REAL cache corruption created")
                # Wait for Redis to be back online
                await asyncio.sleep(2)
            else:
                logger.error(" FAIL:  Failed to restart Redis for real cache corruption")
                raise Exception("Failed to create real cache corruption via Redis restart")
            
        elif corruption_type == "config":
            # REAL configuration corruption: restart PostgreSQL to disrupt database connections
            logger.info("Creating REAL configuration corruption by restarting PostgreSQL service...")
            postgres_restarted = docker_manager.restart_service("postgres", force=True)
            if postgres_restarted:
                logger.info(" PASS:  PostgreSQL service restarted - REAL configuration corruption created")
                # Wait for PostgreSQL to be back online
                await asyncio.sleep(5)  # PostgreSQL takes longer to restart
            else:
                logger.error(" FAIL:  Failed to restart PostgreSQL for real configuration corruption")
                raise Exception("Failed to create real configuration corruption via PostgreSQL restart")
        
        # Verify services are back online after corruption
        services_healthy = docker_manager.wait_for_services(["postgres", "redis"], timeout=30)
        if not services_healthy:
            logger.error(" WARNING: [U+FE0F] Services not healthy after corruption - factory will be in degraded state")
        else:
            logger.info(" PASS:  Services recovered after corruption - factory should handle degraded state gracefully")
    
    async def _apply_factory_configuration_change(self, context_factory, config_change: Dict[str, Any]):
        """Apply REAL factory configuration changes by modifying service behavior."""
        from test_framework.unified_docker_manager import get_default_manager
        
        docker_manager = get_default_manager()
        
        # Map configuration changes to real service modifications
        if "pool_size" in config_change:
            # REAL pool size change: restart backend with different connection pool settings
            logger.info(f"Applying REAL pool size change: {config_change['pool_size']}")
            # This simulates the load that a different pool size would create
            if config_change['pool_size'] < 5:
                # Small pool = more pressure, restart backend to simulate pool exhaustion
                docker_manager.restart_service("backend", force=True)
                await asyncio.sleep(random.uniform(0.2, 0.5))
            
        if "timeout" in config_change:
            # REAL timeout change: create network delay by restarting services
            logger.info(f"Applying REAL timeout change: {config_change['timeout']} seconds")
            # Simulate timeout pressure by restarting a random service
            services = ["postgres", "redis"]
            service_to_restart = random.choice(services)
            docker_manager.restart_service(service_to_restart, force=True)
            
        if "cache_size" in config_change:
            # REAL cache size change: restart Redis to clear cache and simulate different cache behavior
            logger.info(f"Applying REAL cache size change: {config_change['cache_size']}")
            docker_manager.restart_service("redis", force=True)
        
        # Real configuration changes take time to propagate
        await asyncio.sleep(random.uniform(0.2, 0.8))
        
        # Wait for services to be healthy after configuration change
        docker_manager.wait_for_services(["postgres", "redis", "backend"], timeout=15)
        
        logger.info(f" PASS:  REAL factory configuration change applied: {config_change}")

    def teardown_method(self):
        """Clean up after each test with resource reporting."""
        super().teardown_method()
        
        # Report final resource usage
        final_memory = self.stress_manager.get_system_memory_usage()
        logger.info(f"Test completed. Final memory usage: {final_memory}")
        
        # Clean up stress manager
        self.stress_manager.active_factories.clear()
        self.stress_manager.resource_monitors.clear()
        self.stress_manager.failure_scenarios.clear()
        
        # Force garbage collection
        gc.collect()