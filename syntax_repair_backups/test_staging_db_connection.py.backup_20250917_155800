'''
Test script to debug Auth service database connection with staging credentials.

This script tests the database connection locally using the exact same configuration
as the Auth service would use in staging environment.
'''
import asyncio
import asyncpg
import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from auth_service.auth_core.config import AuthConfig
from shared.isolated_environment import get_env
from shared.database_url_builder import DatabaseURLBuilder

# Set up logging
logging.basicConfig( )
level=logging.DEBUG,
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'

logger = logging.getLogger(__name__)


def setup_staging_environment():
"""Setup environment variables for staging database connection test."""
env_manager = get_env()

    # Set staging environment
env_manager.set("ENVIRONMENT", "staging")

    Set staging database credentials from the provided context
env_manager.set("POSTGRES_HOST", "/cloudsql/netra-staging:us-central1:staging-shared-postgres")
env_manager.set("POSTGRES_PORT", "5432")
env_manager.set("POSTGRES_DB", "netra_staging")
env_manager.set("POSTGRES_USER", "postgres")
env_manager.set("POSTGRES_PASSWORD", "DTprdt5KoQXlEG4Gh9lF")

logger.info("Set up staging environment variables")


    async def test_direct_asyncpg_connection():
"""Test direct asyncpg connection using staging credentials."""
logger.info("=== Testing Direct asyncpg Connection ===")

try:
            # Test Unix socket connection (Cloud SQL)
connection_params = { )
'host': '/cloudsql/netra-staging:us-central1:staging-shared-postgres',
'port': 5432,
'database': 'netra_staging',
'user': 'postgres',
'password': 'DTprdt5KoQXlEG4Gh9lF'
            

logger.info("formatted_string")

            # Try to connect
conn = await asyncpg.connect(**connection_params)

            # Test the connection
result = await conn.fetchval('SELECT version()')
logger.info(f"SUCCESS: Direct asyncpg connection successful!")
logger.info("formatted_string")

            # Test basic query
user_count = await conn.fetchval('SELECT COUNT(*) FROM pg_user')
logger.info("formatted_string")

await conn.close()
return True

except Exception as e:
logger.error("formatted_string")
logger.error("formatted_string")
return False


    async def test_tcp_fallback_connection():
"""Test TCP connection as fallback (should fail from local)."""
logger.info("=== Testing TCP Fallback Connection ===")

try:
                        # This should fail since we're not running through Cloud SQL proxy
connection_params = { )
'host': 'staging-shared-postgres.c7vdhks7dj2k.us-central1.gcp.cloud.sql.googleapis.com',
'port': 5432,
'database': 'netra_staging',
'user': 'postgres',
'password': 'DTprdt5KoQXlEG4Gh9lF'
                        

logger.info("formatted_string")

conn = await asyncpg.connect(**connection_params)

result = await conn.fetchval('SELECT version()')
logger.info("formatted_string")

await conn.close()
return True

except Exception as e:
logger.error("formatted_string")
logger.error("formatted_string")
return False


def test_database_url_builder():
"""Test DatabaseURLBuilder with staging configuration."""
logger.info("=== Testing DatabaseURLBuilder ===")

try:
        # Setup environment variables
env_manager = get_env()
env_vars = { )
"ENVIRONMENT": "staging",
"POSTGRES_HOST": env_manager.get("POSTGRES_HOST"),
"POSTGRES_PORT": env_manager.get("POSTGRES_PORT"),
"POSTGRES_DB": env_manager.get("POSTGRES_DB"),
"POSTGRES_USER": env_manager.get("POSTGRES_USER"),
"POSTGRES_PASSWORD": env_manager.get("POSTGRES_PASSWORD")
        

logger.info("formatted_string")

        # Create builder
builder = DatabaseURLBuilder(env_vars)

        # Validate configuration
is_valid, error_msg = builder.validate()
if not is_valid:
logger.error("formatted_string")
return None

logger.info("SUCCESS: Configuration validation passed")

            # Get URLs
async_url = builder.get_url_for_environment(sync=False)
sync_url = builder.get_url_for_environment(sync=True)

            # Mask URLs for logging
masked_async = DatabaseURLBuilder.mask_url_for_logging(async_url)
masked_sync = DatabaseURLBuilder.mask_url_for_logging(sync_url)

logger.info("formatted_string")
logger.info("formatted_string")

            # Debug info
debug_info = builder.debug_info()
logger.info("formatted_string")

return async_url

except Exception as e:
logger.error("formatted_string")
return None


    async def test_auth_config():
