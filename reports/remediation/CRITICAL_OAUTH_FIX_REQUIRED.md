# CRITICAL: OAuth Configuration Fix Required

## Problem Summary
Authentication is completely broken in staging because Google OAuth is rejecting the callback due to redirect URI mismatch.

## Current Behavior (VERIFIED)

1. User visits: `https://app.staging.netrasystems.ai/login`
2. Auth service redirects to Google with:
   ```
   redirect_uri=https://auth.staging.netrasystems.ai/auth/callback
   ```
3. **FAILURE**: Google rejects this because the URI is not in the authorized list

## Root Cause Analysis

### Code Analysis Results:
- ✅ `AuthConfig.get_auth_service_url()` correctly returns `https://auth.staging.netrasystems.ai` for staging
- ✅ `AuthConfig.get_frontend_url()` correctly returns `https://app.staging.netrasystems.ai` for staging  
- ✅ OAuth initiation uses auth service URL for callback (line 433: `redirect_uri = _determine_urls()[0] + "/auth/callback"`)
- ✅ After successful callback, auth service redirects to frontend (line 1032)
- ✅ CORS is properly configured for `app.staging.netrasystems.ai`

### The ONLY Issue:
**Google OAuth Console does not have `https://auth.staging.netrasystems.ai/auth/callback` in authorized redirect URIs**

## Required Google Cloud Console Configuration

### Project: `netra-staging` (Project ID: 701982941522)

Navigate to: **APIs & Services → Credentials → OAuth 2.0 Client IDs**

Find the OAuth client with ID: `701982941522-in8iru136ovb8r7mv0d6rje2pkatgk8s.apps.googleusercontent.com`

### Add These Authorized Redirect URIs:

**CRITICAL - Add this one:**
```
https://auth.staging.netrasystems.ai/auth/callback
```

**Already configured (keep these):**
```
https://app.staging.netrasystems.ai/auth/callback
https://netra-auth-service-701982941522.us-central1.run.app/auth/callback
```

### Authorized JavaScript Origins (verify these are set):
```
https://app.staging.netrasystems.ai
https://auth.staging.netrasystems.ai
https://api.staging.netrasystems.ai
```

## Verification Steps

After adding the redirect URI in Google Console:

1. Test OAuth initiation:
```bash
curl -v "https://auth.staging.netrasystems.ai/auth/google"
# Should redirect to Google without errors
```

2. Complete OAuth flow:
- Visit https://app.staging.netrasystems.ai/login
- Click "Sign in with Google"
- Should complete without redirect_uri_mismatch error

## Why The Code Is Correct

The current implementation is architecturally sound:

1. **Security**: OAuth callbacks go to auth service for validation
2. **Token Management**: Auth service creates and manages JWTs
3. **Separation of Concerns**: Frontend never handles raw OAuth responses
4. **Subdomain Isolation**: Each service has its own subdomain

## Common Misconfigurations to Avoid

❌ **DON'T** change the code to use `app.staging.netrasystems.ai` for OAuth callback
✅ **DO** add `auth.staging.netrasystems.ai/auth/callback` to Google OAuth

❌ **DON'T** mix up the OAuth provider callback (Google → Auth Service) with the final redirect (Auth Service → Frontend)
✅ **DO** understand the two-step flow

## Test Coverage Gap

The tests didn't catch this because:
- OAuth configuration is external (Google Cloud Console)
- Integration tests can't verify Google's OAuth settings
- Need manual verification or API-based configuration checks

## Action Required

**WHO**: Anyone with access to Google Cloud Console for project `netra-staging`
**WHAT**: Add `https://auth.staging.netrasystems.ai/auth/callback` to authorized redirect URIs
**WHEN**: IMMEDIATELY - Authentication is completely broken until this is fixed
**WHERE**: https://console.cloud.google.com/apis/credentials

## Impact If Not Fixed

- ❌ No users can log in to staging
- ❌ All authenticated features are inaccessible
- ❌ Cannot test any user flows
- ❌ Blocks all staging testing and demos

## Confirmation

After fixing, the OAuth flow will work as designed:
1. Google redirects to `auth.staging.netrasystems.ai/auth/callback` ✅
2. Auth service processes and redirects to `app.staging.netrasystems.ai/auth/callback` ✅
3. Frontend receives tokens and establishes session ✅