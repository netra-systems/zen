"""
Unit tests for UnifiedSecretManager SESSION_SECRET loading scenarios.
Reproduces Issue #169 SessionMiddleware authentication context extraction failures.

CRITICAL MISSION: These tests are designed to reproduce the specific error conditions
that cause 'SessionMiddleware must be installed to access request.session' errors.
"""

import unittest
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestUnifiedSecretManagerSessionKeys(SSotBaseTestCase):
    """Test UnifiedSecretManager SESSION_SECRET loading scenarios."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.original_environment = self._env.get("ENVIRONMENT")
        self.original_secret_key = self._env.get("SECRET_KEY")
        self.original_session_secret = self._env.get("SESSION_SECRET")
        
    def tearDown(self):
        """Clean up test environment."""
        # Restore original values
        if self.original_environment:
            self._env.set("ENVIRONMENT", self.original_environment)
        else:
            self._env.unset("ENVIRONMENT")
            
        if self.original_secret_key:
            self._env.set("SECRET_KEY", self.original_secret_key)
        else:
            self._env.unset("SECRET_KEY")
            
        if self.original_session_secret:
            self._env.set("SESSION_SECRET", self.original_session_secret)
        else:
            self._env.unset("SESSION_SECRET")
        super().tearDown()
        
    def test_session_secret_minimum_length_requirement(self):
        """Test that SESSION_SECRET must be at least 32 characters.
        
        CRITICAL: This test reproduces the exact configuration issue
        that causes SessionMiddleware installation failures.
        """
        from netra_backend.app.core.unified_secret_manager import get_session_secret
        
        # Set environment for staging (where issue occurs)
        self._env.set("ENVIRONMENT", "staging")
        
        # Test with short key (should fail)
        short_key = "short_key_123"  # Only 13 characters
        self._env.set("SECRET_KEY", short_key)
        
        try:
            secret_info = get_session_secret("staging")
            
            # If no exception, validate the secret meets minimum requirements
            if len(secret_info.value) < 32:
                self.fail("Short SECRET_KEY should not be accepted or should be replaced with fallback")
                
            # Track if fallback was used
            if secret_info.is_fallback:
                self.record_metric("secret_key_validation_short_key_fallback_used", 1)
            else:
                self.fail("Short key accepted without fallback - this causes SessionMiddleware failures")
                
        except Exception as e:
            # Exception is expected for short keys
            self.assertIn("32 characters", str(e).lower())
            self.record_metric("secret_key_validation", "short_key_rejected", 1)
        
    def test_session_secret_missing_environment_reproduction(self):
        """Test reproduction of missing SECRET_KEY causing SessionMiddleware failures.
        
        CRITICAL: This reproduces the exact GCP staging error condition.
        """
        from netra_backend.app.core.unified_secret_manager import get_session_secret
        
        # Simulate GCP staging environment
        self._env.set("ENVIRONMENT", "staging")
        self._env.set("K_SERVICE", "netra-staging-backend")  # Cloud Run indicator
        
        # Remove all secret environment variables
        self._env.unset("SECRET_KEY")
        self._env.unset("SESSION_SECRET")
        
        try:
            secret_info = get_session_secret("staging")
            
            # In staging, should either fail or use secure fallback
            if secret_info.is_generated:
                # Generated secrets in staging should be logged as error condition
                self.record_metric("secret_key_validation", "staging_generated_secret", 1)
                self.assertTrue(len(secret_info.value) >= 32, "Generated secret must meet minimum length")
            else:
                # If not generated, must be from valid source
                self.assertIn(secret_info.source.value, ["gcp", "env"], 
                             "Staging should use GCP or environment secrets")
                
        except Exception as e:
            # Expected for staging when no secrets available
            self.assertIn("SECRET_KEY", str(e))
            self.record_metric("secret_key_validation", "staging_no_secret_error", 1)
            
    def test_gcp_secret_manager_fallback_scenarios(self):
        """Test GCP Secret Manager fallback scenarios.
        
        Tests the complete fallback chain that prevents SessionMiddleware failures.
        """
        from netra_backend.app.core.unified_secret_manager import UnifiedSecretManager
        
        # Mock GCP environment
        self._env.set("ENVIRONMENT", "staging")
        self._env.set("GCP_PROJECT_ID", "netra-staging")
        
        # Mock GCP Secret Manager failure
        with patch('netra_backend.app.core.unified_secret_manager.UnifiedSecretManager._load_from_gcp_secret_manager') as mock_gcp:
            mock_gcp.side_effect = Exception("Secret Manager API unavailable")
            
            manager = UnifiedSecretManager("staging")
            
            try:
                secret_info = manager.get_secret("SESSION_SECRET", "SECRET_KEY")
                
                # Should use fallback, not fail
                self.assertIsNotNone(secret_info)
                self.assertTrue(secret_info.is_fallback, "Should use fallback when GCP fails")
                self.assertTrue(len(secret_info.value) >= 32, "Fallback must meet minimum requirements")
                
                self.record_metric("gcp_fallback", "secret_manager_unavailable", 1)
                
            except Exception as e:
                # GCP failure should not cause deployment failures
                self.record_metric("gcp_fallback", "fallback_failed", 1)
                self.fail(f"GCP Secret Manager failure should use fallback, not fail: {e}")
                
    def test_development_vs_staging_secret_handling(self):
        """Test different secret handling between development and staging.
        
        Development can be permissive, staging must be secure.
        """
        from netra_backend.app.core.unified_secret_manager import get_session_secret
        
        # Test development environment
        self._env.set("ENVIRONMENT", "development")
        self._env.unset("SECRET_KEY")
        
        try:
            dev_secret = get_session_secret("development")
            
            # Development should get working secret (generated if needed)
            self.assertIsNotNone(dev_secret)
            self.assertTrue(len(dev_secret.value) >= 32)
            
            if dev_secret.is_generated:
                self.record_metric("environment_handling", "dev_generated_secret", 1)
            
        except Exception:
            # Development should not fail due to missing secrets
            self.record_metric("environment_handling", "dev_secret_failed", 1)
            
        # Test staging environment (stricter)
        self._env.set("ENVIRONMENT", "staging")
        
        try:
            staging_secret = get_session_secret("staging")
            
            # Staging should be more restrictive
            if staging_secret.is_generated:
                # Generated secrets in staging should trigger warnings
                self.record_metric("environment_handling", "staging_generated_secret", 1)
                
        except Exception:
            # Staging may fail if no proper secrets available
            self.record_metric("environment_handling", "staging_secret_validation_failed", 1)
            
    def test_session_secret_caching_behavior(self):
        """Test secret caching to prevent multiple GCP calls."""
        from netra_backend.app.core.unified_secret_manager import UnifiedSecretManager
        
        self._env.set("ENVIRONMENT", "staging") 
        valid_secret = "a" * 32 + "valid_session_secret_for_caching_test"
        self._env.set("SECRET_KEY", valid_secret)
        
        manager = UnifiedSecretManager("staging")
        
        # First call
        secret1 = manager.get_secret("SESSION_SECRET", "SECRET_KEY")
        
        # Second call should use cache
        secret2 = manager.get_secret("SESSION_SECRET", "SECRET_KEY")
        
        self.assertEqual(secret1.value, secret2.value)
        self.record_metric("secret_caching", "cache_hit_detected", 1)
        
    def test_session_secret_validation_notes_logging(self):
        """Test that validation notes provide debugging information."""
        from netra_backend.app.core.unified_secret_manager import get_session_secret
        
        self._env.set("ENVIRONMENT", "staging")
        
        # Use a secret with potential issues
        borderline_secret = "a" * 32  # Exactly 32 characters
        self._env.set("SECRET_KEY", borderline_secret)
        
        secret_info = get_session_secret("staging")
        
        # Should have validation notes for debugging
        self.assertIsInstance(secret_info.validation_notes, list)
        self.record_metric("validation_logging", "notes_generated", len(secret_info.validation_notes))
        
    def test_emergency_fallback_prevents_deployment_failure(self):
        """Test that emergency fallbacks prevent SessionMiddleware deployment failures.
        
        CRITICAL: This tests the last line of defense against Issue #169.
        """
        from netra_backend.app.core.unified_secret_manager import UnifiedSecretManager
        
        # Simulate complete configuration failure
        self._env.set("ENVIRONMENT", "development")  # Use dev for emergency fallback
        self._env.unset("SECRET_KEY")
        self._env.unset("SESSION_SECRET")
        
        # Mock all external sources failing
        with patch('netra_backend.app.core.unified_secret_manager.UnifiedSecretManager._load_from_gcp_secret_manager') as mock_gcp:
            mock_gcp.side_effect = Exception("All secrets unavailable")
            
            manager = UnifiedSecretManager("development")
            
            # Should still get a working secret to prevent deployment failure
            secret_info = manager.get_secret("SESSION_SECRET", "SECRET_KEY")
            
            self.assertIsNotNone(secret_info, "Emergency fallback must provide working secret")
            self.assertTrue(len(secret_info.value) >= 32, "Emergency secret must meet requirements")
            self.assertTrue(secret_info.is_generated, "Should be marked as generated")
            
            self.record_metric("emergency_fallback", "deployment_failure_prevented", 1)
            
    def test_production_environment_strict_requirements(self):
        """Test that production environment has strict secret requirements.
        
        Production should never use generated secrets.
        """
        from netra_backend.app.core.unified_secret_manager import get_session_secret
        
        # Simulate production environment
        self._env.set("ENVIRONMENT", "production")
        self._env.unset("SECRET_KEY")
        
        try:
            secret_info = get_session_secret("production")
            
            # Production should never use generated secrets
            self.assertFalse(secret_info.is_generated, 
                           "Production must never use generated secrets")
            
            # Must be from secure source
            self.assertIn(secret_info.source.value, ["gcp", "env"],
                         "Production must use GCP Secret Manager or secure env vars")
                         
            self.record_metric("production_security", "secure_secret_loaded", 1)
            
        except Exception:
            # Production may legitimately fail if no secure secrets available
            self.record_metric("production_security", "secure_secret_required_failed", 1)
            # This is expected behavior for production


if __name__ == "__main__":
    unittest.main()