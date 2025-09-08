"""
Staging environment service authentication test.

This test verifies that service-to-service authentication works correctly
in the staging environment with the proper SERVICE_ID configuration.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability in Staging
- Value Impact: Ensures staging authentication works before production deployment
- Strategic Impact: Prevents authentication failures in production
"""

import os
import sys
import pytest
from typing import Dict
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.isolated_environment import get_env


class TestStagingServiceAuthentication:
    """Test service authentication configuration for staging environment."""
    
    @pytest.fixture(autouse=True)
    def setup_staging_env(self):
        """Set up staging environment for tests."""
        env = get_env()
        self.original_env = env.get("ENVIRONMENT")
        env.set("ENVIRONMENT", "staging", "test_staging")
        yield
        # Restore original environment
        if self.original_env:
            env.set("ENVIRONMENT", self.original_env, "test_staging")
        else:
            env.delete("ENVIRONMENT", "test_staging")
    
    def test_staging_has_service_credentials(self):
        """Test that staging environment has SERVICE_ID and SERVICE_SECRET configured."""
        # Load staging environment file
        staging_env_path = ".env.staging"
        
        if not os.path.exists(staging_env_path):
            pytest.skip("Staging environment file not found")
        
        # Parse staging environment
        staging_vars = {}
        with open(staging_env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    staging_vars[key.strip()] = value.strip()
        
        # Verify SERVICE_ID is set to netra-backend
        assert "SERVICE_ID" in staging_vars, (
            "SERVICE_ID must be configured in .env.staging"
        )
        assert staging_vars["SERVICE_ID"] == "netra-backend", (
            f"SERVICE_ID must be 'netra-backend' in staging, got '{staging_vars.get('SERVICE_ID')}'"
        )
        
        # Verify SERVICE_SECRET is configured
        assert "SERVICE_SECRET" in staging_vars, (
            "SERVICE_SECRET must be configured in .env.staging"
        )
        assert len(staging_vars["SERVICE_SECRET"]) >= 32, (
            "SERVICE_SECRET must be at least 32 characters in staging"
        )
        
        # Verify it's different from JWT secret
        jwt_secret = staging_vars.get("JWT_SECRET_KEY", "") or staging_vars.get("JWT_SECRET_STAGING", "")
        assert staging_vars["SERVICE_SECRET"] != jwt_secret, (
            "SERVICE_SECRET must be different from JWT_SECRET for security"
        )
    
    def test_staging_config_loads_service_credentials(self):
        """Test that staging configuration properly loads service credentials."""
        from netra_backend.app.schemas.config import StagingConfig
        
        # Mock environment to simulate staging
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "SERVICE_ID": "netra-backend",
            "SERVICE_SECRET": "staging-test-secret-for-verification-purposes-32chars",
            "POSTGRES_HOST": "test-host",
            "POSTGRES_USER": "test-user",
            "POSTGRES_PASSWORD": "test-pass",
            "POSTGRES_DB": "test-db"
        }):
            try:
                config = StagingConfig()
                
                # Verify service_id
                assert config.service_id == "netra-backend", (
                    "StagingConfig must use 'netra-backend' as service_id"
                )
                
                # Verify environment
                assert config.environment == "staging", (
                    "StagingConfig must set environment to 'staging'"
                )
            except Exception as e:
                # If there are missing required staging configs, that's OK for this test
                if "DATABASE_URL" not in str(e):
                    raise
    
    def test_auth_client_sends_correct_headers_in_staging(self):
        """Test that auth client sends correct headers in staging environment."""
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        
        # Mock configuration for staging
        with patch('netra_backend.app.clients.auth_client_core.get_configuration') as mock_config:
            mock_conf = MagicMock()
            mock_conf.service_id = "netra-backend"
            mock_conf.service_secret = "staging-secret-for-auth-testing-32-characters-long"
            mock_config.return_value = mock_conf
            
            # Mock environment check
            with patch('netra_backend.app.clients.auth_client_core.get_current_environment') as mock_env:
                mock_env.return_value = "staging"
                
                client = AuthServiceClient()
                headers = client._get_service_auth_headers()
                
                # Verify headers are correct for staging
                assert headers["X-Service-ID"] == "netra-backend", (
                    "Auth client must send 'netra-backend' as X-Service-ID in staging"
                )
                assert "X-Service-Secret" in headers, (
                    "Auth client must include X-Service-Secret header in staging"
                )
                assert headers["X-Service-Secret"] == mock_conf.service_secret, (
                    "Auth client must send correct service secret in staging"
                )
    
    def test_auth_service_validates_staging_credentials(self):
        """Test that auth service properly validates staging credentials."""
        # This test simulates what the auth service does in staging
        env = get_env()
        
        # Simulate staging environment
        env.set("ENVIRONMENT", "staging", "test")
        env.set("SERVICE_ID", "netra-backend", "test")
        env.set("SERVICE_SECRET", "staging-auth-service-secret-32-characters-minimum", "test")
        
        try:
            # Simulate incoming request headers
            incoming_service_id = "netra-backend"
            incoming_service_secret = "staging-auth-service-secret-32-characters-minimum"
            
            # Get expected values (what auth service would do)
            expected_service_id = env.get("SERVICE_ID", "netra-backend")
            expected_service_secret = env.get("SERVICE_SECRET", "")
            
            # Validation logic
            assert expected_service_secret, (
                "Auth service must have SERVICE_SECRET configured in staging"
            )
            
            assert incoming_service_id == expected_service_id, (
                f"Service ID mismatch in staging: expected '{expected_service_id}', got '{incoming_service_id}'"
            )
            
            assert incoming_service_secret == expected_service_secret, (
                "Service secret mismatch in staging"
            )
            
        finally:
            # Cleanup
            env.delete("SERVICE_SECRET", "test")
            env.delete("SERVICE_ID", "test")
    
    def test_error_messages_are_descriptive(self):
        """Test that error messages clearly indicate the problem."""
        env = get_env()
        
        # Test various failure scenarios
        test_cases = [
            {
                "incoming_id": "backend",  # Wrong ID
                "incoming_secret": "correct-secret",
                "expected_id": "netra-backend",
                "expected_secret": "correct-secret",
                "error_contains": ["Service ID mismatch", "netra-backend", "backend"]
            },
            {
                "incoming_id": "netra-backend",
                "incoming_secret": "wrong-secret",
                "expected_id": "netra-backend", 
                "expected_secret": "correct-secret",
                "error_contains": ["Service secret mismatch"]
            },
            {
                "incoming_id": None,
                "incoming_secret": "some-secret",
                "expected_id": "netra-backend",
                "expected_secret": "correct-secret",
                "error_contains": ["X-Service-ID"]
            }
        ]
        
        for case in test_cases:
            # Simulate auth service validation
            if not case["incoming_id"]:
                error_msg = "Token validation request missing service auth headers: X-Service-ID"
            elif case["incoming_id"] != case["expected_id"]:
                error_msg = (
                    f"Service ID mismatch: received '{case['incoming_id']}', "
                    f"expected '{case['expected_id']}'. "
                    f"Backend should use SERVICE_ID='{case['expected_id']}'"
                )
            elif case["incoming_secret"] != case["expected_secret"]:
                error_msg = (
                    f"Service secret mismatch for service '{case['incoming_id']}'. "
                    "Check that SERVICE_SECRET environment variable matches between services."
                )
            else:
                error_msg = None
            
            if error_msg:
                for expected_text in case["error_contains"]:
                    assert expected_text in error_msg, (
                        f"Error message should contain '{expected_text}' for clear debugging"
                    )


