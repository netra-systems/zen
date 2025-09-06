# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Test script to debug Auth service database connection with staging credentials.

# REMOVED_SYNTAX_ERROR: This script tests the database connection locally using the exact same configuration
# REMOVED_SYNTAX_ERROR: as the Auth service would use in staging environment.
# REMOVED_SYNTAX_ERROR: '''
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


# REMOVED_SYNTAX_ERROR: def setup_staging_environment():
    # REMOVED_SYNTAX_ERROR: """Setup environment variables for staging database connection test."""
    # REMOVED_SYNTAX_ERROR: env_manager = get_env()

    # Set staging environment
    # REMOVED_SYNTAX_ERROR: env_manager.set("ENVIRONMENT", "staging")

    # Set staging database credentials from the provided context
    # REMOVED_SYNTAX_ERROR: env_manager.set("POSTGRES_HOST", "/cloudsql/netra-staging:us-central1:staging-shared-postgres")
    # REMOVED_SYNTAX_ERROR: env_manager.set("POSTGRES_PORT", "5432")
    # REMOVED_SYNTAX_ERROR: env_manager.set("POSTGRES_DB", "netra_staging")
    # REMOVED_SYNTAX_ERROR: env_manager.set("POSTGRES_USER", "postgres")
    # REMOVED_SYNTAX_ERROR: env_manager.set("POSTGRES_PASSWORD", "DTprdt5KoQXlEG4Gh9lF")

    # REMOVED_SYNTAX_ERROR: logger.info("Set up staging environment variables")


    # Removed problematic line: async def test_direct_asyncpg_connection():
        # REMOVED_SYNTAX_ERROR: """Test direct asyncpg connection using staging credentials."""
        # REMOVED_SYNTAX_ERROR: logger.info("=== Testing Direct asyncpg Connection ===")

        # REMOVED_SYNTAX_ERROR: try:
            # Test Unix socket connection (Cloud SQL)
            # REMOVED_SYNTAX_ERROR: connection_params = { )
            # REMOVED_SYNTAX_ERROR: 'host': '/cloudsql/netra-staging:us-central1:staging-shared-postgres',
            # REMOVED_SYNTAX_ERROR: 'port': 5432,
            # REMOVED_SYNTAX_ERROR: 'database': 'netra_staging',
            # REMOVED_SYNTAX_ERROR: 'user': 'postgres',
            # REMOVED_SYNTAX_ERROR: 'password': 'DTprdt5KoQXlEG4Gh9lF'
            

            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

            # Try to connect
            # REMOVED_SYNTAX_ERROR: conn = await asyncpg.connect(**connection_params)

            # Test the connection
            # REMOVED_SYNTAX_ERROR: result = await conn.fetchval('SELECT version()')
            # REMOVED_SYNTAX_ERROR: logger.info(f"SUCCESS: Direct asyncpg connection successful!")
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

            # Test basic query
            # REMOVED_SYNTAX_ERROR: user_count = await conn.fetchval('SELECT COUNT(*) FROM pg_user')
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

            # REMOVED_SYNTAX_ERROR: await conn.close()
            # REMOVED_SYNTAX_ERROR: return True

            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                # REMOVED_SYNTAX_ERROR: return False


                # Removed problematic line: async def test_tcp_fallback_connection():
                    # REMOVED_SYNTAX_ERROR: """Test TCP connection as fallback (should fail from local)."""
                    # REMOVED_SYNTAX_ERROR: logger.info("=== Testing TCP Fallback Connection ===")

                    # REMOVED_SYNTAX_ERROR: try:
                        # This should fail since we're not running through Cloud SQL proxy
                        # REMOVED_SYNTAX_ERROR: connection_params = { )
                        # REMOVED_SYNTAX_ERROR: 'host': 'staging-shared-postgres.c7vdhks7dj2k.us-central1.gcp.cloud.sql.googleapis.com',
                        # REMOVED_SYNTAX_ERROR: 'port': 5432,
                        # REMOVED_SYNTAX_ERROR: 'database': 'netra_staging',
                        # REMOVED_SYNTAX_ERROR: 'user': 'postgres',
                        # REMOVED_SYNTAX_ERROR: 'password': 'DTprdt5KoQXlEG4Gh9lF'
                        

                        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                        # REMOVED_SYNTAX_ERROR: conn = await asyncpg.connect(**connection_params)

                        # REMOVED_SYNTAX_ERROR: result = await conn.fetchval('SELECT version()')
                        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                        # REMOVED_SYNTAX_ERROR: await conn.close()
                        # REMOVED_SYNTAX_ERROR: return True

                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                            # REMOVED_SYNTAX_ERROR: return False


