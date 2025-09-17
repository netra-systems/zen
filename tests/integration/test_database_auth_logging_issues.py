'''
Test to reproduce database connection auth logging issues.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System stability and clean logging
- Value Impact: Reduces noise in logs, improves debugging efficiency
- Strategic Impact: Better observability and operational excellence
'''
import asyncio
import logging
import pytest
from io import StringIO
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

    # Import isolated environment for proper environment management
from shared.isolated_environment import get_env


class TestDatabaseAuthLogging:
    """Test database authentication and connection logging issues."""

    @pytest.fixture
    def setup_isolated_env(self, isolated_test_env):
        """Ensure isolated environment for all tests."""
        self.env = isolated_test_env
        return self.env

        @pytest.fixture
    def require_real_services(self, isolated_test_env):
        """Ensure real services are available for integration tests."""
        pass
        from test_framework.service_availability import require_real_services

    # Configure test environment with proper service URLs
    # Support multiple port configurations for different environments
        test_postgres_port = isolated_test_env.get('TEST_POSTGRES_PORT', '5433')
        test_redis_port = isolated_test_env.get('TEST_REDIS_PORT', '6381')

    # Build service URLs with environment awareness
        postgres_url = 'formatted_string'
        redis_url = 'formatted_string'

    # Set the URLs in isolated environment
        isolated_test_env.set('DATABASE_URL', postgres_url, source="test_database_setup")
        isolated_test_env.set('REDIS_URL', redis_url, source="test_redis_setup")

    # Enable real services mode
        isolated_test_env.set('USE_REAL_SERVICES', 'true', source="test_real_services_flag")

        try:
        require_real_services( )
        ['postgresql', 'redis'],
        timeout=15.0,  # Increased timeout for Docker startup
        postgres_url=postgres_url,
        redis_url=redis_url
        
        except Exception as e:
        pytest.skip("")

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
                    # Import auth database components with better error handling
try:
from auth_service.auth_core.database.connection import AuthDatabase
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
except ImportError as import_error:
pytest.skip("")

                            # Create database instance with explicit configuration
auth_db = AuthDatabase()

                            # Initialize database connection with timeout
try:
await asyncio.wait_for(auth_db.initialize(), timeout=30.0)
except asyncio.TimeoutError:
pytest.fail("Database initialization timed out - check service availability")
except Exception as init_error:
pytest.fail("")

                                        # Get the captured logs
log_output = log_capture.getvalue()

                                        # Check for auth-related error messages that shouldn't be there
unwanted_patterns = [ ]
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
                                        

found_issues = []
for pattern in unwanted_patterns:
if pattern.lower() in log_output.lower():
                                                # Find the actual line for better reporting
