# 🔴 STOP: Critical Auth Architecture Information

## READ THIS BEFORE ANY AUTH-RELATED WORK

### The Most Important Thing to Understand
**There is a SEPARATE auth service that runs OUTSIDE the main backend.**

## What This Means

### ✅ CORRECT Architecture
```
Frontend → Auth Service (port 8001) → Returns tokens
Frontend → Main Backend (port 8000) → Uses tokens from auth service
Main Backend → Auth Service → Validates tokens via HTTP
```

### ❌ WRONG Architecture (NEVER DO THIS)
```
Frontend → Main Backend → Main backend authenticates users directly
Main Backend → Database → Checks passwords locally
```

## Quick Reference

### Auth Service (SEPARATE APPLICATION)
- **Location**: `app/auth/auth_service.py`
- **Port**: 8001
- **Purpose**: ALL authentication logic
- **Database**: Separate auth database
- **What it does**:
  - User registration/login
  - OAuth integration (Google, etc.)
  - Token generation/validation
  - Session management
  - Password management

### Main Backend (THIS APPLICATION)
- **Location**: `app/main.py`
- **Port**: 8000
- **Purpose**: Business logic ONLY
- **Database**: Application database
- **Auth Integration**: `app/auth_integration/`
- **What it does**:
  - Calls auth service via `auth_client`
  - NEVER authenticates directly
  - NEVER touches passwords
  - NEVER generates tokens

## File Guide

### Files You Should Use
- `app/auth_integration/auth.py` - FastAPI auth dependencies
- `app/clients/auth_client.py` - HTTP client to auth service
- `app/db/models_user.py` - User profile data (NOT auth data)

### Files You Should NOT Modify (Auth Service Only)
- `app/auth/auth_service.py` - The actual auth service
- `app/auth/oauth_utils.py` - OAuth provider logic
- `app/auth/auth_token_service.py` - Token management

## Common Tasks

### How to Validate a User Token
```python
# ✅ CORRECT
from app.clients.auth_client import auth_client

result = await auth_client.validate_token(token)
if result and result.get("valid"):
    user_id = result.get("user_id")
```

### How to Login a User
```python
# ✅ CORRECT
from app.clients.auth_client import auth_client

result = await auth_client.login(email, password)
if result:
    token = result.get("access_token")
```

### How to Get Current User in Endpoint
```python
# ✅ CORRECT
from app.auth_integration import ActiveUserDep

@app.get("/api/profile")
async def get_profile(user: ActiveUserDep):
    return {"email": user.email}
```

## Testing Requirements

### All Auth Tests Must:
1. Start a real auth service instance
2. Make real HTTP calls (no mocking)
3. Test the complete flow

### Test Example
```python
@pytest.mark.integration
async def test_auth():
    # Start real auth service
    auth_service = await start_test_auth_service()
    
    # Test with real calls
    result = await auth_client.login("test@example.com", "password")
    assert result is not None
```

## Development Setup

### Start Both Services
```bash
# Terminal 1: Auth Service
python app/auth/auth_service.py

# Terminal 2: Main Backend
python app/main.py

# Terminal 3: Frontend
cd frontend && npm run dev
```

## Red Flags (Things That Should Never Happen)

If you see any of these, STOP and reconsider:
- Importing `bcrypt` or `jwt` in main backend
- Direct database queries for user passwords
- Creating login/register endpoints in main backend
- Mocking `auth_client` in tests
- Adding auth logic to `app/main.py`

## More Information

### Detailed Documentation
- `app/auth_integration/CRITICAL_AUTH_ARCHITECTURE.md` - Complete architecture
- `app/tests/auth/AUTH_TEST_REQUIREMENTS.md` - Testing guide
- `app/db/AUTH_DATABASE_ARCHITECTURE.md` - Database separation
- `PROXY_AND_AUTH_ARCHITECTURE.md` - Infrastructure setup

## Questions?

If anything is unclear:
1. Read this document again
2. Check the detailed documentation above
3. Look at existing code in `app/auth_integration/`
4. NEVER guess - auth security is critical

---

**Remember: The auth service is SEPARATE. The main backend only INTEGRATES with it.**