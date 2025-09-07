# Real services test fixtures
"""Real services test fixtures for integration testing with actual services."""

import pytest


@pytest.fixture(scope="session")
def real_postgres_connection():
    """Fixture for real PostgreSQL connection during testing."""
    # Placeholder implementation - returns None for basic compatibility
    # In a real implementation, this would create a connection to a test database
    return None


@pytest.fixture(scope="function") 
def with_test_database():
    """Fixture that provides a test database context."""
    # Placeholder implementation - yields None for basic compatibility  
    # In a real implementation, this would set up and tear down test database
    yield None


@pytest.fixture(scope="function")
def real_services_fixture(real_postgres_connection):
    """Fixture for real services testing - provides access to actual running services."""
    # Returns a dict with real service connections
    return {
        "backend_url": "http://localhost:8000",
        "auth_url": "http://localhost:8081",
        "postgres": real_postgres_connection,  # Use the fixture parameter
        "test_database": None,
        "db": real_postgres_connection  # Also provide as 'db' key for compatibility
    }
