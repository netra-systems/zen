"""
Example Test: Proper Usage of URL Assertions

This test demonstrates when to use flexible vs exact URL assertions
based on test intent and environment.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Improve test reliability and maintainability
- Value Impact: Reduces false test failures from dynamic ports
- Strategic Impact: Enables parallel testing and CI/CD efficiency
"""
import pytest
import os
from shared.isolated_environment import IsolatedEnvironment
from test_framework.url_assertions import assert_base_url_matches, assert_is_localhost_url, assert_is_staging_url, assert_is_production_url, assert_no_localhost_in_url, extract_base_url, extract_port, build_url_with_port, URLAssertion

class TestConfigURLAssertions:
    """Demonstrates proper URL assertion patterns for config tests."""

    def test_config_structure_flexible_ports(self):
        """
        Test config has correct structure without requiring specific ports.
        Use this pattern when testing with dynamic Docker ports.
        """
        config = Mock()
        config.api_url = 'http://localhost:8001'
        config.auth_url = 'http://localhost:8082'
        assert_is_localhost_url(config.api_url)
        assert_is_localhost_url(config.auth_url)
        assert_base_url_matches(config.api_url, 'http://localhost', ignore_port=True)
        assert_base_url_matches(config.auth_url, 'http://localhost', ignore_port=True)
        api_port = extract_port(config.api_url)
        auth_port = extract_port(config.auth_url)
        assert api_port is not None, 'API URL should have a port'
        assert auth_port is not None, 'Auth URL should have a port'
        assert api_port != auth_port, 'Services should use different ports'

    def test_development_config_exact_ports(self):
        """
        Test development environment uses standard ports.
        Use exact assertions when ports are part of the specification.
        """
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            config = Mock()
            config.api_url = 'http://localhost:8000'
            config.auth_url = 'http://localhost:8081'
            config.frontend_url = 'http://localhost:3000'
            assert config.api_url == 'http://localhost:8000'
            assert config.auth_url == 'http://localhost:8081'
            assert config.frontend_url == 'http://localhost:3000'

    def test_staging_config_no_localhost(self):
        """
        Test staging configuration uses proper domains.
        Critical for preventing localhost URLs in production environments.
        """
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            config = Mock()
            config.api_url = 'https://api.staging.netrasystems.ai'
            config.auth_url = 'https://auth.staging.netrasystems.ai'
            config.frontend_url = 'https://app.staging.netrasystems.ai'
            assert_is_staging_url(config.api_url)
            assert_is_staging_url(config.auth_url)
            assert_is_staging_url(config.frontend_url)
            assert_no_localhost_in_url(config.api_url)
            assert_no_localhost_in_url(config.auth_url)
            assert_no_localhost_in_url(config.frontend_url)
            assert config.api_url == 'https://api.staging.netrasystems.ai'
            assert config.auth_url == 'https://auth.staging.netrasystems.ai'

    def test_production_config_exact_urls(self):
        """
        Test production configuration uses exact production URLs.
        Production URLs must be exactly as specified.
        """
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            config = Mock()
            config.api_url = 'https://api.netrasystems.ai'
            config.auth_url = 'https://auth.netrasystems.ai'
            config.frontend_url = 'https://app.netrasystems.ai'
            assert config.api_url == 'https://api.netrasystems.ai'
            assert config.auth_url == 'https://auth.netrasystems.ai'
            assert config.frontend_url == 'https://app.netrasystems.ai'
            assert_is_production_url(config.api_url)
            assert_is_production_url(config.auth_url)
            assert_is_production_url(config.frontend_url)

    def test_dynamic_port_discovery(self):
        """
        Test configuration with dynamically discovered ports.
        Common pattern when using Docker with dynamic port allocation.
        """
        discovered_ports = {'backend': 8005, 'auth': 8086, 'frontend': 3002}
        config = Mock()
        config.api_url = build_url_with_port('http://localhost', discovered_ports['backend'])
        config.auth_url = build_url_with_port('http://localhost', discovered_ports['auth'])
        config.frontend_url = build_url_with_port('http://localhost', discovered_ports['frontend'])
        assert_is_localhost_url(config.api_url)
        assert_is_localhost_url(config.auth_url)
        assert_is_localhost_url(config.frontend_url)
        assert extract_port(config.api_url) == discovered_ports['backend']
        assert extract_port(config.auth_url) == discovered_ports['auth']
        assert extract_port(config.frontend_url) == discovered_ports['frontend']

    def test_url_assertion_context_manager(self):
        """
        Test using URLAssertion context manager for batch assertions.
        Useful when you have many URLs to check with same rules.
        """
        configs = [Mock(api_url='http://localhost:8000', auth_url='http://localhost:8081'), Mock(api_url='http://localhost:8002', auth_url='http://localhost:8083'), Mock(api_url='http://localhost:8004', auth_url='http://localhost:8085')]
        with URLAssertion(ignore_port=True) as url_assert:
            for config in configs:
                url_assert.assert_equal(config.api_url, 'http://localhost:8000')
                url_assert.assert_equal(config.auth_url, 'http://localhost:8081')

    def test_mixed_assertion_patterns(self):
        """
        Test mixing exact and flexible assertions based on requirements.
        Shows how to be selective about what to assert.
        """
        config = Mock()
        config.api_url = 'http://localhost:8000'
        config.auth_url = 'http://localhost:8081'
        config.external_api = 'https://api.example.com'
        config.webhook_url = 'https://webhook.example.com:9000/callback'
        assert config.api_url == 'http://localhost:8000'
        assert config.auth_url == 'http://localhost:8081'
        assert_base_url_matches(config.external_api, 'https://api.example.com', ignore_port=True)
        assert config.webhook_url.startswith('https://webhook.example.com')
        assert '/callback' in config.webhook_url
        webhook_port = extract_port(config.webhook_url)
        assert webhook_port == 9000, 'Webhook should use port 9000'

class TestURLAssertionHelpers:
    """Test the URL assertion helper functions themselves."""

    def test_extract_base_url(self):
        """Test extracting base URL without port."""
        assert extract_base_url('http://localhost:8000') == 'http://localhost'
        assert extract_base_url('https://api.example.com:443') == 'https://api.example.com'
        assert extract_base_url('http://example.com') == 'http://example.com'

    def test_extract_port(self):
        """Test extracting port from URL."""
        assert extract_port('http://localhost:8000') == 8000
        assert extract_port('https://api.example.com:443') == 443
        assert extract_port('http://example.com') is None
        assert extract_port('https://example.com') is None

    def test_build_url_with_port(self):
        """Test building URL with specific port."""
        assert build_url_with_port('http://localhost', 8000) == 'http://localhost:8000'
        assert build_url_with_port('https://api.example.com', 9000) == 'https://api.example.com:9000'
        assert build_url_with_port('http://example.com', 80) == 'http://example.com'
        assert build_url_with_port('https://example.com', 443) == 'https://example.com'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')