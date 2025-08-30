# Comprehensive Migration Guide: From Mocks to Real Services

## Executive Summary

This guide provides a complete roadmap for migrating 2,941+ test files from mock-based testing to real, isolated services using the new IsolatedEnvironment test infrastructure. The migration enables industrial-strength testing with comprehensive service isolation, performance optimization, and reliable resource management.

**Business Value**: Eliminates mock-related test failures, increases confidence in production behavior, and provides a more maintainable test suite.

## Architecture Overview

The new test infrastructure consists of four main components:

1. **IsolatedEnvironmentManager**: Database isolation with transaction-based PostgreSQL, per-database Redis, and schema-based ClickHouse isolation
2. **ExternalServiceManager**: WebSocket, HTTP, file system, and LLM service integration with real endpoints
3. **PerformanceOptimizer**: Resource pooling, performance monitoring, and adaptive optimization strategies
4. **ComprehensiveFixtures**: Pytest fixtures integrating all components for seamless migration

## Migration Strategy

### Phase 1: Infrastructure Setup (Week 1)

1. **Verify Docker Infrastructure**
   ```bash
   # Start test services
   docker-compose -f docker-compose.test.yml up -d
   
   # Verify services are healthy
   python -c "
   import asyncio
   from test_framework.real_services import get_real_services
   
   async def check_health():
       services = get_real_services()
       await services.ensure_all_services_available()
       print('All services healthy!')
   
   asyncio.run(check_health())
   "
   ```

2. **Update conftest.py Files**
   ```python
   # Add to each service's conftest.py
   from test_framework.conftest_comprehensive import *
   ```

3. **Install Additional Dependencies**
   ```bash
   pip install asyncpg redis websockets httpx aiofiles psutil
   ```

### Phase 2: Database Test Migration (Week 2-3)

#### Before: Mock Database Pattern
```python
# OLD: Mock-based database testing
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_database():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=None)
    mock_db.fetchrow = AsyncMock(return_value={'id': 1, 'email': 'test@example.com'})
    mock_db.fetchval = AsyncMock(return_value=1)
    return mock_db

async def test_user_creation(mock_database):
    # Mock-based test
    await user_service.create_user("test@example.com")
    mock_database.execute.assert_called_once()
```

#### After: Real Database Pattern
```python
# NEW: Real database testing with transaction isolation
import pytest

@pytest.mark.requires_postgres
async def test_user_creation(isolated_database):
    # Test with real database - transaction automatically rolls back
    user_id = await isolated_database.fetchval(
        "INSERT INTO users (email) VALUES ($1) RETURNING id",
        "test@example.com"
    )
    
    # Verify user exists in this transaction
    user = await isolated_database.fetchrow(
        "SELECT * FROM users WHERE id = $1",
        user_id
    )
    assert user is not None
    assert user['email'] == "test@example.com"
    
    # No cleanup needed - transaction automatically rolls back
```

#### Migration Steps:

1. **Identify Database Tests**
   ```bash
   # Find all tests using database mocks
   grep -r "mock.*db\|AsyncMock\|MagicMock" */tests/ --include="*.py" | grep -v __pycache__
   ```

2. **Convert Mock Fixtures**
   - Replace `mock_database` fixtures with `isolated_database`
   - Remove `@patch` decorators for database operations
   - Replace mock assertions with real database queries

3. **Update Test Logic**
   ```python
   # Migration template
   async def test_example(isolated_database):
       # 1. Replace service calls that were mocked with real calls
       result = await your_service.method_under_test()
       
       # 2. Replace mock assertions with real database verification
       actual_data = await isolated_database.fetchrow(
           "SELECT * FROM table WHERE condition = $1", 
           result.id
       )
       assert actual_data is not None
       assert actual_data['field'] == expected_value
   ```

### Phase 3: Redis and Caching Migration (Week 3-4)

