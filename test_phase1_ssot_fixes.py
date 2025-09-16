#!/usr/bin/env python3
"""
Test Phase 1 SSOT violation remediation fixes for central configuration validator.

This tests the critical configuration fixes identified in Phase 1:
1. Environment-specific configuration rules
2. SERVICE_SECRET implementation  
3. JWT configuration standardization
"""

import os
import sys
import pytest
from typing import Dict, Any
from unittest.mock import patch

def test_environment_specific_postgres_password_rules():
    """Test that POSTGRES_PASSWORD is handled correctly based on deployment pattern."""
    print("\n[TEST] Environment-specific POSTGRES_PASSWORD validation...")
    
    # Test 1: DATABASE_URL provided (GCP Cloud Run pattern) - should pass without POSTGRES_PASSWORD
    env_vars = {
        "ENVIRONMENT": "staging",
        "DATABASE_URL": "postgresql://user:pass@host:5432/db",
        "REDIS_HOST": "redis-host", 
        "REDIS_PASSWORD": "redis-pass-123456",
        "SERVICE_SECRET": "service-secret-" + "x" * 20,  # 32+ chars total
        "FERNET_KEY": "fernet-key-" + "x" * 22,  # 32+ chars total
        "GEMINI_API_KEY": "gemini-key-123456",
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": "oauth-id-staging",
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "oauth-secret-staging",
        "JWT_SECRET_STAGING": "jwt-secret-" + "x" * 21  # 32+ chars total
    }
    
    try:
        with patch.dict(os.environ, env_vars, clear=True):
            from shared.configuration.central_config_validator import CentralConfigurationValidator
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            print("  ✅ PASS: DATABASE_URL deployment pattern validated correctly")
    except Exception as e:
        print(f"  ❌ FAIL: DATABASE_URL pattern validation failed: {e}")
        return False
        
    # Test 2: Component-based configuration - should require POSTGRES_PASSWORD
    env_vars_component = env_vars.copy()
    del env_vars_component["DATABASE_URL"]
    env_vars_component.update({
        "POSTGRES_HOST": "postgres-host",
        "POSTGRES_PASSWORD": "postgres-pass-123456"
    })
    
    try:
        with patch.dict(os.environ, env_vars_component, clear=True):
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            print("  ✅ PASS: Component-based deployment pattern validated correctly")
    except Exception as e:
        print(f"  ❌ FAIL: Component-based pattern validation failed: {e}")
        return False
        
    # Test 3: Neither DATABASE_URL nor component config - should fail
    env_vars_missing = env_vars.copy()
    del env_vars_missing["DATABASE_URL"]
    # Don't add POSTGRES_HOST/POSTGRES_PASSWORD
    
    try:
        with patch.dict(os.environ, env_vars_missing, clear=True):
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            print("  ❌ FAIL: Missing database config should have failed validation")
            return False
    except ValueError as e:
        if "Database host required" in str(e):
            print("  ✅ PASS: Missing database configuration correctly rejected")
        else:
            print(f"  ❌ FAIL: Wrong error for missing database config: {e}")
            return False
    except Exception as e:
        print(f"  ❌ FAIL: Unexpected error for missing database config: {e}")
        return False
        
    return True


