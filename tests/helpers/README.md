# Test Helpers - Canonical Test Utilities

This directory contains the **Single Source of Truth (SSOT)** for test utilities that should be used across all tests to maintain consistency and eliminate code duplication.

## 🎯 Purpose

Following CLAUDE.md principles, this package eliminates test code duplication by providing canonical helpers that all tests should use instead of implementing authentication logic directly.

## 📁 Files

### `auth_test_utils.py`
**THE canonical test authentication helper** - Use this for all JWT token creation in tests.

### `example_usage_test.py`
Examples showing proper usage patterns. **Delete this file after reviewing the patterns.**

## 🔑 TestAuthHelper - The Canonical Auth Helper

### When to Use TestAuthHelper

✅ **USE TestAuthHelper for:**
- Integration tests that need real JWT tokens
- E2E tests that call actual API endpoints  
- Tests that need tokens with specific permissions
- Tests that interact with WebSocket connections
- Any test that needs to verify token structure

### When NOT to Use TestAuthHelper

❌ **DON'T USE TestAuthHelper for:**
- Pure unit tests that can use mock tokens
- Tests of internal logic that doesn't validate tokens
- Security tests that need malformed/tampered tokens (use `JWTTestHelper` directly)

## 📖 Usage Patterns

### Basic Usage

```python
from tests.helpers.auth_test_utils import TestAuthHelper

# Create helper
auth_helper = TestAuthHelper()

# Most common usage - standard test token
token = auth_helper.create_test_token("user123")

# Use in HTTP requests
headers = auth_helper.get_auth_headers(token)
response = client.get("/api/endpoint", headers=headers)
```

### Specific Permissions

```python
# Token with specific permissions
token = auth_helper.create_test_token_with_permissions(
    "user123",
    ["read", "write", "admin"],
    tier="enterprise"
)
```

### Convenience Methods

```python
# Pre-configured tokens for common scenarios
admin_token = auth_helper.create_admin_test_token()
readonly_token = auth_helper.create_readonly_test_token("user123") 
expired_token = auth_helper.create_expired_test_token("user123")
```

### Environment-Specific

```python
# Test environment (default)
test_helper = TestAuthHelper(environment="test")

# Dev environment  
dev_helper = TestAuthHelper(environment="dev")
```

### Module-Level Convenience Functions

```python
from tests.helpers.auth_test_utils import create_standard_test_token, create_admin_token

# Quick token creation
token = create_standard_test_token("user123")
admin_token = create_admin_token("admin_user")
```

## 🔄 Migration Guide

### From Old Patterns ❌

```python
# DON'T DO THIS ANYMORE - Old approach
from tests.e2e.jwt_token_helpers import JWTTestHelper
jwt_helper = JWTTestHelper()
token = jwt_helper.create_access_token("user123", "user123@test.com")
```

### To New Canonical Pattern ✅

```python
# DO THIS - New canonical approach  
from tests.helpers.auth_test_utils import TestAuthHelper
auth_helper = TestAuthHelper()
token = auth_helper.create_test_token("user123")
```

## 📊 Comparison with Existing Helpers

| Helper | Use Case | Complexity | Token Type |
|--------|----------|------------|------------|
| `TestAuthHelper` | **Integration/E2E tests** | Simple | Real JWT |
| `test_framework.fixtures.auth` | Legacy, mixed use | Complex | Mock + Real |
| `tests.e2e.jwt_token_helpers` | Direct JWT operations | Complex | Real JWT |

### Recommendation

- **Use `TestAuthHelper`** for 90% of test scenarios
- **Use `JWTTestHelper`** directly only for security testing or special JWT operations
- **Avoid** `test_framework.fixtures.auth` for new tests (legacy support only)

## 🧪 Testing the Helper

To verify the helper works correctly:

```bash
# Simple verification
cd /path/to/netra-core-generation-1
python -c "
from tests.helpers.auth_test_utils import TestAuthHelper
helper = TestAuthHelper()
token = helper.create_test_token('test_user')
print(f'Token created: {len(token)} chars')
print(f'Valid structure: {helper.validate_token_structure(token)}')
"
```

## 🎯 Benefits

1. **Single Source of Truth**: One place for token creation logic
2. **Consistency**: All tests use the same token format
3. **Simplicity**: Clean, focused API for common use cases  
4. **Maintainability**: Changes to token logic only need updates in one place
5. **Developer Experience**: Easy to use, well-documented patterns

## 🚀 Next Steps

1. Review the example patterns in `example_usage_test.py`
2. Start using `TestAuthHelper` in new tests
3. Gradually migrate existing tests to use the canonical helper
4. Delete `example_usage_test.py` after understanding the patterns

---

**Remember**: This helper follows SSOT principles from CLAUDE.md. Always prefer using this canonical helper over implementing JWT logic directly in tests.