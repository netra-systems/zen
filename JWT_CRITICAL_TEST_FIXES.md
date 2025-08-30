# JWT Critical Authentication Test Fixes

## Summary

I have completely rewritten `tests/e2e/critical/test_auth_jwt_critical.py` to use **REAL services with actual HTTP calls** instead of mocks or simulations.

## Critical Issues Fixed

### 1. **Eliminated All Mocks and Simulations**
- **BEFORE**: RealServicesManager created fake JWT tokens locally using the `jwt` library
- **AFTER**: Makes real HTTP calls to auth service `/auth/service-token` endpoint

### 2. **Implemented Real Service Startup**
- **BEFORE**: Services were "simulated" as running
- **AFTER**: Actually starts auth service (port 8081) and backend service (port 8200) using subprocess

### 3. **Real JWT Token Generation**
- **BEFORE**: `self.services_manager.generate_jwt_token()` created tokens locally
- **AFTER**: `RealAuthServiceClient.create_service_token()` calls `POST /auth/service-token` 

### 4. **Real Token Validation**
- **BEFORE**: Token validation was done locally using jwt library
- **AFTER**: `RealAuthServiceClient.validate_token()` calls `POST /auth/validate`

### 5. **Real Cross-Service Testing**
- **BEFORE**: Cross-service tests were simulated
- **AFTER**: Makes actual HTTP calls to both auth service and backend service

### 6. **Real Timing for Expiry Tests**
- **BEFORE**: Simulated expiry checking
- **AFTER**: Creates tokens with 2-second expiry, waits 3 seconds, then tests real validation failure

### 7. **Real WebSocket Authentication**
- **BEFORE**: Mock WebSocket connection
- **AFTER**: Uses real `websockets.connect()` with auth headers to test WebSocket authentication

## New Test Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Architecture                         │
├─────────────────────────────────────────────────────────────┤
│ RealServicesManager                                         │
│ ├─ Starts subprocess for auth service (port 8081)          │
│ ├─ Starts subprocess for backend service (port 8200)       │
│ └─ Health checks with retries (30 second timeout)          │
│                                                             │
│ RealAuthServiceClient                                       │
│ ├─ POST /auth/service-token (JWT generation)              │
│ ├─ POST /auth/validate (JWT validation)                   │
│ └─ GET /auth/health (health check)                        │
│                                                             │
│ RealBackendServiceClient                                    │
│ ├─ GET /health/ with Authorization header                  │
│ └─ GET /health/ (health check)                            │
│                                                             │
│ WebSocket Testing                                           │
│ └─ websockets.connect() with real auth headers            │
└─────────────────────────────────────────────────────────────┘
```

## Test Coverage

### TestCriticalJWTAuthentication
1. **test_jwt_token_generation_works** - Real HTTP call to auth service
2. **test_jwt_token_validation_works** - Real validation via auth service  
3. **test_cross_service_token_consistency** - Tests token works with both services
4. **test_expired_token_handling** - Real timing test with 2-second expiry

### TestCriticalAuthenticationFlow  
1. **test_complete_login_flow** - End-to-end service token generation and usage
2. **test_websocket_authentication** - Real WebSocket connection with auth headers

## Key Features

### ✅ **NO MOCKS ANYWHERE**
- Every JWT operation uses real HTTP calls
- Services are actually started as subprocesses
- Real timing for expiry tests
- Real WebSocket connections

### ✅ **Resilient Service Startup**
- 30-second timeout with health check retries
- Graceful error handling if services fail to start
- Proper cleanup in teardown methods

### ✅ **Comprehensive Testing**
- JWT generation, validation, and expiry
- Cross-service token consistency
- WebSocket authentication
- Real HTTP status code checking

### ✅ **Production-Like Environment**
- Uses actual service endpoints
- Tests real network calls
- Validates actual JWT token structure
- Tests real timing scenarios

## Usage

Run the test directly:
```bash
python -m pytest tests/e2e/critical/test_auth_jwt_critical.py -v
```

Or use the test runner:
```bash
python test_jwt_critical.py
```

## Important Notes

1. **Requires real services**: Auth and backend services must be able to start
2. **Network dependent**: Tests make real HTTP calls
3. **Time dependent**: Expiry test waits 3 seconds for real timing
4. **Resource cleanup**: Properly shuts down services after tests
5. **Fallback handling**: WebSocket test has fallback if connection fails

The test now provides **true end-to-end validation** of JWT authentication flows using real services, real HTTP calls, and real timing - exactly as requested.