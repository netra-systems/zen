# Corpus Generation Performance Tests

Comprehensive performance testing suite for the Netra AI Optimization Platform's corpus generation system.

## Overview

This test suite evaluates the performance and scalability characteristics of corpus generation operations, including:

- Large-scale corpus generation (100k+ records)
- Concurrent processing and resource management
- Database performance under load
- Memory and CPU utilization monitoring
- Benchmarking and metrics collection

## Test Structure

### Test Categories

1. **Large Scale Generation** (`TestLargeScaleGeneration`)
   - Tests generation of 100k+ records
   - Memory efficiency validation
   - Resource utilization monitoring

2. **Concurrent Processing** (`TestConcurrentProcessing`)
   - Multiple simultaneous generation jobs
   - Resource contention handling
   - Thread pool efficiency

3. **Database Performance** (`TestDatabasePerformance`)
   - Bulk insert operations
   - Concurrent database operations
   - ClickHouse performance optimization

4. **Benchmark Metrics** (`TestBenchmarkMetrics`)
   - Throughput measurement
   - Latency profiling
   - CPU utilization tracking

## Running Performance Tests

### Quick Start

```bash
# Run all performance tests
python app/tests/performance/run_performance_tests.py

# Run with verbose output
python app/tests/performance/run_performance_tests.py --verbose

# Run benchmark tests only
python app/tests/performance/run_performance_tests.py --benchmark-only
```

### Using pytest directly

```bash
# Run all performance tests
pytest app/tests/performance/test_corpus_generation_perf.py -m performance -v

# Run specific test class
pytest app/tests/performance/test_corpus_generation_perf.py::TestLargeScaleGeneration -v

# Run with resource monitoring
pytest app/tests/performance/test_corpus_generation_perf.py -m performance -s --tb=short
```

## Performance Targets

### Throughput
- **Target**: >10 records/second for content generation
- **Large Scale**: 100k records within 1 hour
- **Concurrent**: 5+ simultaneous jobs without degradation

### Resource Usage
- **Memory**: <8GB RAM for large generation tasks
- **CPU**: <95% utilization to allow system headroom
- **Database**: <60 seconds for 50k record bulk insert

### Latency
- **Average**: <200ms per generation request
- **P95**: <500ms for 95th percentile requests
- **Database**: <30 seconds for concurrent operations

## Test Configuration

### Environment Variables

```bash
CORPUS_TEST_DIR=/tmp/performance_test_corpus
CLICKHOUSE_TEST_HOST=localhost
CLICKHOUSE_TEST_PORT=8443
```

### Test Data

- Small corpus: 2 workload types, minimal records
- Medium corpus: 200 records across types
- Large corpus: 100k+ records for stress testing

## Output and Reporting

### Test Reports

Performance test reports are saved to:
- `test_reports/performance/performance_report_<timestamp>.json`
- `test_reports/performance/latest_performance_report.json`

### Report Structure

```json
{
  "test_run": {
    "timestamp": "2025-01-15 10:30:00",
    "status": "passed",
    "exit_code": 0
  },
  "system_metrics": {
    "execution_time_seconds": 1234.56,
    "memory_usage_mb": 2048.0,
    "cpu_percent_avg": 75.2
  },
  "benchmarks": {
    "throughput": {
      "records_per_second": 15.6,
      "target": "> 10 records/second"
    },
    "latency": {
      "average_ms": 145.3,
      "p95_ms": 387.9
    }
  }
}
```

## Architecture Compliance

### Code Standards
- **File Limit**: Each file ≤300 lines (enforced)
- **Function Limit**: Each function ≤8 lines (enforced)
- **Type Safety**: Full type annotations with Pydantic models
- **Async Patterns**: All I/O operations use async/await

### Test Patterns
- Comprehensive mocking for isolated performance testing
- Resource monitoring with psutil integration
- Concurrent testing with asyncio.gather()
- Benchmark data collection and reporting

## Troubleshooting

### Common Issues

1. **Memory Errors**
   - Reduce test data size
   - Check for memory leaks in generation code
   - Monitor system resources

2. **Timeout Failures**
   - Increase test timeouts for slow systems
   - Check database connectivity
   - Verify mock configurations

3. **Concurrency Issues**
   - Ensure proper async/await usage
   - Check for race conditions
   - Validate thread pool configurations

### Debug Mode

```bash
# Run with detailed debugging
pytest app/tests/performance/test_corpus_generation_perf.py -vv -s --tb=long

# Profile memory usage
python -m memory_profiler app/tests/performance/run_performance_tests.py
```

## Integration

This performance test suite integrates with:
- Main test runner (`python test_runner.py --level performance`)
- CI/CD pipelines for performance regression detection
- Monitoring dashboards for trend analysis
- Architecture health checks

## Contributing

When adding new performance tests:

1. Follow 300-line file limit and 8-line function rules
2. Include comprehensive type annotations
3. Use proper async patterns for I/O operations
4. Add performance targets and assertions
5. Update this documentation

For questions or issues, refer to the main project documentation or create an issue in the project repository.