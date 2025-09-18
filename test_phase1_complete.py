#!/usr/bin/env python3
"""
Complete Phase 1 SSOT Violation Remediation Test Suite

Tests all Phase 1 critical fixes:
1. Environment-specific configuration rules (POSTGRES_PASSWORD based on deployment pattern)
2. SERVICE_SECRET implementation for staging/production
3. JWT configuration standardization (environment-specific secrets)
4. Automatic deployment pattern detection
"""

import os
import sys
from typing import Dict, Any
from unittest.mock import patch

def test_deployment_pattern_detection():
    """Test automatic deployment pattern detection."""
    print("\n[TEST] Automatic deployment pattern detection...")
    
    # Test DATABASE_URL pattern detection
    env_database_url = {
        "ENVIRONMENT": "staging",
        "DATABASE_URL": "postgresql://user:pass@host:5432/db"
    }
    
    try:
        with patch.dict(os.environ, env_database_url, clear=True):
            from shared.configuration.central_config_validator import CentralConfigurationValidator
            validator = CentralConfigurationValidator()
            pattern = validator.detect_deployment_pattern(validator.get_environment())
            if pattern == "database_url":
                print("  ✅ PASS: DATABASE_URL pattern correctly detected")
            else:
                print(f"  ❌ FAIL: Wrong pattern detected: {pattern}")
                return False
    except Exception as e:
        print(f"  ❌ FAIL: DATABASE_URL pattern detection failed: {e}")
        return False
    
    # Test component-based pattern detection
    env_component = {
        "ENVIRONMENT": "staging",
        "POSTGRES_HOST": "postgres-host",
        "POSTGRES_PASSWORD": "postgres-pass-123456"
    }
    
    try:
        with patch.dict(os.environ, env_component, clear=True):
            validator = CentralConfigurationValidator()
            pattern = validator.detect_deployment_pattern(validator.get_environment())
            if pattern == "component_based":
                print("  ✅ PASS: Component-based pattern correctly detected")
            else:
                print(f"  ❌ FAIL: Wrong pattern detected: {pattern}")
                return False
    except Exception as e:
        print(f"  ❌ FAIL: Component-based pattern detection failed: {e}")
        return False
    
    return True


def test_environment_specific_postgres_password():
    """Test POSTGRES_PASSWORD requirements based on deployment pattern."""
    print("\n[TEST] Environment-specific POSTGRES_PASSWORD validation...")
    
    # Test 1: DATABASE_URL deployment - POSTGRES_PASSWORD not required
    env_database_url = {
        "ENVIRONMENT": "staging",
        "DATABASE_URL": "postgresql://user:pass@host:5432/db",
        "REDIS_HOST": "redis-host",
        "REDIS_PASSWORD": "redis-pass-123456",
        "SERVICE_SECRET": "service-secret-" + "x" * 20,
        "FERNET_KEY": "fernet-key-" + "x" * 22,
        "GEMINI_API_KEY": "gemini-key-123456",
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": "oauth-id-staging",
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "oauth-secret-staging-123456789",  # 10+ chars
        "JWT_SECRET_STAGING": "jwt-secret-staging-" + "x" * 14
        # Note: No POSTGRES_PASSWORD provided - should still pass
    }
    
    try:
        with patch.dict(os.environ, env_database_url, clear=True):
            from shared.configuration.central_config_validator import CentralConfigurationValidator
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            print("  ✅ PASS: DATABASE_URL deployment works without POSTGRES_PASSWORD")
    except Exception as e:
        print(f"  ❌ FAIL: DATABASE_URL deployment failed: {e}")
        return False
    
    # Test 2: Component-based deployment - POSTGRES_PASSWORD required
    env_component = {
        "ENVIRONMENT": "staging",
        "POSTGRES_HOST": "postgres-host",
        "POSTGRES_PASSWORD": "postgres-pass-123456",
        "REDIS_HOST": "redis-host", 
        "REDIS_PASSWORD": "redis-pass-123456",
        "SERVICE_SECRET": "service-secret-" + "x" * 20,
        "FERNET_KEY": "fernet-key-" + "x" * 22,
        "GEMINI_API_KEY": "gemini-key-123456",
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": "oauth-id-staging",
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "oauth-secret-staging-123456789",  # 10+ chars
        "JWT_SECRET_STAGING": "jwt-secret-staging-" + "x" * 14
    }
    
    try:
        with patch.dict(os.environ, env_component, clear=True):
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            print("  ✅ PASS: Component-based deployment works with POSTGRES_PASSWORD")
    except Exception as e:
        print(f"  ❌ FAIL: Component-based deployment failed: {e}")
        return False
        
    # Test 3: Component-based deployment without password - should fail
    env_component_no_password = env_component.copy()
    del env_component_no_password["POSTGRES_PASSWORD"]
    
    try:
        with patch.dict(os.environ, env_component_no_password, clear=True):
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            print("  ❌ FAIL: Component-based deployment without password should have failed")
            return False
    except ValueError as e:
        if "Database password required" in str(e):
            print("  ✅ PASS: Component-based deployment correctly requires POSTGRES_PASSWORD")
        else:
            print(f"  ❌ FAIL: Wrong error for missing password: {e}")
            return False
    except Exception as e:
        print(f"  ❌ FAIL: Unexpected error: {e}")
        return False
        
    return True


