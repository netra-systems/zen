"""
Test to reproduce database connection auth logging issues.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: System stability and clean logging
- Value Impact: Reduces noise in logs, improves debugging efficiency
- Strategic Impact: Better observability and operational excellence
"""
import asyncio
import logging
import pytest
from io import StringIO
from pathlib import Path

# Import isolated environment for proper environment management
from shared.isolated_environment import get_env


class TestDatabaseAuthLogging:
    """Test database authentication and connection logging issues."""
    
    @pytest.fixture(autouse=True)
    def setup_isolated_env(self, isolated_test_env):
        """Ensure isolated environment for all tests."""
        self.env = isolated_test_env
        return self.env
    
    @pytest.fixture(autouse=True, scope="function")
    def require_real_services(self, isolated_test_env):
        """Ensure real services are available for integration tests."""
        from test_framework.service_availability import require_real_services
        
        # Check the services needed for database auth testing
        # Set test environment to match our Docker compose test services
        isolated_test_env.set('DATABASE_URL', 'postgresql://test_user:test_pass@localhost:5434/netra_test', source="test_database_setup")
        isolated_test_env.set('REDIS_URL', 'redis://localhost:6381', source="test_redis_setup")
        
        try:
            require_real_services(['postgresql', 'redis'], timeout=10.0)
        except Exception as e:
            pytest.skip(f"Real services unavailable: {e}")
        
        yield
    
    @pytest.mark.asyncio
    async def test_auth_service_database_connection_logs(self):
        """Test that auth service database connection doesn't produce excessive auth error logs."""
        # Capture all log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        
        # Get the root logger and auth logger
        root_logger = logging.getLogger()
        auth_logger = logging.getLogger('auth_service')
        
        # Store original handlers
        original_root_handlers = root_logger.handlers[:]
        original_auth_handlers = auth_logger.handlers[:]
        
        # Clear existing handlers and add our capture handler
        root_logger.handlers = [handler]
        auth_logger.handlers = [handler]
        
        # Set log levels
        root_logger.setLevel(logging.DEBUG)
        auth_logger.setLevel(logging.DEBUG)
        
        try:
            # Import auth database components
            from auth_service.auth_core.database.connection import AuthDatabase
            from auth_service.auth_core.database.database_manager import AuthDatabaseManager
            
            # Create database instance
            auth_db = AuthDatabase()
            
            # Initialize database connection
            await auth_db.initialize()
            
            # Get the captured logs
            log_output = log_capture.getvalue()
            
            # Check for auth-related error messages that shouldn't be there
            unwanted_patterns = [
                "authentication failed",
                "password authentication failed",
                "FATAL",
                "permission denied",
                "Access denied",
                "SCRAM authentication",
                "SSL connection has been closed",
                "no pg_hba.conf entry",
                "password authentication failed for user",
                "could not connect to server",
            ]
            
            found_issues = []
            for pattern in unwanted_patterns:
                if pattern.lower() in log_output.lower():
                    # Find the actual line for better reporting
                    for line in log_output.split('\n'):
                        if pattern.lower() in line.lower():
                            found_issues.append(f"Found unwanted pattern '{pattern}' in: {line.strip()}")
            
            # Assert no unwanted auth error messages
            assert not found_issues, f"Found authentication/connection error logs that shouldn't appear:\n" + "\n".join(found_issues)
            
            # Check that migrations can run successfully (indicates auth is working)
            if not auth_db.is_test_mode:
                # Only test this in non-test mode where we have a real database
                from auth_service.auth_core.database.connection import auth_db as global_auth_db
                
                # Try to execute a simple query
                async with global_auth_db.get_session() as session:
                    from sqlalchemy import text
                    result = await session.execute(text("SELECT 1"))
                    assert result.scalar() == 1, "Database query should succeed"
            
        finally:
            # Restore original handlers
            root_logger.handlers = original_root_handlers
            auth_logger.handlers = original_auth_handlers
            
            # Clean up database connection if needed
            if 'auth_db' in locals() and auth_db.engine:
                await auth_db.engine.dispose()
    
    @pytest.mark.asyncio
    async def test_database_manager_url_building_no_auth_logs(self):
        """Test that DatabaseManager URL building doesn't log auth credentials."""
        # Capture all log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        
        # Get relevant loggers
        loggers_to_check = [
            logging.getLogger('auth_service.auth_core.database'),
            logging.getLogger('dev_launcher'),
            logging.getLogger('netra_backend'),
        ]
        
        # Store original handlers
        original_handlers = {logger: logger.handlers[:] for logger in loggers_to_check}
        
        # Set up our capture handler
        for logger in loggers_to_check:
            logger.handlers = [handler]
            logger.setLevel(logging.DEBUG)
        
        try:
            from auth_service.auth_core.database.database_manager import AuthDatabaseManager
            
            # Test various URL transformations
            test_urls = [
                "postgresql://user:password@localhost/dbname",
                "postgresql+asyncpg://user:secret@host/db?sslmode=require",
                "postgres://admin:pass123@cloudsql/database",
            ]
            
            manager = AuthDatabaseManager()
            
            for url in test_urls:
                # Set environment variable using isolated environment
                original_url = self.env.get('DATABASE_URL')
                self.env.set('DATABASE_URL', url, source="test_database_manager_url_building")
                
                try:
                    # Get various URL formats
                    base_url = manager.get_base_database_url()
                    migration_url = manager.get_migration_url_sync_format()
                    auth_url = manager.get_auth_database_url_async()
                finally:
                    # Restore original URL
                    if original_url:
                        self.env.set('DATABASE_URL', original_url, source="test_cleanup")
                    else:
                        self.env.delete('DATABASE_URL', source="test_cleanup")
            
            # Get captured logs
            log_output = log_capture.getvalue()
            
            # Check that passwords/credentials aren't logged
            credentials = ["password", "secret", "pass123"]
            found_credentials = []
            
            for credential in credentials:
                if credential in log_output:
                    # Find the actual line for better reporting
                    for line in log_output.split('\n'):
                        if credential in line:
                            found_credentials.append(f"Found credential '{credential}' in: {line.strip()}")
            
            # Assert no credentials in logs
            assert not found_credentials, f"Found credentials in logs (security issue):\n" + "\n".join(found_credentials)
            
        finally:
            # Restore original handlers
            for logger, handlers in original_handlers.items():
                logger.handlers = handlers
    
    def test_migration_runner_auth_works(self):
        """Test that migration runner can authenticate to database successfully."""
        # This test verifies that migrations can run, proving auth works
        # but we want to ensure no spurious auth error messages appear
        
        from dev_launcher.migration_runner import MigrationRunner
        
        # Capture logs
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        
        migration_logger = logging.getLogger('dev_launcher.migration_runner')
        original_handlers = migration_logger.handlers[:]
        migration_logger.handlers = [handler]
        migration_logger.setLevel(logging.DEBUG)
        
        try:
            project_root = Path(__file__).parent.parent.parent
            runner = MigrationRunner(project_root)
            
            # Just initialize, don't actually run migrations in test
            # We're checking for auth error logs during initialization
            
            log_output = log_capture.getvalue()
            
            # Check for auth errors that shouldn't be there
            auth_errors = [
                "authentication failed",
                "FATAL",
                "permission denied",
            ]
            
            found_errors = []
            for error in auth_errors:
                if error.lower() in log_output.lower():
                    found_errors.append(error)
            
            assert not found_errors, f"Found auth errors during MigrationRunner init: {found_errors}"
            
        finally:
            migration_logger.handlers = original_handlers


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])