# Staging Environment Mixed Content and WebSocket Audit Report

**Date:** 2025-08-27  
**Environment:** Staging (app.staging.netrasystems.ai)  
**Status:** Critical Issues Identified

## Executive Summary

The staging environment is experiencing critical HTTPS mixed content errors and WebSocket connection failures. The frontend served over HTTPS is attempting to make HTTP requests to the backend API, which is blocked by browser security policies. Additionally, WebSocket connections are failing with authentication errors.

## Issues Identified

### 1. Mixed Content Error (CRITICAL)
**Problem:** HTTPS page requesting HTTP resources
- **Frontend URL:** `https://app.staging.netrasystems.ai`
- **Blocked Request:** `http://api.staging.netrasystems.ai/api/threads/?limit=20&offset=0`
- **Impact:** All API calls are blocked, application is non-functional

### 2. WebSocket Connection Failures
**Problem:** WebSocket connections failing with error code 1006
- **WebSocket URL:** `wss://api.staging.netrasystems.ai/ws`
- **Error:** Authentication error, connection closed abnormally
- **Impact:** Real-time features unavailable

### 3. API Request Failures
**Problem:** Network errors on all API requests
- **Symptom:** "Failed to fetch" errors
- **Root Cause:** Mixed content blocking + possible CORS issues

## Root Cause Analysis

### Issue #1: URL Protocol Mismatch in API Interceptor

The auth interceptor (`frontend/lib/auth-interceptor.ts`) is constructing URLs that result in HTTP protocol:

```typescript
// Line 182 in auth-interceptor.ts
const response = await fetch(url, authConfig);
```

The URL being passed is already `https://api.staging.netrasystems.ai` but somewhere in the request chain, it's being converted to HTTP.

### Issue #2: Backend CORS/Load Balancer Configuration

The GCP Load Balancer or backend service may be:
1. Redirecting HTTPS to HTTP internally
2. Not properly configured for HTTPS termination
3. Missing proper CORS headers for preflight requests

### Issue #3: WebSocket Authentication Flow

WebSocket connections are failing immediately after handshake, suggesting:
1. JWT token not being properly transmitted via subprotocol
2. Backend WebSocket handler rejecting authentication
3. CORS issues with WebSocket upgrade requests

## Recommended Fixes

### Fix 1: Update Frontend API Configuration

**File:** `frontend/lib/unified-api-config.ts`

Ensure staging configuration enforces HTTPS:

```typescript
case 'staging':
  return {
    environment: 'staging',
    urls: {
      api: 'https://api.staging.netrasystems.ai',  // Ensure HTTPS
      websocket: 'wss://api.staging.netrasystems.ai',  // Ensure WSS
      auth: 'https://auth.staging.netrasystems.ai',
      frontend: 'https://app.staging.netrasystems.ai',
    },
    // ... rest of config
  };
```

### Fix 2: Update Auth Interceptor Request Construction

**File:** `frontend/lib/auth-interceptor.ts`

Add explicit HTTPS enforcement:

```typescript
public async authenticatedFetch(
  url: string, 
  config: RequestConfig = {}
): Promise<Response> {
  // Force HTTPS in staging/production
  if (typeof window !== 'undefined' && 
      window.location.protocol === 'https:' && 
      url.startsWith('http://')) {
    url = url.replace('http://', 'https://');
    logger.warn('Forced HTTP to HTTPS upgrade for:', url);
  }
  
  const authConfig = this.applyAuthHeaders(config);
  // ... rest of method
}
```

### Fix 3: Backend CORS Configuration Update

**File:** `shared/cors_config.py`

Ensure staging origins are correctly configured:

```python
def _get_staging_origins() -> List[str]:
    return [
        # Ensure HTTPS for all staging domains
        "https://app.staging.netrasystems.ai",
        "https://auth.staging.netrasystems.ai", 
        "https://api.staging.netrasystems.ai",
        # Remove any HTTP variants for staging
    ]
```

### Fix 4: WebSocket Service Authentication Update

**File:** `frontend/services/webSocketService.ts`

Ensure WebSocket URL uses WSS in staging:

```typescript
private createSecureWebSocket(url: string, options: WebSocketOptions): WebSocket {
  // Force WSS in staging/production
  if (typeof window !== 'undefined' && 
      window.location.protocol === 'https:' && 
      url.startsWith('ws://')) {
    url = url.replace('ws://', 'wss://');
    logger.warn('Forced WS to WSS upgrade for:', url);
  }
  
  const token = options.token;
  // ... rest of method
}
```

### Fix 5: GCP Load Balancer Configuration

**Action Required:** Verify GCP Load Balancer settings
1. Ensure HTTPS termination is properly configured
2. Check backend service protocol settings
3. Verify SSL certificates are properly attached
4. Ensure backend services accept HTTPS connections

### Fix 6: Environment Variable Validation

**File:** `config/staging.env`

Update to ensure HTTPS everywhere:

```env
# API Configuration for Staging - MUST BE HTTPS
API_BASE_URL=https://api.staging.netrasystems.ai
WS_BASE_URL=wss://api.staging.netrasystems.ai
FRONTEND_URL=https://app.staging.netrasystems.ai
AUTH_URL=https://auth.staging.netrasystems.ai

# Enforce HTTPS
FORCE_HTTPS=true
```

## Testing Strategy

### 1. Mixed Content Testing
```bash
# Test API endpoints with HTTPS
curl -H "Authorization: Bearer <token>" https://api.staging.netrasystems.ai/api/threads

# Verify no HTTP redirects
curl -I https://api.staging.netrasystems.ai/health
```

### 2. WebSocket Testing
```javascript
// Test WebSocket connection
const ws = new WebSocket('wss://api.staging.netrasystems.ai/ws', ['Bearer.YOUR_TOKEN_HERE']);
ws.onopen = () => console.log('Connected');
ws.onerror = (e) => console.error('Error:', e);
```

### 3. CORS Testing
```bash
# Test CORS preflight
curl -X OPTIONS https://api.staging.netrasystems.ai/api/threads \
  -H "Origin: https://app.staging.netrasystems.ai" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization"
```

## Deployment Checklist

- [ ] Update frontend configuration to enforce HTTPS
- [ ] Deploy frontend changes to staging
- [ ] Verify GCP Load Balancer HTTPS configuration
- [ ] Update backend CORS configuration if needed
- [ ] Test all API endpoints with HTTPS
- [ ] Test WebSocket connections with WSS
- [ ] Verify authentication flow works end-to-end
- [ ] Run full E2E test suite in staging

## Monitoring

After fixes are deployed, monitor for:
1. Mixed content warnings in browser console
2. WebSocket connection stability
3. API request success rates
4. Authentication token refresh flows

## Priority Actions

1. **IMMEDIATE:** Update frontend to enforce HTTPS URLs (Fix 1 & 2)
2. **HIGH:** Verify GCP Load Balancer configuration (Fix 5)
3. **MEDIUM:** Update WebSocket service for WSS enforcement (Fix 4)
4. **LOW:** Add comprehensive logging for debugging

## Contact for Questions

For infrastructure/GCP configuration: DevOps Team
For frontend fixes: Frontend Team
For backend/CORS issues: Backend Team