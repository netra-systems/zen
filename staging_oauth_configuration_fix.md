# Staging OAuth Configuration Fix

## Problem Identified

The OAuth flow is broken in staging because of a redirect URI mismatch. The auth service is correctly configured but Google OAuth is rejecting the callback.

## Current Flow (CORRECT)

1. User visits `https://app.staging.netrasystems.ai/login`
2. Frontend redirects to `https://auth.staging.netrasystems.ai/auth/google`
3. Auth service redirects to Google with:
   - `redirect_uri=https://auth.staging.netrasystems.ai/auth/callback`
4. Google validates redirect URI against configured URIs
5. After login, Google redirects to `https://auth.staging.netrasystems.ai/auth/callback`
6. Auth service processes callback and redirects to `https://app.staging.netrasystems.ai/auth/callback` with tokens

## The Issue

The auth service is correctly using `https://auth.staging.netrasystems.ai/auth/callback` as the redirect URI, but this URI needs to be added to Google Cloud Console OAuth configuration.

## Required Google Cloud Console Configuration

### OAuth 2.0 Client ID Settings

**Authorized JavaScript origins:**
- `https://app.staging.netrasystems.ai`
- `https://auth.staging.netrasystems.ai`
- `https://api.staging.netrasystems.ai`

**Authorized redirect URIs:**
- `https://auth.staging.netrasystems.ai/auth/callback` ← **CRITICAL: Add this**
- `https://app.staging.netrasystems.ai/auth/callback` (for future direct flows)
- `https://netra-auth-service-701982941522.us-central1.run.app/auth/callback` (backup)

## Steps to Fix

1. **Go to Google Cloud Console**
   - Project: `netra-staging`
   - Navigate to: APIs & Services → Credentials
   - Find OAuth 2.0 Client ID for staging

2. **Add Redirect URIs**
   - Click on the OAuth client
   - Add to "Authorized redirect URIs":
     - `https://auth.staging.netrasystems.ai/auth/callback`
   - Save changes

3. **Verify Configuration**
   - The auth service code is CORRECT
   - The flow is CORRECT
   - Only the Google OAuth configuration needs updating

## Why This Architecture is Correct

1. **Security**: OAuth callback goes to auth service first for validation
2. **Centralization**: Auth service handles all OAuth logic
3. **Separation**: Frontend only receives processed tokens, not raw OAuth responses
4. **Flexibility**: Auth service can validate, transform, and secure tokens before passing to frontend

## Test Commands

After updating Google OAuth configuration:

```bash
# Test OAuth initiation
curl -I "https://auth.staging.netrasystems.ai/auth/google?return_url=https://app.staging.netrasystems.ai/dashboard"

# Should redirect to Google with correct redirect_uri
```

## Common Misunderstandings

- ❌ **Wrong**: OAuth should callback directly to frontend (`app.staging.netrasystems.ai`)
- ✅ **Right**: OAuth callbacks to auth service, which then redirects to frontend

- ❌ **Wrong**: The code needs to be changed to use frontend URL
- ✅ **Right**: The code is correct; Google OAuth config needs updating

## Validation Tests

The failing tests in `test_staging_oauth_redirect_critical.py` are actually testing the WRONG behavior. The auth service SHOULD use its own URL for the OAuth callback, not the frontend URL.

## Environment Variables (Already Correct)

No changes needed to environment variables. The auth service correctly determines URLs based on environment.

## Summary

**No code changes required**. Only need to add `https://auth.staging.netrasystems.ai/auth/callback` to Google OAuth authorized redirect URIs in Google Cloud Console.