#### Before: Mock Redis Pattern
```python
@pytest.fixture
def mock_redis():
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    return mock_redis

async def test_caching(mock_redis):
    await cache_service.set_user_cache("user123", {"name": "test"})
    mock_redis.set.assert_called_once()
```

#### After: Real Redis Pattern
```python
@pytest.mark.requires_redis
async def test_caching(isolated_redis):
    # Test with real Redis - uses isolated database number
    await cache_service.set_user_cache("user123", {"name": "test"})
    
    # Verify data in real Redis
    cached_data = await isolated_redis.get("user:user123")
    assert cached_data is not None
    
    # Database automatically flushed after test
```

### Phase 4: External Service Integration (Week 4-5)

#### WebSocket Testing Migration

```python
# Before: Mock WebSocket
@pytest.fixture
def mock_websocket():
    return MagicMock()

# After: Real WebSocket testing
async def test_websocket_events(websocket_integration_environment):
    websocket = websocket_integration_environment['websocket']
    
    # Register event handler
    websocket.register_message_handler(
        'user_created',
        lambda msg: {'type': 'ack', 'user_id': msg['user_id']}
    )
    
    # Send message
    await websocket.send_message({
        'type': 'user_created',
        'user_id': 123
    })
    
    # Verify response
    response = await websocket.receive_message(timeout=5.0)
    assert response['type'] == 'ack'
```

#### HTTP Client Testing Migration

```python
# Before: Mock HTTP responses
@patch('httpx.AsyncClient.post')
async def test_api_call(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {'success': True}

# After: Real HTTP testing
async def test_api_call(auth_service_integration_environment):
    http_client = auth_service_integration_environment['http']
    
    # Test real auth service signup
    response = await http_client.auth_signup(
        "test@example.com",
        "password123"
    )
    
    assert 'access_token' in response
    assert 'refresh_token' in response
```

### Phase 5: File System Operations (Week 5)

```python
# Before: Mock file operations
@patch('builtins.open')
@patch('os.path.exists')
async def test_file_operations(mock_exists, mock_open):
    mock_exists.return_value = True
    mock_open.return_value.__enter__.return_value.read.return_value = "test data"

# After: Real file system testing
async def test_file_operations(comprehensive_test_environment):
    filesystem = comprehensive_test_environment['filesystem']
    
    # Create real file in isolated directory
    test_file = await filesystem.create_file(
        "test_config.json", 
        '{"key": "value"}'
    )
    
    # Verify file exists and has correct content
    assert test_file.exists()
    content = await filesystem.read_file("test_config.json")
    assert "key" in content
    
    # Files automatically cleaned up after test
```

## Service-Specific Migration Patterns

### Auth Service Tests

```python
# Use auth_service_integration_environment for auth tests
async def test_login_flow(auth_service_integration_environment):
    db = auth_service_integration_environment['database']
    http = auth_service_integration_environment['http']
    redis = auth_service_integration_environment['redis']
    
    # Create user in real database
    user_id = await db.fetchval(
        "INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id",
        "test@example.com", "hashed_password"
    )
    
    # Test real login API
    login_response = await http.auth_login(
        "test@example.com", "password123"
    )
    
    # Verify session in real Redis
    session_key = f"session:{login_response['session_id']}"
    session_data = await redis.get(session_key)
    assert session_data is not None
```

### Analytics Service Tests

```python
# Use analytics_testing_environment for analytics tests
async def test_event_processing(analytics_testing_environment):
    clickhouse = analytics_testing_environment['clickhouse']
    filesystem = analytics_testing_environment['filesystem']
    
    # Create test data file
    events_file = await filesystem.create_file(
        "events.json",
        '[{"event": "click", "user_id": 123, "timestamp": "2023-01-01T00:00:00"}]'
    )
    
    # Process events into real ClickHouse
    table_name = clickhouse.get_table_name("events")
    await clickhouse.execute(f"""
        CREATE TABLE {table_name} (
            event String,
            user_id UInt64,
            timestamp DateTime
        ) ENGINE = Memory
    """)
    
    # Process and verify data
    await analytics_service.process_events_file(str(events_file))
    
    # Verify in real ClickHouse
    result = await clickhouse.execute(f"SELECT COUNT(*) FROM {table_name}")
    assert result[0][0] == 1
```

