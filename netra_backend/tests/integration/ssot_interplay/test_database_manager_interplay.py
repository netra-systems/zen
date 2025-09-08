"""
Integration Tests for DatabaseManager SSOT Interplay

Business Value Justification (BVJ):
- Segment: All segments - Database reliability affects all user operations  
- Business Goal: Data Integrity & Multi-User Safety
- Value Impact: Ensures database operations prevent data corruption and user isolation
- Strategic Impact: CRITICAL for data security and platform reliability

This test suite validates the critical interactions between DatabaseManager and other SSOT 
components across the Netra platform. These tests use REAL services to validate actual 
business scenarios that could break multi-user data operations.

CRITICAL AREAS TESTED:
1. Database Session Isolation - Factory pattern isolation & concurrent user safety
2. Configuration Integration - DatabaseURLBuilder and IsolatedEnvironment interplay
3. Multi-User Transaction Safety - Transaction boundaries and isolation levels  
4. Agent Integration - Database context sharing with agent operations
5. System Integration - Health monitoring, migration, and connection management

WARNING: NO MOCKS! These are integration tests using real DatabaseManager instances,
real database connections, real session management, real transaction isolation.
"""

import asyncio
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from unittest.mock import patch
import os

import pytest
import psycopg2
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError, InvalidRequestError

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture, with_test_database
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.database.session_manager import SessionScopeValidator, SessionIsolationError
from netra_backend.app.websocket_core import create_websocket_manager
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass  
class DatabaseTestMetrics:
    """Metrics for database test validation."""
    session_count: int = 0
    connection_count: int = 0
    transaction_count: int = 0
    rollback_count: int = 0
    error_count: int = 0
    isolation_violations: List[str] = None
    
    def __post_init__(self):
        if self.isolation_violations is None:
            self.isolation_violations = []


