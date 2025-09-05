# OAuth Redirect URI Mismatch Audit Report

## Issue Summary
**Error**: `Error 400: redirect_uri_mismatch`  
**Message**: "You can't sign in to this app because it doesn't comply with Google's OAuth 2.0 policy"  
**Request Details**: `redirect_uri=https://auth.staging.netrasystems.ai/auth/oauth/callback`

## Root Cause Analysis

### 1. Application Configuration
The auth service is correctly configured to use:
- **Redirect URI**: `https://auth.staging.netrasystems.ai/auth/oauth/callback`
- **Source**: `GoogleOAuthProvider.get_redirect_uri()` in `/auth_service/auth_core/oauth/google_oauth.py`

### 2. Google Cloud Console Configuration Mismatch
The error indicates that Google OAuth Console does **NOT** have this exact URI registered.

### 3. Configuration Sources Verified

#### auth_service/auth_core/auth_environment.py (lines 708-726)
```python
def get_oauth_redirect_uri(self, provider: str = "google") -> str:
    # Build from frontend URL
    frontend_url = self.get_frontend_url()
    return f"{frontend_url}/auth/callback"
```
**ISSUE**: The method builds redirect URI from frontend URL, not auth service URL.

#### auth_service/auth_core/oauth/google_oauth.py (lines 78-93)
```python
def get_redirect_uri(self) -> Optional[str]:
    # Get the proper auth service URL from configuration
    base_url = self.auth_env.get_auth_service_url()
    # Construct redirect URI using configured auth service URL
    self._redirect_uri = f"{base_url}/auth/oauth/callback"
    return self._redirect_uri
```
**CORRECT**: This properly constructs the auth service redirect URI.

#### config/staging.env (lines 83-84)
```
OAUTH_REDIRECT_URI=https://auth.staging.netrasystems.ai/oauth/callback
OAUTH_CALLBACK_URL=https://auth.staging.netrasystems.ai/oauth/callback
```
**NOTE**: Path is `/oauth/callback` not `/auth/oauth/callback`

## Critical Findings

### 1. Path Inconsistency
- **Application uses**: `/auth/oauth/callback`
- **Config file has**: `/oauth/callback`
- **Google expects**: Exact match to what's registered

### 2. Multiple Redirect URI Sources
- `AuthEnvironment.get_oauth_redirect_uri()` - Returns frontend URL (wrong)
- `GoogleOAuthProvider.get_redirect_uri()` - Returns auth service URL (correct)
- Environment variables - May override both

### 3. Previous Fix Applied
According to `/SPEC/learnings/oauth_redirect_uri_misconfiguration.xml`, the issue of using frontend URLs was supposedly fixed, but:
- The fix may not be complete
- Google Console may not have been updated
- Path mismatch introduces new failure mode

## Required Actions

### 1. Immediate Fix - Update Google OAuth Console

**Add these EXACT redirect URIs to Google OAuth Console for staging:**
```
https://auth.staging.netrasystems.ai/auth/oauth/callback
https://auth.staging.netrasystems.ai/auth/callback
```

**Access Google Console:**
1. Go to https://console.cloud.google.com/apis/credentials
2. Select the staging project
3. Find OAuth 2.0 Client ID for staging
4. Add both URIs to "Authorized redirect URIs"
5. Save changes

### 2. Code Fix - Standardize Redirect URI Path

**Update** `/auth_service/auth_core/oauth/google_oauth.py` line 91:
```python
# Standardize to use /auth/callback to match documented configuration
self._redirect_uri = f"{base_url}/auth/callback"
```

### 3. Environment Config Fix

**Update** `/config/staging.env` lines 83-84:
```
OAUTH_REDIRECT_URI=https://auth.staging.netrasystems.ai/auth/callback
OAUTH_CALLBACK_URL=https://auth.staging.netrasystems.ai/auth/callback
```

### 4. Fix AuthEnvironment Method

**Update** `/auth_service/auth_core/auth_environment.py` lines 708-726:
```python
def get_oauth_redirect_uri(self, provider: str = "google") -> str:
    """Get OAuth redirect URI with environment-specific defaults.
    
    Args:
        provider: OAuth provider name (google, github, etc.)
        
    Returns:
        Full OAuth callback URL for the provider
    """
    env = self.get_environment()
    
    # Check for explicit override first
    uri = self.env.get("OAUTH_REDIRECT_URI")
    if uri:
        return uri
    
    # Build from AUTH SERVICE URL, not frontend
    auth_url = self.get_auth_service_url()
    return f"{auth_url}/auth/callback"
```

## Validation Steps

1. **Check current Google Console configuration:**
   ```bash
   # This will show what redirect URIs the application expects
   python scripts/validate_oauth_configuration.py --env staging
   ```

2. **Test OAuth flow after Google Console update:**
   ```bash
   # Manual test through browser
   curl -I "https://auth.staging.netrasystems.ai/auth/login/google"
   ```

3. **Verify redirect URI in OAuth URL:**
   - Check that the `redirect_uri` parameter in the Google OAuth URL matches exactly what's in Google Console

## Prevention Measures

1. **Single Source of Truth**: Ensure only `GoogleOAuthProvider.get_redirect_uri()` is used
2. **Path Standardization**: Use `/auth/callback` consistently across all configs
3. **Pre-deployment Validation**: Run OAuth configuration validation before every deployment
4. **Documentation**: Keep Google Console configuration documented and version controlled

## Summary

The redirect URI mismatch is caused by:
1. **Google OAuth Console not having the exact URI** that the application uses
2. **Path inconsistency** between `/auth/oauth/callback` (app) and `/oauth/callback` (config)
3. **Multiple sources** for redirect URI configuration causing confusion

The immediate fix is to **add the exact URIs to Google OAuth Console**. The long-term fix is to standardize the redirect URI path and ensure single source of truth.