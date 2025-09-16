# Testing During Infrastructure Outages - Issue #1278

This guide explains how to run tests when staging infrastructure is experiencing connectivity issues, specifically during VPC connector and Cloud SQL problems.

## Quick Start

### 1. Use Resilient Test Configuration

```bash
# Copy the resilient configuration
cp config/.env.test.resilient config/.env.test.active

# Run tests with enhanced resilience
pytest tests/ --tb=short -v
```

### 2. Check Infrastructure Health First

```python
from test_framework.resilience import validate_infrastructure_health

# Quick health check
health = await validate_infrastructure_health()
print(f"Infrastructure status: {health.overall_status}")

if health.should_use_fallback:
    print("Using fallback configuration due to infrastructure issues")
```

## Infrastructure Outage Scenarios

### Scenario 1: Staging Database Unavailable (Most Common)

**Symptoms:**
- Connection timeouts to `10.52.0.3:5432`
- Cloud SQL proxy connection errors
- VPC connector failures

**Solution:**
```bash
# Set fallback environment variables
export DATABASE_MODE=local
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5435
export INFRASTRUCTURE_DEGRADED_MODE=true

# Run tests with local database
pytest tests/unit/ tests/integration/ -v
```

### Scenario 2: Complete Staging Unavailability

**Symptoms:**
- Backend API returns 502/503 errors
- WebSocket connections fail
- Multiple service timeouts

**Solution:**
```bash
# Enable full offline mode
export NO_REAL_SERVERS=true
export TEST_OFFLINE=true
export WEBSOCKET_MOCK_MODE=true

# Run unit and integration tests only
pytest tests/unit/ tests/integration/ -m "not staging" -v
```

### Scenario 3: WebSocket Service Degraded

**Symptoms:**
- WebSocket connection timeouts
- Event delivery failures
- Agent execution timeouts

**Solution:**
```bash
# Enable WebSocket mock mode
export WEBSOCKET_MOCK_MODE=true
export AGENT_EXECUTION_TIMEOUT=20

# Run tests with WebSocket mocking
pytest tests/ -m "not real_services" -v
```

## Enhanced Test Execution Modes

### 1. Full Mode (All Services Available)
```bash
# Default mode when infrastructure is healthy
pytest tests/e2e/staging/ -v
```

### 2. Degraded Mode (Some Services Available)
```bash
# Automatically detected and applied
export INFRASTRUCTURE_DEGRADED_MODE=true
pytest tests/ --tb=short -v
```

### 3. Offline Mode (No External Services)
```bash
# Complete local testing
export TEST_OFFLINE=true
export NO_REAL_SERVERS=true
pytest tests/unit/ tests/integration/ -v
```

### 4. Critical Only Mode (Essential Tests Only)
```bash
# Run only business-critical tests
export TEST_CRITICAL_ONLY=true
pytest tests/ -m "critical or mission_critical" -v
```

## Automated Infrastructure Health Checks

### Pre-Test Validation

```python
from test_framework.resilience import ResilientTestRunner

# Create resilient test runner
runner = ResilientTestRunner()

# Assess infrastructure health
health = await runner.assess_infrastructure_health()

if health.should_skip_tests:
    print("Skipping tests due to critical infrastructure failures")
    exit(0)

# Apply resilient configuration
execution_mode = runner.determine_execution_mode(health)
runner.apply_resilient_configuration(health, execution_mode)

print(f"Running tests in {execution_mode.value} mode")
```

### Health Check Output Examples

```
INFO: Service database: available (0.123s)
INFO: Service backend_api: degraded (2.456s)
WARNING: Service websocket: unavailable (10.000s)
INFO: Infrastructure health assessment complete: degraded

INFO: Applied resilient configuration for degraded mode
INFO: Falling back to local Redis due to unavailability
INFO: Enabling WebSocket mock mode due to service unavailability
```

## Configuration Files Reference

### Primary Configurations

1. **`.env.test.resilient`** - Enhanced resilience configuration
   - Graceful degradation settings
   - Aggressive timeout configurations
   - Fallback service endpoints

2. **`.env.test.local`** - Local services fallback
   - Local PostgreSQL, Redis, ClickHouse
   - Mocked external services
   - Isolated testing environment

3. **`.env.test.minimal`** - Minimal dependencies
   - Essential services only
   - Fastest startup time
   - Critical path testing

### Environment Variable Quick Reference

```bash
# Infrastructure Resilience
INFRASTRUCTURE_DEGRADED_MODE=true
CONNECTIVITY_RESILIENCE_ENABLED=true
STAGING_CONNECTIVITY_FALLBACK=true

# Service Fallbacks
DATABASE_MODE=local
REDIS_MODE=local
LLM_FALLBACK_MODE=true
AUTH_FALLBACK_MODE=true

# Timeout Optimization
INFRASTRUCTURE_HEALTH_CHECK_TIMEOUT=5
STAGING_CONNECTION_TIMEOUT=10
WEBSOCKET_CONNECTION_TIMEOUT=30

# Test Framework Resilience
TEST_RETRY_ATTEMPTS=3
TEST_RETRY_DELAY=2
TEST_SKIP_ON_INFRASTRUCTURE_FAILURE=true
TEST_GRACEFUL_DEGRADATION=true
```

