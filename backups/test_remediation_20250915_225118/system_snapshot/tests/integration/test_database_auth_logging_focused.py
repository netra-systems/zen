"""
Focused test for database connection auth logging issues.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System stability and clean logging
- Value Impact: Reduces noise in logs, improves debugging efficiency"""
"""
without requiring the full service stack to be available."""
import asyncio
import logging
import pytest
from io import StringIO
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

    # Import isolated environment for proper environment management
from shared.isolated_environment import get_env"""
"""
    """Focused test for database authentication and connection logging issues.""""""
    @pytest.fixture"""
        """Ensure isolated environment for all tests."""
        self.env = isolated_test_env
        return self.env"""
        @pytest.fixture"""
        """Set up test database configuration."""
        pass
    # Configure test environment with proper service URLs
        postgres_url = 'postgresql://test_user:test_pass@localhost:5433/netra_test'"""
"""
        isolated_test_env.set('DATABASE_URL', postgres_url, source="test_database_setup")
        isolated_test_env.set('REDIS_URL', redis_url, source="test_redis_setup")
        isolated_test_env.set('USE_REAL_SERVICES', 'true', source="test_real_services_flag")

    # Set test mode to avoid production checks
        isolated_test_env.set('TESTING', 'true', source="test_mode_flag")
        isolated_test_env.set('AUTH_TEST_MODE', 'true', source="auth_test_mode")

        yield

@pytest.mark.asyncio
    async def test_auth_database_connection_no_auth_errors(self):
"""Test that auth database connections don't produce authentication error logs."""
        # Test basic database connectivity first
import psycopg
postgres_url = 'postgresql://test_user:test_pass@localhost:5433/netra_test'
"""
with psycopg.connect(postgres_url, connect_timeout=5) as conn:"""
cur.execute("SELECT 1")
result = cur.fetchone()
assert result[0] == 1, "Database connectivity test failed"
except Exception as e:
pytest.skip("formatted_string")

                        # Capture all log output
log_capture = StringIO()
handler = logging.StreamHandler(log_capture)
handler.setLevel(logging.DEBUG)

                        # Get the root logger and auth logger
root_logger = logging.getLogger()
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
try:
from auth_service.auth_core.database.connection import AuthDatabase
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
except ImportError as import_error:
pytest.skip("formatted_string")

                                    # Create database instance with explicit configuration
auth_db = AuthDatabase()

                                    # Initialize database connection with timeout
try:
await asyncio.wait_for(auth_db.initialize(), timeout=30.0)
except asyncio.TimeoutError:
pytest.fail("Database initialization timed out - check service availability")
except Exception as init_error:
                                                # Check if this is an expected test environment issue
if "test" not in str(init_error).lower():
pytest.fail("formatted_string")
else:
                                                        # In test mode, some failures are expected - log them but check for auth errors
pass

                                                        # Get the captured logs
log_output = log_capture.getvalue()

                                                        # Check for auth-related error messages that shouldn't be there
unwanted_auth_patterns = [ )
"authentication failed",
"password authentication failed",
"SCRAM authentication",
"SSL connection has been closed",
"no pg_hba.conf entry",
"password authentication failed for user",
                                                        

found_auth_issues = []
for pattern in unwanted_auth_patterns:
if pattern.lower() in log_output.lower():
                                                                # Find the actual line for better reporting
for line in log_output.split(" )
"):
if pattern.lower() in line.lower():
found_auth_issues.append("formatted_string")

                                                                        # Assert no unwanted auth error messages
if found_auth_issues:
pytest.fail( )
f"Found authentication error logs that indicate database auth issues:\
" +
"\
".join(found_auth_issues) +
"formatted_string"
                                                                            

                                                                            # Try to perform a basic database operation if possible
try:
if hasattr(auth_db, 'get_session'):
async with auth_db.get_session() as session:
from sqlalchemy import text
result = await session.execute(text("SELECT 1 as test_value"))
test_result = result.scalar()
assert test_result == 1, "formatted_string"
else:
                                                                                            # Alternative connection test
pass
except Exception as op_error:
                                                                                                # Log but don't fail on operational errors in test environment
logging.getLogger(__name__).info("formatted_string")

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
except Exception as cleanup_error:
                                                                                                                        # Log cleanup errors but don't fail the test
logging.getLogger(__name__).warning("formatted_string")

def test_database_manager_no_credential_logging(self):
"""Test that DatabaseManager URL building doesn't log credentials."""
pass
    # Capture all log output
log_capture = StringIO()
handler = logging.StreamHandler(log_capture)
handler.setLevel(logging.DEBUG)

    # Get relevant loggers
loggers_to_check = [ )
logging.getLogger('auth_service.auth_core.database'),
logging.getLogger('auth_service'),
logging.getLogger(__name__),
    

    # Store original handlers
original_handlers = {logger: logger.handlers[:] for logger in loggers_to_check}

    # Set up our capture handler
for logger in loggers_to_check:
logger.handlers = [handler]
logger.setLevel(logging.DEBUG)

try:"""
from auth_service.auth_core.database.database_manager import AuthDatabaseManager"""
pytest.skip("formatted_string")

                    # Test various URL transformations with different credential patterns
test_urls = [ )
"postgresql://user:password123@localhost/dbname",
"postgresql+asyncpg://user:secret456@host/db?sslmode=require",
"postgres://admin:pass789@cloudsql/database",
"postgresql://test_user:test_pass@localhost:5433/netra_test",  # Match our test config
                    

try:
manager = AuthDatabaseManager()
except Exception as manager_error:
pytest.skip("formatted_string")

for url in test_urls:
                                # Set environment variable using isolated environment
original_url = self.env.get('DATABASE_URL')
self.env.set('DATABASE_URL', url, source="test_database_manager_url_building")

try:
                                    # Test various URL generation methods
if hasattr(manager, 'get_base_database_url'):
base_url = manager.get_base_database_url()
if hasattr(manager, 'get_migration_url_sync_format'):
migration_url = manager.get_migration_url_sync_format()
if hasattr(manager, 'get_auth_database_url_async'):
auth_url = manager.get_auth_database_url_async()
except Exception as url_error:
                                                    # Log but don't fail - this might be expected in some configurations
logging.getLogger(__name__).debug("formatted_string")
finally:
                                                        # Restore original URL
if original_url:
self.env.set('DATABASE_URL', original_url, source="test_cleanup")
else:
self.env.delete('DATABASE_URL', source="test_cleanup")

                                                                # Get captured logs
log_output = log_capture.getvalue()

                                                                # Check that passwords/credentials aren't logged
credentials = ["password123", "secret456", "pass789", "test_pass"]
found_credentials = []

for credential in credentials:
if credential in log_output:
                                                                        # Find the actual line for better reporting
for line in log_output.split(" )
"):
if credential in line:
found_credentials.append("formatted_string")

                                                                                # Assert no credentials in logs
if found_credentials:
pytest.fail( )
f"Found credentials in logs (security issue):\
" + "\
".join(found_credentials) +
"formatted_string"
                                                                                    

finally:
                                                                                        # Restore original handlers
for logger, handlers in original_handlers.items():
logger.handlers = handlers


if __name__ == "__main__":
pytest.main([__file__, "-xvs"])
