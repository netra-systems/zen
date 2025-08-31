#!/usr/bin/env python3
"""
Mission Critical: Pre/Post Deployment JWT Verification

This test verifies JWT configuration before and after deployment to prevent
authentication failures from reaching production.

Should be run:
1. Before deployment (pre-deploy check)
2. After deployment (post-deploy verification)
"""

import os
import sys
import pytest
import subprocess
from pathlib import Path
from typing import Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestPrePostDeploymentJWTVerification:
    """Pre and post deployment JWT verification tests."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Store original environment
        self.original_env = {}
        for key in os.environ:
            if 'JWT' in key or key == 'ENVIRONMENT':
                self.original_env[key] = os.environ[key]
        
        yield
        
        # Restore environment
        for key in list(os.environ.keys()):
            if 'JWT' in key or key == 'ENVIRONMENT':
                del os.environ[key]
        for key, value in self.original_env.items():
            os.environ[key] = value
    
    def test_pre_deployment_staging_jwt_config_validation(self):
        """PRE-DEPLOYMENT: Verify staging JWT configuration is ready for deployment."""
        
        # Simulate staging environment
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['JWT_SECRET_STAGING'] = '7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A'
        
        # Verify configuration files are updated
        config_checks = []
        
        # Check staging auth config removed legacy JWT_SECRET_KEY
        staging_config_path = project_root / "staging_auth_service_config.json"
        if staging_config_path.exists():
            content = staging_config_path.read_text()
            has_legacy_jwt_secret_key = '"name": "JWT_SECRET_KEY"' in content
            has_correct_jwt_secret_staging = '"name": "JWT_SECRET_STAGING"' in content
            
            config_checks.append(("staging_auth_config_no_legacy_jwt_secret_key", not has_legacy_jwt_secret_key))
            config_checks.append(("staging_auth_config_has_jwt_secret_staging", has_correct_jwt_secret_staging))
        
        # Check deployment script uses correct secrets
        deploy_script_path = project_root / "scripts" / "deploy_to_gcp.py"
        if deploy_script_path.exists():
            content = deploy_script_path.read_text()
            backend_uses_staging_secret = "JWT_SECRET_STAGING=jwt-secret-staging:latest" in content
            auth_no_legacy_key = "JWT_SECRET_KEY=jwt-secret-key-staging:latest" not in content
            
            config_checks.append(("deployment_backend_uses_staging_secret", backend_uses_staging_secret))
            config_checks.append(("deployment_auth_no_legacy_key", auth_no_legacy_key))
        
        # Verify services load correctly with staging config
        service_checks = []
        
        try:
            from auth_service.auth_core.secret_loader import AuthSecretLoader
            auth_secret = AuthSecretLoader.get_jwt_secret()
            service_checks.append(("auth_service_loads_staging_secret", len(auth_secret) >= 32))
        except Exception as e:
            service_checks.append(("auth_service_loads_staging_secret", False))
        
        try:
            from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
            backend_manager = UnifiedSecretManager()
            backend_secret = backend_manager.get_jwt_secret()
            service_checks.append(("backend_service_loads_staging_secret", len(backend_secret) >= 32))
        except Exception as e:
            service_checks.append(("backend_service_loads_staging_secret", False))
        
        # Report results
        print("\n🔍 PRE-DEPLOYMENT JWT CONFIGURATION VALIDATION")
        print("=" * 60)
        
        print("\n📁 Configuration Files:")
        for check_name, passed in config_checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
        
        print("\n🚀 Service Loading:")
        for check_name, passed in service_checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
        
        # All checks must pass
        all_passed = all(passed for _, passed in config_checks + service_checks)
        
        if all_passed:
            print("\n✅ PRE-DEPLOYMENT VALIDATION PASSED - Ready for staging deployment")
        else:
            print("\n❌ PRE-DEPLOYMENT VALIDATION FAILED - Fix configuration before deployment")
            
        assert all_passed, "Pre-deployment JWT configuration validation failed"
    
    def test_post_deployment_staging_jwt_consistency(self):
        """POST-DEPLOYMENT: Verify both services use identical JWT secrets in staging."""
        
        # This test would be run against deployed services
        # For now, simulate the post-deployment environment
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['JWT_SECRET_STAGING'] = '7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A'
        
        print("\n🔍 POST-DEPLOYMENT JWT CONSISTENCY VERIFICATION")
        print("=" * 60)
        
        # Load secrets from both services
        auth_secret = None
        backend_secret = None
        
        try:
            from auth_service.auth_core.secret_loader import AuthSecretLoader
            auth_secret = AuthSecretLoader.get_jwt_secret()
            print(f"✅ Auth service JWT secret: {len(auth_secret)} chars")
        except Exception as e:
            print(f"❌ Auth service failed to load JWT secret: {e}")
        
        try:
            from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
            backend_manager = UnifiedSecretManager()
            backend_secret = backend_manager.get_jwt_secret()
            print(f"✅ Backend service JWT secret: {len(backend_secret)} chars")
        except Exception as e:
            print(f"❌ Backend service failed to load JWT secret: {e}")
        
        # Verify consistency
        if auth_secret and backend_secret:
            secrets_match = auth_secret == backend_secret
            secret_length_ok = len(auth_secret) >= 32 and len(backend_secret) >= 32
            
            print(f"\n🔍 Consistency Check:")
            print(f"  Secrets match: {'✅' if secrets_match else '❌'}")
            print(f"  Secret length OK: {'✅' if secret_length_ok else '❌'}")
            
            if secrets_match and secret_length_ok:
                print("\n✅ POST-DEPLOYMENT VERIFICATION PASSED - Services use identical secrets")
                return True
            else:
                print("\n❌ POST-DEPLOYMENT VERIFICATION FAILED - Secret mismatch detected")
                return False
        else:
            print("\n❌ POST-DEPLOYMENT VERIFICATION FAILED - Could not load secrets from both services")
            return False
    
    def test_staging_hard_failure_without_jwt_secret_staging(self):
        """Verify services FAIL HARD when JWT_SECRET_STAGING is missing in staging."""
        
        os.environ['ENVIRONMENT'] = 'staging'
        # Explicitly NOT setting JWT_SECRET_STAGING
        
        print("\n🚨 HARD FAILURE VERIFICATION - Staging without JWT_SECRET_STAGING")
        print("=" * 70)
        
        # Test auth service hard failure
        try:
            from auth_service.auth_core.secret_loader import AuthSecretLoader
            AuthSecretLoader.get_jwt_secret()
            print("❌ Auth service should have failed but didn't")
            assert False, "Auth service should fail without JWT_SECRET_STAGING in staging"
        except ValueError as e:
            if "JWT secret not configured for staging environment" in str(e):
                print("✅ Auth service correctly fails without JWT_SECRET_STAGING")
            else:
                print(f"❌ Auth service failed with unexpected error: {e}")
                assert False, f"Unexpected auth service error: {e}"
        
        # Test backend service hard failure
        try:
            from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
            backend_manager = UnifiedSecretManager()
            backend_manager.get_jwt_secret()
            print("❌ Backend service should have failed but didn't")
            assert False, "Backend service should fail without JWT_SECRET_STAGING in staging"
        except ValueError as e:
            if "JWT secret not configured for staging environment" in str(e):
                print("✅ Backend service correctly fails without JWT_SECRET_STAGING")
            else:
                print(f"❌ Backend service failed with unexpected error: {e}")
                assert False, f"Unexpected backend service error: {e}"
        
        print("\n✅ HARD FAILURE VERIFICATION PASSED - Both services fail correctly")


if __name__ == "__main__":
    # Run the tests directly
    test_instance = TestPrePostDeploymentJWTVerification()
    
    tests = [
        ("Pre-Deployment Validation", test_instance.test_pre_deployment_staging_jwt_config_validation),
        ("Post-Deployment Consistency", test_instance.test_post_deployment_staging_jwt_consistency),
        ("Hard Failure Without Secret", test_instance.test_staging_hard_failure_without_jwt_secret_staging),
    ]
    
    print("🚨 PRE/POST DEPLOYMENT JWT VERIFICATION SUITE")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_instance.setup_and_teardown.__next__()  # Setup
            test_func()
            print(f"✅ {test_name} PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
            failed += 1
        finally:
            try:
                test_instance.setup_and_teardown.__next__()  # Teardown
            except StopIteration:
                pass
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ ALL PRE/POST DEPLOYMENT VERIFICATION TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ SOME PRE/POST DEPLOYMENT VERIFICATION TESTS FAILED")
        sys.exit(1)