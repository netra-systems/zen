# OAuth Staging Configuration Fix

## Overview
This document outlines the critical fixes implemented to resolve OAuth authentication issues in the staging environment. These fixes address the "missing wires" that were preventing OAuth authentication from working properly in staging deployments.

## Problems Identified

### 1. Environment Variable Name Mismatches
**Issue**: The deployment script was using incorrect environment variable names for OAuth credentials.
- **Used**: `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
- **Expected by Auth Service**: `GOOGLE_OAUTH_CLIENT_ID_STAGING` and `GOOGLE_OAUTH_CLIENT_SECRET_STAGING`

### 2. Inconsistent Secret Mapping
The Google Secret Manager mapping in the deployment script didn't match the auth service's secret loading logic.

### 3. Frontend URL Configuration
Ensuring consistency between frontend URL configuration across all services.

## Fixes Implemented

### 1. Deployment Script OAuth Secret Configuration (`scripts/deploy_to_gcp.py`)

**Before**:
```bash
# Backend service
GOOGLE_CLIENT_ID=google-client-id-staging:latest
GOOGLE_CLIENT_SECRET=google-client-secret-staging:latest

# Auth service  
GOOGLE_OAUTH_CLIENT_CLIENT_ID_STAGING=GOOGLE_OAUTH_CLIENT_CLIENT_ID_STAGING:latest
GOOGLE_OAUTH_CLIENT_CLIENT_SECRET_STAGING=GOOGLE_OAUTH_CLIENT_CLIENT_SECRET_STAGING:latest
```

**After**:
```bash
# Both backend and auth services now use consistent naming
GOOGLE_OAUTH_CLIENT_ID_STAGING=google-client-id-staging:latest
GOOGLE_OAUTH_CLIENT_SECRET_STAGING=google-client-secret-staging:latest
```

### 2. Secret Loading Priority Chain

The auth service follows this priority chain for OAuth credentials:

1. **Environment-specific variables** (highest priority):
   - `GOOGLE_OAUTH_CLIENT_ID_STAGING`
   - `GOOGLE_OAUTH_CLIENT_SECRET_STAGING`

2. **Google Secret Manager secrets**:
   - `google-client-id-staging:latest`
   - `google-client-secret-staging:latest`

3. **Fallback variables** (for development):
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`

### 3. Frontend URL Configuration

All services now consistently use:
- **Staging**: `https://app.staging.netrasystems.ai`
- **Production**: `https://netrasystems.ai` 
- **Development**: `http://localhost:3000`

### 4. OAuth Callback Flow

The OAuth callback flow works as follows:

1. **Initiate Login** (`/auth/login`):
   - Frontend redirects to Google OAuth with proper state parameter
   - Callback URL: `https://app.staging.netrasystems.ai/auth/callback`

2. **Google Callback** (`/auth/callback` - GET):
   - Auth service receives OAuth code from Google
   - Validates state parameter for CSRF protection
   - Exchanges code for Google tokens
   - Creates user in database
   - Generates JWT tokens
   - Redirects to frontend with tokens: `https://app.staging.netrasystems.ai/auth/callback?token={access_token}&refresh={refresh_token}`

3. **Frontend Processing**:
   - Frontend receives tokens from URL parameters
   - Stores tokens securely
   - Redirects user to application dashboard

## Environment Variables Required

### For Staging Deployment

**Backend Service**:
```bash
ENVIRONMENT=staging
GOOGLE_OAUTH_CLIENT_ID_STAGING={from GSM}
GOOGLE_OAUTH_CLIENT_SECRET_STAGING={from GSM}
FRONTEND_URL=https://app.staging.netrasystems.ai
AUTH_SERVICE_URL=https://auth.staging.netrasystems.ai
```

**Auth Service**:
```bash
ENVIRONMENT=staging
GOOGLE_OAUTH_CLIENT_ID_STAGING={from GSM}
GOOGLE_OAUTH_CLIENT_SECRET_STAGING={from GSM}
FRONTEND_URL=https://app.staging.netrasystems.ai
AUTH_SERVICE_URL=https://auth.staging.netrasystems.ai
JWT_SECRET_KEY={from GSM}
SERVICE_SECRET={from GSM}
```

**Frontend Service**:
```bash
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://api.staging.netrasystems.ai
NEXT_PUBLIC_AUTH_URL=https://auth.staging.netrasystems.ai
NEXT_PUBLIC_WS_URL=wss://api.staging.netrasystems.ai
```

