# Authentication Flow Documentation

## Overview
Netra uses JWT-based authentication with Google OAuth for production and auto-login for development mode.

## Token Management

### Storage
- **Token Key**: `jwt_token` (consistent across all components)
- **Storage Location**: localStorage
- **Token Format**: Standard JWT containing user info (id, email, etc.)

### Token Usage
- **HTTP Requests**: Bearer token in Authorization header
- **WebSocket**: Token passed as query parameter on connection

## Development Mode Authentication

### Auto-Login Flow
1. On page load, check for existing JWT token
2. If token exists and is valid → use it (maintain session)
3. If no token exists:
   - Check for `dev_logout_flag` in localStorage
   - If flag exists → DO NOT auto-login (user explicitly logged out)
   - If no flag → auto-login with dev user (email: dev@example.com)

### Logout Persistence
- When user logs out in dev mode, set `dev_logout_flag = true`
- This prevents auto-login on next page load
- Flag is cleared when user manually logs in (OAuth or dev login)

### Testing OAuth in Dev Mode
- User can explicitly logout to test OAuth flow
- System will not auto-login after explicit logout
- User can click "Login with Google" to test OAuth
- After successful OAuth login, dev_logout_flag is cleared

## Production Mode Authentication

### OAuth Flow
1. User clicks "Login with Google"
2. Redirected to `/api/auth/login` endpoint
3. Backend redirects to Google OAuth consent screen
4. Google redirects back to `/api/auth/callback`
5. Backend:
   - Validates OAuth token
   - Creates/updates user in database
   - Generates JWT token
   - Redirects to frontend with token
6. Frontend:
   - Stores token in localStorage
   - Decodes token to get user info
   - Establishes WebSocket connection with token

### Logout Flow
1. User clicks logout
2. Frontend calls `/api/auth/logout` endpoint
3. Token removed from localStorage
4. User redirected to home page
5. WebSocket connection closed

## Frontend Components

### AuthContext/Provider
- Primary authentication state management
- Handles token validation and storage
- Manages auto-login logic for dev mode
- Provides auth methods (login, logout)

### authStore (Zustand)
- Optional global state for auth
- Synchronized with AuthContext
- Uses same `jwt_token` key for localStorage

### authService
- Handles all auth API calls
- Manages localStorage operations
- Provides token helper methods
- Manages dev_logout_flag

## Security Considerations

1. **Token Validation**:
   - Frontend validates token with jwt-decode
   - Invalid/expired tokens automatically removed
   - Backend validates token on every request

2. **CORS Configuration**:
   - Authorized origins configured in backend
   - Includes production and development URLs

3. **OAuth Security**:
   - Using Google OAuth with OIDC
   - Client secret stored securely on backend
   - Redirect URIs whitelisted

## Testing Authentication

### Development Mode Testing
```bash
# Test auto-login
1. Clear localStorage
2. Refresh page → should auto-login

# Test logout persistence
1. Click logout in dev mode
2. Refresh page → should NOT auto-login
3. Click login → should login successfully

# Test OAuth in dev
1. Logout in dev mode
2. Click "Login with Google"
3. Complete OAuth flow
4. Verify token stored and user logged in
```

### Production Mode Testing
```bash
# Test OAuth login
1. Access app without token
2. Click "Login with Google"
3. Complete OAuth flow
4. Verify redirect and token storage

# Test token persistence
1. Login successfully
2. Refresh page
3. Should remain logged in

# Test logout
1. Click logout
2. Verify token removed
3. Verify redirect to home
```

## Common Issues & Solutions

### Issue: Token Storage Inconsistency
**Solution**: All components now use `jwt_token` as the localStorage key

### Issue: Dev Mode Auto-Login After Logout
**Solution**: Implemented `dev_logout_flag` to track explicit logouts

### Issue: WebSocket Authentication Failure
**Solution**: Token passed as query parameter, validated on connection

### Issue: OAuth Redirect Loop
**Solution**: Ensure redirect URIs match configuration exactly

## API Endpoints

- `GET /api/auth/config` - Get auth configuration
- `GET /api/auth/login` - Initiate OAuth login
- `GET /api/auth/callback` - OAuth callback handler
- `POST /api/auth/logout` - Logout user
- `POST /api/auth/dev_login` - Dev mode login
- `POST /api/auth/token` - Get JWT token (form-based auth)