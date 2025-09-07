# Interservice Authentication Architecture

## Overview

This document provides comprehensive documentation of the authentication architecture in the Netra platform, focusing on how the backend service delegates authentication responsibilities to the dedicated auth service. The architecture follows a **Single Source of Truth (SSOT)** principle where the auth service is the canonical authority for all authentication and authorization decisions.

## Core Principles

1. **SSOT Compliance**: Auth service is the single source of truth for all JWT operations
2. **Service Delegation**: Backend delegates ALL authentication to auth service
3. **No Local Validation**: Backend NEVER validates JWTs locally (security requirement)
4. **Caching Strategy**: Token validation results are cached for performance
5. **Circuit Breaker**: Protects against auth service failures
6. **Service-to-Service Auth**: Uses SERVICE_ID and SERVICE_SECRET headers

## Authentication Flow Overview

```mermaid
graph TB
    subgraph "Client Layer"
        Client[Web Client]
        Mobile[Mobile App]
    end
    
    subgraph "Backend Service"
        API[API Endpoint]
        MW[Auth Middleware]
        AC[Auth Client]
        Cache[Token Cache]
        CB[Circuit Breaker]
    end
    
    subgraph "Auth Service"
        Val[Token Validator]
        JWT[JWT Handler]
        DB[(User Database)]
        BL[Blacklist Store]
    end
    
    Client -->|Bearer Token| API
    Mobile -->|Bearer Token| API
    API --> MW
    MW --> AC
    AC --> Cache
    Cache -->|Miss| CB
    CB -->|Protected Call| Val
    Val --> JWT
    JWT --> DB
    JWT --> BL
    Val -->|Validation Result| CB
    CB -->|Result| Cache
    Cache -->|Cached Result| AC
    AC -->|User Context| MW
    MW -->|Authorized| API
```

## Detailed Authentication Delegation Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant BE as Backend Service
    participant MW as Auth Middleware
    participant AC as Auth Client
    participant TC as Token Cache
    participant CB as Circuit Breaker
    participant AS as Auth Service
    
    C->>BE: Request with Bearer Token
    BE->>MW: Process Request
    MW->>MW: Extract Token from Header
    MW->>AC: validate_token(token)
    
    Note over AC: Check if auth service enabled
    AC->>TC: get_cached_token(token)
    
    alt Cache Hit & Valid
        TC-->>AC: Return cached result
        AC-->>MW: Return user context
    else Cache Miss or Expired
        AC->>CB: Call with circuit breaker
        CB->>CB: Check circuit state
        
        alt Circuit Closed
            CB->>AS: POST /auth/validate
            Note over AS: X-Service-ID: netra-backend
            Note over AS: X-Service-Secret: [secret]
            AS->>AS: Validate service credentials
            AS->>AS: Decode & verify JWT
            AS->>AS: Check blacklist
            AS->>AS: Check expiration
            AS-->>CB: Validation result
            CB-->>AC: Return result
            AC->>TC: cache_token(token, result)
            AC-->>MW: Return user context
        else Circuit Open
            CB-->>AC: Circuit breaker open error
            AC->>TC: Check for stale cache
            alt Stale cache available
                TC-->>AC: Return stale result (degraded)
                AC-->>MW: Return with warning
            else No cache
                AC-->>MW: Authentication failed
            end
        end
    end
    
    MW->>MW: Set request context
    MW->>BE: Continue to handler
    BE-->>C: Response
```

## Service-to-Service Authentication

```mermaid
graph LR
    subgraph "Backend Service"
        AC[Auth Client]
        Config[Configuration]
    end
    
    subgraph "Request Headers"
        SID[X-Service-ID]
        SEC[X-Service-Secret]
        AUTH[Authorization]
        TRACE[X-Trace-ID]
    end
    
    subgraph "Auth Service"
        SV[Service Validator]
        TV[Token Validator]
    end
    
    Config -->|SERVICE_ID| AC
    Config -->|SERVICE_SECRET| AC
    AC -->|Inject| SID
    AC -->|Inject| SEC
    AC -->|Forward| AUTH
    AC -->|Generate| TRACE
    
    SID --> SV
    SEC --> SV
    SV -->|Validate Service| TV
    AUTH --> TV
    TV -->|Combined Validation| Response[Response]