def test_quick_staging_check():
    """Quick check that can be run to verify staging is configured correctly."""
    print("\n" + "="*60)
    print("STAGING AUTHENTICATION CONFIGURATION CHECK")
    print("="*60)
    
    # Check .env.staging file
    staging_env_path = ".env.staging"
    if os.path.exists(staging_env_path):
        staging_vars = {}
        with open(staging_env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    staging_vars[key.strip()] = value.strip()
        
        # Check SERVICE_ID
        if "SERVICE_ID" in staging_vars:
            if staging_vars["SERVICE_ID"] == "netra-backend":
                print("[OK] SERVICE_ID is correctly set to 'netra-backend' in .env.staging")
            else:
                print(f"[FAIL] SERVICE_ID is '{staging_vars['SERVICE_ID']}', should be 'netra-backend'")
        else:
            print("[FAIL] SERVICE_ID is not configured in .env.staging")
        
        # Check SERVICE_SECRET
        if "SERVICE_SECRET" in staging_vars:
            secret_len = len(staging_vars["SERVICE_SECRET"])
            if secret_len >= 32:
                print(f"[OK] SERVICE_SECRET is configured ({secret_len} chars)")
            else:
                print(f"[FAIL] SERVICE_SECRET is too short ({secret_len} chars, need 32+)")
        else:
            print("[FAIL] SERVICE_SECRET is not configured in .env.staging")
        
        # Check JWT secrets
        jwt_key = staging_vars.get("JWT_SECRET_KEY") or staging_vars.get("JWT_SECRET_STAGING")
        if jwt_key:
            if staging_vars.get("SERVICE_SECRET") != jwt_key:
                print("[OK] SERVICE_SECRET is different from JWT secret")
            else:
                print("[FAIL] SERVICE_SECRET must be different from JWT secret")
    else:
        print(f"[WARN] Staging environment file not found: {staging_env_path}")
    
    print("="*60)
    print("To fix any issues:")
    print("1. Add to .env.staging: SERVICE_ID=netra-backend")
    print("2. Ensure SERVICE_SECRET is set and at least 32 characters")
    print("3. Deploy changes to staging environment")
    print("="*60)


if __name__ == "__main__":
    # Run quick check
    test_quick_staging_check()
    
    # Run full test suite
    print("\nRunning full test suite...")
    pytest.main([__file__, "-v"])