# REMOVED_SYNTAX_ERROR: def test_database_url_builder():
    # REMOVED_SYNTAX_ERROR: """Test DatabaseURLBuilder with staging configuration."""
    # REMOVED_SYNTAX_ERROR: logger.info("=== Testing DatabaseURLBuilder ===")

    # REMOVED_SYNTAX_ERROR: try:
        # Setup environment variables
        # REMOVED_SYNTAX_ERROR: env_manager = get_env()
        # REMOVED_SYNTAX_ERROR: env_vars = { )
        # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "staging",
        # REMOVED_SYNTAX_ERROR: "POSTGRES_HOST": env_manager.get("POSTGRES_HOST"),
        # REMOVED_SYNTAX_ERROR: "POSTGRES_PORT": env_manager.get("POSTGRES_PORT"),
        # REMOVED_SYNTAX_ERROR: "POSTGRES_DB": env_manager.get("POSTGRES_DB"),
        # REMOVED_SYNTAX_ERROR: "POSTGRES_USER": env_manager.get("POSTGRES_USER"),
        # REMOVED_SYNTAX_ERROR: "POSTGRES_PASSWORD": env_manager.get("POSTGRES_PASSWORD")
        

        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

        # Create builder
        # REMOVED_SYNTAX_ERROR: builder = DatabaseURLBuilder(env_vars)

        # Validate configuration
        # REMOVED_SYNTAX_ERROR: is_valid, error_msg = builder.validate()
        # REMOVED_SYNTAX_ERROR: if not is_valid:
            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
            # REMOVED_SYNTAX_ERROR: return None

            # REMOVED_SYNTAX_ERROR: logger.info("SUCCESS: Configuration validation passed")

            # Get URLs
            # REMOVED_SYNTAX_ERROR: async_url = builder.get_url_for_environment(sync=False)
            # REMOVED_SYNTAX_ERROR: sync_url = builder.get_url_for_environment(sync=True)

            # Mask URLs for logging
            # REMOVED_SYNTAX_ERROR: masked_async = DatabaseURLBuilder.mask_url_for_logging(async_url)
            # REMOVED_SYNTAX_ERROR: masked_sync = DatabaseURLBuilder.mask_url_for_logging(sync_url)

            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

            # Debug info
            # REMOVED_SYNTAX_ERROR: debug_info = builder.debug_info()
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

            # REMOVED_SYNTAX_ERROR: return async_url

            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                # REMOVED_SYNTAX_ERROR: return None


                # Removed problematic line: async def test_auth_config():
                    # REMOVED_SYNTAX_ERROR: """Test AuthConfig database URL generation."""
                    # REMOVED_SYNTAX_ERROR: logger.info("=== Testing AuthConfig ===")

                    # REMOVED_SYNTAX_ERROR: try:
                        # Test database URL generation
                        # REMOVED_SYNTAX_ERROR: database_url = AuthConfig.get_database_url()
                        # REMOVED_SYNTAX_ERROR: masked_url = DatabaseURLBuilder.mask_url_for_logging(database_url)

                        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                        # Log configuration
                        # REMOVED_SYNTAX_ERROR: AuthConfig.log_configuration()

                        # REMOVED_SYNTAX_ERROR: return database_url

                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                            # REMOVED_SYNTAX_ERROR: return None


                            # Removed problematic line: async def test_connection_with_auth_config():
                                # REMOVED_SYNTAX_ERROR: """Test connection using AuthConfig generated URL."""
                                # REMOVED_SYNTAX_ERROR: logger.info("=== Testing Connection with AuthConfig URL ===")

                                # REMOVED_SYNTAX_ERROR: try:
                                    # REMOVED_SYNTAX_ERROR: database_url = AuthConfig.get_database_url()
                                    # REMOVED_SYNTAX_ERROR: if not database_url:
                                        # REMOVED_SYNTAX_ERROR: logger.error("FAILED: No database URL generated by AuthConfig")
                                        # REMOVED_SYNTAX_ERROR: return False

                                        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                        # Normalize URL for asyncpg compatibility
                                        # REMOVED_SYNTAX_ERROR: from shared.database_url_builder import DatabaseURLBuilder
                                        # REMOVED_SYNTAX_ERROR: normalized_url = DatabaseURLBuilder.format_for_asyncpg_driver(database_url)

                                        # REMOVED_SYNTAX_ERROR: conn = await asyncpg.connect(normalized_url)

                                        # REMOVED_SYNTAX_ERROR: result = await conn.fetchval('SELECT version()')
                                        # REMOVED_SYNTAX_ERROR: logger.info(f"SUCCESS: AuthConfig URL connection successful!")
                                        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                        # REMOVED_SYNTAX_ERROR: await conn.close()
                                        # REMOVED_SYNTAX_ERROR: return True
                                        # REMOVED_SYNTAX_ERROR: else:
                                            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                                            # REMOVED_SYNTAX_ERROR: return False

                                            # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                                                # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                                                # REMOVED_SYNTAX_ERROR: return False