```

## JWT Validation Process (Auth Service Internal)

```mermaid
flowchart TD
    Start([Token Validation Request])
    
    ValidateService{Validate<br/>Service Credentials}
    Start --> ValidateService
    
    ValidateService -->|Invalid| ServiceError[Return 403:<br/>Invalid Service]
    ValidateService -->|Valid| ExtractToken
    
    ExtractToken[Extract JWT Token]
    ExtractToken --> CheckBlacklist
    
    CheckBlacklist{Token<br/>Blacklisted?}
    CheckBlacklist -->|Yes| BlacklistError[Return 401:<br/>Token Blacklisted]
    CheckBlacklist -->|No| DecodeJWT
    
    DecodeJWT[Decode JWT<br/>with Secret]
    DecodeJWT --> VerifySignature
    
    VerifySignature{Signature<br/>Valid?}
    VerifySignature -->|No| SignatureError[Return 401:<br/>Invalid Signature]
    VerifySignature -->|Yes| CheckExpiry
    
    CheckExpiry{Token<br/>Expired?}
    CheckExpiry -->|Yes| ExpiryError[Return 401:<br/>Token Expired]
    CheckExpiry -->|No| LoadUser
    
    LoadUser[Load User<br/>from Database]
    LoadUser --> UserExists
    
    UserExists{User<br/>Exists?}
    UserExists -->|No| UserError[Return 401:<br/>User Not Found]
    UserExists -->|Yes| BuildResponse
    
    BuildResponse[Build Validation<br/>Response]
    BuildResponse --> Success([Return 200:<br/>Valid Token])
    
    style ServiceError fill:#f96
    style BlacklistError fill:#f96
    style SignatureError fill:#f96
    style ExpiryError fill:#f96
    style UserError fill:#f96
    style Success fill:#9f6
```

## Token Caching Strategy

```mermaid
graph TB
    subgraph "Cache Layers"
        L1[User-Scoped Cache]
        L2[Token Validation Cache]
        TTL[TTL Management]
    end
    
    subgraph "Cache Operations"
        Get[Cache Get]
        Set[Cache Set]
        Inv[Cache Invalidate]
    end
    
    subgraph "Cache Keys"
        UK[user:{user_id}]
        TK[validated_token:{token}]
        BK[blacklist:{token}]
    end
    
    Get --> L1
    Get --> L2
    L1 --> UK
    L2 --> TK
    L2 --> BK
    
    Set --> TTL
    TTL -->|5 min default| L1
    TTL -->|Token TTL - 60s| L2
    
    Inv -->|Logout| L1
    Inv -->|Blacklist| L2
    Inv -->|Refresh| L2
```

## Circuit Breaker States and Transitions

```mermaid
stateDiagram-v2
    [*] --> Closed: Initial State
    
    Closed --> Open: Failure Threshold Reached<br/>(3 consecutive failures)
    Closed --> Closed: Success
    Closed --> Closed: Single Failure
    
    Open --> HalfOpen: After Recovery Timeout<br/>(10 seconds)
    Open --> Open: Request Rejected
    
    HalfOpen --> Closed: Success Threshold Met<br/>(1 success)
    HalfOpen --> Open: Any Failure
    
    note right of Open: All requests fail fast<br/>No auth service calls
    note right of HalfOpen: Limited requests allowed<br/>Testing recovery
    note right of Closed: Normal operation<br/>All requests forwarded
```

## Timing and Performance Expectations

```mermaid
gantt
    title Token Validation Timeline
    dateFormat X
    axisFormat %L
    
    section Cache Hit
    Check Cache           :done, cache1, 0, 5
    Return Cached Result  :done, cache2, 5, 10
    
    section Cache Miss (Success)
    Check Cache           :done, miss1, 0, 5
    Circuit Breaker Check :done, miss2, 5, 10
    Service Auth Headers  :done, miss3, 10, 15
    Network Call to Auth  :active, miss4, 15, 100
    JWT Validation        :active, miss5, 100, 120
    Database Lookup       :active, miss6, 120, 140
    Response Processing   :done, miss7, 140, 145
    Cache Result          :done, miss8, 145, 150
    
    section Circuit Open
    Check Cache           :done, open1, 0, 5
    Circuit Check (Open)  :crit, open2, 5, 10
    Stale Cache Lookup    :done, open3, 10, 15
    Return Degraded       :done, open4, 15, 20
