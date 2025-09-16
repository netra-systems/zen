# Backend Performance Testing Suite

Comprehensive performance testing framework for critical backend operations in the Netra Apex platform.

## Business Value Justification (BVJ)

- **Segment**: Growth & Enterprise
- **Business Goal**: Ensure scalable backend performance under realistic load
- **Value Impact**: 95%+ uptime, <2s response times, support for 100+ concurrent users
- **Revenue Impact**: Prevents performance-related churn and enables customer growth (+$50K MRR)

## Overview

This performance testing suite provides comprehensive coverage of critical backend operations:

1. **Database Performance** - ClickHouse and PostgreSQL query performance
2. **WebSocket Throughput** - Real-time message handling and broadcasting
3. **Agent Processing** - LLM-based agent response times and throughput
4. **API Response Times** - REST endpoint performance under load
5. **Concurrent Users** - Multi-user load handling and scalability
6. **Memory Usage** - Memory allocation, cleanup, and leak detection
7. **Cache Effectiveness** - Cache hit rates and response times

## Quick Start

### Run All Performance Tests

```bash
# Full comprehensive suite (recommended for CI/CD)
python app/tests/performance/run_performance_suite.py

# Quick mode for development (reduced test sizes)
python app/tests/performance/run_performance_suite.py --quick

# Run specific categories only
python app/tests/performance/run_performance_suite.py --categories database websocket agent
```

### Run Individual Test Modules

```bash
# Database performance tests
pytest app/tests/performance/test_comprehensive_backend_performance.py::TestComprehensiveBackendPerformance::test_database_performance_suite -v

# Concurrent user tests
pytest app/tests/performance/test_concurrent_user_performance.py::TestConcurrentUserPerformance::test_basic_concurrent_users -v

# Full performance benchmark
pytest app/tests/performance/test_comprehensive_backend_performance.py::TestComprehensiveBackendPerformance::test_performance_benchmark_suite -v
```

## Test Categories

### 1. Database Performance Tests

**File**: `test_comprehensive_backend_performance.py`

- **Bulk Insert Performance**: 50K record insertion timing
- **Concurrent Query Performance**: Multiple simultaneous database reads
- **Query Optimization**: Performance across different dataset sizes
- **Connection Pool Utilization**: Efficient connection reuse testing

**Key Metrics**:
- Bulk insert time: <30s for 50K records
- Concurrent read time: <5s for 10 parallel queries
- Query response time: <5s regardless of table size

### 2. WebSocket Performance Tests

**File**: `test_comprehensive_backend_performance.py`

- **Message Throughput**: Messages processed per second
- **Broadcast Performance**: Multi-connection message distribution
- **Connection Handling**: WebSocket connection establishment and management

**Key Metrics**:
- Throughput: >1000 messages/second
- Broadcast throughput: >5000 messages/second to 100 connections
- Connection time: <0.1s

### 3. Agent Processing Tests

**File**: `test_comprehensive_backend_performance.py`

- **Processing Speed**: Time to handle agent requests
- **Concurrent Processing**: Multiple agents working simultaneously
- **LLM Response Times**: AI model response performance

**Key Metrics**:
- Processing time: <10s for 100 requests
- Concurrent throughput: >20 requests/second
- LLM response time: <2s average

### 4. API Performance Tests

**File**: `test_comprehensive_backend_performance.py`

- **Response Times**: Individual API endpoint timing
- **Concurrent Load**: Performance under simultaneous requests
- **Throughput**: Requests processed per second

**Key Metrics**:
- Response time: <0.2s average
- Concurrent load: <20s for 1000 requests (50 concurrent)
- Throughput: >100 requests/second

### 5. Concurrent User Tests

**File**: `test_concurrent_user_performance.py`

- **Basic Load**: 25-100 concurrent users
- **Scaling Performance**: Performance as user count increases
- **Burst Capacity**: Handling sudden user spikes
- **Sustained Load**: Long-term stability testing

**Key Metrics**:
- Success rate: >99% (basic), >95% (high load)
- Response time: <2s (basic), <5s (high load)
- Max concurrent users: >100

### 6. Memory Performance Tests

**File**: `test_comprehensive_backend_performance.py`

- **Allocation Patterns**: Memory usage under different loads
- **Cleanup Performance**: Garbage collection timing
- **Memory Leak Detection**: Long-term memory stability

**Key Metrics**:
- Allocation time: <1s for 100MB
- Cleanup time: <0.1s average
- Peak usage: <512MB baseline

### 7. Cache Performance Tests

**File**: `test_comprehensive_backend_performance.py`

- **Hit Rate Testing**: Cache effectiveness measurement
- **Response Times**: Cache lookup performance
- **Load Testing**: Cache performance under concurrent access

**Key Metrics**:
- Hit rate: >80%
- Response time: <0.001s
- Concurrent access: <30s for 5000 operations

## Performance Baselines

### Critical Performance Requirements

| Component | Metric | Baseline | Warning | Critical |
|-----------|--------|----------|---------|----------|
| Database | Bulk Insert (50K) | <30s | <45s | <60s |
| Database | Concurrent Reads | <5s | <8s | <12s |
| WebSocket | Throughput | >1000 msg/s | >500 msg/s | >250 msg/s |
| Agents | Processing Time | <10s | <20s | <30s |
| API | Response Time | <0.2s | <1s | <2s |
| Concurrent | Success Rate | >99% | >95% | >90% |
| Memory | Allocation | <1s | <3s | <5s |
| Cache | Hit Rate | >80% | >60% | >40% |

