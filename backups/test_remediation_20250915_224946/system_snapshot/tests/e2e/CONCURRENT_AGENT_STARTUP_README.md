# Concurrent Agent Startup Test Suite

## Overview

This test suite implements comprehensive validation of concurrent agent startup isolation with 100+ users, ensuring complete multi-tenant security and data isolation for the Netra Apex platform.

## Business Value

**Business Value Justification (BVJ):**
- **Segment**: Enterprise (multi-tenant isolation requirements)
- **Business Goal**: Ensure secure multi-tenant agent isolation at scale
- **Value Impact**: Prevents security breaches and data leaks between 100+ concurrent customers
- **Revenue Impact**: Enterprise trust required for $500K+ multi-tenant contracts

## Test Cases

### 1. Basic Concurrent Agent Startup Isolation
- **Objective**: Verify 100 users can start agents simultaneously with complete isolation
- **Success Criteria**: 
  - 100 unique agent instances created (no ID collisions)
  - Each agent maintains separate context data
  - No cross-user data contamination detected
  - Response time per agent startup < 5 seconds

### 2. Cross-Contamination Detection
- **Objective**: Detect any data leakage between concurrent user sessions
- **Success Criteria**:
  - Zero instances of cross-user data access
  - Each user's sensitive data remains isolated
  - Agent state queries return only user-specific data

### 3. Performance Under Concurrent Load
- **Objective**: Validate system performance meets SLA requirements under 100 user load
- **Success Criteria**:
  - P95 agent startup time < 5 seconds
  - P99 agent startup time < 8 seconds
  - System memory usage < 4GB total
  - CPU usage < 80% during test execution

### 4. WebSocket Connection Scaling
- **Objective**: Verify WebSocket infrastructure can handle 100+ concurrent connections
- **Success Criteria**:
  - 100 stable WebSocket connections established
  - Message routing accuracy 100%
  - No connection drops during test execution

### 5. State Persistence Isolation
- **Objective**: Verify agent state persistence maintains isolation between users
- **Success Criteria**:
  - Each user can only access their own state
  - State queries filtered by user authentication
  - No unauthorized state modification possible

## Prerequisites

### Infrastructure Requirements
- **PostgreSQL**: Dedicated test database with connection pooling (min 50 connections)
- **Redis**: Isolated test instance with separate keyspace prefix
- **ClickHouse**: Test database for metrics isolation validation
- **WebSocket Manager**: Real WebSocket infrastructure with 100+ concurrent connections
- **Auth Service**: Mock or isolated auth service for token generation

### Resource Requirements
- **Memory**: Minimum 8GB available for test execution
- **CPU**: 4+ cores for parallel user simulation
- **Network**: Stable connection for WebSocket testing
- **Disk**: 2GB temporary storage for test artifacts

### Environment Variables

```bash
# Test Database Configuration
TEST_DATABASE_URL=postgresql://test_user:test_pass@localhost:5433/netra_test
TEST_REDIS_URL=redis://localhost:6380/1
TEST_CLICKHOUSE_URL=http://localhost:8124/netra_test

# Concurrent Testing Configuration  
CONCURRENT_TEST_USERS=100
CONCURRENT_TEST_TIMEOUT=300
AGENT_STARTUP_TIMEOUT=30
ISOLATION_VALIDATION_STRICT=true

# Performance Thresholds
MAX_AGENT_STARTUP_TIME=5000  # 5 seconds per agent
MAX_TOTAL_TEST_TIME=180000   # 3 minutes total
MIN_SUCCESS_RATE=95          # 95% minimum success rate

# E2E Service URLs
E2E_AUTH_SERVICE_URL=http://localhost:8001
E2E_BACKEND_URL=http://localhost:8000
E2E_WEBSOCKET_URL=ws://localhost:8000/ws
E2E_REDIS_URL=redis://localhost:6379
E2E_POSTGRES_URL=postgresql://postgres:netra@localhost:5432/netra_test

# Enable E2E Tests
RUN_E2E_TESTS=true
USE_REAL_SERVICES=true
```

## Running the Tests

### Quick Start

```bash
# Run full test suite with 100 users
python tests/e2e/run_concurrent_agent_startup_tests.py

# Quick test with 20 users
python tests/e2e/run_concurrent_agent_startup_tests.py --quick

# Performance-focused test
python tests/e2e/run_concurrent_agent_startup_tests.py --performance-only

# Isolation-focused test
python tests/e2e/run_concurrent_agent_startup_tests.py --isolation-only
```

### Using pytest directly