```

### Performance Targets

| Operation | Target | Maximum | Notes |
|-----------|--------|---------|-------|
| Cache Hit | < 5ms | 10ms | In-memory lookup |
| Cache Miss (Success) | < 150ms | 200ms | Full auth service call |
| Circuit Open (Stale Cache) | < 20ms | 30ms | Degraded mode |
| Circuit Open (No Cache) | < 10ms | 15ms | Fast failure |
| Token Refresh | < 200ms | 300ms | New token generation |
| WebSocket Auth | < 100ms | 150ms | Initial connection |

## WebSocket Authentication Flow

```mermaid
sequenceDiagram
    participant C as WebSocket Client
    participant WS as WebSocket Handler
    participant TRH as Token Refresh Handler
    participant AC as Auth Client
    participant AS as Auth Service
    
    C->>WS: Connect with Token
    WS->>TRH: initialize_connection(ws, token)
    TRH->>AC: validate_token(token)
    AC->>AS: POST /auth/validate
    AS-->>AC: Validation result
    AC-->>TRH: User context
    TRH->>TRH: Store connection info
    TRH->>TRH: Start auto-refresh monitor
    TRH-->>WS: Connection established
    WS-->>C: Connected
    
    loop Every 30 seconds
        TRH->>AC: Check token expiry
        alt Token expires in < 5 min
            TRH->>AC: refresh_token(token)
            AC->>AS: POST /auth/refresh
            AS-->>AC: New token
            AC-->>TRH: New token
            TRH->>C: token_refreshed event
            C->>C: Store new token
        end
    end
    
    C->>WS: Disconnect
    WS->>TRH: cleanup_connection(id)
    TRH->>TRH: Cancel refresh monitor
    TRH->>TRH: Clear cache entries
```

## Token Refresh Strategy

```mermaid
flowchart TD
    Monitor([Auto Refresh Monitor])
    
    Monitor --> CheckExpiry{Token expires<br/>in < 5 min?}
    CheckExpiry -->|No| Sleep[Sleep 30s]
    Sleep --> Monitor
    
    CheckExpiry -->|Yes| AcquireLock[Acquire<br/>Connection Lock]
    AcquireLock --> RefreshToken[Request Token<br/>Refresh]
    
    RefreshToken --> AuthService{Auth Service<br/>Available?}
    AuthService -->|No| NotifyError[Send Error<br/>to Client]
    NotifyError --> ReAuth[Client Must<br/>Re-authenticate]
    
    AuthService -->|Yes| NewToken[Receive<br/>New Token]
    NewToken --> UpdateCache[Update<br/>Token Cache]
    UpdateCache --> NotifyClient[Send New Token<br/>to Client]
    NotifyClient --> UpdateMetrics[Update<br/>Metrics]
    UpdateMetrics --> ReleaseLock[Release Lock]
    ReleaseLock --> Sleep
    
    style ReAuth fill:#f96
    style NotifyClient fill:#9f6
```

## Error Handling and Resilience

```mermaid
graph TD
    subgraph "Error Categories"
        NetErr[Network Errors]
        AuthErr[Auth Failures]
        SvcErr[Service Errors]
    end
    
    subgraph "Resilience Mechanisms"
        Retry[Retry Logic]
        CB2[Circuit Breaker]
        Cache2[Cache Fallback]
        Degrade[Degraded Mode]
    end
    
    subgraph "User Notifications"
        Friendly[User-Friendly Message]
        Code[Support Code]
        Action[Action Required]
    end
    
    NetErr --> Retry
    Retry -->|Max Retries| CB2
    CB2 --> Cache2
    Cache2 -->|Stale Data| Degrade
    
    AuthErr --> Friendly
    SvcErr --> Code
    Degrade --> Action