def test_service_secret_implementation():
    """Test SERVICE_SECRET validation for staging/production."""
    print("\n[TEST] SERVICE_SECRET implementation...")
    
    # Valid environment with SERVICE_SECRET
    valid_env = {
        "ENVIRONMENT": "staging",
        "DATABASE_URL": "postgresql://user:pass@host:5432/db",
        "REDIS_HOST": "redis-host",
        "REDIS_PASSWORD": "redis-pass-123456",
        "SERVICE_SECRET": "service-secret-" + "x" * 20,  # 32+ chars
        "FERNET_KEY": "fernet-key-" + "x" * 22,
        "GEMINI_API_KEY": "gemini-key-123456",
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": "oauth-id-staging",
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "oauth-secret-staging-123456789",  # 10+ chars
        "JWT_SECRET_STAGING": "jwt-secret-staging-" + "x" * 14
    }
    
    try:
        with patch.dict(os.environ, valid_env, clear=True):
            from shared.configuration.central_config_validator import CentralConfigurationValidator
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            print("  ✅ PASS: Valid SERVICE_SECRET accepted")
    except Exception as e:
        print(f"  ❌ FAIL: Valid SERVICE_SECRET rejected: {e}")
        return False
    
    # Missing SERVICE_SECRET - should fail
    env_no_service_secret = valid_env.copy()
    del env_no_service_secret["SERVICE_SECRET"]
    
    try:
        with patch.dict(os.environ, env_no_service_secret, clear=True):
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            print("  ❌ FAIL: Missing SERVICE_SECRET should have failed")
            return False
    except ValueError as e:
        if "SERVICE_SECRET required" in str(e):
            print("  ✅ PASS: Missing SERVICE_SECRET correctly rejected")
        else:
            print(f"  ❌ FAIL: Wrong error for missing SERVICE_SECRET: {e}")
            return False
    except Exception as e:
        print(f"  ❌ FAIL: Unexpected error: {e}")
        return False
        
    return True


def test_jwt_configuration_standardization():
    """Test JWT configuration standardization."""
    print("\n[TEST] JWT configuration standardization...")
    
    # Test staging environment with JWT_SECRET_STAGING
    staging_env = {
        "ENVIRONMENT": "staging",
        "DATABASE_URL": "postgresql://user:pass@host:5432/db",
        "REDIS_HOST": "redis-host",
        "REDIS_PASSWORD": "redis-pass-123456",
        "SERVICE_SECRET": "service-secret-" + "x" * 20,
        "FERNET_KEY": "fernet-key-" + "x" * 22,
        "GEMINI_API_KEY": "gemini-key-123456",
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": "oauth-id-staging",
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "oauth-secret-staging-123456789",  # 10+ chars
        "JWT_SECRET_STAGING": "jwt-secret-staging-" + "x" * 14
    }
    
    try:
        with patch.dict(os.environ, staging_env, clear=True):
            from shared.configuration.central_config_validator import CentralConfigurationValidator
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            jwt_secret = validator.get_jwt_secret()
            expected = staging_env["JWT_SECRET_STAGING"]
            if jwt_secret == expected:
                print("  ✅ PASS: JWT_SECRET_STAGING correctly used for staging")
            else:
                print(f"  ❌ FAIL: Expected {expected}, got {jwt_secret}")
                return False
    except Exception as e:
        print(f"  ❌ FAIL: JWT_SECRET_STAGING validation failed: {e}")
        return False
    
    # Test production environment with JWT_SECRET_PRODUCTION
    production_env = {
        "ENVIRONMENT": "production",
        "DATABASE_URL": "postgresql://user:pass@host:5432/db",
        "REDIS_HOST": "redis-host",
        "REDIS_PASSWORD": "redis-pass-123456",
        "SERVICE_SECRET": "service-secret-" + "x" * 20,
        "FERNET_KEY": "fernet-key-" + "x" * 22,
        "GEMINI_API_KEY": "gemini-key-123456",
        "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION": "oauth-id-production",
        "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION": "oauth-secret-production-123456789",  # 10+ chars
        "JWT_SECRET_PRODUCTION": "jwt-secret-production-" + "x" * 8
    }
    
    try:
        with patch.dict(os.environ, production_env, clear=True):
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            jwt_secret = validator.get_jwt_secret()
            expected = production_env["JWT_SECRET_PRODUCTION"]
            if jwt_secret == expected:
                print("  ✅ PASS: JWT_SECRET_PRODUCTION correctly used for production")
            else:
                print(f"  ❌ FAIL: Expected {expected}, got {jwt_secret}")
                return False
    except Exception as e:
        print(f"  ❌ FAIL: JWT_SECRET_PRODUCTION validation failed: {e}")
        return False
        
    # Test development environment with JWT_SECRET_KEY  
    development_env = {
        "ENVIRONMENT": "development",
        "JWT_SECRET_KEY": "jwt-secret-dev-" + "x" * 17,
        "GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT": "oauth-id-dev",
        "GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT": "oauth-secret-dev-123456789"  # 10+ chars
    }
    
    try:
        with patch.dict(os.environ, development_env, clear=True):
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            jwt_secret = validator.get_jwt_secret()
            expected = development_env["JWT_SECRET_KEY"]
            if jwt_secret == expected:
                print("  ✅ PASS: JWT_SECRET_KEY correctly used for development")
            else:
                print(f"  ❌ FAIL: Expected {expected}, got {jwt_secret}")
                return False
    except Exception as e:
        print(f"  ❌ FAIL: JWT_SECRET_KEY validation failed: {e}")
        return False
        
    return True