# REMOVED_SYNTAX_ERROR: def check_cloud_sql_proxy():
    # REMOVED_SYNTAX_ERROR: """Check if Cloud SQL proxy is needed and available."""
    # REMOVED_SYNTAX_ERROR: logger.info("=== Checking Cloud SQL Proxy Status ===")

    # Check if running on GCP (where Cloud SQL proxy may not be needed)
    # REMOVED_SYNTAX_ERROR: env = get_env()
    # REMOVED_SYNTAX_ERROR: metadata_server = env.get("GCE_METADATA_HOST", "metadata.google.internal")

    # Check for common proxy indicators
    # REMOVED_SYNTAX_ERROR: proxy_indicators = [ )
    # REMOVED_SYNTAX_ERROR: "/cloudsql/" in str(env.get("POSTGRES_HOST", "")),
    # REMOVED_SYNTAX_ERROR: "cloudsql" in str(env.get("INSTANCE_CONNECTION_NAME", "")),
    

    # REMOVED_SYNTAX_ERROR: if any(proxy_indicators):
        # REMOVED_SYNTAX_ERROR: logger.info("Cloud SQL socket connection detected")
        # REMOVED_SYNTAX_ERROR: logger.info("This should work if running on GCP or with Cloud SQL proxy")

        # Check if socket path exists (unix socket)
        # REMOVED_SYNTAX_ERROR: socket_path = env.get("POSTGRES_HOST", "")
        # REMOVED_SYNTAX_ERROR: if socket_path and socket_path.startswith("/cloudsql/"):
            # REMOVED_SYNTAX_ERROR: if os.path.exists(socket_path):
                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
                # REMOVED_SYNTAX_ERROR: else:
                    # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")
                    # REMOVED_SYNTAX_ERROR: logger.info("This might be expected if not running on GCP or without proxy")
                    # REMOVED_SYNTAX_ERROR: else:
                        # REMOVED_SYNTAX_ERROR: logger.info("TCP connection mode")


