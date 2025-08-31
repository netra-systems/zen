# E2E Test Authentication for Staging Environment

## Overview

This document describes the E2E test authentication bypass mechanism for running automated tests against the staging environment without requiring OAuth authentication.

## Security Model

The E2E OAUTH SIMULATION is designed with multiple security layers:

1. **Environment Restriction**: Only works in staging environment, completely disabled in production
2. **Secure Bypass Key**: Requires a secret key stored in Google Secrets Manager
3. **Limited Permissions**: Test users have restricted permissions by default
4. **Audit Logging**: All E2E auth attempts are logged for security monitoring
5. **Token Expiry**: Test tokens have standard 15-minute expiry

## Setup

### 1. Configure the Bypass Key in Google Secrets Manager

Create a secret named `e2e-bypass-key` in Google Secrets Manager for the staging project:

```bash
# Generate a secure random key
openssl rand -hex 32

# Store in Google Secrets Manager
echo -n "your-generated-key" | gcloud secrets create e2e-bypass-key \
    --project=netra-staging \
    --data-file=-
```

### 2. Grant Access to the Secret

Ensure the staging service accounts have access to read the secret:

```bash
gcloud secrets add-iam-policy-binding e2e-bypass-key \
    --project=netra-staging \
    --role=roles/secretmanager.secretAccessor \
    --member=serviceAccount:staging-auth-service@netra-staging.iam.gserviceaccount.com
```

### 3. Set Environment Variable for Tests

Export the bypass key in your test environment:

```bash
export E2E_BYPASS_KEY="your-generated-key"
export ENVIRONMENT=staging
export STAGING_AUTH_URL=https://api.staging.netrasystems.ai
```

## Usage

### Python E2E Tests

```python
from tests.e2e.staging_auth_bypass import StagingAuthHelper

# Initialize auth helper
auth = StagingAuthHelper()

# Get a test token
token = await auth.get_test_token()

# Use token in API requests
headers = {"Authorization": f"Bearer {token}"}

# Or get an authenticated client directly
async with await auth.get_authenticated_client() as client:
    response = await client.get("/api/some-endpoint")
```

### JavaScript/TypeScript E2E Tests

```typescript
// Using the frontend auth service
import { unifiedAuthService } from '@/auth/unified-auth-service';

// Authenticate with E2E bypass
const bypassKey = process.env.E2E_BYPASS_KEY;
const result = await unifiedAuthService.handleE2ETestAuth(bypassKey, {
  email: 'e2e-test@staging.netrasystems.ai',
  name: 'E2E Test User',
  permissions: ['read', 'write']
});

if (result) {
  console.log('E2E auth successful:', result.access_token);
}
```

### Direct API Call

```bash
curl -X POST https://api.staging.netrasystems.ai/auth/e2e/test-auth \
  -H "Content-Type: application/json" \
  -H "X-E2E-Bypass-Key: $E2E_BYPASS_KEY" \
  -d '{
    "email": "e2e-test@staging.netrasystems.ai",
    "name": "E2E Test User",
    "permissions": ["read", "write"]
  }'
```

## Custom Test Users

You can create test users with specific attributes:

```python
token = await auth.get_test_token(
    email="admin-test@staging.netrasystems.ai",
    name="Admin Test User",
    permissions=["read", "write", "admin"]
)
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run E2E Tests on Staging
  env:
    E2E_BYPASS_KEY: ${{ secrets.E2E_BYPASS_KEY }}
    ENVIRONMENT: staging
    STAGING_AUTH_URL: https://api.staging.netrasystems.ai
  run: |
    pytest tests/e2e/test_staging_api_with_auth.py
```

### GitLab CI

```yaml
e2e-staging:
  stage: test
  variables:
    E2E_BYPASS_KEY: $E2E_BYPASS_KEY
    ENVIRONMENT: staging
    STAGING_AUTH_URL: https://api.staging.netrasystems.ai
  script:
    - pytest tests/e2e/test_staging_api_with_auth.py
```

## Token Caching

The auth helper automatically caches tokens to reduce API calls:

- Tokens are cached for 14 minutes (1 minute before expiry)
- Cache is per-instance of StagingAuthHelper
- Use singleton pattern for global caching:

```python
from tests.e2e.staging_auth_bypass import get_staging_auth

auth = get_staging_auth()  # Returns singleton instance
```

## Troubleshooting

### Invalid Bypass Key Error

```
Error: 401 - Invalid E2E bypass key
```

**Solution**: Verify the bypass key matches the one in Google Secrets Manager

### Environment Not Staging

```
Error: 403 - E2E test authentication is only available in staging environment
```

**Solution**: Ensure `ENVIRONMENT=staging` is set

### Secret Not Configured

```
Error: 503 - E2E test authentication is not configured
```

**Solution**: Create the `e2e-bypass-key` secret in Google Secrets Manager

### Network Errors

```
Error: Connection to staging API failed
```

**Solution**: 
- Verify staging API is accessible
- Check firewall rules if running from CI/CD
- Ensure STAGING_AUTH_URL is correct

## Security Best Practices

1. **Never commit bypass keys**: Always use environment variables or secrets management
2. **Rotate keys regularly**: Update the bypass key monthly
3. **Monitor usage**: Review auth logs for suspicious E2E auth attempts
4. **Limit permissions**: Only grant necessary permissions to test users
5. **Use unique emails**: Use descriptive email addresses for different test scenarios

## Monitoring

All E2E authentications are logged with:
- IP address of requester
- User agent
- Test user details
- Timestamp

Monitor these logs for:
- Unexpected IP addresses
- High frequency of requests
- Failed authentication attempts

## Example Test Suite

See `tests/e2e/test_staging_api_with_auth.py` for a complete example test suite using the OAUTH SIMULATION mechanism.