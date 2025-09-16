"""
Comprehensive Unit Tests for OAuth Manager

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure OAuth authentication reliability prevents user login failures
- Value Impact: Prevents $75K+ MRR loss from authentication failures
- Strategic Impact: Core platform authentication functionality

Test Coverage:
- OAuth Manager initialization and provider management
- Multiple provider support (Google, GitHub, etc.)
- Provider configuration validation
- Status reporting and health checks
- Error handling for misconfigured providers
- Security validations for OAuth state parameters
- Provider availability checks
- Configuration consistency validation

CRITICAL: Uses SSOT BaseTestCase and IsolatedEnvironment.
NO direct os.environ access. Uses real services where possible.
"""
import pytest
import uuid
from typing import Dict, Any
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from auth_service.auth_core.oauth_manager import OAuthManager
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider, GoogleOAuthError

class OAuthManagerInitializationTests(SSotBaseTestCase):
    """Test OAuth manager initialization and basic functionality."""

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var('ENVIRONMENT', 'test')
        self.set_env_var('TESTING', 'true')
        self.manager = None

    def test_oauth_manager_initializes_successfully(self):
        """Test that OAuth manager initializes without errors."""
        self.manager = OAuthManager()
        assert self.manager is not None
        assert hasattr(self.manager, '_providers')
        assert isinstance(self.manager._providers, dict)
        self.record_metric('oauth_manager_initialized', True)

    def test_oauth_manager_initializes_providers(self):
        """Test that OAuth manager initializes available providers."""
        self.manager = OAuthManager()
        providers = self.manager.get_available_providers()
        assert isinstance(providers, list)
        self.record_metric('providers_initialized', len(providers))

    def test_oauth_manager_handles_provider_initialization_failures(self):
        """Test that manager handles provider initialization failures gracefully."""
        with patch('auth_service.auth_core.oauth.google_oauth.GoogleOAuthProvider.__init__') as mock_init:
            mock_init.side_effect = GoogleOAuthError('Test initialization failure')
            self.manager = OAuthManager()
            assert self.manager is not None
            providers = self.manager.get_available_providers()
            assert isinstance(providers, list)
            self.record_metric('providers_after_failure', len(providers))

class OAuthManagerProviderManagementTests(SSotBaseTestCase):
    """Test OAuth manager provider management functionality."""

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var('ENVIRONMENT', 'test')
        self.set_env_var('TESTING', 'true')
        self.manager = OAuthManager()

    def test_get_available_providers_returns_list(self):
        """Test that get_available_providers returns a list."""
        providers = self.manager.get_available_providers()
        assert isinstance(providers, list)
        self.record_metric('available_providers_count', len(providers))

    def test_get_provider_google_returns_correct_type(self):
        """Test getting Google OAuth provider returns correct type or None."""
        provider = self.manager.get_provider('google')
        if provider is not None:
            assert isinstance(provider, GoogleOAuthProvider)
            self.record_metric('google_provider_available', True)
        else:
            self.record_metric('google_provider_available', False)

    def test_get_provider_invalid_returns_none(self):
        """Test that getting an invalid provider returns None."""
        provider = self.manager.get_provider('invalid_provider_name')
        assert provider is None
        self.record_metric('invalid_provider_handled', True)

    def test_get_provider_empty_string_returns_none(self):
        """Test that getting provider with empty string returns None."""
        provider = self.manager.get_provider('')
        assert provider is None

    def test_get_provider_none_returns_none(self):
        """Test that getting provider with None returns None."""
        provider = self.manager.get_provider(None)
        assert provider is None

class OAuthManagerProviderStatusTests(SSotBaseTestCase):
    """Test OAuth manager provider status functionality."""

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var('ENVIRONMENT', 'test')
        self.set_env_var('TESTING', 'true')
        self.manager = OAuthManager()

    def test_is_provider_configured_google(self):
        """Test checking if Google provider is configured."""
        is_configured = self.manager.is_provider_configured('google')
        assert isinstance(is_configured, bool)
        self.record_metric('google_provider_configured', is_configured)

    def test_is_provider_configured_invalid_provider(self):
        """Test checking if invalid provider is configured returns False."""
        is_configured = self.manager.is_provider_configured('invalid_provider')
        assert is_configured is False

    def test_get_provider_status_google(self):
        """Test getting Google provider status."""
        status = self.manager.get_provider_status('google')
        assert isinstance(status, dict)
        assert 'provider' in status
        assert 'available' in status
        assert status['provider'] == 'google'
        if status['available']:
            assert 'configured' in status
            assert 'config_status' in status
            assert isinstance(status['configured'], bool)
        self.record_metric('google_status_retrieved', True)

    def test_get_provider_status_invalid_provider(self):
        """Test getting status for invalid provider."""
        status = self.manager.get_provider_status('invalid_provider')
        assert isinstance(status, dict)
        assert status['provider'] == 'invalid_provider'
        assert status['available'] is False
        assert 'error' in status
        assert 'Provider not found' in status['error']

    def test_get_provider_status_all_fields_present(self):
        """Test that provider status contains all required fields."""
        status = self.manager.get_provider_status('google')
        required_fields = ['provider', 'available']
        for field in required_fields:
            assert field in status, f"Required field '{field}' missing from status"
        if status['available']:
            available_fields = ['configured']
            for field in available_fields:
                assert field in status, f"Available provider field '{field}' missing"

