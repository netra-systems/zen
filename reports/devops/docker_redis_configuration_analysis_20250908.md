# Docker Redis Configuration Analysis Report

**Date**: 2025-09-08  
**Context**: Five Whys Root Cause Analysis - Docker Environment Configuration Gap  
**Focus**: Redis port mappings and environment variable inconsistencies

## Executive Summary

Analysis of all Docker Compose configurations reveals **critical inconsistencies** in Redis port mappings and environment variable configurations that directly cause the connection failures identified in the Five Whys analysis.

**Root Cause Confirmed**: The Redis container consistently runs on internal port `6379` but is mapped to **different external ports** across environments, while applications expect different connection patterns based on environment detection logic.

## Redis Port Mapping Analysis

### Complete Port Mapping Matrix

| Docker Compose File | Redis Service | External Port | Internal Port | Application Expectation |
|-------------------|---------------|---------------|---------------|------------------------|
| `docker-compose.yml` (dev) | `dev-redis` | 6380 | 6379 | Uses REDIS_HOST/PORT env vars |
| `docker-compose.alpine-test.yml` | `alpine-test-redis` | 6382 | 6379 | Uses REDIS_URL env var |
| `docker-compose.alpine-dev.yml` | `dev-redis` | 6379 | 6379 | Uses REDIS_URL env var |
| `docker-compose.minimal-test.yml` | `minimal-test-redis` | 6383 | 6379 | No application layer |
| `docker-compose.staging.yml` | `redis` | 6381 | 6379 | Uses REDIS_URL env var |
| `docker-compose.staging.alpine.yml` | `redis` | 6381 | 6379 | Uses REDIS_URL env var |

### Critical Finding: Port Mapping Inconsistencies

**ISSUE 1: Main Development Environment**
- Container: `dev-redis` maps `6380:6379` 
- Application: Expects `dev-redis:6379` (internal Docker network)
- **Status**: ✅ CORRECT - Uses internal Docker networking

**ISSUE 2: Alpine Test Environment** 
- Container: `alpine-test-redis` maps `6382:6379`
- Application: Uses `REDIS_URL: redis://alpine-test-redis:6379`
- **Status**: ✅ CORRECT - Uses internal Docker networking

**ISSUE 3: Local Host Connection Attempts**
- RedisManager has fallback logic to localhost ports
- External port mappings (6380, 6381, 6382, 6383) not consistently used
- **Status**: ❌ PROBLEMATIC - Creates confusion in connection logic

## Environment Variable Configuration Analysis

### Development Environment (`docker-compose.yml`)

```yaml
# Backend Service Environment Variables
REDIS_HOST: dev-redis      # ✅ Correct container name
REDIS_PORT: 6379           # ✅ Correct internal port

# Container Port Mapping
ports:
  - "${DEV_REDIS_PORT:-6380}:6379"  # External:Internal mapping
```

**Analysis**: Correct configuration using Docker internal networking.

### Alpine Test Environment (`docker-compose.alpine-test.yml`)

```yaml
# Backend Service Environment Variables
REDIS_HOST: alpine-test-redis     # ✅ Correct container name
REDIS_PORT: 6379                  # ✅ Correct internal port  
REDIS_URL: redis://alpine-test-redis:6379  # ✅ Complete URL

# Container Port Mapping
ports:
  - "${ALPINE_TEST_REDIS_PORT:-6382}:6379"  # External:Internal
```

**Analysis**: Optimal configuration with both individual variables and complete URL.

### Staging Environments

```yaml
# Both staging.yml and staging.alpine.yml
REDIS_URL: redis://redis:6379/0   # ✅ Correct
REDIS_HOST: redis                 # ✅ Correct
REDIS_PORT: 6379                  # ✅ Correct

# Container Port Mapping
ports:
  - "6381:6379"  # External:Internal
```

**Analysis**: Correct configuration using Docker internal networking.

## Application Logic Analysis

### RedisManager Connection Logic Issues

**File**: `/netra_backend/app/redis_manager.py`