### Backend Integration Tests

```python
# Use comprehensive_test_environment for full integration
async def test_complete_user_workflow(comprehensive_test_environment):
    db = comprehensive_test_environment['database']
    redis = comprehensive_test_environment['redis']
    websocket = comprehensive_test_environment['websocket']
    http = comprehensive_test_environment['http']
    
    # 1. Create user in real database
    user_id = await db.fetchval(
        "INSERT INTO users (email) VALUES ($1) RETURNING id",
        "test@example.com"
    )
    
    # 2. Cache user data in real Redis
    await redis.set(f"user:{user_id}", "test@example.com")
    
    # 3. Test WebSocket notification
    await websocket.send_message({
        "type": "user_created",
        "user_id": user_id
    })
    
    notification = await websocket.receive_message()
    assert notification["type"] == "user_created"
    
    # 4. Test HTTP API
    response = await http.get(f"/api/users/{user_id}")
    assert response.status_code == 200
```

## Performance Optimization

### Using Performance-Optimized Fixtures

```python
# For performance tests
async def test_performance_critical_operation(performance_test_environment):
    # Uses optimized configuration with minimal overhead
    db = performance_test_environment['database']
    
    # Performance test logic
    start_time = time.time()
    
    for i in range(1000):
        await db.execute(
            "INSERT INTO test_table (value) VALUES ($1)",
            f"value_{i}"
        )
    
    duration = time.time() - start_time
    assert duration < 5.0  # Should complete in under 5 seconds
```

### Resource Pool Configuration

```python
# For high-concurrency tests
from test_framework.performance_optimization import (
    create_optimized_environment_manager,
    OptimizationLevel
)

@pytest.fixture(scope="session")
async def high_performance_manager():
    manager = create_optimized_environment_manager(
        OptimizationLevel.CI_THOROUGH,
        {
            'max_concurrent_tests': 50,
            'pool_max_connections': 100,
            'enable_resource_pooling': True
        }
    )
    await manager.initialize()
    yield manager
    await manager.shutdown()
```

## Common Migration Challenges and Solutions

### Challenge 1: Test Data Isolation

**Problem**: Tests interfere with each other due to shared state.

**Solution**: Use transaction-based isolation for PostgreSQL:
```python
# Each test gets its own transaction that rolls back automatically
async def test_user_operations(isolated_database):
    # All operations within this transaction
    user_id = await isolated_database.fetchval("INSERT INTO users...")
    # Transaction automatically rolls back after test
```

### Challenge 2: Slow Test Execution

**Problem**: Real services are slower than mocks.

**Solution**: Use resource pooling and performance optimization:
```python
# Use performance-optimized environment
async def test_bulk_operations(performance_test_environment):
    # Benefits from connection pooling and optimized configuration
    pass
```

### Challenge 3: Service Dependencies

**Problem**: Tests fail when services are unavailable.

**Solution**: Use automatic service availability checking:
```python
@pytest.mark.requires_postgres
@pytest.mark.requires_redis
async def test_with_dependencies(isolated_database, isolated_redis):
    # Test automatically skipped if services unavailable
    pass
```

### Challenge 4: Complex Mock Setups

**Problem**: Existing tests have complex mock configurations.

**Solution**: Replace with real service configuration:
```python
# Before: Complex mock setup
@patch('service.database')
@patch('service.cache')
@patch('service.websocket')
async def test_complex(mock_ws, mock_cache, mock_db):
    # Complex mock configuration...

# After: Simple real service usage
async def test_complex(comprehensive_test_environment):
    # All services available and pre-configured
    db = comprehensive_test_environment['database']
    cache = comprehensive_test_environment['redis']
    websocket = comprehensive_test_environment['websocket']
```

