# User Isolation Integration Tests

## Overview

This test suite provides comprehensive integration testing for User Isolation Patterns in the Netra platform, focusing on multi-tenant security and data isolation. These tests are **mission-critical for Enterprise revenue** as they ensure complete data isolation between users, preventing security breaches that could lose major accounts.

## Business Value Justification (BVJ)

- **Segment**: Enterprise (critical for multi-tenant security)
- **Business Goal**: Guarantee zero risk of data leakage between users
- **Value Impact**: Complete data isolation prevents security breaches, enables enterprise compliance
- **Revenue Impact**: Essential for Enterprise revenue - any data leakage incident could lose major accounts

## Test Files

### 1. `test_data_access_factory_isolation.py`
**Data Access Factory Isolation Patterns**

Tests the Factory pattern implementation for data layer user isolation:
- **Factory creation under concurrent user load** (10+ users)
- **Cross-user data isolation verification** with real databases
- **Resource cleanup** after user session termination
- **Factory error handling** when databases are unavailable
- **Connection pool exhaustion** scenarios
- **Data leakage prevention** between user contexts

**Key Test Cases:**
- `test_clickhouse_factory_creates_isolated_contexts_under_load` - 12 concurrent users
- `test_redis_factory_creates_isolated_contexts_under_load` - 15 concurrent users
- `test_factory_enforces_per_user_context_limits` - Resource limit enforcement
- `test_concurrent_factory_operations_thread_safety` - 20 concurrent operations
- `test_factory_statistics_accuracy_under_load` - Complex load patterns

### 2. `test_user_execution_context_lifecycle.py`
**User Execution Context Lifecycle Management**

Tests UserExecutionContext lifecycle management under realistic conditions:
- **Context creation/cleanup** under high concurrency (20+ users)
- **Database session management** across request boundaries
- **WebSocket routing accuracy** with multiple active users
- **Child context creation** for sub-agent operations
- **Context validation** against malformed/malicious data
- **Memory leak prevention** during long-running sessions

**Key Test Cases:**
- `test_context_creation_under_high_concurrency` - 25 concurrent users
- `test_database_session_management_across_requests` - Session lifecycle
- `test_websocket_routing_accuracy_multiple_users` - 10 concurrent WebSocket connections
- `test_child_context_creation_hierarchy_tracking` - Hierarchical context chains
- `test_memory_leak_prevention_long_running_sessions` - Memory usage validation
- `test_backward_compatibility_supervisor_patterns` - Legacy compatibility

### 3. `test_cross_user_data_isolation.py`
**Cross-User Data Isolation**

Tests cross-user data isolation with realistic scenarios:
- **Real database operations** with multiple users simultaneously
- **Cache key namespacing** to prevent session contamination
- **Data access patterns** that could expose cross-user data
- **Malicious attempts** to access other users' data
- **Race conditions** that might cause data mixing
- **Stress testing** with realistic enterprise user loads

**Key Test Cases:**
- `test_redis_key_namespacing_prevents_cross_user_access` - 5 users with sensitive data
- `test_concurrent_data_operations_prevent_mixing` - 8 concurrent users
- `test_malicious_cross_user_access_attempts_blocked` - Security breach attempts
- `test_stress_test_enterprise_user_load` - 50+ concurrent users
- `test_data_isolation_with_identical_keys_different_users` - Key collision scenarios

### 4. `test_concurrent_user_operations.py`
**Concurrent User Operations**

Tests concurrent user operations under realistic enterprise load:
- **Simultaneous multi-user database operations**
- **Race condition prevention** in shared resources
- **Memory and connection pool management** under load
- **WebSocket event delivery accuracy** during concurrent operations
- **Resource cleanup and leak prevention**
- **Real-world Enterprise usage patterns** (100+ concurrent users)

**Key Test Cases:**
- `test_high_concurrency_context_creation_race_conditions` - 100 concurrent users
- `test_concurrent_data_operations_consistency` - 25 users with 20 ops each
- `test_connection_pool_exhaustion_resilience` - 50 users stressing connection pools
- `test_real_world_enterprise_usage_pattern` - Realistic enterprise simulation
- `test_graceful_degradation_under_extreme_load` - 200 users extreme load

## Usage

### Running All User Isolation Tests
```bash
# Run all user isolation tests
python tests/unified_test_runner.py --category integration --pattern "*user_isolation*"

# Run with real services (recommended for comprehensive testing)
python tests/unified_test_runner.py --real-services --pattern "*user_isolation*"

# Run specific test categories
python tests/unified_test_runner.py --real-services --category integration \
  --test-file netra_backend/tests/integration/user_isolation/test_data_access_factory_isolation.py
```

### Running Individual Test Files
```bash
# Data Access Factory tests
python tests/unified_test_runner.py --real-services \
  --test-file netra_backend/tests/integration/user_isolation/test_data_access_factory_isolation.py

# User Execution Context tests  
python tests/unified_test_runner.py --real-services \
  --test-file netra_backend/tests/integration/user_isolation/test_user_execution_context_lifecycle.py

# Cross-User Data Isolation tests
python tests/unified_test_runner.py --real-services \
  --test-file netra_backend/tests/integration/user_isolation/test_cross_user_data_isolation.py

# Concurrent User Operations tests
python tests/unified_test_runner.py --real-services \
  --test-file netra_backend/tests/integration/user_isolation/test_concurrent_user_operations.py
```