## Retry and Timeout Strategies

### Automatic Retry Logic

The resilient test runner automatically retries tests that fail due to:
- Connection timeouts
- Network unreachable errors
- Service unavailable responses
- Temporary infrastructure failures

```python
# Configuration
TEST_RETRY_ATTEMPTS=3        # Number of retry attempts
TEST_RETRY_DELAY=2          # Delay between retries (seconds)

# Retryable error patterns
- "connection refused"
- "connection timeout"
- "network unreachable"
- "service unavailable"
- "502 bad gateway"
- "503 service unavailable"
```

### Enhanced Timeout Configuration

```bash
# Aggressive timeouts for connectivity detection
INFRASTRUCTURE_HEALTH_CHECK_TIMEOUT=5
STAGING_CONNECTION_TIMEOUT=10
FALLBACK_ACTIVATION_TIMEOUT=3

# Optimized for intermittent connectivity
WEBSOCKET_CONNECTION_TIMEOUT=30
WEBSOCKET_RECV_TIMEOUT=20
WEBSOCKET_SEND_TIMEOUT=15

# Shortened for resilience
AGENT_EXECUTION_TIMEOUT=20
AGENT_THINKING_TIMEOUT=15
AGENT_TOOL_TIMEOUT=10
```

## Running Tests During Specific Infrastructure Issues

### Issue #1278: VPC Connector / Cloud SQL Failures

```bash
# Enable Issue #1278 specific workarounds
export ISSUE_1278_WORKAROUND_ENABLED=true
export VPC_CONNECTOR_BYPASS_MODE=true
export CLOUD_SQL_FALLBACK_MODE=true

# Use local database instead of Cloud SQL
export DATABASE_MODE=local
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5435

# Run tests with VPC connector bypass
pytest tests/ --tb=short -v
```

### Network Connectivity Issues

```bash
# Enable full offline mode
export TEST_OFFLINE=true
export NO_REAL_SERVERS=true

# Run offline-capable tests only
pytest tests/unit/ tests/integration/ -m "not real_services and not staging" -v
```

### Redis/ClickHouse Unavailability

```bash
# Use local Redis and ClickHouse
export REDIS_MODE=local
export CLICKHOUSE_MODE=local

# Skip tests requiring external analytics
pytest tests/ -m "not real_database and not clickhouse" -v
```

## Test Execution Examples

### Example 1: Full Resilient Test Run

```bash
#!/bin/bash
# run_resilient_tests.sh

# Load resilient configuration
source config/.env.test.resilient

# Run infrastructure health check
python -c "
import asyncio
from test_framework.resilience import validate_infrastructure_health

async def main():
    health = await validate_infrastructure_health()
    print(f'Infrastructure status: {health.overall_status.value}')
    if not health.is_staging_available:
        print('Staging unavailable - using fallback configuration')
    exit(0 if health.should_skip_tests else 0)

asyncio.run(main())
"

# Run tests with resilience
pytest tests/ --tb=short -v \
    --maxfail=5 \
    --durations=10 \
    -m "not slow"
```

### Example 2: Critical Path Testing Only

```bash
#!/bin/bash
# run_critical_tests.sh

# Enable critical-only mode
export TEST_CRITICAL_ONLY=true
export SKIP_NON_CRITICAL_TESTS=true

# Run business-critical tests only
pytest tests/ \
    -m "critical or mission_critical or golden_path" \
    --tb=short \
    -v
```

### Example 3: Development Workflow During Outages

```bash
#!/bin/bash
# dev_workflow_during_outage.sh

echo "Checking infrastructure health..."

# Quick health check
python -c "
import asyncio
from test_framework.resilience import validate_critical_services

async def main():
    health = await validate_critical_services()
    print(f'Critical services: {health.overall_status.value}')
    if health.should_use_fallback:
        print('Using fallback configuration')

asyncio.run(main())
"

# Load resilient configuration
cp config/.env.test.resilient .env

# Run development tests
pytest tests/unit/ tests/integration/ \
    -x \
    --tb=short \
    -q \
    -m "not staging"

echo "Development tests complete"
```

## Monitoring and Alerts

### Infrastructure Health Monitoring

```python
from test_framework.resilience import TestConnectivityValidator

# Create validator with monitoring
validator = TestConnectivityValidator()

# Continuous health monitoring
while True:
    health = await validator.validate_all_services()

    if health.overall_status == ConnectivityStatus.UNAVAILABLE:
        print("ALERT: Critical infrastructure failure detected")
        # Send alert notification

    elif health.overall_status == ConnectivityStatus.DEGRADED:
        print("WARNING: Infrastructure degradation detected")

    await asyncio.sleep(300)  # Check every 5 minutes
```

