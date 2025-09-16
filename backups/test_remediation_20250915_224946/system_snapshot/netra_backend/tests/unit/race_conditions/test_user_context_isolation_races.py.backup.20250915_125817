"""
Race Condition Tests: User Context Isolation

This module tests for race conditions in UserExecutionContext creation and management.
Validates that user contexts remain properly isolated under concurrent load.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) 
- Business Goal: Ensure complete user data isolation and prevent data leakage
- Value Impact: Guarantees user privacy and prevents cross-user contamination
- Strategic Impact: CRITICAL - Multi-user isolation is fundamental security requirement

Test Coverage:
- 100 concurrent context creations (stress test)
- User data isolation verification
- Context factory race conditions  
- Memory leak detection under load
- ID generation collision detection
"""

import asyncio
import gc
import time
import uuid
import weakref
from collections import defaultdict
from typing import Dict, List, Set, Any
import pytest

from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextFactory,
    InvalidContextError,
    ContextIsolationError,
    create_isolated_execution_context,
    managed_user_context
)
from shared.isolated_environment import IsolatedEnvironment
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestUserContextIsolationRaces(SSotBaseTestCase):
    """Test race conditions in user context isolation and management."""
    
    def setup_method(self):
        """Set up test environment with isolation monitoring."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.set("TEST_MODE", "context_isolation_testing", source="test")
        
        # Track context creation and isolation
        self.created_contexts: List[UserExecutionContext] = []
        self.context_data: Dict[str, Dict] = {}
        self.isolation_violations: List[Dict] = []
        self.id_collisions: List[Dict] = []
        self.memory_refs: List[weakref.ref] = []
        
    def teardown_method(self):
        """Clean up test state and check for memory leaks."""
        # Force garbage collection
        gc.collect()
        
        # Check for leaked context references
        leaked_refs = [ref for ref in self.memory_refs if ref() is not None]
        if leaked_refs:
            logger.warning(f"Potential memory leaks detected: {len(leaked_refs)} contexts not garbage collected")
        
        # Clear test data
        self.created_contexts.clear()
        self.context_data.clear()
        self.isolation_violations.clear()
        self.id_collisions.clear()
        self.memory_refs.clear()
        
        super().teardown_method()
    
    def _track_context_creation(self, context: UserExecutionContext, metadata: Dict[str, Any]):
        """Track context creation for race condition analysis."""
        self.created_contexts.append(context)
        
        # Store context data for isolation verification
        self.context_data[context.request_id] = {
            "user_id": context.user_id,
            "thread_id": context.thread_id,
            "run_id": context.run_id,
            "request_id": context.request_id,
            "created_at": context.created_at,
            "agent_context": context.agent_context.copy(),
            "audit_metadata": context.audit_metadata.copy(),
            "creation_metadata": metadata,
            "thread_name": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        
        # Add weak reference for memory leak detection
        self.memory_refs.append(weakref.ref(context))
    
    def _check_id_collisions(self, context: UserExecutionContext):
        """Check for ID collisions that indicate race conditions."""
        # Check against existing contexts for ID collisions
        for existing_context in self.created_contexts[:-1]:  # Exclude current context
            if existing_context.request_id == context.request_id:
                self.id_collisions.append({
                    "collision_type": "request_id",
                    "id_value": context.request_id,
                    "contexts": [existing_context.user_id, context.user_id],
                    "timestamp": time.time()
                })
            
            # Check for user+thread+run combination collisions
            if (existing_context.user_id == context.user_id and
                existing_context.thread_id == context.thread_id and
                existing_context.run_id == context.run_id):
                self.id_collisions.append({
                    "collision_type": "user_thread_run_combination",
                    "user_id": context.user_id,
                    "thread_id": context.thread_id,
                    "run_id": context.run_id,
                    "timestamp": time.time()
                })
    
    def _verify_context_isolation(self, context: UserExecutionContext) -> bool:
        """Verify that context is properly isolated from other contexts."""
        try:
            # Verify isolation using built-in method
            context.verify_isolation()
            
            # Additional checks for concurrent access safety
            
            # Check that agent_context is not shared
            for other_context in self.created_contexts[:-1]:
                if other_context.user_id != context.user_id:
                    if id(other_context.agent_context) == id(context.agent_context):
                        self.isolation_violations.append({
                            "violation_type": "shared_agent_context",
                            "context1": other_context.request_id,
                            "context2": context.request_id,
                            "timestamp": time.time()
                        })
                        return False
                    
                    if id(other_context.audit_metadata) == id(context.audit_metadata):
                        self.isolation_violations.append({
                            "violation_type": "shared_audit_metadata",
                            "context1": other_context.request_id,
                            "context2": context.request_id,
                            "timestamp": time.time()
                        })
                        return False
            
            return True
            
        except ContextIsolationError as e:
            self.isolation_violations.append({
                "violation_type": "isolation_error",
                "context": context.request_id,
                "error": str(e),
                "timestamp": time.time()
            })
            return False
    
    @pytest.mark.unit
    @pytest.mark.race_conditions
    async def test_100_concurrent_context_creations(self):
        """Test 100 concurrent UserExecutionContext creations for race conditions."""
        
        async def create_user_context(user_index: int):
            """Create a single user context with tracking."""
            try:
                user_id = f"race_test_user_{user_index:03d}"
                thread_id = f"race_test_thread_{user_index:03d}_{uuid.uuid4().hex[:8]}"
                run_id = f"race_test_run_{user_index:03d}_{uuid.uuid4().hex[:8]}"
                
                # Add some variation in context creation
                if user_index % 3 == 0:
                    # Use factory method
                    context = UserContextFactory.create_context(
                        user_id=user_id,
                        thread_id=thread_id,
                        run_id=run_id
                    )
                elif user_index % 3 == 1:
                    # Use from_request factory method
                    context = UserExecutionContext.from_request(
                        user_id=user_id,
                        thread_id=thread_id,
                        run_id=run_id,
                        agent_context={"test_index": user_index},
                        audit_metadata={"creation_method": "from_request"}
                    )
                else:
                    # Use SSOT factory function
                    context = await create_isolated_execution_context(
                        user_id=user_id,
                        request_id=f"req_{user_index:03d}_{uuid.uuid4().hex[:8]}",
                        thread_id=thread_id,
                        run_id=run_id,
                        validate_user=False  # Skip user validation for speed
                    )
                
                # Track creation and check for issues
                creation_metadata = {
                    "user_index": user_index,
                    "creation_method": ["factory", "from_request", "isolated_factory"][user_index % 3],
                    "creation_time": time.time()
                }
                
                self._track_context_creation(context, creation_metadata)
                self._check_id_collisions(context)
                
                # Verify isolation
                isolation_valid = self._verify_context_isolation(context)
                
                return {
                    "user_index": user_index,
                    "context": context,
                    "success": True,
                    "isolation_valid": isolation_valid
                }
                
            except Exception as e:
                logger.error(f"Context creation failed for user {user_index}: {e}")
                return {
                    "user_index": user_index,
                    "context": None,
                    "success": False,
                    "error": str(e)
                }
        
        # Create 100 contexts concurrently
        start_time = time.time()
        results = await asyncio.gather(
            *[create_user_context(i) for i in range(100)],
            return_exceptions=True
        )
        creation_time = time.time() - start_time
        
        # Analyze results
        successful_creations = len([r for r in results if isinstance(r, dict) and r.get("success")])
        failed_creations = len([r for r in results if not isinstance(r, dict) or not r.get("success")])
        isolation_valid_count = len([r for r in results if isinstance(r, dict) and r.get("isolation_valid")])
        
        # Check for race condition indicators
        assert len(self.id_collisions) == 0, (
            f"ID collisions detected: {self.id_collisions}. "
            f"This indicates race conditions in ID generation or context management."
        )
        
        assert len(self.isolation_violations) == 0, (
            f"Isolation violations detected: {self.isolation_violations}. "
            f"This indicates race conditions in context isolation."
        )
        
        # Verify all contexts were created successfully
        assert successful_creations == 100, (
            f"Expected 100 successful context creations, got {successful_creations}. "
            f"Failed: {failed_creations}. Race conditions may have caused creation failures."
        )
        
        # Verify all contexts have valid isolation
        assert isolation_valid_count == successful_creations, (
            f"Expected {successful_creations} contexts with valid isolation, got {isolation_valid_count}. "
            f"Race conditions may have violated context isolation."
        )
        
        # Verify reasonable creation time (should be concurrent)
        assert creation_time < 10.0, (
            f"Context creation took {creation_time:.2f}s, expected < 10s. "
            f"This may indicate serialization instead of concurrent creation."
        )
        
        # Verify unique request IDs
        request_ids = [ctx.request_id for ctx in self.created_contexts]
        unique_request_ids = set(request_ids)
        assert len(request_ids) == len(unique_request_ids), (
            f"Duplicate request IDs detected: {len(request_ids)} total, {len(unique_request_ids)} unique. "
            f"This indicates race conditions in ID generation."
        )
        
        logger.info(
            f" PASS:  100 concurrent context creations completed successfully in {creation_time:.2f}s. "
            f"Success rate: {successful_creations}/100, Isolation valid: {isolation_valid_count}/100, "
            f"ID collisions: {len(self.id_collisions)}, Isolation violations: {len(self.isolation_violations)}"
        )
    
    @pytest.mark.unit
    @pytest.mark.race_conditions
    async def test_user_data_isolation_under_load(self):
        """Test user data isolation under concurrent load with overlapping users."""
        
        # Create contexts with intentionally overlapping user IDs
        async def create_contexts_for_user(user_id: str, context_count: int):
            """Create multiple contexts for the same user."""
            contexts = []
            
            for i in range(context_count):
                try:
                    # Use different creation methods to stress test isolation
                    if i % 2 == 0:
                        context = UserExecutionContext.from_request(
                            user_id=user_id,
                            thread_id=f"thread_{user_id}_{i}",
                            run_id=f"run_{user_id}_{i}_{uuid.uuid4().hex[:6]}",
                            agent_context={"user_specific_data": f"data_for_{user_id}_{i}"},
                            audit_metadata={"user_operation": f"operation_{i}"}
                        )
                    else:
                        context = await create_isolated_execution_context(
                            user_id=user_id,
                            request_id=f"req_{user_id}_{i}_{uuid.uuid4().hex[:6]}",
                            validate_user=False
                        )
                    
                    contexts.append(context)
                    self._track_context_creation(context, {"user_batch": user_id, "context_index": i})
                    
                except Exception as e:
                    logger.error(f"Failed to create context for user {user_id}, index {i}: {e}")
            
            return contexts
        
        # Create 5 users with 10 contexts each = 50 total contexts
        user_ids = [f"isolation_user_{i:02d}" for i in range(5)]
        
        # Create all contexts concurrently
        all_user_contexts = await asyncio.gather(
            *[create_contexts_for_user(user_id, 10) for user_id in user_ids],
            return_exceptions=True
        )
        
        # Flatten results
        all_contexts = []
        for user_contexts in all_user_contexts:
            if isinstance(user_contexts, list):
                all_contexts.extend(user_contexts)
        
        # Verify isolation between users
        contexts_by_user = defaultdict(list)
        for context in all_contexts:
            contexts_by_user[context.user_id].append(context)
        
        # Check that each user has exactly 10 contexts
        for user_id in user_ids:
            user_contexts = contexts_by_user[user_id]
            assert len(user_contexts) == 10, (
                f"User {user_id} should have 10 contexts, got {len(user_contexts)}. "
                f"Race conditions may have caused context loss or corruption."
            )
            
            # Verify all contexts for this user have unique request IDs
            request_ids = [ctx.request_id for ctx in user_contexts]
            unique_request_ids = set(request_ids)
            assert len(request_ids) == len(unique_request_ids), (
                f"User {user_id} has duplicate request IDs: {len(request_ids)} total, "
                f"{len(unique_request_ids)} unique. Race condition in ID generation."
            )
            
            # Verify no shared objects between contexts
            for i, ctx1 in enumerate(user_contexts):
                for j, ctx2 in enumerate(user_contexts):
                    if i != j:
                        assert id(ctx1.agent_context) != id(ctx2.agent_context), (
                            f"User {user_id} contexts {i} and {j} share agent_context object. "
                            f"Isolation violation - race condition in context creation."
                        )
                        assert id(ctx1.audit_metadata) != id(ctx2.audit_metadata), (
                            f"User {user_id} contexts {i} and {j} share audit_metadata object. "
                            f"Isolation violation - race condition in context creation."
                        )
        
        # Cross-user isolation verification
        for user1_id, user1_contexts in contexts_by_user.items():
            for user2_id, user2_contexts in contexts_by_user.items():
                if user1_id != user2_id:
                    # Verify no request ID collisions between users
                    user1_request_ids = set(ctx.request_id for ctx in user1_contexts)
                    user2_request_ids = set(ctx.request_id for ctx in user2_contexts)
                    
                    collisions = user1_request_ids & user2_request_ids
                    assert len(collisions) == 0, (
                        f"Request ID collisions between users {user1_id} and {user2_id}: {collisions}. "
                        f"Race condition in cross-user ID generation."
                    )
        
        # Check for isolation violations
        assert len(self.isolation_violations) == 0, (
            f"Isolation violations detected: {self.isolation_violations}"
        )
        
        assert len(self.id_collisions) == 0, (
            f"ID collisions detected: {self.id_collisions}"
        )
        
        logger.info(
            f" PASS:  User data isolation test passed: 5 users  x  10 contexts = {len(all_contexts)} total contexts. "
            f"All contexts properly isolated with unique IDs."
        )
    
    @pytest.mark.unit
    @pytest.mark.race_conditions
    async def test_context_factory_concurrent_access(self):
        """Test context factory for race conditions under concurrent access."""
        factory = UserContextFactory()
        
        async def factory_stress_test(batch_index: int):
            """Stress test context factory with concurrent access."""
            contexts_created = []
            
            try:
                for i in range(5):  # 5 contexts per batch
                    context_index = batch_index * 5 + i
                    
                    # Alternate between factory methods
                    if i % 2 == 0:
                        context = factory.create_context(
                            user_id=f"factory_user_{context_index}",
                            thread_id=f"factory_thread_{context_index}",
                            run_id=f"factory_run_{context_index}"
                        )
                    else:
                        # Create with session
                        base_context = factory.create_context(
                            user_id=f"factory_user_{context_index}",
                            thread_id=f"factory_thread_{context_index}",
                            run_id=f"factory_run_{context_index}"
                        )
                        # Simulate adding session (using None as mock)
                        context = base_context.with_db_session(None)
                    
                    contexts_created.append(context)
                    
                    # Small delay to create race condition opportunity
                    await asyncio.sleep(0.0001)
                
                return {
                    "batch_index": batch_index,
                    "contexts": contexts_created,
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Factory stress test failed for batch {batch_index}: {e}")
                return {
                    "batch_index": batch_index,
                    "contexts": contexts_created,
                    "success": False,
                    "error": str(e)
                }
        
        # Run 20 concurrent batches (100 total contexts)
        batch_results = await asyncio.gather(
            *[factory_stress_test(i) for i in range(20)],
            return_exceptions=True
        )
        
        # Collect all contexts
        all_factory_contexts = []
        successful_batches = 0
        
        for result in batch_results:
            if isinstance(result, dict) and result.get("success"):
                successful_batches += 1
                all_factory_contexts.extend(result["contexts"])
        
        # Verify results
        assert successful_batches == 20, (
            f"Expected 20 successful factory batches, got {successful_batches}. "
            f"Race conditions may have caused factory failures."
        )
        
        assert len(all_factory_contexts) == 100, (
            f"Expected 100 factory-created contexts, got {len(all_factory_contexts)}. "
            f"Race conditions may have caused context loss."
        )
        
        # Check for duplicate request IDs (race condition indicator)
        request_ids = [ctx.request_id for ctx in all_factory_contexts]
        unique_request_ids = set(request_ids)
        
        assert len(request_ids) == len(unique_request_ids), (
            f"Duplicate request IDs in factory-created contexts: "
            f"{len(request_ids)} total, {len(unique_request_ids)} unique. "
            f"Race condition in factory ID generation."
        )
        
        # Verify all contexts pass isolation check
        for ctx in all_factory_contexts:
            try:
                ctx.verify_isolation()
            except ContextIsolationError as e:
                raise AssertionError(f"Factory-created context failed isolation check: {e}")
        
        logger.info(
            f" PASS:  Context factory concurrent access test passed: "
            f"{successful_batches}/20 successful batches, {len(all_factory_contexts)} total contexts, "
            f"all with unique IDs and proper isolation."
        )
    
    @pytest.mark.unit  
    @pytest.mark.race_conditions
    async def test_memory_leak_detection_under_load(self):
        """Test for memory leaks in context creation under concurrent load."""
        initial_context_count = len(self.created_contexts)
        
        async def create_and_cleanup_contexts(batch_size: int):
            """Create contexts and let them go out of scope."""
            contexts = []
            
            for i in range(batch_size):
                context = UserExecutionContext.from_request(
                    user_id=f"memory_test_user_{i}",
                    thread_id=f"memory_test_thread_{i}",
                    run_id=f"memory_test_run_{i}",
                    agent_context={"batch_data": [1, 2, 3, 4, 5]},  # Some data to allocate
                    audit_metadata={"test_type": "memory_leak_detection"}
                )
                contexts.append(context)
                
                # Add weak reference for tracking
                self.memory_refs.append(weakref.ref(context))
            
            # Use contexts in managed context to simulate real usage
            for context in contexts:
                async with managed_user_context(context, cleanup_db_session=False) as managed_ctx:
                    # Simulate some work
                    assert managed_ctx.user_id.startswith("memory_test_user_")
                    await asyncio.sleep(0.0001)
            
            # Contexts should go out of scope here
            return len(contexts)
        
        # Create contexts in multiple batches
        batch_sizes = [10, 15, 20, 10]  # 55 total contexts
        
        created_counts = await asyncio.gather(
            *[create_and_cleanup_contexts(size) for size in batch_sizes]
        )
        
        total_created = sum(created_counts)
        assert total_created == 55, f"Expected 55 contexts created, got {total_created}"
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow cleanup to complete
        gc.collect()
        
        # Check how many contexts are still referenced
        live_refs = [ref for ref in self.memory_refs if ref() is not None]
        
        # Allow some contexts to remain (from other tests), but not all
        max_allowed_live = initial_context_count + 10  # Allow some leeway
        
        assert len(live_refs) <= max_allowed_live, (
            f"Memory leak detected: {len(live_refs)} contexts still live after cleanup. "
            f"Expected <= {max_allowed_live}. Race conditions may be preventing proper cleanup."
        )
        
        logger.info(
            f" PASS:  Memory leak detection test passed: "
            f"{total_created} contexts created, {len(live_refs)} still live "
            f"(within acceptable range of <= {max_allowed_live})"
        )
    
    @pytest.mark.unit
    @pytest.mark.race_conditions
    async def test_id_generation_collision_detection(self):
        """Test ID generation for collisions under concurrent load."""
        id_generator = UnifiedIdGenerator()
        generated_ids = {
            "user_ids": set(),
            "thread_ids": set(), 
            "run_ids": set(),
            "request_ids": set(),
            "websocket_ids": set()
        }
        
        async def generate_ids_concurrently(batch_index: int):
            """Generate various types of IDs concurrently."""
            batch_ids = {
                "user_ids": [],
                "thread_ids": [],
                "run_ids": [],
                "request_ids": [],
                "websocket_ids": []
            }
            
            try:
                for i in range(10):  # 10 IDs per batch
                    # Generate different types of IDs
                    user_id = f"race_user_{batch_index}_{i}"
                    thread_id, run_id, request_id = id_generator.generate_user_context_ids(
                        user_id=user_id,
                        operation=f"batch_{batch_index}_op_{i}"
                    )
                    websocket_id = id_generator.generate_websocket_client_id(user_id)
                    
                    batch_ids["user_ids"].append(user_id)
                    batch_ids["thread_ids"].append(thread_id)
                    batch_ids["run_ids"].append(run_id)
                    batch_ids["request_ids"].append(request_id)
                    batch_ids["websocket_ids"].append(websocket_id)
                
                return {"batch_index": batch_index, "ids": batch_ids, "success": True}
                
            except Exception as e:
                logger.error(f"ID generation failed for batch {batch_index}: {e}")
                return {"batch_index": batch_index, "ids": batch_ids, "success": False, "error": str(e)}
        
        # Generate IDs in 15 concurrent batches (150 IDs of each type)
        results = await asyncio.gather(
            *[generate_ids_concurrently(i) for i in range(15)],
            return_exceptions=True
        )
        
        # Collect all generated IDs
        successful_batches = 0
        for result in results:
            if isinstance(result, dict) and result.get("success"):
                successful_batches += 1
                batch_ids = result["ids"]
                
                for id_type, ids in batch_ids.items():
                    generated_ids[id_type].update(ids)
        
        # Verify no collisions occurred
        for id_type, ids in generated_ids.items():
            expected_count = successful_batches * 10
            actual_count = len(ids)
            
            assert actual_count == expected_count, (
                f"ID collision detected in {id_type}: expected {expected_count} unique IDs, "
                f"got {actual_count}. Race condition in ID generation."
            )
        
        assert successful_batches == 15, (
            f"Expected 15 successful ID generation batches, got {successful_batches}. "
            f"Race conditions may have caused generation failures."
        )
        
        logger.info(
            f" PASS:  ID generation collision test passed: "
            f"{successful_batches}/15 successful batches, "
            f"all {len(generated_ids['request_ids'])} IDs unique across all types."
        )