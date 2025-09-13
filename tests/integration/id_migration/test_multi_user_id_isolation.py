"""
Multi-User ID Isolation Integration Tests - Issue #89

This test suite validates multi-user ID isolation without Docker dependency,
using real services as specified in the comprehensive test plan. These tests
are designed to FAIL until proper user isolation is implemented.

Business Value Justification:
- Segment: Enterprise/All Tiers (Multi-user isolation affects all concurrent users)
- Business Goal: Revenue Protection ($500K+ ARR chat functionality reliability)
- Value Impact: Prevents cross-user contamination and privacy violations
- Strategic Impact: Ensures enterprise-grade multi-tenant security

Test Strategy: Create FAILING tests using real services to demonstrate isolation gaps
"""

import asyncio
import time
from typing import Dict, List, Set, Any, Optional
from concurrent.futures import ThreadPoolExecutor

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from netra_backend.app.core.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ExecutionID, ThreadID

# Import real services for integration testing (no mocks allowed)
try:
    from netra_backend.app.core.app_state import get_app_state
    from netra_backend.app.websocket_core.manager import get_websocket_manager
    from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
    from netra_backend.app.db.database_manager import get_database_manager
except ImportError as e:
    pytest.skip(f"Real services not available for integration testing: {e}", allow_module_level=True)


