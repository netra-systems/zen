# Real Services Testing Migration Guide

## Overview

This guide helps migrate from the existing 5766+ mock violations to real service testing infrastructure. The new system uses actual PostgreSQL, Redis, ClickHouse, WebSocket, and HTTP connections instead of mocks.

## Quick Start

### 1. Enable Real Services

```bash
# Start test infrastructure
docker-compose -f docker-compose.test.yml up -d

# Set environment variable to enable real services
export USE_REAL_SERVICES=true

# Run tests with real services
python -m pytest tests/ --real-services
```

### 2. Update Your Tests

Replace mock fixtures with real service fixtures:

```python
# OLD (using mocks)
async def test_user_creation(mock_database):
    mock_database.execute.return_value = None
    await user_service.create_user("test@example.com")
    mock_database.execute.assert_called_once()

# NEW (using real services)
async def test_user_creation(real_postgres):
    user_id = await user_service.create_user("test@example.com")
    
    # Verify in real database
    user = await real_postgres.fetchrow(
        "SELECT * FROM auth.users WHERE email = $1",
        "test@example.com"
    )
    assert user is not None
    assert user['email'] == "test@example.com"
```

## Architecture

### Service Components

```
docker-compose.test.yml
├── test-postgres (PostgreSQL 15)    # Real database with test schemas
├── test-redis (Redis 7)             # Real cache with test isolation
├── test-clickhouse (ClickHouse 23)  # Real analytics with test data
├── test-seeder                      # Loads test fixtures
└── test-monitor                     # Health monitoring
```

### Test Framework Structure

```
test_framework/
├── real_services.py                 # Core real service managers
├── conftest_real_services.py        # Real service fixtures
├── fixtures/
│   ├── postgres/                    # SQL fixture files
│   ├── redis/                       # Redis fixture data
│   └── clickhouse/                  # Analytics fixture data
└── REAL_SERVICES_MIGRATION_GUIDE.md # This guide
```

## Migration Patterns

### Database Testing

#### Before (Mocks)
```python
@pytest.fixture
def mock_database():
    mock = MagicMock()
    mock.execute = AsyncMock(return_value=None)
    mock.fetchrow = AsyncMock(return_value={'id': 123})
    return mock

async def test_create_user(mock_database):
    result = await create_user("test@example.com")
    mock_database.execute.assert_called_once()
```

#### After (Real Services) 
```python
async def test_create_user(real_postgres):
    # Test with real database
    user_id = await create_user("test@example.com")
    
    # Verify with actual database query
    user = await real_postgres.fetchrow(
        "SELECT * FROM auth.users WHERE id = $1", user_id
    )
    assert user['email'] == "test@example.com"
    assert user['is_active'] is True
    
    # Test constraints work
    with pytest.raises(Exception):  # Unique constraint
        await create_user("test@example.com")
```

### Redis Testing

#### Before (Mocks)
```python
@pytest.fixture
def mock_redis():
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    return mock

async def test_cache_user(mock_redis):
    await cache_user_profile("user123", {"name": "Test"})
    mock_redis.set.assert_called_once()
```

#### After (Real Services)
```python
async def test_cache_user(real_redis):
    profile = {"name": "Test User", "email": "test@example.com"}
    
    # Test actual caching
    await cache_user_profile("user123", profile)
    
    # Verify cached data
    cached = await real_redis.get("user_profile:user123")
    assert json.loads(cached)['name'] == "Test User"
    
    # Test TTL works
    await real_redis.set("temp_key", "value", ex=1)
    await asyncio.sleep(2)
    assert await real_redis.get("temp_key") is None
```

### ClickHouse Analytics Testing

#### Before (Mocks) 
```python
@pytest.fixture
def mock_clickhouse():
    mock = MagicMock()
    mock.execute = AsyncMock(return_value=[[100]])
    return mock

async def test_analytics_query(mock_clickhouse):
    count = await get_user_event_count("user123")
    assert count == 100
    mock_clickhouse.execute.assert_called()
```