def test_service_secret_validation():
    """Test SERVICE_SECRET validation for staging/production environments."""
    print("\n[TEST] SERVICE_SECRET validation for staging/production...")
    
    # Base valid environment
    base_env = {
        "ENVIRONMENT": "staging",
        "DATABASE_URL": "postgresql://user:pass@host:5432/db",
        "REDIS_HOST": "redis-host",
        "REDIS_PASSWORD": "redis-pass-123456", 
        "FERNET_KEY": "fernet-key-" + "x" * 20,
        "GEMINI_API_KEY": "gemini-key-123456",
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": "oauth-id-staging",
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "oauth-secret-staging",
        "JWT_SECRET_STAGING": "jwt-secret-" + "x" * 21  # 32+ chars total
    }
    
    # Test 1: Valid SERVICE_SECRET
    env_with_service_secret = base_env.copy()
    env_with_service_secret["SERVICE_SECRET"] = "service-secret-" + "x" * 20
    
    try:
        with patch.dict(os.environ, env_with_service_secret, clear=True):
            from shared.configuration.central_config_validator import CentralConfigurationValidator
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            print("  ✅ PASS: Valid SERVICE_SECRET accepted")
    except Exception as e:
        print(f"  ❌ FAIL: Valid SERVICE_SECRET rejected: {e}")
        return False
        
    # Test 2: Missing SERVICE_SECRET in staging
    try:
        with patch.dict(os.environ, base_env, clear=True):
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            print("  ❌ FAIL: Missing SERVICE_SECRET should have failed validation")
            return False
    except ValueError as e:
        if "SERVICE_SECRET required" in str(e):
            print("  ✅ PASS: Missing SERVICE_SECRET correctly rejected")
        else:
            print(f"  ❌ FAIL: Wrong error for missing SERVICE_SECRET: {e}")
            return False
    except Exception as e:
        print(f"  ❌ FAIL: Unexpected error for missing SERVICE_SECRET: {e}")
        return False
        
    # Test 3: SERVICE_SECRET too short
    env_short_secret = base_env.copy()
    env_short_secret["SERVICE_SECRET"] = "short"
    
    try:
        with patch.dict(os.environ, env_short_secret, clear=True):
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            print("  ❌ FAIL: Short SERVICE_SECRET should have failed validation")
            return False
    except ValueError as e:
        if "must be at least 32 characters" in str(e):
            print("  ✅ PASS: Short SERVICE_SECRET correctly rejected")
        else:
            print(f"  ❌ FAIL: Wrong error for short SERVICE_SECRET: {e}")
            return False
    except Exception as e:
        print(f"  ❌ FAIL: Unexpected error for short SERVICE_SECRET: {e}")
        return False
        
    return True


def test_jwt_configuration_standardization():
    """Test JWT configuration standardization and deprecation."""
    print("\n[TEST] JWT configuration standardization...")
    
    # Test 1: JWT_SECRET_STAGING for staging environment
    staging_env = {
        "ENVIRONMENT": "staging",
        "DATABASE_URL": "postgresql://user:pass@host:5432/db",
        "REDIS_HOST": "redis-host",
        "REDIS_PASSWORD": "redis-pass-123456",
        "SERVICE_SECRET": "service-secret-" + "x" * 20,  # 32+ chars total
        "FERNET_KEY": "fernet-key-" + "x" * 22,  # 32+ chars total
        "GEMINI_API_KEY": "gemini-key-123456",
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": "oauth-id-staging",
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "oauth-secret-staging",
        "JWT_SECRET_STAGING": "jwt-secret-staging-" + "x" * 14  # 33 chars total
    }
    
    try:
        with patch.dict(os.environ, staging_env, clear=True):
            from shared.configuration.central_config_validator import CentralConfigurationValidator
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            jwt_secret = validator.get_jwt_secret()
            if jwt_secret == staging_env["JWT_SECRET_STAGING"]:
                print("  ✅ PASS: JWT_SECRET_STAGING correctly used for staging")
            else:
                print(f"  ❌ FAIL: Wrong JWT secret returned: {jwt_secret}")
                return False
    except Exception as e:
        print(f"  ❌ FAIL: JWT_SECRET_STAGING validation failed: {e}")
        return False
        
    # Test 2: JWT_SECRET_PRODUCTION for production environment
    prod_env = staging_env.copy()
    prod_env["ENVIRONMENT"] = "production"
    del prod_env["JWT_SECRET_STAGING"]
    prod_env["JWT_SECRET_PRODUCTION"] = "jwt-secret-production-" + "x" * 9  # 33 chars total
    prod_env["GOOGLE_OAUTH_CLIENT_ID_PRODUCTION"] = "oauth-id-prod"
    prod_env["GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION"] = "oauth-secret-prod"
    del prod_env["GOOGLE_OAUTH_CLIENT_ID_STAGING"]
    del prod_env["GOOGLE_OAUTH_CLIENT_SECRET_STAGING"]
    
    try:
        with patch.dict(os.environ, prod_env, clear=True):
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            jwt_secret = validator.get_jwt_secret()
            if jwt_secret == prod_env["JWT_SECRET_PRODUCTION"]:
                print("  ✅ PASS: JWT_SECRET_PRODUCTION correctly used for production")
            else:
                print(f"  ❌ FAIL: Wrong JWT secret returned for production: {jwt_secret}")
                return False
    except Exception as e:
        print(f"  ❌ FAIL: JWT_SECRET_PRODUCTION validation failed: {e}")
        return False
        
    # Test 3: JWT_SECRET_KEY for development environment
    dev_env = {
        "ENVIRONMENT": "development",
        "JWT_SECRET_KEY": "jwt-secret-dev-" + "x" * 17,  # 32+ chars total
        "GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT": "oauth-id-dev",
        "GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT": "oauth-secret-dev"
    }
    
    try:
        with patch.dict(os.environ, dev_env, clear=True):
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            jwt_secret = validator.get_jwt_secret()
            if jwt_secret == dev_env["JWT_SECRET_KEY"]:
                print("  ✅ PASS: JWT_SECRET_KEY correctly used for development")
            else:
                print(f"  ❌ FAIL: Wrong JWT secret returned for development: {jwt_secret}")
                return False
    except Exception as e:
        print(f"  ❌ FAIL: JWT_SECRET_KEY validation failed: {e}")
        return False
        
    return True


