# 🚨 CRITICAL: E2E Docker Test Failures - Five Whys Deep Analysis

## Executive Summary: LIFE OR DEATH SITUATION
The E2E tests are failing due to cascading infrastructure issues. Our agent tests - the core business value - cannot run reliably.

## FIVE WHYS ROOT CAUSE ANALYSIS

### Problem: E2E Agent Tests Keep Failing on Local Docker

#### Why #1: Tests fail with "No such container" and connection errors
**Observation:** Docker compose starts services but then fails with container not found errors
**Evidence:** `Error response from daemon: No such container: a72f16f5edc0f2bf7fc86e61ce1bf49ffbe17edb54cd99f585c4f711f0ee06d3`

#### Why #2: Docker containers are being started but not properly tracked
**Observation:** The test runner creates unique project names but loses container references
**Evidence:** `netra-e2e-test-unified-runner-1757100039` creates containers but can't access them
**Root Issue:** Race condition between container creation and health checks

#### Why #3: Health checks are timing out before services are ready
**Observation:** Services have `start_period: 30s-90s` but tests try to connect immediately
**Evidence:** Alpine containers need more startup time than allocated
**Critical Finding:** ClickHouse needs 90s start_period but tests wait max 60s

#### Why #4: Memory limits are too restrictive for agent workloads
**Current Limits:**
- Backend: 2G limit, 1G reservation
- Auth: 2G limit, 1G reservation  
- PostgreSQL: 1G limit, 512M reservation
- ClickHouse: 1G limit, 512M reservation

**Problem:** Agent tests spawn multiple LLM calls and tool executions that spike memory usage
**Evidence:** Services likely OOM-killing during complex agent operations

#### Why #5: The system wasn't designed for multi-user concurrent agent execution
**Root Cause:** Original single-user design doesn't account for:
- Multiple WebSocket connections per test
- Concurrent agent executions
- Factory pattern overhead (new instances per request)
- LLM response buffering in memory

## CRITICAL MEMORY CALCULATIONS

### Current Total Memory Budget: ~7.5GB
- Backend: 2G
- Auth: 2G  
- PostgreSQL: 1G
- ClickHouse: 1G
- Redis: 512M
- Frontend: 512M
- OS/Docker overhead: ~500M

### Agent Test Memory Requirements (Per Test):
- LLM response buffering: ~500MB per agent
- WebSocket connection: ~50MB
- Tool execution context: ~200MB
- Database connections: ~100MB
**Total per concurrent test: ~850MB**

### For 5 Critical Tests Running Concurrently:
- 5 tests × 850MB = 4.25GB just for tests
- Plus base services = 11.75GB total
**EXCEEDS most development machines!**

## TOP 5 MOST CRITICAL AGENT TESTS (MUST WORK)

Based on business value and WebSocket event coverage:

1. **test_websocket_agent_events_suite.py** - $500K+ ARR impact
   - Tests all 5 critical WebSocket events
   - Validates real-time agent communication
   
2. **test_agent_orchestration_real_llm.py** - Core agent execution
   - Tests ExecutionEngine with real LLM
   - Validates tool dispatcher integration
   
3. **test_agent_websocket_events_comprehensive.py** - Full event flow
   - Tests complete agent lifecycle
   - Validates all event types and sequences
   
4. **test_agent_message_flow_implementation.py** - User chat flow
   - Tests end-to-end message processing
   - Validates response streaming
   
5. **test_agent_write_review_refine_integration_core.py** - Multi-agent collaboration
   - Tests agent workflow execution
   - Validates state management

## IMMEDIATE FIXES REQUIRED

### 1. Increase Memory Allocations (CRITICAL)
```yaml
# PRODUCTION-READY MEMORY SETTINGS
backend:
  limits: 4G      # Was 2G - DOUBLE IT
  reservations: 2G # Was 1G - DOUBLE IT

auth:
  limits: 3G      # Was 2G - 50% increase  
  reservations: 1.5G # Was 1G

postgres:
  limits: 2G      # Was 1G - DOUBLE IT
  reservations: 1G # Was 512M

clickhouse:
  limits: 2G      # Was 1G - DOUBLE IT
  reservations: 1G # Was 512M

redis:
  limits: 1G      # Was 512M - DOUBLE IT
  reservations: 512M # Was 256M
```

### 2. Fix Health Check Timeouts
```yaml
healthcheck:
  interval: 10s     # Check every 10s
  timeout: 10s      # Allow 10s per check (was 3-5s)
  retries: 30       # Try 30 times (was 10-15)
  start_period: 120s # CRITICAL: 2 minutes startup (was 30-90s)
```

### 3. Optimize Container Startup Order
```yaml
depends_on:
  postgres:
    condition: service_healthy
    restart: true  # Auto-restart if health check fails
  redis:
    condition: service_healthy
    restart: true
  clickhouse:
    condition: service_started  # Don't wait for slow ClickHouse
```

### 4. Add Memory Monitoring
```python
# Add to test setup
def monitor_memory_usage():
    """Track memory usage during tests."""
    import psutil
    process = psutil.Process()
    return {
        'rss': process.memory_info().rss / 1024 / 1024,  # MB
        'vms': process.memory_info().vms / 1024 / 1024,  # MB
        'available': psutil.virtual_memory().available / 1024 / 1024  # MB
    }
```

### 5. Implement Test Isolation
```python
# Run critical tests sequentially, not in parallel
CRITICAL_TESTS = [
    'test_websocket_agent_events_suite.py',
    'test_agent_orchestration_real_llm.py',
    # ... etc
]

for test in CRITICAL_TESTS:
    cleanup_docker()
    start_fresh_containers()
    run_single_test(test)
    collect_results()
```

## BUSINESS IMPACT IF NOT FIXED

- **Revenue Loss:** $500K+ ARR at risk (chat functionality broken)
- **User Experience:** Complete failure of AI agent interactions
- **Development Velocity:** Team blocked on testing
- **Production Risk:** Untested code reaching production
- **Customer Churn:** Users leave due to unreliable agents

## NEXT STEPS (IN ORDER)

1. ✅ Docker daemon must be running
2. 🔧 Update docker-compose.alpine-test.yml with new memory limits
3. 🔧 Fix health check timeouts
4. 🔧 Run top 5 tests individually with monitoring
5. 🔧 Implement permanent fixes in UnifiedDockerManager

This is LIFE OR DEATH for the product. These tests MUST work.