### Running Specific Test Methods
```bash
# Run high-concurrency factory tests
python tests/unified_test_runner.py --real-services -k "factory_creates_isolated_contexts_under_load"

# Run memory leak prevention tests
python tests/unified_test_runner.py --real-services -k "memory_leak_prevention"

# Run enterprise load tests
python tests/unified_test_runner.py --real-services -k "enterprise_user_load"
```

## Test Coverage

### User Load Testing
- **Low Load**: 5-10 concurrent users
- **Medium Load**: 15-25 concurrent users  
- **High Load**: 50+ concurrent users
- **Extreme Load**: 100-200 concurrent users

### Data Operations Coverage
- **Redis Operations**: String, JSON, List, Set, Hash operations
- **ClickHouse Operations**: Context creation, query isolation, cache management
- **Database Sessions**: Lifecycle management, cleanup, isolation
- **WebSocket Routing**: Connection multiplexing, event delivery

### Security Testing
- **Cross-user access attempts**: Malicious key access patterns
- **Data contamination**: Key collision scenarios
- **Session mixing**: Namespace isolation verification
- **Information leakage**: Sensitive data exposure prevention

### Performance Benchmarks
- **Context Creation**: < 1.0s average for normal load
- **Memory Usage**: < 100MB for 600 contexts
- **Throughput**: > 50 contexts/sec creation rate
- **Operations**: > 100 operations/sec sustained load

## Expected Test Count

**Total: 30 integration tests across 4 files**
- Data Access Factory: 8 tests
- User Execution Context: 9 tests  
- Cross-User Data Isolation: 7 tests
- Concurrent User Operations: 6 tests

## Key Dependencies

### Real Services Required
- **PostgreSQL**: Database session testing
- **Redis**: Cache isolation testing  
- **ClickHouse**: Query isolation testing (optional - uses mocks if unavailable)

### Test Framework Dependencies
- `BaseIntegrationTest`: Base test class with setup/teardown
- `pytest-asyncio`: Async test support
- `tracemalloc`: Memory usage monitoring
- `asyncio.gather`: Concurrent operation testing

## Success Criteria

### Functional Requirements
- **100% data isolation**: Zero cross-user data leakage
- **Context isolation**: Proper factory pattern isolation
- **Resource cleanup**: No memory/connection leaks
- **Concurrent safety**: No race conditions under load

### Performance Requirements  
- **Context creation**: < 3.0s for 25+ concurrent users
- **Memory efficiency**: < 2MB per 100 contexts
- **Throughput**: > 100 operations/sec sustained
- **Success rate**: > 95% under normal enterprise load

### Security Requirements
- **Access control**: Malicious access attempts blocked
- **Data namespace**: Complete key isolation by user
- **Session integrity**: No session mixing between users
- **Audit trails**: Complete request traceability

## Error Handling

### Expected Failures
- **Connection pool exhaustion**: Graceful degradation when pools are full
- **Service unavailability**: Proper error messages when services are down
- **Memory constraints**: Controlled failure when memory is exhausted
- **Timeout scenarios**: Proper cleanup when operations timeout

### Failure Recovery
- **Resource cleanup**: All contexts cleaned up on failure
- **Factory reset**: Clean factory state between tests
- **Memory management**: Garbage collection after each test
- **Connection recovery**: Pool restoration after exhaustion

## Monitoring and Metrics

### Memory Monitoring
- Peak memory usage tracking with `tracemalloc`
- Memory leak detection between test rounds
- Memory efficiency per operation calculations

### Performance Monitoring  
- Context creation timing measurements
- Operation throughput calculations
- Concurrent load handling metrics
- Resource utilization tracking

### Security Monitoring
- Cross-user access attempt detection
- Data contamination verification
- Isolation breach monitoring
- Audit trail completeness validation

## Contributing

When adding new user isolation tests:

1. **Follow naming convention**: `test_*_isolation.py` or `test_*_concurrent_*.py`
2. **Include BVJ comments**: Business Value Justification for each test
3. **Use realistic data**: Simulate actual enterprise usage patterns
4. **Test concurrency**: Always test with multiple users
5. **Validate isolation**: Ensure complete data separation
6. **Monitor resources**: Track memory and connection usage
7. **Document scenarios**: Explain what business scenarios are tested

### Test Template
```python
@pytest.mark.asyncio
async def test_new_isolation_scenario(self):
    """Test description with realistic business scenario.
    
    Business Value Justification (BVJ):
    - Segment: Enterprise
    - Business Goal: Specific isolation requirement
    - Value Impact: How this prevents data breaches
    - Revenue Impact: Why this matters for Enterprise revenue
    """
    # Test implementation with multiple users
    users = [f"test_user_{i}" for i in range(10)]
    
    # Concurrent operations
    results = await asyncio.gather(*[
        user_operation(user) for user in users
    ])
    
    # Isolation verification
    assert all(result.is_isolated for result in results)
```

## Related Documentation

- **[User Context Architecture](../../../reports/archived/USER_CONTEXT_ARCHITECTURE.md)** - Factory patterns and isolation principles
- **[Test Creation Guide](../../../reports/testing/TEST_CREATION_GUIDE.md)** - SSOT patterns for test creation
- **[Agent Architecture Disambiguation Guide](../../../docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** - Context usage in agent systems

---

**⚠️ CRITICAL**: These tests are essential for Enterprise revenue protection. Any failures indicate potential security vulnerabilities that could result in data breaches and loss of major accounts. All tests must pass before production deployment.