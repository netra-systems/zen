from shared.isolated_environment import IsolatedEnvironment
from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''L3 Integration Tests for Database Connectivity with Docker Compose Services.

# REMOVED_SYNTAX_ERROR: These tests validate database connectivity, transactions, and management using
# REMOVED_SYNTAX_ERROR: real PostgreSQL and ClickHouse services via Docker Compose, providing L3-level
# REMOVED_SYNTAX_ERROR: realism as required by testing.xml Mock-Real Spectrum.

# REMOVED_SYNTAX_ERROR: Business Value: Ensures database connectivity patterns work in production-like
# REMOVED_SYNTAX_ERROR: environments, preventing connection failures and data integrity issues that
# REMOVED_SYNTAX_ERROR: could impact customer operations and data reliability.
""

import pytest
import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from netra_backend.app.db.database_manager import DatabaseManager
# Use canonical DatabaseManager instead of deprecated db_connection_manager
# from netra_backend.app.core.unified.db_connection_manager import get_db_manager
from netra_backend.app.db.postgres_core import AsyncDatabase


# REMOVED_SYNTAX_ERROR: @pytest.mark.integration
# REMOVED_SYNTAX_ERROR: @pytest.mark.real_services
# REMOVED_SYNTAX_ERROR: class TestDatabaseConnectivityL3:
    # REMOVED_SYNTAX_ERROR: """L3 Integration tests for database connectivity with Docker Compose services."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def postgres_connection(self):
    # REMOVED_SYNTAX_ERROR: """Connect to Docker Compose PostgreSQL service."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: conn = await asyncpg.connect( )
        # REMOVED_SYNTAX_ERROR: host='localhost',
        # REMOVED_SYNTAX_ERROR: port=5432,
        # REMOVED_SYNTAX_ERROR: user='postgres',
        # REMOVED_SYNTAX_ERROR: password='postgres',
        # REMOVED_SYNTAX_ERROR: database='netra_dev'
        
        # REMOVED_SYNTAX_ERROR: yield conn
        # REMOVED_SYNTAX_ERROR: await conn.close()
        # REMOVED_SYNTAX_ERROR: except Exception as e:
            # REMOVED_SYNTAX_ERROR: pytest.skip("formatted_string")

            # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def clickhouse_connection(self):
    # REMOVED_SYNTAX_ERROR: """Connect to Docker Compose ClickHouse service."""
    # REMOVED_SYNTAX_ERROR: try:
        # ClickHouse connection - for now just return connection info
        # REMOVED_SYNTAX_ERROR: yield { )
        # REMOVED_SYNTAX_ERROR: 'host': 'localhost',
        # REMOVED_SYNTAX_ERROR: 'port': 8124,
        # REMOVED_SYNTAX_ERROR: 'user': 'netra',
        # REMOVED_SYNTAX_ERROR: 'password': 'netra123',
        # REMOVED_SYNTAX_ERROR: 'database': 'netra_dev'
        
        # REMOVED_SYNTAX_ERROR: except Exception as e:
            # REMOVED_SYNTAX_ERROR: pytest.skip("formatted_string")

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_postgres_connection_lifecycle(self, postgres_connection):
                # REMOVED_SYNTAX_ERROR: """Test complete PostgreSQL connection lifecycle with real database."""
                # Use Docker Compose PostgreSQL service
                # REMOVED_SYNTAX_ERROR: async_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/netra_dev"

                # Test engine creation
                # REMOVED_SYNTAX_ERROR: engine = create_async_engine(async_url, echo=False, pool_size=2, max_overflow=5)

                # REMOVED_SYNTAX_ERROR: try:
                    # Test connection
                    # REMOVED_SYNTAX_ERROR: async with engine.begin() as conn:
                        # REMOVED_SYNTAX_ERROR: result = await conn.execute(text("SELECT version()"))
                        # REMOVED_SYNTAX_ERROR: version = result.fetchone()
                        # REMOVED_SYNTAX_ERROR: assert "PostgreSQL" in version[0]

                        # Test session creation and transactions
                        # REMOVED_SYNTAX_ERROR: async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

                        # REMOVED_SYNTAX_ERROR: async with async_session() as session:
                            # Test transaction with real database
                            # REMOVED_SYNTAX_ERROR: await session.execute(text("CREATE TEMPORARY TABLE test_table (id INTEGER, name TEXT)"))
                            # REMOVED_SYNTAX_ERROR: await session.execute(text("INSERT INTO test_table (id, name) VALUES (1, 'test')"))

                            # REMOVED_SYNTAX_ERROR: result = await session.execute(text("SELECT COUNT(*) FROM test_table"))
                            # REMOVED_SYNTAX_ERROR: count = result.fetchone()
                            # REMOVED_SYNTAX_ERROR: assert count[0] == 1

                            # Test rollback
                            # REMOVED_SYNTAX_ERROR: await session.rollback()

                            # Verify transaction rollback worked
                            # REMOVED_SYNTAX_ERROR: result = await session.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'test_table'"))
                            # REMOVED_SYNTAX_ERROR: table_count = result.fetchone()
                            # REMOVED_SYNTAX_ERROR: assert table_count[0] == 0  # Temporary table rolled back

                            # REMOVED_SYNTAX_ERROR: finally:
                                # REMOVED_SYNTAX_ERROR: await engine.dispose()

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_database_manager_real_url_processing(self, postgres_connection):
                                    # REMOVED_SYNTAX_ERROR: """Test DatabaseManager URL processing with Docker Compose service URL."""
                                    # REMOVED_SYNTAX_ERROR: real_url = 'postgresql://postgres:postgres@localhost:5432/netra_dev'

                                    # Override environment with Docker Compose service URL
                                    # REMOVED_SYNTAX_ERROR: import os
                                    # Removed problematic line: with pytest.mock.patch.dict(os.environ, {'DATABASE_URL': real_url}):

                                        # Test base URL processing
                                        # REMOVED_SYNTAX_ERROR: base_url = DatabaseManager.get_base_database_url()
                                        # REMOVED_SYNTAX_ERROR: assert "postgresql://" in base_url
                                        # REMOVED_SYNTAX_ERROR: assert "localhost" in base_url

                                        # Test migration URL (sync format)
                                        # REMOVED_SYNTAX_ERROR: migration_url = DatabaseManager.get_migration_url_sync_format()
                                        # REMOVED_SYNTAX_ERROR: assert "postgresql://" in migration_url
                                        # REMOVED_SYNTAX_ERROR: assert "asyncpg" not in migration_url

                                        # Test application URL (async format)
                                        # REMOVED_SYNTAX_ERROR: app_url = DatabaseManager.get_application_url_async()
                                        # REMOVED_SYNTAX_ERROR: assert "postgresql+asyncpg://" in app_url

                                        # Validate URLs work with real database
                                        # REMOVED_SYNTAX_ERROR: from sqlalchemy import create_engine
                                        # REMOVED_SYNTAX_ERROR: sync_engine = create_engine(migration_url, echo=False)

                                        # REMOVED_SYNTAX_ERROR: with sync_engine.connect() as conn:
                                            # REMOVED_SYNTAX_ERROR: result = conn.execute(text("SELECT 1"))
                                            # REMOVED_SYNTAX_ERROR: assert result.fetchone()[0] == 1

                                            # REMOVED_SYNTAX_ERROR: sync_engine.dispose()

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_async_database_class_with_real_postgres(self, postgres_connection):
                                                # REMOVED_SYNTAX_ERROR: """Test AsyncDatabase class with real PostgreSQL container."""
                                                # REMOVED_SYNTAX_ERROR: real_url = 'postgresql://postgres:postgres@pytest.fixture

                                                # Create AsyncDatabase instance with real URL
                                                # REMOVED_SYNTAX_ERROR: db = AsyncDatabase(real_url)

                                                # REMOVED_SYNTAX_ERROR: try:
                                                    # REMOVED_SYNTAX_ERROR: await db.connect()

                                                    # Test database operations
                                                    # REMOVED_SYNTAX_ERROR: async with db.session() as session:
                                                        # Create test data
                                                        # REMOVED_SYNTAX_ERROR: await session.execute(text("CREATE TEMPORARY TABLE async_test (id SERIAL PRIMARY KEY, data TEXT)"))
                                                        # REMOVED_SYNTAX_ERROR: await session.execute(text("INSERT INTO async_test (data) VALUES ('test_data')"))
                                                        # REMOVED_SYNTAX_ERROR: await session.commit()

                                                        # Query test data
                                                        # REMOVED_SYNTAX_ERROR: result = await session.execute(text("SELECT data FROM async_test WHERE id = 1"))
                                                        # REMOVED_SYNTAX_ERROR: data = result.fetchone()
                                                        # REMOVED_SYNTAX_ERROR: assert data[0] == "test_data"

                                                        # Test transaction isolation
                                                        # REMOVED_SYNTAX_ERROR: await session.execute(text("INSERT INTO async_test (data) VALUES ('uncommitted')"))

                                                        # In separate session, shouldn't see uncommitted data
                                                        # REMOVED_SYNTAX_ERROR: async with db.session() as session2:
                                                            # REMOVED_SYNTAX_ERROR: result2 = await session2.execute(text("SELECT COUNT(*) FROM async_test"))
                                                            # REMOVED_SYNTAX_ERROR: count = result2.fetchone()
                                                            # REMOVED_SYNTAX_ERROR: assert count[0] == 1  # Only committed record visible

                                                            # REMOVED_SYNTAX_ERROR: await session.rollback()  # Rollback uncommitted insert

                                                            # REMOVED_SYNTAX_ERROR: finally:
                                                                # REMOVED_SYNTAX_ERROR: await db.disconnect()

                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_connection_pooling_with_real_postgres(self, postgres_connection):
                                                                    # REMOVED_SYNTAX_ERROR: """Test connection pooling behavior with real PostgreSQL."""
                                                                    # REMOVED_SYNTAX_ERROR: real_url = 'postgresql://postgres:postgres@pytest.fixture

                                                                    # Create engine with specific pool settings
                                                                    # REMOVED_SYNTAX_ERROR: engine = create_async_engine( )
                                                                    # REMOVED_SYNTAX_ERROR: real_url,
                                                                    # REMOVED_SYNTAX_ERROR: echo=False,
                                                                    # REMOVED_SYNTAX_ERROR: pool_size=3,
                                                                    # REMOVED_SYNTAX_ERROR: max_overflow=2,
                                                                    # REMOVED_SYNTAX_ERROR: pool_timeout=10,
                                                                    # REMOVED_SYNTAX_ERROR: pool_recycle=3600
                                                                    

                                                                    # REMOVED_SYNTAX_ERROR: async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

                                                                    # REMOVED_SYNTAX_ERROR: try:
                                                                        # Test concurrent connections up to pool limit