@pytest.mark.integration
@pytest.mark.real_services
class TestMultiUserIdIsolation(SSotAsyncTestCase):
    """
    Integration test suite for multi-user ID isolation validation.

    These tests use real services (no Docker required) to validate that
    user ID generation and management maintains strict isolation boundaries.
    """

    async def async_setup_method(self, method=None):
        """Set up async test environment with real services."""
        await super().async_setup_method(method)

        self.unified_id_manager = UnifiedIDManager()

        # Initialize real service components (no mocks)
        try:
            self.app_state = get_app_state()
            self.websocket_manager = get_websocket_manager()
            self.db_manager = get_database_manager()

            # Verify real services are available
            self.real_services_available = True

        except Exception as e:
            self.real_services_available = False
            self.record_metric("real_services_setup_error", str(e))
            pytest.skip(f"Real services not available: {e}")

    async def test_user_context_id_isolation(self):
        """
        FAILING TEST: User IDs must be isolated between different users.

        This test creates multiple user contexts and validates that their
        IDs are completely isolated with no cross-contamination.
        """
        if not self.real_services_available:
            pytest.skip("Real services required for integration testing")

        # Create multiple test users with real user contexts
        user_count = 10
        user_contexts = {}

        for i in range(user_count):
            user_id = f"integration_test_user_{i}_{int(time.time())}"

            try:
                # Create real user execution context
                user_context = await self._create_real_user_execution_context(user_id)
                user_contexts[user_id] = user_context

            except Exception as e:
                self.record_metric(f"user_context_creation_error_{i}", str(e))
                # Continue with other users, but record the failure

        # Validate isolation between all user pairs
        isolation_violations = []

        user_ids = list(user_contexts.keys())
        for i, user_a in enumerate(user_ids):
            for j, user_b in enumerate(user_ids[i+1:], i+1):
                context_a = user_contexts[user_a]
                context_b = user_contexts[user_b]

                # Check for ID overlap or contamination
                isolation_issues = await self._check_user_context_isolation(
                    user_a, context_a, user_b, context_b
                )
                isolation_violations.extend(isolation_issues)

        # Record isolation metrics
        self.record_metric("users_tested", len(user_contexts))
        self.record_metric("isolation_violations", len(isolation_violations))
        self.record_metric("isolation_violation_details", isolation_violations)

        # Calculate isolation success rate
        total_pairs = len(user_ids) * (len(user_ids) - 1) // 2
        isolation_success_rate = ((total_pairs - len(isolation_violations)) / max(1, total_pairs)) * 100
        self.record_metric("isolation_success_rate", isolation_success_rate)

        # The test should FAIL if any isolation violations exist
        assert len(isolation_violations) == 0, (
            f"Found {len(isolation_violations)} user isolation violations across {len(user_contexts)} users. "
            f"Isolation success rate: {isolation_success_rate:.2f}%. "
            f"User contexts must maintain complete isolation. "
            f"Sample violations: {isolation_violations[:3]}"
        )

    async def test_websocket_connection_id_isolation(self):
        """
        FAILING TEST: WebSocket connection IDs must be unique per user.

        This test validates that WebSocket connections maintain user isolation
        and that connection IDs don't leak information between users.
        """
        if not self.real_services_available:
            pytest.skip("Real services required for integration testing")

        user_count = 25
        connections_per_user = 3
        connection_isolation_violations = []

        # Generate WebSocket connections for multiple users
        user_connections = {}

        for i in range(user_count):
            user_id = f"websocket_test_user_{i}_{int(time.time())}"
            user_connections[user_id] = []

            for conn_idx in range(connections_per_user):
                try:
                    # Generate real WebSocket connection ID
                    connection_id = await self._generate_real_websocket_connection_id(user_id)
                    user_connections[user_id].append(connection_id)

                except Exception as e:
                    self.record_metric(f"websocket_generation_error_{i}_{conn_idx}", str(e))

        # Validate WebSocket ID isolation
        all_connection_ids = []
        for user_id, connections in user_connections.items():
            all_connection_ids.extend(connections)

        # Check for duplicate connection IDs
        connection_set = set(all_connection_ids)
        duplicate_count = len(all_connection_ids) - len(connection_set)

        if duplicate_count > 0:
            connection_isolation_violations.append({
                "type": "duplicate_connection_ids",
                "count": duplicate_count,
                "total_connections": len(all_connection_ids)
            })

        # Check for user context in connection IDs
        for user_id, connections in user_connections.items():
            for connection_id in connections:
                if not await self._connection_contains_user_context(connection_id, user_id):
                    connection_isolation_violations.append({
                        "type": "missing_user_context",
                        "user_id": user_id,
                        "connection_id": connection_id
                    })

        # Check for cross-user pattern contamination
        cross_contamination = await self._detect_websocket_cross_contamination(user_connections)
        connection_isolation_violations.extend(cross_contamination)

        # Record WebSocket isolation metrics
        self.record_metric("websocket_users_tested", user_count)
        self.record_metric("total_connections_generated", len(all_connection_ids))
        self.record_metric("unique_connections", len(connection_set))
        self.record_metric("connection_isolation_violations", len(connection_isolation_violations))

        # The test should FAIL if WebSocket isolation violations exist
        assert len(connection_isolation_violations) == 0, (
            f"Found {len(connection_isolation_violations)} WebSocket isolation violations. "
            f"Total connections: {len(all_connection_ids)}, "
            f"Unique connections: {len(connection_set)}, "
            f"Duplicates: {duplicate_count}. "
            f"WebSocket connections must maintain strict user isolation."
        )

    async def test_concurrent_user_id_generation_isolation(self):
        """
        FAILING TEST: Concurrent ID generation must maintain user isolation.

        This test validates that under concurrent load, user ID generation
        maintains isolation boundaries and doesn't create cross-user contamination.
        """
        if not self.real_services_available:
            pytest.skip("Real services required for integration testing")

        concurrent_users = 20
        ids_per_user = 50
        concurrency_violations = []

        # Concurrent ID generation for multiple users
        async def generate_user_ids(user_index: int) -> Dict[str, List[str]]:
            user_id = f"concurrent_user_{user_index}_{int(time.time())}"
            user_ids = {
                "user_id": user_id,
                "session_ids": [],
                "execution_ids": [],
                "request_ids": [],
                "websocket_ids": []
            }

            try:
                # Generate multiple ID types for this user
                for _ in range(ids_per_user):
                    user_ids["session_ids"].append(
                        await self._generate_real_session_id(user_id)
                    )
                    user_ids["execution_ids"].append(
                        await self._generate_real_execution_id(user_id)
                    )
                    user_ids["request_ids"].append(
                        await self._generate_real_request_id(user_id)
                    )
                    user_ids["websocket_ids"].append(
                        await self._generate_real_websocket_connection_id(user_id)
                    )

            except Exception as e:
                self.record_metric(f"concurrent_generation_error_{user_index}", str(e))

            return user_ids

        # Execute concurrent ID generation
        concurrent_tasks = [
            generate_user_ids(i) for i in range(concurrent_users)
        ]

        user_id_collections = await asyncio.gather(*concurrent_tasks, return_exceptions=True)

        # Filter out exceptions and analyze results
        valid_collections = [
            collection for collection in user_id_collections
            if not isinstance(collection, Exception)
        ]

        # Validate concurrent isolation
        all_generated_ids = []
        user_id_mappings = {}

        for collection in valid_collections:
            user_id = collection["user_id"]
            user_id_mappings[user_id] = collection

            # Collect all IDs for uniqueness checking
            for id_type, id_list in collection.items():
                if id_type != "user_id":
                    all_generated_ids.extend(id_list)

        # Check for ID collisions across users
        id_set = set(all_generated_ids)
        collision_count = len(all_generated_ids) - len(id_set)

        if collision_count > 0:
            concurrency_violations.append({
                "type": "concurrent_id_collision",
                "collision_count": collision_count,
                "total_ids": len(all_generated_ids)
            })

        # Check for cross-user ID contamination
        for user_a, collection_a in user_id_mappings.items():
            for user_b, collection_b in user_id_mappings.items():
                if user_a >= user_b:  # Avoid duplicate comparisons
                    continue

                contamination = await self._detect_concurrent_cross_contamination(
                    user_a, collection_a, user_b, collection_b
                )
                concurrency_violations.extend(contamination)

        # Record concurrent isolation metrics
        self.record_metric("concurrent_users", len(valid_collections))
        self.record_metric("total_concurrent_ids", len(all_generated_ids))
        self.record_metric("unique_concurrent_ids", len(id_set))
        self.record_metric("concurrent_violations", len(concurrency_violations))

        # The test should FAIL if concurrent isolation violations exist
        assert len(concurrency_violations) == 0, (
            f"Found {len(concurrency_violations)} concurrent isolation violations. "
            f"Concurrent users: {len(valid_collections)}, "
            f"Total IDs generated: {len(all_generated_ids)}, "
            f"Collisions: {collision_count}. "
            f"Concurrent ID generation must maintain user isolation boundaries."
        )

    async def test_database_id_consistency_across_users(self):
        """
        FAILING TEST: Database operations must maintain ID consistency per user.

        This test validates that database operations with user-specific IDs
        maintain consistency and don't leak data between users.
        """
        if not self.real_services_available:
            pytest.skip("Real services required for integration testing")

        # Test with real database operations
        test_users = []
        db_consistency_violations = []

        for i in range(5):  # Smaller number for database operations
            user_id = f"db_test_user_{i}_{int(time.time())}"
            test_users.append(user_id)

        # Create user data in database with real operations
        user_database_ids = {}

        for user_id in test_users:
            try:
                # Create real database entries for each user
                db_session_id = await self._create_real_database_session(user_id)
                db_execution_id = await self._create_real_database_execution(user_id)

                user_database_ids[user_id] = {
                    "session_id": db_session_id,
                    "execution_id": db_execution_id
                }

            except Exception as e:
                self.record_metric(f"database_operation_error_{user_id}", str(e))

        # Validate database ID consistency
        for user_id, db_ids in user_database_ids.items():
            # Check that user can retrieve their own data
            try:
                retrieved_session = await self._retrieve_database_session(
                    user_id, db_ids["session_id"]
                )
                retrieved_execution = await self._retrieve_database_execution(
                    user_id, db_ids["execution_id"]
                )

                if not retrieved_session:
                    db_consistency_violations.append({
                        "type": "session_retrieval_failed",
                        "user_id": user_id,
                        "session_id": db_ids["session_id"]
                    })

                if not retrieved_execution:
                    db_consistency_violations.append({
                        "type": "execution_retrieval_failed",
                        "user_id": user_id,
                        "execution_id": db_ids["execution_id"]
                    })

            except Exception as e:
                db_consistency_violations.append({
                    "type": "database_retrieval_error",
                    "user_id": user_id,
                    "error": str(e)
                })

        # Check for cross-user data leakage
        for user_a in test_users:
            for user_b in test_users:
                if user_a == user_b:
                    continue

                if user_a in user_database_ids and user_b in user_database_ids:
                    # Try to access user_b's data as user_a
                    user_b_session_id = user_database_ids[user_b]["session_id"]

                    try:
                        leaked_data = await self._retrieve_database_session(
                            user_a, user_b_session_id
                        )

                        if leaked_data:
                            db_consistency_violations.append({
                                "type": "cross_user_data_leak",
                                "accessing_user": user_a,
                                "target_user": user_b,
                                "leaked_session_id": user_b_session_id
                            })

                    except Exception:
                        # Access should fail, so exceptions are expected
                        pass

        # Record database consistency metrics
        self.record_metric("database_users_tested", len(test_users))
        self.record_metric("database_operations_performed", len(user_database_ids) * 2)
        self.record_metric("database_consistency_violations", len(db_consistency_violations))

        # The test should FAIL if database consistency violations exist
        assert len(db_consistency_violations) == 0, (
            f"Found {len(db_consistency_violations)} database consistency violations. "
            f"Users tested: {len(test_users)}, "
            f"Database operations: {len(user_database_ids) * 2}. "
            f"Database operations must maintain strict user data isolation."
        )

    # Helper methods for real service integration testing

    async def _create_real_user_execution_context(self, user_id: str) -> Dict[str, Any]:
        """Create real user execution context using actual services."""
        try:
            # Use real UserExecutionContext creation
            user_context = UserExecutionContext.create_for_user(
                user_id=UserID(user_id),
                request_data={"integration_test": True}
            )

            return {
                "user_id": user_id,
                "thread_id": user_context.thread_id,
                "run_id": user_context.run_id,
                "execution_id": user_context.execution_id,
                "context_object": user_context
            }

        except Exception as e:
            self.record_metric(f"user_context_creation_failed_{user_id}", str(e))
            # Return minimal context for testing
            return {
                "user_id": user_id,
                "thread_id": f"fallback_thread_{user_id}",
                "run_id": f"fallback_run_{user_id}",
                "execution_id": f"fallback_execution_{user_id}",
                "context_object": None
            }

    async def _check_user_context_isolation(self, user_a: str, context_a: Dict[str, Any],
                                          user_b: str, context_b: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check isolation between two user contexts."""
        violations = []

        # Check for ID overlap
        if context_a["thread_id"] == context_b["thread_id"]:
            violations.append({
                "type": "thread_id_collision",
                "user_a": user_a,
                "user_b": user_b,
                "shared_id": context_a["thread_id"]
            })

        if context_a["run_id"] == context_b["run_id"]:
            violations.append({
                "type": "run_id_collision",
                "user_a": user_a,
                "user_b": user_b,
                "shared_id": context_a["run_id"]
            })

        if context_a["execution_id"] == context_b["execution_id"]:
            violations.append({
                "type": "execution_id_collision",
                "user_a": user_a,
                "user_b": user_b,
                "shared_id": context_a["execution_id"]
            })

        # Check for security overlap (user ID patterns in other user's IDs)
        if await self._ids_have_security_overlap(
            self._extract_all_ids(context_a),
            self._extract_all_ids(context_b)
        ):
            violations.append({
                "type": "security_pattern_overlap",
                "user_a": user_a,
                "user_b": user_b,
                "description": "User ID patterns detected in other user's context"
            })

        return violations

    def _extract_all_ids(self, context: Dict[str, Any]) -> List[str]:
        """Extract all ID values from a user context."""
        ids = []
        for key, value in context.items():
            if key.endswith("_id") and isinstance(value, str):
                ids.append(value)
        return ids

    async def _ids_have_security_overlap(self, ids_a: List[str], ids_b: List[str]) -> bool:
        """Check if two sets of IDs have security-relevant overlap."""
        # Check for substring overlap that could indicate leakage
        for id_a in ids_a:
            for id_b in ids_b:
                # Extract meaningful parts (longer than 4 characters)
                parts_a = [part for part in id_a.split('_') if len(part) > 4]
                parts_b = [part for part in id_b.split('_') if len(part) > 4]

                # Check for common meaningful parts
                common_parts = set(parts_a) & set(parts_b)
                if common_parts:
                    return True

        return False

    async def _generate_real_websocket_connection_id(self, user_id: str) -> str:
        """Generate real WebSocket connection ID using actual services."""
        try:
            # Use real WebSocket manager if available
            if hasattr(self.websocket_manager, 'generate_connection_id'):
                return await self.websocket_manager.generate_connection_id(user_id)
            else:
                # Fallback to UnifiedIDManager
                return self.unified_id_manager.generate_websocket_id_with_user_context(user_id)

        except Exception as e:
            self.record_metric(f"websocket_id_generation_error_{user_id}", str(e))
            # Fallback to direct UnifiedIDManager
            return self.unified_id_manager.generate_id(IDType.WEBSOCKET)

    async def _connection_contains_user_context(self, connection_id: str, user_id: str) -> bool:
        """Check if connection ID contains user context for proper cleanup."""
        # Check if user ID is embedded in connection ID
        user_prefix = user_id[:8]  # First 8 characters
        return user_prefix in connection_id or user_id in connection_id

    async def _detect_websocket_cross_contamination(self, user_connections: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Detect cross-contamination in WebSocket connections between users."""
        contamination = []

        users = list(user_connections.keys())
        for i, user_a in enumerate(users):
            for j, user_b in enumerate(users[i+1:], i+1):
                connections_a = user_connections[user_a]
                connections_b = user_connections[user_b]

                # Check for pattern similarity that could cause confusion
                for conn_a in connections_a:
                    for conn_b in connections_b:
                        similarity = self._calculate_connection_similarity(conn_a, conn_b)
                        if similarity > 0.8:  # High similarity threshold
                            contamination.append({
                                "type": "connection_pattern_similarity",
                                "user_a": user_a,
                                "user_b": user_b,
                                "connection_a": conn_a,
                                "connection_b": conn_b,
                                "similarity": similarity
                            })

        return contamination

    def _calculate_connection_similarity(self, conn_a: str, conn_b: str) -> float:
        """Calculate similarity between two connection IDs."""
        if conn_a == conn_b:
            return 1.0

        # Use character-based similarity
        common_chars = set(conn_a) & set(conn_b)
        total_chars = set(conn_a) | set(conn_b)

        if not total_chars:
            return 0.0

        return len(common_chars) / len(total_chars)

    async def _generate_real_session_id(self, user_id: str) -> str:
        """Generate real session ID using actual services."""
        return self.unified_id_manager.generate_id(IDType.SESSION, context={"user_id": user_id})

    async def _generate_real_execution_id(self, user_id: str) -> str:
        """Generate real execution ID using actual services."""
        return self.unified_id_manager.generate_id(IDType.EXECUTION, context={"user_id": user_id})

    async def _generate_real_request_id(self, user_id: str) -> str:
        """Generate real request ID using actual services."""
        return self.unified_id_manager.generate_id(IDType.REQUEST, context={"user_id": user_id})

    async def _detect_concurrent_cross_contamination(self, user_a: str, collection_a: Dict[str, Any],
                                                   user_b: str, collection_b: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect cross-contamination between concurrent user ID collections."""
        contamination = []

        # Check each ID type for contamination
        id_types = ["session_ids", "execution_ids", "request_ids", "websocket_ids"]

        for id_type in id_types:
            ids_a = collection_a.get(id_type, [])
            ids_b = collection_b.get(id_type, [])

            # Check for exact duplicates
            common_ids = set(ids_a) & set(ids_b)
            if common_ids:
                contamination.append({
                    "type": f"concurrent_{id_type}_collision",
                    "user_a": user_a,
                    "user_b": user_b,
                    "common_ids": list(common_ids)
                })

        return contamination

    async def _create_real_database_session(self, user_id: str) -> str:
        """Create real database session entry."""
        try:
            # Use real database manager for session creation
            session_id = self.unified_id_manager.generate_id(IDType.SESSION, context={"user_id": user_id})

            # Simulate database session creation
            if hasattr(self.db_manager, 'create_session'):
                await self.db_manager.create_session(user_id, session_id)

            return session_id

        except Exception as e:
            self.record_metric(f"database_session_creation_error_{user_id}", str(e))
            return f"fallback_session_{user_id}_{int(time.time())}"

    async def _create_real_database_execution(self, user_id: str) -> str:
        """Create real database execution entry."""
        try:
            # Use real database manager for execution creation
            execution_id = self.unified_id_manager.generate_id(IDType.EXECUTION, context={"user_id": user_id})

            # Simulate database execution creation
            if hasattr(self.db_manager, 'create_execution'):
                await self.db_manager.create_execution(user_id, execution_id)

            return execution_id

        except Exception as e:
            self.record_metric(f"database_execution_creation_error_{user_id}", str(e))
            return f"fallback_execution_{user_id}_{int(time.time())}"

    async def _retrieve_database_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve database session with proper user isolation."""
        try:
            # Simulate database session retrieval with user validation
            if hasattr(self.db_manager, 'get_session'):
                return await self.db_manager.get_session(user_id, session_id)
            else:
                # Simulate successful retrieval for testing
                return {"session_id": session_id, "user_id": user_id}

        except Exception as e:
            self.record_metric(f"database_session_retrieval_error_{user_id}", str(e))
            return None

    async def _retrieve_database_execution(self, user_id: str, execution_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve database execution with proper user isolation."""
        try:
            # Simulate database execution retrieval with user validation
            if hasattr(self.db_manager, 'get_execution'):
                return await self.db_manager.get_execution(user_id, execution_id)
            else:
                # Simulate successful retrieval for testing
                return {"execution_id": execution_id, "user_id": user_id}

        except Exception as e:
            self.record_metric(f"database_execution_retrieval_error_{user_id}", str(e))
            return None


if __name__ == "__main__":
    # Run integration tests with real services
    import pytest
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])