#### After (Real Services)
```python
async def test_analytics_query(real_clickhouse):
    # Insert real test data
    await real_clickhouse.execute("""
        INSERT INTO user_events (user_id, event_type, session_id)
        VALUES ('user123', 'login', 'session1')
    """)
    
    # Test actual query
    count = await get_user_event_count("user123")
    assert count == 1
    
    # Test aggregations work
    result = await real_clickhouse.execute("""
        SELECT event_type, count() 
        FROM user_events 
        WHERE user_id = 'user123' 
        GROUP BY event_type
    """)
    assert result[0] == ('login', 1)
```

### WebSocket Testing

#### Before (Mocks)
```python
@pytest.fixture
def mock_websocket():
    mock = MagicMock()
    mock.send = AsyncMock()
    mock.receive = AsyncMock(return_value='{"type": "message"}')
    return mock

async def test_websocket_message(mock_websocket):
    await send_websocket_message(mock_websocket, {"hello": "world"})
    mock_websocket.send.assert_called_once()
```

#### After (Real Services)
```python
async def test_websocket_message(real_websocket_client):
    # Connect to real WebSocket
    await real_websocket_client.connect("/ws/chat")
    
    # Send real message
    await real_websocket_client.send({
        "type": "message",
        "content": "Hello, world!"
    })
    
    # Receive real response
    response = await real_websocket_client.receive_json()
    assert response['type'] == "message_received"
    assert 'timestamp' in response
```

### HTTP API Testing

#### Before (Mocks)
```python
@pytest.fixture
def mock_http_client():
    mock = MagicMock()
    mock.post = AsyncMock(return_value=MagicMock(
        status_code=200,
        json=lambda: {"id": "123"}
    ))
    return mock

async def test_api_call(mock_http_client):
    result = await create_user_via_api({"email": "test@example.com"})
    assert result['id'] == "123"
```

#### After (Real Services)
```python
async def test_api_call(real_http_client, real_services):
    auth_url = real_services.config.auth_service_url
    
    # Make real HTTP request
    response = await real_http_client.post(
        f"{auth_url}/api/users",
        json={"email": "test@example.com", "name": "Test User"}
    )
    
    assert response.status_code == 201
    user_data = response.json()
    assert user_data['email'] == "test@example.com"
    assert 'id' in user_data
    
    # Verify user exists in database
    user = await real_postgres.fetchrow(
        "SELECT * FROM auth.users WHERE id = $1", user_data['id']
    )
    assert user is not None
```

## Fixture Reference

### Core Fixtures

- `real_services` - Main services manager with automatic cleanup
- `real_postgres` - PostgreSQL database connection with transaction isolation
- `real_redis` - Redis connection with test database isolation  
- `real_clickhouse` - ClickHouse connection with test schema
- `real_websocket_client` - WebSocket client for connection testing
- `real_http_client` - HTTP client for API testing

### Replacement Fixtures (Drop-in Replacements)

- `redis_manager` - Replaces `mock_redis_manager` with real Redis
- `redis_client` - Replaces `mock_redis_client` with real Redis client
- `clickhouse_client` - Replaces `mock_clickhouse_client` with real ClickHouse
- `database_connection` - Replaces database mocks with real connection

### Test Data Fixtures

- `test_user` - Creates real user in database with proper relationships
- `test_organization` - Creates real organization with memberships
- `test_agent` - Creates real agent with proper configuration
- `test_conversation` - Creates real conversation with messages
- `test_user_token` - Generates real JWT token for authenticated testing

## Performance Optimizations

### Database Performance
- Uses tmpfs storage for ultra-fast I/O
- Optimized PostgreSQL configuration for testing
- Connection pooling with proper isolation
- Parallel test execution support

### Redis Performance  
- No persistence (save "") for speed
- In-memory operation only
- Automatic cleanup between tests
- Connection reuse

### ClickHouse Performance
- Optimized table engines (MergeTree)
- Proper partitioning for test data
- Bulk insertions for fixture loading
- Async operations where possible

## Configuration

### Environment Variables

