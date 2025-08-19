# Testing with Feature Flags - TDD Best Practices

## Overview

Our testing infrastructure supports feature flags to enable Test-Driven Development (TDD) while maintaining 100% pass rates for production-ready features. This allows you to:

1. Write tests before implementation (TDD)
2. Keep tests for in-development features without breaking CI/CD
3. Clearly track feature readiness
4. Maintain visibility of work in progress

## Quick Start

### 1. Basic Feature Flag Usage

```python
from test_framework.decorators import feature_flag

@feature_flag("new_payment_system")
def test_payment_processing():
    """This test will be skipped if 'new_payment_system' is not enabled."""
    # Your test code here
    assert process_payment(100) == "success"
```

### 2. TDD Workflow

```python
from test_framework.decorators import tdd_test

@tdd_test("user_profile_api", expected_to_fail=True)
def test_user_can_update_profile():
    """Test written before implementation - expected to fail initially."""
    response = client.put("/api/profile", json={"name": "John"})
    assert response.status_code == 200
    assert response.json()["name"] == "John"
```

## Feature Flag Configuration

Feature flags are configured in `test_feature_flags.json`:

```json
{
  "features": {
    "feature_name": {
      "status": "in_development",  // or "enabled", "disabled", "experimental"
      "description": "Feature description",
      "owner": "team-name",
      "target_release": "v1.2.0",
      "dependencies": ["other_feature"],
      "metadata": {
        "jira_ticket": "PROJ-123"
      }
    }
  }
}
```

### Feature Statuses

- **`enabled`**: Feature is complete, tests must pass
- **`in_development`**: Feature being developed, tests may fail (skipped in CI)
- **`disabled`**: Feature is disabled, tests are skipped
- **`experimental`**: Feature is experimental, tests run only when opted in

## Environment Variable Overrides

Override feature flags via environment variables:

```bash
# Enable a feature for testing
export TEST_FEATURE_NEW_PAYMENT_SYSTEM=enabled

# Disable a feature
export TEST_FEATURE_LEGACY_API=disabled

# Mark as in development
export TEST_FEATURE_USER_PROFILE=in_development
```

## Decorator Reference

### `@feature_flag(feature_name)`
Skip test if feature is not enabled.

```python
@feature_flag("advanced_search")
def test_search_with_filters():
    # Test for a feature that may not be ready
    pass
```

### `@tdd_test(feature_name, expected_to_fail=True)`
Mark test as TDD test that's expected to fail initially.

```python
@tdd_test("shopping_cart", expected_to_fail=True)
def test_add_item_to_cart():
    # Test written before implementation
    pass
```

### `@requires_feature(*features)`
Test requires multiple features to be enabled.

```python
@requires_feature("auth", "payments", "notifications")
def test_purchase_flow():
    # Test requiring multiple features
    pass
```

### `@experimental_test(reason)`
Test for experimental features.

```python
@experimental_test("Testing new ML model")
def test_ml_predictions():
    # Experimental test
    pass
```

### `@performance_test(threshold_ms)`
Performance-sensitive test with threshold.

```python
@performance_test(threshold_ms=100)
def test_api_response_time():
    # Test must complete within 100ms
    pass
```

### `@integration_only()` / `@unit_only()`
Control when tests run based on test level.

```python
@integration_only()
def test_database_transaction():
    # Only runs during integration testing
    pass

@unit_only()
def test_utility_function():
    # Only runs during unit testing
    pass
```

## TDD Best Practices

### 1. Write Tests First

```python
# Step 1: Write the test (will fail initially)
@tdd_test("user_settings")
def test_user_can_save_preferences():
    user = create_test_user()
    response = save_preferences(user.id, {"theme": "dark"})
    assert response.success
    assert get_preferences(user.id)["theme"] == "dark"
```

### 2. Mark Feature as In Development

```json
{
  "features": {
    "user_settings": {
      "status": "in_development",
      "description": "User preference management",
      "target_release": "v1.2.0"
    }
  }
}
```

### 3. Implement the Feature