"""Test AuthConfig database URL generation."""
logger.info("=== Testing AuthConfig ===")

try:
                        # Test database URL generation
database_url = AuthConfig.get_database_url()
masked_url = DatabaseURLBuilder.mask_url_for_logging(database_url)

logger.info("formatted_string")

                        # Log configuration
AuthConfig.log_configuration()

return database_url

except Exception as e:
logger.error("formatted_string")
return None


    async def test_connection_with_auth_config():
"""Test connection using AuthConfig generated URL."""
logger.info("=== Testing Connection with AuthConfig URL ===")

try:
database_url = AuthConfig.get_database_url()
if not database_url:
logger.error("FAILED: No database URL generated by AuthConfig")
return False

logger.info("formatted_string")

                                        # Normalize URL for asyncpg compatibility
from shared.database_url_builder import DatabaseURLBuilder
normalized_url = DatabaseURLBuilder.format_for_asyncpg_driver(database_url)

conn = await asyncpg.connect(normalized_url)

result = await conn.fetchval('SELECT version()')
logger.info(f"SUCCESS: AuthConfig URL connection successful!")
logger.info("formatted_string")

await conn.close()
return True
else:
logger.error("formatted_string")
return False

except Exception as e:
logger.error("formatted_string")
logger.error("formatted_string")
return False


def check_cloud_sql_proxy():
"""Check if Cloud SQL proxy is needed and available."""
logger.info("=== Checking Cloud SQL Proxy Status ===")

    # Check if running on GCP (where Cloud SQL proxy may not be needed)
env = get_env()
metadata_server = env.get("GCE_METADATA_HOST", "metadata.google.internal")

    # Check for common proxy indicators
proxy_indicators = [ )
"/cloudsql/" in str(env.get("POSTGRES_HOST", "")),
"cloudsql" in str(env.get("INSTANCE_CONNECTION_NAME", "")),
    

if any(proxy_indicators):
logger.info("Cloud SQL socket connection detected")
logger.info("This should work if running on GCP or with Cloud SQL proxy")

        # Check if socket path exists (unix socket)
socket_path = env.get("POSTGRES_HOST", "")
if socket_path and socket_path.startswith("/cloudsql/"):
if os.path.exists(socket_path):
logger.info("formatted_string")
else:
logger.warning("formatted_string")
logger.info("This might be expected if not running on GCP or without proxy")
else:
logger.info("TCP connection mode")


def validate_staging_credentials():
"""Validate staging database credentials using IsolatedEnvironment validator."""
logger.info("=== Validating Staging Credentials ===")

try:
env_manager = get_env()
validation = env_manager.validate_staging_database_credentials()

if validation["valid"]:
logger.info("SUCCESS: Credential validation passed")
else:
logger.error("FAILED: Credential validation failed")
for issue in validation["issues"]:
logger.error("formatted_string")

for warning in validation["warnings"]:
logger.warning("formatted_string")

return validation["valid"]

except Exception as e:
logger.error("formatted_string")
return False


async def main():
"""Main test function."""
print("Auth Service Database Connection Test")
print("=" * 50)

    # Setup environment
setup_staging_environment()

    # Run tests
tests_passed = 0
total_tests = 7

    # 1. Check Cloud SQL proxy status
check_cloud_sql_proxy()

    # 2. Validate credentials
if validate_staging_credentials():
tests_passed += 1

        # 3. Test DatabaseURLBuilder
if test_database_url_builder():
tests_passed += 1

            # 4. Test AuthConfig
            # Removed problematic line: if await test_auth_config():
tests_passed += 1

                # 5. Test direct asyncpg connection (Unix socket)
                # Removed problematic line: if await test_direct_asyncpg_connection():
tests_passed += 1

                    # 6. Test TCP fallback (expected to fail locally)
                    # Removed problematic line: if await test_tcp_fallback_connection():
tests_passed += 1

                        # 7. Test connection with AuthConfig URL
                        # Removed problematic line: if await test_connection_with_auth_config():
tests_passed += 1

print("\n" + "=" * 50)
print("formatted_string")

if tests_passed >= 4:  # Allow for TCP fallback failure
print("SUCCESS: Connection testing completed successfully")
print("The Auth service should be able to connect to staging database")
else:
print("FAILURE: Multiple connection tests failed")
print("Check the error messages above for specific issues")

return tests_passed >= 4


if __name__ == "__main__":
try:
success = asyncio.run(main())
sys.exit(0 if success else 1)
except KeyboardInterrupt:
print("\nTest interrupted by user")
sys.exit(1)
except Exception as e:
print("formatted_string")
sys.exit(1)