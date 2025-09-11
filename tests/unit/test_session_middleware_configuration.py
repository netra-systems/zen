"""
Unit tests for SessionMiddleware configuration scenarios.
Reproduces Issue #169 SessionMiddleware installation and configuration failures.

CRITICAL MISSION: These tests validate the complete SessionMiddleware setup chain
to identify exactly where the 'SessionMiddleware must be installed' errors originate.
"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestSessionMiddlewareConfiguration(SSotBaseTestCase):
    """Test SessionMiddleware configuration and installation scenarios."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        # Environment is available as self._env from SSotBaseTestCase
        
        # Store original values
        self.original_values = {
            'ENVIRONMENT': self._env.get('ENVIRONMENT'),
            'SECRET_KEY': self._env.get('SECRET_KEY'),
            'K_SERVICE': self._env.get('K_SERVICE'),
            'GCP_PROJECT_ID': self._env.get('GCP_PROJECT_ID')
        }
        
    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment
        for key, value in self.original_values.items():
            if value is not None:
                self._env.set(key, value)
            else:
                self._env.unset(key)
        super().tearDown()
        
    def test_session_middleware_staging_configuration_validation(self):
        """Test SessionMiddleware configuration validation for staging environment.
        
        CRITICAL: This reproduces the exact staging configuration that fails.
        """
        from netra_backend.app.core.middleware_setup import setup_session_middleware
        from fastapi import FastAPI
        
        # Simulate GCP Cloud Run staging environment
        self._env.set("ENVIRONMENT", "staging")
        self._env.set("K_SERVICE", "netra-staging-backend")
        
        # Test with missing SECRET_KEY (reproduces the issue)
        self._env.unset("SECRET_KEY")
        
        app = FastAPI()
        
        try:
            setup_session_middleware(app)
            
            # If successful, verify SessionMiddleware was actually added
            session_middleware_found = any(
                'SessionMiddleware' in str(middleware.cls) 
                for middleware in app.user_middleware
            )
            
            if session_middleware_found:
                self.record_metric("staging_config", "middleware_installed", 1)
            else:
                self.record_metric("staging_config", "middleware_not_found", 1)
                self.fail("SessionMiddleware setup succeeded but middleware not found in stack")
                
        except Exception as e:
            # This is the expected error that causes Issue #169
            self.record_metric("staging_config", "setup_failed", 1)
            
            # Log the specific error for analysis
            error_msg = str(e).lower()
            if "secret" in error_msg:
                self.record_metric("staging_config", "secret_key_error", 1)
            if "gcp" in error_msg or "secret manager" in error_msg:
                self.record_metric("staging_config", "gcp_secret_manager_error", 1)
                
            # Re-raise for further analysis
            raise
            
    def test_middleware_order_dependency_validation(self):
        """Test middleware installation order to prevent dependency issues.
        
        SessionMiddleware must be installed before GCPAuthContextMiddleware.
        """
        from netra_backend.app.core.middleware_setup import setup_middleware
        from fastapi import FastAPI
        
        self._env.set("ENVIRONMENT", "staging")
        valid_secret = "a" * 32 + "valid_secret_for_middleware_order_test"
        self._env.set("SECRET_KEY", valid_secret)
        
        app = FastAPI()
        
        try:
            setup_middleware(app)
            
            # Check middleware order
            middleware_classes = [str(middleware.cls) for middleware in app.user_middleware]
            
            session_index = -1
            auth_context_index = -1
            
            for i, middleware_str in enumerate(middleware_classes):
                if 'SessionMiddleware' in middleware_str:
                    session_index = i
                if 'GCPAuth' in middleware_str or 'AuthContext' in middleware_str:
                    auth_context_index = i
                    
            # SessionMiddleware should be installed before auth context middleware
            if session_index >= 0 and auth_context_index >= 0:
                # Note: middleware stack is processed in reverse order
                if session_index > auth_context_index:
                    self.record_metric("middleware_order", "correct_order", 1)
                else:
                    self.record_metric("middleware_order", "incorrect_order", 1)
                    self.fail("SessionMiddleware must be installed after GCPAuthContextMiddleware in stack (processed first)")
            elif session_index >= 0:
                self.record_metric("middleware_order", "session_only", 1)
            else:
                self.record_metric("middleware_order", "no_session_middleware", 1)
                self.fail("SessionMiddleware not found in middleware stack")
                
        except Exception as e:
            self.record_metric("middleware_order", "setup_failed", 1)
            raise
            
    def test_session_middleware_secret_key_validation_integration(self):
        """Test integration between secret validation and SessionMiddleware setup."""
        from netra_backend.app.core.middleware_setup import _validate_and_get_secret_key
        from netra_backend.app.core.configuration import get_configuration
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        
        self._env.set("ENVIRONMENT", "staging")
        
        # Test with valid secret
        valid_secret = "a" * 32 + "integration_test_secret_key"
        self._env.set("SECRET_KEY", valid_secret)
        
        config = get_configuration()
        auth_client = AuthServiceClient()
        environment = auth_client.detect_environment()
        
        try:
            result_secret = _validate_and_get_secret_key(config, environment)
            
            self.assertEqual(result_secret, valid_secret)
            self.record_metric("secret_integration", "valid_key_accepted", 1)
            
        except Exception as e:
            self.record_metric("secret_integration", "validation_failed", 1)
            self.fail(f"Valid secret key validation failed: {e}")
            
    def test_session_middleware_fallback_mechanism(self):
        """Test SessionMiddleware fallback when primary setup fails."""
        from netra_backend.app.core.middleware_setup import _add_fallback_session_middleware
        from fastapi import FastAPI
        
        app = FastAPI()
        
        # This should always succeed as emergency fallback
        _add_fallback_session_middleware(app)
        
        # Verify fallback middleware was added
        session_middleware_found = any(
            'SessionMiddleware' in str(middleware.cls)
            for middleware in app.user_middleware
        )
        
        self.assertTrue(session_middleware_found, "Fallback SessionMiddleware should be installed")
        self.record_metric("fallback_mechanism", "fallback_installed", 1)
        
    def test_environment_specific_session_configuration(self):
        """Test environment-specific session configuration differences."""
        from netra_backend.app.core.middleware_setup import _determine_session_config
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        
        auth_client = AuthServiceClient()
        
        # Test development configuration
        self._env.set("ENVIRONMENT", "development")
        dev_env = auth_client.detect_environment()
        dev_config = _determine_session_config(dev_env)
        
        self.assertIn("same_site", dev_config)
        self.assertIn("https_only", dev_config)
        self.record_metric("env_config", "development_config", 1)
        
        # Test staging configuration
        self._env.set("ENVIRONMENT", "staging")
        staging_env = auth_client.detect_environment()
        staging_config = _determine_session_config(staging_env)
        
        self.assertIn("same_site", staging_config)
        self.assertIn("https_only", staging_config)
        
        # Staging should be more secure than development
        if staging_config["https_only"] and not dev_config.get("https_only", False):
            self.record_metric("env_config", "staging_more_secure", 1)
        
    def test_session_middleware_installation_validation(self):
        """Test post-installation validation catches configuration issues."""
        from netra_backend.app.core.middleware_setup import _validate_session_middleware_installation
        from fastapi import FastAPI
        from starlette.middleware.sessions import SessionMiddleware
        
        app = FastAPI()
        
        # Test with no SessionMiddleware
        try:
            _validate_session_middleware_installation(app)
            # Should log warning but not fail
            self.record_metric("installation_validation", "no_middleware_detected", 1)
        except Exception as e:
            # Should not raise exceptions, only log warnings
            self.fail(f"Validation should not raise exceptions: {e}")
            
        # Test with SessionMiddleware installed
        app.add_middleware(
            SessionMiddleware,
            secret_key="test_key_32_characters_minimum_required",
            same_site="lax",
            https_only=False
        )
        
        try:
            _validate_session_middleware_installation(app)
            self.record_metric("installation_validation", "middleware_found", 1)
        except Exception as e:
            self.fail(f"Validation with installed middleware should not fail: {e}")
            
    def test_gcp_cloud_run_specific_configuration(self):
        """Test GCP Cloud Run specific configuration handling."""
        from netra_backend.app.core.middleware_setup import setup_session_middleware
        from fastapi import FastAPI
        
        # Simulate Cloud Run environment
        self._env.set("ENVIRONMENT", "staging")
        self._env.set("K_SERVICE", "netra-staging-backend")
        self._env.set("K_REVISION", "netra-staging-backend-00001")
        
        valid_secret = "a" * 32 + "cloud_run_test_secret_key"
        self._env.set("SECRET_KEY", valid_secret)
        
        app = FastAPI()
        
        try:
            setup_session_middleware(app)
            
            # Should succeed in Cloud Run environment
            middleware_found = any(
                'SessionMiddleware' in str(middleware.cls)
                for middleware in app.user_middleware
            )
            
            self.assertTrue(middleware_found, "SessionMiddleware should be installed in Cloud Run")
            self.record_metric("cloud_run_config", "setup_successful", 1)
            
        except Exception as e:
            self.record_metric("cloud_run_config", "setup_failed", 1)
            # This reproduces the production issue
            raise
            
    def test_concurrent_session_middleware_initialization(self):
        """Test SessionMiddleware initialization under concurrent conditions."""
        import asyncio
        from netra_backend.app.core.middleware_setup import setup_session_middleware
        from fastapi import FastAPI
        
        self._env.set("ENVIRONMENT", "development")
        valid_secret = "a" * 32 + "concurrent_test_secret_key"
        self._env.set("SECRET_KEY", valid_secret)
        
        async def setup_app():
            app = FastAPI()
            setup_session_middleware(app)
            return app
            
        # Test multiple concurrent initializations
        async def test_concurrent():
            tasks = [setup_app() for _ in range(3)]
            apps = await asyncio.gather(*tasks)
            
            # All should succeed
            for app in apps:
                middleware_found = any(
                    'SessionMiddleware' in str(middleware.cls)
                    for middleware in app.user_middleware
                )
                self.assertTrue(middleware_found)
                
            self.record_metric("concurrent_init", "all_successful", 1)
            
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_concurrent())
        finally:
            loop.close()


if __name__ == "__main__":
    unittest.main()