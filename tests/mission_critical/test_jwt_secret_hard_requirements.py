from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Mission Critical: JWT Secret Hard Requirements Test

Verifies that both auth and backend services FAIL HARD when environment-specific 
JWT secrets are not provided, with no fallbacks allowed.

This test prevents authentication failures by ensuring proper secret configuration
before deployment.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestJWTSecretHardRequirements:
    """Test JWT secret hard requirements with no fallbacks."""
    
    def setup_method(self):
        """Clear JWT environment variables before each test."""
        self.original_env = {}
        for key in list(os.environ.keys()):
            if 'JWT' in key or key == 'ENVIRONMENT':
                self.original_env[key] = os.environ[key]
                del os.environ[key]
    
    def teardown_method(self):
        """Restore original environment after each test."""
        # Clear all JWT vars
        for key in list(os.environ.keys()):
            if 'JWT' in key or key == 'ENVIRONMENT':
                del os.environ[key]
        
        # Restore original values
        for key, value in self.original_env.items():
            os.environ[key] = value
    
    def test_staging_auth_service_requires_jwt_secret_staging(self):
        """Test auth service FAILS HARD without JWT_SECRET_STAGING in staging."""
        os.environ['ENVIRONMENT'] = 'staging'
        # Explicitly NOT setting JWT_SECRET_STAGING
        
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        with pytest.raises(ValueError, match="JWT secret not configured for staging environment"):
            AuthSecretLoader.get_jwt_secret()
    
    def test_staging_backend_service_requires_jwt_secret_staging(self):
        """Test backend service FAILS HARD without JWT_SECRET_STAGING in staging."""
        os.environ['ENVIRONMENT'] = 'staging'
        # Explicitly NOT setting JWT_SECRET_STAGING
        
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        
        secret_manager = UnifiedSecretManager()
        with pytest.raises(ValueError, match="JWT secret not configured for staging environment"):
            secret_manager.get_jwt_secret()
    
    def test_production_auth_service_requires_jwt_secret_production(self):
        """Test auth service FAILS HARD without JWT_SECRET_PRODUCTION in production."""
        os.environ['ENVIRONMENT'] = 'production'
        # Explicitly NOT setting JWT_SECRET_PRODUCTION
        
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        with pytest.raises(ValueError, match="JWT secret not configured for production environment"):
            AuthSecretLoader.get_jwt_secret()
    
    def test_production_backend_service_requires_jwt_secret_production(self):
        """Test backend service FAILS HARD without JWT_SECRET_PRODUCTION in production."""
        os.environ['ENVIRONMENT'] = 'production'
        # Explicitly NOT setting JWT_SECRET_PRODUCTION
        
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        
        secret_manager = UnifiedSecretManager()
        with pytest.raises(ValueError, match="JWT secret not configured for production environment"):
            secret_manager.get_jwt_secret()
    
    def test_development_auth_service_requires_jwt_secret_key(self):
        """Test auth service FAILS HARD without JWT_SECRET_KEY in development."""
        os.environ['ENVIRONMENT'] = 'development'
        # Explicitly NOT setting JWT_SECRET_KEY
        
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        with pytest.raises(ValueError, match="JWT secret not configured for development environment"):
            AuthSecretLoader.get_jwt_secret()
    
    def test_development_backend_service_requires_jwt_secret_key(self):
        """Test backend service FAILS HARD without JWT_SECRET_KEY in development."""
        os.environ['ENVIRONMENT'] = 'development'
        # Explicitly NOT setting JWT_SECRET_KEY
        
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        
        secret_manager = UnifiedSecretManager()
        with pytest.raises(ValueError, match="JWT secret not configured for development environment"):
            secret_manager.get_jwt_secret()
    
    def test_staging_services_use_same_secret_when_properly_configured(self):
        """Test that both services use the same JWT secret when properly configured for staging."""
        staging_secret = "test-staging-jwt-secret-86-characters-long-for-proper-security-validation-testing"
        
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['JWT_SECRET_STAGING'] = staging_secret
        
        # Test auth service
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        auth_jwt_secret = AuthSecretLoader.get_jwt_secret()
        
        # Test backend service
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        backend_secret_manager = UnifiedSecretManager()
        backend_jwt_secret = backend_secret_manager.get_jwt_secret()
        
        # Verify both services use the same secret
        assert auth_jwt_secret == backend_jwt_secret == staging_secret
        assert len(auth_jwt_secret) >= 32  # Security requirement
    
    def test_development_services_use_same_secret_when_properly_configured(self):
        """Test that both services use the same JWT secret when properly configured for development."""
        dev_secret = "test-development-jwt-secret-key-64-characters-long-for-testing"
        
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['JWT_SECRET_KEY'] = dev_secret
        
        # Test auth service
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        auth_jwt_secret = AuthSecretLoader.get_jwt_secret()
        
        # Test backend service
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        backend_secret_manager = UnifiedSecretManager()
        backend_jwt_secret = backend_secret_manager.get_jwt_secret()
        
        # Verify both services use the same secret
        assert auth_jwt_secret == backend_jwt_secret == dev_secret
        assert len(auth_jwt_secret) >= 32  # Security requirement
    
    def test_no_fallback_to_jwt_secret_key_in_staging(self):
        """Test that staging environment does NOT fallback to JWT_SECRET_KEY."""
        os.environ['ENVIRONMENT'] = 'staging'
        os.environ['JWT_SECRET_KEY'] = 'should-not-be-used-in-staging-fallback'
        # Explicitly NOT setting JWT_SECRET_STAGING
        
        # Auth service should fail
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        with pytest.raises(ValueError, match="JWT secret not configured for staging environment"):
            AuthSecretLoader.get_jwt_secret()
        
        # Backend service should fail
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        backend_secret_manager = UnifiedSecretManager()
        with pytest.raises(ValueError, match="JWT secret not configured for staging environment"):
            backend_secret_manager.get_jwt_secret()
    
    def test_no_fallback_to_jwt_secret_key_in_production(self):
        """Test that production environment does NOT fallback to JWT_SECRET_KEY."""
        os.environ['ENVIRONMENT'] = 'production'
        os.environ['JWT_SECRET_KEY'] = 'should-not-be-used-in-production-fallback'
        # Explicitly NOT setting JWT_SECRET_PRODUCTION
        
        # Auth service should fail
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        with pytest.raises(ValueError, match="JWT secret not configured for production environment"):
            AuthSecretLoader.get_jwt_secret()
        
        # Backend service should fail  
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        backend_secret_manager = UnifiedSecretManager()
        with pytest.raises(ValueError, match="JWT secret not configured for production environment"):
            backend_secret_manager.get_jwt_secret()


