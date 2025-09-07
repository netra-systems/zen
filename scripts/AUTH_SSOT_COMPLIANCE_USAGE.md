# Auth SSOT Compliance Check - Usage Guide

## Overview

The Auth SSOT Compliance Check script (`check_auth_ssot_compliance.py`) is an automated tool that detects violations of our auth service Single Source of Truth (SSOT) pattern. This prevents developers from accidentally reintroducing JWT operations into the backend service, which could cause the same authentication failures we previously fixed.

## Critical Context

**Why This Script Exists:**
- We removed JWT decoding from backend to enforce auth service SSOT
- This prevents JWT secret mismatches that caused $50K MRR loss from WebSocket failures
- Automated checks prevent human error from reintroducing violations
- Maintains clean service boundaries and multi-user isolation

## Usage

### Basic Usage

```bash
# Run full compliance check
python scripts/check_auth_ssot_compliance.py

# Exclude test files (recommended for CI/CD)
python scripts/check_auth_ssot_compliance.py --exclude-tests

# Verbose output with code snippets
python scripts/check_auth_ssot_compliance.py --verbose
```

### Exit Codes

- **0**: All checks pass, no violations found
- **1**: SSOT violations detected (blocks CI/CD)
- **2**: Script error or interrupted

## What It Detects

### 🚨 Critical Violations (Always Block CI/CD)

1. **JWT Library Imports**
   ```python
   import jwt                    # ❌ VIOLATION
   from jwt import decode        # ❌ VIOLATION
   ```
   **Fix**: Use auth service client instead

2. **JWT Operations**
   ```python
   jwt.decode(token, secret)     # ❌ VIOLATION
   jwt.encode(payload, secret)   # ❌ VIOLATION
   ```
   **Fix**: Use auth service `/validate` and `/token` endpoints

3. **Local Token Validation Methods**
   ```python
   def validate_token(token):    # ❌ VIOLATION
   def decode_token(token):      # ❌ VIOLATION
   def verify_jwt(token):        # ❌ VIOLATION
   ```
   **Fix**: Remove local validation, use auth service client

### ⚠️ Conditional Violations

4. **Authentication Fallbacks** (only flagged if not using unified JWT secret)
   ```python
   # These are OK if file uses shared.jwt_secret_manager
   fallback_validation()        # ⚠️  MAY BE VIOLATION
   legacy_auth()               # ⚠️  MAY BE VIOLATION
   ```

5. **WebSocket JWT Issues**
   ```python
   # WebSocket-specific fallback validation
   fallback_jwt_validation()    # ❌ VIOLATION
   legacy_jwt_auth()           # ❌ VIOLATION
   ```

## Allowed Files

These files are **explicitly allowed** to have JWT operations:

### Auth Service (SSOT)
- `auth_service/auth_core/core/jwt_handler.py`
- `auth_service/auth_core/core/jwt_cache.py`
- `auth_service/auth_core/core/token_validator.py`

### Infrastructure
- `shared/jwt_secret_manager.py` (JWT secret management only)
- `netra_backend/app/websocket_core/user_context_extractor.py` (uses unified JWT secret)

### Testing
- `test_framework/jwt_test_utils.py`
- `test_framework/fixtures/auth.py`
- `test_framework/ssot/e2e_auth_helper.py`
- `tests/e2e/jwt_token_helpers.py`
- `netra_backend/tests/integration/jwt_token_helpers.py`

## Exception Handling

If you need to add JWT operations to a file for a legitimate reason, use exception markers:

```python
# @auth_ssot_exception: Required for legacy integration during migration
import jwt

# @jwt_allowed: WebSocket requires JWT for real-time auth validation
payload = jwt.decode(token, secret, algorithms=['HS256'])
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Auth SSOT Compliance Check
on: [push, pull_request]
jobs:
  auth-compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Check Auth SSOT Compliance
        run: |
          python scripts/check_auth_ssot_compliance.py --exclude-tests
        shell: bash
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: auth-ssot-compliance
        name: Auth SSOT Compliance Check
        entry: python scripts/check_auth_ssot_compliance.py --exclude-tests
        language: system
        pass_filenames: false
        always_run: true
```

