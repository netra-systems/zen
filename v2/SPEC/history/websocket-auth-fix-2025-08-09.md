# WebSocket Authentication Fix - 2025-08-09

## Issue Summary

WebSocket connections were failing with a 403 Forbidden error due to multiple configuration and implementation issues.

### Error Messages
```
INFO:     127.0.0.1:65101 - "WebSocket /ws/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." 403
INFO:     connection rejected (403 Forbidden)
ERROR    | app.routes.websockets:websocket_endpoint:33 - Token payload is invalid
```

## Root Causes Identified

### 1. JWT Secret Key Configuration Issue
- **Problem**: The `jwt_secret_key` was set to `None` in the base AppConfig
- **Impact**: All JWT encoding/decoding operations failed, making authentication impossible
- **Location**: `app/schemas/Config.py:139`

### 2. Token Path vs Query Parameter Mismatch
- **Problem**: Frontend was sending token in URL path (`/ws/{token}`), but one WebSocket route expected it as a query parameter (`/ws?token=...`)
- **Impact**: Conflicting implementations and URL encoding issues
- **Locations**: 
  - `app/routes/websockets.py` (expected query param)
  - `app/routes/ws.py` (expected path param - unused file)
  - `frontend/services/webSocketService.ts` (sent as path)
  - `frontend/providers/WebSocketProvider.tsx` (sent as query)

### 3. Token Expiration Configuration
- **Problem**: Token creation was hardcoded to 15 minutes instead of using the configured 30 minutes
- **Impact**: Tokens expired faster than expected
- **Location**: `app/services/security_service.py:31`

### 4. WebSocket Service Dependencies
- **Problem**: Dependency injection doesn't work well with WebSocket endpoints - `get_security_service` expected a Request object
- **Impact**: TypeError when trying to authenticate WebSocket connections
- **Location**: `app/dependencies.py:19`

## Solutions Implemented

### 1. Fixed JWT Secret Key Configuration
```python
# app/schemas/Config.py
class DevelopmentConfig(AppConfig):
    jwt_secret_key: str = "development_secret_key_for_jwt_do_not_use_in_production"
    fernet_key: str = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
```

### 2. Standardized WebSocket Authentication Flow
```python
# app/routes/websockets.py
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    db_session = Depends(get_async_db),
):
    await websocket.accept()
    
    # Get token from query parameters
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="No token provided")
        return
    
    # Get services from app state instead of dependency injection
    app = websocket.app
    security_service = app.state.security_service
    agent_service = app.state.agent_service
```

### 3. Fixed Token Expiration
```python
# app/services/security_service.py
def create_access_token(self, data: schemas.TokenPayload, expires_delta: Optional[timedelta] = None):
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
```

### 4. Updated Frontend WebSocket Service
```typescript
// frontend/services/webSocketService.ts
public async connect(url: string) {
    // Now accepts full URL instead of constructing it
    this.ws = new WebSocket(url);
}
```

## Key Learnings

1. **WebSocket Authentication**: FastAPI WebSocket endpoints have limitations with dependency injection. Direct access to app state is more reliable.

2. **Token Transport**: Query parameters are more suitable than path parameters for WebSocket authentication tokens to avoid URL encoding issues.

3. **Configuration Validation**: Critical security configurations like JWT secrets should have validation to prevent None values at startup.

4. **Error Logging**: Specific error messages for different JWT failure modes (expired vs invalid) greatly help debugging.

## Testing Checklist

- [ ] Backend server restarted with new configuration
- [ ] User logs in to get fresh token with new JWT secret
- [ ] WebSocket connects successfully with token in query parameter
- [ ] Token expiration respects configured 30-minute timeout
- [ ] Error messages are clear when authentication fails

## Related Files Modified

1. `app/schemas/Config.py` - Added JWT secret key to DevelopmentConfig
2. `app/routes/websockets.py` - Fixed WebSocket authentication flow
3. `app/services/security_service.py` - Fixed token expiration and error handling
4. `frontend/services/webSocketService.ts` - Simplified connection logic
5. `CLAUDE.md` - Updated with WebSocket authentication pattern