### SLA Requirements

- **Uptime**: 99.9% availability
- **Response Time**: <2s for 95% of requests
- **Throughput**: Support 100+ concurrent users
- **Error Rate**: <0.1% under normal load
- **Memory**: <1GB peak usage per instance

## Configuration

### Performance Baseline Configuration

**File**: `performance_baseline_config.py`

Contains all performance metrics definitions, baseline values, and thresholds. Metrics are categorized and include:

- Baseline values (target performance)
- Warning thresholds (performance degradation alerts)
- Critical thresholds (unacceptable performance)
- Whether higher values are better (e.g., throughput vs response time)

### Test Execution Modes

#### Quick Mode (`--quick`)
- Reduced dataset sizes for faster execution
- Suitable for development and rapid feedback
- Typical runtime: 2-5 minutes

#### Full Mode (default)
- Complete dataset sizes for comprehensive testing
- Suitable for CI/CD and release validation
- Typical runtime: 10-15 minutes

## Reports and Output

### Generated Reports

1. **Performance Benchmark Report** - `performance_benchmark_report_<timestamp>.json`
   - Comprehensive test results with pass/fail status
   - Statistical analysis and trend data
   - Baseline compliance verification

2. **Detailed Results** - `performance_detailed_results_<timestamp>.json`
   - Raw test execution data
   - Timing information and metadata
   - Error details and debugging information

3. **Baseline Configuration** - `performance_baselines.json`
   - Current baseline definitions
   - Threshold configurations
   - Metric categorization

### Console Output Example

```
[14:32:15] Starting comprehensive performance test suite...
[14:32:15] Running in (Full Mode)

--- Running DATABASE tests ---
[14:32:15] Starting database performance tests...
[14:32:16]   Testing bulk insert performance...
[14:32:45]   Testing concurrent database reads...
[14:32:50] Database performance tests completed.

--- Running WEBSOCKET tests ---
[14:32:50] Starting WebSocket performance tests...
[14:32:51]   Testing WebSocket message throughput...
[14:33:02]   Testing WebSocket broadcast performance...
[14:33:15] WebSocket performance tests completed.

Performance test suite completed in 645.23 seconds.

============================================================
PERFORMANCE TEST SUMMARY
============================================================
Total Tests: 24
Passed: 22
Failed: 2
Pass Rate: 91.7%
Average Duration: 26.884s

Severity Breakdown:
  INFO: 18
  LOW: 4
  MEDIUM: 2

Category Breakdown:
  DATABASE: 3/3 (100.0%)
  WEBSOCKET: 3/3 (100.0%)
  AGENT: 2/3 (66.7%)
  API: 3/3 (100.0%)
  MEMORY: 2/2 (100.0%)
  CACHE: 2/2 (100.0%)
  CONCURRENT: 3/3 (100.0%)
============================================================

✅ Performance tests PASSED (Pass rate: 91.7%)
```

## Integration with CI/CD

### GitHub Actions Integration

Add to `.github/workflows/performance-tests.yml`:

```yaml
name: Performance Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
      
      - name: Run performance tests
        run: |
          python app/tests/performance/run_performance_suite.py --quick
      
      - name: Upload performance reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: performance-reports
          path: test_reports/
```

### Local Development

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run performance tests before committing
python app/tests/performance/run_performance_suite.py --quick

# Run specific performance tests during development
pytest app/tests/performance/ -k "test_database_performance" -v
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```bash
   # Run memory-specific tests
   python app/tests/performance/run_performance_suite.py --categories memory
   ```

2. **Database Performance Issues**
   ```bash
   # Test database performance in isolation
   python app/tests/performance/run_performance_suite.py --categories database
   ```

3. **WebSocket Connection Problems**
   ```bash
   # Test WebSocket performance
   python app/tests/performance/run_performance_suite.py --categories websocket
   ```

### Performance Optimization

1. **Database Optimization**
   - Check connection pool settings
   - Verify query optimization
   - Monitor index usage

2. **WebSocket Optimization**
   - Tune message batch sizes
   - Optimize compression settings
   - Check connection limits

3. **Memory Optimization**
   - Profile memory usage patterns
   - Check for memory leaks
   - Optimize garbage collection

### Debug Mode

```bash
# Run with detailed logging
python app/tests/performance/run_performance_suite.py --quick

# Run specific test with pytest debugging
pytest app/tests/performance/test_comprehensive_backend_performance.py::TestComprehensiveBackendPerformance::test_database_performance_suite -v -s --tb=long
```

## Architecture Compliance

### Code Standards
- **File Limit**: Each file ≤300 lines (enforced)
- **Function Limit**: Each function ≤8 lines (enforced)
- **Type Safety**: Full type annotations with Pydantic models
- **Async Patterns**: All I/O operations use async/await

### Test Patterns
- Comprehensive mocking for isolated performance testing
- Resource monitoring and metrics collection
- Concurrent testing with asyncio patterns
- Benchmark data collection and reporting

## Contributing

When adding new performance tests:

1. Follow 450-line file limit and 25-line function rules
2. Include comprehensive type annotations
3. Use proper async patterns for I/O operations
4. Add performance targets and assertions
5. Update baseline configuration and documentation

For questions or issues, refer to the main project documentation or create an issue in the project repository.