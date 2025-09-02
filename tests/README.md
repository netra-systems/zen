# Netra Test Suite

## Primary Test Runner: `unified_test_runner.py`

**Location:** `/tests/unified_test_runner.py`  
**Absolute Path:** `/Users/anthony/Documents/GitHub/netra-apex/tests/unified_test_runner.py`

### Main Test Orchestrator

```bash
# From project root:
python tests/unified_test_runner.py

# From anywhere with absolute path:
python /Users/anthony/Documents/GitHub/netra-apex/tests/unified_test_runner.py

# Common usage patterns:
python tests/unified_test_runner.py --category integration --no-coverage --fast-fail
python tests/unified_test_runner.py --categories smoke unit integration api --real-llm --env staging
```

## 🔴 Mission Critical Tests (Run Before Deployment)

### Core Business Value Protection
```bash
# WebSocket chat delivery - MUST PASS
python tests/mission_critical/test_websocket_agent_events_suite.py

# SSOT compliance validation
python tests/mission_critical/test_no_ssot_violations.py

# Docker orchestration stability
python tests/mission_critical/test_orchestration_integration.py

# Complete mission critical suite
python tests/unified_test_runner.py --category mission_critical --real-services
```

## 🚀 Quick Start

### Run all tests with failures first and parallel execution:
```bash
python run_tests_parallel.py
```

### Run specific test categories:
```bash
# Authentication tests
python run_tests_parallel.py tests/test_auth.py

# WebSocket tests  
python run_tests_parallel.py tests/test_websocket_connection.py

# Performance tests
python run_tests_parallel.py tests/test_performance.py

# Database tests
python run_tests_parallel.py tests/test_database_integration.py
```

### Generate test summary report:
```bash
python test_summary.py --html
```

## 📊 Test Categories

### 0. **Mission Critical Tests** (`/tests/mission_critical/`)
- 120+ tests protecting core business value
- WebSocket event delivery validation
- Agent golden pattern compliance
- Docker stability and orchestration
- SSOT violation detection
- Infrastructure resilience patterns

### 1. **Authentication Tests** (`test_auth.py`)
- Password hashing and verification
- JWT token creation and validation
- User registration and login
- Token refresh and expiration
- Password reset flow
- Authorization and access control

### 2. **WebSocket Tests** (`test_websocket_connection.py`)
- Connection establishment and teardown
- Message handling and broadcasting
- Error recovery and reconnection
- Concurrent connections
- Rate limiting
- Heartbeat/ping-pong mechanism

### 3. **Agent System Tests** (`test_agent_system.py`)
- Supervisor initialization
- Thread and message creation
- Sub-agent delegation
- Tool execution
- State management
- Parallel execution
- Token counting and context window management

### 4. **Database Integration Tests** (`test_database_integration.py`)
- User CRUD operations
- Thread and message relationships
- Run status management
- Supply catalog operations
- Transaction handling
- Cascade deletions
- Query performance
- Concurrent updates

### 5. **API Endpoint Tests** (`test_api_endpoints.py`)
- Health checks
- Thread operations (create, get, list)
- Message operations
- Run management
- Generation endpoints
- Workload analysis
- Supply catalog listing
- Optimization recommendations
- Error handling
- Pagination

### 6. **Performance Tests** (`test_performance.py`)
- Concurrent WebSocket connections (100+ simultaneous)
- Message throughput (100+ msg/s)
- Database query performance (<10ms avg)
- Token generation speed (<1ms)
- Cache performance (<5ms write, <3ms read)
- LLM streaming latency
- Parallel API requests (50+ RPS)
- Memory efficiency
- Error recovery time (<100ms)

## ⚙️ Configuration

