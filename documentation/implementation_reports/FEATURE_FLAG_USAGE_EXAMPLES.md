# Feature Flag Testing Decorators - Usage Examples

This document demonstrates all available feature flag testing decorators and their usage patterns.

## Available Decorators

### 1. @feature_flag("feature_name")
Skip test if feature is not enabled.

```python
@feature_flag("roi_calculator")
def test_roi_calculation():
    # Test skipped if roi_calculator not enabled
    assert calculate_roi(1000, 0.2) == 200
```

### 2. @tdd_test("feature_name", expected_to_fail=True)
TDD workflow - mark tests as expected to fail during development.

```python
@tdd_test("new_auth_system", expected_to_fail=True)
def test_oauth_flow():
    # Written before implementation, expected to fail
    user = oauth_login("user@example.com")
    assert user.is_authenticated
```

### 3. @requires_feature("feat_a", "feat_b")
Require multiple features to be enabled.

```python
@requires_feature("auth_integration", "websocket_streaming")
def test_authenticated_websocket():
    # Requires both features enabled
    pass
```

### 4. @experimental_test("description")
Only run when ENABLE_EXPERIMENTAL_TESTS=true.

```python
@experimental_test("Testing new ML algorithm")
def test_ml_rate_limiter():
    # Only runs when opted into experimental tests
    limiter = MLRateLimiter()
    assert limiter.analyze_pattern([1, 2, 4]) is not None
```

### 5. @performance_test(threshold_ms=100)
Performance tests with automatic threshold checking.

```python
@performance_test(threshold_ms=100)
def test_api_response_time():
    # Must complete within 100ms
    response = call_api()
    assert response.status_code == 200
```

### 6. @integration_only()
Only run during integration test levels.

```python
@integration_only()
def test_database_transaction():
    # Only runs when TEST_LEVEL=integration
    pass
```

### 7. @requires_env("VAR1", "VAR2")
Skip if required environment variables not set.

```python
@requires_env("GEMINI_API_KEY", "OPENAI_API_KEY")
def test_multi_llm_orchestration():
    # Requires both API keys to be set
    pass
```

### 8. @flaky_test(max_retries=3, reason="Network dependency")
Retry tests on failure.

```python
@flaky_test(max_retries=3, reason="External API dependency")
def test_github_api_integration():
    # Will retry up to 3 times if it fails
    response = call_github_api()
    assert response.status_code == 200
```

## Environment Overrides

Override feature status using environment variables:

```bash
# Enable a disabled feature for testing
export TEST_FEATURE_ENTERPRISE_SSO=enabled

# Disable an enabled feature
export TEST_FEATURE_ROI_CALCULATOR=disabled

# Enable experimental tests
export ENABLE_EXPERIMENTAL_TESTS=true

# Enable performance tests in fast mode
export ENABLE_PERFORMANCE_TESTS=true
```

## Combining Decorators

Decorators can be combined for complex requirements:

```python
@integration_only()
@requires_feature("auth_integration", "websocket_streaming")
@performance_test(threshold_ms=500)
@requires_env("DATABASE_URL")
def test_complex_integration():
    """
    This test:
    - Only runs during integration testing
    - Requires auth and websocket features
    - Must complete within 500ms
    - Needs DATABASE_URL environment variable
    """
    pass
```

## Feature Configuration

Features are configured in `test_feature_flags.json`:

```json
{
  "features": {
    "feature_name": {
      "status": "enabled|in_development|disabled|experimental",
      "description": "Feature description",
      "owner": "team-name",
      "target_release": "v1.x.x",
      "dependencies": ["other_feature"],
      "metadata": { "jira_ticket": "TICKET-123" }
    }
  }
}
```

## Usage in Test Runner

Feature flags integrate seamlessly with the unified test runner:

```bash
# Normal test run - respects all feature flags
python unified_test_runner.py --level integration

# Enable experimental tests for this run
ENABLE_EXPERIMENTAL_TESTS=true python unified_test_runner.py

# Override specific feature status
TEST_FEATURE_NEW_FEATURE=enabled python unified_test_runner.py
```

The test runner will display feature flag summaries showing which features are enabled, disabled, in development, or experimental.