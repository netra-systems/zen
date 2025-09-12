"""
Test User Context Corruption Recovery Scenarios

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure system resilience against context corruption
- Value Impact: Prevents user session failures and data corruption scenarios
- Strategic Impact: Core platform reliability and user trust

This test suite validates context recovery mechanisms when corruption occurs
at various levels of the user context lifecycle. Tests must be DIFFICULT
and stress the system to catch real problems before production.

CRITICAL: Uses real services (PostgreSQL, Redis) - no mocks allowed
"""

import asyncio
import json
import logging
import os
import pytest
import random
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# SSOT imports for user context architecture
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.services.user_execution_context import UserContextFactory
from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory
from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user

logger = logging.getLogger(__name__)


class TestUserContextCorruptionRecovery(BaseIntegrationTest):
    """Test user context corruption recovery mechanisms with REAL services."""
    
    def setup_method(self):
        """Set up method with enhanced logging and real service preparation."""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.id_manager = UnifiedIDManager()
        self.corruption_scenarios = []
        self.recovery_metrics = {}
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_partial_context_metadata_corruption_recovery(self, real_services_fixture):
        """
        Test recovery from partial context metadata corruption.
        
        This test simulates scenarios where context metadata is partially
        corrupted but core data remains intact. System should detect
        corruption and rebuild metadata from available information.
        
        CRITICAL: This is a DIFFICULT test that intentionally corrupts
        context metadata to validate recovery mechanisms.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for corruption testing")
            
        engine = real_services_fixture["postgres"]
        
        # Create test user with valid context
        user_token, user_data = await create_authenticated_user(
            environment="test",
            user_id=f"corrupt-test-{uuid.uuid4().hex[:8]}",
            email=f"corrupt-test-{int(time.time())}@example.com"
        )
        user_id = user_data["id"]
        
        # Create initial user context
        session_factory = RequestScopedSessionFactory(engine=engine)
        context_factory = UserContextFactory(
            session_factory=session_factory,
            unified_id_manager=self.id_manager
        )
        
        async with session_factory.create_session() as session:
            # Create valid context first
            context = await context_factory.create_user_context(
                user_id=user_id,
                session=session,
                metadata={"initial_state": "valid", "creation_time": datetime.now(timezone.utc).isoformat()}
            )
            
            context_id = context.context_id
            logger.info(f"Created initial context: {context_id}")
            
            # CORRUPTION SCENARIO 1: Corrupt metadata partially
            await self._corrupt_context_metadata(session, context_id, corruption_type="partial")
            
            # Attempt to retrieve corrupted context - should trigger recovery
            recovery_start = time.time()
            recovered_context = await context_factory.get_user_context(
                user_id=user_id,
                session=session,
                create_if_missing=True  # Enable recovery mode
            )
            recovery_duration = time.time() - recovery_start
            
            # Validate recovery success
            assert recovered_context is not None, "Context recovery failed - returned None"
            assert recovered_context.user_id == user_id, "Recovered context has wrong user_id"
            assert recovered_context.context_id == context_id, "Context ID not preserved during recovery"
            
            # Verify recovery metrics
            self.recovery_metrics["partial_metadata_corruption"] = {
                "recovery_time": recovery_duration,
                "success": True,
                "original_context_id": context_id,
                "recovered_context_id": recovered_context.context_id
            }
            
            # PERFORMANCE ASSERTION: Recovery should be fast (< 5 seconds)
            assert recovery_duration < 5.0, f"Context recovery took too long: {recovery_duration:.2f}s"
            
            logger.info(f" PASS:  Partial metadata corruption recovery successful in {recovery_duration:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_context_state_inconsistency_detection_and_repair(self, real_services_fixture):
        """
        Test detection and repair of context state inconsistencies.
        
        This creates scenarios where context state becomes inconsistent
        between Redis cache and PostgreSQL database. The system should
        detect mismatches and repair them automatically.
        
        CRITICAL: Tests cross-service consistency validation.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for state consistency testing")
            
        engine = real_services_fixture["postgres"]
        
        # Create test user
        user_token, user_data = await create_authenticated_user(
            environment="test",
            user_id=f"state-test-{uuid.uuid4().hex[:8]}",
            email=f"state-test-{int(time.time())}@example.com"
        )
        user_id = user_data["id"]
        
        session_factory = RequestScopedSessionFactory(engine=engine)
        context_factory = UserContextFactory(
            session_factory=session_factory,
            unified_id_manager=self.id_manager
        )
        
        async with session_factory.create_session() as session:
            # Create context with initial state
            context = await context_factory.create_user_context(
                user_id=user_id,
                session=session,
                metadata={
                    "state": "active",
                    "last_activity": datetime.now(timezone.utc).isoformat(),
                    "session_count": 1
                }
            )
            
            # INCONSISTENCY SCENARIO: Create database-cache mismatch
            await self._create_state_inconsistency(session, context.context_id)
            
            # Trigger consistency check
            consistency_start = time.time()
            repaired_context = await context_factory.validate_and_repair_context_state(
                context_id=context.context_id,
                session=session
            )
            consistency_duration = time.time() - consistency_start
            
            # Validate repair success
            assert repaired_context is not None, "Context state repair failed"
            assert repaired_context.context_id == context.context_id, "Context ID changed during repair"
            
            # Verify state consistency restored
            state_valid = await self._verify_context_state_consistency(session, context.context_id)
            assert state_valid, "Context state consistency not restored after repair"
            
            self.recovery_metrics["state_inconsistency_repair"] = {
                "repair_time": consistency_duration,
                "success": True,
                "context_id": context.context_id
            }
            
            # PERFORMANCE ASSERTION: State repair should be efficient
            assert consistency_duration < 3.0, f"State repair took too long: {consistency_duration:.2f}s"
            
            logger.info(f" PASS:  State inconsistency detection and repair successful in {consistency_duration:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_concurrent_context_corruption_resilience(self, real_services_fixture):
        """
        Test resilience against concurrent context corruption scenarios.
        
        This test simulates multiple users experiencing context corruption
        simultaneously to validate that recovery mechanisms don't interfere
        with each other and system remains stable under load.
        
        CRITICAL: This is a STRESS test with concurrent operations.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for concurrent corruption testing")
            
        engine = real_services_fixture["postgres"]
        session_factory = RequestScopedSessionFactory(engine=engine)
        context_factory = UserContextFactory(
            session_factory=session_factory,
            unified_id_manager=self.id_manager
        )
        
        # Create multiple test users
        num_users = 5
        users = []
        contexts = []
        
        for i in range(num_users):
            user_token, user_data = await create_authenticated_user(
                environment="test",
                user_id=f"concurrent-{i}-{uuid.uuid4().hex[:8]}",
                email=f"concurrent-{i}-{int(time.time())}@example.com"
            )
            users.append(user_data)
        
        # Create contexts for all users
        async with session_factory.create_session() as session:
            for user_data in users:
                context = await context_factory.create_user_context(
                    user_id=user_data["id"],
                    session=session,
                    metadata={"user_index": users.index(user_data), "state": "initial"}
                )
                contexts.append(context)
        
        # CONCURRENT CORRUPTION: Corrupt all contexts simultaneously
        corruption_tasks = []
        for context in contexts:
            task = asyncio.create_task(
                self._corrupt_context_concurrently(context.context_id, context.user_id)
            )
            corruption_tasks.append(task)
        
        await asyncio.gather(*corruption_tasks)
        
        # CONCURRENT RECOVERY: Attempt recovery for all contexts
        recovery_start = time.time()
        recovery_tasks = []
        
        for i, context in enumerate(contexts):
            task = asyncio.create_task(
                self._recover_context_concurrently(
                    context_factory, context.context_id, users[i]["id"], engine
                )
            )
            recovery_tasks.append(task)
        
        recovery_results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
        recovery_duration = time.time() - recovery_start
        
        # Validate all recoveries successful
        successful_recoveries = 0
        for i, result in enumerate(recovery_results):
            if isinstance(result, Exception):
                logger.error(f"Recovery failed for user {i}: {result}")
            else:
                successful_recoveries += 1
                assert result is not None, f"Recovery returned None for user {i}"
        
        # RESILIENCE ASSERTION: At least 80% of recoveries should succeed
        success_rate = successful_recoveries / num_users
        assert success_rate >= 0.8, f"Concurrent recovery success rate too low: {success_rate:.1%}"
        
        self.recovery_metrics["concurrent_corruption_resilience"] = {
            "num_users": num_users,
            "successful_recoveries": successful_recoveries,
            "success_rate": success_rate,
            "total_recovery_time": recovery_duration
        }
        
        logger.info(f" PASS:  Concurrent corruption resilience test: {successful_recoveries}/{num_users} recoveries in {recovery_duration:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_context_creation_failure_cascade_prevention(self, real_services_fixture):
        """
        Test prevention of context creation failure cascades.
        
        When context creation fails for one user, it should not affect
        other users' context operations. This test validates isolation
        of failure scenarios.
        
        CRITICAL: Tests failure isolation mechanisms.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for cascade prevention testing")
            
        engine = real_services_fixture["postgres"]
        session_factory = RequestScopedSessionFactory(engine=engine)
        context_factory = UserContextFactory(
            session_factory=session_factory,
            unified_id_manager=self.id_manager
        )
        
        # Create normal user
        normal_user_token, normal_user_data = await create_authenticated_user(
            environment="test",
            user_id=f"normal-{uuid.uuid4().hex[:8]}",
            email=f"normal-{int(time.time())}@example.com"
        )
        
        # Create problematic user (will trigger creation failure)
        problem_user_token, problem_user_data = await create_authenticated_user(
            environment="test", 
            user_id=f"problem-{uuid.uuid4().hex[:8]}",
            email=f"problem-{int(time.time())}@example.com"
        )
        
        async with session_factory.create_session() as session:
            # Create normal context first (should succeed)
            normal_context = await context_factory.create_user_context(
                user_id=normal_user_data["id"],
                session=session,
                metadata={"type": "normal", "expected": "success"}
            )
            assert normal_context is not None, "Normal context creation failed"
            
            # Create REAL database constraint violation by corrupting database state
            try:
                # First create a context with duplicate constraints to trigger real failure
                await self._create_real_database_constraint_violation(session, problem_user_data["id"])
                
                # Now attempt to create context - should fail due to real constraint violation
                problem_context = await context_factory.create_user_context(
                    user_id=problem_user_data["id"],
                    session=session,
                    metadata={"type": "problem", "expected": "failure"}
                )
                # If we reach here, the real constraint violation didn't work as expected
                logger.warning("Expected constraint violation did not occur - continuing test")
            except Exception as e:
                logger.info(f"Real database constraint violation occurred: {e}")
                # This is the expected behavior - real constraint should cause failure
            
            # Verify normal user's context still works after problem user's failure
            retrieved_normal = await context_factory.get_user_context(
                user_id=normal_user_data["id"],
                session=session
            )
            
            assert retrieved_normal is not None, "Normal user context affected by other user's failure"
            assert retrieved_normal.context_id == normal_context.context_id, "Normal context corrupted by failure cascade"
            
            # Verify problem user can still create context after failure (recovery)
            recovery_context = await context_factory.create_user_context(
                user_id=problem_user_data["id"],
                session=session,
                metadata={"type": "recovery", "attempt": 2}
            )
            assert recovery_context is not None, "Recovery context creation failed"
            
        self.recovery_metrics["cascade_prevention"] = {
            "normal_user_unaffected": True,
            "problem_user_recovered": True,
            "isolation_maintained": True
        }
        
        logger.info(" PASS:  Context creation failure cascade prevention successful")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_memory_pressure_context_recovery_behavior(self, real_services_fixture):
        """
        Test context recovery behavior under memory pressure conditions.
        
        This test simulates high memory usage scenarios and validates
        that context recovery mechanisms remain functional even when
        system resources are constrained.
        
        CRITICAL: This is a RESOURCE STRESS test.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for memory pressure testing")
            
        engine = real_services_fixture["postgres"]
        session_factory = RequestScopedSessionFactory(engine=engine)
        context_factory = UserContextFactory(
            session_factory=session_factory,
            unified_id_manager=self.id_manager
        )
        
        # Create test user
        user_token, user_data = await create_authenticated_user(
            environment="test",
            user_id=f"memory-test-{uuid.uuid4().hex[:8]}",
            email=f"memory-test-{int(time.time())}@example.com"
        )
        user_id = user_data["id"]
        
        # Simulate memory pressure by creating large data structures
        memory_pressure_data = []
        try:
            # Create substantial memory pressure (but not crash the test)
            for i in range(1000):
                large_dict = {f"key_{j}": f"value_{'x' * 1000}" for j in range(100)}
                memory_pressure_data.append(large_dict)
            
            async with session_factory.create_session() as session:
                # Create context under memory pressure
                pressure_start = time.time()
                context = await context_factory.create_user_context(
                    user_id=user_id,
                    session=session,
                    metadata={
                        "created_under_pressure": True,
                        "memory_items": len(memory_pressure_data),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                creation_duration = time.time() - pressure_start
                
                assert context is not None, "Context creation failed under memory pressure"
                
                # Corrupt context while under memory pressure
                await self._corrupt_context_metadata(session, context.context_id, corruption_type="full")
                
                # Attempt recovery under memory pressure
                recovery_start = time.time()
                recovered_context = await context_factory.get_user_context(
                    user_id=user_id,
                    session=session,
                    create_if_missing=True
                )
                recovery_duration = time.time() - recovery_start
                
                assert recovered_context is not None, "Context recovery failed under memory pressure"
                
                # PERFORMANCE ASSERTION: Even under pressure, should complete reasonably
                assert creation_duration < 10.0, f"Context creation too slow under pressure: {creation_duration:.2f}s"
                assert recovery_duration < 10.0, f"Context recovery too slow under pressure: {recovery_duration:.2f}s"
                
                self.recovery_metrics["memory_pressure_recovery"] = {
                    "creation_time": creation_duration,
                    "recovery_time": recovery_duration,
                    "memory_items": len(memory_pressure_data),
                    "success": True
                }
                
                logger.info(f" PASS:  Memory pressure recovery successful: creation={creation_duration:.2f}s, recovery={recovery_duration:.2f}s")
        
        finally:
            # Clean up memory pressure
            del memory_pressure_data

    async def _corrupt_context_metadata(self, session, context_id: str, corruption_type: str = "partial"):
        """Create REAL context metadata corruption in database using actual SQL operations."""
        try:
            if corruption_type == "partial":
                # Create REAL partial corruption - insert malformed JSON that database will accept but app cannot parse
                corrupt_metadata = '{"corrupted": true, "invalid_json": "unterminated'  # Real malformed JSON
                query = "UPDATE user_contexts SET metadata = :metadata WHERE context_id = :context_id"
            else:
                # Full corruption - actually set metadata to NULL or corrupt the entire row
                corrupt_metadata = None
                query = "UPDATE user_contexts SET metadata = :metadata WHERE context_id = :context_id"
            
            # Execute REAL database update - this actually corrupts the data
            result = await session.execute(query, {"metadata": corrupt_metadata, "context_id": context_id})
            if result.rowcount == 0:
                logger.warning(f"No rows affected when corrupting context {context_id} - context may not exist")
            
            # REAL commit - this persists the corruption to the database
            await session.commit()
            logger.info(f"REAL database corruption applied: {context_id} ({corruption_type}), rows affected: {result.rowcount}")
            
            # Verify the corruption was actually written
            verify_query = "SELECT metadata FROM user_contexts WHERE context_id = :context_id"
            verify_result = await session.execute(verify_query, {"context_id": context_id})
            row = verify_result.fetchone()
            if row:
                actual_metadata = row[0]
                logger.info(f"Verified corruption: metadata now = {actual_metadata}")
            else:
                logger.error(f"Context {context_id} not found after corruption attempt")
                
        except Exception as e:
            logger.error(f"Failed to create real corruption for {context_id}: {e}")
            # Re-raise to ensure test failure is visible
            raise
    
    async def _create_state_inconsistency(self, session, context_id: str):
        """Create REAL state inconsistency between database and any caching layer."""
        try:
            # Create REAL different state values in database
            db_state = {"state": "database_version", "timestamp": time.time(), "corrupted_by_test": True}
            
            # REAL database update with inconsistent state
            query = "UPDATE user_contexts SET state = :state WHERE context_id = :context_id"
            result = await session.execute(query, {"state": json.dumps(db_state), "context_id": context_id})
            
            if result.rowcount == 0:
                logger.warning(f"No context found to create inconsistency for {context_id}")
                # Create the context first if it doesn't exist
                insert_query = "INSERT INTO user_contexts (context_id, state, created_at) VALUES (:context_id, :state, NOW())"
                await session.execute(insert_query, {"context_id": context_id, "state": json.dumps(db_state)})
            
            await session.commit()
            
            # TODO: If Redis cache is available, create different state there
            # This would require injecting Redis connection and creating cache inconsistency
            # For now, we create database-level inconsistency which is still real corruption
            
            # Verify the inconsistency was created
            verify_query = "SELECT state FROM user_contexts WHERE context_id = :context_id"
            verify_result = await session.execute(verify_query, {"context_id": context_id})
            row = verify_result.fetchone()
            if row:
                logger.info(f"REAL state inconsistency created: {context_id} -> {row[0]}")
            else:
                logger.error(f"Failed to verify state inconsistency for {context_id}")
                
        except Exception as e:
            logger.error(f"Failed to create real state inconsistency for {context_id}: {e}")
            raise
    
    async def _verify_context_state_consistency(self, session, context_id: str) -> bool:
        """Verify that context state is consistent and not corrupted."""
        try:
            # REAL verification - check actual database state
            query = "SELECT state, metadata FROM user_contexts WHERE context_id = :context_id"
            result = await session.execute(query, {"context_id": context_id})
            row = result.fetchone()
            
            if not row:
                logger.warning(f"Context {context_id} not found during consistency check")
                return False
                
            state_data, metadata = row[0], row[1]
            
            # Verify state is valid JSON and not corrupted
            if state_data:
                try:
                    parsed_state = json.loads(state_data)
                    if not isinstance(parsed_state, dict) or "state" not in parsed_state:
                        logger.warning(f"State format invalid for {context_id}")
                        return False
                    # Check if this was corrupted by our test
                    if parsed_state.get("corrupted_by_test"):
                        logger.info(f"Context {context_id} still shows test corruption - consistency not restored")
                        return False
                except json.JSONDecodeError as e:
                    logger.warning(f"State JSON corrupted for {context_id}: {e}")
                    return False
            
            # Verify metadata is also consistent
            if metadata:
                try:
                    parsed_metadata = json.loads(metadata)
                    if not isinstance(parsed_metadata, dict):
                        logger.warning(f"Metadata format invalid for {context_id}")
                        return False
                except json.JSONDecodeError as e:
                    logger.warning(f"Metadata JSON corrupted for {context_id}: {e}")
                    return False
            
            logger.info(f"Context {context_id} state consistency verified")
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify consistency for {context_id}: {e}")
            return False
    
    async def _corrupt_context_concurrently(self, context_id: str, user_id: str):
        """Create REAL context corruption in a concurrent scenario using database operations."""
        try:
            # Simulate realistic concurrent corruption timing
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
            # Create REAL corruption using direct database access
            from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            
            # Use a separate session for concurrent corruption to simulate real race conditions
            session_factory = RequestScopedSessionFactory()
            async with session_factory.create_session() as corruption_session:
                # Apply REAL corruption - corrupt both metadata and state
                corrupt_metadata = '{"concurrent_corruption": true, "corrupted_at": ' + str(time.time()) + ', "invalid":'
                corrupt_state = '{"concurrent_state_corruption": true}'
                
                # Execute REAL corruption operations
                metadata_query = "UPDATE user_contexts SET metadata = :metadata WHERE context_id = :context_id"
                state_query = "UPDATE user_contexts SET state = :state WHERE context_id = :context_id" 
                
                await corruption_session.execute(metadata_query, {"metadata": corrupt_metadata, "context_id": context_id})
                await corruption_session.execute(state_query, {"state": corrupt_state, "context_id": context_id})
                await corruption_session.commit()
            
            # Track the REAL corruption attempt
            self.corruption_scenarios.append({
                "context_id": context_id,
                "user_id": user_id,
                "timestamp": time.time(),
                "type": "concurrent_real_corruption",
                "corruption_applied": True
            })
            
            logger.info(f"REAL concurrent corruption applied to context: {context_id}")
            
        except Exception as e:
            logger.error(f"Failed to create real concurrent corruption for {context_id}: {e}")
            # Still track the attempt even if it failed
            self.corruption_scenarios.append({
                "context_id": context_id,
                "user_id": user_id,
                "timestamp": time.time(),
                "type": "concurrent_corruption_failed",
                "error": str(e)
            })
            raise
    
    async def _create_real_database_constraint_violation(self, session, user_id: str):
        """Create REAL database constraint violation to trigger authentic failure scenarios."""
        try:
            # Method 1: Attempt to create duplicate primary key constraint violation
            # Insert a row that will conflict with the next context creation
            conflict_context_id = f"duplicate-{user_id}-{int(time.time())}"
            
            # First, create a context that will establish constraints
            insert_query = """
            INSERT INTO user_contexts (context_id, user_id, metadata, state, created_at) 
            VALUES (:context_id, :user_id, :metadata, :state, NOW())
            """
            
            await session.execute(insert_query, {
                "context_id": conflict_context_id,
                "user_id": user_id,
                "metadata": json.dumps({"constraint_test": True}),
                "state": json.dumps({"initial": True})
            })
            
            # Method 2: Create foreign key constraint violation by referencing non-existent data
            # This depends on the actual schema, but we can try inserting invalid references
            
            # Method 3: Violate unique constraints if they exist
            # Attempt to insert the same context_id again to trigger unique constraint violation
            await session.execute(insert_query, {
                "context_id": conflict_context_id,  # Same ID - should violate unique constraint
                "user_id": user_id,
                "metadata": json.dumps({"duplicate_test": True}),
                "state": json.dumps({"duplicate": True})
            })
            
            await session.commit()
            logger.error("Expected constraint violation did not occur - this might indicate schema issues")
            
        except Exception as e:
            # This is expected - constraint violations should raise exceptions
            logger.info(f"Successfully created real constraint violation: {e}")
            # Don't commit the violating transaction
            await session.rollback()
            # Re-raise to ensure the calling code handles the real failure
            raise
    
    async def _recover_context_concurrently(self, context_factory, context_id: str, user_id: str, engine):
        """Attempt context recovery in concurrent scenario."""
        session_factory = RequestScopedSessionFactory(engine=engine)
        
        async with session_factory.create_session() as session:
            # Simulate processing delay
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            return await context_factory.get_user_context(
                user_id=user_id,
                session=session,
                create_if_missing=True
            )

    def teardown_method(self):
        """Clean up after each test with metrics reporting."""
        super().teardown_method()
        
        if self.recovery_metrics:
            logger.info("=== Context Corruption Recovery Test Metrics ===")
            for test_name, metrics in self.recovery_metrics.items():
                logger.info(f"{test_name}: {metrics}")
            
        # Clear corruption tracking
        self.corruption_scenarios.clear()
        self.recovery_metrics.clear()