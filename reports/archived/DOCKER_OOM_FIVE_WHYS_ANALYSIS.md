# Docker OOM (Out of Memory) Issues - Five Whys Analysis

## Executive Summary
Docker containers are experiencing OOM kills during testing, causing test failures and instability. This analysis uses the Five Whys method to identify root causes and propose solutions.

## Current State Analysis

### Memory Configuration Observed:

1. **Regular Test Environment** (`docker-compose.test.yml`):
   - PostgreSQL: 512MB limit, 256MB reserved
   - Redis: No explicit limit (uses maxmemory 512mb internally)
   - Backend: 2GB limit, 1GB reserved
   - Auth: 1GB limit, 512MB reserved
   - Frontend: 1GB limit, 512MB reserved

2. **Alpine Test Environment** (`docker-compose.alpine-test.yml`):
   - PostgreSQL: 1GB limit, 512MB reserved
   - Redis: 512MB limit, 256MB reserved
   - ClickHouse: 1GB limit, 512MB reserved
   - Backend: **4GB limit**, 2GB reserved
   - Auth: 2GB limit, 1GB reserved
   - Frontend: 512MB limit, 256MB reserved

## Five Whys Analysis

### Problem: Docker containers are being OOM killed during tests

**Why #1: Why are containers being OOM killed?**
- Containers are exceeding their memory limits during test execution
- Evidence: Alpine backend has 4GB limit (highest), regular backend has 2GB limit
- Total potential memory usage: ~10GB in Alpine environment if all services max out

**Why #2: Why are containers exceeding memory limits?**
- Multiple factors contribute:
  1. Test framework overhead (pytest collection, fixtures)
  2. Concurrent service execution without coordination
  3. Memory-intensive operations (LLM calls, database operations)
  4. No memory pooling or sharing between containers

**Why #3: Why is there no memory coordination between containers?**
- Each container has fixed limits regardless of actual usage patterns
- Docker Compose doesn't dynamically adjust memory based on system availability
- Test runner doesn't check available memory before starting services
- Services start simultaneously without staged rollout

**Why #4: Why don't we have dynamic memory management?**
- Current architecture assumptions:
  1. Fixed memory limits provide predictability
  2. All services need to run simultaneously
  3. Host system has sufficient memory (>16GB assumed)
  4. No memory monitoring or adjustment mechanisms implemented

**Why #5: Why was the system designed with these assumptions?**
- Root causes identified:
  1. **Development vs Testing Environment Mismatch**: Developers likely have 32GB+ RAM, CI/test environments may have less
  2. **Lack of Memory Profiling**: No baseline memory usage data for realistic test scenarios
  3. **Over-provisioning**: Conservative limits set too high for safety
  4. **Missing Resource Orchestration**: No intelligent service startup/shutdown based on test needs

## Root Cause Summary

### Primary Root Causes:
1. **Over-allocation**: Total memory limits (10GB+) exceed typical test environment capacity
2. **Static Allocation**: Fixed limits don't adapt to actual usage patterns
3. **Simultaneous Startup**: All services start together, creating memory spike
4. **No Memory Monitoring**: Test framework doesn't track or respond to memory pressure
5. **Alpine Backend Over-provisioned**: 4GB limit for backend is excessive for test scenarios

## Recommended Solutions

### Immediate Fixes (Quick Wins):

1. **Reduce Alpine Backend Memory Limit**:
   - Change from 4GB to 2GB (matching regular test environment)
   - This alone saves 2GB of potential allocation

2. **Implement Staged Service Startup**:
   - Start infrastructure services first (Postgres, Redis)
   - Wait for health checks
   - Then start application services
   - Reduces peak memory usage

3. **Add Memory Pre-flight Check**:
   ```python
   def check_available_memory():
       available = psutil.virtual_memory().available
       required = calculate_required_memory()
       if available < required:
           raise MemoryError(f"Insufficient memory: {available}MB available, {required}MB required")
   ```

### Medium-term Improvements:

1. **Dynamic Memory Allocation Based on Test Category**:
   - Unit tests: Minimal services (1GB total)
   - Integration tests: Core services (3GB total)
   - E2E tests: Full stack (5GB total)

2. **Service Lifecycle Management**:
   - Start services on-demand
   - Stop unused services during long tests
   - Implement service pooling for parallel tests

3. **Memory-Optimized Test Profiles**:
   ```yaml
   # docker-compose.test-minimal.yml
   services:
     test-postgres:
       deploy:
         resources:
           limits:
             memory: 256M  # Reduced for unit tests
   ```

### Long-term Solutions:

1. **Implement Memory Governor**:
   - Monitor real-time memory usage
   - Dynamically adjust container limits
   - Pause/resume services based on memory pressure

2. **Test Sharding with Resource Pools**:
   - Split tests into memory-bounded shards
   - Run shards sequentially on memory-constrained systems
   - Parallel execution only when memory permits

3. **Container Memory Profiling**:
   - Baseline actual memory usage per service
   - Set limits at 120% of peak observed usage
   - Regular profiling to detect memory leaks

## Implementation Priority

### Phase 1 (Immediate - Today):
```yaml
# Update docker-compose.alpine-test.yml
alpine-test-backend:
  deploy:
    resources:
      limits:
        memory: 2G  # Reduced from 4G
        
# Update docker-compose.test.yml  
test-postgres:
  deploy:
    resources:
      limits:
        memory: 256M  # Reduced from 512M for test scenarios
```

### Phase 2 (This Week):
- Implement memory pre-flight checks in test runner
- Add staged service startup
- Create minimal memory profile for unit tests

### Phase 3 (This Month):
- Deploy memory monitoring dashboard
- Implement dynamic service lifecycle management
- Create memory-optimized test profiles

## Monitoring & Validation

### Success Metrics:
- Zero OOM kills in standard test runs
- Test execution on 8GB systems
- 50% reduction in peak memory usage
- Faster test startup times

### Monitoring Commands:
```bash
# Real-time memory monitoring during tests
docker stats --no-stream
docker system df
free -h

# Per-container memory usage
docker inspect <container> | grep -i memory
```

## Conclusion

The Docker OOM issues stem from over-provisioned memory limits (especially Alpine backend at 4GB) combined with simultaneous service startup and lack of dynamic memory management. Immediate reduction of memory limits and staged startup will provide quick relief, while longer-term solutions involve dynamic resource management and memory-aware test orchestration.

**Total Memory Reduction Potential**: 
- Current: ~10GB total limits
- Optimized: ~5GB total limits  
- Minimal (unit tests): ~2GB total limits

This represents a 50-80% reduction in memory requirements while maintaining test reliability.