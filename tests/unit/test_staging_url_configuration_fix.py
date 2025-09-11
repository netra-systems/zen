"""
Unit Tests for Staging URL Configuration Fix - Issue #257

Business Value Justification (BVJ):
- Segment: Platform/Internal - Deployment Infrastructure 
- Business Goal: Prevent staging environment configuration drift and hardcoded URL issues
- Value Impact: Eliminates production-staging URL discrepancies that block testing and deployment
- Revenue Protection: Ensures staging accurately represents production for $500K+ ARR validation

PURPOSE: 
Test that staging environment URLs are properly centralized and not hardcoded.
Validates that all staging tests use URLConstants.STAGING_BACKEND_URL instead of
hardcoded "https://netra-staging-backend.run.app" values.

ISSUE #257: E2E staging tests use hardcoded URLs instead of centralized constants,
causing staging environment to point to wrong infrastructure and breaking integration tests.

These tests MUST FAIL initially to demonstrate the hardcoded URL problem before the fix.
"""

import pytest
import re
from typing import List, Dict, Set
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import the modules we need to test
from netra_backend.app.core.network_constants import URLConstants


class TestStagingUrlConfigurationFix(SSotBaseTestCase):
    """
    Test suite for staging URL configuration centralization fix.
    
    These tests validate that staging URLs are properly centralized
    and not hardcoded throughout the codebase.
    """
    
    def test_staging_url_constants_exist(self):
        """Test that all required staging URL constants are defined in URLConstants."""
        
        # Verify that URLConstants has the staging URLs we expect
        assert hasattr(URLConstants, 'STAGING_BACKEND_URL'), (
            "URLConstants missing STAGING_BACKEND_URL constant"
        )
        assert hasattr(URLConstants, 'STAGING_AUTH_URL'), (
            "URLConstants missing STAGING_AUTH_URL constant"
        )
        assert hasattr(URLConstants, 'STAGING_FRONTEND_URL'), (
            "URLConstants missing STAGING_FRONTEND_URL constant"
        )
        assert hasattr(URLConstants, 'STAGING_WEBSOCKET_URL'), (
            "URLConstants missing STAGING_WEBSOCKET_URL constant"
        )
        
        # Verify the URLs are the correct load balancer endpoints
        assert URLConstants.STAGING_BACKEND_URL == "https://api.staging.netrasystems.ai", (
            f"STAGING_BACKEND_URL should be load balancer endpoint, got: {URLConstants.STAGING_BACKEND_URL}"
        )
        assert URLConstants.STAGING_AUTH_URL == "https://auth.staging.netrasystems.ai", (
            f"STAGING_AUTH_URL should be load balancer endpoint, got: {URLConstants.STAGING_AUTH_URL}"
        )
        assert URLConstants.STAGING_FRONTEND_URL == "https://app.staging.netrasystems.ai", (
            f"STAGING_FRONTEND_URL should be load balancer endpoint, got: {URLConstants.STAGING_FRONTEND_URL}"
        )
        assert URLConstants.STAGING_WEBSOCKET_URL == "wss://api.staging.netrasystems.ai/ws", (
            f"STAGING_WEBSOCKET_URL should be load balancer WebSocket endpoint, got: {URLConstants.STAGING_WEBSOCKET_URL}"
        )
    
    def test_no_hardcoded_staging_urls_in_e2e_tests(self):
        """
        Test that E2E tests do not contain hardcoded staging URLs.
        
        THIS TEST SHOULD FAIL INITIALLY - demonstrating the current hardcoded URL problem.
        """
        
        # Read the E2E staging test file that has the issue
        e2e_test_file = "/Users/anthony/Desktop/netra-apex/tests/e2e/test_basic_triage_response_staging_e2e.py"
        
        try:
            with open(e2e_test_file, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"E2E test file not found: {e2e_test_file}")
        
        # Look for hardcoded staging URLs
        hardcoded_patterns = [
            r'https://netra-staging-backend\.run\.app',
            r'https://netra-staging-auth\.run\.app',
            r'wss://netra-staging-backend\.run\.app',
            r'"https://netra-staging-[^"]+\.run\.app[^"]*"'
        ]
        
        found_hardcoded = []
        for pattern in hardcoded_patterns:
            matches = re.findall(pattern, content)
            if matches:
                # Find line numbers for better debugging
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        found_hardcoded.append(f"Line {i}: {line.strip()}")
        
        # THIS ASSERTION SHOULD FAIL INITIALLY
        assert len(found_hardcoded) == 0, (
            f"Found hardcoded staging URLs in {e2e_test_file}:\n" + 
            "\n".join(found_hardcoded) + 
            "\n\nThese should use URLConstants.STAGING_*_URL instead"
        )
    
    def test_staging_e2e_test_uses_url_constants(self):
        """
        Test that staging E2E tests properly import and use URLConstants.
        
        THIS TEST SHOULD FAIL INITIALLY - demonstrating missing URLConstants usage.
        """
        
        e2e_test_file = "/Users/anthony/Desktop/netra-apex/tests/e2e/test_basic_triage_response_staging_e2e.py"
        
        try:
            with open(e2e_test_file, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"E2E test file not found: {e2e_test_file}")
        
        # Check for URLConstants import
        url_constants_import_patterns = [
            r'from netra_backend\.app\.core\.network_constants import.*URLConstants',
            r'from.*network_constants.*import.*URLConstants',
            r'import.*URLConstants'
        ]
        
        has_url_constants_import = any(
            re.search(pattern, content) for pattern in url_constants_import_patterns
        )
        
        # THIS ASSERTION SHOULD FAIL INITIALLY
        assert has_url_constants_import, (
            f"E2E test file {e2e_test_file} should import URLConstants from network_constants"
        )
        
        # Check for URLConstants usage in StagingEnvironmentConfig
        url_constants_usage_patterns = [
            r'URLConstants\.STAGING_BACKEND_URL',
            r'URLConstants\.STAGING_AUTH_URL',
            r'URLConstants\.STAGING_WEBSOCKET_URL'
        ]
        
        found_usage = []
        for pattern in url_constants_usage_patterns:
            if re.search(pattern, content):
                found_usage.append(pattern)
        
        # THIS ASSERTION SHOULD FAIL INITIALLY
        assert len(found_usage) >= 3, (
            f"E2E test file should use URLConstants for staging URLs. "
            f"Found usage of: {found_usage}, expected at least 3 staging URL constants"
        )
    
    def test_staging_environment_config_default_values(self):
        """
        Test that StagingEnvironmentConfig uses correct default values.
        
        THIS TEST SHOULD FAIL INITIALLY - demonstrating current hardcoded defaults.
        """
        
        e2e_test_file = "/Users/anthony/Desktop/netra-apex/tests/e2e/test_basic_triage_response_staging_e2e.py"
        
        try:
            with open(e2e_test_file, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"E2E test file not found: {e2e_test_file}")
        
        # Find the StagingEnvironmentConfig instantiation
        # Use a more robust approach to find the complete config block
        start_pattern = r'self\.staging_config\s*=\s*StagingEnvironmentConfig\('
        start_match = re.search(start_pattern, content)
        
        if not start_match:
            pytest.fail("Could not find StagingEnvironmentConfig instantiation in E2E test")
        
        # Find the matching closing parenthesis for the constructor
        start_pos = start_match.start()
        paren_count = 0
        current_pos = start_match.end() - 1  # Start at the opening parenthesis
        
        for i, char in enumerate(content[current_pos:], current_pos):
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count == 0:
                    end_pos = i + 1
                    break
        else:
            pytest.fail("Could not find matching closing parenthesis for StagingEnvironmentConfig")
        
        config_params = content[start_pos:end_pos]
        
        # Check that it's not using hardcoded run.app URLs
        hardcoded_run_app_pattern = r'https://[^"]*\.run\.app[^"]*'
        hardcoded_matches = re.findall(hardcoded_run_app_pattern, config_params)
        
        # THIS ASSERTION SHOULD FAIL INITIALLY
        assert len(hardcoded_matches) == 0, (
            f"StagingEnvironmentConfig uses hardcoded .run.app URLs: {hardcoded_matches}. "
            f"Should use URLConstants.STAGING_*_URL instead"
        )
        
        # Check that it IS using URLConstants
        url_constants_in_config = re.findall(r'URLConstants\.\w+', config_params)
        
        # THIS ASSERTION SHOULD FAIL INITIALLY
        assert len(url_constants_in_config) >= 3, (
            f"StagingEnvironmentConfig should use URLConstants for staging URLs. "
            f"Found: {url_constants_in_config}, expected at least 3 URLConstants references"
        )
    
    def test_staging_url_consistency_across_constants(self):
        """Test that staging URLs in constants are consistent and follow patterns."""
        
        # All staging URLs should use the same domain pattern
        staging_urls = [
            URLConstants.STAGING_BACKEND_URL,
            URLConstants.STAGING_AUTH_URL, 
            URLConstants.STAGING_FRONTEND_URL
        ]
        
        for url in staging_urls:
            # Should use staging.netrasystems.ai domain
            assert "staging.netrasystems.ai" in url, (
                f"Staging URL should use staging.netrasystems.ai domain: {url}"
            )
            
            # Should use HTTPS
            assert url.startswith("https://"), (
                f"Staging URL should use HTTPS: {url}"
            )
            
            # Should not use .run.app (legacy Cloud Run URLs)
            assert ".run.app" not in url, (
                f"Staging URL should not use .run.app domain: {url}"
            )
        
        # WebSocket URL should be WSS and include /ws path
        ws_url = URLConstants.STAGING_WEBSOCKET_URL
        assert ws_url.startswith("wss://"), (
            f"Staging WebSocket URL should use WSS: {ws_url}"
        )
        assert ws_url.endswith("/ws"), (
            f"Staging WebSocket URL should end with /ws path: {ws_url}"
        )
    
    def test_environment_url_resolution_staging(self):
        """Test that environment URL resolution works correctly for staging."""
        
        from netra_backend.app.core.network_constants import NetworkEnvironmentHelper
        
        # Mock staging environment
        with self.mock_environment_variables({'ENVIRONMENT': 'staging'}):
            service_urls = NetworkEnvironmentHelper.get_service_urls_for_environment()
            
            # Should resolve to staging URLs from constants
            assert service_urls['backend'] == URLConstants.STAGING_BACKEND_URL, (
                f"Staging backend URL should resolve to constant: "
                f"got {service_urls['backend']}, expected {URLConstants.STAGING_BACKEND_URL}"
            )
            
            assert service_urls['frontend'] == URLConstants.STAGING_FRONTEND_URL, (
                f"Staging frontend URL should resolve to constant: "
                f"got {service_urls['frontend']}, expected {URLConstants.STAGING_FRONTEND_URL}"
            )
            
            assert service_urls['auth_service'] == URLConstants.STAGING_AUTH_URL, (
                f"Staging auth URL should resolve to constant: "
                f"got {service_urls['auth_service']}, expected {URLConstants.STAGING_AUTH_URL}"
            )
    
    def test_cors_origins_include_staging_urls(self):
        """Test that CORS origins properly include staging URLs."""
        
        cors_origins = URLConstants.get_cors_origins("staging")
        
        # Should include all staging URLs
        expected_staging_urls = [
            URLConstants.STAGING_FRONTEND_URL,
            URLConstants.STAGING_BACKEND_URL,
            URLConstants.STAGING_AUTH_URL
        ]
        
        for expected_url in expected_staging_urls:
            assert expected_url in cors_origins, (
                f"CORS origins should include staging URL: {expected_url}. "
                f"Got CORS origins: {cors_origins}"
            )
    
    def test_no_legacy_staging_constants_usage(self):
        """Test that legacy staging constants are not used in E2E tests."""
        
        e2e_test_file = "/Users/anthony/Desktop/netra-apex/tests/e2e/test_basic_triage_response_staging_e2e.py"
        
        try:
            with open(e2e_test_file, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"E2E test file not found: {e2e_test_file}")
        
        # Check that it's not using legacy STAGING_APP or STAGING_FRONTEND constants
        legacy_patterns = [
            r'URLConstants\.STAGING_APP',
            r'URLConstants\.STAGING_FRONTEND[^_]'  # Match STAGING_FRONTEND but not STAGING_FRONTEND_URL
        ]
        
        found_legacy = []
        for pattern in legacy_patterns:
            matches = re.findall(pattern, content)
            if matches:
                found_legacy.extend(matches)
        
        assert len(found_legacy) == 0, (
            f"E2E test should not use legacy staging constants: {found_legacy}. "
            f"Use STAGING_*_URL constants instead"
        )