```bash
# Enable real services
USE_REAL_SERVICES=true

# Service endpoints
TEST_POSTGRES_HOST=localhost
TEST_POSTGRES_PORT=5434
TEST_POSTGRES_USER=test_user
TEST_POSTGRES_PASSWORD=test_pass

TEST_REDIS_HOST=localhost  
TEST_REDIS_PORT=6381

TEST_CLICKHOUSE_HOST=localhost
TEST_CLICKHOUSE_HTTP_PORT=8125

# Test behavior
TEST_CONNECTION_TIMEOUT=10.0
TEST_QUERY_TIMEOUT=30.0
TEST_SERVICE_STARTUP_TIMEOUT=60.0
```

### Docker Compose Override

Create `docker-compose.test.override.yml` for custom settings:

```yaml
version: '3.8'
services:
  test-postgres:
    environment:
      # Custom test database settings
      POSTGRES_SHARED_BUFFERS: 512MB
      POSTGRES_WORK_MEM: 8MB
    ports:
      - "15432:5432"  # Custom port mapping
      
  test-redis:
    command: |
      redis-server 
        --maxmemory 1gb
        --maxmemory-policy allkeys-lru
    
  test-clickhouse:
    environment:
      # Custom ClickHouse settings
      CLICKHOUSE_MAX_MEMORY_USAGE: 2000000000
```

## Best Practices

### 1. Test Isolation

```python
# Good: Each test gets clean data
async def test_user_creation(real_services):
    # real_services automatically resets data before test
    user = await create_user("test@example.com")
    assert user is not None

async def test_user_deletion(real_services):
    # Starts with clean database again
    user = await create_user("delete@example.com") 
    await delete_user(user['id'])
```

### 2. Performance Monitoring

```python
async def test_database_performance(real_postgres, performance_monitor):
    performance_monitor.start("user_creation")
    
    # Create 100 users
    for i in range(100):
        await create_user(f"user{i}@example.com")
    
    duration = performance_monitor.end("user_creation")
    performance_monitor.assert_performance("user_creation", 5.0)  # Max 5 seconds
```

### 3. Realistic Test Data

```python
async def test_user_workflow(real_postgres, test_user, test_organization):
    # Uses realistic test data from fixtures
    assert test_user['email'] == 'test@example.com'
    assert test_organization['plan'] == 'free'
    
    # Test realistic workflows
    await upgrade_organization(test_organization['id'], 'pro')
    
    updated_org = await real_postgres.fetchrow(
        "SELECT * FROM backend.organizations WHERE id = $1",
        test_organization['id']
    )
    assert updated_org['plan'] == 'pro'
```

### 4. Error Testing

```python
async def test_database_constraints(real_postgres):
    # Test real database constraints
    await create_user("unique@example.com")
    
    # Should raise real database constraint error
    with pytest.raises(asyncpg.UniqueViolationError):
        await create_user("unique@example.com")

async def test_redis_memory_limits(real_redis):
    # Test real Redis behavior
    large_data = "x" * (10 * 1024 * 1024)  # 10MB
    
    # Should handle large data appropriately
    result = await real_redis.set("large_key", large_data)
    assert result is True
```

## Migration Checklist

### Phase 1: Infrastructure Setup
- [ ] Start docker-compose.test.yml services
- [ ] Verify service health with test monitor
- [ ] Run sample tests with USE_REAL_SERVICES=true
- [ ] Confirm test data seeding works

### Phase 2: Test Migration  
- [ ] Identify tests using mock fixtures
- [ ] Replace mock fixtures with real service fixtures
- [ ] Update test assertions to verify real data
- [ ] Add performance assertions where appropriate

### Phase 3: Validation
- [ ] Run full test suite with real services
- [ ] Verify test isolation works correctly
- [ ] Check test performance meets requirements
- [ ] Validate error handling with real services

### Phase 4: Optimization
- [ ] Profile test performance bottlenecks
- [ ] Optimize fixture loading and cleanup
- [ ] Add parallel test execution
- [ ] Monitor service resource usage

