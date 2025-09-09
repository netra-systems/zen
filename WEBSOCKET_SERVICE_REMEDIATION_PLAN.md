# WebSocket Service Remediation Plan

## Executive Summary

**Issue**: Real WebSocket error event delivery system is not operational due to missing WebSocket service at `ws://localhost:8002/ws`

**Root Cause**: Docker containers for the test environment (specifically `alpine-test-backend`) are not running, causing WebSocket endpoint unavailability

**Impact**: 
- Mock WebSocket error event delivery works (5/5 events) 
- Real WebSocket connection fails with "[WinError 1225] The remote computer refused the network connection"
- Production deployment would fail WebSocket functionality

## Investigation Findings

### 1. WebSocket Configuration Analysis

**WebSocket Endpoint Configuration**:
- Main WebSocket endpoint: `ws://localhost:8002/ws` (from `/netra_backend/app/routes/websocket.py`)
- Docker mapping: External port 8002 → Internal port 8000
- Service implemented in: `netra_backend.app.routes.websocket.websocket_endpoint()`

**Key Features**:
- JWT authentication (header or subprotocol)
- Automatic message routing via MessageRouter
- Heartbeat monitoring
- Rate limiting and error handling
- Support for 5 critical error event types

### 2. Docker Infrastructure Analysis

**Required Services**:
```yaml
# From docker-compose.alpine-test.yml
services:
  alpine-test-backend:     # Port 8002:8000 (WebSocket service)
  alpine-test-auth:        # Port 8083:8081 (Authentication)
  alpine-test-postgres:    # Port 5435:5432 (Database)
  alpine-test-redis:       # Port 6382:6379 (Cache)
  alpine-test-clickhouse:  # Port 8126:8123 (Analytics)
```

**Current Status**:
- ✅ PostgreSQL, Redis, ClickHouse, Auth Service: Running and healthy
- ❌ Backend Service: Failed to start due to migration dependency
- ❌ Migration Service: Failed with "Path doesn't exist: netra_backend/app/alembic"

### 3. Service Dependency Chain

```
WebSocket Service (port 8002)
    ↓ depends on
Backend Container (alpine-test-backend)
    ↓ depends on
Migration Service (alpine-test-migration)
    ↓ depends on
Database Services (postgres, redis, clickhouse)
```

**Failure Point**: Migration service fails → Backend can't start → WebSocket unavailable

## Remediation Options

### Option 1: Quick Fix - Start Backend Without Migration (Recommended for Testing)

```bash
# Start infrastructure services
cd /path/to/netra-core-generation-1
docker-compose -f docker-compose.alpine-test.yml up -d alpine-test-postgres alpine-test-redis alpine-test-auth

# Start backend without migration dependency
docker-compose -f docker-compose.alpine-test.yml up -d alpine-test-backend --no-deps

# Verify WebSocket service
curl -f http://localhost:8002/health
```

**Pros**: Fast setup, isolates WebSocket testing
**Cons**: May have database schema issues

### Option 2: Fix Migration Service (Recommended for Production)

```bash
# Create missing alembic directory
mkdir -p netra_backend/app/alembic

# Initialize alembic if needed
cd netra_backend
alembic init app/alembic

# Or copy from existing location if available
# Check if alembic exists elsewhere in the codebase

# Then start full stack
docker-compose -f docker-compose.alpine-test.yml up -d
```

### Option 3: Use Unified Test Runner (Recommended for CI/CD)

```bash
# Use test runner which handles Docker startup automatically
python tests/unified_test_runner.py --real-services --category websocket
```

## Step-by-Step Remediation Instructions

### Phase 1: Immediate WebSocket Service Activation

1. **Start Infrastructure Services**:
   ```bash
   docker-compose -f docker-compose.alpine-test.yml up -d \
     alpine-test-postgres \
     alpine-test-redis \
     alpine-test-auth
   ```

2. **Verify Infrastructure Health**:
   ```bash
   docker ps --filter "name=alpine-test" --format "table {{.Names}}\t{{.Status}}"
   # Should show all services as "Up" and "(healthy)"
   ```

3. **Start Backend Without Dependencies**:
   ```bash
   docker-compose -f docker-compose.alpine-test.yml up -d alpine-test-backend --no-deps
   ```

4. **Verify WebSocket Service**:
   ```bash
   # Test HTTP health endpoint
   curl -f http://localhost:8002/health
   
   # Test WebSocket configuration endpoint
   curl http://localhost:8002/ws/config
   ```

### Phase 2: WebSocket Error Event Testing

1. **Run WebSocket Error Event Tests**:
   ```bash
   # Set environment for real services
   export USE_REAL_SERVICES=true
   export WEBSOCKET_URL=ws://localhost:8002/ws
   
   # Run WebSocket error event delivery tests
   python tests/unified_test_runner.py --real-services --pattern "*websocket*error*"
   ```

