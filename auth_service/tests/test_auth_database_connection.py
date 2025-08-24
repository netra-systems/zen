"""
Test auth service database connection during tests.

This test verifies that the auth service properly uses SQLite during pytest execution
and doesn't incorrectly try to connect to PostgreSQL.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Reliability
- Value Impact: Ensures auth tests run correctly in isolated environments
- Strategic Impact: Enables reliable CI/CD and development workflows
"""
import os
import pytest


def test_database_url_is_sqlite_during_tests():
    """Test that DATABASE_URL is set to SQLite during pytest execution."""
    # This should be SQLite as set by conftest.py
    database_url = os.environ.get("DATABASE_URL", "")
    assert database_url.startswith("sqlite"), f"Expected SQLite URL, got: {database_url}"


@pytest.mark.asyncio
async def test_auth_database_connection_uses_sqlite():
    """Test that auth service uses SQLite for database connections during tests."""
    from auth_service.auth_core.database.connection import auth_db
    
    # Initialize the database
    await auth_db.initialize()
    
    # Check that the engine URL is SQLite
    engine_url = str(auth_db.engine.url)
    assert "sqlite" in engine_url.lower(), f"Expected SQLite engine, got: {engine_url}"
    
    # Test basic database operations work
    from sqlalchemy import text
    async with auth_db.get_session() as session:
        # Execute a simple query to verify connection works
        result = await session.execute(text("SELECT 1 as test_value"))
        row = result.fetchone()
        assert row is not None
        assert row[0] == 1


@pytest.mark.asyncio 
async def test_auth_database_table_creation():
    """Test that auth service can create tables in SQLite."""
    from auth_service.auth_core.database.connection import auth_db
    from auth_service.auth_core.database.models import Base
    
    # Initialize the database 
    await auth_db.initialize()
    
    # Create tables (should work with SQLite)
    await auth_db.create_tables()
    
    # Verify tables exist by checking metadata
    from sqlalchemy import text
    async with auth_db.get_session() as session:
        # Check if auth_users table exists (basic smoke test)
        result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='auth_users'"))
        table_exists = result.fetchone() is not None
        assert table_exists, "auth_users table should exist after table creation"


def test_auth_config_database_url_in_tests():
    """Test that AuthConfig returns appropriate database URL during tests."""
    from auth_service.auth_core.config import AuthConfig
    
    # Get database URL through auth config
    database_url = AuthConfig.get_database_url()
    
    # During tests, this should be empty or SQLite (handled by connection logic)
    # The connection.py should fall back to SQLite when empty
    if database_url:
        assert "sqlite" in database_url.lower() or database_url == "", \
            f"Expected SQLite or empty URL during tests, got: {database_url}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])