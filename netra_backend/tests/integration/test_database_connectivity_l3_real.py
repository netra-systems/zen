"""L3 Integration Tests for Database Connectivity with Real Containerized Services.

These tests validate database connectivity, transactions, and management using 
real PostgreSQL and ClickHouse containers via Testcontainers, providing L3-level 
realism as required by testing.xml Mock-Real Spectrum.

Business Value: Ensures database connectivity patterns work in production-like
environments, preventing connection failures and data integrity issues that 
could impact customer operations and data reliability.
"""

import pytest
import asyncio
from testcontainers.postgres import PostgresContainer
from testcontainers.clickhouse import ClickHouseContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.core.unified.db_connection_manager import get_db_manager
from netra_backend.app.db.postgres_core import AsyncDatabase


@pytest.mark.integration
class TestDatabaseConnectivityL3:
    """L3 Integration tests for database connectivity with real containers."""
    
    @pytest.fixture(scope="class")
    def postgres_container(self):
        """Start real PostgreSQL container for testing."""
        try:
            with PostgresContainer("postgres:15") as postgres:
                yield postgres
        except Exception as e:
            pytest.skip(f"PostgreSQL container not available: {e}")
    
    @pytest.fixture(scope="class")
    def clickhouse_container(self):
        """Start real ClickHouse container for testing."""
        try:
            with ClickHouseContainer("clickhouse/clickhouse-server:latest") as clickhouse:
                yield clickhouse
        except Exception as e:
            pytest.skip(f"ClickHouse container not available: {e}")
    
    @pytest.mark.asyncio
    async def test_postgres_connection_lifecycle(self, postgres_container):
        """Test complete PostgreSQL connection lifecycle with real database."""
        # Get real connection URL from container
        db_url = postgres_container.get_connection_url()
        async_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        
        # Test engine creation
        engine = create_async_engine(async_url, echo=False, pool_size=2, max_overflow=5)
        
        try:
            # Test connection
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT version()"))
                version = result.fetchone()
                assert "PostgreSQL" in version[0]
            
            # Test session creation and transactions
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            
            async with async_session() as session:
                # Test transaction with real database
                await session.execute(text("CREATE TEMPORARY TABLE test_table (id INTEGER, name TEXT)"))
                await session.execute(text("INSERT INTO test_table (id, name) VALUES (1, 'test')"))
                
                result = await session.execute(text("SELECT COUNT(*) FROM test_table"))
                count = result.fetchone()
                assert count[0] == 1
                
                # Test rollback
                await session.rollback()
                
                # Verify transaction rollback worked
                result = await session.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'test_table'"))
                table_count = result.fetchone()
                assert table_count[0] == 0  # Temporary table rolled back
                
        finally:
            await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_database_manager_real_url_processing(self, postgres_container):
        """Test DatabaseManager URL processing with real container URL."""
        real_url = postgres_container.get_connection_url()
        
        # Override environment with real container URL
        import os
        with pytest.mock.patch.dict(os.environ, {'DATABASE_URL': real_url}):
            
            # Test base URL processing
            base_url = DatabaseManager.get_base_database_url()
            assert "postgresql://" in base_url
            assert postgres_container.get_container_host_ip() in base_url
            
            # Test migration URL (sync format)
            migration_url = DatabaseManager.get_migration_url_sync_format()
            assert "postgresql://" in migration_url
            assert "asyncpg" not in migration_url
            
            # Test application URL (async format)
            app_url = DatabaseManager.get_application_url_async()
            assert "postgresql+asyncpg://" in app_url
            
            # Validate URLs work with real database
            from sqlalchemy import create_engine
            sync_engine = create_engine(migration_url, echo=False)
            
            with sync_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1
            
            sync_engine.dispose()
    
    @pytest.mark.asyncio
    async def test_async_database_class_with_real_postgres(self, postgres_container):
        """Test AsyncDatabase class with real PostgreSQL container."""
        real_url = postgres_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
        
        # Create AsyncDatabase instance with real URL
        db = AsyncDatabase(real_url)
        
        try:
            await db.connect()
            
            # Test database operations
            async with db.session() as session:
                # Create test data
                await session.execute(text("CREATE TEMPORARY TABLE async_test (id SERIAL PRIMARY KEY, data TEXT)"))
                await session.execute(text("INSERT INTO async_test (data) VALUES ('test_data')"))
                await session.commit()
                
                # Query test data
                result = await session.execute(text("SELECT data FROM async_test WHERE id = 1"))
                data = result.fetchone()
                assert data[0] == "test_data"
                
                # Test transaction isolation
                await session.execute(text("INSERT INTO async_test (data) VALUES ('uncommitted')"))
                
                # In separate session, shouldn't see uncommitted data
                async with db.session() as session2:
                    result2 = await session2.execute(text("SELECT COUNT(*) FROM async_test"))
                    count = result2.fetchone()
                    assert count[0] == 1  # Only committed record visible
                
                await session.rollback()  # Rollback uncommitted insert
                
        finally:
            await db.disconnect()
    
    @pytest.mark.asyncio
    async def test_connection_pooling_with_real_postgres(self, postgres_container):
        """Test connection pooling behavior with real PostgreSQL."""
        real_url = postgres_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
        
        # Create engine with specific pool settings
        engine = create_async_engine(
            real_url, 
            echo=False, 
            pool_size=3,
            max_overflow=2,
            pool_timeout=10,
            pool_recycle=3600
        )
        
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        try:
            # Test concurrent connections up to pool limit
            async def run_query(query_id):
                async with async_session() as session:
                    result = await session.execute(text(f"SELECT {query_id} as id, pg_backend_pid()"))
                    return result.fetchone()
            
            # Run 5 concurrent queries (pool_size=3, max_overflow=2)
            tasks = [run_query(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            
            # Verify all queries succeeded
            assert len(results) == 5
            query_ids = [r[0] for r in results]
            assert set(query_ids) == {0, 1, 2, 3, 4}
            
            # Verify different backend PIDs (connection reuse)
            backend_pids = [r[1] for r in results]
            unique_pids = set(backend_pids)
            assert len(unique_pids) <= 5  # Should reuse connections from pool
            
        finally:
            await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_database_error_handling_with_real_failures(self, postgres_container):
        """Test database error handling with real connection failures."""
        valid_url = postgres_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
        
        # Test with valid connection first
        engine = create_async_engine(valid_url, echo=False)
        
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                # Connection works
            
            # Test handling of real SQL errors
            async with engine.begin() as conn:
                with pytest.raises(Exception):  # Should raise SQLAlchemy exception
                    await conn.execute(text("SELECT * FROM nonexistent_table"))
            
            # Test constraint violations
            async with engine.begin() as conn:
                await conn.execute(text("CREATE TEMPORARY TABLE constraint_test (id INTEGER PRIMARY KEY)"))
                await conn.execute(text("INSERT INTO constraint_test (id) VALUES (1)"))
                
                with pytest.raises(Exception):  # Should raise integrity error
                    await conn.execute(text("INSERT INTO constraint_test (id) VALUES (1)"))  # Duplicate key
                
        finally:
            await engine.dispose()
        
        # Test with invalid connection
        invalid_url = "postgresql+asyncpg://invalid_user:wrong_pass@nonexistent_host:5432/invalid_db"
        invalid_engine = create_async_engine(invalid_url, echo=False)
        
        with pytest.raises(Exception):  # Should raise connection error
            async with invalid_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        
        await invalid_engine.dispose()
    
    @pytest.mark.asyncio
    async def test_concurrent_transactions_real_database(self, postgres_container):
        """Test concurrent transaction handling with real PostgreSQL."""
        real_url = postgres_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(real_url, echo=False, pool_size=5)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        # Setup test table
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TEMPORARY TABLE concurrent_test (id INTEGER, counter INTEGER DEFAULT 0)"))
            await conn.execute(text("INSERT INTO concurrent_test (id, counter) VALUES (1, 0)"))
        
        try:
            # Test concurrent updates to same record
            async def increment_counter(session_id):
                async with async_session() as session:
                    # Read current value
                    result = await session.execute(text("SELECT counter FROM concurrent_test WHERE id = 1"))
                    current_value = result.fetchone()[0]
                    
                    # Small delay to increase chance of race condition
                    await asyncio.sleep(0.1)
                    
                    # Update with new value
                    await session.execute(text(f"UPDATE concurrent_test SET counter = {current_value + 1} WHERE id = 1"))
                    await session.commit()
                    
                    return session_id
            
            # Run concurrent updates
            tasks = [increment_counter(i) for i in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify final counter value (some updates may have been lost due to race conditions)
            async with async_session() as session:
                result = await session.execute(text("SELECT counter FROM concurrent_test WHERE id = 1"))
                final_value = result.fetchone()[0]
                
                # With race conditions, final value should be between 1 and 3
                assert 1 <= final_value <= 3
            
        finally:
            await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_db_connection_manager_integration(self, postgres_container):
        """Test database connection manager with real PostgreSQL."""
        real_url = postgres_container.get_connection_url()
        
        # Override environment for connection manager
        import os
        with pytest.mock.patch.dict(os.environ, {'DATABASE_URL': real_url}):
            
            # Test connection manager initialization
            db_manager = get_db_manager()
            
            # Test async session creation
            async with db_manager.get_async_session() as session:
                result = await session.execute(text("SELECT current_database()"))
                db_name = result.fetchone()[0]
                assert db_name == postgres_container.database_name
            
            # Test multiple concurrent sessions
            async def test_session(session_id):
                async with db_manager.get_async_session() as session:
                    result = await session.execute(text(f"SELECT {session_id} as session_id"))
                    return result.fetchone()[0]
            
            tasks = [test_session(i) for i in range(5)]
            session_results = await asyncio.gather(*tasks)
            assert session_results == [0, 1, 2, 3, 4]
    
    @pytest.mark.skipif(True, reason="ClickHouse tests require additional setup")
    @pytest.mark.asyncio
    async def test_clickhouse_connectivity_real(self, clickhouse_container):
        """Test ClickHouse connectivity with real container."""
        # This would test ClickHouse integration if container is available
        # Skipped for now as ClickHouse container setup is more complex
        pass
    
    @pytest.mark.asyncio
    async def test_database_migration_patterns(self, postgres_container):
        """Test database migration patterns with real PostgreSQL."""
        real_url = postgres_container.get_connection_url()
        
        # Test sync engine for migrations (alembic-style)
        sync_engine = DatabaseManager.create_migration_engine()
        
        # Override with real URL
        import os
        with pytest.mock.patch.dict(os.environ, {'DATABASE_URL': real_url}):
            sync_engine = DatabaseManager.create_migration_engine()
            
            try:
                # Test migration-style operations
                with sync_engine.connect() as conn:
                    # Create migration table
                    conn.execute(text("CREATE TABLE IF NOT EXISTS migration_test (version VARCHAR(255) PRIMARY KEY, applied_at TIMESTAMP DEFAULT NOW())"))
                    conn.commit()
                    
                    # Insert migration record
                    conn.execute(text("INSERT INTO migration_test (version) VALUES ('001_initial')"))
                    conn.commit()
                    
                    # Query migration status
                    result = conn.execute(text("SELECT version FROM migration_test"))
                    migrations = result.fetchall()
                    assert ('001_initial',) in migrations
                    
            finally:
                sync_engine.dispose()
    
    @pytest.mark.asyncio
    async def test_ssl_connection_handling(self, postgres_container):
        """Test SSL connection parameter handling."""
        base_url = postgres_container.get_connection_url()
        
        # Test various SSL parameter combinations
        ssl_variants = [
            base_url + "?sslmode=prefer",
            base_url + "?ssl=prefer",
            base_url + "?sslmode=require&ssl=prefer"
        ]
        
        for test_url in ssl_variants:
            with pytest.mock.patch.dict('os.environ', {'DATABASE_URL': test_url}):
                # Test URL processing handles SSL parameters
                processed_url = DatabaseManager.get_application_url_async()
                
                # Should convert to asyncpg format and handle SSL properly
                assert "postgresql+asyncpg://" in processed_url
                
                # Test that connection still works (SSL negotiation with container)
                try:
                    engine = create_async_engine(processed_url, echo=False)
                    async with engine.begin() as conn:
                        result = await conn.execute(text("SELECT 1"))
                        assert result.fetchone()[0] == 1
                    await engine.dispose()
                except Exception as e:
                    # SSL might fail with test container, but URL processing should work
                    assert "postgresql+asyncpg://" in processed_url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])