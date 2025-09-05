"""Test that DATABASE_URL is properly passed through the system.

This test ensures that DATABASE_URL environment variable is correctly:
1. Retrieved from the environment
2. Passed through DatabaseURLBuilder
3. Formatted for the appropriate driver
4. Used by DatabaseManager
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from shared.isolated_environment import get_env
from shared.database_url_builder import DatabaseURLBuilder
from netra_backend.app.db.database_manager import DatabaseManager


class TestDatabaseURLPassing:
    """Test suite for DATABASE_URL environment variable passing."""
    
    def test_database_url_retrieved_from_environment(self):
        """Test that DATABASE_URL is retrieved from environment."""
        env = get_env()
        
        # Set a test DATABASE_URL
        test_url = "postgresql://test_user:test_pass@test_host:5432/test_db"
        env.set("DATABASE_URL", test_url)
        
        # Verify it can be retrieved
        retrieved_url = env.get("DATABASE_URL")
        assert retrieved_url == test_url, f"Expected {test_url}, got {retrieved_url}"
    
    def test_database_url_builder_uses_environment(self):
        """Test that DatabaseURLBuilder correctly uses DATABASE_URL from environment."""
        env = get_env()
        
        # Set test DATABASE_URL and environment
        test_url = "postgresql://test_user:test_pass@test_host:5432/test_db"
        env.set("DATABASE_URL", test_url)
        env.set("ENVIRONMENT", "test")
        
        # Create builder with environment
        builder = DatabaseURLBuilder(env.as_dict())
        
        # Verify builder has the DATABASE_URL
        assert builder.database_url == test_url, f"Builder didn't get DATABASE_URL: {builder.database_url}"
        
        # Verify it returns the URL for test environment
        url = builder.get_url_for_environment()
        assert url == test_url, f"Builder didn't return DATABASE_URL for test environment: {url}"
    
    def test_database_url_formatted_for_asyncpg(self):
        """Test that DATABASE_URL is correctly formatted for asyncpg driver."""
        env = get_env()
        
        # Set test DATABASE_URL
        test_url = "postgresql://test_user:test_pass@test_host:5432/test_db"
        env.set("DATABASE_URL", test_url)
        
        # Create builder
        builder = DatabaseURLBuilder(env.as_dict())
        
        # Format for asyncpg
        asyncpg_url = builder.format_url_for_driver(test_url, 'asyncpg')
        
        # Verify it's formatted correctly
        expected_url = "postgresql+asyncpg://test_user:test_pass@test_host:5432/test_db"
        assert asyncpg_url == expected_url, f"Expected {expected_url}, got {asyncpg_url}"
    
    def test_database_manager_retrieves_database_url(self):
        """Test that DatabaseManager correctly retrieves and formats DATABASE_URL."""
        env = get_env()
        
        # Set test DATABASE_URL and environment
        test_url = "postgresql://test_user:test_pass@test_host:5432/test_db"
        env.set("DATABASE_URL", test_url)
        env.set("ENVIRONMENT", "test")
        
        # Create DatabaseManager
        manager = DatabaseManager()
        
        # Get database URL from manager
        manager_url = manager._get_database_url()
        
        # Verify it's formatted for asyncpg
        assert "postgresql+asyncpg://" in manager_url, f"URL not formatted for asyncpg: {manager_url}"
        assert "test_user" in manager_url, f"User not in URL: {manager_url}"
        assert "test_host" in manager_url, f"Host not in URL: {manager_url}"
        assert "test_db" in manager_url, f"Database not in URL: {manager_url}"
    
    def test_database_url_fallback_to_components(self):
        """Test that system falls back to POSTGRES_* components if DATABASE_URL not set."""
        env = get_env()
        
        # Clear DATABASE_URL
        env.delete("DATABASE_URL")
        
        # Set individual components
        env.set("POSTGRES_HOST", "component_host")
        env.set("POSTGRES_PORT", "5433")
        env.set("POSTGRES_USER", "component_user")
        env.set("POSTGRES_PASSWORD", "component_pass")
        env.set("POSTGRES_DB", "component_db")
        env.set("ENVIRONMENT", "test")
        
        # Create builder
        builder = DatabaseURLBuilder(env.as_dict())
        
        # Verify it builds URL from components
        assert builder.postgres_host == "component_host"
        assert builder.postgres_user == "component_user"
        assert builder.postgres_db == "component_db"
        
        # Get URL - should be built from components
        url = builder.tcp.async_url
        assert url is not None, "Failed to build URL from components"
        assert "component_host" in url
        assert "component_user" in url
        assert "component_db" in url
    
    def test_database_url_priority_over_components(self):
        """Test that DATABASE_URL takes priority over individual components."""
        env = get_env()
        
        # Set both DATABASE_URL and components
        test_url = "postgresql://url_user:url_pass@url_host:5432/url_db"
        env.set("DATABASE_URL", test_url)
        env.set("POSTGRES_HOST", "component_host")
        env.set("POSTGRES_USER", "component_user")
        env.set("POSTGRES_DB", "component_db")
        env.set("ENVIRONMENT", "test")
        
        # Create builder
        builder = DatabaseURLBuilder(env.as_dict())
        
        # Get URL - should use DATABASE_URL, not components
        url = builder.get_url_for_environment()
        assert url == test_url, f"DATABASE_URL should take priority: {url}"
        
        # Verify URL contains DATABASE_URL values, not component values
        assert "url_user" in url
        assert "url_host" in url
        assert "url_db" in url
        assert "component_host" not in url
        assert "component_user" not in url
        assert "component_db" not in url


if __name__ == "__main__":
    # Run the tests
    test_suite = TestDatabaseURLPassing()
    
    print("Running DATABASE_URL passing tests...")
    
    test_suite.test_database_url_retrieved_from_environment()
    print("✓ DATABASE_URL retrieved from environment")
    
    test_suite.test_database_url_builder_uses_environment()
    print("✓ DatabaseURLBuilder uses DATABASE_URL from environment")
    
    test_suite.test_database_url_formatted_for_asyncpg()
    print("✓ DATABASE_URL formatted for asyncpg driver")
    
    test_suite.test_database_manager_retrieves_database_url()
    print("✓ DatabaseManager retrieves and formats DATABASE_URL")
    
    test_suite.test_database_url_fallback_to_components()
    print("✓ System falls back to POSTGRES_* components when needed")
    
    test_suite.test_database_url_priority_over_components()
    print("✓ DATABASE_URL takes priority over individual components")
    
    print("\nAll tests passed! DATABASE_URL is being properly passed through the system.")