if __name__ == "__main__":
    # Run the tests directly
    test_instance = TestJWTSecretHardRequirements()
    
    tests = [
        ("Staging Auth Hard Requirement", test_instance.test_staging_auth_service_requires_jwt_secret_staging),
        ("Staging Backend Hard Requirement", test_instance.test_staging_backend_service_requires_jwt_secret_staging),
        ("Production Auth Hard Requirement", test_instance.test_production_auth_service_requires_jwt_secret_production),
        ("Production Backend Hard Requirement", test_instance.test_production_backend_service_requires_jwt_secret_production),
        ("Development Auth Hard Requirement", test_instance.test_development_auth_service_requires_jwt_secret_key),
        ("Development Backend Hard Requirement", test_instance.test_development_backend_service_requires_jwt_secret_key),
        ("Staging Services Consistency", test_instance.test_staging_services_use_same_secret_when_properly_configured),
        ("Development Services Consistency", test_instance.test_development_services_use_same_secret_when_properly_configured),
        ("No Staging Fallback", test_instance.test_no_fallback_to_jwt_secret_key_in_staging),
        ("No Production Fallback", test_instance.test_no_fallback_to_jwt_secret_key_in_production),
    ]
    
    print("🚨 JWT Secret Hard Requirements Test Suite")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_instance.setup_method()
            test_func()
            test_instance.teardown_method()
            print(f"✅ {test_name}")
            passed += 1
        except Exception as e:
            test_instance.teardown_method()
            print(f"❌ {test_name}: {e}")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All JWT hard requirement tests PASSED")
        sys.exit(0)
    else:
        print("❌ Some JWT hard requirement tests FAILED")
        sys.exit(1)
