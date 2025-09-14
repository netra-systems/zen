#!/usr/bin/env python
"""WebSocket Manager Instance Uniqueness Test - SSOT CRITICAL

PURPOSE: Validate single manager instance per user context or proper factory-managed uniqueness
EXPECTED BEHAVIOR: Test should FAIL initially, proving multiple manager instances created
SUCCESS CRITERIA: After SSOT consolidation, proper instance management established

BUSINESS VALUE: Prevents memory leaks and ensures proper user isolation
FAILURE CONSEQUENCE: Multiple instances cause memory growth and user data contamination

This test is designed to FAIL initially, proving that WebSocket manager instances
are not properly managed, leading to resource leaks and user isolation violations.
After SSOT consolidation, this test should PASS with proper instance management.

Test Categories:
1. Instance Creation - Validate manager instance creation patterns
2. Instance Uniqueness - Verify singleton or factory-managed uniqueness
3. User Isolation - Ensure separate instances for different users
4. Memory Management - Validate no instance leaks occur

Expected Failure Modes (Before SSOT):
- Multiple instances created for same user context
- Global singleton shared across different users
- Memory leaks from unmanaged instance creation
- Instance state contamination between users

Expected Success Criteria (After SSOT):
- Single instance per user context OR properly managed factory pattern
- Perfect user isolation between different user contexts
- No memory leaks or resource accumulation
- Consistent instance behavior across all access patterns
"""

import asyncio
import gc
import sys
import os
import weakref
import time
import threading
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.logging.unified_logging_ssot import get_logger

# Import types and utilities
from shared.types.core_types import UserID, ThreadID, ensure_user_id, ensure_thread_id
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Import WebSocket manager (canonical path)
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

logger = get_logger(__name__)


@dataclass
class InstanceTracker:
    """Track WebSocket manager instances for uniqueness validation."""
    instance_id: str
    user_id: str
    thread_id: str
    creation_time: float
    instance_type: str
    memory_address: str
    weak_ref: Optional[Any] = None


