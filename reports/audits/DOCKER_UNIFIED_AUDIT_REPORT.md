# Docker Unified System Audit Report

## Executive Summary
Critical deltas have been identified between test and development Docker environments that are causing crashes and configuration mismatches. The primary issues stem from inconsistent credentials, port allocations, and service naming conventions.

## Critical Findings

### 1. Database Credential Mismatch (CRITICAL)
**Issue**: Test and development environments use different PostgreSQL credentials
- **Development**: `POSTGRES_USER=netra`, `POSTGRES_PASSWORD=netra123`, `POSTGRES_DB=netra_dev`
- **Test**: `POSTGRES_USER=test_user`, `POSTGRES_PASSWORD=test_pass`, `POSTGRES_DB=netra_test`
- **Alpine Test**: `POSTGRES_USER=test`, `POSTGRES_PASSWORD=test`, `POSTGRES_DB=netra_test`

**Impact**: Connection failures when UnifiedDockerManager attempts to connect with incorrect credentials

**Evidence**: 
- docker-compose.yml:26-28 (dev credentials)
- docker-compose.test.yml:16-18 (test credentials)
- docker-compose.alpine-test.yml:13-15 (alpine credentials)

### 2. Port Allocation Conflicts
**Issue**: Port ranges overlap between environments causing binding failures
- **Development**: Uses ports 8000-8999 (PortRange.DEVELOPMENT)
- **Test (Shared)**: Uses ports 30000-30999 (PortRange.SHARED_TEST)
- **Test (Dedicated)**: Uses ports 31000-39999 (PortRange.DEDICATED_TEST)

**Current State**:
```
Dev Services Running:
- Backend: 8000
- Auth: 8081
- Frontend: 3000
- Postgres: 5433
- Redis: 6380
- ClickHouse: 8124
```

**Problem**: UnifiedDockerManager's DynamicPortAllocator doesn't properly isolate environments

### 3. Service Naming Inconsistencies
**Issue**: Docker container names differ between environments
- **Development**: `netra-core-generation-1-dev-dev-{service}-1`
- **Test**: `netra-core-generation-1-test-{service}-1`
- **Production**: Different prefixes entirely

**Impact**: Service discovery failures when UnifiedDockerManager searches for wrong container names

### 4. Health Check Configuration Deltas
**Issue**: Inconsistent health check configurations
- **Development**: Uses `pg_isready -U $$POSTGRES_USER` (variable interpolation)
- **Test**: Uses `pg_isready -U test_user -d netra_test` (hardcoded)
- **Timeout Values**: Different across environments (30s dev vs 20s test)

### 5. Memory Limits Discrepancies
**Issue**: Memory limits vary significantly
- **Development Postgres**: 512MB limit, 256MB reservation
- **Test Postgres**: 512MB limit, 256MB reservation (same)
- **Auth Service Dev**: 1024MB (increased from 512MB)
- **Auth Service Test**: Not specified consistently

### 6. Image Naming Convention Issues
**Issue**: Different image naming patterns
- **Development**: `netra-dev-{service}:latest`
- **Test**: `netra-test-{service}:latest`
- **Alpine Test**: `netra-alpine-test-{service}:latest`

**Problem**: UnifiedDockerManager may attempt to use wrong images

### 7. Network Configuration Differences
**Issue**: Network isolation not properly enforced
- All services use `default` network
- No explicit network segmentation between test/dev
- Potential for cross-environment communication

### 8. Environment Variable Propagation
**Issue**: Inconsistent environment variable handling
- UnifiedDockerManager uses `IsolatedEnvironment`
- Docker Compose files use direct environment interpolation
- Mismatch in how credentials are passed to services

## Root Cause Analysis

### Primary Root Cause
The UnifiedDockerManager attempts to be a Single Source of Truth (SSOT) but lacks proper environment-specific configuration loading. It uses hardcoded service configurations that don't match the actual Docker Compose files.

### Contributing Factors
1. **No Central Configuration**: Each docker-compose file maintains its own configuration
2. **Dynamic Port Allocation Issues**: PortAllocator doesn't respect compose file port mappings
3. **Missing Environment Context**: UnifiedDockerManager doesn't properly detect which environment it's operating in
4. **Credential Management**: No unified credential management system