### Test Configuration (`config/pytest.ini`)
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
addopts = --tb=short -v --disable-warnings --failed-first -rf -n auto
asyncio_default_fixture_loop_scope = function
```

### Key Features:
- **--failed-first**: Runs previously failed tests first
- **-rf**: Shows failure summary
- **-n auto**: Automatic parallel execution using all available CPUs

## 🛠️ Test Infrastructure

### Fixtures (`conftest.py`)
- **async_session**: In-memory SQLite database for testing
- **mock_redis_manager**: Mocked Redis operations
- **mock_websocket_manager**: Mocked WebSocket connections
- **mock_llm_manager**: Mocked LLM operations
- **auth_headers**: Pre-generated authentication headers
- **test_user**: Standard test user object

### Automatic Mocking
All external dependencies are automatically mocked:
- Database connections
- Redis operations
- ClickHouse queries
- External API calls
- File system operations

## 🏃 Performance Optimization

### Parallel Execution
Tests run in parallel by default using pytest-xdist:
```bash
# Use all CPUs
python run_tests_parallel.py --parallel 0

# Use specific number of workers
python run_tests_parallel.py --parallel 8
```

### Quick Mode
Stop on first failure for rapid feedback:
```bash
python run_tests_parallel.py --quick
```

### Coverage Report
Generate coverage reports:
```bash
python run_tests_parallel.py --coverage
```

### Profiling
Identify slow tests:
```bash
python run_tests_parallel.py --profile
```

## 📈 Performance Benchmarks

| Test Category | Target | Actual |
|--------------|--------|--------|
| WebSocket Connections | 100 concurrent | ✅ Supported |
| Message Throughput | 100 msg/s | ✅ Achieved |
| API Response Time | <100ms | ✅ Met |
| Database Queries | <10ms | ✅ Met |
| Token Generation | <1ms | ✅ Met |
| Cache Operations | <5ms | ✅ Met |
| Test Suite Runtime | <60s | ✅ With parallelization |

## 🔍 Debugging Failed Tests

### View detailed failure information:
```bash
pytest tests/test_auth.py::test_user_login_success -vv --tb=long
```

### Run with debugging:
```bash
pytest tests/test_auth.py --pdb
```

### Generate HTML report:
```bash
python test_summary.py --html
# Open test_report.html in browser
```

## 🎯 Test Best Practices

1. **Use fixtures** for common setup/teardown
2. **Mock external dependencies** to ensure isolated testing
3. **Test both success and failure paths**
4. **Include performance assertions** for critical paths
5. **Use descriptive test names** that explain what is being tested
6. **Keep tests independent** - no shared state between tests
7. **Test concurrency** where applicable
8. **Include edge cases** and error conditions

## 📝 Adding New Tests

1. Create test file with `test_` prefix
2. Import required fixtures from conftest.py
3. Use `@pytest.mark.asyncio` for async tests
4. Follow naming convention: `test_<feature>_<scenario>`
5. Include docstrings explaining test purpose
6. Add performance assertions where relevant

Example:
```python
@pytest.mark.asyncio
async def test_feature_success_case(client, auth_headers):
    """Test successful feature operation"""
    response = await client.post("/api/feature", 
                                 json={"data": "test"},
                                 headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

## 🚨 Common Issues and Solutions

### Issue: Tests timing out
**Solution**: Check for blocking operations, use mocks for external services

### Issue: Database connection errors
**Solution**: Ensure test database is using in-memory SQLite

### Issue: Import errors
**Solution**: Check PYTHONPATH and ensure project root is in sys.path

### Issue: Async test failures
**Solution**: Ensure proper use of `@pytest.mark.asyncio` decorator

## 📊 Continuous Integration

For CI/CD pipelines:
```yaml
test:
  script:
    - python run_tests_parallel.py --parallel 4 --failed-first
    - python test_summary.py --html
  artifacts:
    reports:
      - test_report.html
    when: always
```

## 🔧 Maintenance

Regular maintenance tasks:
1. Update test fixtures when models change
2. Review and optimize slow tests quarterly
3. Increase coverage for new features
4. Remove obsolete tests
5. Update performance benchmarks as needed