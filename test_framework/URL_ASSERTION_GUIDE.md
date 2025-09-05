# URL Assertion Guide for Dynamic Ports

## Overview

When testing configurations and services that may use dynamic ports, tests should be flexible about port assertions unless they are specifically testing port configuration.

## When to Use Flexible URL Assertions

### ✅ Use Flexible Assertions When:
- Testing configuration structure/format (not specific values)
- Testing with Docker dynamic port allocation
- Testing service discovery (ports may vary)
- Testing in CI/CD with parallel test runs

### ❌ Use Exact Assertions When:
- Testing specific environment configurations (dev/staging/prod)
- Testing port-specific functionality
- Testing that a client stores the exact URL passed to it
- Testing URL generation for specific environments

## Usage Examples

```python
from test_framework.url_assertions import (
    assert_base_url_matches,
    assert_is_localhost_url,
    assert_is_staging_url,
    assert_no_localhost_in_url,
    URLAssertion
)

# Example 1: Assert base URL without port
def test_config_returns_valid_url():
    config = get_config()
    # Don't care about exact port, just that it's localhost
    assert_is_localhost_url(config.api_url)
    assert_base_url_matches(config.api_url, "http://localhost", ignore_port=True)

# Example 2: Assert exact URL including port
def test_development_config_uses_standard_ports():
    config = get_dev_config()
    # In dev, we expect specific ports
    assert config.api_url == "http://localhost:8000"
    assert config.auth_url == "http://localhost:8081"

# Example 3: Assert environment-appropriate URLs
def test_staging_config_no_localhost():
    config = get_staging_config()
    assert_is_staging_url(config.api_url)
    assert_no_localhost_in_url(config.api_url)

# Example 4: Use context manager for multiple assertions
def test_multiple_urls():
    config = get_config()
    with URLAssertion(ignore_port=True) as url_assert:
        url_assert.assert_equal(config.api_url, "http://localhost:8000")
        url_assert.assert_equal(config.auth_url, "http://localhost:8081")
        # Will only check scheme and hostname, not ports
```

## Common Patterns

### Testing Config Structure (Port-Agnostic)
```python
def test_config_structure():
    config = get_config()
    # Check URL is present and valid format
    assert config.api_url.startswith("http")
    # Check it's a localhost URL without asserting specific port
    assert_is_localhost_url(config.api_url)
```

### Testing Environment-Specific Config (Port-Specific)
```python
def test_production_urls():
    with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
        config = get_config()
        # Production URLs should be exact
        assert config.api_url == "https://api.netrasystems.ai"
        assert config.auth_url == "https://auth.netrasystems.ai"
```

### Testing with Dynamic Docker Ports
```python
def test_with_docker_dynamic_ports():
    # Get actual port from Docker
    port_discovery = DockerPortDiscovery()
    backend_port = port_discovery.get_port("backend")
    
    config = get_config()
    # Assert base URL but allow dynamic port
    expected_base = "http://localhost"
    actual_url = f"http://localhost:{backend_port}"
    assert_base_url_matches(config.api_url, expected_base, ignore_port=True)
    # Or check exact URL with discovered port
    assert config.api_url == actual_url
```

## Migration Guide

When updating existing tests:

1. **Identify the test's purpose**: Is it testing configuration values or structure?
2. **Choose appropriate assertion**: Exact match vs flexible match
3. **Document intent**: Add comments explaining why flexible/exact assertion is used

### Before (Brittle):
```python
def test_config():
    config = get_config()
    assert config.api_url == "http://localhost:8000"  # Fails with dynamic ports
```

### After (Flexible):
```python
def test_config():
    config = get_config()
    # Testing config structure, not specific port values
    assert_is_localhost_url(config.api_url)
    # Or if you need to check the base URL
    assert_base_url_matches(config.api_url, "http://localhost", ignore_port=True)
```

## Best Practices

1. **Be explicit about test intent**: Use comments to explain why you're using flexible vs exact assertions
2. **Default to exact for environment tests**: When testing dev/staging/prod configs, use exact URLs
3. **Use flexible for structure tests**: When testing that config has correct structure/format
4. **Consider parallel execution**: Use flexible assertions when tests might run in parallel with dynamic ports
5. **Test both structure and values separately**: Have separate tests for config structure vs specific values