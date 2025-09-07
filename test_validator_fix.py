#!/usr/bin/env python3
"""
Test script to validate the database configuration validator fix.

This simulates the GCP Cloud Run environment to verify our fix works.
"""

import sys
import os
sys.path.insert(0, '.')

def test_gcp_staging_config():
    """Test the updated validator with GCP staging configuration."""
    print("Testing GCP Staging Configuration Validation Fix...")
    
    # Simulate GCP Cloud Run environment variables (DATABASE_URL pattern)
    gcp_env = {
        'ENVIRONMENT': 'staging',
        'DATABASE_URL': 'postgresql+asyncpg://user:password@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres',
        'JWT_SECRET_STAGING': 'test-jwt-secret-32-characters-long',
        'GEMINI_API_KEY': 'test-gemini-key-12345',
        'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'test-client-id',
        'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'test-client-secret-long-enough',
        'SERVICE_SECRET': 'test-service-secret-32-characters-long',
        'FERNET_KEY': 'test-fernet-key-32-characters-long-enough',
        'REDIS_PASSWORD': 'test-redis-password',
        'REDIS_HOST': 'redis.example.com'
    }

    def mock_env_getter(key, default=None):
        return gcp_env.get(key, default)

    try:
        from shared.configuration.central_config_validator import CentralConfigurationValidator, Environment
        
        print("SUCCESS: Imported central validator successfully")
        
        # Create validator with mock environment
        validator = CentralConfigurationValidator(mock_env_getter)
        validator._current_environment = Environment.STAGING  # Force staging environment
        
        # Test database configuration validation specifically
        print("Testing database configuration validation...")
        validator._validate_database_configuration(Environment.STAGING)
        print("SUCCESS: Database configuration validation PASSED")
        
        # Test database credentials function
        print("Testing database credentials function...")
        db_creds = validator.get_database_credentials()
        print(f"SUCCESS: Database credentials: {db_creds}")
        
        # Test the full validation (this will fail on other configs, but database should pass)
        print("Testing database validation within full validation...")
        try:
            validator.validate_all_requirements()
            print("SUCCESS: FULL VALIDATION PASSED - All systems go!")
        except ValueError as e:
            if "Database" not in str(e):
                print("SUCCESS: Database validation passed within full validation")
                print(f"INFO: Other validation failures (expected): {e}")
            else:
                print(f"FAILED: Database validation still failing: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"FAILED: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_component_based_config():
    """Test the validator with component-based configuration (POSTGRES_*)."""
    print("\nTesting Component-Based Configuration (POSTGRES_*)...")
    
    # Simulate component-based environment variables
    component_env = {
        'ENVIRONMENT': 'staging',
        'POSTGRES_HOST': '/cloudsql/netra-staging:us-central1:staging-shared-postgres',
        'POSTGRES_PASSWORD': 'secure-password-123',
        'POSTGRES_USER': 'postgres',
        'POSTGRES_DB': 'netra_staging',
        'POSTGRES_PORT': '5432',
        'JWT_SECRET_STAGING': 'test-jwt-secret-32-characters-long',
        'GEMINI_API_KEY': 'test-gemini-key-12345',
        'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'test-client-id',
        'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'test-client-secret-long-enough',
        'SERVICE_SECRET': 'test-service-secret-32-characters-long',
        'FERNET_KEY': 'test-fernet-key-32-characters-long-enough',
        'REDIS_PASSWORD': 'test-redis-password',
        'REDIS_HOST': 'redis.example.com'
    }

    def mock_env_getter(key, default=None):
        return component_env.get(key, default)

    try:
        from shared.configuration.central_config_validator import CentralConfigurationValidator, Environment
        
        validator = CentralConfigurationValidator(mock_env_getter)
        validator._current_environment = Environment.STAGING
        
        # Test database configuration validation
        print("Testing component-based database validation...")
        validator._validate_database_configuration(Environment.STAGING)
        print("SUCCESS: Component-based database validation PASSED")
        
        return True
        
    except Exception as e:
        print(f"FAILED: Component-based test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Database Configuration Validator Fix")
    print("=" * 60)
    
    success1 = test_gcp_staging_config()
    success2 = test_component_based_config()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("SUCCESS: Database configuration validator fix is working!")
        print("   DATABASE_URL pattern (GCP Cloud Run) - SUPPORTED")
        print("   Component-based pattern (POSTGRES_*) - SUPPORTED")
        print("   Cloud SQL socket paths - SUPPORTED")
        sys.exit(0)
    else:
        print("FAILURE: Database configuration validator needs more work")
        sys.exit(1)