## Troubleshooting

### Services Won't Start
```bash
# Check service logs
docker-compose -f docker-compose.test.yml logs test-postgres
docker-compose -f docker-compose.test.yml logs test-redis
docker-compose -f docker-compose.test.yml logs test-clickhouse

# Check service health
curl http://localhost:9090/health-status
```

### Tests Are Slow
```python
# Add performance monitoring
async def test_slow_operation(real_services, performance_monitor):
    performance_monitor.start("operation")
    await slow_operation()
    duration = performance_monitor.end("operation")
    print(f"Operation took {duration:.2f} seconds")
```

### Connection Issues
```python
# Add connection debugging
async def test_debug_connections(real_services):
    # Check service availability
    await real_services.ensure_all_services_available()
    
    # Test connections individually  
    async with real_services.postgres.connection() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1
```

### Memory Issues
```bash
# Monitor service resource usage
docker stats netra-test-postgres netra-test-redis netra-test-clickhouse

# Adjust memory limits in docker-compose.test.yml
```

## Migration Examples

### Example 1: Auth Service Migration

**Before (auth_service/tests/test_login.py):**
```python
async def test_login_success(mock_database, mock_redis):
    mock_database.fetchrow.return_value = {
        'id': 'user123', 'email': 'test@example.com', 
        'password_hash': 'hashed', 'is_active': True
    }
    mock_redis.get.return_value = None
    
    result = await login("test@example.com", "password")
    assert result['success'] is True
```

**After:**
```python
async def test_login_success(real_postgres, real_redis, test_user):
    # Use real user from database
    result = await login(test_user['email'], "test123")  # Real password
    
    assert result['success'] is True
    assert result['user_id'] == test_user['id']
    
    # Verify session stored in real Redis
    session_key = f"session:{result['session_token']}"
    session_data = await real_redis.get(session_key)
    assert session_data is not None
    
    session = json.loads(session_data)
    assert session['user_id'] == test_user['id']
```

### Example 2: Backend Service Migration

**Before (netra_backend/tests/test_agents.py):**
```python
async def test_create_agent(mock_database):
    mock_database.fetchval.return_value = 'agent123'
    
    agent = await create_agent({
        'name': 'Test Agent',
        'organization_id': 'org123'
    })
    assert agent['id'] == 'agent123'
```

**After:**
```python
async def test_create_agent(real_postgres, test_organization, test_user):
    agent_data = {
        'name': 'Test Agent',
        'description': 'A test agent',
        'organization_id': test_organization['id'],
        'created_by': test_user['id']
    }
    
    agent = await create_agent(agent_data)
    
    # Verify in real database
    db_agent = await real_postgres.fetchrow(
        "SELECT * FROM backend.agents WHERE id = $1", agent['id']
    )
    assert db_agent['name'] == 'Test Agent'
    assert db_agent['organization_id'] == test_organization['id']
    assert db_agent['created_by'] == test_user['id']
    assert db_agent['is_active'] is True
```

## Benefits of Real Service Testing

### 1. Catch Real Issues
- Database constraint violations
- SQL syntax errors
- Data type mismatches
- Connection pool exhaustion
- Memory leaks
- Performance bottlenecks

### 2. Higher Confidence
- Tests real database transactions
- Validates actual connection pooling
- Tests real error conditions
- Verifies serialization/deserialization
- Tests real timeout behavior

### 3. Better Development Experience
- No mock setup/maintenance
- Real error messages
- Actual performance characteristics
- Realistic test data
- Real integration testing

### 4. Production Parity
- Same database engines and versions
- Same connection libraries
- Same error conditions  
- Same performance characteristics
- Same data constraints

## Conclusion

Real service testing provides significantly higher confidence than mocks while eliminating the overhead of maintaining 5766+ mock violations. The infrastructure is optimized for speed and reliability, making it practical for everyday development and CI/CD pipelines.

Start with the Quick Start section above, then gradually migrate tests following the patterns in this guide. The real service fixtures are designed as drop-in replacements for existing mocks, making migration straightforward.