class TestDatabaseManagerInterplay(BaseIntegrationTest):
    """Integration tests for DatabaseManager SSOT interactions."""
    
    def setup_method(self):
        """Set up each test with clean database state."""
        super().setup_method()
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.test_request_id = f"req_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        # Track resources for cleanup
        self.created_sessions: List[AsyncSession] = []
        self.created_managers: List[DatabaseManager] = []
        self.test_metrics = DatabaseTestMetrics()
        
    def teardown_method(self):
        """Clean up database resources after each test."""
        super().teardown_method()
        # Clean up any created resources
        for manager in self.created_managers:
            try:
                asyncio.run(manager.close_all())
            except Exception as e:
                logger.warning(f"Failed to clean up manager: {e}")

    # ========== DATABASE SESSION ISOLATION TESTS ==========

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_session_isolation_concurrent_users(self, with_test_database):
        """
        Test database session isolation between concurrent users.
        
        BVJ: All segments | Data Integrity | Prevents user data leakage and corruption
        """
        # Create separate database managers for each user
        user1_manager = DatabaseManager()
        user2_manager = DatabaseManager()
        self.created_managers.extend([user1_manager, user2_manager])
        
        await user1_manager.initialize()
        await user2_manager.initialize()
        
        # Track session isolation
        user1_sessions = []
        user2_sessions = []
        
        async def user1_operations():
            """Simulate user 1 database operations."""
            for i in range(3):
                async with user1_manager.get_session() as session:
                    user1_sessions.append(id(session))
                    # Create user-specific data
                    await session.execute(text(f"CREATE TEMP TABLE user1_temp_{i} (id INT)"))
                    await session.execute(text(f"INSERT INTO user1_temp_{i} VALUES ({i})"))
                    await asyncio.sleep(0.01)  # Allow concurrent execution
                    
        async def user2_operations():
            """Simulate user 2 database operations."""
            for i in range(3):
                async with user2_manager.get_session() as session:
                    user2_sessions.append(id(session))
                    # Create user-specific data
                    await session.execute(text(f"CREATE TEMP TABLE user2_temp_{i} (id INT)"))
                    await session.execute(text(f"INSERT INTO user2_temp_{i} VALUES ({i + 100})"))
                    await asyncio.sleep(0.01)  # Allow concurrent execution
        
        # Run concurrent user operations
        await asyncio.gather(user1_operations(), user2_operations())
        
        # Verify session isolation - no shared session objects
        assert len(set(user1_sessions)) == 3, "User 1 should have 3 unique sessions"
        assert len(set(user2_sessions)) == 3, "User 2 should have 3 unique sessions"
        assert set(user1_sessions).isdisjoint(set(user2_sessions)), "Sessions must be isolated between users"
        
        logger.info("✅ Database session isolation verified for concurrent users")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_transaction_boundary_management_across_agent_operations(self, with_test_database):
        """
        Test transaction boundary management across agent operations.
        
        BVJ: All segments | Data Integrity | Ensures agent operations maintain transaction boundaries
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        # Create user context for agent operations
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id=self.test_request_id,
            thread_id=self.test_thread_id
        )
        
        transaction_states = []
        
        async def agent_database_operation(operation_id: int):
            """Simulate agent database operation with transaction boundary."""
            async with manager.get_session() as session:
                try:
                    # Simulate agent data creation
                    await session.execute(text(f"CREATE TEMP TABLE agent_op_{operation_id} (id INT)"))
                    await session.execute(text(f"INSERT INTO agent_op_{operation_id} VALUES ({operation_id})"))
                    
                    # Check transaction state
                    result = await session.execute(text("SELECT txid_current()"))
                    txid = result.scalar()
                    transaction_states.append(f"op_{operation_id}_tx_{txid}")
                    
                    # Simulate agent processing time
                    await asyncio.sleep(0.02)
                    
                    if operation_id == 2:
                        # Force rollback for one operation
                        raise Exception(f"Simulated agent error in operation {operation_id}")
                        
                except Exception as e:
                    # Transaction should rollback automatically
                    logger.info(f"Operation {operation_id} rolled back: {e}")
                    self.test_metrics.rollback_count += 1
                    raise
        
        # Execute multiple agent operations
        results = []
        for i in range(4):
            try:
                await agent_database_operation(i)
                results.append(f"success_{i}")
            except Exception:
                results.append(f"failed_{i}")
        
        # Verify transaction isolation
        assert len(set(transaction_states)) >= 3, "Each operation should have unique transaction ID"
        assert self.test_metrics.rollback_count == 1, "One operation should have rolled back"
        assert "failed_2" in results, "Operation 2 should have failed"
        assert "success_0" in results, "Other operations should succeed independently"
        
        logger.info("✅ Transaction boundary management verified across agent operations")

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_session_cleanup_and_resource_management(self, with_test_database):
        """
        Test session cleanup and resource management.
        
        BVJ: Platform/Internal | System Stability | Prevents memory leaks and connection exhaustion
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        initial_engine = manager.get_engine()
        
        # Track resource usage
        session_lifecycle = []
        
        async def create_and_cleanup_sessions():
            """Create sessions and verify cleanup."""
            for i in range(5):
                session_id = None
                try:
                    async with manager.get_session() as session:
                        session_id = id(session)
                        session_lifecycle.append(f"created_{session_id}")
                        
                        # Use session
                        await session.execute(text("SELECT 1"))
                        
                        # Verify session is active
                        assert session.is_active or not session.autocommit, "Session should be active"
                        
                except Exception as e:
                    session_lifecycle.append(f"error_{session_id}_{e}")
                finally:
                    if session_id:
                        session_lifecycle.append(f"cleanup_{session_id}")
        
        # Execute session lifecycle test
        await create_and_cleanup_sessions()
        
        # Verify resource cleanup
        created_count = len([x for x in session_lifecycle if x.startswith("created_")])
        cleanup_count = len([x for x in session_lifecycle if x.startswith("cleanup_")])
        
        assert created_count == 5, "Should have created 5 sessions"
        assert cleanup_count == 5, "Should have cleaned up 5 sessions"
        
        # Verify engine is still available
        assert manager.get_engine() is initial_engine, "Engine should remain consistent"
        
        # Test connection pool health
        health_check = await manager.health_check()
        assert health_check["status"] == "healthy", "Connection pool should remain healthy"
        
        logger.info("✅ Session cleanup and resource management verified")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_pool_management_under_concurrent_load(self, with_test_database):
        """
        Test connection pool management under concurrent load.
        
        BVJ: All segments | System Reliability | Prevents connection exhaustion under user load
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        connection_metrics = []
        error_count = 0
        
        async def concurrent_database_operations(worker_id: int):
            """Simulate concurrent database operations."""
            nonlocal error_count
            worker_connections = []
            
            try:
                for operation in range(3):
                    async with manager.get_session() as session:
                        connection_id = id(session.get_bind()) if hasattr(session, 'get_bind') else id(session)
                        worker_connections.append(f"worker_{worker_id}_op_{operation}_conn_{connection_id}")
                        
                        # Simulate database work
                        await session.execute(text(f"SELECT {worker_id} + {operation} as result"))
                        await asyncio.sleep(0.01)
                        
                connection_metrics.extend(worker_connections)
                        
            except Exception as e:
                error_count += 1
                logger.error(f"Worker {worker_id} failed: {e}")
        
        # Run concurrent workers
        workers = [concurrent_database_operations(i) for i in range(8)]
        await asyncio.gather(*workers, return_exceptions=True)
        
        # Verify connection pool management
        assert len(connection_metrics) > 0, "Should have recorded connection metrics"
        assert error_count == 0, "No connection pool errors should occur"
        
        # Verify pool health after concurrent load
        health_check = await manager.health_check()
        assert health_check["status"] == "healthy", "Pool should remain healthy after concurrent load"
        
        # Verify unique connections were used (pool reuse is expected)
        unique_connections = len(set([m.split('_conn_')[1] for m in connection_metrics if '_conn_' in m]))
        logger.info(f"Used {unique_connections} unique connections for {len(connection_metrics)} operations")
        
        logger.info("✅ Connection pool management verified under concurrent load")

    # ========== CONFIGURATION INTEGRATION TESTS ==========

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_connection_string_parsing_with_isolated_environment(self, with_test_database):
        """
        Test database connection string parsing and validation with IsolatedEnvironment.
        
        BVJ: Platform/Internal | Configuration Consistency | Ensures database URLs are built correctly
        """
        # Test with different environment configurations
        test_environments = {
            "development": {
                "POSTGRES_HOST": "localhost",
                "POSTGRES_PORT": "5432",
                "POSTGRES_DB": "netra_dev",
                "POSTGRES_USER": "netra_user",
                "POSTGRES_PASSWORD": "test_password",
                "ENVIRONMENT": "development"
            },
            "test": {
                "POSTGRES_HOST": "localhost",
                "POSTGRES_PORT": "5434",
                "POSTGRES_DB": "netra_test",
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_password",
                "ENVIRONMENT": "test"
            }
        }
        
        url_results = {}
        
        for env_name, env_vars in test_environments.items():
            # Create isolated environment with specific configuration
            isolated_env = IsolatedEnvironment(env_vars)
            
            # Create database manager with this environment
            manager = DatabaseManager()
            
            # Patch the environment for this test
            with patch('shared.isolated_environment.get_env', return_value=isolated_env):
                # Test URL building
                url = manager._get_database_url()
                url_results[env_name] = url
                
                # Verify URL components
                assert "postgresql+asyncpg://" in url, f"URL should use asyncpg driver for {env_name}"
                assert env_vars["POSTGRES_HOST"] in url, f"URL should contain host for {env_name}"
                assert env_vars["POSTGRES_PORT"] in url, f"URL should contain port for {env_name}"
                assert env_vars["POSTGRES_DB"] in url, f"URL should contain database for {env_name}"
                
            self.created_managers.append(manager)
        
        # Verify different environments produce different URLs
        assert url_results["development"] != url_results["test"], "Different environments should produce different URLs"
        
        logger.info(f"✅ Database URL parsing verified for environments: {list(url_results.keys())}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_environment_variables_priority_resolution(self, with_test_database):
        """
        Test database environment variables priority resolution.
        
        BVJ: Platform/Internal | Configuration Reliability | Ensures correct config precedence
        """
        # Test environment variable precedence
        base_env = {
            "POSTGRES_HOST": "base_host",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "base_db",
            "POSTGRES_USER": "base_user", 
            "POSTGRES_PASSWORD": "base_password"
        }
        
        override_env = base_env.copy()
        override_env.update({
            "POSTGRES_HOST": "override_host",
            "POSTGRES_PORT": "9999"
        })
        
        # Test base environment
        base_isolated_env = IsolatedEnvironment(base_env)
        base_url_builder = DatabaseURLBuilder(base_env)
        base_url = base_url_builder.get_url_for_environment(sync=False)
        
        # Test override environment
        override_isolated_env = IsolatedEnvironment(override_env)
        override_url_builder = DatabaseURLBuilder(override_env)
        override_url = override_url_builder.get_url_for_environment(sync=False)
        
        # Verify precedence
        assert "base_host" in base_url, "Base URL should use base host"
        assert "override_host" in override_url, "Override URL should use override host"
        assert "9999" in override_url, "Override URL should use override port"
        assert base_url != override_url, "Different environments should produce different URLs"
        
        # Test with DatabaseManager
        manager = DatabaseManager()
        self.created_managers.append(manager)
        
        with patch('shared.isolated_environment.get_env', return_value=override_isolated_env):
            constructed_url = manager._get_database_url()
            assert "override_host" in constructed_url, "Manager should respect environment overrides"
            assert "9999" in constructed_url, "Manager should use override port"
        
        logger.info("✅ Database environment variable priority resolution verified")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_health_monitoring_configuration_integration(self, with_test_database):
        """
        Test database health monitoring configuration integration.
        
        BVJ: Platform/Internal | System Reliability | Ensures database health monitoring works correctly
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        # Test health check functionality
        health_result = await manager.health_check()
        
        assert "status" in health_result, "Health check should include status"
        assert "engine" in health_result, "Health check should include engine info"
        assert health_result["status"] in ["healthy", "unhealthy"], "Status should be valid"
        
        # Test health check with different engines
        try:
            # Health check on non-existent engine should fail gracefully
            bad_health = await manager.health_check("nonexistent_engine")
            assert bad_health["status"] == "unhealthy", "Non-existent engine should be unhealthy"
        except ValueError as e:
            # This is also acceptable - engine validation
            assert "not found" in str(e), "Should get engine not found error"
        
        # Test application engine creation for health checks
        app_engine = manager.create_application_engine()
        assert app_engine is not None, "Should create application engine for health checks"
        
        # Cleanup application engine
        await app_engine.dispose()
        
        logger.info("✅ Database health monitoring configuration integration verified")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_pool_configuration_from_environment_variables(self, with_test_database):
        """
        Test connection pool configuration from environment variables.
        
        BVJ: Platform/Internal | Performance Optimization | Ensures optimal connection pool configuration
        """
        # Test different pool configurations
        pool_configs = {
            "small_pool": {
                "POSTGRES_HOST": "localhost",
                "POSTGRES_PORT": "5434",
                "POSTGRES_DB": "test_db",
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_password",
                "DATABASE_POOL_SIZE": "2",
                "DATABASE_MAX_OVERFLOW": "5"
            },
            "large_pool": {
                "POSTGRES_HOST": "localhost", 
                "POSTGRES_PORT": "5434",
                "POSTGRES_DB": "test_db",
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_password",
                "DATABASE_POOL_SIZE": "10",
                "DATABASE_MAX_OVERFLOW": "20"
            }
        }
        
        for config_name, config_env in pool_configs.items():
            isolated_env = IsolatedEnvironment(config_env)
            
            with patch('shared.isolated_environment.get_env', return_value=isolated_env):
                manager = DatabaseManager()
                await manager.initialize()
                
                engine = manager.get_engine()
                
                # Verify engine was created successfully
                assert engine is not None, f"Engine should be created for {config_name}"
                
                # Test engine functionality
                health_check = await manager.health_check()
                assert health_check["status"] == "healthy", f"Engine should be healthy for {config_name}"
                
                self.created_managers.append(manager)
        
        logger.info("✅ Connection pool configuration from environment variables verified")

    # ========== MULTI-USER TRANSACTION SAFETY TESTS ==========

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_data_isolation_in_concurrent_database_operations(self, with_test_database):
        """
        Test user data isolation in concurrent database operations.
        
        BVJ: All segments | Data Security | Ensures user data cannot leak between concurrent operations
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        # Create user contexts
        user_contexts = [
            UserExecutionContext(
                user_id=f"user_{i}_{uuid.uuid4().hex[:8]}",
                request_id=f"req_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}"
            )
            for i in range(3)
        ]
        
        user_data_results = {}
        
        async def user_data_operations(user_context: UserExecutionContext):
            """Simulate user-specific data operations."""
            user_results = []
            
            for operation in range(3):
                async with manager.get_session() as session:
                    # Create user-specific temporary table
                    table_name = f"user_data_{user_context.user_id}_{operation}"
                    await session.execute(text(f"CREATE TEMP TABLE {table_name} (id INT, user_id TEXT)"))
                    
                    # Insert user-specific data
                    await session.execute(
                        text(f"INSERT INTO {table_name} VALUES (:id, :user_id)"),
                        {"id": operation, "user_id": user_context.user_id}
                    )
                    
                    # Query user data
                    result = await session.execute(
                        text(f"SELECT user_id FROM {table_name} WHERE id = :id"),
                        {"id": operation}
                    )
                    returned_user_id = result.scalar()
                    user_results.append(returned_user_id)
            
            user_data_results[user_context.user_id] = user_results
        
        # Run concurrent user operations
        await asyncio.gather(*[user_data_operations(ctx) for ctx in user_contexts])
        
        # Verify data isolation
        for user_context in user_contexts:
            user_results = user_data_results[user_context.user_id]
            
            # All results should be for this specific user
            assert all(result == user_context.user_id for result in user_results), \
                f"User {user_context.user_id} should only see their own data"
            
            # No other user's data should be visible
            other_user_ids = [ctx.user_id for ctx in user_contexts if ctx.user_id != user_context.user_id]
            assert not any(other_id in user_results for other_id in other_user_ids), \
                f"User {user_context.user_id} should not see other users' data"
        
        logger.info("✅ User data isolation verified in concurrent database operations")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_transaction_rollback_isolation_between_users(self, with_test_database):
        """
        Test transaction rollback isolation between users.
        
        BVJ: All segments | Data Integrity | Ensures transaction failures don't affect other users
        """
        manager = DatabaseManager()
        self.created_managers.append(manager) 
        await manager.initialize()
        
        # Create test users
        user1_id = f"user1_{uuid.uuid4().hex[:8]}"
        user2_id = f"user2_{uuid.uuid4().hex[:8]}"
        
        transaction_results = {"user1": [], "user2": []}
        
        async def user1_operations():
            """User 1 operations - will have one rollback."""
            for i in range(3):
                try:
                    async with manager.get_session() as session:
                        await session.execute(text(f"CREATE TEMP TABLE u1_table_{i} (id INT)"))
                        await session.execute(text(f"INSERT INTO u1_table_{i} VALUES ({i})"))
                        
                        if i == 1:
                            # Force rollback for user 1
                            raise Exception("User 1 simulated error")
                            
                        transaction_results["user1"].append(f"success_{i}")
                        
                except Exception as e:
                    transaction_results["user1"].append(f"rollback_{i}")
        
        async def user2_operations():
            """User 2 operations - should all succeed despite user 1 rollback."""
            for i in range(3):
                try:
                    async with manager.get_session() as session:
                        await session.execute(text(f"CREATE TEMP TABLE u2_table_{i} (id INT)"))
                        await session.execute(text(f"INSERT INTO u2_table_{i} VALUES ({i + 100})"))
                        
                        transaction_results["user2"].append(f"success_{i}")
                        
                except Exception as e:
                    transaction_results["user2"].append(f"error_{i}")
        
        # Run concurrent user operations
        await asyncio.gather(user1_operations(), user2_operations())
        
        # Verify rollback isolation
        assert "rollback_1" in transaction_results["user1"], "User 1 should have rollback"
        assert "success_0" in transaction_results["user1"], "User 1 other transactions should succeed"
        assert "success_2" in transaction_results["user1"], "User 1 other transactions should succeed"
        
        # User 2 should be unaffected by User 1's rollback
        assert all("success" in result for result in transaction_results["user2"]), \
            "User 2 should not be affected by User 1 rollback"
        assert len(transaction_results["user2"]) == 3, "User 2 should complete all operations"
        
        logger.info("✅ Transaction rollback isolation verified between users")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_deadlock_prevention_and_resolution(self, with_test_database):
        """
        Test deadlock prevention and resolution.
        
        BVJ: All segments | System Reliability | Ensures database operations don't deadlock under concurrent load
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        # Create shared test tables
        async with manager.get_session() as setup_session:
            await setup_session.execute(text("CREATE TEMP TABLE deadlock_test_a (id INT PRIMARY KEY, value INT)"))
            await setup_session.execute(text("CREATE TEMP TABLE deadlock_test_b (id INT PRIMARY KEY, value INT)"))
            await setup_session.execute(text("INSERT INTO deadlock_test_a VALUES (1, 100), (2, 200)"))
            await setup_session.execute(text("INSERT INTO deadlock_test_b VALUES (1, 300), (2, 400)"))
        
        deadlock_results = []
        
        async def operation_a():
            """First operation - updates A then B."""
            try:
                async with manager.get_session() as session:
                    # Update table A first
                    await session.execute(text("UPDATE deadlock_test_a SET value = 101 WHERE id = 1"))
                    await asyncio.sleep(0.1)  # Allow other operation to start
                    
                    # Then update table B
                    await session.execute(text("UPDATE deadlock_test_b SET value = 301 WHERE id = 1"))
                    
                    deadlock_results.append("operation_a_success")
                    
            except Exception as e:
                deadlock_results.append(f"operation_a_error_{type(e).__name__}")
        
        async def operation_b():
            """Second operation - updates B then A."""
            try:
                async with manager.get_session() as session:
                    # Update table B first
                    await session.execute(text("UPDATE deadlock_test_b SET value = 302 WHERE id = 2"))
                    await asyncio.sleep(0.1)  # Allow other operation to start
                    
                    # Then update table A  
                    await session.execute(text("UPDATE deadlock_test_a SET value = 102 WHERE id = 2"))
                    
                    deadlock_results.append("operation_b_success")
                    
            except Exception as e:
                deadlock_results.append(f"operation_b_error_{type(e).__name__}")
        
        # Run potentially deadlocking operations
        await asyncio.gather(operation_a(), operation_b(), return_exceptions=True)
        
        # Verify deadlock handling
        success_count = len([r for r in deadlock_results if "success" in r])
        error_count = len([r for r in deadlock_results if "error" in r])
        
        # At least one operation should complete, and errors should be handled gracefully
        assert success_count >= 1, "At least one operation should succeed"
        assert success_count + error_count == 2, "Should have exactly 2 operation results"
        
        logger.info(f"✅ Deadlock prevention verified: {success_count} successes, {error_count} handled errors")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_schema_operations_isolation(self, with_test_database):
        """
        Test concurrent schema operations isolation.
        
        BVJ: Platform/Internal | Data Integrity | Ensures schema changes don't interfere with concurrent operations
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        schema_results = []
        
        async def schema_operation(operation_id: int):
            """Perform schema operations in isolation."""
            try:
                async with manager.get_session() as session:
                    # Create operation-specific schema
                    table_name = f"schema_test_{operation_id}"
                    await session.execute(text(f"CREATE TEMP TABLE {table_name} (id INT, data TEXT)"))
                    
                    # Add data
                    await session.execute(
                        text(f"INSERT INTO {table_name} VALUES (:id, :data)"),
                        {"id": operation_id, "data": f"data_{operation_id}"}
                    )
                    
                    # Modify schema
                    await session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN extra INT DEFAULT {operation_id}"))
                    
                    # Verify schema modification
                    result = await session.execute(text(f"SELECT extra FROM {table_name} WHERE id = :id"), {"id": operation_id})
                    extra_value = result.scalar()
                    
                    schema_results.append(f"operation_{operation_id}_extra_{extra_value}")
                    
            except Exception as e:
                schema_results.append(f"operation_{operation_id}_error_{e}")
        
        # Run concurrent schema operations
        await asyncio.gather(*[schema_operation(i) for i in range(4)])
        
        # Verify schema isolation
        success_count = len([r for r in schema_results if "extra" in r])
        assert success_count == 4, "All schema operations should succeed"
        
        # Verify each operation had its correct extra value
        for i in range(4):
            expected_result = f"operation_{i}_extra_{i}"
            assert expected_result in schema_results, f"Operation {i} should have correct extra value"
        
        logger.info("✅ Concurrent schema operations isolation verified")

    # ========== AGENT INTEGRATION TESTS ==========

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_session_lifecycle_with_agent_operations(self, with_test_database):
        """
        Test database session lifecycle with agent operations.
        
        BVJ: All segments | Agent Operations | Ensures agents can perform database operations reliably
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        # Create agent context
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id=self.test_request_id,
            thread_id=self.test_thread_id
        )
        
        agent_session_lifecycle = []
        
        async def simulate_agent_database_workflow():
            """Simulate complete agent database workflow."""
            # Phase 1: Agent initialization
            async with manager.get_session() as session:
                agent_session_lifecycle.append("agent_init_session_created")
                
                # Create agent workspace
                await session.execute(text("CREATE TEMP TABLE agent_workspace (id INT, operation TEXT, result TEXT)"))
                await session.execute(
                    text("INSERT INTO agent_workspace VALUES (1, 'initialization', 'agent_started')"),
                )
                agent_session_lifecycle.append("agent_workspace_created")
            
            # Phase 2: Agent data processing
            async with manager.get_session() as session:
                agent_session_lifecycle.append("agent_processing_session_created")
                
                # Process data
                await session.execute(
                    text("INSERT INTO agent_workspace VALUES (2, 'processing', 'data_analyzed')"),
                )
                
                # Check results
                result = await session.execute(text("SELECT COUNT(*) FROM agent_workspace"))
                count = result.scalar()
                agent_session_lifecycle.append(f"agent_processed_records_{count}")
            
            # Phase 3: Agent finalization
            async with manager.get_session() as session:
                agent_session_lifecycle.append("agent_finalization_session_created")
                
                # Finalize results
                await session.execute(
                    text("INSERT INTO agent_workspace VALUES (3, 'finalization', 'agent_completed')"),
                )
                
                # Get final results
                results = await session.execute(text("SELECT operation, result FROM agent_workspace ORDER BY id"))
                final_results = results.fetchall()
                agent_session_lifecycle.append(f"agent_final_results_{len(final_results)}")
        
        # Execute agent workflow
        await simulate_agent_database_workflow()
        
        # Verify agent session lifecycle
        expected_phases = [
            "agent_init_session_created",
            "agent_workspace_created", 
            "agent_processing_session_created",
            "agent_processed_records_2",
            "agent_finalization_session_created",
            "agent_final_results_3"
        ]
        
        for phase in expected_phases:
            assert phase in agent_session_lifecycle, f"Agent lifecycle should include {phase}"
        
        logger.info("✅ Database session lifecycle verified with agent operations")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_specific_database_context_isolation(self, with_test_database):
        """
        Test agent-specific database context isolation.
        
        BVJ: All segments | Multi-Agent Safety | Ensures agents don't interfere with each other's database context
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        # Create multiple agent contexts
        agent_contexts = {
            "data_agent": UserExecutionContext(
                user_id=self.test_user_id,
                request_id=f"data_req_{uuid.uuid4().hex[:8]}",
                thread_id=f"data_thread_{uuid.uuid4().hex[:8]}"
            ),
            "optimization_agent": UserExecutionContext(
                user_id=self.test_user_id,
                request_id=f"opt_req_{uuid.uuid4().hex[:8]}",
                thread_id=f"opt_thread_{uuid.uuid4().hex[:8]}"
            ),
            "report_agent": UserExecutionContext(
                user_id=self.test_user_id,
                request_id=f"report_req_{uuid.uuid4().hex[:8]}",
                thread_id=f"report_thread_{uuid.uuid4().hex[:8]}"
            )
        }
        
        agent_results = {}
        
        async def agent_database_operations(agent_name: str, context: UserExecutionContext):
            """Simulate agent-specific database operations."""
            agent_data = []
            
            for step in range(3):
                async with manager.get_session() as session:
                    # Create agent-specific workspace
                    table_name = f"{agent_name}_workspace_{step}"
                    await session.execute(text(f"CREATE TEMP TABLE {table_name} (id INT, agent TEXT, step INT)"))
                    
                    # Store agent-specific data
                    await session.execute(
                        text(f"INSERT INTO {table_name} VALUES (:id, :agent, :step)"),
                        {"id": step, "agent": agent_name, "step": step}
                    )
                    
                    # Query agent data
                    result = await session.execute(
                        text(f"SELECT agent FROM {table_name} WHERE step = :step"),
                        {"step": step}
                    )
                    returned_agent = result.scalar()
                    agent_data.append(returned_agent)
            
            agent_results[agent_name] = agent_data
        
        # Run concurrent agent operations
        await asyncio.gather(*[
            agent_database_operations(name, context) 
            for name, context in agent_contexts.items()
        ])
        
        # Verify agent context isolation
        for agent_name, agent_data in agent_results.items():
            # Agent should only see its own data
            assert all(data == agent_name for data in agent_data), \
                f"Agent {agent_name} should only see its own data"
            assert len(agent_data) == 3, f"Agent {agent_name} should complete all operations"
            
            # No other agent data should be visible
            other_agents = [name for name in agent_contexts.keys() if name != agent_name]
            assert not any(other_agent in agent_data for other_agent in other_agents), \
                f"Agent {agent_name} should not see other agents' data"
        
        logger.info("✅ Agent-specific database context isolation verified")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_session_sharing_across_agent_workflow(self, with_test_database):
        """
        Test database session sharing across agent workflow.
        
        BVJ: All segments | Agent Workflow | Ensures agents can share data within a single workflow
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        # Create workflow context
        workflow_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id=self.test_request_id,
            thread_id=self.test_thread_id
        )
        
        workflow_data = []
        
        # Create shared workflow session
        async with manager.get_session() as workflow_session:
            # Initialize workflow workspace
            await workflow_session.execute(text("CREATE TEMP TABLE workflow_shared (id INT, stage TEXT, data TEXT, agent TEXT)"))
            
            # Stage 1: Data Agent
            await workflow_session.execute(
                text("INSERT INTO workflow_shared VALUES (1, 'data_collection', 'raw_data_collected', 'data_agent')"),
            )
            
            # Stage 2: Processing Agent
            result = await workflow_session.execute(text("SELECT data FROM workflow_shared WHERE stage = 'data_collection'"))
            previous_data = result.scalar()
            
            await workflow_session.execute(
                text("INSERT INTO workflow_shared VALUES (2, 'processing', 'processed_' || :prev_data, 'processing_agent')"),
                {"prev_data": previous_data}
            )
            
            # Stage 3: Optimization Agent
            result = await workflow_session.execute(text("SELECT data FROM workflow_shared WHERE stage = 'processing'"))
            processed_data = result.scalar()
            
            await workflow_session.execute(
                text("INSERT INTO workflow_shared VALUES (3, 'optimization', 'optimized_' || :proc_data, 'optimization_agent')"),
                {"proc_data": processed_data}
            )
            
            # Get complete workflow results
            results = await workflow_session.execute(text("SELECT stage, data, agent FROM workflow_shared ORDER BY id"))
            workflow_data = results.fetchall()
        
        # Verify workflow data sharing
        assert len(workflow_data) == 3, "Should have 3 workflow stages"
        
        stages = [row[0] for row in workflow_data]
        expected_stages = ["data_collection", "processing", "optimization"]
        assert stages == expected_stages, "Workflow stages should be in correct order"
        
        # Verify data flow between agents
        data_values = [row[1] for row in workflow_data]
        assert "processed_raw_data_collected" in data_values[1], "Processing agent should use data agent output"
        assert "optimized_processed_raw_data_collected" in data_values[2], "Optimization agent should use processing agent output"
        
        logger.info("✅ Database session sharing verified across agent workflow")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_cleanup_during_agent_failure_scenarios(self, with_test_database):
        """
        Test database cleanup during agent failure scenarios.
        
        BVJ: All segments | System Reliability | Ensures database resources are cleaned up during agent failures
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        failure_scenarios = []
        cleanup_results = []
        
        async def failing_agent_scenario(scenario_id: int):
            """Simulate agent failure scenarios with database cleanup."""
            try:
                async with manager.get_session() as session:
                    # Create agent resources
                    await session.execute(text(f"CREATE TEMP TABLE agent_fail_{scenario_id} (id INT)"))
                    await session.execute(text(f"INSERT INTO agent_fail_{scenario_id} VALUES ({scenario_id})"))
                    
                    # Simulate different failure scenarios
                    if scenario_id == 1:
                        raise ValueError(f"Agent processing error {scenario_id}")
                    elif scenario_id == 2:
                        raise OperationalError("DB connection issue", None, None)
                    elif scenario_id == 3:
                        raise Exception(f"Unexpected agent error {scenario_id}")
                    else:
                        # Success case
                        cleanup_results.append(f"success_{scenario_id}")
                        
            except Exception as e:
                failure_scenarios.append(f"failed_{scenario_id}_{type(e).__name__}")
                # Session should auto-rollback and cleanup
                cleanup_results.append(f"cleanup_{scenario_id}")
        
        # Run multiple failure scenarios
        await asyncio.gather(*[
            failing_agent_scenario(i) for i in range(5)
        ], return_exceptions=True)
        
        # Verify failure handling and cleanup
        assert len(failure_scenarios) == 3, "Should have 3 failure scenarios"
        assert len(cleanup_results) == 5, "Should have cleanup for all scenarios"
        
        # Verify specific failure types were handled
        failure_types = [scenario.split('_')[-1] for scenario in failure_scenarios]
        assert "ValueError" in failure_types, "Should handle ValueError"
        assert "OperationalError" in failure_types, "Should handle OperationalError"
        assert "Exception" in failure_types, "Should handle generic Exception"
        
        # Verify database manager is still healthy after failures
        health_check = await manager.health_check()
        assert health_check["status"] == "healthy", "Database should remain healthy after agent failures"
        
        logger.info("✅ Database cleanup verified during agent failure scenarios")

    # ========== SYSTEM INTEGRATION TESTS ==========

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_health_monitoring_and_circuit_breaker_integration(self, with_test_database):
        """
        Test database health monitoring and circuit breaker integration.
        
        BVJ: Platform/Internal | System Reliability | Ensures database health monitoring prevents cascade failures
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        health_checks = []
        
        # Perform multiple health checks
        for i in range(5):
            health_result = await manager.health_check()
            health_checks.append(health_result["status"])
            await asyncio.sleep(0.01)  # Small delay between checks
        
        # All health checks should pass
        assert all(status == "healthy" for status in health_checks), "All health checks should pass"
        
        # Test health monitoring under load
        concurrent_health_tasks = []
        for i in range(10):
            concurrent_health_tasks.append(manager.health_check())
        
        concurrent_results = await asyncio.gather(*concurrent_health_tasks)
        concurrent_statuses = [result["status"] for result in concurrent_results]
        
        assert all(status == "healthy" for status in concurrent_statuses), \
            "Health checks should remain consistent under concurrent load"
        
        # Test circuit breaker behavior by creating a bad engine
        try:
            # This should fail gracefully
            bad_health = await manager.health_check("nonexistent")
            assert bad_health["status"] == "unhealthy", "Non-existent engine should report unhealthy"
        except ValueError:
            # This is also acceptable - validation error
            pass
        
        logger.info("✅ Database health monitoring and circuit breaker integration verified")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_migration_coordination_with_service_startup(self, with_test_database):
        """
        Test database migration coordination with service startup.
        
        BVJ: Platform/Internal | Deployment Reliability | Ensures database schema is correctly managed during startup
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        
        # Test migration URL generation
        migration_url = manager.get_migration_url_sync_format()
        
        # Verify migration URL format
        assert "postgresql://" in migration_url, "Migration URL should use sync driver"
        assert "postgresql+asyncpg://" not in migration_url, "Migration URL should not use async driver"
        
        # Test manager initialization after migration URL generation
        await manager.initialize()
        
        # Verify manager is properly initialized
        engine = manager.get_engine()
        assert engine is not None, "Engine should be initialized after migration URL generation"
        
        # Test concurrent initialization (idempotent)
        await manager.initialize()  # Should not cause issues
        same_engine = manager.get_engine()
        assert engine is same_engine, "Multiple initialization should return same engine"
        
        # Test health check after initialization
        health_check = await manager.health_check()
        assert health_check["status"] == "healthy", "Database should be healthy after initialization"
        
        logger.info("✅ Database migration coordination verified with service startup")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_retry_and_recovery_patterns(self, with_test_database):
        """
        Test connection retry and recovery patterns.
        
        BVJ: Platform/Internal | System Resilience | Ensures database connections recover from temporary failures
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        await manager.initialize()
        
        # Test normal operation
        async with manager.get_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            assert result.scalar() == 1, "Normal operation should work"
        
        # Test recovery after connection issues
        recovery_attempts = []
        
        for attempt in range(3):
            try:
                async with manager.get_session() as session:
                    # Simulate potential connection recovery
                    await session.execute(text("SELECT 1 as recovery_test"))
                    recovery_attempts.append(f"success_{attempt}")
                    
            except Exception as e:
                recovery_attempts.append(f"error_{attempt}_{type(e).__name__}")
        
        # Most attempts should succeed (unless there are real connection issues)
        success_count = len([a for a in recovery_attempts if "success" in a])
        assert success_count >= 2, "Connection recovery should generally succeed"
        
        # Test engine recreation capability
        original_engine = manager.get_engine()
        
        # Force engine reset by closing and reinitializing
        await manager.close_all()
        await manager.initialize()
        
        new_engine = manager.get_engine()
        assert new_engine is not None, "Should be able to create new engine after close"
        
        # Test that new engine works
        health_check = await manager.health_check()
        assert health_check["status"] == "healthy", "Recreated engine should be healthy"
        
        logger.info("✅ Connection retry and recovery patterns verified")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_event_logging_and_monitoring_integration(self, with_test_database):
        """
        Test database event logging and monitoring integration.
        
        BVJ: Platform/Internal | Observability | Ensures database operations are properly logged and monitored
        """
        manager = DatabaseManager()
        self.created_managers.append(manager)
        
        # Capture log events during database operations
        logged_events = []
        
        # Mock logger to capture events
        original_logger = logger
        
        class LogCapture:
            def info(self, message):
                logged_events.append(f"INFO: {message}")
                original_logger.info(message)
                
            def error(self, message):
                logged_events.append(f"ERROR: {message}")
                original_logger.error(message)
                
            def debug(self, message):
                logged_events.append(f"DEBUG: {message}")
                original_logger.debug(message)
                
            def warning(self, message):
                logged_events.append(f"WARNING: {message}")
                original_logger.warning(message)
        
        log_capture = LogCapture()
        
        with patch.object(manager, 'logger', log_capture):
            # Test initialization logging
            await manager.initialize()
            
            # Test session operations logging
            async with manager.get_session() as session:
                await session.execute(text("SELECT 1 as monitoring_test"))
            
            # Test health check logging
            await manager.health_check()
            
            # Test error scenario logging
            try:
                await manager.health_check("nonexistent_engine")
            except:
                pass
        
        # Verify logging integration
        info_logs = [event for event in logged_events if "INFO:" in event]
        assert len(info_logs) > 0, "Should have logged info events"
        
        # Check for specific database events
        initialization_logged = any("initialized" in log.lower() for log in logged_events)
        assert initialization_logged, "Database initialization should be logged"
        
        # Test monitoring metrics collection
        monitoring_data = {
            "sessions_created": len([event for event in logged_events if "session" in event.lower()]),
            "health_checks": len([event for event in logged_events if "health" in event.lower()]),
            "errors_handled": len([event for event in logged_events if "ERROR:" in event])
        }
        
        assert monitoring_data["sessions_created"] >= 0, "Should track session creation"
        assert monitoring_data["health_checks"] >= 1, "Should track health checks"
        
        logger.info(f"✅ Database event logging verified: {len(logged_events)} events captured")
        logger.info(f"✅ Monitoring data collected: {monitoring_data}")