def test_legacy_configuration_handling():
    """Test legacy configuration detection and warnings."""
    print("\n[TEST] Legacy configuration handling...")
    
    try:
        from shared.configuration.central_config_validator import LegacyConfigMarker
        
        # Test JWT_SECRET is marked as legacy
        if LegacyConfigMarker.is_legacy_variable("JWT_SECRET"):
            print("  ✅ PASS: JWT_SECRET correctly identified as legacy")
        else:
            print("  ❌ FAIL: JWT_SECRET not identified as legacy")
            return False
            
        # Test JWT_SECRET is not supported
        legacy_info = LegacyConfigMarker.get_legacy_info("JWT_SECRET")
        if legacy_info and not legacy_info["still_supported"]:
            print("  ✅ PASS: JWT_SECRET correctly marked as no longer supported")
        else:
            print("  ❌ FAIL: JWT_SECRET legacy status incorrect")
            return False
            
        # Test replacement variables
        replacements = LegacyConfigMarker.get_replacement_variables("JWT_SECRET")
        if "JWT_SECRET_KEY" in replacements:
            print("  ✅ PASS: JWT_SECRET replacement correctly identified")
        else:
            print(f"  ❌ FAIL: Wrong replacement variables: {replacements}")
            return False
            
    except Exception as e:
        print(f"  ❌ FAIL: Legacy configuration handling failed: {e}")
        return False
        
    return True


def main():
    """Run complete Phase 1 SSOT violation remediation test suite."""
    print("=" * 80)
    print("Phase 1 SSOT Violation Remediation - COMPLETE TEST SUITE")
    print("=" * 80)
    print("Testing critical configuration fixes for $500K+ ARR cascade failure prevention")
    
    all_passed = True
    
    # Test automatic deployment pattern detection
    if not test_deployment_pattern_detection():
        all_passed = False
        
    # Test environment-specific POSTGRES_PASSWORD rules
    if not test_environment_specific_postgres_password():
        all_passed = False
        
    # Test SERVICE_SECRET implementation
    if not test_service_secret_implementation():
        all_passed = False
        
    # Test JWT configuration standardization
    if not test_jwt_configuration_standardization():
        all_passed = False
        
    # Test legacy configuration handling
    if not test_legacy_configuration_handling():
        all_passed = False
        
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 PHASE 1 SSOT VIOLATION REMEDIATION COMPLETE!")
        print("")
        print("✅ Environment-specific configuration rules implemented")
        print("✅ Automatic deployment pattern detection working")
        print("✅ SERVICE_SECRET validation implemented for staging/production")
        print("✅ JWT configuration standardization complete")
        print("✅ Legacy configuration detection and warnings working")
        print("")
        print("CRITICAL FIXES COMPLETE:")
        print("• POSTGRES_PASSWORD rules based on deployment pattern")
        print("• SERVICE_SECRET validation for inter-service auth")
        print("• JWT_SECRET standardization with environment-specific secrets")
        print("• Automatic DATABASE_URL vs component-based detection")
        print("")
        print("Phase 1 remediation prevents $500K+ ARR cascade failures.")
        return 0
    else:
        print("❌ PHASE 1 REMEDIATION INCOMPLETE!")
        print("Some critical configuration fixes failed validation.")
        print("Phase 1 must be completed before Phase 2 can begin.")
        return 1


if __name__ == "__main__":
    sys.exit(main())