**Issue 1: Test Environment Detection**
```python
# Lines 145-150: Problematic test detection logic
if hasattr(current_loop, '_pytest_test_loop') or 'pytest' in str(current_loop):
    redis_url = redis_url.replace(':6379/', ':6381/')  # ❌ WRONG PORT
    logger.debug(f"Test environment detected - using Redis URL: {redis_url}")
```

**Problem**: Changes port to 6381 (staging port) instead of 6382 (alpine-test port).

**Issue 2: BackendEnvironment Redis URL Logic**
```python
# Lines 125-127: Simple fallback logic
def get_redis_url(self) -> str:
    return self.env.get("REDIS_URL", "redis://localhost:6379/0")
```

**Problem**: Falls back to localhost:6379, but Docker environments use different external ports.

## Configuration Gaps Identified

### Gap 1: Environment Detection vs Port Selection

| Environment | Expected Port Logic | Actual Container Port | Status |
|------------|-------------------|---------------------|---------|
| Development | localhost:6380 | dev-redis:6379 | ❌ Mismatch |
| Alpine Test | localhost:6382 | alpine-test-redis:6379 | ❌ Mismatch |  
| Staging | localhost:6381 | redis:6379 | ❌ Mismatch |

### Gap 2: Missing Environment Variable Consistency

**Missing Standardization**:
- Some environments use `REDIS_URL` only
- Others use `REDIS_HOST` + `REDIS_PORT` 
- No consistent environment detection mechanism

### Gap 3: Test Environment Docker Network Isolation

**Problem**: Applications running inside Docker containers should NEVER connect to localhost ports - they should use Docker internal networking.

**Current Issue**: RedisManager test detection tries to connect to external localhost ports instead of internal container names.

## Root Cause Summary

**From Five Whys Analysis**: Redis container runs on 6380:6379 mapping but application tries localhost:6379

**Confirmed Root Causes**:

1. **Docker Network Confusion**: Application logic mixes Docker internal networking (correct) with localhost external port logic (incorrect)

2. **Inconsistent Environment Detection**: Test environment detection uses wrong port mappings (6381 instead of 6382)

3. **Port Mapping Misunderstanding**: External port mappings (6380, 6381, 6382) are for HOST access, not container-to-container communication

4. **Environment Variable Inconsistencies**: Some Docker Compose files provide complete REDIS_URL while others rely on host/port combinations

## Impact Analysis

### Immediate Impact
- Redis connections fail in test environments
- Intermittent connection issues in development
- Silent fallbacks to localhost causing confusion

### Systemic Impact  
- Docker environment configuration not validated consistently
- No automatic environment detection for Docker networking
- Manual port management across multiple environments

## Recommendations

### Immediate Fixes Required

1. **Fix RedisManager Test Detection Logic**:
   ```python
   # Replace lines 145-150 with proper Docker environment detection
   if self._is_docker_environment():
       # Use container name from environment, don't modify ports
       pass
   ```

2. **Standardize Environment Variables Across All Docker Compose Files**:
   ```yaml
   # Required for all environments
   REDIS_URL: redis://{service-name}:6379
   REDIS_HOST: {service-name}  
   REDIS_PORT: 6379
   DOCKER_ENVIRONMENT: "true"  # New variable for detection
   ```

3. **Add Docker Environment Detection**:
   ```python
   def _is_docker_environment(self) -> bool:
       return self.env.get("DOCKER_ENVIRONMENT", "false").lower() == "true"
   ```

### Long-term Solutions

1. **Docker Network Health Checks**: Add Redis connectivity validation to Docker health checks
2. **Environment Configuration Validation**: Startup validation that confirms Redis connectivity matches expected configuration
3. **Unified Docker Environment Management**: Single source of truth for all Docker environment configurations

## Next Steps

1. Implement immediate fixes to RedisManager test detection logic
2. Update all Docker Compose files with consistent environment variables  
3. Add Docker environment detection to BackendEnvironment
4. Create validation scripts for Docker environment configuration
5. Update documentation for Docker networking vs localhost access patterns

---

**Five Whys Context**: This analysis addresses WHY #2 (immediate cause) and WHY #3 (system failure) by ensuring Docker configurations match application expectations consistently, preventing the Redis connection failures that cascade into larger system issues.