# REMOVED_SYNTAX_ERROR: def validate_staging_credentials():
    # REMOVED_SYNTAX_ERROR: """Validate staging database credentials using IsolatedEnvironment validator."""
    # REMOVED_SYNTAX_ERROR: logger.info("=== Validating Staging Credentials ===")

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: env_manager = get_env()
        # REMOVED_SYNTAX_ERROR: validation = env_manager.validate_staging_database_credentials()

        # REMOVED_SYNTAX_ERROR: if validation["valid"]:
            # REMOVED_SYNTAX_ERROR: logger.info("SUCCESS: Credential validation passed")
            # REMOVED_SYNTAX_ERROR: else:
                # REMOVED_SYNTAX_ERROR: logger.error("FAILED: Credential validation failed")
                # REMOVED_SYNTAX_ERROR: for issue in validation["issues"]:
                    # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")

                    # REMOVED_SYNTAX_ERROR: for warning in validation["warnings"]:
                        # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                        # REMOVED_SYNTAX_ERROR: return validation["valid"]

                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                            # REMOVED_SYNTAX_ERROR: return False


# REMOVED_SYNTAX_ERROR: async def main():
    # REMOVED_SYNTAX_ERROR: """Main test function."""
    # REMOVED_SYNTAX_ERROR: print("Auth Service Database Connection Test")
    # REMOVED_SYNTAX_ERROR: print("=" * 50)

    # Setup environment
    # REMOVED_SYNTAX_ERROR: setup_staging_environment()

    # Run tests
    # REMOVED_SYNTAX_ERROR: tests_passed = 0
    # REMOVED_SYNTAX_ERROR: total_tests = 7

    # 1. Check Cloud SQL proxy status
    # REMOVED_SYNTAX_ERROR: check_cloud_sql_proxy()

    # 2. Validate credentials
    # REMOVED_SYNTAX_ERROR: if validate_staging_credentials():
        # REMOVED_SYNTAX_ERROR: tests_passed += 1

        # 3. Test DatabaseURLBuilder
        # REMOVED_SYNTAX_ERROR: if test_database_url_builder():
            # REMOVED_SYNTAX_ERROR: tests_passed += 1

            # 4. Test AuthConfig
            # Removed problematic line: if await test_auth_config():
                # REMOVED_SYNTAX_ERROR: tests_passed += 1

                # 5. Test direct asyncpg connection (Unix socket)
                # Removed problematic line: if await test_direct_asyncpg_connection():
                    # REMOVED_SYNTAX_ERROR: tests_passed += 1

                    # 6. Test TCP fallback (expected to fail locally)
                    # Removed problematic line: if await test_tcp_fallback_connection():
                        # REMOVED_SYNTAX_ERROR: tests_passed += 1

                        # 7. Test connection with AuthConfig URL
                        # Removed problematic line: if await test_connection_with_auth_config():
                            # REMOVED_SYNTAX_ERROR: tests_passed += 1

                            # REMOVED_SYNTAX_ERROR: print("\n" + "=" * 50)
                            # REMOVED_SYNTAX_ERROR: print("formatted_string")

                            # REMOVED_SYNTAX_ERROR: if tests_passed >= 4:  # Allow for TCP fallback failure
                            # REMOVED_SYNTAX_ERROR: print("SUCCESS: Connection testing completed successfully")
                            # REMOVED_SYNTAX_ERROR: print("The Auth service should be able to connect to staging database")
                            # REMOVED_SYNTAX_ERROR: else:
                                # REMOVED_SYNTAX_ERROR: print("FAILURE: Multiple connection tests failed")
                                # REMOVED_SYNTAX_ERROR: print("Check the error messages above for specific issues")

                                # REMOVED_SYNTAX_ERROR: return tests_passed >= 4


                                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                    # REMOVED_SYNTAX_ERROR: try:
                                        # REMOVED_SYNTAX_ERROR: success = asyncio.run(main())
                                        # REMOVED_SYNTAX_ERROR: sys.exit(0 if success else 1)
                                        # REMOVED_SYNTAX_ERROR: except KeyboardInterrupt:
                                            # REMOVED_SYNTAX_ERROR: print("\nTest interrupted by user")
                                            # REMOVED_SYNTAX_ERROR: sys.exit(1)
                                            # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                # REMOVED_SYNTAX_ERROR: sys.exit(1)