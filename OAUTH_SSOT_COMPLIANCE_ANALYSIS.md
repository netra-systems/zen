# OAuth Redirect URI SSOT Compliance Analysis

## Executive Summary
**CRITICAL FINDING**: The OAuth redirect URI configuration **VIOLATES SSOT principles** with multiple conflicting sources of truth.

## SSOT Violations Identified

### 1. Multiple Sources for Redirect URI

#### Source 1: `GoogleOAuthProvider.get_redirect_uri()` 
**Location**: `/auth_service/auth_core/oauth/google_oauth.py:78-93`
```python
def get_redirect_uri(self) -> Optional[str]:
    base_url = self.auth_env.get_auth_service_url()
    self._redirect_uri = f"{base_url}/auth/oauth/callback"
    return self._redirect_uri
```
**Returns**: `https://auth.staging.netrasystems.ai/auth/oauth/callback`

#### Source 2: `AuthEnvironment.get_oauth_redirect_uri()`
**Location**: `/auth_service/auth_core/auth_environment.py:708-726`
```python
def get_oauth_redirect_uri(self, provider: str = "google") -> str:
    uri = self.env.get("OAUTH_REDIRECT_URI")
    if uri:
        return uri
    frontend_url = self.get_frontend_url()
    return f"{frontend_url}/auth/callback"
```
**Returns**: `https://app.staging.netrasystems.ai/auth/callback` (WRONG - frontend URL!)

#### Source 3: Environment Variables
**Location**: `/config/staging.env:83-84`
```
OAUTH_REDIRECT_URI=https://auth.staging.netrasystems.ai/oauth/callback
OAUTH_CALLBACK_URL=https://auth.staging.netrasystems.ai/oauth/callback
```
**Note**: Missing `/auth` prefix in path

#### Source 4: Hardcoded in Routes
**Location**: `/auth_service/auth_core/routes/auth_routes.py:79-85`
```python
"endpoints": {
    "callback": f"{auth_base_url}/auth/callback",
},
"authorized_redirect_uris": [f"{frontend_base_url}/auth/callback"]
```
**Mixed**: Returns both auth and frontend URLs!

### 2. Path Inconsistencies

- **Application uses**: `/auth/oauth/callback` and `/auth/callback`
- **Config file has**: `/oauth/callback`
- **Tests expect**: Various combinations

### 3. Who Uses What?

#### GoogleOAuthProvider (CORRECT)
- Uses its own `get_redirect_uri()` method
- Correctly returns auth service URL
- Path: `/auth/oauth/callback`

#### AuthEnvironment (WRONG)
- `get_oauth_redirect_uri()` returns frontend URL
- Used by tests and some configuration validation
- Path: `/auth/callback`

#### Tests (MIXED)
- Some tests use `GoogleOAuthProvider.get_redirect_uri()` (correct)
- Some tests use `AuthEnvironment.get_oauth_redirect_uri()` (wrong)
- Tests expect different paths in different places

## Why This Causes OAuth Failure

1. **Google Console Configuration**: Must have EXACT match to what application sends
2. **Application sends**: `https://auth.staging.netrasystems.ai/auth/oauth/callback`
3. **If Google Console has**: Any other URL = `redirect_uri_mismatch`

## SSOT Violation Impact

### Business Impact
- 100% OAuth authentication failure when misconfigured
- User cannot sign in via Google
- Lost user conversions

### Technical Impact
- Multiple teams can "fix" the same issue differently
- Tests pass with wrong configuration
- Deployment succeeds but runtime fails

### Maintenance Impact
- Confusion about which method to use
- Different services use different sources
- Changes in one place don't propagate

## Required SSOT Fix

### Step 1: Choose Single Source of Truth
**Recommendation**: `GoogleOAuthProvider.get_redirect_uri()` should be the ONLY source

### Step 2: Remove/Deprecate Other Sources
1. **Delete**: `AuthEnvironment.get_oauth_redirect_uri()` method
2. **Update**: All tests to use `GoogleOAuthProvider.get_redirect_uri()`
3. **Remove**: Environment variable overrides for redirect URI
4. **Fix**: Route handlers to use GoogleOAuthProvider

### Step 3: Standardize Path
Choose ONE path and use it everywhere:
- **Recommended**: `/auth/callback` (simpler, matches documentation)
- **Alternative**: `/auth/oauth/callback` (more explicit)

### Step 4: Update Implementation

```python
# Single source of truth in GoogleOAuthProvider
class GoogleOAuthProvider:
    def get_redirect_uri(self) -> str:
        """SINGLE SOURCE OF TRUTH for OAuth redirect URI"""
        base_url = self.auth_env.get_auth_service_url()
        return f"{base_url}/auth/callback"  # Standardized path

# Remove this method entirely
# AuthEnvironment.get_oauth_redirect_uri() - DELETE THIS

# Update routes to use provider
oauth_provider = GoogleOAuthProvider()
redirect_uri = oauth_provider.get_redirect_uri()
```

### Step 5: Update Google Console
Add ONLY the URI from `GoogleOAuthProvider.get_redirect_uri()`:
- Staging: `https://auth.staging.netrasystems.ai/auth/callback`
- Production: `https://auth.netrasystems.ai/auth/callback`

## Validation Checklist

- [ ] Only ONE method returns redirect URI
- [ ] All services use the same method
- [ ] All tests use the same method
- [ ] Environment variables don't override programmatic values
- [ ] Google Console has exact match to application
- [ ] Path is consistent across all uses

## Summary

The current implementation **severely violates SSOT** with:
- **4 different sources** for redirect URI
- **2 different URL patterns** (auth vs frontend)
- **3 different paths** (`/auth/callback`, `/auth/oauth/callback`, `/oauth/callback`)

This is why OAuth is failing - the application doesn't have a single, authoritative source for what redirect URI to use, leading to mismatches with Google's configuration.