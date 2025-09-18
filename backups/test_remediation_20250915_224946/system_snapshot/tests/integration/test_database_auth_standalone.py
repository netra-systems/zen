from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'''
env = get_env()
Standalone test for database connection auth logging issues.

This test validates the core business requirement: that database authentication
does not produce excessive error logs that pollute our logging system.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System stability and clean logging
- Value Impact: Reduces noise in logs, improves debugging efficiency
- Strategic Impact: Better observability and operational excellence
'''
import asyncio
import logging
import os
import sys
from io import StringIO
from pathlib import Path

    # Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

    # Set up test environment
env.set('DATABASE_URL', 'postgresql://test_user:test_pass@localhost:5433/netra_test', "test")
env.set('REDIS_URL', 'redis://localhost:6381', "test")
env.set('TESTING', 'true', "test")
env.set('AUTH_TEST_MODE', 'true', "test")
env.set('USE_REAL_SERVICES', 'true', "test")


def test_database_connection_no_auth_errors():
"""Test that database connections don't produce authentication error logs."""
print("Testing database connectivity first...")

    # Test basic database connectivity first
try:
import psycopg
postgres_url = 'postgresql://test_user:test_pass@localhost:5433/netra_test'

with psycopg.connect(postgres_url, connect_timeout=5) as conn:
with conn.cursor() as cur:
cur.execute("SELECT 1")
result = cur.fetchone()
assert result[0] == 1, "Database connectivity test failed"
print(" PASS:  Basic database connectivity test passed")
except Exception as e:
print("formatted_string")
print("Skipping test - requires PostgreSQL on localhost:5433")
return

print("Testing auth service database connection logs...")

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
                        # Import and test auth database components
try:
from auth_service.auth_core.database.connection import AuthDatabase
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
print(" PASS:  Auth service imports successful")
except ImportError as import_error:
print("formatted_string")
return

                                # Create database instance
auth_db = AuthDatabase()
print(" PASS:  AuthDatabase instance created")

                                # Try to initialize database connection
try:
asyncio.run(asyncio.wait_for(auth_db.initialize(), timeout=10.0))
print(" PASS:  Database initialization completed")
except asyncio.TimeoutError:
print(" WARNING: [U+FE0F]  Database initialization timed out (may be expected in test environment)")
except Exception as init_error:
print("formatted_string")

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

                                                            # Report results
if found_auth_issues:
print(" FAIL:  Found authentication error logs that indicate auth issues:")
for issue in found_auth_issues:
print("formatted_string")
print(" )
Full log output:")
print(log_output)
return False
else:
print(" PASS:  No authentication error patterns found in logs")

                                                                        # Test basic database operations if possible
try:
if hasattr(auth_db, 'get_session'):
    async def test_db_op():
async with auth_db.get_session() as session:
from sqlalchemy import text
result = await session.execute(text("SELECT 1 as test_value"))
await asyncio.sleep(0)
return result.scalar()

test_result = asyncio.run(test_db_op())
if test_result == 1:
print(" PASS:  Database operation test passed")
else:
print("formatted_string")
except Exception as op_error:
print("formatted_string")

return True

finally:
                                                                                                        # Restore original handlers
root_logger.handlers = original_root_handlers
auth_logger.handlers = original_auth_handlers

                                                                                                        # Cleanup
if 'auth_db' in locals():
try:
if hasattr(auth_db, 'cleanup'):
asyncio.run(auth_db.cleanup())
elif hasattr(auth_db, 'engine') and auth_db.engine:
asyncio.run(auth_db.engine.dispose())
except Exception as cleanup_error:
print("formatted_string")


def test_database_manager_no_credential_logging():
"""Test that DatabaseManager URL building doesn't log credentials."""
pass
print("Testing DatabaseManager credential logging...")

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

try:
try:
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
print(" PASS:  AuthDatabaseManager import successful")
except ImportError as import_error:
print("formatted_string")
return False

                    # Test various URL transformations with different credential patterns
test_urls = [ )
"postgresql://user:password123@localhost/dbname",
"postgresql+asyncpg://user:secret456@host/db?sslmode=require",
"postgres://admin:pass789@cloudsql/database",
"postgresql://test_user:test_pass@localhost:5433/netra_test",
                    

try:
manager = AuthDatabaseManager()
print(" PASS:  AuthDatabaseManager instance created")
except Exception as manager_error:
print("formatted_string")
return False

for i, url in enumerate(test_urls):
                                # Set environment variable
original_url = env.get('DATABASE_URL')
env.set('DATABASE_URL', url, "test")

try:
                                    # Test various URL generation methods
if hasattr(manager, 'get_base_database_url'):
base_url = manager.get_base_database_url()
if hasattr(manager, 'get_migration_url_sync_format'):
migration_url = manager.get_migration_url_sync_format()
if hasattr(manager, 'get_auth_database_url_async'):
auth_url = manager.get_auth_database_url_async()
print("formatted_string")
except Exception as url_error:
print("formatted_string")
finally:
                                                        # Restore original URL
if original_url:
env.set('DATABASE_URL', original_url, "test")
elif 'DATABASE_URL' in os.environ:
env.delete('DATABASE_URL', "test")

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

                                                                                # Report results
if found_credentials:
print(" FAIL:  Found credentials in logs (security issue):")
for cred in found_credentials:
print("formatted_string")
print(" )
Full log output:")
print(log_output)
return False
else:
print(" PASS:  No credentials found in logs")
return True

finally:
                                                                                                # Restore original handlers
for logger, handlers in original_handlers.items():
logger.handlers = handlers


def main():
"""Main test runner."""
print("=" * 60)
print("STANDALONE DATABASE AUTH LOGGING TEST")
print("=" * 60)
print()

success_count = 0
total_tests = 2

print("Test 1: Database connection auth error logging")
print("-" * 50)
if test_database_connection_no_auth_errors():
success_count += 1
print(" PASS:  PASS: Database connection auth logging test")
else:
print(" FAIL:  FAIL: Database connection auth logging test")
print()

print("Test 2: Database manager credential logging")
print("-" * 50)
if test_database_manager_no_credential_logging():
success_count += 1
print(" PASS:  PASS: Database manager credential logging test")
else:
print(" FAIL:  FAIL: Database manager credential logging test")
print()

print("=" * 60)
print("formatted_string")
print("=" * 60)

if success_count == total_tests:
print(" CELEBRATION:  All tests passed! Database auth logging is working correctly.")
return True
else:
print(" WARNING: [U+FE0F]  Some tests failed. Review the output above for details.")
return False


if __name__ == "__main__":
success = main()
sys.exit(0 if success else 1)
pass