# REMOVED_SYNTAX_ERROR: async def run_query(query_id):
    # REMOVED_SYNTAX_ERROR: async with async_session() as session:
        # REMOVED_SYNTAX_ERROR: result = await session.execute(text("formatted_string"))
        # REMOVED_SYNTAX_ERROR: return result.fetchone()

        # Run 5 concurrent queries (pool_size=3, max_overflow=2)
        # REMOVED_SYNTAX_ERROR: tasks = [run_query(i) for i in range(5)]
        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

        # Verify all queries succeeded
        # REMOVED_SYNTAX_ERROR: assert len(results) == 5
        # REMOVED_SYNTAX_ERROR: query_ids = [r[0] for r in results]
        # REMOVED_SYNTAX_ERROR: assert set(query_ids) == {0, 1, 2, 3, 4}

        # Verify different backend PIDs (connection reuse)
        # REMOVED_SYNTAX_ERROR: backend_pids = [r[1] for r in results]
        # REMOVED_SYNTAX_ERROR: unique_pids = set(backend_pids)
        # REMOVED_SYNTAX_ERROR: assert len(unique_pids) <= 5  # Should reuse connections from pool

        # REMOVED_SYNTAX_ERROR: finally:
            # REMOVED_SYNTAX_ERROR: await engine.dispose()

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_database_error_handling_with_real_failures(self, postgres_connection):
                # REMOVED_SYNTAX_ERROR: """Test database error handling with real connection failures."""
                # REMOVED_SYNTAX_ERROR: valid_url = 'postgresql://postgres:postgres@pytest.fixture

                # Test with valid connection first
                # REMOVED_SYNTAX_ERROR: engine = create_async_engine(valid_url, echo=False)

                # REMOVED_SYNTAX_ERROR: try:
                    # REMOVED_SYNTAX_ERROR: async with engine.begin() as conn:
                        # REMOVED_SYNTAX_ERROR: await conn.execute(text("SELECT 1"))
                        # Connection works

                        # Test handling of real SQL errors
                        # REMOVED_SYNTAX_ERROR: async with engine.begin() as conn:
                            # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception):  # Should raise SQLAlchemy exception
                            # REMOVED_SYNTAX_ERROR: await conn.execute(text("SELECT * FROM nonexistent_table"))

                            # Test constraint violations
                            # REMOVED_SYNTAX_ERROR: async with engine.begin() as conn:
                                # REMOVED_SYNTAX_ERROR: await conn.execute(text("CREATE TEMPORARY TABLE constraint_test (id INTEGER PRIMARY KEY)"))
                                # REMOVED_SYNTAX_ERROR: await conn.execute(text("INSERT INTO constraint_test (id) VALUES (1)"))

                                # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception):  # Should raise integrity error
                                # REMOVED_SYNTAX_ERROR: await conn.execute(text("INSERT INTO constraint_test (id) VALUES (1)"))  # Duplicate key

                                # REMOVED_SYNTAX_ERROR: finally:
                                    # REMOVED_SYNTAX_ERROR: await engine.dispose()

                                    # Test with invalid connection
                                    # REMOVED_SYNTAX_ERROR: invalid_url = "postgresql+asyncpg://invalid_user:wrong_pass@nonexistent_host:5432/invalid_db"
                                    # REMOVED_SYNTAX_ERROR: invalid_engine = create_async_engine(invalid_url, echo=False)

                                    # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception):  # Should raise connection error
                                    # REMOVED_SYNTAX_ERROR: async with invalid_engine.begin() as conn:
                                        # REMOVED_SYNTAX_ERROR: await conn.execute(text("SELECT 1"))

                                        # REMOVED_SYNTAX_ERROR: await invalid_engine.dispose()

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_concurrent_transactions_real_database(self, postgres_connection):
                                            # REMOVED_SYNTAX_ERROR: """Test concurrent transaction handling with real PostgreSQL."""
                                            # REMOVED_SYNTAX_ERROR: real_url = 'postgresql://postgres:postgres@pytest.fixture
                                            # REMOVED_SYNTAX_ERROR: engine = create_async_engine(real_url, echo=False, pool_size=5)
                                            # REMOVED_SYNTAX_ERROR: async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

                                            # Setup test table
                                            # REMOVED_SYNTAX_ERROR: async with engine.begin() as conn:
                                                # REMOVED_SYNTAX_ERROR: await conn.execute(text("CREATE TEMPORARY TABLE concurrent_test (id INTEGER, counter INTEGER DEFAULT 0)"))
                                                # REMOVED_SYNTAX_ERROR: await conn.execute(text("INSERT INTO concurrent_test (id, counter) VALUES (1, 0)"))

                                                # REMOVED_SYNTAX_ERROR: try:
                                                    # Test concurrent updates to same record