## Migration Checklist

### Per Test File:
- [ ] Replace mock fixtures with real service fixtures
- [ ] Remove `@patch` decorators
- [ ] Replace mock assertions with real service verification
- [ ] Add service requirement markers
- [ ] Update imports to use new fixtures
- [ ] Test with real services locally
- [ ] Verify CI/CD compatibility

### Per Service:
- [ ] Update conftest.py with comprehensive fixtures
- [ ] Configure docker-compose.test.yml services
- [ ] Update requirements.txt with new dependencies
- [ ] Create service-specific migration documentation
- [ ] Run full test suite with real services
- [ ] Performance benchmark and optimize

### Per Test Suite:
- [ ] Identify all mock usage patterns
- [ ] Categorize by complexity (simple, moderate, complex)
- [ ] Migrate in order of increasing complexity
- [ ] Validate each batch before proceeding
- [ ] Update documentation and examples
- [ ] Train team on new patterns

## Automated Migration Tools

### Mock Detection Script
```python
#!/usr/bin/env python3
"""
Script to detect and categorize mock usage in test files.
"""

import os
import re
from pathlib import Path

def find_mock_usage(directory):
    """Find all mock usage in test files."""
    mock_patterns = [
        r'@patch\(',
        r'@mock\.',
        r'MagicMock\(',
        r'AsyncMock\(',
        r'Mock\(',
        r'mock_\w+',
        r'unittest\.mock'
    ]
    
    results = {}
    
    for test_file in Path(directory).rglob('test_*.py'):
        with open(test_file, 'r') as f:
            content = f.read()
            
        matches = []
        for pattern in mock_patterns:
            matches.extend(re.findall(pattern, content))
            
        if matches:
            results[str(test_file)] = {
                'mock_count': len(matches),
                'mock_types': list(set(matches)),
                'complexity': 'complex' if len(matches) > 10 else 'moderate' if len(matches) > 3 else 'simple'
            }
    
    return results

if __name__ == '__main__':
    results = find_mock_usage('.')
    
    print(f"Found {len(results)} test files with mocks:")
    
    for complexity in ['simple', 'moderate', 'complex']:
        files = [f for f, data in results.items() if data['complexity'] == complexity]
        print(f"\n{complexity.upper()} ({len(files)} files):")
        
        for file_path in sorted(files):
            data = results[file_path]
            print(f"  {file_path}: {data['mock_count']} mocks")
```

### Migration Template Generator
```python
#!/usr/bin/env python3
"""
Generate migration templates for test files.
"""

def generate_migration_template(original_file, mock_analysis):
    """Generate migration template based on mock analysis."""
    
    template = f"""
# Migration Template for {original_file}
# Original mock count: {mock_analysis['mock_count']}
# Complexity: {mock_analysis['complexity']}

# Step 1: Update imports
from test_framework.conftest_comprehensive import *

# Step 2: Replace fixtures
# OLD: @pytest.fixture def mock_database()...
# NEW: Use isolated_database fixture directly

# Step 3: Update test functions
# Replace mock assertions with real service verification

# Template for database tests:
async def test_example(isolated_database):
    # Your test logic here
    result = await isolated_database.fetchrow("SELECT * FROM table WHERE condition = $1", value)
    assert result is not None

# Template for comprehensive tests:
async def test_integration(comprehensive_test_environment):
    db = comprehensive_test_environment['database']
    redis = comprehensive_test_environment['redis']
    # Your integration test logic here

# Add service requirement markers:
# @pytest.mark.requires_postgres
# @pytest.mark.requires_redis
# @pytest.mark.requires_clickhouse
"""
    return template
```

## CI/CD Integration