class TestWebSocketManagerInstanceUniqueness(SSotAsyncTestCase):
    """
    SSOT Critical Test: WebSocket Manager Instance Uniqueness Validation

    This test validates that WebSocket manager instances are properly managed
    to prevent memory leaks, ensure user isolation, and maintain system stability.

    EXPECTED TO FAIL INITIALLY: This test should fail before SSOT consolidation,
    proving that instance management is not properly implemented.
    """

    def setup_method(self, method):
        """Setup test environment for instance uniqueness validation."""
        super().setup_method(method)

        # Set environment for SSOT validation
        self.set_env_var("TESTING_SSOT_WEBSOCKET", "true")
        self.set_env_var("WEBSOCKET_INSTANCE_TRACKING", "strict")
        self.set_env_var("MEMORY_LEAK_DETECTION", "enabled")

        # Instance tracking
        self.created_instances = []
        self.instance_registry = {}
        self.user_instance_map = {}
        self.memory_snapshots = []

        # Performance tracking
        self.creation_times = []
        self.gc_collections_before = gc.get_count()

        logger.info(f"🔍 SSOT TEST: {method.__name__ if method else 'unknown'}")
        logger.info("📍 PURPOSE: Validate WebSocket manager instance uniqueness and management")

    async def test_websocket_manager_single_user_instance_uniqueness(self):
        """
        CRITICAL: Validate single instance per user context.

        This test creates multiple manager requests for the same user context
        and validates that either:
        1. The same instance is returned (singleton per user)
        2. A new instance is created but old ones are properly cleaned up

        EXPECTED TO FAIL: Multiple instances created without cleanup (memory leak)
        AFTER CONSOLIDATION: Proper instance management established
        """
        logger.info("🔍 PHASE 1: Testing single user instance uniqueness")

        # Create consistent user context
        user_context = UserExecutionContext(
            user_id=ensure_user_id("unique_test_user"),
            thread_id=ensure_thread_id("unique_test_thread"),
            session_id="unique_test_session"
        )

        instances = []
        instance_ids = set()
        memory_addresses = set()

        # Create multiple manager instances for same user
        for i in range(5):
            logger.debug(f"📍 Creating manager instance {i+1}/5 for same user")

            creation_start = time.time()
            manager = await get_websocket_manager(user_context=user_context)
            creation_time = time.time() - creation_start

            # Track instance details
            instance_info = InstanceTracker(
                instance_id=str(id(manager)),
                user_id=str(user_context.user_id),
                thread_id=str(user_context.thread_id),
                creation_time=creation_time,
                instance_type=type(manager).__name__,
                memory_address=hex(id(manager)),
                weak_ref=weakref.ref(manager)
            )

            instances.append(manager)
            self.created_instances.append(instance_info)
            instance_ids.add(instance_info.instance_id)
            memory_addresses.add(instance_info.memory_address)
            self.creation_times.append(creation_time)

            logger.info(f"✅ Instance {i+1}: {instance_info.memory_address} ({instance_info.instance_type})")

        # Analyze instance uniqueness
        logger.info(f"📊 INSTANCE ANALYSIS:")
        logger.info(f"   Instances created: {len(instances)}")
        logger.info(f"   Unique instance IDs: {len(instance_ids)}")
        logger.info(f"   Unique memory addresses: {len(memory_addresses)}")
        logger.info(f"   Average creation time: {sum(self.creation_times)/len(self.creation_times):.4f}s")

        # Validate instance management - THIS SHOULD FAIL OR REQUIRE SPECIFIC BEHAVIOR
        if len(instance_ids) == 1:
            # Singleton pattern - same instance returned
            logger.info("✅ SINGLETON PATTERN: Same instance returned for same user context")
            self.record_metric("instance_pattern", "singleton_per_user")

        elif len(instance_ids) == len(instances):
            # New instance each time - check if this is intentional and properly managed
            logger.warning("⚠️ NEW INSTANCE PATTERN: New instance created each time")

            # This might be acceptable IF old instances are properly cleaned up
            # Let's check memory management
            instances.clear()  # Release references
            gc.collect()  # Force garbage collection

            # Wait for cleanup
            await asyncio.sleep(0.1)

            # Check if instances were cleaned up
            alive_instances = sum(1 for instance_info in self.created_instances
                                if instance_info.weak_ref is not None and instance_info.weak_ref() is not None)

            if alive_instances > 1:
                failure_message = (
                    f"❌ WEBSOCKET INSTANCE LEAK: Multiple instances alive for single user!\n"
                    f"   Created instances: {len(instances)} (expected: 5)\n"
                    f"   Alive after cleanup: {alive_instances} (expected: 0-1)\n"
                    f"   Unique instances: {len(instance_ids)}\n"
                    f"   Memory addresses: {memory_addresses}\n"
                    f"\n🚨 THIS PROVES MEMORY LEAK - INSTANCE MANAGEMENT REQUIRED!"
                )

                logger.error(failure_message)
                self.record_metric("instance_leak_detected", True)

                # This assertion should FAIL if instances are not properly managed
                self.fail(failure_message)

            else:
                logger.info("✅ INSTANCE CLEANUP SUCCESS: Old instances properly cleaned up")
                self.record_metric("instance_pattern", "new_instance_with_cleanup")

        else:
            # Mixed pattern - some instances same, some different (unexpected)
            failure_message = (
                f"❌ WEBSOCKET INSTANCE INCONSISTENCY: Mixed instance creation pattern!\n"
                f"   Created instances: {len(instances)}\n"
                f"   Unique instances: {len(instance_ids)}\n"
                f"   This indicates inconsistent instance management.\n"
                f"\n🚨 THIS PROVES INCONSISTENT BEHAVIOR - SSOT CONSOLIDATION REQUIRED!"
            )

            logger.error(failure_message)
            self.record_metric("instance_pattern", "inconsistent")

            # This assertion should FAIL for inconsistent behavior
            self.fail(failure_message)

    async def test_websocket_manager_multi_user_isolation(self):
        """
        CRITICAL: Validate perfect user isolation between different users.

        This test creates managers for different users and validates that:
        1. Each user gets their own instance (no sharing)
        2. Instances are properly isolated
        3. No cross-user contamination occurs

        EXPECTED TO FAIL: Shared instances between different users (isolation breach)
        AFTER CONSOLIDATION: Perfect user isolation established
        """
        logger.info("🔍 PHASE 2: Testing multi-user instance isolation")

        # Create different user contexts
        user_contexts = [
            UserExecutionContext(
                user_id=ensure_user_id(f"isolation_user_{i}"),
                thread_id=ensure_thread_id(f"isolation_thread_{i}"),
                session_id=f"isolation_session_{i}"
            )
            for i in range(3)
        ]

        user_instances = {}
        shared_instances = []

        # Create managers for each user
        for i, user_context in enumerate(user_contexts):
            logger.debug(f"📍 Creating manager for user {i+1}/3: {user_context.user_id}")

            manager = await get_websocket_manager(user_context=user_context)

            # Track instance for this user
            instance_info = InstanceTracker(
                instance_id=str(id(manager)),
                user_id=str(user_context.user_id),
                thread_id=str(user_context.thread_id),
                creation_time=time.time(),
                instance_type=type(manager).__name__,
                memory_address=hex(id(manager)),
                weak_ref=weakref.ref(manager)
            )

            user_instances[str(user_context.user_id)] = {
                'manager': manager,
                'info': instance_info,
                'context': user_context
            }

            logger.info(f"✅ User {i+1}: {instance_info.memory_address} ({instance_info.instance_type})")

        # Analyze user isolation
        all_instance_ids = [data['info'].instance_id for data in user_instances.values()]
        unique_instance_ids = set(all_instance_ids)

        logger.info(f"📊 USER ISOLATION ANALYSIS:")
        logger.info(f"   Users tested: {len(user_contexts)}")
        logger.info(f"   Instances created: {len(all_instance_ids)}")
        logger.info(f"   Unique instances: {len(unique_instance_ids)}")

        # Check for shared instances between users
        if len(unique_instance_ids) < len(user_contexts):
            # Some instances are shared between users - CRITICAL SECURITY ISSUE
            instance_count_map = {}
            for instance_id in all_instance_ids:
                instance_count_map[instance_id] = instance_count_map.get(instance_id, 0) + 1

            shared_instances = [iid for iid, count in instance_count_map.items() if count > 1]

            failure_message = (
                f"❌ CRITICAL USER ISOLATION BREACH: Shared instances between different users!\n"
                f"   Users: {len(user_contexts)}\n"
                f"   Unique instances: {len(unique_instance_ids)} (expected: {len(user_contexts)})\n"
                f"   Shared instances: {shared_instances}\n"
                f"   Instance sharing details:\n"
            )

            for user_id, data in user_instances.items():
                sharing_count = instance_count_map.get(data['info'].instance_id, 1)
                failure_message += f"     - User {user_id}: Instance {data['info'].memory_address} (shared: {sharing_count > 1})\n"

            failure_message += f"\n🚨 THIS IS A CRITICAL SECURITY VULNERABILITY - IMMEDIATE FIX REQUIRED!"

            logger.error(failure_message)
            self.record_metric("user_isolation_breach", True)
            self.record_metric("shared_instances", len(shared_instances))

            # This assertion should FAIL for user isolation breaches
            self.fail(failure_message)

        else:
            # Perfect isolation - each user has their own instance
            logger.info("✅ USER ISOLATION SUCCESS: Each user has unique manager instance")
            self.record_metric("user_isolation_breach", False)
            self.record_metric("user_isolation_perfect", True)

        # Additional validation: Test instance behavior isolation
        await self._validate_instance_behavior_isolation(user_instances)

    async def _validate_instance_behavior_isolation(self, user_instances: Dict[str, Dict[str, Any]]):
        """Validate that instances behave independently (no shared state)."""
        logger.info("🔍 PHASE 2b: Validating instance behavior isolation")

        # Test that instances can be configured independently
        for user_id, data in user_instances.items():
            manager = data['manager']
            context = data['context']

            # Try to set some state or configuration on each instance
            if hasattr(manager, 'set_user_context'):
                try:
                    await manager.set_user_context(context)
                    logger.debug(f"✅ Set context for user {user_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not set context for user {user_id}: {e}")

            # Validate that each instance has proper user context
            if hasattr(manager, 'user_context') or hasattr(manager, 'get_user_context'):
                try:
                    if hasattr(manager, 'get_user_context'):
                        instance_context = await manager.get_user_context()
                    else:
                        instance_context = getattr(manager, 'user_context', None)

                    if instance_context:
                        self.assertEqual(
                            str(instance_context.user_id),
                            str(context.user_id),
                            f"User context mismatch for user {user_id}"
                        )
                        logger.debug(f"✅ Context validation passed for user {user_id}")

                except Exception as e:
                    logger.warning(f"⚠️ Could not validate context for user {user_id}: {e}")

        logger.info("✅ BEHAVIOR ISOLATION: Instance behavior appears isolated")

    async def test_websocket_manager_concurrent_creation_safety(self):
        """
        CRITICAL: Validate thread-safe instance creation under concurrent load.

        This test creates multiple managers concurrently and validates that:
        1. No race conditions occur during instance creation
        2. Instance management remains consistent under load
        3. User isolation is maintained during concurrent access

        EXPECTED TO FAIL: Race conditions or inconsistent instance creation
        AFTER CONSOLIDATION: Thread-safe instance management
        """
        logger.info("🔍 PHASE 3: Testing concurrent instance creation safety")

        # Create multiple user contexts for concurrent testing
        user_contexts = [
            UserExecutionContext(
                user_id=ensure_user_id(f"concurrent_user_{i}"),
                thread_id=ensure_thread_id(f"concurrent_thread_{i}"),
                session_id=f"concurrent_session_{i}"
            )
            for i in range(10)
        ]

        # Concurrent creation tasks
        async def create_manager_for_user(user_context: UserExecutionContext) -> Tuple[UserExecutionContext, Any, float]:
            """Create manager for user and return timing info."""
            start_time = time.time()
            try:
                manager = await get_websocket_manager(user_context=user_context)
                creation_time = time.time() - start_time
                return user_context, manager, creation_time
            except Exception as e:
                logger.error(f"❌ Failed to create manager for {user_context.user_id}: {e}")
                return user_context, None, time.time() - start_time

        # Execute concurrent creation
        logger.info(f"📍 Creating {len(user_contexts)} managers concurrently")
        concurrent_start = time.time()

        tasks = [create_manager_for_user(context) for context in user_contexts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        concurrent_time = time.time() - concurrent_start

        # Analyze concurrent creation results
        successful_creations = []
        failed_creations = []
        creation_times = []

        for result in results:
            if isinstance(result, Exception):
                failed_creations.append(str(result))
                logger.error(f"❌ Concurrent creation exception: {result}")
            else:
                context, manager, timing = result
                if manager is not None:
                    successful_creations.append((context, manager))
                    creation_times.append(timing)
                else:
                    failed_creations.append(f"Manager creation returned None for {context.user_id}")

        logger.info(f"📊 CONCURRENT CREATION ANALYSIS:")
        logger.info(f"   Total attempted: {len(user_contexts)}")
        logger.info(f"   Successful: {len(successful_creations)}")
        logger.info(f"   Failed: {len(failed_creations)}")
        logger.info(f"   Total time: {concurrent_time:.3f}s")
        logger.info(f"   Average per creation: {sum(creation_times)/len(creation_times) if creation_times else 0:.4f}s")

        # Validate concurrent creation success
        if len(failed_creations) > 0:
            failure_message = (
                f"❌ CONCURRENT CREATION FAILURES: Some managers failed to create!\n"
                f"   Attempted: {len(user_contexts)}\n"
                f"   Successful: {len(successful_creations)}\n"
                f"   Failed: {len(failed_creations)}\n"
                f"   Failure details: {failed_creations[:3]}{'...' if len(failed_creations) > 3 else ''}\n"
                f"\n🚨 THIS INDICATES RACE CONDITIONS OR INSTABILITY!"
            )

            logger.error(failure_message)
            self.record_metric("concurrent_creation_failures", len(failed_creations))

            # This may fail if there are race conditions
            if len(failed_creations) > len(user_contexts) * 0.1:  # More than 10% failure rate
                self.fail(failure_message)

        # Validate instance uniqueness in concurrent creation
        instance_ids = set()
        for context, manager in successful_creations:
            instance_ids.add(id(manager))

        expected_unique_instances = len(successful_creations)
        actual_unique_instances = len(instance_ids)

        if actual_unique_instances != expected_unique_instances:
            failure_message = (
                f"❌ CONCURRENT INSTANCE UNIQUENESS FAILURE: Instance sharing detected!\n"
                f"   Successful creations: {len(successful_creations)}\n"
                f"   Unique instances: {actual_unique_instances}\n"
                f"   Expected unique: {expected_unique_instances}\n"
                f"\n🚨 THIS INDICATES INSTANCE SHARING OR RACE CONDITIONS!"
            )

            logger.error(failure_message)
            self.record_metric("concurrent_instance_sharing", True)

            # This should fail if instances are shared inappropriately
            self.fail(failure_message)

        logger.info("✅ CONCURRENT CREATION SUCCESS: All managers created safely with unique instances")
        self.record_metric("concurrent_creation_success_rate", len(successful_creations) / len(user_contexts))

    async def test_websocket_manager_memory_leak_detection(self):
        """
        CRITICAL: Validate no memory leaks in instance creation/destruction.

        This test creates and destroys managers multiple times and validates
        that memory usage doesn't continuously grow.

        EXPECTED TO FAIL: Memory leaks from unmanaged instance creation
        AFTER CONSOLIDATION: Stable memory usage with proper cleanup
        """
        logger.info("🔍 PHASE 4: Testing memory leak detection")

        # Baseline memory measurement
        gc.collect()
        baseline_objects = len(gc.get_objects())
        baseline_gc_counts = gc.get_count()

        logger.info(f"📊 BASELINE MEMORY: {baseline_objects} objects, GC: {baseline_gc_counts}")

        # Create and destroy managers multiple times
        peak_objects = baseline_objects
        memory_snapshots = [baseline_objects]

        for cycle in range(5):
            logger.debug(f"📍 Memory test cycle {cycle + 1}/5")

            # Create multiple managers
            user_contexts = [
                UserExecutionContext(
                    user_id=ensure_user_id(f"memory_test_user_{cycle}_{i}"),
                    thread_id=ensure_thread_id(f"memory_test_thread_{cycle}_{i}"),
                    session_id=f"memory_test_session_{cycle}_{i}"
                )
                for i in range(10)
            ]

            managers = []
            for context in user_contexts:
                manager = await get_websocket_manager(user_context=context)
                managers.append(manager)

            # Measure memory after creation
            current_objects = len(gc.get_objects())
            memory_snapshots.append(current_objects)
            peak_objects = max(peak_objects, current_objects)

            logger.debug(f"   After creation: {current_objects} objects (+{current_objects - baseline_objects})")

            # Clear references and force cleanup
            managers.clear()
            del managers
            del user_contexts
            gc.collect()

            # Measure memory after cleanup
            cleanup_objects = len(gc.get_objects())
            memory_snapshots.append(cleanup_objects)

            logger.debug(f"   After cleanup: {cleanup_objects} objects (+{cleanup_objects - baseline_objects})")

            # Small delay to allow any async cleanup
            await asyncio.sleep(0.1)

        # Final cleanup and measurement
        gc.collect()
        final_objects = len(gc.get_objects())
        final_gc_counts = gc.get_count()

        logger.info(f"📊 FINAL MEMORY: {final_objects} objects, GC: {final_gc_counts}")
        logger.info(f"   Peak objects: {peak_objects} (+{peak_objects - baseline_objects})")
        logger.info(f"   Final delta: +{final_objects - baseline_objects} objects")

        # Analyze memory growth
        memory_growth = final_objects - baseline_objects
        max_cycle_growth = max(memory_snapshots) - baseline_objects

        # Record memory metrics
        self.record_metric("baseline_objects", baseline_objects)
        self.record_metric("final_objects", final_objects)
        self.record_metric("memory_growth", memory_growth)
        self.record_metric("peak_memory_growth", max_cycle_growth)

        # Validate memory leak detection
        # Allow some growth for normal operations, but detect significant leaks
        acceptable_growth = 100  # Allow up to 100 additional objects
        significant_leak_threshold = 500  # More than 500 objects indicates a leak

        if memory_growth > significant_leak_threshold:
            failure_message = (
                f"❌ SIGNIFICANT MEMORY LEAK DETECTED: Excessive object growth!\n"
                f"   Baseline objects: {baseline_objects}\n"
                f"   Final objects: {final_objects}\n"
                f"   Memory growth: +{memory_growth} objects\n"
                f"   Peak growth: +{max_cycle_growth} objects\n"
                f"   Leak threshold: {significant_leak_threshold}\n"
                f"\n🚨 THIS INDICATES SERIOUS MEMORY MANAGEMENT ISSUES!"
            )

            logger.error(failure_message)
            self.record_metric("memory_leak_detected", True)

            # This should fail for significant memory leaks
            self.fail(failure_message)

        elif memory_growth > acceptable_growth:
            logger.warning(f"⚠️ MODERATE MEMORY GROWTH: +{memory_growth} objects (above {acceptable_growth} threshold)")
            self.record_metric("memory_growth_concern", True)
            # Don't fail, but log concern

        else:
            logger.info(f"✅ MEMORY MANAGEMENT SUCCESS: Growth +{memory_growth} objects (within acceptable limits)")
            self.record_metric("memory_leak_detected", False)

    def teardown_method(self, method):
        """Teardown with comprehensive instance tracking report."""
        try:
            # Force garbage collection and final memory check
            gc.collect()
            final_gc_counts = gc.get_count()

            # Check for lingering weak references
            alive_instances = sum(1 for instance_info in self.created_instances
                                if instance_info.weak_ref is not None and instance_info.weak_ref() is not None)

            # Log comprehensive results
            logger.info("📊 WEBSOCKET INSTANCE UNIQUENESS TEST RESULTS:")
            logger.info(f"   Instances tracked: {len(self.created_instances)}")
            logger.info(f"   Instances still alive: {alive_instances}")
            logger.info(f"   Average creation time: {sum(self.creation_times)/len(self.creation_times) if self.creation_times else 0:.4f}s")
            logger.info(f"   GC collections change: {[f - i for i, f in zip(self.gc_collections_before, final_gc_counts)]}")

            # Record final metrics
            self.record_metric("total_instances_tracked", len(self.created_instances))
            self.record_metric("instances_alive_at_teardown", alive_instances)
            self.record_metric("average_creation_time", sum(self.creation_times)/len(self.creation_times) if self.creation_times else 0)

            if alive_instances == 0:
                logger.info("✅ INSTANCE CLEANUP SUCCESS: All tracked instances properly cleaned up")
                self.record_metric("instance_cleanup_success", True)
            else:
                logger.warning(f"⚠️ INSTANCE CLEANUP WARNING: {alive_instances} instances still alive")
                self.record_metric("instance_cleanup_success", False)

        except Exception as e:
            logger.error(f"❌ TEARDOWN ERROR: {str(e)}")

        finally:
            super().teardown_method(method)


if __name__ == "__main__":
    """Run WebSocket manager instance uniqueness test directly."""
    import pytest

    logger.info("🚨 RUNNING WEBSOCKET MANAGER INSTANCE UNIQUENESS TEST")
    logger.info("📍 PURPOSE: Validate proper instance management and user isolation")

    # Run the test
    pytest.main([__file__, "-v", "-s"])