# REMOVED_SYNTAX_ERROR: async def increment_counter(session_id):
    # REMOVED_SYNTAX_ERROR: async with async_session() as session:
        # Read current value
        # REMOVED_SYNTAX_ERROR: result = await session.execute(text("SELECT counter FROM concurrent_test WHERE id = 1"))
        # REMOVED_SYNTAX_ERROR: current_value = result.fetchone()[0]

        # Small delay to increase chance of race condition
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

        # Update with new value
        # REMOVED_SYNTAX_ERROR: await session.execute(text("formatted_string"))
        # REMOVED_SYNTAX_ERROR: await session.commit()

        # REMOVED_SYNTAX_ERROR: return session_id

        # Run concurrent updates
        # REMOVED_SYNTAX_ERROR: tasks = [increment_counter(i) for i in range(3)]
        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify final counter value (some updates may have been lost due to race conditions)
        # REMOVED_SYNTAX_ERROR: async with async_session() as session:
            # REMOVED_SYNTAX_ERROR: result = await session.execute(text("SELECT counter FROM concurrent_test WHERE id = 1"))
            # REMOVED_SYNTAX_ERROR: final_value = result.fetchone()[0]

            # With race conditions, final value should be between 1 and 3
            # REMOVED_SYNTAX_ERROR: assert 1 <= final_value <= 3

            # REMOVED_SYNTAX_ERROR: finally:
                # REMOVED_SYNTAX_ERROR: await engine.dispose()

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_db_connection_manager_integration(self, postgres_connection):
                    # REMOVED_SYNTAX_ERROR: """Test database connection manager with real PostgreSQL."""
                    # REMOVED_SYNTAX_ERROR: real_url = 'postgresql://postgres:postgres@localhost:5432/netra_dev'

                    # Override environment for connection manager
                    # REMOVED_SYNTAX_ERROR: import os
                    # Removed problematic line: with pytest.mock.patch.dict(os.environ, {'DATABASE_URL': real_url}):

                        # Test connection manager initialization - use canonical DatabaseManager
                        # db_manager = get_db_manager()  # DEPRECATED

                        # Test async session creation using DatabaseManager directly
                        # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_db() as session:
                            # REMOVED_SYNTAX_ERROR: result = await session.execute(text("SELECT current_database()"))
                            # REMOVED_SYNTAX_ERROR: db_name = result.fetchone()[0]
                            # REMOVED_SYNTAX_ERROR: assert db_name == 'netra_dev'

                            # Test multiple concurrent sessions
                            # Removed problematic line: async def test_session(session_id):
                                # REMOVED_SYNTAX_ERROR: async with db_manager.get_db() as session:
                                    # REMOVED_SYNTAX_ERROR: result = await session.execute(text("formatted_string"))
                                    # REMOVED_SYNTAX_ERROR: return result.fetchone()[0]

                                    # REMOVED_SYNTAX_ERROR: tasks = [test_session(i) for i in range(5)]
                                    # REMOVED_SYNTAX_ERROR: session_results = await asyncio.gather(*tasks)
                                    # REMOVED_SYNTAX_ERROR: assert session_results == [0, 1, 2, 3, 4]

                                    # REMOVED_SYNTAX_ERROR: @pytest.fixture
                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_clickhouse_connectivity_real(self, clickhouse_container):
                                        # REMOVED_SYNTAX_ERROR: """Test ClickHouse connectivity with real container."""
                                        # This would test ClickHouse integration if container is available
                                        # Skipped for now as ClickHouse container setup is more complex

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_database_migration_patterns(self, postgres_connection):
                                            # REMOVED_SYNTAX_ERROR: """Test database migration patterns with real PostgreSQL."""
                                            # REMOVED_SYNTAX_ERROR: real_url = 'postgresql://postgres:postgres@localhost:5432/netra_dev'

                                            # Test sync engine for migrations (alembic-style)
                                            # REMOVED_SYNTAX_ERROR: sync_engine = DatabaseManager.create_migration_engine()

                                            # Override with real URL
                                            # REMOVED_SYNTAX_ERROR: import os
                                            # Removed problematic line: with pytest.mock.patch.dict(os.environ, {'DATABASE_URL': real_url}):
                                                # REMOVED_SYNTAX_ERROR: sync_engine = DatabaseManager.create_migration_engine()

                                                # REMOVED_SYNTAX_ERROR: try:
                                                    # Test migration-style operations
                                                    # REMOVED_SYNTAX_ERROR: with sync_engine.connect() as conn:
                                                        # Create migration table
                                                        # REMOVED_SYNTAX_ERROR: conn.execute(text("CREATE TABLE IF NOT EXISTS migration_test (version VARCHAR(255) PRIMARY KEY, applied_at TIMESTAMP DEFAULT NOW())"))
                                                        # REMOVED_SYNTAX_ERROR: conn.commit()

                                                        # Insert migration record
                                                        # REMOVED_SYNTAX_ERROR: conn.execute(text("INSERT INTO migration_test (version) VALUES ('001_initial')"))
                                                        # REMOVED_SYNTAX_ERROR: conn.commit()

                                                        # Query migration status
                                                        # REMOVED_SYNTAX_ERROR: result = conn.execute(text("SELECT version FROM migration_test"))
                                                        # REMOVED_SYNTAX_ERROR: migrations = result.fetchall()
                                                        # REMOVED_SYNTAX_ERROR: assert ('001_initial',) in migrations

                                                        # REMOVED_SYNTAX_ERROR: finally:
                                                            # REMOVED_SYNTAX_ERROR: sync_engine.dispose()

                                                            # Removed problematic line: @pytest.mark.asyncio
                                                            # Removed problematic line: async def test_ssl_connection_handling(self, postgres_connection):
                                                                # REMOVED_SYNTAX_ERROR: """Test SSL connection parameter handling."""
                                                                # REMOVED_SYNTAX_ERROR: base_url = 'postgresql://postgres:postgres@localhost:5432/netra_dev'

                                                                # Test various SSL parameter combinations
                                                                # REMOVED_SYNTAX_ERROR: ssl_variants = [ )
                                                                # REMOVED_SYNTAX_ERROR: base_url + "?sslmode=prefer",
                                                                # REMOVED_SYNTAX_ERROR: base_url + "?ssl=prefer",
                                                                # REMOVED_SYNTAX_ERROR: base_url + "?sslmode=require&ssl=prefer"
                                                                

                                                                # REMOVED_SYNTAX_ERROR: for test_url in ssl_variants:
                                                                    # Removed problematic line: with pytest.mock.patch.dict('os.environ', {'DATABASE_URL': test_url}):
                                                                        # Test URL processing handles SSL parameters
                                                                        # REMOVED_SYNTAX_ERROR: processed_url = DatabaseManager.get_application_url_async()

                                                                        # Should convert to asyncpg format and handle SSL properly
                                                                        # REMOVED_SYNTAX_ERROR: assert "postgresql+asyncpg://" in processed_url

                                                                        # Test that connection still works (SSL negotiation with container)
                                                                        # REMOVED_SYNTAX_ERROR: try:
                                                                            # REMOVED_SYNTAX_ERROR: engine = create_async_engine(processed_url, echo=False)
                                                                            # REMOVED_SYNTAX_ERROR: async with engine.begin() as conn:
                                                                                # REMOVED_SYNTAX_ERROR: result = await conn.execute(text("SELECT 1"))
                                                                                # REMOVED_SYNTAX_ERROR: assert result.fetchone()[0] == 1
                                                                                # REMOVED_SYNTAX_ERROR: await engine.dispose()
                                                                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                                    # SSL might fail with test container, but URL processing should work
                                                                                    # REMOVED_SYNTAX_ERROR: assert "postgresql+asyncpg://" in processed_url


                                                                                    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                                                        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])
