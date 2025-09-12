"""
Simple test to validate Auth service database URL construction for staging.

This test focuses on URL construction logic rather than actual connections,
since Unix socket connections cannot be tested on Windows.
"""
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


def setup_minimal_staging_environment():
    """Setup minimal environment variables for URL construction test."""
    env_manager = get_env()
    
    # Set staging environment
    env_manager.set("ENVIRONMENT", "staging")
    
    # Set staging database credentials
    env_manager.set("POSTGRES_HOST", "/cloudsql/netra-staging:us-central1:staging-shared-postgres")
    env_manager.set("POSTGRES_PORT", "5432")
    env_manager.set("POSTGRES_DB", "netra_staging")
    env_manager.set("POSTGRES_USER", "postgres")
    env_manager.set("POSTGRES_PASSWORD", "DTprdt5KoQXlEG4Gh9lF")
    
    # Set required staging variables to prevent AuthConfig errors
    env_manager.set("SERVICE_ID", "auth-service-staging")
    env_manager.set("SERVICE_SECRET", "test-staging-service-secret-12345678901234567890")
    env_manager.set("JWT_SECRET_KEY", "test-staging-jwt-secret-key-12345678901234567890")
    # TOMBSTONE: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET superseded by environment-specific variables
    env_manager.set("GOOGLE_OAUTH_CLIENT_ID_STAGING", "test-staging-client-id")
    env_manager.set("GOOGLE_OAUTH_CLIENT_SECRET_STAGING", "test-staging-client-secret")
    
    logger.info("Set up minimal staging environment variables")


def test_url_construction():
    """Test URL construction logic for staging environment."""
    logger.info("=== Testing URL Construction ===")
    
    try:
        # Setup environment
        setup_minimal_staging_environment()
        
        # Test DatabaseURLBuilder directly
        env_manager = get_env()
        env_vars = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": env_manager.get("POSTGRES_HOST"),
            "POSTGRES_PORT": env_manager.get("POSTGRES_PORT"), 
            "POSTGRES_DB": env_manager.get("POSTGRES_DB"),
            "POSTGRES_USER": env_manager.get("POSTGRES_USER"),
            "POSTGRES_PASSWORD": env_manager.get("POSTGRES_PASSWORD")
        }
        
        builder = DatabaseURLBuilder(env_vars)
        
        # Validate configuration
        is_valid, error_msg = builder.validate()
        if not is_valid:
            logger.error(f"Configuration validation failed: {error_msg}")
            return False
        
        logger.info("SUCCESS: Configuration validation passed")
        
        # Check if Cloud SQL is detected
        logger.info(f"Cloud SQL detected: {builder.cloud_sql.is_cloud_sql}")
        logger.info(f"TCP config available: {builder.tcp.has_config}")
        
        # Get URLs
        async_url = builder.get_url_for_environment(sync=False)
        sync_url = builder.get_url_for_environment(sync=True)
        
        if async_url:
            masked_async = DatabaseURLBuilder.mask_url_for_logging(async_url)
            logger.info(f"Async URL: {masked_async}")
        else:
            logger.error("No async URL generated")
            return False
            
        if sync_url:
            masked_sync = DatabaseURLBuilder.mask_url_for_logging(sync_url)
            logger.info(f"Sync URL: {masked_sync}")
        else:
            logger.error("No sync URL generated")
            return False
        
        # Check URL format for Cloud SQL
        expected_patterns = [
            "postgresql+asyncpg://" in async_url,
            "postgresql://" in sync_url,
            "?host=/cloudsql/" in async_url,
            "?host=/cloudsql/" in sync_url,
            "/netra_staging" in async_url,
            "/netra_staging" in sync_url
        ]
        
        if all(expected_patterns):
            logger.info("SUCCESS: URLs have expected Cloud SQL format")
            return True
        else:
            logger.error("FAILED: URLs missing expected Cloud SQL patterns")
            logger.error(f"Pattern check results: {expected_patterns}")
            return False
            
    except Exception as e:
        logger.error(f"URL construction test failed: {e}")
        return False