### Docker Compose Update
```yaml
# Add to .github/workflows/test.yml or equivalent
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_PASSWORD: test_pass
      POSTGRES_USER: test_user
      POSTGRES_DB: netra_test
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
  
  redis:
    image: redis:7
    options: >-
      --health-cmd "redis-cli ping"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

### Environment Variables
```bash
# Required environment variables for CI
export TEST_POSTGRES_HOST=localhost
export TEST_POSTGRES_PORT=5432
export TEST_POSTGRES_USER=test_user
export TEST_POSTGRES_PASSWORD=test_pass
export TEST_POSTGRES_DB=netra_test

export TEST_REDIS_HOST=localhost
export TEST_REDIS_PORT=6379

export TEST_CLICKHOUSE_HOST=localhost
export TEST_CLICKHOUSE_HTTP_PORT=8123
```

## Validation and Testing

### Infrastructure Validation Script
```python
#!/usr/bin/env python3
"""
Validate test infrastructure setup.
"""

import asyncio
import logging
from test_framework.isolated_environment_manager import get_isolated_environment_manager
from test_framework.external_service_integration import get_external_service_manager

async def validate_infrastructure():
    """Validate all infrastructure components."""
    try:
        # Test environment manager
        env_manager = get_isolated_environment_manager()
        await env_manager.initialize()
        
        # Test database isolation
        test_id = "validation_test"
        async with env_manager.create_test_environment(test_id) as resources:
            print(f"✓ Created test environment with resources: {list(resources.keys())}")
            
            # Test database
            if 'database' in resources:
                db = resources['database']
                result = await db.fetchval("SELECT 1")
                assert result == 1
                print("✓ Database isolation working")
            
            # Test Redis
            if 'redis' in resources:
                redis = resources['redis']
                await redis.set("test_key", "test_value")
                value = await redis.get("test_key")
                assert value == "test_value"
                print("✓ Redis isolation working")
        
        await env_manager.shutdown()
        print("✓ Infrastructure validation successful")
        
    except Exception as e:
        print(f"✗ Infrastructure validation failed: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(validate_infrastructure())
```

## Success Metrics

- **Test Reliability**: Flaky test reduction from mock-related failures
- **Coverage Improvement**: Real service interaction testing
- **Performance**: Acceptable test execution times with real services
- **Maintainability**: Reduced mock setup complexity
- **Confidence**: Higher confidence in production behavior

## Timeline and Rollout

### Week 1: Infrastructure Setup
- [ ] Deploy test infrastructure
- [ ] Validate all services
- [ ] Update CI/CD pipelines

### Week 2-3: Database Migration (Priority 1)
- [ ] Auth service database tests (400+ tests)
- [ ] Backend database tests (800+ tests)
- [ ] Analytics service database tests (200+ tests)

### Week 4-5: External Services (Priority 2)
- [ ] WebSocket integration tests (300+ tests)
- [ ] HTTP client tests (500+ tests)
- [ ] File system tests (200+ tests)

### Week 6: Validation and Optimization
- [ ] Performance benchmarking
- [ ] CI/CD optimization
- [ ] Documentation updates
- [ ] Team training

### Week 7-8: Remaining Tests (Priority 3)
- [ ] Complex integration tests (500+ tests)
- [ ] Edge case tests (241+ tests)
- [ ] Performance tests

## Support and Resources

### Documentation
- [IsolatedEnvironment API Reference](./isolated_environment_manager.py)
- [External Services Integration](./external_service_integration.py)
- [Performance Optimization Guide](./performance_optimization.py)
- [Pytest Fixtures Reference](./conftest_comprehensive.py)

### Support Channels
- Technical questions: Create GitHub issues with `test-infrastructure` label
- Migration assistance: Tag `@test-infrastructure-team` in Slack
- Performance issues: Use `#performance-optimization` channel

### Training Materials
- Migration workshop recordings
- Interactive migration examples
- Best practices documentation
- Troubleshooting guides

---

**Status**: Ready for implementation
**Last Updated**: 2025-08-30
**Version**: 1.0.0