def test_legacy_configuration_detection():
    """Test legacy configuration detection and warnings."""
    print("\n[TEST] Legacy configuration detection...")
    
    # Test legacy JWT_SECRET usage (should be deprecated)
    legacy_env = {
        "ENVIRONMENT": "development",
        "JWT_SECRET": "legacy-jwt-secret-12345",  # This should trigger deprecation warning
        "GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT": "oauth-id-dev",
        "GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT": "oauth-secret-dev"
    }
    
    try:
        with patch.dict(os.environ, legacy_env, clear=True):
            from shared.configuration.central_config_validator import CentralConfigurationValidator
            validator = CentralConfigurationValidator()
            
            # Check if legacy variable is detected
            from shared.configuration.central_config_validator import LegacyConfigMarker
            if LegacyConfigMarker.is_legacy_variable("JWT_SECRET"):
                print("  ✅ PASS: JWT_SECRET correctly identified as legacy")
            else:
                print("  ❌ FAIL: JWT_SECRET not identified as legacy")
                return False
                
            # Check legacy info
            legacy_info = LegacyConfigMarker.get_legacy_info("JWT_SECRET")
            if legacy_info and not legacy_info["still_supported"]:
                print("  ✅ PASS: JWT_SECRET correctly marked as no longer supported")
            else:
                print("  ❌ FAIL: JWT_SECRET legacy status incorrect")
                return False
                
    except Exception as e:
        print(f"  ❌ FAIL: Legacy configuration detection failed: {e}")
        return False
        
    return True


def main():
    """Run all Phase 1 SSOT violation remediation tests."""
    print("=" * 60)
    print("Phase 1 SSOT Violation Remediation Validation")
    print("=" * 60)
    
    all_passed = True
    
    # Test environment-specific POSTGRES_PASSWORD rules
    if not test_environment_specific_postgres_password_rules():
        all_passed = False
        
    # Test SERVICE_SECRET implementation
    if not test_service_secret_validation():
        all_passed = False
        
    # Test JWT configuration standardization
    if not test_jwt_configuration_standardization():
        all_passed = False
        
    # Test legacy configuration detection
    if not test_legacy_configuration_detection():
        all_passed = False
        
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL PHASE 1 TESTS PASSED!")
        print("✅ Environment-specific configuration rules working")
        print("✅ SERVICE_SECRET validation implemented") 
        print("✅ JWT configuration standardization complete")
        print("✅ Legacy configuration detection working")
        print("\nPhase 1 SSOT violation remediation is COMPLETE.")
        return 0
    else:
        print("❌ SOME PHASE 1 TESTS FAILED!")
        print("Phase 1 SSOT violation remediation needs additional work.")
        return 1


if __name__ == "__main__":
    sys.exit(main())