## Google Secret Manager Configuration

The following secrets must be configured in Google Secret Manager:

```bash
# OAuth Credentials
google-client-id-staging: {your-google-oauth-client-id}
google-client-secret-staging: {your-google-oauth-client-secret}

# JWT Configuration  
jwt-secret-key-staging: {secure-64-char-string}
service-secret-staging: {different-secure-32-char-string}

# Database Configuration
postgres-host-staging: /cloudsql/netra-staging:us-central1:staging-shared-postgres
postgres-port-staging: 5432
postgres-db-staging: netra_dev
postgres-user-staging: postgres
postgres-password-staging: {database-password}
```

## Deployment Process

### 1. Update Secrets
```bash
# Set required environment variables
export GOOGLE_CLIENT_ID="your-google-oauth-client-id"
export GOOGLE_CLIENT_SECRET="your-google-oauth-client-secret"
export GEMINI_API_KEY="your-gemini-api-key"
```

### 2. Deploy to Staging
```bash
# Deploy with local build (fastest)
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Or deploy with checks (recommended for production-readiness testing)
python scripts/deploy_to_gcp.py --project netra-staging --build-local --run-checks
```

### 3. Verify OAuth Configuration
```bash
# Check auth service configuration
curl https://auth.staging.netrasystems.ai/auth/config

# Expected response should include:
# - google_client_id: (your client ID)
# - endpoints.callback: https://app.staging.netrasystems.ai/auth/callback
# - authorized_redirect_uris: ["https://app.staging.netrasystems.ai/auth/callback"]
```

## Testing OAuth Flow

### 1. Manual Testing
1. Navigate to `https://app.staging.netrasystems.ai`
2. Click "Sign in with Google"
3. Complete Google OAuth flow
4. Verify successful login and redirect to dashboard

### 2. Automated Testing
```bash
# Run OAuth-specific tests
python unified_test_runner.py --level integration --pattern "*oauth*" --env staging

# Run comprehensive auth tests
python unified_test_runner.py --level integration --pattern "*auth*" --env staging
```

## Troubleshooting

### Common Issues

**1. "OAuth not configured" Error**:
- Verify `GOOGLE_OAUTH_CLIENT_ID_STAGING` is set in Google Secret Manager
- Check deployment logs for secret loading errors

**2. "Invalid redirect URI" Error**:
- Ensure Google OAuth app is configured with correct redirect URIs
- Verify frontend URL matches exactly in all configurations

**3. "State parameter validation failed"**:
- Check that frontend and auth service are using same domain
- Verify CORS configuration allows cross-origin requests

**4. "Failed to exchange code" Error**:
- Verify `GOOGLE_OAUTH_CLIENT_SECRET_STAGING` is correct
- Check network connectivity to Google OAuth endpoints

### Debugging Commands

```bash
# Check auth service health
curl https://auth.staging.netrasystems.ai/health

# Check auth configuration
curl https://auth.staging.netrasystems.ai/auth/config

# Check deployment status
gcloud run services describe netra-auth-service --region us-central1 --project netra-staging

# View auth service logs
gcloud logs read --project netra-staging --filter="resource.labels.service_name=netra-auth-service" --limit 50
```

## Security Considerations

1. **Environment Variable Naming**: Using environment-specific variables prevents accidental use of production credentials in staging
2. **State Parameter Validation**: CSRF protection through OAuth state parameter validation
3. **Secure Redirect URLs**: Only allowing approved redirect URLs prevents OAuth hijacking
4. **Secret Rotation**: All secrets can be rotated independently through Google Secret Manager

## Related Files

- `scripts/deploy_to_gcp.py` - Deployment configuration
- `auth_service/auth_core/config.py` - Auth service configuration
- `auth_service/auth_core/secret_loader.py` - Secret loading logic
- `auth_service/auth_core/routes/auth_routes.py` - OAuth callback implementation
- `frontend/lib/unified-api-config.ts` - Frontend URL configuration

## Validation Checklist

- [ ] OAuth credentials mapped correctly in deployment script
- [ ] Environment variable names consistent between services  
- [ ] Google Secret Manager secrets configured
- [ ] Frontend redirect URLs match auth service configuration
- [ ] OAuth callback flow works end-to-end
- [ ] State parameter validation prevents CSRF attacks
- [ ] Error handling provides clear troubleshooting information