### Manual CI Integration

```bash
# In your CI script
python scripts/check_auth_ssot_compliance.py --exclude-tests
if [ $? -ne 0 ]; then
    echo "❌ Auth SSOT compliance check failed - blocking deployment"
    exit 1
fi
echo "✅ Auth SSOT compliance check passed"
```

## Sample Output

### Passing Check
```
================================================================================
AUTH SSOT COMPLIANCE CHECK RESULTS
================================================================================

Files Checked: 2394
Violations Found: 0
Warnings: 0
Allowed Exceptions: 0

[PASS] COMPLIANCE CHECK PASSED

All checks passed! The backend properly delegates JWT operations
to the auth service, maintaining clean SSOT architecture.
================================================================================

[PASS] Exiting with code 0 - no violations found
```

### Failing Check
```
================================================================================
AUTH SSOT COMPLIANCE CHECK RESULTS
================================================================================

Files Checked: 2394
Violations Found: 15
Warnings: 0
Allowed Exceptions: 0

[!] CRITICAL VIOLATIONS DETECTED (15)
============================================================

JWT_IMPORT (5 instances):
  File: netra_backend/app/middleware/custom_auth.py:17
     Issue: Direct JWT library import
     Fix: Use auth service client instead of direct JWT operations

JWT_DECODE (10 instances):
  File: netra_backend/app/middleware/custom_auth.py:45
     Issue: JWT token decoding
     Fix: Use auth service /validate endpoint instead

================================================================================
[FAIL] COMPLIANCE CHECK FAILED

VIOLATIONS DETECTED: The backend contains JWT operations that violate
the auth service SSOT pattern. These must be removed to prevent:
- JWT secret mismatch errors
- WebSocket authentication failures  
- Multi-user isolation issues
- Service boundary violations

BUSINESS IMPACT: These violations could cause $50K MRR loss
from WebSocket authentication failures and security issues.
================================================================================

[FAIL] Exiting with code 1 due to 15 violations
```

## Troubleshooting

### Common Issues

1. **"File not found" errors**
   - Ensure you're running from project root
   - Use `--project-root` flag if needed

2. **Too many violations on first run**
   - This is expected - the codebase currently has JWT operations
   - Use this as a baseline to track cleanup progress
   - Focus on high-risk violations first (JWT_DECODE, JWT_ENCODE)

3. **False positives in test files**
   - Use `--exclude-tests` flag
   - Or add exception markers to legitimate test JWT operations

4. **Legitimate JWT operations flagged**
   - Add the file to `allowed_jwt_files` list in script
   - Or use exception markers for specific lines

### Performance

- Script scans ~2400 files in ~5 seconds
- Safe for CI/CD pipelines
- Memory usage: <50MB

## Architecture Integration

This script enforces our core architectural principle:

```
┌─────────────────┐    ┌──────────────────┐
│   Frontend      │    │   Auth Service   │
│                 │───▶│   (JWT SSOT)     │
└─────────────────┘    └──────────────────┘
                                │
┌─────────────────┐             │
│   Backend       │◀────────────┘
│   (NO JWT OPS)  │   Auth Client Only
└─────────────────┘
```

**Key Points:**
- Auth Service = Single Source of Truth for JWT operations
- Backend = Uses auth service client, NO direct JWT operations
- WebSocket = Uses unified JWT secret manager (same as auth service)
- Tests = Can use JWT for test token creation only

## Business Impact

**Prevention Value:**
- 🛡️ Prevents $50K MRR loss from auth failures
- 🔒 Maintains security isolation between users
- ⚡ Prevents "error behind the error" JWT secret mismatches
- 🏗️ Enforces clean service architecture
- 🚀 Enables confident continuous deployment

**When It Blocks:**
This script should **block deployments** when violations are found, preventing:
- WebSocket 403 authentication failures
- JWT secret mismatch errors in staging/production
- Cross-user data leakage
- Service boundary violations
- Technical debt accumulation

Use this tool regularly and integrate into your CI/CD pipeline to maintain architectural compliance and prevent costly authentication regressions.