def test_auth_config_integration():
    """Test AuthConfig URL generation."""
    logger.info("=== Testing AuthConfig Integration ===")
    
    try:
        # This should now work since we set all required variables
        database_url = AuthConfig.get_database_url()
        
        if not database_url:
            logger.error("FAILED: No database URL generated by AuthConfig")
            return False
        
        masked_url = DatabaseURLBuilder.mask_url_for_logging(database_url)
        logger.info(f"AuthConfig URL: {masked_url}")
        
        # Verify URL format
        if "postgresql+asyncpg://" in database_url and "/cloudsql/" in database_url:
            logger.info("SUCCESS: AuthConfig generated correct Cloud SQL URL")
            return True
        else:
            logger.error("FAILED: AuthConfig URL has incorrect format")
            return False
            
    except Exception as e:
        logger.error(f"AuthConfig integration test failed: {e}")
        return False


def analyze_connection_issue():
    """Analyze why the connection might be failing in staging."""
    logger.info("=== Analyzing Connection Issue ===")
    
    observations = []
    
    # 1. Check if we're using the right connection method
    try:
        database_url = AuthConfig.get_database_url()
        if "/cloudsql/" in database_url:
            observations.append("[U+2713] Using Cloud SQL Unix socket connection")
            observations.append("[U+2713] This is the correct method for GCP Cloud Run")
        else:
            observations.append("[U+2717] Not using Cloud SQL socket - this could be the issue")
    except Exception as e:
        observations.append(f"[U+2717] Error getting database URL: {e}")
    
    # 2. Check credentials format
    env_manager = get_env()
    postgres_user = env_manager.get("POSTGRES_USER")
    postgres_password = env_manager.get("POSTGRES_PASSWORD")
    
    if postgres_user == "postgres":
        observations.append("[U+2713] Using standard 'postgres' user")
    else:
        observations.append(f"? Using non-standard user: {postgres_user}")
    
    if postgres_password and len(postgres_password) >= 16:
        observations.append("[U+2713] Password has sufficient length")
    elif postgres_password:
        observations.append(f"? Password seems short ({len(postgres_password)} chars)")
    else:
        observations.append("[U+2717] No password configured")
    
    # 3. Environment analysis
    if env_manager.get("ENVIRONMENT") == "staging":
        observations.append("[U+2713] Environment set to 'staging'")
    else:
        observations.append("[U+2717] Environment not set to 'staging'")
    
    logger.info("Connection Analysis:")
    for obs in observations:
        logger.info(f"  {obs}")
    
    # 4. Most likely issues
    likely_issues = [
        "Unix socket path doesn't exist in Cloud Run environment",
        "Database user doesn't exist or password is incorrect", 
        "Cloud SQL instance is not running or accessible",
        "Network configuration issue in Cloud Run",
        "SSL/authentication method mismatch"
    ]
    
    logger.info("Most likely issues in staging environment:")
    for i, issue in enumerate(likely_issues, 1):
        logger.info(f"  {i}. {issue}")
    
    return True


def main():
    """Main test function."""
    print("Auth Service URL Construction Test")
    print("=" * 50)
    
    tests = [
        ("URL Construction", test_url_construction),
        ("AuthConfig Integration", test_auth_config_integration),
        ("Connection Issue Analysis", analyze_connection_issue)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            if test_func():
                logger.info(f"[U+2713] {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"[U+2717] {test_name} FAILED")
        except Exception as e:
            logger.error(f"[U+2717] {test_name} CRASHED: {e}")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("SUCCESS: URL construction is working correctly")
        print("The issue is likely with the actual database connection in Cloud Run")
    else:
        print("FAILURE: URL construction has issues")
        
    return passed == len(tests)


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test crashed: {e}")
        sys.exit(1)