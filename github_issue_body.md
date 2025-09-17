## 🚨 P0 CRITICAL: Backend Service Cannot Start

### Error Summary
Backend service is failing to start due to missing `auth_service` module imports.

### Error Details
```
ModuleNotFoundError: No module named 'auth_service'
File: /app/netra_backend/app/websocket_core/websocket_manager.py:53
Import: from auth_service.auth_core.core.token_validator import TokenValidator
```

### Business Impact
- **Golden Path:** COMPLETELY BROKEN - Users cannot access system
- **Chat Functionality:** 0% operational - Service won't start
- **Service Availability:** 0% - Cannot initialize

### Root Cause Analysis
The backend service is attempting to import `auth_service` modules directly, but the auth_service package is not available in the backend container. This is an architectural issue where the backend should be using service-to-service communication (HTTP/gRPC) instead of direct imports.

### Immediate Recovery Actions
1. Remove direct imports to `auth_service` from backend
2. Implement proper service-to-service communication
3. Deploy emergency fix to staging

### Affected Files (Import Violations)
- `/app/netra_backend/app/auth/models.py:22` - `from auth_service.auth_core.database.models import`
- `/app/netra_backend/app/websocket_core/websocket_manager.py:53` - `from auth_service.auth_core.core.token_validator import TokenValidator`
- `/app/netra_backend/app/routes/websocket_ssot.py:173` - `from auth_service.auth_core.core.token_validator import TokenValidator`
- `/app/netra_backend/app/auth_integration/auth.py:45` (implied by log patterns)
- `/app/netra_backend/app/middleware/gcp_auth_context_middleware.py` (affected in import chain)

### Log Evidence
**Service:** netra-backend-staging (netra-staging project)
**Error Count:** 84 of 1,000 logs (8.4%)
**Pattern:** Import chain failures across WebSocket, auth, middleware components

### Required Fix
Replace all direct `auth_service` imports with HTTP client calls to auth service API endpoints:
1. **Update Models:** Replace auth_service model imports with local auth integration models
2. **Update WebSocket Manager:** Replace TokenValidator import with HTTP token validation calls
3. **Update Auth Integration:** Use HTTP API for all auth service communication
4. **Update Middleware:** Remove direct auth_service dependencies