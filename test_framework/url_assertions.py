"""
URL Assertion Utilities for Testing

Provides flexible URL assertion helpers that can handle both 
static and dynamic port configurations.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Improve test reliability with dynamic ports
- Value Impact: Reduces test flakiness from port conflicts
- Strategic Impact: Enables parallel test execution

SSOT Integration:
- Works with test_framework.docker_port_discovery for dynamic ports
- Compatible with shared.port_discovery for service port resolution
- Follows NETRA architecture patterns for test utilities
"""

from typing import Optional, Union, Dict
from urllib.parse import urlparse
import re
import logging

# Integration with port discovery systems
try:
    from test_framework.docker_port_discovery import DockerPortDiscovery
    DOCKER_DISCOVERY_AVAILABLE = True
except ImportError:
    DOCKER_DISCOVERY_AVAILABLE = False

try:
    from shared.port_discovery import PortDiscovery
    SHARED_DISCOVERY_AVAILABLE = True
except ImportError:
    SHARED_DISCOVERY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Public API exports
__all__ = [
    # Core assertion functions
    'assert_base_url_matches',
    'assert_url_pattern',
    'assert_url_startswith',
    
    # Environment-specific assertions
    'assert_is_localhost_url',
    'assert_is_staging_url',
    'assert_is_production_url',
    'assert_no_localhost_in_url',
    
    # Service-aware assertions
    'assert_service_url_valid',
    'get_dynamic_service_url',
    
    # URL manipulation utilities
    'extract_base_url',
    'extract_port',
    'build_url_with_port',
    
    # Context manager
    'URLAssertion',
]


def assert_base_url_matches(actual: str, expected_base: str, 
                           ignore_port: bool = False,
                           message: Optional[str] = None) -> None:
    """
    Assert that the base URL matches, optionally ignoring port.
    
    Args:
        actual: The actual URL to test
        expected_base: The expected base URL (may include port)
        ignore_port: If True, only compare scheme and hostname
        message: Optional custom assertion message
    
    Raises:
        AssertionError: If URLs don't match according to criteria
    """
    actual_parsed = urlparse(actual)
    expected_parsed = urlparse(expected_base)
    
    # Compare scheme
    assert actual_parsed.scheme == expected_parsed.scheme, \
        f"{message or 'URL scheme mismatch'}: {actual_parsed.scheme} != {expected_parsed.scheme}"
    
    # Compare hostname
    assert actual_parsed.hostname == expected_parsed.hostname, \
        f"{message or 'URL hostname mismatch'}: {actual_parsed.hostname} != {expected_parsed.hostname}"
    
    # Compare port if not ignoring
    if not ignore_port:
        assert actual_parsed.port == expected_parsed.port, \
            f"{message or 'URL port mismatch'}: {actual_parsed.port} != {expected_parsed.port}"


def assert_url_pattern(actual: str, pattern: str,
                       message: Optional[str] = None) -> None:
    """
    Assert that URL matches a regex pattern.
    
    Args:
        actual: The actual URL to test
        pattern: Regex pattern to match against
        message: Optional custom assertion message
    
    Raises:
        AssertionError: If URL doesn't match pattern
    """
    assert re.match(pattern, actual), \
        f"{message or 'URL pattern mismatch'}: {actual} does not match {pattern}"


def assert_url_startswith(actual: str, prefix: str,
                         message: Optional[str] = None) -> None:
    """
    Assert that URL starts with given prefix.
    
    Args:
        actual: The actual URL to test
        prefix: URL prefix to check
        message: Optional custom assertion message
    
    Raises:
        AssertionError: If URL doesn't start with prefix
    """
    assert actual.startswith(prefix), \
        f"{message or 'URL prefix mismatch'}: {actual} does not start with {prefix}"


def extract_base_url(url: str) -> str:
    """
    Extract base URL without port.
    
    Args:
        url: Full URL with or without port
        
    Returns:
        Base URL in format scheme://hostname
    """
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.hostname}"


def extract_port(url: str) -> Optional[int]:
    """
    Extract port from URL.
    
    Args:
        url: URL to extract port from
        
    Returns:
        Port number or None if not specified
    """
    parsed = urlparse(url)
    return parsed.port


def build_url_with_port(base_url: str, port: int) -> str:
    """
    Build URL with specific port.
    
    Args:
        base_url: Base URL without port
        port: Port number to add
        
    Returns:
        Complete URL with port
    """
    parsed = urlparse(base_url)
    # Handle default ports
    if (parsed.scheme == 'http' and port == 80) or \
       (parsed.scheme == 'https' and port == 443):
        return base_url
    
    # Build URL with explicit port
    return f"{parsed.scheme}://{parsed.hostname}:{port}"


