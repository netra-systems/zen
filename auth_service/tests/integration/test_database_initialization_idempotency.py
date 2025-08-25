"""
Database initialization idempotency tests for auth service.

These tests specifically target the UniqueViolationError warnings seen in staging logs
during database initialization. The database initialization should be idempotent and
handle existing schemas, tables, and constraints gracefully.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy import text

from auth_service.auth_core.database.connection import auth_db
from auth_service.auth_core.database.models import Base, AuthUser
from auth_service.init_database import init_auth_database
from test_framework.environment_markers import env

pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth_service,
    pytest.mark.database,
    pytest.mark.idempotency,
    pytest.mark.asyncio
]

class TestDatabaseInitializationIdempotency:
    """Test that database initialization is truly idempotent."""
    
    async def test_init_database_script_idempotency(self):
        """
        Test the init_database.py script can be run multiple times safely.
        
        EXPECTED FAILURE: Currently may raise UniqueViolationError on repeated runs.
        """
        # Run initialization first time
        success1 = await init_auth_database()
        assert success1, "First database initialization should succeed"
        
        # Run initialization second time - should not fail
        success2 = await init_auth_database()
        assert success2, "Second database initialization should also succeed (idempotent)"
        
        # Run third time to be sure
        success3 = await init_auth_database()
        assert success3, "Third database initialization should also succeed (idempotent)"
    
    async def test_create_all_metadata_idempotency(self):
        """
        Test that SQLAlchemy create_all is idempotent.
        
        EXPECTED FAILURE: May not handle existing objects gracefully.
        """
        # Initialize database connection
        await auth_db.initialize()
        
        # Create tables first time
        async with auth_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create tables second time - should not raise errors
        try:
            async with auth_db.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            pytest.fail(f"Second create_all should be idempotent but failed: {e}")
        
        # Verify tables exist and are functional
        async with auth_db.get_session() as session:
            result = await session.execute(
                text("SELECT tablename FROM pg_tables WHERE tablename LIKE 'auth_%'")
            )
            tables = [row[0] for row in result.fetchall()]
            assert len(tables) > 0, "Auth tables should exist after initialization"
    
    async def test_database_initialization_with_existing_constraints(self):
        """
        Test initialization when database constraints already exist.
        
        EXPECTED FAILURE: May try to create duplicate constraints.
        """
        await auth_db.initialize()
        
        # Create tables first time
        async with auth_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Simulate the scenario where we try to add constraints that already exist
        try:
            async with auth_db.get_session() as session:
                # Try to create a constraint that might already exist
                await session.execute(text("""
                    ALTER TABLE auth_users 
                    ADD CONSTRAINT auth_users_email_unique UNIQUE (email)
                """))
                await session.commit()
        except ProgrammingError:
            # Expected - constraint already exists
            pass
        except Exception as e:
            # This should be handled gracefully
            pytest.fail(f"Constraint creation should handle existing constraints: {e}")
        
        # Now run full initialization again - should handle existing constraints
        try:
            await init_auth_database()
        except Exception as e:
            pytest.fail(f"Database initialization should handle existing constraints: {e}")
    
    async def test_database_initialization_interrupted_state_recovery(self):
        """
        Test recovery from interrupted database initialization.
        
        EXPECTED FAILURE: May not handle partial initialization states properly.
        """
        await auth_db.initialize()
        
        # Simulate interrupted initialization by creating some tables but not others
        async with auth_db.engine.begin() as conn:
            # Create only one table to simulate partial initialization
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS auth_users (
                    id VARCHAR PRIMARY KEY,
                    email VARCHAR UNIQUE NOT NULL,
                    full_name VARCHAR,
                    auth_provider VARCHAR,
                    is_active BOOLEAN DEFAULT true,
                    is_verified BOOLEAN DEFAULT false,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
        
        # Now run full initialization - should complete the missing pieces
        try:
            success = await init_auth_database()
            assert success, "Database initialization should recover from partial state"
        except Exception as e:
            pytest.fail(f"Database initialization should recover from interruption: {e}")
        
        # Verify all expected tables exist
        async with auth_db.get_session() as session:
            result = await session.execute(
                text("SELECT tablename FROM pg_tables WHERE tablename LIKE 'auth_%'")
            )
            tables = [row[0] for row in result.fetchall()]
            assert 'auth_users' in tables, "auth_users table should exist"
    
    async def test_concurrent_database_initializations(self):
        """
        Test multiple concurrent database initialization attempts.
        
        EXPECTED FAILURE: Race conditions may cause constraint violations.
        """
        async def safe_init():
            try:
                return await init_auth_database()
            except Exception as e:
                return f"Error: {e}"
        
        # Run 5 concurrent initializations
        tasks = [safe_init() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # At least some should succeed
        success_count = sum(1 for result in results if result is True)
        assert success_count > 0, f"At least one concurrent initialization should succeed: {results}"
        
        # None should have unhandled exceptions (should return True or error string)
        for i, result in enumerate(results):
            assert result is True or isinstance(result, str), \
                f"Initialization #{i+1} returned unexpected type: {type(result)} - {result}"
    
    async def test_database_schema_creation_idempotency(self):
        """
        Test that schema creation commands are idempotent.
        
        EXPECTED FAILURE: May try to create schemas that already exist.
        """
        await auth_db.initialize()
        
        # Create schema multiple times
        async with auth_db.get_session() as session:
            # First creation
            await session.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
            await session.commit()
            
            # Second creation - should not fail due to IF NOT EXISTS
            await session.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))  
            await session.commit()
        
        # Run full database initialization - should handle existing schema
        try:
            success = await init_auth_database()
            assert success, "Database initialization should handle existing schemas"
        except Exception as e:
            pytest.fail(f"Database initialization failed with existing schema: {e}")

class TestDatabaseIndexCreationIdempotency:
    """Test that database index creation is idempotent."""
    
    async def test_index_creation_idempotency(self):
        """
        Test that indexes can be created multiple times without errors.
        
        EXPECTED FAILURE: May try to create duplicate indexes.
        """
        await auth_db.initialize()
        
        # Create tables first
        async with auth_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create an index manually first time
        async with auth_db.get_session() as session:
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_auth_users_email 
                ON auth_users (email)
            """))
            await session.commit()
        
        # Create same index second time - should not fail with IF NOT EXISTS
        async with auth_db.get_session() as session:
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_auth_users_email 
                ON auth_users (email)
            """))
            await session.commit()
        
        # Run full initialization - should handle existing indexes
        try:
            success = await init_auth_database()
            assert success, "Database initialization should handle existing indexes"
        except Exception as e:
            pytest.fail(f"Database initialization failed with existing indexes: {e}")

class TestDatabaseSequenceAndTypeIdempotency:
    """Test idempotency of sequences, types, and other database objects."""
    
    async def test_custom_type_creation_idempotency(self):
        """
        Test that custom database types can be created idempotently.
        
        EXPECTED FAILURE: May try to create types that already exist.
        """
        await auth_db.initialize()
        
        # Create a custom enum type
        async with auth_db.get_session() as session:
            await session.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE auth_provider_enum AS ENUM ('google', 'github', 'local');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            await session.commit()
        
        # Try to create it again - should not fail
        async with auth_db.get_session() as session:
            await session.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE auth_provider_enum AS ENUM ('google', 'github', 'local');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            await session.commit()
        
        # Run full initialization
        try:
            success = await init_auth_database()
            assert success, "Database initialization should handle existing types"
        except Exception as e:
            pytest.fail(f"Database initialization failed with existing types: {e}")

class TestDatabaseRollbackAndRecovery:
    """Test database rollback and recovery scenarios."""
    
    async def test_failed_initialization_rollback(self):
        """
        Test that failed initialization attempts don't leave database in bad state.
        
        EXPECTED FAILURE: May leave partial objects that interfere with retry.
        """
        await auth_db.initialize()
        
        # Simulate a failed initialization by causing an error mid-process
        with patch('auth_service.auth_core.database.models.Base.metadata.create_all', 
                   side_effect=Exception("Simulated failure")):
            try:
                await init_auth_database()
                pytest.fail("Expected initialization to fail with mocked exception")
            except Exception:
                # Expected failure
                pass
        
        # Now try normal initialization - should succeed despite previous failure
        try:
            success = await init_auth_database()
            assert success, "Database initialization should recover from previous failure"
        except Exception as e:
            pytest.fail(f"Database initialization should recover from rollback: {e}")
    
    async def test_partial_table_creation_recovery(self):
        """
        Test recovery when only some tables were created successfully.
        
        EXPECTED FAILURE: May not handle missing tables properly.
        """
        await auth_db.initialize()
        
        # Manually create only part of the schema
        async with auth_db.get_session() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS auth_users (
                    id VARCHAR PRIMARY KEY,
                    email VARCHAR UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            await session.commit()
        
        # Run full initialization - should create missing tables
        try:
            success = await init_auth_database()
            assert success, "Database initialization should create missing tables"
            
            # Verify all expected tables exist
            result = await session.execute(
                text("SELECT tablename FROM pg_tables WHERE tablename LIKE 'auth_%'")
            )
            tables = [row[0] for row in result.fetchall()]
            assert 'auth_users' in tables, "auth_users should exist"
            
        except Exception as e:
            pytest.fail(f"Database initialization should handle partial schema: {e}")

# Error handling and validation tests
class TestDatabaseInitializationErrorHandling:
    """Test error handling during database initialization."""
    
    async def test_invalid_database_url_handling(self):
        """
        Test initialization with invalid database URL.
        
        Should fail gracefully with clear error message.
        """
        # This test ensures error handling, not idempotency, but related to robustness
        with patch.dict('os.environ', {'DATABASE_URL': 'invalid://url'}):
            try:
                success = await init_auth_database()
                assert not success, "Initialization should fail with invalid database URL"
            except Exception as e:
                # Should handle the error gracefully
                assert "database" in str(e).lower() or "connection" in str(e).lower(), \
                    f"Error should mention database connection issue: {e}"
    
    async def test_permission_denied_recovery(self):
        """
        Test behavior when database operations are denied due to permissions.
        
        Should handle permission errors gracefully.
        """
        # This would require mocking permission errors
        # For now, just ensure the test structure exists for future implementation
        pass