### Test Result Analysis

```python
from test_framework.resilience import ResilientTestRunner

# Run tests and generate report
runner = ResilientTestRunner()
result = await runner.run_test_suite(test_commands)

# Generate comprehensive report
report = runner.generate_resilience_report(result)
print(report)

# Check for infrastructure-related failures
infra_failures = result.infrastructure_unavailable_tests
if infra_failures > 0:
    print(f"WARNING: {infra_failures} tests skipped due to infrastructure issues")
```

## Troubleshooting Common Issues

### Problem: Tests timing out during infrastructure issues

**Solution:**
```bash
# Reduce timeouts for faster failure detection
export INFRASTRUCTURE_HEALTH_CHECK_TIMEOUT=3
export STAGING_CONNECTION_TIMEOUT=5
export TEST_RETRY_ATTEMPTS=2
```

### Problem: Too many tests being skipped

**Solution:**
```bash
# Disable aggressive skipping
export TEST_SKIP_ON_INFRASTRUCTURE_FAILURE=false
export TEST_GRACEFUL_DEGRADATION=true

# Run with more lenient criteria
pytest tests/ --maxfail=10 -v
```

### Problem: Local services not starting

**Solution:**
```bash
# Check local service containers
docker ps | grep -E "(postgres|redis|clickhouse)"

# Restart services if needed
docker-compose -f docker/docker-compose.local.yml up -d

# Verify connectivity
python -c "
import asyncio
from test_framework.resilience import validate_infrastructure_health
asyncio.run(validate_infrastructure_health())
"
```

### Problem: WebSocket tests failing

**Solution:**
```bash
# Enable WebSocket mock mode
export WEBSOCKET_MOCK_MODE=true
export NO_REAL_SERVERS=true

# Run WebSocket tests with mocking
pytest tests/ -k "websocket" -v
```

## Best Practices

### 1. Always Check Infrastructure Health First

```python
# At the start of test sessions
health = await validate_infrastructure_health()
if health.should_skip_tests:
    pytest.skip("Infrastructure unavailable")
```

### 2. Use Appropriate Test Markers

```python
# Mark tests appropriately
@pytest.mark.staging
@pytest.mark.real_services
def test_staging_functionality():
    pass

@pytest.mark.critical
@pytest.mark.offline_capable
def test_critical_functionality():
    pass
```

### 3. Implement Graceful Degradation

```python
# Check service availability in tests
if not is_service_available("staging_backend"):
    pytest.skip("Staging backend unavailable")
```

### 4. Monitor Test Execution Patterns

```bash
# Use resilient test runner for comprehensive reporting
python -c "
import asyncio
from test_framework.resilience import run_tests_with_resilience

asyncio.run(run_tests_with_resilience([
    'pytest tests/unit/',
    'pytest tests/integration/',
    'pytest tests/e2e/ -m critical'
]))
"
```

## Recovery Procedures

### When Infrastructure Recovers

1. **Validate Recovery**
   ```bash
   python -c "
   import asyncio
   from test_framework.resilience import validate_infrastructure_health

   async def main():
       health = await validate_infrastructure_health()
       print(f'Status: {health.overall_status.value}')
       if health.overall_status.value == 'available':
           print('Infrastructure recovery confirmed')

   asyncio.run(main())
   "
   ```

2. **Switch Back to Full Configuration**
   ```bash
   # Remove degraded mode settings
   unset INFRASTRUCTURE_DEGRADED_MODE
   unset TEST_OFFLINE
   unset WEBSOCKET_MOCK_MODE

   # Load standard test configuration
   cp config/.env.test.local .env
   ```

3. **Run Full Test Suite**
   ```bash
   # Comprehensive test run to verify recovery
   pytest tests/ --tb=short -v --durations=20
   ```

## Support and Escalation

### When to Escalate Infrastructure Issues

1. **Critical services down for > 30 minutes**
2. **Multiple consecutive test suite failures**
3. **VPC connector or Cloud SQL persistent errors**
4. **Complete staging environment unavailability**

### Escalation Contact Information

- **Infrastructure Team:** Create GitHub issue with label `infrastructure`
- **DevOps Team:** Tag `@devops` in related issues
- **Issue #1278 Tracking:** Add comment to existing issue

### Incident Response

```bash
# Quick incident assessment
python -c "
import asyncio
from test_framework.resilience import assess_test_infrastructure_health

async def main():
    health = await assess_test_infrastructure_health()

    print('INCIDENT ASSESSMENT')
    print(f'Overall Status: {health.overall_status.value}')
    print(f'Staging Available: {health.is_staging_available}')
    print(f'Should Skip Tests: {health.should_skip_tests}')

    unavailable = health.get_unavailable_services()
    if unavailable:
        print(f'Unavailable Services: {[s.value for s in unavailable]}')

asyncio.run(main())
"
```

---

*This documentation is maintained as part of Issue #1278 resolution efforts. Last updated: September 2024*