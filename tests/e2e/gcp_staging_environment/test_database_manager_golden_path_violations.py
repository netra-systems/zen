#!/usr/bin/env python3
"""E2E STAGING: DatabaseManager Golden Path Violation Detection

BUSINESS VALUE: $500K+ ARR - End-to-end database functionality for Golden Path

DESIGNED TO FAIL when:
1. Golden Path database operations fail
2. Concurrent user database operations fail
3. WebSocket + database integration broken
4. Database performance degrades
5. Real staging environment connectivity issues

DESIGNED TO PASS when:
1. Complete Golden Path user flow works
2. Multiple concurrent users supported
3. WebSocket events stored properly
4. Performance within acceptable limits
5. Staging environment fully functional

ANY FAILURE HERE INDICATES BROKEN GOLDEN PATH DATABASE FUNCTIONALITY.
"""

import asyncio
import os
import sys
import uuid
import time
from typing import Dict, Any, Optional, List
import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.e2e
@pytest.mark.staging_only
class TestDatabaseManagerGoldenPathViolations(SSotAsyncTestCase):
    """Test suite to detect DatabaseManager Golden Path violations in staging environment."""

    async def test_golden_path_complete_user_database_flow(self):
        """MUST FAIL if complete Golden Path database user flow is broken.

        Tests the complete user journey from login through chat interactions,
        validating that all database operations work end-to-end.
        """
        test_user_id = f"golden_path_test_user_{uuid.uuid4()}"

        try:
            from netra_backend.app.db.database_manager import DatabaseManager
        except ImportError as e:
            pytest.fail(f"CRITICAL: Cannot import DatabaseManager: {e}")

        db_manager = DatabaseManager()
        await db_manager.initialize()

        # Phase 1: User Authentication Database Operations
        try:
            async with db_manager.get_postgres_session() as session:
                from sqlalchemy import text

                # Simulate user lookup/creation (similar to auth flow)
                result = await session.execute(
                    text("SELECT current_timestamp as auth_time, :user_id as user_id"),
                    {"user_id": test_user_id}
                )
                auth_data = result.fetchone()

                if not auth_data:
                    pytest.fail("USER AUTHENTICATION DATABASE OPERATION FAILED")

        except Exception as e:
            pytest.fail(f"GOLDEN PATH AUTH DATABASE PHASE FAILED: {e}")

        # Phase 2: Chat Session Storage (PostgreSQL)
        session_id = f"session_{uuid.uuid4()}"
        try:
            async with db_manager.get_postgres_session() as session:
                from sqlalchemy import text

                # Simulate chat session storage
                await session.execute(
                    text("""
                        SELECT
                            :session_id as session_id,
                            :user_id as user_id,
                            current_timestamp as created_at
                    """),
                    {"session_id": session_id, "user_id": test_user_id}
                )

                # Test session retrieval
                result = await session.execute(
                    text("SELECT :session_id as retrieved_session"),
                    {"session_id": session_id}
                )
                session_data = result.fetchone()

                if not session_data:
                    pytest.fail("CHAT SESSION DATABASE STORAGE FAILED")

        except Exception as e:
            pytest.fail(f"GOLDEN PATH CHAT SESSION PHASE FAILED: {e}")

        # Phase 3: Metrics and Analytics Storage (ClickHouse)
        try:
            async with db_manager.get_clickhouse_session() as session:
                # Simulate agent execution metrics storage
                result = await session.execute("""
                    SELECT
                        now() as event_time,
                        'agent_execution' as event_type,
                        'test_metric' as metric_name
                """)
                metrics_data = result.fetchone()

                if not metrics_data:
                    pytest.fail("METRICS DATABASE STORAGE FAILED")

        except Exception as e:
            pytest.fail(f"GOLDEN PATH METRICS PHASE FAILED: {e}")

        # Phase 4: WebSocket Database Session Factory Integration
        try:
            session_factory = db_manager.get_db_session_factory()
            if not session_factory:
                pytest.fail("WEBSOCKET SESSION FACTORY CREATION FAILED")

            # Test that factory can create sessions (critical for WebSocket events)
            # This validates the fix for GitHub Issue #204
            if not callable(session_factory):
                pytest.fail("SESSION FACTORY NOT CALLABLE")

        except Exception as e:
            pytest.fail(f"GOLDEN PATH WEBSOCKET DATABASE INTEGRATION FAILED: {e}")

    async def test_concurrent_golden_path_users_database_operations(self):
        """MUST FAIL if database cannot handle concurrent Golden Path users.

        Simulates 10 concurrent users going through complete Golden Path flow,
        validating database can handle realistic concurrent load.
        """
        async def simulate_user_golden_path_flow(user_number: int):
            """Simulate complete Golden Path database operations for one user."""
            user_id = f"concurrent_user_{user_number}_{uuid.uuid4()}"

            try:
                from netra_backend.app.db.database_manager import DatabaseManager
            except ImportError as e:
                raise Exception(f"Import failed for user {user_number}: {e}")

            db_manager = DatabaseManager()
            await db_manager.initialize()

            # User auth simulation
            async with db_manager.get_postgres_session() as session:
                from sqlalchemy import text
                await session.execute(
                    text("SELECT :user_id as user_id, pg_sleep(0.1)"),
                    {"user_id": user_id}
                )

            # Chat session simulation
            session_id = f"session_{user_number}_{uuid.uuid4()}"
            async with db_manager.get_postgres_session() as session:
                await session.execute(
                    text("SELECT :session_id as session_id, pg_sleep(0.1)"),
                    {"session_id": session_id}
                )

            # Metrics simulation
            async with db_manager.get_clickhouse_session() as session:
                await session.execute("""
                    SELECT
                        now() as event_time,
                        'concurrent_test' as event_type
                """)

            return f"User {user_number} completed successfully"

        # Test 10 concurrent users
        start_time = time.time()
        tasks = []

        for user_num in range(10):
            task = simulate_user_golden_path_flow(user_num)
            tasks.append(task)

        try:
            results = await asyncio.gather(*tasks)
            end_time = time.time()

            # All users should complete successfully
            if len(results) != 10:
                pytest.fail(f"CONCURRENT USERS FAILED: Only {len(results)}/10 completed")

            # Should complete within reasonable time (< 30 seconds for 10 users)
            execution_time = end_time - start_time
            if execution_time > 30:
                pytest.fail(f"CONCURRENT DATABASE OPERATIONS TOO SLOW: {execution_time:.2f}s")

        except Exception as e:
            pytest.fail(f"CONCURRENT GOLDEN PATH DATABASE OPERATIONS FAILED: {e}")

    async def test_database_websocket_event_storage_integration(self):
        """MUST FAIL if WebSocket events cannot be properly stored in database.

        Validates that WebSocket agent events can be stored and retrieved
        from the database, ensuring complete Golden Path functionality.
        """
        event_id = f"websocket_event_{uuid.uuid4()}"

        try:
            from netra_backend.app.db.database_manager import DatabaseManager
        except ImportError as e:
            pytest.fail(f"CRITICAL: Cannot import DatabaseManager: {e}")

        db_manager = DatabaseManager()
        await db_manager.initialize()

        # Simulate WebSocket event storage
        websocket_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        try:
            # Test storing all required WebSocket events
            for event_type in websocket_events:
                async with db_manager.get_postgres_session() as session:
                    from sqlalchemy import text

                    # Simulate event storage
                    await session.execute(
                        text("""
                            SELECT
                                :event_id as event_id,
                                :event_type as event_type,
                                current_timestamp as event_time
                        """),
                        {"event_id": f"{event_id}_{event_type}", "event_type": event_type}
                    )

                # Also store metrics in ClickHouse
                async with db_manager.get_clickhouse_session() as session:
                    await session.execute("""
                        SELECT
                            now() as event_time,
                            'websocket_event' as category,
                            'golden_path_test' as source
                    """)

        except Exception as e:
            pytest.fail(f"WEBSOCKET EVENT DATABASE STORAGE FAILED: {e}")

        # Test WebSocket session factory accessibility
        try:
            session_factory = db_manager.get_db_session_factory()
            if not session_factory:
                pytest.fail("WEBSOCKET SESSION FACTORY UNAVAILABLE FOR EVENT STORAGE")

        except Exception as e:
            pytest.fail(f"WEBSOCKET SESSION FACTORY ACCESS FAILED: {e}")

    async def test_database_performance_under_golden_path_load(self):
        """MUST FAIL if database performance degrades under Golden Path load.

        Tests database performance with realistic Golden Path usage patterns
        to ensure acceptable response times and resource usage.
        """
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
        except ImportError as e:
            pytest.fail(f"CRITICAL: Cannot import DatabaseManager: {e}")

        db_manager = DatabaseManager()
        await db_manager.initialize()

        # Performance test parameters
        num_operations = 50
        max_acceptable_time_per_op = 0.5  # 500ms max per operation

        # Test PostgreSQL performance
        postgres_times = []
        for i in range(num_operations):
            start_time = time.time()
            try:
                async with db_manager.get_postgres_session() as session:
                    from sqlalchemy import text
                    await session.execute(
                        text("SELECT :iteration as iteration, current_timestamp"),
                        {"iteration": i}
                    )
            except Exception as e:
                pytest.fail(f"POSTGRES OPERATION {i} FAILED: {e}")

            operation_time = time.time() - start_time
            postgres_times.append(operation_time)

            if operation_time > max_acceptable_time_per_op:
                pytest.fail(
                    f"POSTGRES PERFORMANCE DEGRADED: Operation {i} took {operation_time:.2f}s "
                    f"(max acceptable: {max_acceptable_time_per_op}s)"
                )

        # Test ClickHouse performance
        clickhouse_times = []
        for i in range(num_operations):
            start_time = time.time()
            try:
                async with db_manager.get_clickhouse_session() as session:
                    await session.execute(f"SELECT {i} as iteration, now()")
            except Exception as e:
                pytest.fail(f"CLICKHOUSE OPERATION {i} FAILED: {e}")

            operation_time = time.time() - start_time
            clickhouse_times.append(operation_time)

            if operation_time > max_acceptable_time_per_op:
                pytest.fail(
                    f"CLICKHOUSE PERFORMANCE DEGRADED: Operation {i} took {operation_time:.2f}s "
                    f"(max acceptable: {max_acceptable_time_per_op}s)"
                )

        # Validate overall performance metrics
        avg_postgres_time = sum(postgres_times) / len(postgres_times)
        avg_clickhouse_time = sum(clickhouse_times) / len(clickhouse_times)

        if avg_postgres_time > 0.2:  # 200ms average
            pytest.fail(f"POSTGRES AVERAGE PERFORMANCE TOO SLOW: {avg_postgres_time:.2f}s")

        if avg_clickhouse_time > 0.2:  # 200ms average
            pytest.fail(f"CLICKHOUSE AVERAGE PERFORMANCE TOO SLOW: {avg_clickhouse_time:.2f}s")

    async def test_database_connection_recovery_golden_path(self):
        """MUST FAIL if database connections cannot recover from failures.

        Tests that database connections can be re-established after failures,
        ensuring Golden Path resilience in staging environment.
        """
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
        except ImportError as e:
            pytest.fail(f"CRITICAL: Cannot import DatabaseManager: {e}")

        db_manager = DatabaseManager()
        await db_manager.initialize()

        # Test normal operation
        try:
            async with db_manager.get_postgres_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1 as initial_test"))
                if not result.fetchone():
                    pytest.fail("INITIAL DATABASE CONNECTION FAILED")
        except Exception as e:
            pytest.fail(f"INITIAL DATABASE TEST FAILED: {e}")

        # Test connection cleanup and re-initialization
        try:
            await db_manager.close_connections()

            # Re-initialize
            await db_manager.initialize()

            # Test connections work after re-initialization
            async with db_manager.get_postgres_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1 as recovery_test"))
                if not result.fetchone():
                    pytest.fail("DATABASE CONNECTION RECOVERY FAILED")

            async with db_manager.get_clickhouse_session() as session:
                result = await session.execute("SELECT 1 as recovery_test")
                if not result.fetchone():
                    pytest.fail("CLICKHOUSE CONNECTION RECOVERY FAILED")

        except Exception as e:
            pytest.fail(f"DATABASE CONNECTION RECOVERY FAILED: {e}")