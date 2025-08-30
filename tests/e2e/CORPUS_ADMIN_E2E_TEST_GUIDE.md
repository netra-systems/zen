# Corpus Admin E2E Test Suite Guide

## Overview

This document provides comprehensive guidance for running and understanding the CorpusAdminSubAgent E2E test suite (`test_corpus_admin_e2e.py`).

## CRITICAL PRODUCTION CONTEXT

**Business Value Protection:** These tests protect **$500K+ MRR** from corpus operation failures in enterprise environments.

**Zero Downtime Requirement:** Corpus operations must maintain 99.9% uptime for enterprise clients who rely on knowledge base availability for critical operations.

## Test Coverage

### Complete User Journey Tests

1. **`test_complete_corpus_creation_journey`**
   - Full API → Triage → Supervisor → CorpusAdmin → Database workflow
   - Real-time WebSocket monitoring throughout process
   - Database persistence verification
   - Performance validation (<5 seconds end-to-end)

2. **`test_multi_agent_collaboration_flow`**
   - Agent handoff sequence validation
   - Context preservation across agents
   - Workflow orchestration verification
   - Agent isolation and communication testing

3. **`test_corpus_search_and_retrieve_flow`** 
   - Natural language search processing
   - Result quality and relevance validation
   - Search performance benchmarks (<2 seconds)
   - Result formatting and ranking verification

### Production Scale Tests

4. **`test_bulk_corpus_operations`**
   - Concurrent corpus creation (5 simultaneous)
   - Bulk search operations under load
   - System stability metrics validation
   - Performance under production-like volumes

5. **`test_concurrent_user_operations`**
   - Multi-user operation isolation
   - Concurrent session management
   - User data isolation verification
   - Thread safety validation

### Critical Reliability Tests

6. **`test_high_risk_operation_approval_flow`**
   - Approval workflow for dangerous operations
   - User consent and authorization flow
   - Security validation for bulk operations
   - Approval timing and UX verification

7. **`test_error_recovery_and_graceful_degradation`**
   - Database connection failure recovery
   - Network interruption handling
   - Partial operation failure recovery
   - System health restoration validation

8. **`test_performance_benchmarks`**
   - Establishes performance baselines
   - CI/CD performance tracking
   - Regression detection
   - SLA validation for enterprise clients

## Running the Tests

### Prerequisites

1. **Real Services Required**
   ```bash
   # Ensure services are running
   docker-compose -f docker-compose.dev.yml up backend auth postgres redis
   ```

2. **Environment Setup**
   ```bash
   export TEST_ENVIRONMENT=dev
   export TEST_USE_REAL_SERVICES=true
   export TEST_USE_REAL_LLM=false  # Set to true for full integration
   ```

### Basic Test Execution

```bash
# Run all Corpus Admin E2E tests
python unified_test_runner.py --file tests/e2e/test_corpus_admin_e2e.py --real-services

# Run specific test categories
python unified_test_runner.py --markers "e2e and corpus_admin" --real-services

# Run with performance benchmarks
python unified_test_runner.py --markers "e2e and corpus_admin and performance" --real-services
```

### Environment-Specific Testing

```bash
# Development environment (default)
python unified_test_runner.py --env dev --markers "e2e and corpus_admin"

# Staging environment validation
python unified_test_runner.py --env staging --markers "e2e and corpus_admin" --real-services

# Production-safe tests (requires explicit flag)
python unified_test_runner.py --env prod --allow-prod --markers "e2e and corpus_admin"
```

### Real LLM Integration Testing

```bash
# Run with actual LLM API calls (requires API keys)
export TEST_USE_REAL_LLM=true
export TEST_LLM_TIMEOUT=30
python unified_test_runner.py --markers "e2e and corpus_admin and real_llm" --real-llm
```

## Test Architecture

### Real Services Integration

Tests use **actual services** not mocks:
- **PostgreSQL** for database persistence
- **Redis** for caching and state management  
- **WebSocket** for real-time communication
- **ClickHouse** for corpus indexing and search
- **LLM APIs** when `--real-llm` flag is set

### WebSocket Communication Testing

Each test establishes real WebSocket connections to monitor:
- Agent lifecycle events
- Progress updates during operations
- Error notifications and recovery
- Performance metrics collection

### Multi-Agent Workflow Validation

Tests verify complete agent collaboration:
```
User Request → API → Triage → Supervisor → CorpusAdmin → Database → Response
                ↓        ↓         ↓           ↓           ↓
            WebSocket WebSocket WebSocket WebSocket WebSocket
             Updates   Updates   Updates   Updates   Updates
```

## Performance Benchmarks

### Target Performance Metrics

