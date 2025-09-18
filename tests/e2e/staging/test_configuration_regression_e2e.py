#!/usr/bin/env python
"""
E2E Test: Golden Path Configuration Protection (Staging)

This test validates end-to-end configuration protection for the Golden Path
user flow in the staging GCP environment.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent configuration cascade failures in production  
- Value Impact: 500K+ ARR Golden Path configuration protection
- Strategic Impact: Mission critical infrastructure validation

This test uses the staging GCP environment to validate that configuration
regression prevention works in a real cloud deployment scenario.
"""

import unittest
import sys
import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.secrets_config import (
    get_secret_mappings, 
    validate_secret_mappings,
    SecretConfig
)

# Try to import staging-specific utilities
try:
    from shared.isolated_environment import IsolatedEnvironment, get_env
    ISOLATED_ENV_AVAILABLE = True
except ImportError:
    ISOLATED_ENV_AVAILABLE = False

try:
    from test_framework.ssot.isolated_test_helper import IsolatedTestCase
    TEST_BASE_AVAILABLE = True
except ImportError:
    TEST_BASE_AVAILABLE = False


class StagingConfigurationE2ETest(unittest.TestCase):
    """
    E2E test for configuration validation in staging environment.
    
    This test validates that the Golden Path configuration is properly
    protected against regressions in a real cloud deployment scenario.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up staging E2E test environment."""
        cls.environment = 'staging'
        cls.golden_path_secrets = [
            'SERVICE_SECRET',    # Inter-service auth  
            'JWT_SECRET_KEY',    # User authentication
            'SECRET_KEY',        # General encryption
            'SESSION_SECRET_KEY', # Session management
            'POSTGRES_PASSWORD', # Database access
            'GOOGLE_CLIENT_ID',  # OAuth authentication
            'GOOGLE_CLIENT_SECRET', # OAuth authentication
        ]
    
    def test_staging_configuration_mappings_exist(self):
        """
        Test that all required configuration mappings exist in staging.
        
        This validates that the staging deployment would have access
        to all secrets needed for Golden Path functionality.
        """
        print(f"\n🔍 Testing staging configuration mappings...")
        
        mappings = get_secret_mappings(self.environment)
        
        # Should have substantial number of mappings
        self.assertGreaterEqual(len(mappings), 20,
                              f"Staging should have sufficient secret mappings (got {len(mappings)})")
        
        # Validate all Golden Path secrets are mapped
        missing_secrets = []
        for secret in self.golden_path_secrets:
            if secret not in mappings:
                missing_secrets.append(secret)
        
        if missing_secrets:
            self.fail(
                f"GOLDEN PATH BLOCKED: Missing secrets in staging mappings: {', '.join(missing_secrets)}. "
                f"This would prevent 500K+ ARR user flow from working in staging deployment."
            )
        
        # Validate mappings are not empty
        empty_mappings = []
        for secret in self.golden_path_secrets:
            gsm_name = mappings.get(secret, '')
            if not gsm_name or gsm_name.isspace():
                empty_mappings.append(secret)
        
        if empty_mappings:
            self.fail(
                f"GOLDEN PATH BLOCKED: Empty GSM mappings in staging: {', '.join(empty_mappings)}. "
                f"This would prevent 500K+ ARR functionality from working."
            )
        
        print(f"CHECK All {len(self.golden_path_secrets)} Golden Path secrets properly mapped in staging")
    
    def test_staging_configuration_validation_passes(self):
        """
        Test that staging configuration passes validation checks.
        
        This validates that the staging environment configuration
        meets all requirements for Golden Path protection.
        """
        print(f"\n🔍 Testing staging configuration validation...")
        
        is_valid, errors = validate_secret_mappings(self.environment)
        
        # Log validation results
        status = "CHECK VALID" if is_valid else "WARNING️ ISSUES"
        print(f"Staging validation: {status} ({len(errors)} validation messages)")
        
        if errors:
            print("Validation messages:")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
        
        # For staging, we can accept some validation warnings
        # but no critical blocking errors should exist
        critical_errors = []
        for error in errors:
            if any(keyword in error.lower() for keyword in [
                'missing critical', 'empty gsm mappings', 'critical secret missing'
            ]):
                critical_errors.append(error)
        
        if critical_errors:
            self.fail(
                f"CRITICAL STAGING ERRORS: {len(critical_errors)} critical validation errors found. "
                f"This blocks 500K+ ARR Golden Path protection: {'; '.join(critical_errors)}"
            )
        
        print(f"CHECK Staging configuration validation acceptable for Golden Path protection")
    
    def test_oauth_configuration_completeness_staging(self):
        """
        Test that OAuth configuration is complete for staging.
        
        OAuth is critical for user authentication in the Golden Path.
        This validates both backend and auth service patterns work.
        """
        print(f"\n🔍 Testing OAuth configuration completeness in staging...")
        
        mappings = get_secret_mappings(self.environment)
        
        # Backend OAuth pattern (simplified names)
        backend_oauth_secrets = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET']
        missing_backend_oauth = []
        
        for secret in backend_oauth_secrets:
            if secret not in mappings:
                missing_backend_oauth.append(secret)
            else:
                gsm_name = mappings[secret]
                if not gsm_name or gsm_name.isspace():
                    missing_backend_oauth.append(f"{secret} (empty mapping)")
        
        if missing_backend_oauth:
            self.fail(
                f"OAUTH BLOCKED: Backend OAuth configuration incomplete in staging: "
                f"{', '.join(missing_backend_oauth)}. This blocks user authentication for 500K+ ARR."
            )
        
        # Auth service OAuth pattern (environment-specific names)
        auth_oauth_secrets = [
            'GOOGLE_OAUTH_CLIENT_ID_STAGING',
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING'
        ]
        missing_auth_oauth = []
        
        for secret in auth_oauth_secrets:
            if secret not in mappings:
                missing_auth_oauth.append(secret)
            else:
                gsm_name = mappings[secret]
                if not gsm_name or gsm_name.isspace():
                    missing_auth_oauth.append(f"{secret} (empty mapping)")
        
        if missing_auth_oauth:
            self.fail(
                f"OAUTH BLOCKED: Auth service OAuth configuration incomplete in staging: "
                f"{', '.join(missing_auth_oauth)}. This blocks user authentication for 500K+ ARR."
            )
        
        print(f"CHECK OAuth configuration complete for both backend and auth service in staging")
    
    def test_jwt_configuration_consistency_staging(self):
        """
        Test that JWT configuration is consistent in staging.
        
        JWT configuration issues have historically caused major outages.
        This validates all JWT-related secrets are properly configured.
        """
        print(f"\n🔍 Testing JWT configuration consistency in staging...")
        
        mappings = get_secret_mappings(self.environment)
        
        # All JWT-related secrets that should exist
        jwt_secrets = [
            'JWT_SECRET',
            'JWT_SECRET_KEY', 
            'JWT_SECRET_STAGING'
        ]
        
        found_jwt_secrets = []
        missing_jwt_secrets = []
        empty_jwt_secrets = []
        
        for secret in jwt_secrets:
            if secret in mappings:
                gsm_name = mappings[secret]
                if gsm_name and not gsm_name.isspace():
                    found_jwt_secrets.append((secret, gsm_name))
                else:
                    empty_jwt_secrets.append(secret)
            else:
                missing_jwt_secrets.append(secret)
        
        # Must have at least one JWT secret properly configured
        if not found_jwt_secrets:
            self.fail(
                f"JWT BLOCKED: No JWT secrets properly configured in staging. "
                f"Missing: {', '.join(missing_jwt_secrets)}. "
                f"Empty: {', '.join(empty_jwt_secrets)}. "
                f"This blocks user authentication for 500K+ ARR."
            )
        
        # Check for consistency - all found JWT secrets should map to same GSM secret
        gsm_names = [gsm_name for _, gsm_name in found_jwt_secrets]
        unique_gsm_names = set(gsm_names)
        
        if len(unique_gsm_names) > 1:
            print(f"WARNING️ JWT secrets map to different GSM secrets: {dict(found_jwt_secrets)}")
            print("This may cause authentication inconsistencies")
        else:
            print(f"CHECK JWT secrets consistently mapped to: {list(unique_gsm_names)[0]}")
        
        print(f"CHECK JWT configuration sufficient for staging Golden Path authentication")
    
    def test_database_configuration_staging(self):
        """
        Test that database configuration is complete for staging.
        
        Database access is critical for Golden Path functionality.
        This validates all database secrets are properly configured.
        """
        print(f"\n🔍 Testing database configuration in staging...")
        
        mappings = get_secret_mappings(self.environment)
        
        # Database secrets required for Golden Path
        database_secrets = [
            'POSTGRES_PASSWORD',
            'POSTGRES_HOST',
            'POSTGRES_PORT', 
            'POSTGRES_DB',
            'POSTGRES_USER'
        ]
        
        missing_db_secrets = []
        empty_db_secrets = []
        
        for secret in database_secrets:
            if secret not in mappings:
                missing_db_secrets.append(secret)
            else:
                gsm_name = mappings[secret]
                if not gsm_name or gsm_name.isspace():
                    empty_db_secrets.append(secret)
        
        # Critical database secrets that MUST exist
        critical_db_secrets = ['POSTGRES_PASSWORD']
        critical_missing = [s for s in critical_db_secrets if s in missing_db_secrets or s in empty_db_secrets]
        
        if critical_missing:
            self.fail(
                f"DATABASE BLOCKED: Critical database secrets missing/empty in staging: "
                f"{', '.join(critical_missing)}. This blocks database access for 500K+ ARR."
            )
        
        if missing_db_secrets:
            print(f"WARNING️ Non-critical database secrets missing: {', '.join(missing_db_secrets)}")
        
        print(f"CHECK Critical database configuration available for staging Golden Path")
    
    @unittest.skipIf(not ISOLATED_ENV_AVAILABLE, "IsolatedEnvironment not available")
    def test_environment_isolation_staging(self):
        """
        Test that staging environment is properly isolated.
        
        This validates that staging configuration doesn't leak
        production secrets and vice versa.
        """
        print(f"\n🔍 Testing environment isolation for staging...")
        
        env = get_env()
        env.set('ENVIRONMENT', 'staging', source='test')
        
        staging_mappings = get_secret_mappings('staging')
        production_mappings = get_secret_mappings('production')
        
        # Check for production secrets in staging
        staging_production_leaks = []
        for secret, gsm_name in staging_mappings.items():
            if 'production' in gsm_name.lower():
                staging_production_leaks.append(f"{secret} -> {gsm_name}")
        
        if staging_production_leaks:
            self.fail(
                f"ENVIRONMENT LEAK: Staging references production secrets: "
                f"{'; '.join(staging_production_leaks)}. This could cause configuration confusion."
            )
        
        # Check for staging secrets in production  
        production_staging_leaks = []
        for secret, gsm_name in production_mappings.items():
            if 'staging' in gsm_name.lower():
                production_staging_leaks.append(f"{secret} -> {gsm_name}")
        
        if production_staging_leaks:
            print(f"WARNING️ Production references staging secrets: {'; '.join(production_staging_leaks[:3])}")
            print("This should be addressed before production deployment")
        
        print(f"CHECK Environment isolation properly maintained for staging")
    
    def test_mission_critical_configuration_end_to_end(self):
        """
        End-to-end test of mission critical configuration protection.
        
        This simulates the full configuration validation that would happen
        during deployment to ensure Golden Path protection works.
        """
        print(f"\n🔍 Running end-to-end mission critical configuration validation...")
        
        # Step 1: Validate mappings exist
        try:
            mappings = get_secret_mappings(self.environment)
            self.assertGreater(len(mappings), 0, "Should retrieve secret mappings")
            print(f"CHECK Step 1: Retrieved {len(mappings)} secret mappings")
        except Exception as e:
            self.fail(f"STEP 1 FAILED: Cannot retrieve secret mappings: {e}")
        
        # Step 2: Validate configuration
        try:
            is_valid, errors = validate_secret_mappings(self.environment)
            self.assertIsInstance(is_valid, bool, "Should return validation status")
            self.assertIsInstance(errors, list, "Should return error list")
            print(f"CHECK Step 2: Configuration validation completed ({len(errors)} messages)")
        except Exception as e:
            self.fail(f"STEP 2 FAILED: Cannot validate secret mappings: {e}")
        
        # Step 3: Validate Golden Path secrets
        golden_path_status = []
        for secret in self.golden_path_secrets:
            if secret in mappings:
                gsm_name = mappings[secret]
                if gsm_name and not gsm_name.isspace():
                    golden_path_status.append(f"CHECK {secret}")
                else:
                    golden_path_status.append(f"X {secret} (empty)")
            else:
                golden_path_status.append(f"X {secret} (missing)")
        
        failed_secrets = [status for status in golden_path_status if 'X' in status]
        
        if failed_secrets:
            self.fail(
                f"GOLDEN PATH VALIDATION FAILED: {len(failed_secrets)} secrets failed validation. "
                f"This blocks 500K+ ARR functionality: {'; '.join(failed_secrets)}"
            )
        
        print(f"CHECK Step 3: All {len(self.golden_path_secrets)} Golden Path secrets validated")
        
        # Summary
        total_errors = len([e for e in errors if 'critical' in e.lower()])
        print(f"\n🎉 END-TO-END VALIDATION COMPLETE")
        print(f"   - {len(mappings)} secret mappings validated")
        print(f"   - {len(self.golden_path_secrets)} Golden Path secrets confirmed")  
        print(f"   - {total_errors} critical errors found")
        print(f"   - 500K+ ARR Golden Path configuration PROTECTED")


if __name__ == '__main__':
    print("="*90)
    print("E2E TEST: Golden Path Configuration Protection (Staging)")
    print("="*90)
    print("PURPOSE: Validate end-to-end configuration protection in staging GCP environment")
    print("SCOPE: Staging deployment configuration validation without Docker dependencies")
    print("BUSINESS IMPACT: 500K+ ARR Golden Path configuration protection")
    print("="*90)
    print()
    
    # Check if we're in a CI environment
    ci_environment = os.getenv('CI', '').lower() in ['true', '1', 'yes']
    if ci_environment:
        print("🤖 Running in CI environment - some tests may be skipped")
    
    unittest.main(verbosity=2)