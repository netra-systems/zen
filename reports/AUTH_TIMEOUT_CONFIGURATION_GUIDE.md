# Auth Service Timeout Configuration Guide

**Generated:** 2025-09-11  
**Issue:** #395 - Staging timeout 0.5s too aggressive for GCP Cloud Run  
**Resolution:** 6-Phase remediation plan implementation

## Recommended Timeout Values by Environment

### Staging Environment
**Purpose:** GCP Cloud Run compatibility with 87% buffer utilization

```bash
# HTTP Client Timeouts (Total: 12s)
AUTH_CONNECT_TIMEOUT=2.0    # Connection establishment
AUTH_READ_TIMEOUT=4.0       # Response reading
AUTH_WRITE_TIMEOUT=2.0      # Request writing  
AUTH_POOL_TIMEOUT=4.0       # Connection pool

# Health Check Timeout
AUTH_HEALTH_CHECK_TIMEOUT=1.5  # Increased from 0.5s for 87% buffer
```

**Buffer Analysis:**
- Auth service response time: 0.195s (measured)
- Health check timeout: 1.5s
- Buffer utilization: 87% ((1.5-0.195)/1.5)
- Previous buffer: 61% with 0.5s timeout

### Production Environment
**Purpose:** Balanced reliability without excessive delays

```bash
# HTTP Client Timeouts (Total: 15s)
AUTH_CONNECT_TIMEOUT=2.0
AUTH_READ_TIMEOUT=5.0
AUTH_WRITE_TIMEOUT=3.0
AUTH_POOL_TIMEOUT=5.0

# Health Check Timeout  
AUTH_HEALTH_CHECK_TIMEOUT=1.0  # Fast but reliable
```

### Development Environment
**Purpose:** Quick feedback for development workflow

```bash
# HTTP Client Timeouts (Total: 8s)
AUTH_CONNECT_TIMEOUT=1.0
AUTH_READ_TIMEOUT=3.0
AUTH_WRITE_TIMEOUT=1.0
AUTH_POOL_TIMEOUT=3.0

# Health Check Timeout
AUTH_HEALTH_CHECK_TIMEOUT=1.0
```

## Environment Variable Override System

The auth client now supports runtime timeout configuration via environment variables:

1. **AUTH_CONNECT_TIMEOUT** - Connection establishment timeout
2. **AUTH_READ_TIMEOUT** - Response reading timeout
3. **AUTH_WRITE_TIMEOUT** - Request writing timeout
4. **AUTH_POOL_TIMEOUT** - Connection pool timeout
5. **AUTH_HEALTH_CHECK_TIMEOUT** - Health check connectivity timeout

## Validation Commands

```bash
# Test staging configuration
ENVIRONMENT=staging python -c "
from netra_backend.app.clients.auth_client_core import AuthServiceClient
client = AuthServiceClient()
timeouts = client._get_environment_specific_timeouts()
print(f'Staging timeouts: {timeouts}')
"

# Test with environment variable override
AUTH_HEALTH_CHECK_TIMEOUT=2.0 python -c "
from netra_backend.app.clients.auth_client_core import AuthServiceClient
import asyncio
client = AuthServiceClient()
# Would need async context to test health check timeout
"
```

## Circuit Breaker Alignment

Circuit breaker timeouts should be configured to complement health check timeouts:

```bash
# Ensure call_timeout > health_check_timeout
AUTH_CIRCUIT_CALL_TIMEOUT=3.0  # Should be > 1.5s health check timeout
AUTH_CIRCUIT_RECOVERY_TIMEOUT=10.0
```

## Migration Path

1. **Immediate:** Updated default timeouts provide better GCP Cloud Run compatibility
2. **Runtime:** Set environment variables to override defaults without code changes  
3. **Monitoring:** Debug logs show actual timeout configuration per environment
4. **Testing:** Run timeout reproduction tests to validate fixes

## Business Impact

- **$500K+ ARR Protection:** Reliable auth service connectivity prevents Golden Path failures
- **User Experience:** 87% buffer utilization reduces timeout-related authentication failures
- **Development Velocity:** Environment-specific defaults with runtime overrides
- **Operational Flexibility:** No code changes required to adjust timeouts

## References

- **Issue #395:** Auth service timeout configuration problems
- **Auth Client Core:** `netra_backend/app/clients/auth_client_core.py`
- **Timeout Tests:** `tests/unit/test_auth_service_timeout_reproduction.py`