| Operation | Target | Measurement |
|-----------|---------|-------------|
| Corpus Creation | <3.0s | End-to-end API response |
| Corpus Search | <1.0s | Query to results delivery |
| Bulk Operations | <10.0s | 5 concurrent corpus operations |
| WebSocket Latency | <0.1s | Round-trip message time |

### Performance Validation

Tests automatically validate:
- Average response times meet targets
- 95th percentile performance consistency
- Error rates remain below 5%
- System stability under load

## Error Recovery Testing

### Simulated Failure Scenarios

1. **Database Connection Failures**
   - Simulated connection drops
   - Automatic retry mechanisms
   - Graceful degradation validation

2. **Network Interruptions**
   - WebSocket disconnection/reconnection
   - Request persistence during outages
   - State synchronization after recovery

3. **Partial Operation Failures**
   - Document processing errors
   - Partial success handling
   - Warning message propagation

### Recovery Pattern Validation

Tests ensure system follows recovery patterns:
- Automatic retry with exponential backoff
- User notification of issues
- Fallback mechanisms activation
- Complete system health restoration

## Test Data Management

### Corpus Test Data

Tests create realistic corpus data:
- **Small**: 3 documents, ~500 words total
- **Medium**: 10 documents, ~2000 words total  
- **Large**: 50 documents, ~25000 words total

### Data Cleanup

All tests include automatic cleanup:
- Corpus deletion after test completion
- Database state restoration
- Redis cache clearing
- WebSocket connection closure

## Debugging Failed Tests

### Common Issues

1. **Service Connection Failures**
   ```bash
   # Check service health
   curl http://localhost:8000/health
   curl http://localhost:8001/health
   ```

2. **WebSocket Connection Issues**
   ```bash
   # Verify WebSocket endpoint
   wscat -c ws://localhost:8000/ws
   ```

3. **Database Persistence Failures**
   ```bash
   # Check PostgreSQL connection
   psql -h localhost -p 5432 -U postgres -d netra_dev
   ```

### Test Logging

Tests generate detailed logs:
- Agent collaboration sequence
- WebSocket message flow
- Performance timing data
- Error details and stack traces

### Log Locations

```bash
# Test execution logs
tail -f logs/test_execution.log

# WebSocket communication logs  
tail -f logs/websocket_debug.log

# Performance benchmark data
ls -la test_results/corpus_admin_e2e_performance_*.json
```

## CI/CD Integration

### Automated Test Execution

Tests are designed for CI/CD pipelines:
- Environment variable configuration
- Docker container compatibility
- Performance result artifacts
- Test report generation

### Pipeline Configuration

```yaml
# Example GitHub Actions configuration
- name: Run Corpus Admin E2E Tests
  run: |
    export TEST_ENVIRONMENT=ci
    export TEST_USE_REAL_SERVICES=true
    python unified_test_runner.py --markers "e2e and corpus_admin" --xml-report
```

### Performance Tracking

Results stored for trend analysis:
- JSON performance reports
- Historical comparison data
- Regression detection alerts
- SLA compliance monitoring

## Enterprise Validation

### Production Readiness Checklist

Before deploying to production, ensure:
- [ ] All E2E tests pass consistently
- [ ] Performance benchmarks meet targets  
- [ ] Error recovery scenarios validated
- [ ] Multi-user isolation confirmed
- [ ] Approval workflows functional
- [ ] WebSocket reliability verified

### Enterprise-Specific Tests

Additional validation for enterprise clients:
- Large-scale corpus operations (1000+ documents)
- Concurrent user limits (100+ simultaneous users)
- Data privacy and isolation verification
- Audit trail completeness
- Backup and recovery procedures

## Maintenance and Updates

### Test Maintenance

Regular maintenance tasks:
- Update performance baselines quarterly
- Add new test scenarios for features
- Refresh test data with realistic content
- Validate environment compatibility

### Adding New Tests

When adding new corpus functionality:
1. Add E2E test coverage first (TDD approach)
2. Include WebSocket monitoring
3. Add performance benchmarks
4. Document expected behavior
5. Include error scenarios

## Support and Troubleshooting

### Getting Help

For test issues or questions:
1. Check test logs for specific error details
2. Validate service health and connectivity
3. Review environment configuration
4. Consult this documentation for common patterns

### Contributing

When contributing new tests:
- Follow existing test patterns
- Include comprehensive documentation
- Add performance validation
- Ensure proper cleanup
- Test in multiple environments

---

**Remember**: These tests protect critical enterprise functionality worth hundreds of thousands in MRR. Thorough testing prevents costly production incidents and maintains client trust in our corpus management capabilities.