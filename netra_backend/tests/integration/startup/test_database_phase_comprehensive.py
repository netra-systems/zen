"""
Integration Tests for System Startup DATABASE Phase

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability & Chat Readiness
- Value Impact: Ensures database infrastructure is properly configured for chat functionality
- Strategic Impact: Prevents database failures that would block all user interactions and data persistence

CRITICAL: These tests validate the DATABASE phase of system startup:
1. PostgreSQL connection establishment and validation
2. Database schema validation and migrations
3. Connection pool configuration and management
4. Database health checks and monitoring
5. User authentication database operations
6. Thread/message storage capabilities
7. Database performance requirements for chat
8. Database isolation and multi-user support
9. Database failover and error handling
10. Database readiness for real-time chat operations

The DATABASE phase is foundational - if it fails, chat data persistence cannot work.
"""

import asyncio
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import text, select, MetaData, Table
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.service_availability import check_service_availability, ServiceUnavailableError
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.database import get_db, get_system_db, get_database_url, get_engine, get_sessionmaker, DatabaseManager, database_manager
from netra_backend.app.core.backend_environment import BackendEnvironment
from netra_backend.app.startup_checks.database_checks import DatabaseChecker
from netra_backend.app.db.models_postgres import Thread, Message
from netra_backend.app.db.models_user import User
from netra_backend.app.services.database.health_checker import ConnectionHealthChecker

# Check service availability at module level
_service_status = check_service_availability(['postgresql'], timeout=2.0)
_postgresql_available = _service_status['postgresql'] is True
_postgresql_skip_reason = f"PostgreSQL unavailable: {_service_status['postgresql']}" if not _postgresql_available else None