```bash
# Run all concurrent startup tests
pytest tests/e2e/test_concurrent_agent_startup.py -v

# Run specific test case
pytest tests/e2e/test_concurrent_agent_startup.py::test_concurrent_agent_startup_isolation -v

# Run with custom configuration
CONCURRENT_TEST_USERS=50 pytest tests/e2e/test_concurrent_agent_startup.py -v
```

### Advanced Usage

```bash
# Verbose mode with detailed logging
python tests/e2e/run_concurrent_agent_startup_tests.py --verbose --report-file results.json

# Custom user count and timeout
python tests/e2e/run_concurrent_agent_startup_tests.py --users 50 --timeout 180

# Performance benchmarking
python tests/e2e/run_concurrent_agent_startup_tests.py --performance-only --users 200
```

## Test Architecture

### Key Components

1. **ConcurrentTestEnvironment**: Manages test environment setup and cleanup
2. **ConcurrentTestOrchestrator**: Orchestrates concurrent user operations
3. **PerformanceMetricsCollector**: Collects comprehensive performance metrics
4. **CrossContaminationDetector**: Detects data leakage between users
5. **TestUser**: Represents individual test users with unique data

### Test Flow

1. **Environment Setup**: Initialize databases, Redis, and service connections
2. **User Creation**: Generate 100 unique test users with distinct data
3. **Concurrent Execution**: Establish WebSocket connections and send messages simultaneously
4. **Isolation Validation**: Verify complete isolation between user sessions
5. **Performance Analysis**: Collect and validate performance metrics
6. **Cleanup**: Clean up all test data and connections

## Monitoring and Debugging

### Logging
- Test execution logs are written to `concurrent_test_run.log`
- Use `--verbose` flag for detailed debug information
- Performance metrics are logged during test execution

### Performance Metrics
- Agent startup times (P95, P99, average)
- System resource usage (memory, CPU)
- WebSocket connection stability
- Database operation timing

### Troubleshooting

#### Common Issues

1. **Service Unavailable**: Ensure all required services are running
   ```bash
   # Check service health
   curl http://localhost:8001/health  # Auth service
   curl http://localhost:8000/health  # Backend service
   ```

2. **Database Connection Issues**: Verify database configuration
   ```bash
   # Test PostgreSQL connection
   psql postgresql://postgres:netra@localhost:5432/netra_test -c "SELECT 1;"
   ```

3. **Memory/Resource Issues**: Reduce user count or increase system resources
   ```bash
   # Run with fewer users
   python tests/e2e/run_concurrent_agent_startup_tests.py --users 20
   ```

4. **Timeout Issues**: Increase timeout values
   ```bash
   # Increase timeouts
   CONCURRENT_TEST_TIMEOUT=600 python tests/e2e/run_concurrent_agent_startup_tests.py
   ```

## Performance Expectations

### Success Criteria Thresholds
- **P95 agent startup time**: < 5 seconds
- **P99 agent startup time**: < 8 seconds
- **System memory usage**: < 4GB total
- **CPU usage**: < 80% during test execution
- **Success rate**: ≥ 95% of agent startups successful
- **Total test time**: < 3 minutes for 100 users

### Typical Performance
- **Average startup time**: 2-3 seconds per agent
- **Memory usage**: 2-3GB during peak execution
- **CPU usage**: 40-60% during concurrent operations
- **WebSocket connections**: 100% success rate expected

## Integration with CI/CD

### GitHub Actions Integration

```yaml
name: Concurrent Agent Startup Tests
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  concurrent-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: netra
          POSTGRES_DB: netra_test
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
      
      redis:
        image: redis:7
        options: --health-cmd "redis-cli ping" --health-interval 10s --health-timeout 5s --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run concurrent startup tests
        run: |
          python tests/e2e/run_concurrent_agent_startup_tests.py --report-file concurrent-test-results.json
        env:
          RUN_E2E_TESTS: true
          CONCURRENT_TEST_USERS: 50  # Reduced for CI
          E2E_POSTGRES_URL: postgresql://postgres:netra@localhost:5432/netra_test
          E2E_REDIS_URL: redis://localhost:6379
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: concurrent-test-results
          path: concurrent-test-results.json
```

## Contributing

When modifying these tests:

1. **Maintain Architectural Compliance**: Follow the <300 line file size limit
2. **Preserve Business Value**: Ensure changes align with enterprise isolation requirements
3. **Update Documentation**: Keep this README current with any changes
4. **Test Locally**: Always run tests locally before committing
5. **Performance Impact**: Consider performance implications of changes

## Support

For issues or questions regarding this test suite:

1. Check the troubleshooting section above
2. Review test execution logs
3. Validate environment configuration
4. Ensure all prerequisites are met
5. Contact the platform team for infrastructure issues