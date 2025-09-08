# Docker Environment Variable Fixes Proposal

**Date**: 2025-09-08  
**Context**: Addressing Redis configuration inconsistencies from Five Whys analysis  
**Priority**: HIGH - Critical for Docker environment stability

## Summary of Fixes

This proposal addresses the **configuration management systemic gap** identified in the Five Whys root cause analysis by implementing standardized Docker environment variable configurations and validation.

## Fix 1: Standardize Environment Variables Across All Docker Compose Files

### Current Problems
- Inconsistent use of `REDIS_URL` vs `REDIS_HOST`/`REDIS_PORT`
- Missing Docker environment detection variables
- No standard health check variables

### Proposed Solution: Standard Docker Environment Block

Add to **ALL** Docker Compose files for backend and auth services:

```yaml
environment:
  # Core Environment
  ENVIRONMENT: {environment_name}
  
  # Docker Environment Detection (NEW)
  DOCKER_ENVIRONMENT: "true"
  CONTAINER_NAME: "{service-name}"
  
  # Redis Configuration (STANDARDIZED)
  REDIS_URL: redis://{redis-service-name}:6379
  REDIS_HOST: {redis-service-name}
  REDIS_PORT: 6379
  
  # Health Check Configuration (NEW)
  HEALTH_CHECK_TIMEOUT: 10
  REDIS_CONNECTION_TIMEOUT: 5
  
  # Existing variables continue unchanged...
```

### Implementation for Each File

#### 1. `docker-compose.yml` (Development)

**Backend Service**:
```yaml
dev-backend:
  environment:
    # Docker Detection (NEW)
    DOCKER_ENVIRONMENT: "true"
    CONTAINER_NAME: "dev-backend"
    
    # Redis (ENHANCED)
    REDIS_URL: redis://dev-redis:6379/0  # (add database number)
    REDIS_HOST: dev-redis                # (existing)
    REDIS_PORT: 6379                     # (existing)
    
    # Health Check (NEW)
    HEALTH_CHECK_TIMEOUT: 10
    REDIS_CONNECTION_TIMEOUT: 5
```

**Auth Service**:
```yaml
dev-auth:
  environment:
    # Docker Detection (NEW)  
    DOCKER_ENVIRONMENT: "true"
    CONTAINER_NAME: "dev-auth"
    
    # Redis (ENHANCED)
    REDIS_URL: redis://dev-redis:6379/1  # (add database number)
    REDIS_HOST: dev-redis                # (existing)
    REDIS_PORT: 6379                     # (existing)
    
    # Health Check (NEW)
    HEALTH_CHECK_TIMEOUT: 10
    REDIS_CONNECTION_TIMEOUT: 5
```

#### 2. `docker-compose.alpine-test.yml`

**Backend Service**:
```yaml
alpine-test-backend:
  environment:
    # Docker Detection (NEW)
    DOCKER_ENVIRONMENT: "true"
    CONTAINER_NAME: "alpine-test-backend"
    
    # Redis (EXISTING - NO CHANGE)
    REDIS_URL: redis://alpine-test-redis:6379
    REDIS_HOST: alpine-test-redis  
    REDIS_PORT: 6379
    
    # Health Check (NEW)
    HEALTH_CHECK_TIMEOUT: 10
    REDIS_CONNECTION_TIMEOUT: 5
```

#### 3. All Other Docker Compose Files

Apply same pattern with appropriate service names and environment-specific values.

## Fix 2: Update RedisManager Docker Environment Detection

### Current Problematic Code
```python
# Lines 145-150 in redis_manager.py - REMOVE THIS
if hasattr(current_loop, '_pytest_test_loop') or 'pytest' in str(current_loop):
    redis_url = redis_url.replace(':6379/', ':6381/')  # ❌ WRONG
    logger.debug(f"Test environment detected - using Redis URL: {redis_url}")
```

### Proposed Replacement

**File**: `/netra_backend/app/redis_manager.py`

