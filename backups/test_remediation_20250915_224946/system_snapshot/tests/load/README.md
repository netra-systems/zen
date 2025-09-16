# Production Load Tests for Concurrent Agent Persistence

This directory contains comprehensive production-grade load tests that validate the platform's ability to handle enterprise-scale concurrent agent workloads with production performance requirements.

## Business Value Justification

- **Segment**: Enterprise ($50K+ MRR workloads)
- **Business Goal**: Platform Scalability, 99.9% Uptime SLA, Customer Retention
- **Value Impact**: Supports 100+ concurrent agents for mission-critical operations
- **Strategic Impact**: Validates enterprise scalability claims, prevents churn from performance issues

## Critical Performance Requirements

- Support 100+ concurrent agents (Enterprise tier)
- P50 < 50ms, P99 < 200ms for state persistence operations
- 99.9% success rate under peak load
- Zero data loss under extreme load conditions
- Graceful degradation patterns under resource exhaustion
- Sub-100ms average latency for enterprise SLAs
- Memory usage < 2GB peak during concurrent operations
- Connection pooling efficiency validation

## Test Suite Overview

### Core Load Tests

1. **`test_100_concurrent_agents_baseline`**
   - Validates baseline performance with 100+ concurrent agents
   - Tests Enterprise tier concurrent execution capabilities
   - Validates P50/P99 latency requirements and throughput metrics

2. **`test_mixed_workload_read_write_patterns`**
   - Tests realistic production read/write patterns (60% reads, 40% writes)
   - Validates data integrity under concurrent operations
   - Ensures read operations remain faster than writes

3. **`test_state_size_scalability`**
   - Tests scalability across different agent state sizes (small → enterprise)
   - Validates graceful performance degradation with state complexity
   - Ensures Enterprise states don't cause system instability

4. **`test_sustained_load_24_hours_simulation`**
   - Simulates 24-hour continuous operations with compressed timing
   - Tests memory leak detection and performance degradation
   - Validates checkpoint creation over extended periods

### Stress and Resilience Tests

5. **`test_burst_traffic_handling`**
   - Tests traffic spike patterns (baseline → 4x spike → recovery)
   - Validates graceful degradation during spikes
   - Ensures system recovery to baseline performance

6. **`test_redis_connection_pool_exhaustion`**
   - Tests Redis connection pool behavior under extreme load (200+ connections)
   - Validates graceful handling of connection exhaustion
   - Ensures system stability during connection pressure

7. **`test_postgres_checkpoint_under_load`**
   - Tests PostgreSQL checkpoint creation during concurrent load
   - Validates disaster recovery compliance under stress
   - Ensures critical checkpoints succeed despite load

### Resource and Performance Tests

8. **`test_memory_usage_under_load`**
   - Monitors memory usage patterns and leak detection
   - Validates memory usage stays under 2GB peak
   - Tests garbage collection effectiveness

9. **`test_latency_sla_compliance`**
   - Validates SLA compliance over multiple measurement intervals
   - Tests P50 < 50ms, P95 < 150ms, P99 < 200ms requirements
   - Ensures 99.9% availability during normal operations

10. **`test_failure_recovery_under_load`**
    - Tests failure injection and recovery patterns
    - Validates graceful degradation during failures
    - Ensures system recovery to baseline performance

## Prerequisites

### System Requirements
- Sufficient system resources for load testing (8GB+ RAM recommended)
- Real Redis, PostgreSQL, and ClickHouse connections
- Production-like environment configuration

### Environment Setup
```bash
# Ensure test environment is running
python scripts/launch_test_env.py

# Verify database connections
python scripts/docker_env_manager.py status
```

## Running Load Tests

### Quick Start
```bash
# Run all load tests
python tests/load/run_load_tests.py

# Run specific test
python tests/load/run_load_tests.py --test test_100_concurrent_agents_baseline

# Quick smoke test (reduced load)
python tests/load/run_load_tests.py --quick
```

### Direct pytest Usage
```bash
# Run all load tests
pytest tests/load/ -m load -v --asyncio-mode=auto

# Run specific test
pytest tests/load/test_production_load_persistence.py::test_100_concurrent_agents_baseline -v

# Run with custom markers
pytest tests/load/ -m "load and not slow" -v
```