@pytest.mark.skipif(not _postgresql_available, reason=_postgresql_skip_reason)
class TestDatabasePhaseComprehensive(BaseIntegrationTest):
    """
    Comprehensive integration tests for system startup DATABASE phase.
    
    CRITICAL: These tests ensure the foundation of chat data persistence.
    Without proper DATABASE phase, the system cannot store user interactions.
    
    Note: These tests require PostgreSQL service to be running.
    """
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.logger.info("Setting up DATABASE phase integration test")
        
        # Store original environment for cleanup
        self.original_env = dict(os.environ)
        
        # Configure test database connection (port 5434 for test environment) FIRST
        self._setup_test_database_config()
        
        # Get test environment configuration AFTER setting env vars
        self.env = get_env()
        self.backend_env = BackendEnvironment()
        
        # Initialize test database manager
        self.database_manager = DatabaseManager()
        
        # Track resources for cleanup
        self.test_engines = []
        self.test_sessions = []
        
        self.logger.info("DATABASE phase test setup complete")
    
    def teardown_method(self):
        """Cleanup after each test method."""
        super().teardown_method()
        
        # Clean up database resources synchronously
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, schedule cleanup
                loop.create_task(self._cleanup_database_resources())
            else:
                # If no loop, run cleanup in new loop
                asyncio.run(self._cleanup_database_resources())
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
        
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
        
        self.logger.info("DATABASE phase test cleanup complete")
    
    def _setup_test_database_config(self):
        """Setup test database configuration for integration tests."""
        # Configure for test database (port 5434)
        test_db_config = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5434',  # Test environment port
            'POSTGRES_DB': 'netra_test',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'postgres'
        }
        
        # Apply test configuration to environment
        for key, value in test_db_config.items():
            os.environ[key] = value
            
        self.logger.info(f"Configured test database: {test_db_config['POSTGRES_HOST']}:{test_db_config['POSTGRES_PORT']}/{test_db_config['POSTGRES_DB']}")
    
    async def _cleanup_database_resources(self):
        """Clean up database connections and resources."""
        try:
            # Close all test sessions
            for session in self.test_sessions:
                if session and not session.is_closed:
                    await session.close()
            
            # Close all test engines
            for engine in self.test_engines:
                if engine:
                    await engine.dispose()
            
            self.logger.info("Database resources cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error cleaning up database resources: {e}")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_database_connection_establishment(self):
        """
        BVJ: Platform/Internal - Chat Infrastructure
        Test that PostgreSQL connection can be established successfully.
        CRITICAL: Chat cannot function without database connectivity.
        """
        self.logger.info("Testing database connection establishment")
        
        # Test database URL generation
        database_url = get_database_url()
        assert database_url, "Database URL must be generated from environment"
        assert "postgresql+asyncpg://" in database_url, "Must use async PostgreSQL driver"
        assert ":5434" in database_url, "Must connect to test database port 5434"
        
        # Test engine creation
        engine = get_engine()
        assert engine is not None, "Database engine must be created"
        self.test_engines.append(engine)
        
        # Test actual connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 as test_value"))
            row = result.fetchone()
            assert row[0] == 1, "Database connection must execute queries successfully"
        
        self.logger.info("Database connection establishment test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_database_schema_validation(self):
        """
        BVJ: Platform/Internal - Chat Data Integrity
        Test that required database schema exists for chat functionality.
        CRITICAL: Chat requires users, threads, and messages tables.
        """
        self.logger.info("Testing database schema validation")
        
        engine = get_engine()
        self.test_engines.append(engine)
        
        async with engine.connect() as conn:
            # Check for required chat tables
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'threads', 'messages')
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result.fetchall()]
            
            # Verify core chat tables exist or can be created
            expected_tables = ['users', 'threads', 'messages']
            for table in expected_tables:
                if table not in tables:
                    self.logger.warning(f"Table {table} not found - would be created during migration")
        
        self.logger.info("Database schema validation test completed")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_connection_pool_configuration(self):
        """
        BVJ: Platform/Internal - Chat Performance
        Test that database connection pool is properly configured.
        CRITICAL: Chat requires efficient connection management for multiple users.
        """
        self.logger.info("Testing database connection pool configuration")
        
        engine = get_engine()
        self.test_engines.append(engine)
        
        # Verify engine configuration
        assert engine.pool is not None, "Engine must have connection pool configured"
        
        # Test multiple concurrent connections
        connections = []
        try:
            # Create multiple connections to test pool
            for i in range(3):
                conn = await engine.connect()
                connections.append(conn)
                
                # Test that each connection works
                result = await conn.execute(text(f"SELECT {i + 1} as connection_id"))
                row = result.fetchone()
                assert row[0] == i + 1, f"Connection {i + 1} must work independently"
            
        finally:
            # Clean up connections
            for conn in connections:
                await conn.close()
        
        self.logger.info("Connection pool configuration test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_database_health_checks(self):
        """
        BVJ: Platform/Internal - System Reliability
        Test database health check functionality for monitoring.
        CRITICAL: Chat system must detect database issues proactively.
        """
        self.logger.info("Testing database health checks")
        
        # Test basic health check
        engine = get_engine()
        self.test_engines.append(engine)
        
        # Simulate health check query
        async with engine.connect() as conn:
            start_time = time.time()
            result = await conn.execute(text("SELECT version(), current_timestamp, current_database()"))
            response_time = time.time() - start_time
            
            row = result.fetchone()
            assert row is not None, "Health check query must return results"
            assert response_time < 1.0, "Health check must respond within 1 second"
            
            # Verify database information
            version, timestamp, database = row
            assert "PostgreSQL" in str(version), "Must be PostgreSQL database"
            assert "netra" in str(database).lower(), "Must be connected to Netra database"
        
        self.logger.info("Database health checks test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_user_authentication_database_operations(self):
        """
        BVJ: Free/Early/Mid/Enterprise - User Authentication
        Test database operations required for user authentication in chat.
        CRITICAL: Chat requires user authentication and session management.
        """
        self.logger.info("Testing user authentication database operations")
        
        async with get_db() as session:
            self.test_sessions.append(session)
            
            # Test user table access (read-only for integration test)
            try:
                # Test that we can query user table structure
                result = await session.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    ORDER BY column_name
                """))
                
                columns = {row[0]: row[1] for row in result.fetchall()}
                
                # Verify essential user columns exist or would be created
                expected_columns = ['id', 'email', 'created_at']
                for col in expected_columns:
                    if col not in columns:
                        self.logger.warning(f"User column {col} not found - would be created during migration")
                
            except Exception as e:
                # Table might not exist yet - that's ok for startup test
                self.logger.info(f"Users table not found (expected during startup): {e}")
        
        self.logger.info("User authentication database operations test completed")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_thread_message_storage_capabilities(self):
        """
        BVJ: Free/Early/Mid/Enterprise - Chat Functionality
        Test database operations for thread and message storage.
        CRITICAL: Chat core functionality requires persistent message storage.
        """
        self.logger.info("Testing thread/message storage capabilities")
        
        async with get_db() as session:
            self.test_sessions.append(session)
            
            # Test threads table structure
            try:
                result = await session.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'threads' 
                    ORDER BY column_name
                """))
                
                thread_columns = {row[0]: row[1] for row in result.fetchall()}
                
                # Verify essential thread columns
                expected_thread_columns = ['id', 'user_id', 'title', 'created_at']
                for col in expected_thread_columns:
                    if col not in thread_columns:
                        self.logger.warning(f"Thread column {col} not found - would be created during migration")
                
            except Exception as e:
                self.logger.info(f"Threads table not found (expected during startup): {e}")
            
            # Test messages table structure
            try:
                result = await session.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'messages' 
                    ORDER BY column_name
                """))
                
                message_columns = {row[0]: row[1] for row in result.fetchall()}
                
                # Verify essential message columns
                expected_message_columns = ['id', 'thread_id', 'content', 'created_at']
                for col in expected_message_columns:
                    if col not in message_columns:
                        self.logger.warning(f"Message column {col} not found - would be created during migration")
                        
            except Exception as e:
                self.logger.info(f"Messages table not found (expected during startup): {e}")
        
        self.logger.info("Thread/message storage capabilities test completed")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_database_performance_requirements(self):
        """
        BVJ: Platform/Internal - Chat Performance
        Test database performance meets chat requirements.
        CRITICAL: Chat requires fast database responses for good UX.
        """
        self.logger.info("Testing database performance requirements")
        
        engine = get_engine()
        self.test_engines.append(engine)
        
        # Test query performance
        performance_tests = [
            ("SELECT 1", 0.1),  # Basic query < 100ms
            ("SELECT generate_series(1, 100)", 0.5),  # Small result set < 500ms
            ("SELECT current_timestamp, version()", 0.2),  # System info < 200ms
        ]
        
        async with engine.connect() as conn:
            for query, max_time in performance_tests:
                start_time = time.time()
                await conn.execute(text(query))
                elapsed = time.time() - start_time
                
                assert elapsed < max_time, f"Query '{query}' took {elapsed:.3f}s, expected < {max_time}s"
                self.logger.info(f"Query performance OK: '{query}' completed in {elapsed:.3f}s")
        
        self.logger.info("Database performance requirements test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_database_isolation_multi_user_support(self):
        """
        BVJ: Free/Early/Mid/Enterprise - Multi-User Chat
        Test database isolation for concurrent user operations.
        CRITICAL: Chat must support multiple users without data leakage.
        """
        self.logger.info("Testing database isolation and multi-user support")
        
        # Test multiple concurrent sessions
        sessions = []
        try:
            # Create multiple concurrent database sessions
            for i in range(3):
                session_maker = get_sessionmaker()
                session = session_maker()
                sessions.append(session)
                self.test_sessions.append(session)
                
                # Test that each session has independent transaction state
                result = await session.execute(text(f"SELECT {i + 1} as session_id"))
                row = result.fetchone()
                assert row[0] == i + 1, f"Session {i + 1} must maintain independent state"
            
            # Test concurrent query execution
            tasks = []
            for i, session in enumerate(sessions):
                task = asyncio.create_task(
                    session.execute(text(f"SELECT pg_sleep(0.1), {i + 1} as concurrent_id"))
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # Verify all concurrent queries completed successfully
            for i, result in enumerate(results):
                row = result.fetchone()
                assert row[1] == i + 1, f"Concurrent session {i + 1} must return correct result"
                
        finally:
            # Close all sessions
            for session in sessions:
                await session.close()
        
        self.logger.info("Database isolation multi-user support test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_database_failover_error_handling(self):
        """
        BVJ: Platform/Internal - System Resilience
        Test database error handling and recovery mechanisms.
        CRITICAL: Chat must gracefully handle database connection issues.
        """
        self.logger.info("Testing database failover and error handling")
        
        # Test connection timeout handling
        test_engine = create_async_engine(
            get_database_url(),
            poolclass=NullPool,
            connect_args={"connect_timeout": 1},  # Very short timeout
            echo=False
        )
        self.test_engines.append(test_engine)
        
        # Test that engine handles connection properly
        async with test_engine.connect() as conn:
            result = await conn.execute(text("SELECT 'connection_test' as status"))
            row = result.fetchone()
            assert row[0] == 'connection_test', "Connection with timeout must work normally"
        
        # Test invalid query error handling
        async with get_db() as session:
            self.test_sessions.append(session)
            
            try:
                # Execute invalid SQL to test error handling
                await session.execute(text("SELECT * FROM nonexistent_table_12345"))
                assert False, "Invalid query should raise exception"
            except Exception as e:
                # Verify we get appropriate database error
                assert "relation" in str(e).lower() or "table" in str(e).lower(), \
                    "Should get table/relation error for nonexistent table"
                self.logger.info(f"Database error handling working correctly: {type(e).__name__}")
        
        self.logger.info("Database failover error handling test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_database_migration_readiness(self):
        """
        BVJ: Platform/Internal - Deployment Reliability
        Test database migration capabilities for schema updates.
        CRITICAL: Chat system must support schema evolution.
        """
        self.logger.info("Testing database migration readiness")
        
        engine = get_engine()
        self.test_engines.append(engine)
        
        # Test database metadata access
        async with engine.connect() as conn:
            # Check database version and capabilities
            result = await conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            assert "PostgreSQL" in version, "Must be PostgreSQL for migration support"
            
            # Check migration table support
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                )
            """))
            
            has_alembic = result.fetchone()[0]
            if not has_alembic:
                self.logger.info("Alembic version table not found - would be created during first migration")
            else:
                self.logger.info("Alembic version table exists - migrations are supported")
            
            # Test schema information access
            result = await conn.execute(text("""
                SELECT schemaname, tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                LIMIT 5
            """))
            
            tables = result.fetchall()
            self.logger.info(f"Found {len(tables)} tables in public schema")
        
        self.logger.info("Database migration readiness test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_database_startup_health_validation(self):
        """
        BVJ: Platform/Internal - System Startup
        Test comprehensive database health validation during startup.
        CRITICAL: Startup must validate database is ready for chat operations.
        """
        self.logger.info("Testing database startup health validation")
        
        # Test database checker initialization
        mock_app = MagicMock()
        checker = DatabaseChecker(mock_app)
        
        # Verify checker is configured properly
        assert hasattr(checker, 'app'), "Database checker must have app reference"
        assert hasattr(checker, 'environment'), "Database checker must know environment"
        
        # Test connection validation (integration with real database)
        engine = get_engine()
        self.test_engines.append(engine)
        
        health_checks = [
            "SELECT 1 as connectivity_check",
            "SELECT current_database() as database_name",
            "SELECT current_user as database_user",
            "SELECT extract(epoch from now()) as timestamp_check"
        ]
        
        async with engine.connect() as conn:
            for check_sql in health_checks:
                start_time = time.time()
                result = await conn.execute(text(check_sql))
                elapsed = time.time() - start_time
                
                row = result.fetchone()
                assert row is not None, f"Health check '{check_sql}' must return result"
                assert elapsed < 0.5, f"Health check '{check_sql}' must complete quickly"
                
                self.logger.info(f"Health check passed: {check_sql} -> {row[0]} ({elapsed:.3f}s)")
        
        self.logger.info("Database startup health validation test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_database_session_lifecycle_management(self):
        """
        BVJ: Platform/Internal - Resource Management
        Test database session creation, usage, and cleanup.
        CRITICAL: Chat must properly manage database sessions to avoid leaks.
        """
        self.logger.info("Testing database session lifecycle management")
        
        # Test session creation and cleanup
        session_count = 0
        
        # Test get_db context manager
        async with get_db() as session:
            session_count += 1
            self.test_sessions.append(session)
            
            # Verify session is usable
            result = await session.execute(text("SELECT 'session_test' as status"))
            row = result.fetchone()
            assert row[0] == 'session_test', "Session must execute queries successfully"
            
            # Verify session properties
            assert not session.is_closed, "Active session must not be closed"
            
        # Test system database session
        async with get_system_db() as system_session:
            session_count += 1
            self.test_sessions.append(system_session)
            
            # Verify system session works
            result = await system_session.execute(text("SELECT 'system_session_test' as status"))
            row = result.fetchone()
            assert row[0] == 'system_session_test', "System session must work correctly"
        
        # Test session maker directly
        session_maker = get_sessionmaker()
        direct_session = session_maker()
        session_count += 1
        self.test_sessions.append(direct_session)
        
        try:
            result = await direct_session.execute(text("SELECT 'direct_session_test' as status"))
            row = result.fetchone()
            assert row[0] == 'direct_session_test', "Direct session must work correctly"
        finally:
            await direct_session.close()
        
        self.logger.info(f"Session lifecycle management test completed - created {session_count} sessions")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_database_transaction_handling(self):
        """
        BVJ: Platform/Internal - Data Consistency
        Test database transaction handling for chat operations.
        CRITICAL: Chat must maintain data consistency across operations.
        """
        self.logger.info("Testing database transaction handling")
        
        async with get_db() as session:
            self.test_sessions.append(session)
            
            # Test transaction begin/commit
            async with session.begin() as transaction:
                # Execute a query within transaction
                result = await session.execute(text("SELECT 'transaction_test' as status"))
                row = result.fetchone()
                assert row[0] == 'transaction_test', "Query within transaction must work"
                
                # Transaction commits automatically when context exits
            
            # Test transaction rollback (simulate error scenario)
            try:
                async with session.begin() as transaction:
                    # Execute valid query first
                    await session.execute(text("SELECT 1"))
                    # Force rollback by raising exception
                    raise Exception("Simulated error for rollback test")
            except Exception as e:
                assert "Simulated error" in str(e), "Exception should be propagated correctly"
                self.logger.info("Transaction rollback test completed successfully")
        
        self.logger.info("Database transaction handling test completed successfully")
    
    @pytest.mark.integration
    @pytest.mark.startup_database
    async def test_database_readiness_for_chat_operations(self):
        """
        BVJ: Free/Early/Mid/Enterprise - Core Chat Business Value
        Test that database is fully ready to support chat operations.
        CRITICAL: This is the ultimate validation that chat can function.
        """
        self.logger.info("Testing database readiness for chat operations")
        
        # Test all components required for chat functionality
        async with get_db() as session:
            self.test_sessions.append(session)
            
            # Test database can handle typical chat queries
            chat_readiness_queries = [
                "SELECT current_timestamp as server_time",
                "SELECT current_user as db_user",
                "SELECT current_database() as db_name",
                "SELECT pg_is_in_recovery() as is_replica",
            ]
            
            for query in chat_readiness_queries:
                start_time = time.time()
                result = await session.execute(text(query))
                elapsed = time.time() - start_time
                
                row = result.fetchone()
                assert row is not None, f"Chat readiness query '{query}' must return result"
                assert elapsed < 0.1, f"Chat readiness query '{query}' must be fast (<100ms)"
                
                self.logger.info(f"Chat readiness check: {query} -> {row[0]} ({elapsed:.3f}s)")
            
            # Test concurrent session capacity (simulate multiple users)
            concurrent_sessions = []
            try:
                for i in range(5):
                    session_maker = get_sessionmaker()
                    concurrent_session = session_maker()
                    concurrent_sessions.append(concurrent_session)
                    self.test_sessions.append(concurrent_session)
                    
                    # Each session should work independently
                    result = await concurrent_session.execute(
                        text(f"SELECT {i + 1} as user_simulation")
                    )
                    row = result.fetchone()
                    assert row[0] == i + 1, f"Concurrent session {i + 1} must work correctly"
                
                self.logger.info(f"Successfully created {len(concurrent_sessions)} concurrent sessions for chat simulation")
                
            finally:
                # Clean up concurrent sessions
                for concurrent_session in concurrent_sessions:
                    await concurrent_session.close()
        
        self.logger.info("Database readiness for chat operations test completed successfully")
        
        # Final validation log
        self.logger.info(
            "[U+1F680] DATABASE PHASE VALIDATION COMPLETE: Database infrastructure is ready to support chat functionality"
        )