Write your implementation code. Tests will still be skipped in CI.

### 4. Enable Feature When Ready

```json
{
  "features": {
    "user_settings": {
      "status": "enabled",  // Changed from "in_development"
      "description": "User preference management"
    }
  }
}
```

## Running Tests with Feature Flags

### Run All Tests (respecting feature flags)
```bash
python test_runner.py --level integration
```

### Run Tests for Specific Feature
```bash
# Enable feature temporarily
TEST_FEATURE_NEW_PAYMENT_SYSTEM=enabled python test_runner.py --level unit
```

### Run Experimental Tests
```bash
ENABLE_EXPERIMENTAL_TESTS=true python test_runner.py --level integration
```

### Show Feature Flag Status
```bash
python -c "from test_framework.feature_flags import get_feature_flag_manager; m = get_feature_flag_manager(); print(m.get_feature_summary())"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run Tests (Production Features Only)
  run: |
    python test_runner.py --level integration --no-coverage --fast-fail
  env:
    # Only enabled features will be tested
    CI: true

- name: Run Tests (Including In-Development)
  run: |
    # Force specific features for testing
    TEST_FEATURE_NEW_API=enabled python test_runner.py --level integration
```

## Managing Feature Flags

### Programmatic Management

```python
from test_framework.feature_flags import get_feature_flag_manager, FeatureFlag, FeatureStatus

manager = get_feature_flag_manager()

# Add new feature flag
manager.add_flag(FeatureFlag(
    name="new_feature",
    status=FeatureStatus.IN_DEVELOPMENT,
    description="New feature description",
    owner="team-name",
    target_release="v1.3.0"
))

# Enable a feature
manager.enable_feature("new_feature")

# Save changes
manager.save_flags()
```

### Command Line Management

```bash
# Check feature status
python -m test_framework.feature_flags status

# Enable a feature
python -m test_framework.feature_flags enable new_feature

# Disable a feature
python -m test_framework.feature_flags disable old_feature
```

## Migration Guide

### Converting Existing Tests

Before:
```python
def test_complex_feature():
    # Test that might fail if feature isn't ready
    result = complex_operation()
    assert result.status == "success"
```

After:
```python
@feature_flag("complex_feature")
def test_complex_feature():
    # Now safely skipped if feature isn't ready
    result = complex_operation()
    assert result.status == "success"
```

### Handling Flaky Tests

```python
@flaky_test(max_retries=3, reason="External API dependency")
@feature_flag("external_integration")
def test_external_api():
    # Test that might fail due to network issues
    response = call_external_api()
    assert response.ok
```

## Best Practices

1. **Use Descriptive Feature Names**: `user_profile_management` not `feature1`

2. **Document Dependencies**: List required features in dependencies

3. **Set Target Releases**: Track when features should be ready

4. **Clean Up Old Flags**: Remove flags for features that are permanently enabled

5. **Use Metadata**: Track JIRA tickets, owners, and dates

6. **Test Both Paths**: Ensure tests work when feature is both enabled and disabled

7. **Progressive Enhancement**: Start with `in_development`, move to `experimental`, then `enabled`

## Troubleshooting

### Tests Not Being Skipped

Check:
1. Feature flag configuration in `test_feature_flags.json`
2. Environment variable overrides
3. Decorator is properly imported and applied

### Feature Flag Not Found

Features default to enabled if not configured. Add explicit configuration:

```json
{
  "features": {
    "your_feature": {
      "status": "in_development"
    }
  }
}
```

### Environment Override Not Working

Environment variables must be uppercase with underscores:
- ✅ `TEST_FEATURE_MY_FEATURE=enabled`
- ❌ `test_feature_my-feature=enabled`

## Summary

Feature flags enable:
- ✅ TDD workflow without breaking CI/CD
- ✅ 100% pass rate for production features
- ✅ Clear visibility of work in progress
- ✅ Gradual feature rollout
- ✅ Easy feature toggling for testing

This system ensures we can maintain high code quality while supporting agile development practices.