```python
def _get_redis_url_for_environment(self) -> str:
    """Get Redis URL with proper Docker environment handling."""
    backend_env = BackendEnvironment()
    
    # Check if we're in a Docker environment
    if backend_env.is_docker_environment():
        # In Docker: use container networking - no port modifications needed
        redis_url = backend_env.get_redis_url()
        container_name = backend_env.get("CONTAINER_NAME", "unknown")
        logger.debug(f"Docker environment detected (container: {container_name}) - using Redis URL: {redis_url}")
        return redis_url
    else:
        # Outside Docker: use localhost with appropriate external port
        return self._get_localhost_redis_url()
    
def _get_localhost_redis_url(self) -> str:
    """Get localhost Redis URL for non-Docker environments."""
    backend_env = BackendEnvironment()
    environment = backend_env.get_environment()
    
    # Map environment to external Redis ports
    port_mapping = {
        "development": 6380,  # DEV_REDIS_PORT
        "test": 6382,         # ALPINE_TEST_REDIS_PORT  
        "staging": 6381,      # Staging port
    }
    
    port = port_mapping.get(environment, 6379)
    redis_url = f"redis://localhost:{port}/0"
    logger.debug(f"Non-Docker environment ({environment}) - using Redis URL: {redis_url}")
    return redis_url
```

**Update `_attempt_connection()` method**:
```python
async def _attempt_connection(self, is_initial: bool = False) -> bool:
    async with self._connection_lock:
        try:
            # Clean up existing client...
            # (existing cleanup code)
            
            # Get Redis URL based on environment - UPDATED LOGIC
            redis_url = self._get_redis_url_for_environment()
            
            # Create new client instance...
            # (rest of method unchanged)
```

## Fix 3: Add Docker Environment Detection to BackendEnvironment

**File**: `/netra_backend/app/core/backend_environment.py`

Add these methods:

```python
def is_docker_environment(self) -> bool:
    """Check if running in Docker container."""
    return self.env.get("DOCKER_ENVIRONMENT", "false").lower() == "true"

def get_container_name(self) -> str:
    """Get Docker container name."""
    return self.env.get("CONTAINER_NAME", "unknown")

def get_health_check_timeout(self) -> int:
    """Get health check timeout in seconds."""
    try:
        return int(self.env.get("HEALTH_CHECK_TIMEOUT", "10"))
    except ValueError:
        return 10

def get_redis_connection_timeout(self) -> int:
    """Get Redis connection timeout in seconds.""" 
    try:
        return int(self.env.get("REDIS_CONNECTION_TIMEOUT", "5"))
    except ValueError:
        return 5
```

## Fix 4: Enhanced Docker Health Checks

### Add Redis Connectivity Validation

Update all Docker Compose health checks to include Redis connectivity:

```yaml
# Example for backend services
healthcheck:
  test: |
    curl -f http://localhost:8000/health &&
    python -c "
    import asyncio
    import redis.asyncio as redis
    async def check():
        r = redis.from_url('redis://{redis-service}:6379')
        await r.ping()
        await r.aclose()
    asyncio.run(check())
    " || exit 1
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 40s
```

### Add Dedicated Redis Health Check Script

**New file**: `/scripts/docker_health_check.py`

```python
#!/usr/bin/env python3
"""
Docker Health Check Script for Redis Connectivity
Usage: python scripts/docker_health_check.py --service redis
"""
import asyncio
import sys
import logging
from typing import Optional

try:
    import redis.asyncio as redis
except ImportError:
    print("Redis not available - health check skipped")
    sys.exit(0)

from netra_backend.app.core.backend_environment import BackendEnvironment

async def check_redis_connectivity() -> bool:
    """Check Redis connectivity with proper timeout."""
    try:
        env = BackendEnvironment()
        redis_url = env.get_redis_url()
        timeout = env.get_redis_connection_timeout()
        
        client = redis.from_url(redis_url, decode_responses=True)
        
        # Test connectivity with timeout
        await asyncio.wait_for(client.ping(), timeout=timeout)
        await client.aclose()
        
        print(f"✅ Redis connectivity OK: {redis_url}")
        return True
        
    except Exception as e:
        print(f"❌ Redis connectivity FAILED: {e}")
        return False

async def main():
    """Main health check entry point."""
    success = await check_redis_connectivity()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
```

