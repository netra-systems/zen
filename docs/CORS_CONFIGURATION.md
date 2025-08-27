# CORS Configuration Guide

## Overview

Cross-Origin Resource Sharing (CORS) configuration is standardized across all Netra services using the unified `shared/cors_config.py` module. This ensures consistent CORS handling between frontend and backend components across all environments.

## Architecture

All services use the centralized CORS configuration:

```
shared/cors_config.py → {netra_backend, auth_service}
```

This Single Source of Truth (SSOT) approach ensures:
- Consistent origin whitelisting across services
- Environment-aware configuration
- Unified debugging and monitoring

## Environment-Specific Configuration

### Development
- **Purpose**: Maximum compatibility for local development
- **Origins**: Extensive localhost variations including Docker containers
- **Features**:
  - HTTP/HTTPS on common development ports (3000, 3001, 8000, 8080, 5173, 4200)
  - IPv4 and IPv6 localhost variants
  - Docker service names and bridge network IPs
  - Container name patterns

### Staging
- **Purpose**: Production-like testing with development flexibility
- **Origins**: Staging domains + development origins for testing
- **Features**:
  - `*.staging.netrasystems.ai` domains
  - Cloud Run URL patterns
  - Local development support for staging testing

### Production
- **Purpose**: Strict security with verified domains only
- **Origins**: Official production domains
- **Features**:
  - `netrasystems.ai` and subdomains only
  - No wildcard origins for security

## Required Headers

### Request Headers Allowed
- `Authorization` - Authentication tokens
- `Content-Type` - Request content type
- `X-Request-ID` - Request tracing
- `X-Trace-ID` - Distributed tracing
- `Accept` - Response format preference
- `Origin` - Request origin (required for CORS)
- `Referer` - Referring page
- `X-Requested-With` - AJAX request identification

### Response Headers Exposed
- `X-Trace-ID` - For request tracing
- `X-Request-ID` - For debugging
- `Content-Length` - Response size
- `Content-Type` - Response format

## Cross-Origin Requests

### Preflight Requests (OPTIONS)
- Automatically handled by FastAPI CORSMiddleware
- Returns allowed methods, headers, and max-age
- Credentials are allowed for authenticated requests

### Allowed Methods
- `GET` - Data retrieval
- `POST` - Data creation
- `PUT` - Data updates  
- `DELETE` - Data deletion
- `PATCH` - Partial updates
- `OPTIONS` - Preflight requests
- `HEAD` - Headers-only requests

## Testing CORS Locally

### 1. Verify Configuration
```bash
# Check backend CORS config
curl http://localhost:8000/health/cors/test

# Check auth service CORS config  
curl http://localhost:8081/cors/test
```

### 2. Test Preflight Request
```bash
curl -X OPTIONS \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization" \
  http://localhost:8000/api/some-endpoint
```

### 3. Test Actual Cross-Origin Request
```javascript
// From http://localhost:3000
fetch('http://localhost:8000/api/health', {
  method: 'GET',
  credentials: 'include', // Important for authentication
  headers: {
    'Content-Type': 'application/json'
  }
})
```

## Common CORS Errors and Fixes

### 1. "Access-Control-Allow-Origin" missing
**Error**: `No 'Access-Control-Allow-Origin' header is present`

**Causes**:
- Origin not in allowed origins list
- CORS middleware not properly configured
- Server error preventing CORS headers

**Fix**:
- Check origin is in `shared/cors_config.py` for your environment
- Verify CORS middleware is added to FastAPI app
- Check server logs for errors

### 2. Credentials blocked
**Error**: `Credentials flag is 'true', but CORS does not allow credentials`

**Causes**:  
- Using wildcard origin (`*`) with credentials
- Origin not properly whitelisted

**Fix**:
- Ensure specific origins are listed instead of wildcards
- Add your origin to the appropriate environment configuration

### 3. Method not allowed
**Error**: `Method POST is not allowed by Access-Control-Allow-Methods`

**Causes**:
- HTTP method not in allowed methods list
- Preflight request failing

**Fix**:
- Verify method is in `allow_methods` configuration
- Check preflight request succeeds first

### 4. Headers not allowed
**Error**: `Request header 'X-Custom-Header' is not allowed`

**Causes**:
- Custom header not in `allow_headers` list
- Preflight validation failing

**Fix**:
- Add header to `allow_headers` in shared CORS config
- Test preflight request independently

## Environment Variables

### Override Configuration
```bash
# Override allowed origins (comma-separated)
CORS_ORIGINS="http://localhost:3000,https://app.example.com"

# Environment detection
ENVIRONMENT=development  # or staging, production
```

### Service-Specific Variables
```bash
# Backend service
NETRA_ENV=development

# Auth service  
AUTH_ENV=development
```

## Static Assets and CDN

Static assets (fonts, images, scripts) are served with appropriate CORS headers:

- Font files: `Access-Control-Allow-Origin: *`
- Images: Origin-specific headers
- Scripts: Strict origin validation

For CDN usage, ensure:
1. CDN URLs are added to staging/production origins
2. Cache headers don't interfere with CORS
3. Static asset paths are configured correctly

## WebSocket CORS

WebSocket connections use the same origin validation as HTTP requests but are handled separately by `WebSocketCORSHandler`.

### Configuration
- Same origins as HTTP CORS
- Validated during WebSocket handshake
- Environment-aware security levels

### Testing WebSocket CORS
```javascript
// Test WebSocket connection from allowed origin
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => console.log('WebSocket connected');
ws.onerror = (error) => console.log('WebSocket error:', error);
```

## Monitoring and Debugging

### Health Endpoints
- Backend: `GET /health/cors/test`
- Auth Service: `GET /cors/test`

### Response Format
```json
{
  "service": "netra-backend",
  "version": "1.0.0", 
  "cors_status": "configured",
  "environment": "development",
  "origins_count": 45,
  "allow_credentials": true,
  "config_valid": true,
  "cors_env_override": false
}
```

### Logging
CORS configuration is logged at service startup:
- Origin count per environment
- Credentials setting
- First few origins for verification

## Security Considerations

### Development
- Permissive origins for flexibility
- Localhost variations supported
- Docker container compatibility

### Staging  
- Production domains + development origins
- Testing production-like restrictions
- Cloud Run pattern validation

### Production
- Strict origin whitelisting
- No wildcard patterns
- Minimal attack surface

### Best Practices
1. Never use wildcard (`*`) origins with credentials
2. Regularly audit allowed origins
3. Remove unused development origins from production
4. Monitor CORS errors in production logs
5. Test CORS changes in staging first

## Troubleshooting Checklist

1. **Verify service is running**: Check service health endpoints
2. **Check origin format**: Must match exactly (protocol, domain, port)
3. **Validate environment**: Ensure correct environment is detected
4. **Test preflight**: OPTIONS request should succeed first
5. **Check credentials**: Ensure `credentials: 'include'` is set correctly
6. **Review server logs**: Look for CORS-related errors or warnings
7. **Verify middleware order**: CORS middleware should be added early
8. **Test with curl**: Isolate browser-specific issues

For additional support, check the service logs and health endpoints for detailed CORS configuration information.