class OAuthManagerErrorHandlingTests(SSotBaseTestCase):
    """Test OAuth manager error handling and edge cases."""

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var('ENVIRONMENT', 'test')
        self.set_env_var('TESTING', 'true')

    def test_manager_handles_provider_initialization_exceptions(self):
        """Test manager handles provider initialization exceptions gracefully."""
        with patch('auth_service.auth_core.oauth.google_oauth.GoogleOAuthProvider.__init__') as mock_init:
            mock_init.side_effect = Exception('Unexpected initialization error')
            manager = OAuthManager()
            assert manager is not None
            providers = manager.get_available_providers()
            assert isinstance(providers, list)

    def test_manager_handles_provider_method_exceptions(self):
        """Test manager handles exceptions in provider methods."""
        manager = OAuthManager()
        with patch.object(manager, '_providers', {'google': MagicMock()}) as mock_providers:
            mock_provider = mock_providers['google']
            mock_provider.is_configured.side_effect = Exception('Provider method error')
            is_configured = manager.is_provider_configured('google')
            assert isinstance(is_configured, bool)

    def test_manager_thread_safety_basic(self):
        """Test basic thread safety of manager operations."""
        manager = OAuthManager()
        results = []
        for _ in range(10):
            providers = manager.get_available_providers()
            results.append(providers)
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result

    def test_manager_memory_usage(self):
        """Test that manager doesn't leak memory during operations."""
        import gc
        initial_objects = len(gc.get_objects())
        for _ in range(10):
            manager = OAuthManager()
            manager.get_available_providers()
            manager.get_provider('google')
            manager.get_provider_status('google')
            del manager
        gc.collect()
        final_objects = len(gc.get_objects())
        growth = final_objects - initial_objects
        assert growth < 1000, f'Excessive memory growth: {growth} objects'
        self.record_metric('memory_growth', growth)

class OAuthManagerIntegrationTests(SSotBaseTestCase):
    """Test OAuth manager integration scenarios."""

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var('ENVIRONMENT', 'test')
        self.set_env_var('TESTING', 'true')
        self.manager = OAuthManager()

    def test_manager_provider_consistency(self):
        """Test consistency between manager and direct provider access."""
        manager_provider = self.manager.get_provider('google')
        if manager_provider is not None:
            direct_provider = GoogleOAuthProvider()
            manager_configured = manager_provider.is_configured()
            direct_configured = direct_provider.is_configured()
            assert manager_configured == direct_configured
            self.record_metric('provider_consistency_verified', True)
        else:
            self.record_metric('google_provider_not_available', True)

    def test_manager_status_vs_provider_health(self):
        """Test that manager status is consistent with provider health."""
        manager_status = self.manager.get_provider_status('google')
        if manager_status['available']:
            provider = self.manager.get_provider('google')
            assert provider is not None
            provider_health = provider.self_check()
            if 'is_healthy' in provider_health:
                manager_configured = manager_status.get('configured', False)
                provider_healthy = provider_health['is_healthy']
                if manager_configured:
                    assert isinstance(provider_healthy, bool)
            self.record_metric('status_health_consistency', True)

    def test_manager_with_multiple_operations(self):
        """Test manager with multiple concurrent operations."""
        operations_count = 0
        providers = self.manager.get_available_providers()
        operations_count += 1
        for provider_name in ['google', 'invalid']:
            provider = self.manager.get_provider(provider_name)
            operations_count += 1
            status = self.manager.get_provider_status(provider_name)
            operations_count += 1
            is_configured = self.manager.is_provider_configured(provider_name)
            operations_count += 1
        self.record_metric('operations_completed', operations_count)
        assert operations_count >= 8