## Fix 5: Environment Startup Validation

### Add Configuration Validation on Service Startup

**File**: `/netra_backend/app/core/startup_validation.py` (NEW)

```python
"""
Docker Environment Startup Validation
Validates configuration consistency on service startup
"""
import logging
import asyncio
from typing import Dict, List, Any

from netra_backend.app.core.backend_environment import BackendEnvironment
from netra_backend.app.redis_manager import redis_manager

logger = logging.getLogger(__name__)

async def validate_docker_environment() -> Dict[str, Any]:
    """Validate Docker environment configuration on startup."""
    env = BackendEnvironment()
    issues = []
    warnings = []
    
    # Check Docker environment detection
    if env.is_docker_environment():
        container_name = env.get_container_name()
        logger.info(f"Docker environment detected - Container: {container_name}")
        
        # Validate Redis configuration
        redis_url = env.get_redis_url()
        if "localhost" in redis_url:
            issues.append(f"Docker container using localhost Redis URL: {redis_url}")
        
        # Test Redis connectivity
        try:
            client = await redis_manager.get_client()
            if client:
                await client.ping()
                logger.info("✅ Redis connectivity validated")
            else:
                issues.append("Redis client not available during startup")
        except Exception as e:
            issues.append(f"Redis connectivity failed during startup: {e}")
    else:
        logger.info("Non-Docker environment detected")
        warnings.append("Running outside Docker environment")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "environment": env.get_environment(),
        "docker_container": env.is_docker_environment(),
        "container_name": env.get_container_name() if env.is_docker_environment() else None
    }

async def startup_validation():
    """Run all startup validations."""
    logger.info("Running Docker environment startup validation...")
    
    validation_result = await validate_docker_environment()
    
    if not validation_result["valid"]:
        logger.error("❌ Docker environment validation FAILED:")
        for issue in validation_result["issues"]:
            logger.error(f"  - {issue}")
        
        # In production/staging, fail fast on configuration errors
        env = BackendEnvironment()
        if env.is_production() or env.is_staging():
            raise RuntimeError("Docker environment validation failed in production/staging")
    else:
        logger.info("✅ Docker environment validation passed")
    
    if validation_result["warnings"]:
        for warning in validation_result["warnings"]:
            logger.warning(f"⚠️  {warning}")
    
    return validation_result
```

**Integration**: Add to FastAPI startup events in main application file.

## Implementation Priority

### Phase 1: Critical Fixes (Immediate)
1. Update RedisManager environment detection logic
2. Add `DOCKER_ENVIRONMENT` variable to all Docker Compose files
3. Fix test environment port mapping logic

### Phase 2: Standardization (This Week)
1. Standardize all Docker Compose environment variables
2. Add Docker environment detection to BackendEnvironment
3. Implement startup validation

### Phase 3: Health Checks (Next Week)  
1. Enhanced Docker health checks with Redis connectivity
2. Docker health check script
3. Monitoring and alerting for configuration drift

## Testing Strategy

### Validation Commands

```bash
# Test each Docker environment
docker-compose -f docker-compose.yml up --build
docker-compose -f docker-compose.alpine-test.yml up --build  
docker-compose -f docker-compose.staging.alpine.yml up --build

# Validate Redis connectivity in each
docker-compose exec {service} python scripts/docker_health_check.py
```

### Success Criteria
- [ ] All Docker environments start successfully
- [ ] Redis connectivity works in all environments  
- [ ] No localhost Redis URLs in Docker containers
- [ ] Health checks pass consistently
- [ ] Startup validation reports no critical issues

---

**Five Whys Context**: These fixes directly address the **configuration management systemic gap** (root cause) by implementing automated validation and standardized configuration management that prevents the Redis connection mismatches that caused the original system failures.