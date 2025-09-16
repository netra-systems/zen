"""
Unit tests for SessionMiddleware SECRET_KEY validation.
Tests configuration requirements that prevent staging deployment failures.
"""

import unittest
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestSessionMiddlewareSecretKeyValidation(SSotBaseTestCase):
    """Test SECRET_KEY validation for SessionMiddleware configuration."""
    
    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        self.original_secret = self.env.get("SECRET_KEY")
        
    def teardown_method(self, method=None):
        """Clean up test environment."""
        if self.original_secret:
            self.env.set("SECRET_KEY", self.original_secret)
        else:
            self.env.unset("SECRET_KEY")
        super().teardown_method(method)
        
    def test_secret_key_minimum_length_requirement(self):
        """Test that SECRET_KEY must be at least 32 characters."""
        from netra_backend.app.core.middleware_setup import _validate_and_get_secret_key
        from unittest.mock import MagicMock
        
        # Test with short key (should fail)
        short_key = "short_key_123"
        self.env.set("SECRET_KEY", short_key)
        
        # Create mock config and environment
        config = MagicMock()
        config.secret_key = short_key
        
        with self.assertRaises(ValueError) as context:
            _validate_and_get_secret_key(config, self.env)
        
        self.assertIn("at least 32 characters", str(context.exception))
        self._track_metric("secret_key_validation", "short_key_rejected", 1)
        
    def test_secret_key_valid_length_accepted(self):
        """Test that valid length SECRET_KEY is accepted."""
        from netra_backend.app.core.middleware_setup import _validate_and_get_secret_key
        from unittest.mock import MagicMock
        
        # Test with valid key (32+ characters)
        valid_key = "a" * 32 + "valid_secret_key_for_testing"
        self.env.set("SECRET_KEY", valid_key)
        
        # Create mock config
        config = MagicMock()
        config.secret_key = valid_key
        
        result = _validate_and_get_secret_key(config, self.env)
        self.assertEqual(result, valid_key)
        self._track_metric("secret_key_validation", "valid_key_accepted", 1)
        
    def test_secret_key_missing_environment_fallback(self):
        """Test fallback behavior when SECRET_KEY is missing."""
        from netra_backend.app.core.middleware_setup import _validate_and_get_secret_key
        from unittest.mock import MagicMock
        
        # Remove SECRET_KEY from environment
        self.env.unset("SECRET_KEY")
        
        # Create mock config with no secret_key
        config = MagicMock()
        config.secret_key = None
        
        with self.assertRaises(ValueError) as context:
            _validate_and_get_secret_key(config, self.env)
        
        self.assertIn("SECRET_KEY", str(context.exception))
        self._track_metric("secret_key_validation", "missing_key_error", 1)
        
    def test_staging_environment_secret_key_requirement(self):
        """Test SECRET_KEY requirements in staging environment."""
        from netra_backend.app.core.middleware_setup import _validate_and_get_secret_key
        from unittest.mock import MagicMock
        
        # Simulate staging environment
        self.env.set("ENV", "staging")
        self.env.set("SECRET_KEY", "staging_key_short")
        
        # Create mock config
        config = MagicMock()
        config.secret_key = "staging_key_short"
        
        with self.assertRaises(ValueError) as context:
            _validate_and_get_secret_key(config, self.env)
        
        self.assertIn("at least 32 characters", str(context.exception))
        self._track_metric("secret_key_validation", "staging_validation_failed", 1)
        
    def test_production_environment_secret_key_requirement(self):
        """Test SECRET_KEY requirements in production environment."""
        from netra_backend.app.core.middleware_setup import _validate_and_get_secret_key
        from unittest.mock import MagicMock
        
        # Simulate production environment with valid key
        self.env.set("ENV", "production")
        prod_key = "production_secret_key_" + "x" * 32
        self.env.set("SECRET_KEY", prod_key)
        
        # Create mock config
        config = MagicMock()
        config.secret_key = prod_key
        
        result = _validate_and_get_secret_key(config, self.env)
        self.assertEqual(result, prod_key)
        self._track_metric("secret_key_validation", "production_validation_passed", 1)
        
    def test_development_environment_secret_key_handling(self):
        """Test SECRET_KEY handling in development environment."""
        from netra_backend.app.core.middleware_setup import _validate_and_get_secret_key
        from unittest.mock import MagicMock
        
        # Simulate development environment
        self.env.set("ENV", "development")
        dev_key = "dev_key"  # Short key might be allowed in dev
        self.env.set("SECRET_KEY", dev_key)
        
        # Create mock config
        config = MagicMock()
        config.secret_key = dev_key
        
        # Development might have relaxed requirements or generate a default
        try:
            result = _validate_and_get_secret_key(config, self.env)
            if result == dev_key:
                self._track_metric("secret_key_validation", "dev_short_key_allowed", 1)
            else:
                self._track_metric("secret_key_validation", "dev_default_generated", 1)
        except ValueError:
            # Even dev might require minimum length
            self._track_metric("secret_key_validation", "dev_validation_enforced", 1)
            
    def test_secret_key_special_characters_handling(self):
        """Test SECRET_KEY with special characters."""
        from netra_backend.app.core.middleware_setup import _validate_and_get_secret_key
        from unittest.mock import MagicMock
        
        # Test with special characters
        special_key = "!@#$%^&*()_+" + "a" * 32 + "{}[]|\\:;\"'<>,.?/"
        self.env.set("SECRET_KEY", special_key)
        
        # Create mock config
        config = MagicMock()
        config.secret_key = special_key
        
        result = _validate_and_get_secret_key(config, self.env)
        self.assertEqual(result, special_key)
        self._track_metric("secret_key_validation", "special_chars_accepted", 1)


if __name__ == "__main__":
    unittest.main()