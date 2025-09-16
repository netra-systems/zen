# ClickHouse Testing Documentation

## Overview
Comprehensive testing suite for ClickHouse integration with real API connections and production-like scenarios.

## Test Files

### Core Test Files
- **`test_real_clickhouse_api.py`** - Real ClickHouse API integration tests with live connections
- **`test_query_correctness.py`** - SQL query structure and correctness validation
- **`test_performance_edge_cases.py`** - Performance testing and edge case handling
- **`test_corpus_generation_coverage.py`** - Corpus table lifecycle and generation workflows
- **`test_realistic_clickhouse_operations.py`** - Production-like data volumes and patterns

### Service Tests
- **`../services/test_clickhouse_service.py`** - ClickHouse service layer testing with real connections
- **`../services/test_clickhouse_query_fixer.py`** - Array syntax fixing and query interception

## Key Features

### 1. Real API Testing
All tests use actual ClickHouse Cloud connections when available:
- Connection validation
- Table creation and management
- Data insertion and retrieval
- Complex aggregation queries
- Time-series analysis

### 2. Array Syntax Fixing
Automatic correction of incorrect array syntax:
```sql
-- Incorrect (will be fixed automatically)
SELECT metrics.value[1] FROM workload_events

-- Correct
SELECT arrayElement(metrics.value, 1) FROM workload_events
```

### 3. Query Interceptor
The `ClickHouseQueryInterceptor` class wraps all queries to:
- Fix array syntax issues automatically
- Track query statistics
- Handle errors gracefully
- Support retry logic

### 4. Performance Testing
- Batch insert operations (1000+ records)
- Query performance benchmarking
- Index optimization validation
- Connection pooling and recovery

## Configuration

### Environment Variables
```bash
# ClickHouse Configuration
CLICKHOUSE_HOST=clickhouse_host_url_placeholder
CLICKHOUSE_PORT=8443
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=<password>
CLICKHOUSE_DB=default
```

### Test Configuration
Tests automatically use the appropriate configuration based on environment:
- `development` - Uses dev credentials with ClickHouse Cloud
- `testing` - Uses mock client unless explicitly enabled
- `production` - Uses production credentials

## Running Tests

### Quick Test Commands
```bash
# Run all ClickHouse tests
pytest app/tests/clickhouse/ -v

# Run specific test file
pytest app/tests/clickhouse/test_real_clickhouse_api.py -v

# Run with real ClickHouse (skip mocks)
DEV_MODE_CLICKHOUSE_ENABLED=true pytest app/tests/clickhouse/ -v

# Run specific test class
pytest app/tests/clickhouse/test_real_clickhouse_api.py::TestRealClickHouseConnection -v
```

### Test Levels
Tests are organized by complexity and requirements:
1. **Unit Tests** - Query syntax fixing, validation
2. **Integration Tests** - Real API connections, table operations
3. **Performance Tests** - Batch operations, benchmarking
4. **End-to-End Tests** - Full workflow validation

## Test Data

### Workload Events Schema
```sql
CREATE TABLE workload_events (
    trace_id String,
    span_id String,
    user_id String,
    session_id String,
    timestamp DateTime64(3),
    workload_type String,
    status String,
    duration_ms Int32,
    metrics Nested(
        name Array(String),
        value Array(Float64),
        unit Array(String)
    ),
    input_text String,
    output_text String,
    metadata String
) ENGINE = MergeTree()
ORDER BY (workload_type, timestamp, trace_id)
```

### Corpus Tables
Dynamic corpus tables are created with pattern:
```sql
CREATE TABLE netra_content_corpus_<UUID> (
    record_id UUID,
    workload_type String,
    prompt String,
    response String,
    metadata String,
    created_at DateTime64(3)
) ENGINE = MergeTree()
ORDER BY (workload_type, created_at)
```

## Common Issues and Solutions

### Authentication Errors
**Problem**: `Authentication failed: password is incorrect`
**Solution**: Ensure correct environment variables are set and loaded

### Table Not Found
**Problem**: `Table workload_events doesn't exist`
**Solution**: Run `create_workload_events_table_if_missing()` from `clickhouse_init.py`

### Array Syntax Errors
**Problem**: `Code: 386. NO_COMMON_TYPE`
**Solution**: Use `arrayElement()` instead of bracket notation, or enable query interceptor

### Connection Timeouts
**Problem**: Connection timeout errors
**Solution**: Check network connectivity to ClickHouse Cloud, verify firewall rules

## Best Practices

### 1. Always Use Query Interceptor
Wrap ClickHouse clients with the interceptor to fix syntax issues:
```python
from netra_backend.app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor

client = ClickHouseDatabase(...)
interceptor = ClickHouseQueryInterceptor(client)
```

### 2. Batch Operations
For bulk inserts, use batch operations:
```python
await client.insert_data('table_name', batch_data, column_names=columns)
```

### 3. Proper Cleanup
Always clean up test data and connections:
```python
try:
    # Test operations
    pass
finally:
    await client.disconnect()
```

### 4. Use Fixtures
Leverage pytest fixtures for common setup:
```python
@pytest.fixture
async def clickhouse_client():
    async with get_clickhouse_client() as client:
        yield client
```

## Monitoring and Debugging

### Query Statistics
The interceptor tracks:
- Total queries executed
- Queries fixed
- Fix rate percentage
- Error counts

### Logging
Enable debug logging for detailed information:
```python
import logging
logging.getLogger('app.db').setLevel(logging.DEBUG)
```

### Performance Metrics
Tests include performance benchmarking:
- Insert rates (events/second)
- Query response times
- Index vs full scan comparisons

## CI/CD Integration

### GitHub Actions
Tests are integrated with CI pipeline:
```yaml
- name: Run ClickHouse Tests
  env:
    CLICKHOUSE_HOST: ${{ secrets.CLICKHOUSE_HOST }}
    CLICKHOUSE_PASSWORD: ${{ secrets.CLICKHOUSE_PASSWORD }}
  run: |
    pytest app/tests/clickhouse/ --tb=short
```

### Coverage Requirements
- Minimum 80% code coverage for ClickHouse modules
- All critical paths must be tested
- Performance benchmarks must pass thresholds

## Future Improvements

1. **Connection Pooling** - Implement connection pool for better performance
2. **Async Batch Processing** - Optimize batch operations with async processing
3. **Query Caching** - Add caching layer for frequently used queries
4. **Distributed Testing** - Support for testing distributed ClickHouse clusters
5. **Load Testing** - Add comprehensive load testing scenarios

## Support

For issues or questions:
1. Check this documentation
2. Review test examples in `test_real_clickhouse_api.py`
3. Consult the ClickHouse spec: `SPEC/clickhouse.xml`
4. Check logs for detailed error messages