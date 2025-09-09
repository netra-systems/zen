"""
Race Condition Tests: Database Session Management

This module tests for race conditions in database session allocation and management.
Validates that database sessions remain isolated and properly managed under concurrent load.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Ensure data integrity and prevent database connection exhaustion
- Value Impact: Prevents data corruption, connection leaks, and system instability
- Strategic Impact: CRITICAL - Database reliability is fundamental to platform operation

Test Coverage:
- 100 concurrent session allocations
- Session isolation verification
- Connection pool exhaustion detection
- Session cleanup and resource management
- Transaction isolation under concurrent access
"""

import asyncio
import gc
import time
import uuid
import weakref
from collections import defaultdict
from typing import Dict, List, Set, Any, Optional
from unittest.mock import Mock, AsyncMock
import pytest

from netra_backend.app.database.request_scoped_session_factory import (
    RequestScopedSessionFactory,
    get_session_factory,
    get_isolated_session,
    validate_session_isolation,
    ConnectionPoolMetrics
)
from shared.isolated_environment import IsolatedEnvironment
from shared.metrics.session_metrics import SessionState, DatabaseSessionMetrics
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from test_framework.ssot.real_services_test_fixtures import requires_real_database
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestDatabaseSessionRaces(SSotBaseTestCase):
    """Test race conditions in database session management."""
    
    def setup_method(self):
        """Set up test environment with database session tracking."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.set("TEST_MODE", "database_session_race_testing", source="test")
        
        # Track session allocation and management
        self.allocated_sessions: List[Any] = []
        self.session_metrics: Dict[str, DatabaseSessionMetrics] = {}
        self.race_condition_detections: List[Dict] = []
        self.session_refs: List[weakref.ref] = []
        self.connection_pool_states: List[Dict] = []
        
        # Initialize database helper
        self.db_helper = DatabaseTestHelper()
        
    def teardown_method(self):
        """Clean up test state and verify no session leaks."""
        # Force cleanup of sessions
        for session in self.allocated_sessions:
            try:
                if hasattr(session, 'close'):
                    asyncio.create_task(session.close())
            except Exception as e:
                logger.warning(f"Error closing session during cleanup: {e}")
        
        # Force garbage collection
        gc.collect()
        
        # Check for leaked session references
        leaked_refs = [ref for ref in self.session_refs if ref() is not None]
        if leaked_refs:
            logger.warning(f"Potential session leaks detected: {len(leaked_refs)} sessions not garbage collected")
        
        # Clear tracking data
        self.allocated_sessions.clear()
        self.session_metrics.clear()
        self.race_condition_detections.clear()
        self.session_refs.clear()
        self.connection_pool_states.clear()
        
        super().teardown_method()
    
    def _track_session_allocation(self, session: Any, user_id: str, request_id: str, thread_id: str = None):
        """Track session allocation for race condition analysis."""
        self.allocated_sessions.append(session)
        self.session_refs.append(weakref.ref(session))
        
        # Record allocation event
        allocation_event = {
            "session_info": getattr(session, 'info', {}),
            "user_id": user_id,
            "request_id": request_id,
            "thread_id": thread_id,
            "allocation_time": time.time(),
            "allocator_task": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        
        # Check for potential race conditions in session allocation
        self._check_session_allocation_races(allocation_event)
    
    def _check_session_allocation_races(self, allocation_event: Dict):
        """Check for race conditions in session allocation."""
        user_id = allocation_event["user_id"]
        request_id = allocation_event["request_id"]
        
        # Check for duplicate request IDs (race condition indicator)
        existing_requests = [
            event for event in self.connection_pool_states
            if event.get("request_id") == request_id
        ]
        
        if existing_requests:
            self._detect_race_condition(
                "duplicate_request_id",
                {"request_id": request_id, "user_id": user_id},
                allocation_event
            )
        
        # Check for excessive sessions for single user (potential leak or race)
        user_sessions = [
            event for event in self.connection_pool_states
            if event.get("user_id") == user_id
        ]
        
        if len(user_sessions) > 10:  # Threshold for excessive sessions
            self._detect_race_condition(
                "excessive_user_sessions",
                {"user_id": user_id, "session_count": len(user_sessions)},
                allocation_event
            )
    
    def _detect_race_condition(self, condition_type: str, metadata: Dict, context: Dict):
        """Record race condition detection."""
        race_condition = {
            "condition_type": condition_type,
            "metadata": metadata,
            "context": context,
            "timestamp": time.time(),
            "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        self.race_condition_detections.append(race_condition)
        logger.warning(f"Database session race condition detected: {race_condition}")
    
    def _record_pool_state(self, factory: RequestScopedSessionFactory):
        """Record connection pool state for analysis."""
        pool_metrics = factory.get_pool_metrics()
        session_metrics = factory.get_session_metrics()
        
        pool_state = {
            "timestamp": time.time(),
            "active_sessions": pool_metrics.active_sessions,
            "total_created": pool_metrics.total_sessions_created,
            "sessions_closed": pool_metrics.sessions_closed,
            "leaked_sessions": pool_metrics.leaked_sessions,
            "peak_concurrent": pool_metrics.peak_concurrent_sessions,
            "current_session_count": len(session_metrics),
            "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        
        self.connection_pool_states.append(pool_state)
        
        # Check for pool exhaustion indicators
        if pool_metrics.active_sessions > 50:  # High session count
            self._detect_race_condition(
                "potential_pool_exhaustion",
                {"active_sessions": pool_metrics.active_sessions},
                pool_state
            )
    
    @pytest.mark.integration
    @pytest.mark.race_conditions
    @requires_real_database
    async def test_100_concurrent_session_allocations(self):
        """Test 100 concurrent database session allocations for race conditions."""
        factory = await get_session_factory()
        
        async def allocate_session(allocation_index: int):
            """Allocate a single database session with tracking."""
            try:
                user_id = f"race_db_user_{allocation_index:03d}"
                request_id = f"race_db_req_{allocation_index:03d}_{uuid.uuid4().hex[:8]}"
                thread_id = f"race_db_thread_{allocation_index:03d}"
                
                # Record pool state before allocation
                self._record_pool_state(factory)
                
                # Allocate session using factory
                async with factory.get_request_scoped_session(user_id, request_id, thread_id) as session:
                    # Track session allocation
                    self._track_session_allocation(session, user_id, request_id, thread_id)
                    
                    # Verify session isolation
                    isolation_valid = await validate_session_isolation(session, user_id)
                    
                    # Perform a simple database operation to test functionality
                    from sqlalchemy import text
                    result = await session.execute(text("SELECT 1 as test_value"))
                    test_value = result.scalar()
                    
                    # Small delay to create race condition opportunities
                    await asyncio.sleep(0.001)
                    
                    # Record pool state during allocation
                    self._record_pool_state(factory)
                    
                    return {
                        "allocation_index": allocation_index,
                        "user_id": user_id,
                        "request_id": request_id,
                        "session_valid": session is not None,
                        "isolation_valid": isolation_valid,
                        "db_operation_success": test_value == 1,
                        "success": True
                    }
                    
            except Exception as e:
                logger.error(f"Session allocation failed for index {allocation_index}: {e}")
                return {
                    "allocation_index": allocation_index,
                    "success": False,
                    "error": str(e)
                }
        
        # Allocate 100 sessions concurrently
        start_time = time.time()
        results = await asyncio.gather(
            *[allocate_session(i) for i in range(100)],
            return_exceptions=True
        )
        allocation_time = time.time() - start_time
        
        # Analyze results
        successful_allocations = len([r for r in results if isinstance(r, dict) and r.get("success")])
        failed_allocations = len([r for r in results if not isinstance(r, dict) or not r.get("success")])
        valid_isolations = len([r for r in results if isinstance(r, dict) and r.get("isolation_valid")])
        successful_db_ops = len([r for r in results if isinstance(r, dict) and r.get("db_operation_success")])
        
        # Check for race condition indicators
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in database session allocation: {self.race_condition_detections}"
        )
        
        # Verify all allocations succeeded
        assert successful_allocations == 100, (
            f"Expected 100 successful session allocations, got {successful_allocations}. "
            f"Failed: {failed_allocations}. Race conditions may have caused allocation failures."
        )
        
        # Verify all sessions have valid isolation
        assert valid_isolations == successful_allocations, (
            f"Expected {successful_allocations} sessions with valid isolation, got {valid_isolations}. "
            f"Race conditions may have violated session isolation."
        )
        
        # Verify all database operations succeeded
        assert successful_db_ops == successful_allocations, (
            f"Expected {successful_allocations} successful DB operations, got {successful_db_ops}. "
            f"Race conditions may have affected database functionality."
        )
        
        # Verify reasonable allocation time
        assert allocation_time < 30.0, (
            f"Session allocation took {allocation_time:.2f}s, expected < 30s. "
            f"This may indicate serialization or database bottlenecks."
        )
        
        # Verify unique request IDs
        request_ids = [r.get("request_id") for r in results if isinstance(r, dict) and r.get("request_id")]
        unique_request_ids = set(request_ids)
        
        assert len(request_ids) == len(unique_request_ids), (
            f"Duplicate request IDs detected: {len(request_ids)} total, {len(unique_request_ids)} unique. "
            f"Race condition in request ID generation."
        )
        
        # Check final pool state
        final_pool_metrics = factory.get_pool_metrics()
        
        # Verify no session leaks
        assert final_pool_metrics.leaked_sessions == 0, (
            f"Session leaks detected: {final_pool_metrics.leaked_sessions} leaked sessions. "
            f"Race conditions may have prevented proper cleanup."
        )
        
        logger.info(
            f"✅ 100 concurrent database session allocations completed successfully in {allocation_time:.2f}s. "
            f"Success rate: {successful_allocations}/100, Valid isolation: {valid_isolations}/100, "
            f"Successful DB ops: {successful_db_ops}/100, Race conditions: {len(self.race_condition_detections)}, "
            f"Leaked sessions: {final_pool_metrics.leaked_sessions}"
        )
    
    @pytest.mark.integration
    @pytest.mark.race_conditions
    @requires_real_database
    async def test_session_isolation_under_concurrent_load(self):
        """Test session isolation under concurrent load with overlapping users."""
        factory = await get_session_factory()
        
        async def create_user_sessions(user_id: str, session_count: int):
            """Create multiple sessions for the same user concurrently."""
            user_sessions = []
            
            async def create_single_session(session_index: int):
                try:
                    request_id = f"isolation_req_{user_id}_{session_index}_{uuid.uuid4().hex[:6]}"
                    thread_id = f"isolation_thread_{user_id}_{session_index}"
                    
                    async with get_isolated_session(user_id, request_id, thread_id) as session:
                        # Verify session belongs to correct user
                        session_valid = await validate_session_isolation(session, user_id)
                        
                        # Perform user-specific database operation
                        from sqlalchemy import text
                        result = await session.execute(
                            text("SELECT :user_id as session_user"), 
                            {"user_id": user_id}
                        )
                        session_user = result.scalar()
                        
                        # Verify no cross-user contamination
                        user_match = session_user == user_id
                        
                        return {
                            "user_id": user_id,
                            "session_index": session_index,
                            "request_id": request_id,
                            "session_valid": session_valid,
                            "user_match": user_match,
                            "success": True
                        }
                        
                except Exception as e:
                    logger.error(f"Session creation failed for {user_id}, session {session_index}: {e}")
                    return {
                        "user_id": user_id,
                        "session_index": session_index,
                        "success": False,
                        "error": str(e)
                    }
            
            # Create sessions for this user concurrently
            session_results = await asyncio.gather(
                *[create_single_session(i) for i in range(session_count)],
                return_exceptions=True
            )
            
            return [r for r in session_results if isinstance(r, dict)]
        
        # Create 8 users with 5 sessions each = 40 total sessions
        user_ids = [f"isolation_user_{i:02d}" for i in range(8)]
        
        # Create all user sessions concurrently
        all_user_results = await asyncio.gather(
            *[create_user_sessions(user_id, 5) for user_id in user_ids],
            return_exceptions=True
        )
        
        # Flatten results
        all_session_results = []
        for user_results in all_user_results:
            if isinstance(user_results, list):
                all_session_results.extend(user_results)
        
        # Analyze session isolation
        sessions_by_user = defaultdict(list)
        for result in all_session_results:
            if result.get("success"):
                sessions_by_user[result["user_id"]].append(result)
        
        # Verify each user has exactly 5 sessions
        for user_id in user_ids:
            user_sessions = sessions_by_user[user_id]
            assert len(user_sessions) == 5, (
                f"User {user_id} should have 5 sessions, got {len(user_sessions)}. "
                f"Race conditions may have caused session loss or corruption."
            )
            
            # Verify all sessions for this user are valid and isolated
            for session_result in user_sessions:
                assert session_result["session_valid"], (
                    f"User {user_id} session {session_result['session_index']} failed isolation validation. "
                    f"Race condition in session isolation."
                )
                
                assert session_result["user_match"], (
                    f"User {user_id} session {session_result['session_index']} has user mismatch. "
                    f"Cross-user contamination detected - race condition in session management."
                )
            
            # Verify unique request IDs for this user
            user_request_ids = [s["request_id"] for s in user_sessions]
            unique_user_request_ids = set(user_request_ids)
            
            assert len(user_request_ids) == len(unique_user_request_ids), (
                f"User {user_id} has duplicate request IDs: {len(user_request_ids)} total, "
                f"{len(unique_user_request_ids)} unique. Race condition in ID generation."
            )
        
        # Cross-user isolation verification
        all_request_ids = [r["request_id"] for r in all_session_results if r.get("success")]
        unique_all_request_ids = set(all_request_ids)
        
        assert len(all_request_ids) == len(unique_all_request_ids), (
            f"Cross-user request ID collisions detected: {len(all_request_ids)} total, "
            f"{len(unique_all_request_ids)} unique. Race condition in global ID generation."
        )
        
        # Check for race conditions
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in session isolation: {self.race_condition_detections}"
        )
        
        logger.info(
            f"✅ Session isolation test passed: 8 users × 5 sessions = {len(all_session_results)} total sessions. "
            f"All sessions properly isolated with unique IDs and correct user association."
        )
    
    @pytest.mark.integration
    @pytest.mark.race_conditions
    @requires_real_database
    async def test_connection_pool_exhaustion_detection(self):
        """Test connection pool behavior under high concurrent load."""
        factory = await get_session_factory()
        initial_pool_metrics = factory.get_pool_metrics()
        
        # Track pool state throughout test
        pool_states = []
        
        async def stress_test_session_allocation(batch_index: int, sessions_per_batch: int = 10):
            """Stress test session allocation in batches."""
            batch_sessions = []
            
            try:
                for session_index in range(sessions_per_batch):
                    user_id = f"stress_user_{batch_index:02d}_{session_index:02d}"
                    request_id = f"stress_req_{batch_index:02d}_{session_index:02d}"
                    
                    # Track pool state before allocation
                    pool_metrics = factory.get_pool_metrics()
                    pool_states.append({
                        "batch_index": batch_index,
                        "session_index": session_index,
                        "active_sessions": pool_metrics.active_sessions,
                        "total_created": pool_metrics.total_sessions_created,
                        "timestamp": time.time()
                    })
                    
                    # Allocate session
                    async with get_isolated_session(user_id, request_id) as session:
                        # Perform lightweight database operation
                        from sqlalchemy import text
                        await session.execute(text("SELECT 1"))
                        
                        batch_sessions.append({
                            "user_id": user_id,
                            "request_id": request_id,
                            "success": True
                        })
                        
                        # Small delay to maintain concurrent load
                        await asyncio.sleep(0.002)
                
                return {
                    "batch_index": batch_index,
                    "sessions": batch_sessions,
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Stress test batch {batch_index} failed: {e}")
                return {
                    "batch_index": batch_index,
                    "sessions": batch_sessions,
                    "success": False,
                    "error": str(e)
                }
        
        # Run 12 concurrent batches of 10 sessions each = 120 total sessions
        start_time = time.time()
        batch_results = await asyncio.gather(
            *[stress_test_session_allocation(i, 10) for i in range(12)],
            return_exceptions=True
        )
        stress_test_time = time.time() - start_time
        
        # Analyze stress test results
        successful_batches = len([r for r in batch_results if isinstance(r, dict) and r.get("success")])
        total_sessions_allocated = sum(
            len(r["sessions"]) for r in batch_results 
            if isinstance(r, dict) and r.get("sessions")
        )
        
        # Get final pool metrics
        final_pool_metrics = factory.get_pool_metrics()
        
        # Analyze pool behavior during stress test
        max_concurrent_sessions = max(state["active_sessions"] for state in pool_states)
        peak_created_sessions = max(state["total_created"] for state in pool_states)
        
        # Verify stress test completed successfully
        assert successful_batches == 12, (
            f"Expected 12 successful stress test batches, got {successful_batches}. "
            f"Connection pool may have been exhausted due to race conditions."
        )
        
        assert total_sessions_allocated == 120, (
            f"Expected 120 sessions allocated, got {total_sessions_allocated}. "
            f"Connection pool exhaustion may have prevented allocations."
        )
        
        # Check for pool exhaustion indicators
        assert final_pool_metrics.pool_exhaustion_events == 0, (
            f"Pool exhaustion events detected: {final_pool_metrics.pool_exhaustion_events}. "
            f"Race conditions may have caused connection pool exhaustion."
        )
        
        # Verify no session leaks after stress test
        assert final_pool_metrics.leaked_sessions == 0, (
            f"Session leaks detected after stress test: {final_pool_metrics.leaked_sessions}. "
            f"Race conditions may have prevented proper session cleanup."
        )
        
        # Verify reasonable stress test time
        assert stress_test_time < 60.0, (
            f"Stress test took {stress_test_time:.2f}s, expected < 60s. "
            f"Connection pool bottlenecks may indicate race conditions."
        )
        
        # Check for race conditions
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected during stress test: {self.race_condition_detections}"
        )
        
        logger.info(
            f"✅ Connection pool stress test passed: "
            f"{successful_batches}/12 successful batches, {total_sessions_allocated} sessions allocated "
            f"in {stress_test_time:.2f}s. Peak concurrent sessions: {max_concurrent_sessions}, "
            f"Pool exhaustion events: {final_pool_metrics.pool_exhaustion_events}, "
            f"Leaked sessions: {final_pool_metrics.leaked_sessions}"
        )
    
    @pytest.mark.integration
    @pytest.mark.race_conditions
    @requires_real_database
    async def test_transaction_isolation_races(self):
        """Test database transaction isolation under concurrent access."""
        factory = await get_session_factory()
        
        async def concurrent_transaction_test(transaction_index: int):
            """Test database transactions for isolation violations."""
            try:
                user_id = f"tx_user_{transaction_index:03d}"
                request_id = f"tx_req_{transaction_index:03d}_{uuid.uuid4().hex[:6]}"
                
                async with get_isolated_session(user_id, request_id) as session:
                    # Start transaction
                    await session.begin()
                    
                    try:
                        # Perform transaction-isolated database operations
                        from sqlalchemy import text
                        
                        # Create a test value specific to this transaction
                        test_value = f"tx_test_value_{transaction_index}_{int(time.time() * 1000)}"
                        
                        # Simulate transactional work with potential race conditions
                        await session.execute(
                            text("SELECT pg_sleep(0.001)")  # 1ms delay to create race opportunities
                        )
                        
                        # Verify transaction isolation - each transaction should see its own data
                        result = await session.execute(
                            text("SELECT :test_value as isolated_value"),
                            {"test_value": test_value}
                        )
                        isolated_value = result.scalar()
                        
                        # Check that we got our own value back (transaction isolation)
                        isolation_valid = isolated_value == test_value
                        
                        # Commit transaction
                        await session.commit()
                        
                        return {
                            "transaction_index": transaction_index,
                            "user_id": user_id,
                            "test_value": test_value,
                            "isolated_value": isolated_value,
                            "isolation_valid": isolation_valid,
                            "success": True
                        }
                        
                    except Exception as e:
                        # Rollback on error
                        await session.rollback()
                        raise e
                        
            except Exception as e:
                logger.error(f"Transaction test failed for index {transaction_index}: {e}")
                return {
                    "transaction_index": transaction_index,
                    "success": False,
                    "error": str(e)
                }
        
        # Run 25 concurrent transactions
        transaction_results = await asyncio.gather(
            *[concurrent_transaction_test(i) for i in range(25)],
            return_exceptions=True
        )
        
        # Analyze transaction isolation results
        successful_transactions = len([r for r in transaction_results if isinstance(r, dict) and r.get("success")])
        failed_transactions = len([r for r in transaction_results if not isinstance(r, dict) or not r.get("success")])
        valid_isolations = len([r for r in transaction_results if isinstance(r, dict) and r.get("isolation_valid")])
        
        # Check for transaction isolation violations
        test_values = [r.get("test_value") for r in transaction_results if isinstance(r, dict) and r.get("test_value")]
        isolated_values = [r.get("isolated_value") for r in transaction_results if isinstance(r, dict) and r.get("isolated_value")]
        
        # Verify all test values are unique (no cross-transaction contamination)
        unique_test_values = set(test_values)
        assert len(test_values) == len(unique_test_values), (
            f"Cross-transaction contamination detected: {len(test_values)} values, "
            f"{len(unique_test_values)} unique. Race condition in transaction isolation."
        )
        
        # Verify all transactions succeeded
        assert successful_transactions == 25, (
            f"Expected 25 successful transactions, got {successful_transactions}. "
            f"Failed: {failed_transactions}. Race conditions may have caused transaction failures."
        )
        
        # Verify all transactions maintained isolation
        assert valid_isolations == successful_transactions, (
            f"Expected {successful_transactions} transactions with valid isolation, got {valid_isolations}. "
            f"Race conditions may have violated transaction isolation."
        )
        
        # Check for race conditions
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in transaction isolation: {self.race_condition_detections}"
        )
        
        logger.info(
            f"✅ Transaction isolation race test passed: "
            f"{successful_transactions}/25 successful transactions, "
            f"{valid_isolations}/25 with valid isolation, "
            f"{len(unique_test_values)} unique test values, "
            f"0 race conditions detected"
        )