class URLAssertion:
    """
    Context manager for flexible URL assertions in tests.
    """
    
    def __init__(self, ignore_port: bool = False):
        """
        Initialize URL assertion context.
        
        Args:
            ignore_port: If True, ignore port differences in assertions
        """
        self.ignore_port = ignore_port
    
    def assert_equal(self, actual: str, expected: str) -> None:
        """
        Assert URLs are equal according to context settings.
        
        Args:
            actual: Actual URL
            expected: Expected URL
        """
        if self.ignore_port:
            assert_base_url_matches(actual, expected, ignore_port=True)
        else:
            assert actual == expected
    
    def assert_matches_environment(self, url: str, env: str) -> None:
        """
        Assert URL matches expected pattern for environment.
        
        Args:
            url: URL to test
            env: Environment name (development, test, staging, production)
        """
        patterns = {
            'development': r'http://localhost(:\d+)?',
            'test': r'http://(localhost|127\.0\.0\.1)(:\d+)?',
            'staging': r'https://.*\.staging\.netrasystems\.ai',
            'production': r'https://.*\.netrasystems\.ai'
        }
        
        pattern = patterns.get(env)
        if pattern:
            assert_url_pattern(url, pattern, 
                             f"URL doesn't match {env} environment pattern")


# Convenience functions for common assertions
def assert_is_localhost_url(url: str) -> None:
    """Assert URL is a localhost URL."""
    parsed = urlparse(url)
    assert parsed.hostname in ['localhost', '127.0.0.1'], \
        f"URL {url} is not a localhost URL"


def assert_is_staging_url(url: str) -> None:
    """Assert URL is a staging URL."""
    assert 'staging.netrasystems.ai' in url, \
        f"URL {url} is not a staging URL"


def assert_is_production_url(url: str) -> None:
    """Assert URL is a production URL."""
    assert 'netrasystems.ai' in url and 'staging' not in url, \
        f"URL {url} is not a production URL"


def assert_no_localhost_in_url(url: str) -> None:
    """Assert URL doesn't contain localhost references."""
    assert 'localhost' not in url.lower(), \
        f"URL {url} contains localhost"
    assert '127.0.0.1' not in url, \
        f"URL {url} contains 127.0.0.1"


def get_dynamic_service_url(service: str, use_docker: bool = True) -> Optional[str]:
    """
    Get dynamically discovered URL for a service.
    
    Args:
        service: Service name (backend, auth, frontend, etc.)
        use_docker: Use Docker port discovery if available
        
    Returns:
        Service URL with discovered port, or None if not available
    """
    # Try Docker discovery first if requested
    if use_docker and DOCKER_DISCOVERY_AVAILABLE:
        try:
            discovery = DockerPortDiscovery()
            ports = discovery.discover_all_ports()
            if service in ports:
                port_info = ports[service]
                if port_info and hasattr(port_info, 'external_port'):
                    return f"http://localhost:{port_info.external_port}"
        except Exception as e:
            logger.debug(f"Docker discovery failed for {service}: {e}")
    
    # Fall back to shared port discovery
    if SHARED_DISCOVERY_AVAILABLE:
        try:
            port = PortDiscovery.get_port(service)
            if port:
                return f"http://localhost:{port}"
        except Exception as e:
            logger.debug(f"Shared port discovery failed for {service}: {e}")
    
    return None


def assert_service_url_valid(service: str, actual_url: str,
                            allow_dynamic: bool = True) -> None:
    """
    Assert that a service URL is valid, considering dynamic ports.
    
    Args:
        service: Service name (backend, auth, etc.)
        actual_url: The actual URL to validate
        allow_dynamic: Allow dynamic port discovery
    
    Raises:
        AssertionError: If URL is invalid for the service
    """
    if allow_dynamic:
        # Get dynamically discovered URL
        dynamic_url = get_dynamic_service_url(service)
        if dynamic_url:
            # Check if URL matches dynamic discovery
            assert_base_url_matches(actual_url, dynamic_url, ignore_port=False)
            return
    
    # Fall back to checking URL structure
    assert_is_localhost_url(actual_url)
    
    # Verify it has a port
    parsed = urlparse(actual_url)
    assert parsed.port is not None, \
        f"Service {service} URL should include a port: {actual_url}"