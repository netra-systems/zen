# CRITICAL: Unified Auth Service Architecture

## 🔴 MANDATORY: READ THIS FIRST BEFORE ANY AUTH CHANGES

### THE GOLDEN RULE
**There is ONE and ONLY ONE auth service that runs OUTSIDE the main backend.**
- The auth service is a SEPARATE microservice
- The main backend MUST NEVER implement auth logic
- The main backend ONLY integrates via the auth_integration module

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│                    (Next.js Application)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ OAuth Flow / API Calls
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    AUTH SERVICE                              │
│              (STANDALONE MICROSERVICE)                       │
│                                                              │
│  - Runs on separate port (e.g., 8001)                       │
│  - Handles ALL authentication logic                         │
│  - OAuth provider integration                               │
│  - Token generation/validation                              │
│  - Session management                                       │
│  - Located in: app/auth/auth_service.py                    │
└─────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP API Calls
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    MAIN BACKEND                              │
│              (FastAPI Application)                           │
│                                                              │
│  auth_integration/ (ONLY integration point)                 │
│  ├── auth.py - Dependency injection                        │
│  └── Uses auth_client to call auth service                 │
│                                                              │
│  clients/auth_client.py                                     │
│  └── HTTP client to auth service                           │
│                                                              │
│  ⚠️ NEVER implement auth logic here!                        │
└──────────────────────────────────────────────────────────────┘
```

## File Purposes - CRITICAL TO UNDERSTAND

### ✅ CORRECT: Auth Service Files (Separate Microservice)
- `app/auth/auth_service.py` - The ACTUAL auth service (runs independently)
- `app/auth/oauth_utils.py` - OAuth provider integration
- `app/auth/auth_token_service.py` - Token management
- `app/auth/auth_session_manager.py` - Session handling

### ✅ CORRECT: Main Backend Integration Files
- `app/auth_integration/auth.py` - FastAPI dependencies for auth
- `app/clients/auth_client.py` - HTTP client to call auth service
- `app/auth_integration/__init__.py` - Re-exports for convenience

### ❌ WRONG: DO NOT CREATE
- Any auth implementation in the main backend
- Local token validation (except emergency fallback)
- Direct OAuth provider integration in main backend
- User authentication logic in main backend

## Testing Requirements

### Integration Tests (MANDATORY)
All auth-related tests MUST be integration tests that:
1. Start the real auth service (or use a test instance)
2. Make real HTTP calls through auth_client
3. Test the full flow from backend → auth service → backend

### Example Test Pattern
```python
@pytest.mark.integration
async def test_auth_flow():
    # Start auth service on test port
    auth_service = await start_test_auth_service(port=8001)
    
    # Configure auth_client to use test service
    auth_client.settings.base_url = "http://localhost:8001"
    
    # Test real authentication flow
    result = await auth_client.validate_token("test_token")
    assert result is not None
```

### ❌ NEVER Mock These
- auth_client HTTP calls
- Token validation responses
- OAuth flows
- Session management

## Common Mistakes to AVOID

### 1. Recreating Auth Logic
❌ WRONG:
```python
# In main backend
def validate_token(token: str):
    # Implementing validation logic
    payload = jwt.decode(token, secret)
    return payload
```

✅ CORRECT:
```python
# In main backend
async def validate_token(token: str):
    # ONLY call auth service
    return await auth_client.validate_token(token)
```

### 2. Direct Database Access
❌ WRONG:
```python
# In main backend
user = db.query(User).filter(User.email == email).first()
if verify_password(password, user.password_hash):
    # authenticate
```

✅ CORRECT:
```python
# In main backend
result = await auth_client.login(email, password)
if result and result.get("valid"):
    # authenticated via auth service
```

## Development Setup

### Running Both Services
```bash
# Terminal 1: Start Auth Service
python app/auth/auth_service.py
# Runs on http://localhost:8001

# Terminal 2: Start Main Backend
python app/main.py
# Runs on http://localhost:8000
```

### Environment Variables
```env
# Main Backend
AUTH_SERVICE_URL=http://localhost:8001
AUTH_SERVICE_ENABLED=true

# Auth Service
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-secret
JWT_SECRET_KEY=your-jwt-secret
```

## Proxy and Load Balancer Configuration

### Production Architecture
```
Internet → Load Balancer → Auth Service (multiple instances)
                        ↘ Main Backend (multiple instances)
```

### Service Discovery
- Auth service registered as `auth-service` in service mesh
- Main backend discovers via environment variable or service discovery
- Health checks at `/health` endpoint

## Regression Prevention Checklist

Before ANY auth-related changes, verify:
- [ ] You are NOT implementing auth logic in main backend
- [ ] You are using auth_client for ALL auth operations
- [ ] Tests use real auth service (not mocks)
- [ ] No direct database queries for users/sessions in main backend
- [ ] No JWT encoding/decoding in main backend
- [ ] All OAuth redirects go through auth service

## Contact for Questions
If unclear about auth architecture:
1. Read this document again
2. Check `app/clients/auth_client.py` for integration examples
3. Look at existing auth_integration usage
4. NEVER guess - auth security is critical

## Final Warning
**Creating duplicate auth logic in the main backend is a CRITICAL security vulnerability.**
**Always use the unified auth service via auth_client.**