class TestStagingUrlFixValidation(SSotBaseTestCase):
    """
    Test suite to validate the fix for staging URL configuration.
    
    These tests verify that after the fix is applied, staging URLs
    are properly centralized and configurable.
    """
    
    def test_staging_urls_are_load_balancer_endpoints(self):
        """Test that staging URLs point to load balancer endpoints, not direct Cloud Run."""
        
        # These should be load balancer endpoints, not direct Cloud Run URLs
        load_balancer_patterns = [
            (URLConstants.STAGING_BACKEND_URL, "api.staging.netrasystems.ai"),
            (URLConstants.STAGING_AUTH_URL, "auth.staging.netrasystems.ai"),
            (URLConstants.STAGING_FRONTEND_URL, "app.staging.netrasystems.ai")
        ]
        
        for url, expected_domain in load_balancer_patterns:
            assert expected_domain in url, (
                f"Staging URL should use load balancer domain {expected_domain}: {url}"
            )
            
            # Should NOT be direct Cloud Run URLs
            assert "run.app" not in url, (
                f"Staging URL should not be direct Cloud Run URL: {url}"
            )
    
    def test_staging_configuration_environment_variable_override(self):
        """Test that staging URLs can be overridden via environment variables."""
        
        from netra_backend.app.core.network_constants import NetworkEnvironmentHelper
        
        # Test with custom staging URLs via environment variables
        custom_backend_url = "https://custom-staging-backend.example.com"
        custom_auth_url = "https://custom-staging-auth.example.com" 
        custom_frontend_url = "https://custom-staging-frontend.example.com"
        
        with self.mock_environment_variables({
            'ENVIRONMENT': 'staging',
            'BACKEND_SERVICE_URL': custom_backend_url,
            'AUTH_SERVICE_URL': custom_auth_url,
            'FRONTEND_URL': custom_frontend_url
        }):
            service_urls = NetworkEnvironmentHelper.get_service_urls_for_environment()
            
            # Should use environment variable overrides
            assert service_urls['backend'] == custom_backend_url, (
                f"Should use environment variable override for backend URL"
            )
            assert service_urls['auth_service'] == custom_auth_url, (
                f"Should use environment variable override for auth URL"
            )
            assert service_urls['frontend'] == custom_frontend_url, (
                f"Should use environment variable override for frontend URL"
            )
    
    def test_staging_url_constants_documentation(self):
        """Test that staging URL constants have proper documentation."""
        
        # Read the network_constants.py file to check documentation
        network_constants_file = "/Users/anthony/Desktop/netra-apex/netra_backend/app/core/network_constants.py"
        
        try:
            with open(network_constants_file, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"Network constants file not found: {network_constants_file}")
        
        # Should have comments explaining the staging URLs
        staging_url_section = re.search(
            r'# GCP Staging Service URLs.*?STAGING_WEBSOCKET_URL', 
            content, 
            re.DOTALL
        )
        
        assert staging_url_section is not None, (
            "network_constants.py should have documented staging URL section"
        )
        
        # Should mention load balancer endpoints
        assert "load balancer" in staging_url_section.group(0).lower(), (
            "Staging URL documentation should mention load balancer endpoints"
        )


if __name__ == '__main__':
    # Run the staging URL configuration tests
    pytest.main([__file__, '-v', '--tb=long'])