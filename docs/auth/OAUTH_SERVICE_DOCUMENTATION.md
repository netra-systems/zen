# Netra Apex OAuth Service Architecture - Complete Guide for Junior Engineers

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Core Authentication Concepts](#core-authentication-concepts)
3. [OAuth Service Architecture](#oauth-service-architecture)
4. [Token Exchange Flow](#token-exchange-flow)
5. [JWT Implementation Details](#jwt-implementation-details)
6. [Development vs Production Configuration](#development-vs-production-configuration)
7. [API Integration Points](#api-integration-points)
8. [Security Best Practices](#security-best-practices)
9. [Troubleshooting Guide](#troubleshooting-guide)

## Executive Summary

The Netra Apex platform uses a **unified, dedicated OAuth service** for all authentication and authorization needs. This service provides:

- **Centralized Authentication**: Single source of truth for user authentication across all services
- **OAuth 2.0 + OpenID Connect**: Industry-standard protocol for secure authentication
- **JWT Tokens**: Stateless, secure token-based authentication
- **Multi-Environment Support**: Seamless configuration across dev, staging, and production
- **Google OAuth Integration**: Primary authentication method via Google accounts

## Core Authentication Concepts

### Authentication vs Authorization

**Authentication** answers: "Who are you?"
- Verifying user identity through credentials (username/password, OAuth tokens)
- Establishing that a user is who they claim to be

**Authorization** answers: "What can you do?"
- Determining what resources/actions an authenticated user can access
- Based on roles, permissions, and policies

### OAuth 2.0 Basics

OAuth 2.0 is an authorization framework that enables applications to obtain limited access to user accounts. Key components:

1. **Resource Owner**: The user who owns the data
2. **Client**: The application requesting access (Netra Apex frontend)
3. **Authorization Server**: Google's OAuth server
4. **Resource Server**: Netra Apex backend API

### JWT (JSON Web Tokens) Basics

JWTs are self-contained tokens that carry user information. Structure:

```
header.payload.signature
```

- **Header**: Token type and signing algorithm
- **Payload**: User data and claims
- **Signature**: Ensures token integrity

## OAuth Service Architecture

### Directory Structure

```
app/
├── auth_integration/        # Shared auth service integration
│   ├── __init__.py
│   └── auth.py             # FastAPI dependency injection for auth
├── clients/
│   └── auth_client.py      # Auth service client with caching & circuit breaker
├── routes/auth/
│   └── auth.py             # OAuth endpoints and callback handlers
└── services/
    ├── security_service.py  # JWT creation and validation
    └── key_manager.py       # Cryptographic key management
```

### Key Components

#### 1. AuthServiceClient (`app/clients/auth_client.py`)

The central client for all auth operations:

```python
class AuthServiceClient:
    def __init__(self):
        self.base_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
        self.enabled = os.getenv("AUTH_SERVICE_ENABLED", "true").lower() == "true"
        self.cache_ttl = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "300"))
        self.circuit_breaker = CircuitBreaker()
        self._token_cache: Dict[str, CachedToken] = {}
```

**Features:**
- Token validation with 5-minute caching
- Circuit breaker pattern for resilience
- Automatic failover to local validation
- Environment-aware configuration

#### 2. Auth Integration Module (`app/auth_integration/auth.py`)

FastAPI dependency injection for protected routes:

```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    token = credentials.credentials
    validation_result = await auth_client.validate_token(token)
    # ... user lookup and validation
```

#### 3. OAuth Route Handler (`app/routes/auth/auth.py`)

Manages OAuth flow and callbacks:

```python
@router.get("/login")
async def login(request: Request):
    # Initiates OAuth flow with Google
    
@router.get("/callback")
async def callback(request: Request):
    # Handles OAuth callback from Google
```

## Token Exchange Flow

### Complete OAuth Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant AuthService
    participant Google
    
    User->>Frontend: Click "Login with Google"
    Frontend->>Backend: GET /api/auth/login
    Backend->>Backend: Get OAuth config for environment
    Backend->>Frontend: Redirect to Google OAuth
    Frontend->>Google: Authorization request
    User->>Google: Approve permissions
    Google->>Frontend: Redirect with auth code
    Frontend->>Backend: GET /api/auth/callback?code=xyz
    Backend->>Google: Exchange code for tokens
    Google->>Backend: Return access_token + id_token
    Backend->>Backend: Extract user info from id_token
    Backend->>AuthService: Validate/create user
    Backend->>Backend: Create JWT token
    Backend->>Frontend: Redirect with JWT
    Frontend->>Frontend: Store JWT in localStorage
```

### Token Validation Flow

```python
# 1. Client sends request with Bearer token
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

# 2. Backend validates token
async def validate_token(token: str):
    # Check cache first
    if cached := self._get_cached_token(token):
        return cached
    
    # Remote validation with circuit breaker
    result = await self.circuit_breaker.call(
        self._validate_token_remote, token
    )
    
    # Cache valid tokens
    if result:
        self._cache_token(token, result)
    
    return result

# 3. Fallback to local validation if service down
if auth_service_unavailable:
    return await self._local_validate(token)
```

## JWT Implementation Details

### Token Creation

```python
def create_access_token(self, data: TokenPayload, expires_delta: Optional[timedelta] = None):
    to_encode = data.model_dump()
    current_time = datetime.now(UTC)
    
    # Standard JWT claims
    to_encode.update({
        "exp": expire,              # Expiration time
        "iat": current_time,        # Issued at
        "nbf": current_time,        # Not before
        "jti": secrets.token_hex(16), # JWT ID for blacklisting
        "iss": "netra-auth-service",  # Issuer
        "aud": "netra-api",           # Audience
        "sub": str(user.id)           # Subject (user ID)
    })
    
    # Sign with secret key
    encoded_jwt = jwt.encode(
        to_encode, 
        self.key_manager.jwt_secret_key, 
        algorithm="HS256"
    )
    return encoded_jwt
```

### Token Validation

```python
def decode_access_token(self, token: str) -> Optional[dict]:
    payload = jwt.decode(
        token, 
        self.key_manager.jwt_secret_key, 
        algorithms=["HS256"],
        audience="netra-api",        # Must match creation
        issuer="netra-auth-service", # Must match creation
        options={
            "verify_exp": True,       # Check expiration
            "verify_iat": True,       # Check issued at
            "verify_nbf": True,       # Check not before
            "verify_aud": True,       # Check audience
            "verify_iss": True,       # Check issuer
            "verify_signature": True  # Verify signature
        }
    )
    
    # Additional security: max token age 24 hours
    if (current_timestamp - iat_timestamp) > 86400:
        raise TokenTooOldError()
    
    return payload
```

## Development vs Production Configuration

### Environment Detection

The system automatically detects the environment:

```python
def detect_environment(self) -> Environment:
    # 1. Check explicit override
    if env_override := os.getenv("ENVIRONMENT"):
        return self._parse_environment(env_override)
    
    # 2. Check testing flag
    if os.getenv("TESTING") in ["true", "1"]:
        return Environment.TESTING
    
    # 3. Check Cloud Run variables
    if k_service := os.getenv("K_SERVICE"):
        if "prod" in k_service.lower():
            return Environment.PRODUCTION
        if "staging" in k_service.lower():
            return Environment.STAGING
    
    # 4. Default to development
    return Environment.DEVELOPMENT
```

### Environment-Specific OAuth Configuration

#### Development Environment

```python
OAuthConfig(
    client_id="dev_client_id",
    client_secret="dev_secret",
    redirect_uris=[
        "http://localhost:8000/api/auth/callback",
        "http://localhost:3000/api/auth/callback",
        "http://localhost:3010/api/auth/callback"
    ],
    javascript_origins=[
        "http://localhost:3000",
        "http://localhost:3010",
        "http://localhost:8000"
    ],
    allow_dev_login=True,      # Enable dev login endpoint
    allow_mock_auth=True,      # Allow mock authentication
    use_proxy=False
)
```

#### Staging Environment

```python
OAuthConfig(
    client_id="staging_client_id",
    client_secret="staging_secret",
    redirect_uris=[
        "https://app.staging.netrasystems.ai/api/auth/callback",
        "https://app.staging.netrasystems.ai/callback"
    ],
    javascript_origins=[
        "https://app.staging.netrasystems.ai",
        "https://app.staging.netrasystems.ai"
    ],
    allow_dev_login=False,
    allow_mock_auth=False,
    use_proxy=False  # True for PR environments
)
```

#### Production Environment

```python
OAuthConfig(
    client_id="prod_client_id",
    client_secret="prod_secret",
    redirect_uris=[
        "https://api.netrasystems.ai/api/auth/callback",
        "https://netrasystems.ai/callback"
    ],
    javascript_origins=[
        "https://netrasystems.ai",
        "https://api.netrasystems.ai"
    ],
    allow_dev_login=False,
    allow_mock_auth=False,
    use_proxy=False
)
```

### Key Differences by Environment

| Feature | Development | Staging | Production |
|---------|------------|---------|------------|
| Protocol | HTTP | HTTPS | HTTPS |
| Dev Login | ✅ Enabled | ❌ Disabled | ❌ Disabled |
| Mock Auth | ✅ Enabled | ❌ Disabled | ❌ Disabled |
| Token Cache | 5 minutes | 5 minutes | 5 minutes |
| Circuit Breaker | 5 failures/60s | 5 failures/60s | 5 failures/60s |
| JWT Expiry | 30 minutes | 30 minutes | 30 minutes |
| CORS Origins | localhost:* | staging.* | netrasystems.ai |

## API Integration Points

### Protected Route Example

```python
from app.auth_integration.auth import ActiveUserDep

@router.get("/protected")
async def protected_endpoint(user: ActiveUserDep):
    """
    This endpoint requires authentication.
    ActiveUserDep automatically:
    1. Extracts Bearer token from header
    2. Validates token with auth service
    3. Loads user from database
    4. Returns 401 if invalid
    """
    return {"message": f"Hello {user.email}"}
```

### Admin-Only Route

```python
from app.auth_integration.auth import AdminDep

@router.post("/admin/action")
async def admin_action(admin: AdminDep):
    """
    Requires admin permissions.
    AdminDep checks:
    1. User is authenticated
    2. User has is_admin=True
    3. Returns 403 if not admin
    """
    return {"status": "Admin action performed"}
```

### Optional Authentication

```python
from app.auth_integration.auth import OptionalUserDep

@router.get("/public")
async def public_endpoint(user: OptionalUserDep):
    """
    Works with or without authentication.
    Returns None if not authenticated.
    """
    if user:
        return {"message": f"Welcome {user.email}"}
    return {"message": "Welcome guest"}
```

## Security Best Practices

### 1. Token Security

- **Never log tokens**: Tokens contain sensitive data
- **Use HTTPS in production**: Prevents token interception
- **Short expiration times**: 30-minute default
- **Token rotation**: Refresh tokens before expiry

### 2. Secret Management

```python
# NEVER hardcode secrets
BAD: jwt_secret = "my-secret-key"

# ALWAYS use environment variables
GOOD: jwt_secret = os.getenv("JWT_SECRET_KEY")

# Use secret managers in production
BEST: jwt_secret = secret_manager.get_secret("jwt-secret")
```

### 3. Circuit Breaker Pattern

Prevents cascading failures:

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout_seconds=60):
        # After 5 failures, circuit opens for 60 seconds
        # Prevents hammering a down service
```

### 4. Token Caching

Reduces auth service load:

```python
class CachedToken:
    def __init__(self, data: Dict, ttl_seconds: int):
        self.data = data
        self.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    
    def is_valid(self) -> bool:
        return datetime.utcnow() < self.expires_at
```

## Troubleshooting Guide

### Common Issues

#### 1. "OAuth credentials not configured"

**Cause**: Missing Google OAuth client ID/secret
**Solution**: 
```bash
# Check environment variables
echo $GOOGLE_OAUTH_CLIENT_ID_DEV
echo $GOOGLE_OAUTH_CLIENT_SECRET_DEV

# Set if missing
export GOOGLE_OAUTH_CLIENT_ID_DEV="your-client-id"
export GOOGLE_OAUTH_CLIENT_SECRET_DEV="your-secret"
```

#### 2. "Redirect URI mismatch"

**Cause**: Callback URL not in Google OAuth allowed list
**Solution**: 
1. Go to Google Cloud Console
2. Navigate to APIs & Services > Credentials
3. Edit OAuth 2.0 Client
4. Add redirect URI to "Authorized redirect URIs"

#### 3. "Invalid or expired token"

**Cause**: Token expired (30 min) or auth service down
**Debug**:
```python
# Check token expiration
import jwt
decoded = jwt.decode(token, options={"verify_signature": False})
print(f"Expires: {decoded['exp']}")
print(f"Current: {datetime.now().timestamp()}")
```

#### 4. "Circuit breaker is open"

**Cause**: Auth service experienced 5+ failures
**Solution**: 
- Wait 60 seconds for circuit to close
- Check auth service health: `curl http://localhost:8081/health`
- Check logs for underlying issue

### Debug Commands

```bash
# Test auth service connectivity
curl -X POST http://localhost:8081/auth/validate \
  -H "Content-Type: application/json" \
  -d '{"token": "your-jwt-token"}'

# Decode JWT without validation (debugging only!)
echo "your-jwt-token" | cut -d. -f2 | base64 -d

# Check environment
python -c "from app.clients.auth_client import auth_client; print(auth_client.detect_environment())"

# Test OAuth config
python -c "from app.clients.auth_client import auth_client; print(auth_client.get_oauth_config())"
```

### Logging

Key log locations for debugging:

```python
# Auth client logs
logger = logging.getLogger("app.clients.auth_client")

# OAuth route logs  
logger = logging.getLogger("app.routes.auth.auth")

# Security service logs
logger = logging.getLogger("app.services.security_service")
```

Enable debug logging:
```python
logging.getLogger("app.clients.auth_client").setLevel(logging.DEBUG)
```

## Summary

The Netra Apex OAuth service provides:

1. **Unified Authentication**: Single service for all auth needs
2. **Environment Flexibility**: Automatic configuration per environment
3. **Security First**: JWT validation, circuit breakers, token caching
4. **Developer Friendly**: Clear dependency injection, good error messages
5. **Production Ready**: Resilient patterns, proper secret management

Remember: Authentication verifies identity, authorization controls access, and our OAuth service handles both seamlessly across all environments.