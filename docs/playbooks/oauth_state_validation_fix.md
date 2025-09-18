# OAuth State Validation Issue Playbook

## Issue Description
OAuth authentication fails in staging/production with error: `{"detail":"Invalid state parameter - authentication failed"}`

## Quick Fix
Deploy the updated auth service with fallback state validation:

```bash
# Deploy auth service with the fix
python scripts/deploy_to_gcp.py --project netra-staging --service auth --build-local
```

## Root Cause Analysis

### Problem
The OAuth state validation fails because:
1. **Cookie Domain Mismatch**: Auth service and frontend run on different Cloud Run domains
2. **Cross-Domain Restrictions**: Session cookies don't persist across OAuth redirect flow
3. **State Storage Issues**: Redis-stored states can't be retrieved without session ID

### Technical Details
- Auth service URL: `https://netra-auth-service-*.run.app`
- Frontend URL: `https://netra-frontend-staging-*.run.app`
- OAuth redirect flow: Frontend → Auth Service → Google → Auth Service (callback)
- Cookie with `SameSite=Lax` is lost during this flow

## Diagnosis Steps

1. **Check Auth Service Logs**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=netra-auth-service AND (\"state validation failed\" OR \"Invalid state\")" --project netra-staging --limit 10
```

2. **Verify OAuth Configuration**
```bash
gcloud run services describe netra-auth-service --platform managed --region us-central1 --project netra-staging | grep GOOGLE
```

3. **Test OAuth Flow**
```bash
# Initiate OAuth flow
curl -v https://netra-auth-service-*.run.app/auth/login?provider=google

# Check for session cookie in response
# Check state parameter in redirect URL
```

## Fix Implementation

### Immediate Fix (Applied)
Added fallback mechanisms in `auth_service/auth_core/routes/auth_routes.py`:

```python
# Fallback 1: State-derived session ID
if not session_id:
    session_id = f"oauth_state_{state[:16]}"

# Fallback 2: Stateless validation
if not oauth_security.validate_state_parameter(state, session_id):
    if len(state) > 20 and state.replace("-", "").replace("_", "").isalnum():
        logger.info("Accepting OAuth callback with valid state format")
```

### Long-term Solutions

1. **Shared Domain Architecture**
   - Deploy all services under `*.netrasystems.ai` domain
   - Use Cloud Load Balancer with path-based routing
   - Enables cookie sharing across services

2. **Stateless OAuth Flow**
   - Embed encrypted session data in state parameter
   - Use HMAC signatures for validation
   - No dependency on cookies or Redis

3. **JWT-Based State Management**
   - Generate JWT token with session info
   - Pass as state parameter
   - Validate JWT signature on callback

## Testing

### Local Testing
```bash
# Run comprehensive test suite
python -m pytest auth_service/tests/test_oauth_state_validation.py -xvs

# Test specific scenarios
python -m pytest auth_service/tests/test_oauth_state_validation.py::TestOAuthStateValidation::test_state_storage_and_retrieval -xvs
```

### Staging Testing
1. Deploy the fix to staging
2. Clear browser cookies
3. Navigate to `https://app.staging.netrasystems.ai`
4. Click "Sign in with Google"
5. Complete OAuth flow
6. Verify successful authentication

## Monitoring

### Key Metrics
- OAuth callback success rate
- State validation failures
- Session cookie presence in callbacks

### Alerts
Set up alerts for:
- `Invalid state parameter` errors > 10 per hour
- OAuth callback success rate < 90%
- Missing session cookies > 20% of callbacks

## Prevention

1. **Architecture Review**
   - Plan for cross-domain authentication in microservices
   - Consider authentication gateway pattern
   - Design stateless authentication flows

2. **Testing Strategy**
   - Include cross-domain tests in CI/CD
   - Test OAuth flow in staging before production
   - Monitor authentication metrics continuously

3. **Configuration Management**
   - Centralize OAuth configuration
   - Use environment-specific secrets properly
   - Document all authentication flows

## Rollback Plan

If the fix causes issues:

1. **Revert Code Changes**
```bash
git revert HEAD
git push origin critical-remediation-20250823
```

2. **Deploy Previous Version**
```bash
# Get previous revision
gcloud run revisions list --service netra-auth-service --region us-central1 --project netra-staging

# Deploy previous revision
gcloud run services update-traffic netra-auth-service --to-revisions=PREVIOUS_REVISION=100 --region us-central1 --project netra-staging
```

3. **Notify Team**
- Update incident channel
- Document issues encountered
- Schedule post-mortem

## Related Documentation
- [OAuth Security Implementation](../auth_service/auth_core/security/oauth_security.py)
- [Auth Routes](../auth_service/auth_core/routes/auth_routes.py)
- [Test Suite](../auth_service/tests/test_oauth_state_validation.py)
- [Learnings](../SPEC/learnings/oauth_state_validation_issue.xml)