2. **Verify 5 Critical Error Events**:
   - `agent_error` - Agent execution failures
   - `tool_error` - Tool execution failures  
   - `validation_error` - Input validation failures
   - `timeout_error` - Operation timeout failures
   - `system_error` - System-level failures

### Phase 3: Authentication Integration Validation

1. **Test JWT Authentication**:
   ```bash
   # Verify auth service is running
   curl http://localhost:8083/health
   
   # Test WebSocket with authentication
   # (Use WebSocket test client with JWT token)
   ```

2. **Validate Multi-User Isolation**:
   ```bash
   # Run user isolation tests
   python tests/unified_test_runner.py --real-services --pattern "*user*isolation*"
   ```

## Environment Configuration

### Required Environment Variables

```bash
# WebSocket Service Configuration
WEBSOCKET_URL=ws://localhost:8002/ws
BACKEND_URL=http://localhost:8002
AUTH_SERVICE_URL=http://localhost:8083

# Database Configuration (for backend)
POSTGRES_HOST=alpine-test-postgres
POSTGRES_PORT=5432
POSTGRES_USER=test
POSTGRES_PASSWORD=test
POSTGRES_DB=netra_test

# Redis Configuration
REDIS_HOST=alpine-test-redis
REDIS_PORT=6379
REDIS_URL=redis://alpine-test-redis:6379

# Testing Configuration
USE_REAL_SERVICES=true
ENVIRONMENT=test
TEST_MODE=true
```

### Docker Port Mappings

| Service | Internal Port | External Port | Purpose |
|---------|---------------|---------------|---------|
| Backend (WebSocket) | 8000 | 8002 | WebSocket endpoint |
| Auth Service | 8081 | 8083 | Authentication |
| PostgreSQL | 5432 | 5435 | Database |
| Redis | 6379 | 6382 | Cache |
| ClickHouse | 8123 | 8126 | Analytics |

## Production Deployment Considerations

### 1. WebSocket Service Requirements

- **Authentication**: JWT tokens via header or WebSocket subprotocol
- **Rate Limiting**: Environment-specific limits (dev: 300/min, staging: 100/min, prod: 30/min)
- **Heartbeat**: Configurable intervals (dev: 45s, staging: 30s, prod: 25s)
- **Connection Limits**: Max 3 connections per user
- **Message Size**: Max 8KB per message

### 2. Error Event Delivery Requirements

The WebSocket service MUST deliver these 5 error event types:

1. **agent_error**: When AI agent execution fails
2. **tool_error**: When tool execution encounters errors
3. **validation_error**: When input validation fails
4. **timeout_error**: When operations exceed time limits
5. **system_error**: When system-level failures occur

### 3. Infrastructure Dependencies

- **Database**: PostgreSQL with proper migrations
- **Cache**: Redis for session management
- **Authentication**: Separate auth service on port 8081
- **Monitoring**: ClickHouse for analytics (optional)

## Validation Checklist

### ✅ WebSocket Service Health
- [ ] HTTP health endpoint responds: `curl http://localhost:8002/health`
- [ ] WebSocket config endpoint responds: `curl http://localhost:8002/ws/config`
- [ ] WebSocket connection accepts: Test with WebSocket client
- [ ] Authentication works: JWT token validation
- [ ] All 5 error event types deliver correctly

### ✅ Infrastructure Health
- [ ] PostgreSQL accessible and schema ready
- [ ] Redis accessible for session storage
- [ ] Auth service responds on port 8083
- [ ] Network connectivity between services

### ✅ Integration Testing
- [ ] Real WebSocket error event delivery test passes
- [ ] Multi-user isolation works correctly
- [ ] Authentication integration functions
- [ ] Error recovery and reconnection works
- [ ] Rate limiting functions correctly

## Monitoring and Maintenance

### Key Metrics to Monitor
- WebSocket connection count and success rate
- Error event delivery latency and success rate
- Authentication success/failure rates
- Connection duration and disconnection reasons
- Resource usage (CPU, memory, network)

### Common Issues and Solutions
1. **Connection Refused**: Check if backend container is running
2. **Authentication Failures**: Verify auth service connectivity
3. **Database Errors**: Check PostgreSQL health and schema
4. **Memory Issues**: Monitor container resource limits
5. **Network Issues**: Verify Docker network configuration

## Next Steps

1. **Immediate**: Implement Option 1 (Quick Fix) for testing
2. **Short-term**: Fix migration service for full stack
3. **Medium-term**: Integrate with CI/CD pipeline
4. **Long-term**: Implement comprehensive monitoring

---

**Report Generated**: 2025-09-09
**Priority**: HIGH - Required for production WebSocket functionality
**Owner**: Platform Team
**Review Date**: Weekly until resolved