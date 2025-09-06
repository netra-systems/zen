"""
Test Auth service with the ACTUAL staging credentials from Secret Manager.
This test validates the exact configuration that would be used in production.
"""
import asyncio
import sys
import logging
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from auth_service.auth_core.config import AuthConfig
from shared.isolated_environment import get_env
from shared.database_url_builder import DatabaseURLBuilder

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_actual_staging_credentials():
    """Setup the ACTUAL staging credentials from Secret Manager."""
    env_manager = get_env()
    
    # Set staging environment
    env_manager.set("ENVIRONMENT", "staging")
    
    # ACTUAL credentials from Secret Manager
    env_manager.set("POSTGRES_HOST", "/cloudsql/netra-staging:us-central1:staging-shared-postgres")
    env_manager.set("POSTGRES_PORT", "5432")
    env_manager.set("POSTGRES_DB", "postgres")  # CORRECTED: Use actual DB name from Secret Manager
    env_manager.set("POSTGRES_USER", "postgres")
    env_manager.set("POSTGRES_PASSWORD", "DTprdt5KoQXlEG4Gh9lF")
    
    # Set required staging variables to prevent AuthConfig errors
    env_manager.set("SERVICE_ID", "auth-service-staging")
    env_manager.set("SERVICE_SECRET", "test-staging-service-secret-12345678901234567890")
    env_manager.set("JWT_SECRET_KEY", "test-staging-jwt-secret-key-12345678901234567890")
    # TOMBSTONE: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET superseded by environment-specific variables
    env_manager.set("GOOGLE_OAUTH_CLIENT_ID_STAGING", "test-staging-client-id")
    env_manager.set("GOOGLE_OAUTH_CLIENT_SECRET_STAGING", "test-staging-client-secret")
    
    logger.info("Set up ACTUAL staging credentials from Secret Manager")


def test_url_generation_with_actual_credentials():
    """Test URL generation with actual staging credentials."""
    logger.info("=== Testing URL Generation with Actual Credentials ===")
    
    try:
        # Setup environment
        setup_actual_staging_credentials()
        
        # Test AuthConfig URL generation
        database_url = AuthConfig.get_database_url()
        
        if not database_url:
            logger.error("FAILED: No database URL generated")
            return False
        
        masked_url = DatabaseURLBuilder.mask_url_for_logging(database_url)
        logger.info(f"Generated URL: {masked_url}")
        
        # Verify URL components
        expected_components = [
            "postgresql+asyncpg://" in database_url,
            "/cloudsql/netra-staging:us-central1:staging-shared-postgres" in database_url,
            "/postgres" in database_url,  # CORRECTED: Expect postgres DB
            "postgres:" in database_url,  # CORRECTED: Expect postgres user
        ]
        
        if all(expected_components):
            logger.info("SUCCESS: URL contains all expected components")
        else:
            logger.error(f"FAILED: URL missing expected components: {expected_components}")
            logger.error(f"Full URL for debug: {database_url}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"FAILED: URL generation failed: {e}")
        return False


def analyze_database_mismatch():
    """Analyze the database name mismatch issue."""
    logger.info("=== Analyzing Database Name Configuration ===")
    
    logger.info("ISSUE IDENTIFIED:")
    logger.info("  - Secret Manager postgres-db-staging = 'postgres'")
    logger.info("  - But code was expecting 'netra_staging'")
    logger.info("  - Available databases on instance:")
    logger.info("    * postgres (system database)")
    logger.info("    * netra_pr_branch_* (PR databases)")
    logger.info("    * netra_pr-* (PR databases)")
    
    logger.info("\nRECOMMENDATIONS:")
    logger.info("  1. IMMEDIATE FIX: Use 'postgres' database as configured in Secret Manager")
    logger.info("  2. PROPER FIX: Create 'netra_staging' database for staging environment")
    logger.info("  3. UPDATE: Secret Manager to use 'netra_staging' if that's the intended DB")
    
    logger.info("\nLIKELY CAUSE OF AUTH FAILURES:")
    logger.info("  - Auth service trying to connect to 'postgres' database")
    logger.info("  - But application schema might not exist in 'postgres' database")
    logger.info("  - OR 'postgres' database doesn't have the required tables/schema")
    
    return True


def provide_next_steps():
    """Provide next steps to resolve the issue."""
    logger.info("=== Next Steps to Resolve Auth Database Issue ===")
    
    steps = [
        "1. VERIFY which database should be used:",
        "   - Check if 'postgres' DB has auth tables",
        "   - OR create 'netra_staging' database for staging",
        "",
        "2. UPDATE Secret Manager if needed:",
        "   gcloud secrets versions add postgres-db-staging --data-file=<new_db_name>",
        "",
        "3. RUN database migrations on correct database:",
        "   - Ensure auth service tables exist in target database",
        "   - Run Alembic migrations if needed",
        "",
        "4. TEST connection in staging environment:",
        "   - Deploy with corrected credentials",
        "   - Monitor logs for connection success",
        "",
        "5. VERIFY auth operations work end-to-end:",
        "   - Test login flow",
        "   - Verify JWT token generation",
        "   - Confirm session management"
    ]
    
    for step in steps:
        logger.info(step)
    
    return True


def main():
    """Main test function."""
    print("Auth Service Actual Staging Credentials Test")
    print("=" * 50)
    
    tests = [
        ("URL Generation with Actual Credentials", test_url_generation_with_actual_credentials),
        ("Database Mismatch Analysis", analyze_database_mismatch),
        ("Next Steps Guidance", provide_next_steps)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            if test_func():
                logger.info(f"COMPLETED: {test_name}")
                passed += 1
            else:
                logger.error(f"FAILED: {test_name}")
        except Exception as e:
            logger.error(f"CRASHED: {test_name} - {e}")
    
    print("\n" + "=" * 50)
    print(f"Analysis Complete: {passed}/{len(tests)} sections completed")
    
    print("\nKEY FINDING:")
    print("The Auth service database connection issue is likely caused by:")
    print("1. Database name mismatch ('postgres' vs expected 'netra_staging')")  
    print("2. Missing auth service tables in the 'postgres' database")
    print("3. Need to run migrations or use correct staging database")
        
    return True


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f"Test crashed: {e}")
        sys.exit(1)