for line in log_output.split(" )
"):
if pattern.lower() in line.lower():
found_issues.append("")

                                                        # Assert no unwanted auth error messages
assert not found_issues, f'Found authentication/connection error logs that shouldn't appear:
" + "
".join(found_issues)

                                                            # Verify database connectivity with a simple query
                                                            # This validates that authentication and connection are working
try:
if hasattr(auth_db, 'get_session'):
async with auth_db.get_session() as session:
from sqlalchemy import text
result = await session.execute(text("SELECT 1 as test_value"))
test_result = result.scalar()
assert test_result == 1, ""
elif hasattr(auth_db, 'engine') and auth_db.engine:
                                                                            # Alternative method if get_session not available
async with auth_db.engine.begin() as conn:
from sqlalchemy import text
result = await conn.execute(text("SELECT 1 as test_value"))
test_result = result.scalar()
assert test_result == 1, ""
else:
                                                                                    # Log warning if we can't test connectivity
import logging
logging.getLogger(__name__).warning("Could not verify database connectivity - no session method available")
except Exception as connectivity_error:
pytest.fail("")

finally:
                                                                                            # Restore original handlers
root_logger.handlers = original_root_handlers
auth_logger.handlers = original_auth_handlers

                                                                                            # Enhanced cleanup with proper error handling
if 'auth_db' in locals():
try:
if hasattr(auth_db, 'cleanup'):
await auth_db.cleanup()
elif hasattr(auth_db, 'engine') and auth_db.engine:
await auth_db.engine.dispose()
elif hasattr(auth_db, 'close'):
await auth_db.close()
except Exception as cleanup_error:
                                                                                                                    # Log cleanup errors but don't fail the test
import logging
logging.getLogger(__name__).warning("")

@pytest.mark.asyncio
    async def test_database_manager_url_building_no_auth_logs(self):
"""Test that DatabaseManager URL building doesn't log auth credentials."""
pass
                                                                                                                        # Capture all log output
log_capture = StringIO()
handler = logging.StreamHandler(log_capture)
handler.setLevel(logging.DEBUG)

                                                                                                                        # Get relevant loggers
loggers_to_check = [ ]
logging.getLogger('auth_service.auth_core.database'),
logging.getLogger('dev_launcher'),
logging.getLogger('netra_backend'),
                                                                                                                        

                                                                                                                        # Store original handlers
original_handlers = {logger: logger.handlers[:] for logger in loggers_to_check}

                                                                                                                        # Set up our capture handler
for logger in loggers_to_check:
logger.handlers = [handler]
logger.setLevel(logging.DEBUG)

try:
try:
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
except ImportError as import_error:
pytest.skip("")

                                                                                                                                        # Test various URL transformations with different credential patterns
test_urls = [ ]
"postgresql://user:password@localhost/dbname",
"postgresql+asyncpg://user:secret@host/db?sslmode=require",
"postgres://admin:pass123@cloudsql/database",
"postgresql://test_user:test_pass@localhost:5433/netra_test",  # Match our test config
                                                                                                                                        

try:
manager = AuthDatabaseManager()
except Exception as manager_error:
pytest.skip("")

for url in test_urls:
                                                                                                                                                    # Set environment variable using isolated environment
original_url = self.env.get('DATABASE_URL')
self.env.set('DATABASE_URL', url, source="test_database_manager_url_building")

try:
                                                                                                                                                        # Get various URL formats with better error handling
if hasattr(manager, 'get_base_database_url'):
base_url = manager.get_base_database_url()
if hasattr(manager, 'get_migration_url_sync_format'):
migration_url = manager.get_migration_url_sync_format()
if hasattr(manager, 'get_auth_database_url_async'):
auth_url = manager.get_auth_database_url_async()
except Exception as url_error:
                                                                                                                                                                        # Log but don't fail - this might be expected in some configurations
import logging
logging.getLogger(__name__).debug("")
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
for line in log_output.split(" )
"):
if credential in line:
found_credentials.append("")

                                                                                                                                                                                                    # Assert no credentials in logs
assert not found_credentials, f"Found credentials in logs (security issue):
" + "
".join(found_credentials)

finally:
                                                                                                                                                                                                            # Restore original handlers
for logger, handlers in original_handlers.items():
logger.handlers = handlers

def test_migration_runner_auth_works(self):
"""Test that migration runner can authenticate to database successfully."""
    # This test verifies that migrations can run, proving auth works
    # but we want to ensure no spurious auth error messages appear

try:
from dev_launcher.migration_runner import MigrationRunner
except ImportError as import_error:
pytest.skip("")

            # Capture logs with proper setup
log_capture = StringIO()
handler = logging.StreamHandler(log_capture)
handler.setLevel(logging.DEBUG)

migration_logger = logging.getLogger('dev_launcher.migration_runner')
original_handlers = migration_logger.handlers[:]
migration_logger.handlers = [handler]
migration_logger.setLevel(logging.DEBUG)

try:
project_root = Path(__file__).parent.parent.parent

                # Initialize MigrationRunner with better error handling
try:
runner = MigrationRunner(project_root)
except Exception as runner_error:
pytest.skip("")

                        # Just initialize, don't actually run migrations in test
                        # We're checking for auth error logs during initialization

log_output = log_capture.getvalue()

                        # Check for auth errors that shouldn't be there
auth_errors = [ ]
"authentication failed",
"FATAL",
"permission denied",
                        

found_errors = []
for error in auth_errors:
if error.lower() in log_output.lower():
found_errors.append(error)

if found_errors:
                                    # Provide detailed error information for debugging
error_details = "
".join(["" for error in found_errors])
pytest.fail( )
""
f"This indicates database authentication issues that could affect system stability."
                                        

finally:
migration_logger.handlers = original_handlers


if __name__ == "__main__":
pytest.main([__file__, "-xvs"])
pass