## Recommendations

### Immediate Actions (P0)

1. **Standardize Database Credentials**
   ```python
   # In UnifiedDockerManager
   ENVIRONMENT_CREDENTIALS = {
       EnvironmentType.DEVELOPMENT: {
           "postgres_user": "netra",
           "postgres_password": "netra123",
           "postgres_db": "netra_dev"
       },
       EnvironmentType.TEST: {
           "postgres_user": "test_user",
           "postgres_password": "test_pass",
           "postgres_db": "netra_test"
       }
   }
   ```

2. **Fix Port Discovery**
   - Update `_discover_ports_from_existing_containers` to properly parse container names
   - Ensure port allocator respects existing docker-compose port mappings

3. **Correct Service URLs**
   - Fix hardcoded connection strings in `_build_service_url`
   - Use environment-specific credentials

### Short-term Fixes (P1)

1. **Create Environment Configuration YAML**
   ```yaml
   # config/docker_environments.yaml
   environments:
     development:
       prefix: "dev"
       credentials:
         postgres_user: "netra"
         postgres_password: "netra123"
       ports:
         backend: 8000
         auth: 8081
     test:
       prefix: "test"
       credentials:
         postgres_user: "test_user"
         postgres_password: "test_pass"
       ports:
         backend: 8000
         auth: 8001
   ```

2. **Implement Environment Detection**
   ```python
   def detect_environment(self) -> EnvironmentType:
       # Check running containers
       # Check environment variables
       # Default to test for safety
   ```

3. **Add Configuration Validation**
   - Validate docker-compose files match expected configuration
   - Add startup checks for credential mismatches

### Long-term Solutions (P2)

1. **Unified Configuration System**
   - Single source of truth for all Docker configurations
   - Generate docker-compose files from central config
   - Use Docker Compose override files for environment-specific settings

2. **Service Registry**
   - Implement service registry for dynamic discovery
   - Use Docker labels for service identification
   - Remove hardcoded container name patterns

3. **Proper Test Isolation**
   - Use Docker networks for environment isolation
   - Implement namespace-based container naming
   - Add environment prefixes to all resources

## Validation Checklist

- [ ] All services start without port conflicts
- [ ] Database connections use correct credentials
- [ ] Health checks pass within timeout periods
- [ ] No cross-environment communication
- [ ] Consistent memory limits applied
- [ ] Proper image selection per environment
- [ ] Environment variables correctly propagated
- [ ] Service discovery works reliably

## Testing Recommendations

1. **Create Integration Test**
   ```python
   def test_environment_isolation():
       # Start dev environment
       # Start test environment
       # Verify no conflicts
       # Verify correct credentials used
   ```

2. **Add Smoke Tests**
   - Verify each environment can start independently
   - Check service connectivity with correct credentials
   - Validate port allocations don't conflict

3. **Monitor Resource Usage**
   - Track memory usage vs limits
   - Monitor port allocation patterns
   - Log credential usage attempts

## Conclusion

The Docker unified system has fundamental configuration management issues causing crashes between test and development environments. The primary issue is the lack of environment-aware configuration in UnifiedDockerManager, leading to credential mismatches and port conflicts.

Implementing the recommended immediate actions will stabilize the system, while the long-term solutions will prevent future configuration drift.

## Appendix: File References

### Critical Files to Review
1. `test_framework/unified_docker_manager.py` - Lines 117-124 (SERVICE_CONFIGS)
2. `test_framework/dynamic_port_allocator.py` - Lines 117-124 (port configs)
3. `docker-compose.yml` - Development environment configuration
4. `docker-compose.test.yml` - Test environment configuration
5. `docker-compose.alpine-test.yml` - Alpine test configuration

### Configuration Sync Points
- UnifiedDockerManager.SERVICES (line 208-244)
- DynamicPortAllocator.SERVICE_CONFIGS (line 117-124)
- Docker Compose service definitions (multiple files)

---
*Report Generated: 2025-09-02*
*Severity: CRITICAL*
*Action Required: IMMEDIATE*