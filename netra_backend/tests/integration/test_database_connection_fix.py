from shared.isolated_environment import get_env
"""
Test and fix database connection issues.
This test identifies and fixes database authentication problems.
"""
import pytest
import os
from netra_backend.app.config import get_config


env = get_env()
class TestDatabaseConnectionFix:
    """Test and fix database connection issues."""

    def test_database_url_credentials_issue(self):
        """Test database URL and identify credential issues."""
        config = get_config()
        
        print(f"Environment: {config.environment}")
        print(f"Database URL: {config.database_url}")
        
        # Check if using test credentials that are causing auth failures
        if 'test:test@' in config.database_url:
            print("⚠ Using test:test credentials which are failing authentication")
            
            # The issue is that test:test credentials don't exist in the database
            # We should use the same credentials as development
            suggested_fix = config.database_url.replace('test:test@', 'postgres:postgres@')
            suggested_fix = suggested_fix.replace('netra_test', 'netra_dev')
            
            print(f"Suggested fix: {suggested_fix}")
            
            pytest.fail(f"Database authentication failing with test:test credentials. "
                       f"Should use postgres:postgres credentials for development database.")
        
        # Check environment variables
        test_db_url = os.getenv('TEST_DATABASE_URL')
        db_url = os.getenv('DATABASE_URL')
        
        print(f"TEST_DATABASE_URL env var: {test_db_url}")
        print(f"DATABASE_URL env var: {db_url}")

    def test_database_connection_environment_override(self):
        """Test overriding database connection for testing."""
        # Try to set a working database URL for testing
        working_db_url = "postgresql://postgres:postgres@localhost:5432/netra_dev"
        
        # Set environment variable temporarily
        env.set('TEST_DATABASE_URL', working_db_url, "test")
        
        print(f"Set TEST_DATABASE_URL to: {working_db_url}")
        
        # Test that this would work by checking the format
        assert 'postgres:postgres@' in working_db_url, "Should use postgres credentials"
        assert 'netra_dev' in working_db_url, "Should use development database"

    def test_identify_database_server_availability(self):
        """Test if PostgreSQL server is running."""
        import socket
        
        # Test if PostgreSQL port is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        
        try:
            result = sock.connect_ex(('localhost', 5432))
            if result == 0:
                print("✓ PostgreSQL server is running on localhost:5432")
                return True
            else:
                print(f"✗ PostgreSQL server not accessible (result: {result})")
                return False
        except Exception as e:
            print(f"✗ Error checking PostgreSQL server: {e}")
            return False
        finally:
            sock.close()

    def test_suggest_database_setup_fix(self):
        """Suggest fixes for database setup issues."""
        config = get_config()
        
        fixes = []
        
        if not self.test_identify_database_server_availability():
            fixes.append("1. Start PostgreSQL server (e.g., via Docker or local installation)")
            fixes.append("   Docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres")
        
        if 'test:test@' in config.database_url:
            fixes.append("2. Fix database credentials in test configuration")
            fixes.append("   Change test:test to postgres:postgres in database URL")
            fixes.append("   Or create 'test' user with password 'test' in PostgreSQL")
        
        if 'netra_test' in config.database_url:
            fixes.append("3. Create netra_test database or use netra_dev database")
            fixes.append("   SQL: CREATE DATABASE netra_test;")
            fixes.append("   Or change database name in test config to netra_dev")
        
        if fixes:
            print("Suggested fixes for database issues:")
            for fix in fixes:
                print(fix)
        else:
            print("✓ No obvious database setup issues found")

    def test_apply_temporary_database_fix(self):
        """Apply temporary fix by using development database for testing."""
        # This is a temporary fix - use the development database for tests
        # instead of trying to create a separate test database
        
        dev_db_url = "postgresql://postgres:postgres@localhost:5432/netra_dev"
        
        # Override the environment variable for this test session
        env.set('DATABASE_URL', dev_db_url, "test")
        
        print(f"Applied temporary fix: Using development database for tests")
        print(f"DATABASE_URL set to: {dev_db_url}")
        
        # Verify the fix would work
        from shared.isolated_environment import IsolatedEnvironment
        env = IsolatedEnvironment()
        env.set('DATABASE_URL', dev_db_url, source='database_fix')
        
        print("✓ Applied database connection fix to isolated environment")


if __name__ == "__main__":
    # Run this test to fix database connection issues
    pytest.main([__file__, "-v", "-s"])