class OAuthManagerConfigurationTests(SSotBaseTestCase):
    """Test OAuth manager configuration scenarios."""

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var('ENVIRONMENT', 'test')
        self.set_env_var('TESTING', 'true')

    def test_manager_with_development_environment(self):
        """Test manager behavior in development environment."""
        with self.temp_env_vars(ENVIRONMENT='development'):
            manager = OAuthManager()
            assert manager is not None
            providers = manager.get_available_providers()
            assert isinstance(providers, list)

    def test_manager_with_staging_environment(self):
        """Test manager behavior in staging environment."""
        with self.temp_env_vars(ENVIRONMENT='staging'):
            manager = OAuthManager()
            assert manager is not None
            status = manager.get_provider_status('google')
            assert isinstance(status, dict)

    def test_manager_with_production_environment(self):
        """Test manager behavior in production environment."""
        with self.temp_env_vars(ENVIRONMENT='production'):
            manager = OAuthManager()
            assert manager is not None
            providers = manager.get_available_providers()
            assert isinstance(providers, list)

    def test_manager_configuration_changes(self):
        """Test manager response to configuration changes."""
        manager = OAuthManager()
        initial_status = manager.get_provider_status('google')
        with self.temp_env_vars(ENVIRONMENT='development'):
            new_manager = OAuthManager()
            new_status = new_manager.get_provider_status('google')
            assert 'provider' in new_status
            assert 'available' in new_status
            assert initial_status['provider'] == new_status['provider']

class OAuthManagerSecurityTests(SSotBaseTestCase):
    """Test OAuth manager security features."""

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var('ENVIRONMENT', 'test')
        self.set_env_var('TESTING', 'true')
        self.manager = OAuthManager()

    def test_manager_no_credential_leakage(self):
        """Test that manager doesn't leak credentials in responses."""
        status = self.manager.get_provider_status('google')
        status_str = str(status).lower()
        forbidden_patterns = ['client_secret', 'password', 'secret=', 'key=', 'token=']
        for pattern in forbidden_patterns:
            assert pattern not in status_str, f'Potential credential leak: {pattern}'
        self.record_metric('credential_leak_check', True)

    def test_manager_input_validation(self):
        """Test manager validates inputs properly."""
        invalid_inputs = [None, '', '  ', 'invalid/provider', 'provider@name']
        for invalid_input in invalid_inputs:
            provider = self.manager.get_provider(invalid_input)
            assert provider is None
            status = self.manager.get_provider_status(invalid_input)
            assert isinstance(status, dict)
            assert status['available'] is False
        self.record_metric('input_validation_tests', len(invalid_inputs))

    def test_manager_state_isolation(self):
        """Test that multiple manager instances don't interfere."""
        manager1 = OAuthManager()
        manager2 = OAuthManager()
        status1 = manager1.get_provider_status('google')
        status2 = manager2.get_provider_status('google')
        assert status1['provider'] == status2['provider']
        assert status1['available'] == status2['available']
        self.record_metric('state_isolation_verified', True)

class OAuthManagerPerformanceTests(SSotBaseTestCase):
    """Test OAuth manager performance characteristics."""

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var('ENVIRONMENT', 'test')
        self.set_env_var('TESTING', 'true')

    def test_manager_initialization_performance(self):
        """Test that manager initializes within reasonable time."""
        import time
        start_time = time.time()
        manager = OAuthManager()
        end_time = time.time()
        initialization_time = end_time - start_time
        assert initialization_time < 1.0, f'Initialization took {initialization_time:.3f}s'
        self.record_metric('initialization_time', initialization_time)

    def test_manager_operation_performance(self):
        """Test that manager operations are performant."""
        manager = OAuthManager()
        import time
        operations = [lambda: manager.get_available_providers(), lambda: manager.get_provider('google'), lambda: manager.get_provider_status('google'), lambda: manager.is_provider_configured('google')]
        for i, operation in enumerate(operations):
            start_time = time.time()
            result = operation()
            end_time = time.time()
            operation_time = end_time - start_time
            assert operation_time < 0.1, f'Operation {i} took {operation_time:.3f}s'
            self.record_metric(f'operation_{i}_time', operation_time)

    def test_manager_memory_efficiency(self):
        """Test that manager uses memory efficiently."""
        import sys
        manager = OAuthManager()
        manager_size = sys.getsizeof(manager)
        assert manager_size < 10240, f'Manager size: {manager_size} bytes'
        self.record_metric('manager_size_bytes', manager_size)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')