### Advanced Options
```bash
# Verbose output with custom report directory
python tests/load/run_load_tests.py --verbose --report-dir custom_reports

# Parallel execution (experimental)
python tests/load/run_load_tests.py --parallel 2
```

## Test Reports

Load tests generate detailed performance reports in JSON format:

### Report Location
- Default: `test_reports/load/`
- Custom: Specify with `--report-dir` option

### Report Contents
- Comprehensive performance metrics (latency percentiles, throughput)
- Resource utilization data (memory, CPU, connections)
- SLA compliance measurements
- Data integrity validation results
- Business KPI tracking

### Sample Report Structure
```json
{
  "test_name": "100_concurrent_agents_baseline",
  "timestamp": 1640995200,
  "metrics": {
    "agents": {"executed": 100, "succeeded": 98, "success_rate": 98.0},
    "performance": {"p50_latency_ms": 45.2, "p99_latency_ms": 187.3},
    "resources": {"peak_memory_mb": 1456, "avg_cpu_percent": 67.4},
    "sla_compliance": {"availability_percent": 98.0, "sla_violations": 0}
  }
}
```

## Performance Benchmarks

### Enterprise SLA Requirements
| Metric | Requirement | Test Coverage |
|--------|-------------|---------------|
| P50 Latency | < 50ms | ✅ All tests |
| P99 Latency | < 200ms | ✅ All tests |
| Availability | ≥ 99.9% | ✅ SLA compliance test |
| Concurrent Agents | 100+ | ✅ Baseline test |
| Memory Usage | < 2GB peak | ✅ Memory test |
| Error Rate | < 1% | ✅ All tests |

### Expected Results
- **Baseline Load**: 95%+ success rate, P50 < 50ms
- **Mixed Workload**: 90%+ success rate, reads faster than writes
- **Scalability**: <10x performance degradation from small to enterprise states
- **Sustained Load**: <20% performance degradation over time
- **Burst Traffic**: 80%+ success during spikes, graceful recovery
- **Connection Pool**: 70%+ success under extreme load
- **Recovery**: 90%+ success post-failure, <1.5x latency increase

## Troubleshooting

### Common Issues

1. **Connection Timeouts**
   ```bash
   # Check database services
   python scripts/docker_env_manager.py status
   
   # Restart if needed
   python scripts/docker_env_manager.py restart
   ```

2. **Memory Exhaustion**
   ```bash
   # Reduce concurrent agents in quick mode
   python tests/load/run_load_tests.py --quick
   ```

3. **Test Failures**
   ```bash
   # Run specific failing test with verbose output
   pytest tests/load/test_production_load_persistence.py::test_name -v -s
   ```

### Performance Optimization
- Ensure sufficient system resources (8GB+ RAM, 4+ CPU cores)
- Use SSD storage for better I/O performance
- Optimize Docker container resource limits
- Monitor system resource usage during tests

### Debugging
```bash
# Enable debug logging
export PYTEST_LOAD_TESTING_DEBUG=1
pytest tests/load/ -m load -v -s

# Check test reports for detailed metrics
ls -la test_reports/load/
```

## Integration with CI/CD

### GitHub Actions
```yaml
- name: Run Production Load Tests
  run: |
    python tests/load/run_load_tests.py --quick
  env:
    LOAD_TEST_REPORT_DIR: ${{ github.workspace }}/reports
```

### Performance Monitoring
- Integrate reports with monitoring systems
- Set up alerts for SLA violations
- Track performance trends over time

## Business KPI Validation

The load tests validate critical business KPIs:

- **Customer Retention**: Performance meets Enterprise SLA requirements
- **Revenue Protection**: Validates $50K+ MRR workload capabilities
- **Scalability Claims**: Proves 100+ concurrent agent support
- **Reliability**: 99.9% uptime during production-like load
- **Cost Efficiency**: Resource usage remains within operational limits

## Contributing

When adding new load tests:

1. Follow the existing test structure and naming conventions
2. Include comprehensive business value justification
3. Add detailed performance assertions and SLA validation
4. Update this README with new test descriptions
5. Ensure tests use real services (no mocks in load tests)

## Support

For issues with load tests:
1. Check the troubleshooting section above
2. Review test reports for detailed failure information
3. Ensure all prerequisites are met
4. Contact the platform team for production performance issues