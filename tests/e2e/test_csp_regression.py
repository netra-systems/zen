"""
CSP (Content Security Policy) Regression Tests

Tests to prevent regression of CSP configuration issues that would break:
1. Web Worker creation from blob URLs
2. External API connections to feature flags and DNS services

This test ensures the CSP fixes from CSP_WORKER_BLOB_ERROR_FIX_20250107.md remain in place.
"""

import pytest
import requests
from typing import Dict, List, Tuple
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestCSPRegression:
    """Test suite to prevent CSP configuration regressions."""
    
    @pytest.fixture
    def staging_url(self) -> str:
        """Get staging environment URL."""
        return "https://app.staging.netrasystems.ai"
    
    @pytest.fixture
    def local_url(self) -> str:
        """Get local development URL."""
        return "http://localhost:3000"
    
    def get_csp_header(self, url: str) -> str:
        """Fetch CSP header from the given URL."""
        try:
            response = requests.head(url, timeout=10)
            return response.headers.get('content-security-policy', '')
        except requests.RequestException:
            return ''
    
    def parse_csp_directives(self, csp_header: str) -> Dict[str, List[str]]:
        """Parse CSP header into a dictionary of directives."""
        directives = {}
        if not csp_header:
            return directives
        
        parts = csp_header.split(';')
        for part in parts:
            part = part.strip()
            if ' ' in part:
                directive_name = part.split(' ')[0]
                directive_values = part.split(' ')[1:]
                directives[directive_name] = directive_values
        
        return directives
    
    @pytest.mark.staging
    def test_staging_csp_blob_support(self, staging_url):
        """Test that staging CSP allows blob: URLs for workers."""
        csp_header = self.get_csp_header(staging_url)
        assert csp_header, "CSP header must be present in staging"
        
        directives = self.parse_csp_directives(csp_header)
        
        # Check script-src includes blob:
        assert 'script-src' in directives, "script-src directive must be present"
        assert 'blob:' in directives['script-src'], \
            "script-src must include 'blob:' to support worker creation"
        
        # Check worker-src directive exists and includes blob:
        if 'worker-src' in directives:
            assert 'blob:' in directives['worker-src'], \
                "worker-src must include 'blob:' when present"
    
    @pytest.mark.staging
    def test_staging_csp_external_apis(self, staging_url):
        """Test that staging CSP allows required external API connections."""
        csp_header = self.get_csp_header(staging_url)
        assert csp_header, "CSP header must be present in staging"
        
        directives = self.parse_csp_directives(csp_header)
        
        # Check connect-src includes required external domains
        assert 'connect-src' in directives, "connect-src directive must be present"
        
        connect_src_values = ' '.join(directives['connect-src'])
        
        # Critical external services that must be allowed
        required_domains = [
            'https://featureassets.org',  # Feature flag service
            'https://cloudflare-dns.com',  # DNS service
            'https://*.staging.netrasystems.ai',  # Our own staging domain
            'wss://*.staging.netrasystems.ai',  # WebSocket connections
        ]
        
        for domain in required_domains:
            assert domain in connect_src_values or domain.replace('https://', '') in connect_src_values, \
                f"connect-src must include {domain}"
    
    @pytest.mark.staging
    def test_staging_csp_complete_configuration(self, staging_url):
        """Test that all critical CSP directives are properly configured."""
        csp_header = self.get_csp_header(staging_url)
        assert csp_header, "CSP header must be present"
        
        directives = self.parse_csp_directives(csp_header)
        
        # Verify all critical directives are present
        required_directives = [
            'default-src',
            'script-src',
            'style-src',
            'img-src',
            'connect-src',
            'font-src',
            'media-src',
            'frame-src'
        ]
        
        for directive in required_directives:
            assert directive in directives, f"{directive} must be present in CSP"
        
        # Verify blob: support in image sources
        assert 'blob:' in directives.get('img-src', []), \
            "img-src must include 'blob:' for image handling"
        
        # Verify data: URIs are allowed where needed
        assert 'data:' in directives.get('img-src', []), \
            "img-src must include 'data:' for inline images"
        assert 'data:' in directives.get('font-src', []), \
            "font-src must include 'data:' for inline fonts"
    
    @pytest.mark.skipif(
        not os.getenv('TEST_LOCAL_CSP', '').lower() == 'true',
        reason="Local CSP testing requires TEST_LOCAL_CSP=true and running local server"
    )
    def test_local_csp_configuration(self, local_url):
        """Test local development CSP configuration."""
        csp_header = self.get_csp_header(local_url)
        
        if not csp_header:
            pytest.skip("Local server not running or CSP not configured")
        
        directives = self.parse_csp_directives(csp_header)
        
        # Local should have similar blob: support
        if 'script-src' in directives:
            assert 'blob:' in directives['script-src'], \
                "Local script-src should include 'blob:' for development"
        
        # Local should allow localhost connections
        if 'connect-src' in directives:
            connect_src_values = ' '.join(directives['connect-src'])
            assert 'localhost' in connect_src_values or '127.0.0.1' in connect_src_values, \
                "Local connect-src should allow localhost connections"
    
    @pytest.mark.staging
    def test_csp_not_too_permissive(self, staging_url):
        """Test that CSP is not overly permissive (security check)."""
        csp_header = self.get_csp_header(staging_url)
        assert csp_header, "CSP header must be present"
        
        # Check for overly permissive patterns that should be avoided
        dangerous_patterns = [
            "'unsafe-eval'",  # Should not be in production/staging
            '*',  # Wildcard domain (except for subdomains like *.staging.netrasystems.ai)
            'http:',  # Non-HTTPS sources in staging
        ]
        
        for pattern in dangerous_patterns:
            if pattern == '*':
                # Allow subdomain wildcards but not bare wildcards
                assert not ' * ' in f' {csp_header} ', \
                    "CSP should not contain bare wildcard (*) sources"
            elif pattern == "'unsafe-eval'":
                # unsafe-eval should not be in staging
                assert pattern not in csp_header, \
                    f"Staging CSP should not contain {pattern} for security"
            elif pattern == 'http:':
                # Check for non-HTTPS sources (except ws:// for WebSockets)
                parts = csp_header.split()
                for part in parts:
                    if part.startswith('http:') and not part.startswith('http://localhost'):
                        pytest.fail(f"Staging CSP should not contain non-HTTPS source: {part}")


@pytest.mark.staging
class TestCSPFunctionalValidation:
    """Functional tests to validate CSP doesn't break actual functionality."""
    
    @pytest.mark.skip(reason="Requires browser automation setup")
    def test_worker_creation_in_browser(self):
        """Test that workers can actually be created in the browser.
        
        This would require Selenium or Playwright to:
        1. Load the staging site
        2. Execute JavaScript to create a blob: URL worker
        3. Verify no CSP violations in console
        """
        pass
    
    @pytest.mark.skip(reason="Requires browser automation setup")
    def test_external_api_calls_in_browser(self):
        """Test that external API calls work in the browser.
        
        This would require browser automation to:
        1. Load the staging site
        2. Monitor network requests to external services
        3. Verify no CSP violations for connect-src
        """
        pass


if __name__ == "__main__":
    # Run staging tests by default
    pytest.main([__file__, '-v', '-m', 'staging'])