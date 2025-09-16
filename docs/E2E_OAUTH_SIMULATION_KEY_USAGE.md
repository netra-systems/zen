# E2E_OAUTH_SIMULATION_KEY Usage Guide

## Overview

The `E2E_OAUTH_SIMULATION_KEY` is a security-critical environment variable used to bypass OAuth authentication during automated End-to-End (E2E) testing on the staging environment. This key enables test automation without requiring real OAuth flows while maintaining security boundaries.

## Business Value

- **Prevents $50K+ MRR Loss**: Enables reliable staging environment testing
- **Automated Testing**: Allows E2E tests to run without manual OAuth intervention
- **Security Compliance**: Only works in staging environment, not production
- **CI/CD Pipeline**: Enables automated deployment validation

## How It Works

### Security Architecture

1. **Environment Restricted**: Only functions in `staging` environment
2. **Secure Storage**: Key stored in Google Secret Manager (`e2e-oauth-simulation-key`)
3. **Request Validation**: Uses HMAC comparison for secure key validation
4. **Audit Logging**: All usage is logged for security auditing

### Implementation Flow

```
1. E2E Test → Includes X-E2E-Bypass-Key header
2. Auth Service → Validates environment == 'staging'
3. Secret Loader → Retrieves key from GCP Secret Manager
4. Route Handler → HMAC validates provided vs expected key
5. If Valid → Creates temporary test user token
6. Test Continues → With authenticated session
```

## Configuration Locations

The key has been added to all necessary configuration files:

### Environment Files
- `/.env.development` - Development placeholder value
- `/config/development.env` - Development configuration
- `/config/staging.env` - Staging configuration (empty, loaded from secrets)

### Docker Configuration
- `/docker-compose.yml` - Development auth service environment
- `/docker-compose.dev.yml` - Alternative development environment

### Example Files
- `/config/.env.example` - Template for new deployments
- `/config/env/.env.example` - Comprehensive configuration template
- `/config/env/.env.staging.example` - Staging-specific template

## Usage in Code

### Auth Service Implementation
The key is used in:
- `/auth_service/auth_core/secret_loader.py` - Key retrieval logic
- `/auth_service/auth_core/routes/auth_routes.py` - Authentication bypass endpoint

### E2E Test Implementation
The key is used by:
- `/tests/e2e/staging_auth_bypass.py` - Main bypass functionality
- `/tests/e2e/staging_config.py` - Configuration management
- `/tests/e2e/staging_auth_client.py` - Client authentication

## Security Requirements

### Development Environment
- Uses placeholder value: `dev-e2e-oauth-bypass-key-for-testing-only-change-in-staging`
- Logged warning when key is requested (not allowed in development)

### Staging Environment
- Key must be stored in Google Secret Manager
- Secret name: `e2e-oauth-simulation-key`
- Injected via Cloud Run `--set-secrets` flag
- Only accessible to staging auth service

### Production Environment
- Key MUST NOT be configured in production
- Auth service will refuse to load key in production environment
- Any attempt logged as security violation

## Deployment Configuration

### Google Secret Manager Setup
```bash
# Create the secret in GCP
gcloud secrets create e2e-oauth-simulation-key --data-file=key.txt

# Grant access to staging auth service
gcloud secrets add-iam-policy-binding e2e-oauth-simulation-key \
  --member="serviceAccount:netra-auth@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Cloud Run Configuration
```yaml
# In deployment configuration
env:
  - name: E2E_OAUTH_SIMULATION_KEY
    valueFrom:
      secretKeyRef:
        name: e2e-oauth-simulation-key
        version: latest
```

## API Usage

### Request Format
```http
POST /auth/e2e/test-auth
X-E2E-Bypass-Key: your-secure-bypass-key
Content-Type: application/json

{
  "email": "e2e-test@staging.netrasystems.ai",
  "name": "E2E Test User",
  "permissions": ["read", "write"]
}
```

### Response Format
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

## Testing Examples

### Python E2E Test
```python
from tests.e2e.staging_auth_bypass import StagingAuthHelper

# Initialize helper
auth_helper = StagingAuthHelper()

# Get test token
token = await auth_helper.get_test_token(
    email="test@example.com",
    permissions=["read", "write"]
)

# Use in API requests
headers = {"Authorization": f"Bearer {token}"}
```

### Direct HTTP Usage
```python
import os
import httpx

bypass_key = os.getenv("E2E_OAUTH_SIMULATION_KEY")
auth_url = "https://netra-auth-service-staging.run.app"

async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{auth_url}/auth/e2e/test-auth",
        headers={"X-E2E-Bypass-Key": bypass_key},
        json={"email": "test@example.com"}
    )
    token = response.json()["access_token"]
```

## Troubleshooting

### Common Issues

1. **Key Not Found Error**
   - Verify key exists in Google Secret Manager
   - Check Cloud Run service has secret access permissions
   - Ensure secret is properly mounted in deployment

2. **Invalid Key Error**
   - Verify key value matches exactly between tests and secrets
   - Check for trailing whitespace or encoding issues
   - Ensure key is not modified during environment loading

3. **Environment Restriction Error**
   - Verify `ENVIRONMENT=staging` is set correctly
   - Check auth service is detecting environment properly
   - Ensure not attempting to use in development/production

### Debug Commands
```bash
# Check if key is loaded in auth service
kubectl exec -it auth-service-pod -- env | grep E2E_OAUTH

# Verify secret exists in GCP
gcloud secrets describe e2e-oauth-simulation-key

# Test key access from service account
gcloud secrets access latest --secret="e2e-oauth-simulation-key"
```

## Security Considerations

### What This Key DOES
- Allows E2E tests to authenticate on staging
- Creates temporary test user sessions
- Enables automated testing workflows
- Maintains audit trail of usage

### What This Key DOES NOT
- Work in production environment
- Provide persistent authentication
- Grant elevated system privileges  
- Bypass other security validations

### Best Practices
1. Rotate key regularly (monthly recommended)
2. Use unique, cryptographically secure values
3. Monitor usage logs for anomalies
4. Restrict access to staging deployment pipeline only
5. Never commit actual key values to source control

## Integration Points

### CI/CD Pipeline
The key integrates with:
- GitHub Actions staging deployment
- Automated E2E test execution
- Staging environment validation
- Pre-production quality gates

### Monitoring
Usage is tracked via:
- Auth service security logs
- GCP Secret Manager access logs
- Application performance monitoring
- Security incident detection

## Maintenance

### Regular Tasks
- [ ] Monthly key rotation
- [ ] Access audit review
- [ ] Usage pattern analysis
- [ ] Security log monitoring

### Emergency Procedures
1. **Suspected Compromise**: Immediately rotate key in Secret Manager
2. **Staging Breach**: Revoke all staging secrets, redeploy environment
3. **Test Failures**: Verify key accessibility and staging environment health

---

Generated: 2025-08-31  
Version: 1.0  
Owner: Engineering Team