```

## Configuration Requirements

### Backend Service Configuration

```yaml
# Required Environment Variables
SERVICE_ID: netra-backend
SERVICE_SECRET: [32+ character secret]
AUTH_SERVICE_URL: http://auth-service:8081
AUTH_SERVICE_ENABLED: true
AUTH_CLIENT_TIMEOUT: 10
AUTH_CLIENT_MAX_RETRIES: 3
AUTH_CLIENT_CACHE_TTL: 300
AUTH_CLIENT_CIRCUIT_BREAKER: true
```

### Auth Service Configuration

```yaml
# Required Environment Variables
JWT_SECRET: [32+ character secret, must match across services]
JWT_ALGORITHM: HS256
TOKEN_EXPIRY_MINUTES: 60
REFRESH_TOKEN_EXPIRY_DAYS: 7
BLACKLIST_CHECK_ENABLED: true
SERVICE_AUTH_ENABLED: true
```

## Security Considerations

1. **JWT Secret Synchronization**: JWT_SECRET must be identical across all environments for a given deployment
2. **Service Credentials**: SERVICE_SECRET should be unique per service and rotated regularly
3. **No Local Validation**: Backend must NEVER decode JWTs locally - security vulnerability
4. **Blacklist Checking**: Auth service checks blacklist before ANY validation
5. **Atomic Operations**: Blacklist checks are atomic to prevent race conditions
6. **Cache Invalidation**: Tokens are immediately invalidated in cache upon logout/blacklist

## Monitoring and Observability

```mermaid
graph LR
    subgraph "Metrics"
        M1[Total Validations]
        M2[Cache Hit Rate]
        M3[Circuit Breaker State]
        M4[Validation Latency]
        M5[Refresh Success Rate]
    end
    
    subgraph "Alerts"
        A1[Circuit Open > 1min]
        A2[Cache Hit Rate < 80%]
        A3[Validation P95 > 200ms]
        A4[Auth Service Down]
    end
    
    subgraph "Logs"
        L1[Service Auth Failures]
        L2[Token Validation Errors]
        L3[Circuit State Changes]
        L4[Cache Operations]
    end
    
    M1 --> Dashboard
    M2 --> Dashboard
    M3 --> A1
    M4 --> A3
    M5 --> Dashboard
    
    A1 --> PagerDuty
    A2 --> Slack
    A3 --> Slack
    A4 --> PagerDuty
```

## Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| SERVICE_SECRET not set | 403 errors, "Inter-service auth failed" | Set SERVICE_SECRET env var |
| JWT_SECRET mismatch | All tokens invalid | Ensure JWT_SECRET identical across services |
| Circuit breaker stuck open | All auth fails after errors | Wait for recovery timeout (10s) or restart |
| High cache miss rate | Slow performance | Increase cache TTL or check token expiry |
| WebSocket token refresh fails | Connection drops after 1 hour | Check refresh endpoint and network |

## Testing Strategies

1. **Unit Tests**: Mock auth service responses, test cache behavior
2. **Integration Tests**: Use real auth service, test service-to-service auth
3. **E2E Tests**: Full flow with real JWT tokens, test WebSocket refresh
4. **Load Tests**: Verify cache effectiveness under load
5. **Chaos Tests**: Test circuit breaker behavior with auth service failures

## Migration Notes

### From Local JWT Validation
1. Remove all `import jwt` statements
2. Replace `jwt.decode()` with `auth_client.validate_token()`
3. Update error handling for auth service failures
4. Add circuit breaker configuration
5. Test degraded mode behavior

### WebSocket Token Refresh
1. Initialize TokenRefreshHandler with WebSocket manager
2. Call `initialize_connection()` on connect
3. Handle `token_refreshed` events in client
4. Call `cleanup_connection()` on disconnect
5. Monitor refresh metrics

## Conclusion

This architecture ensures secure, scalable, and resilient authentication across the Netra platform. By delegating all authentication to a dedicated service with proper caching and circuit breaker patterns, we achieve:

- **Security**: No JWT secrets in backend service
- **Performance**: Sub-10ms cache hits for most requests
- **Resilience**: Graceful degradation during auth service issues
- **Scalability**: Stateless backend can scale horizontally
- **Maintainability**: Single source of truth for auth logic