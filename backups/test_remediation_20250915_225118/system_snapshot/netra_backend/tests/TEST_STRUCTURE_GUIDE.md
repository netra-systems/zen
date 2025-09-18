# Netra Test Structure Guide

## Test Organization Principles

### 1. Clear Test Naming Convention
```python
# ✅ GOOD: Descriptive test names that explain what is being tested
async def test_agent_handles_concurrent_requests_without_race_conditions():
    """Test that agent service properly handles multiple concurrent requests"""
    
# ❌ BAD: Vague or generic test names  
async def test_agent_works():
    """Test agent"""
```

### 2. Test Categories

#### Unit Tests (`test_*_unit.py`)
- **Purpose**: Test individual functions/methods in isolation
- **Mocking**: Mock ALL external dependencies
- **Speed**: < 100ms per test
- **Example**: Testing a single service method with mocked database

#### Integration Tests (`test_*_integration.py`)
- **Purpose**: Test interaction between components
- **Mocking**: Mock external services (APIs, LLMs) but use real database
- **Speed**: < 1s per test
- **Example**: Testing API endpoint with real database

#### E2E Tests (`test_*_e2e.py`)
- **Purpose**: Test complete user workflows
- **Mocking**: Minimal - only external APIs if needed
- **Speed**: < 10s per test
- **Example**: Complete chat conversation flow

#### Critical Path Tests (`test_*_critical.py`)
- **Purpose**: Test essential functionality that must never break
- **Mocking**: Whatever ensures reliability
- **Speed**: < 500ms per test
- **Example**: User authentication, payment processing

## Common Test Patterns

### 1. Pass-Through Function Testing
When testing functions that primarily delegate to other services:

```python
# CLEAR PATTERN: Explicitly test delegation behavior
async def test_agent_service_delegates_to_supervisor():
    """
    Test that AgentService.process_request correctly delegates to SupervisorAgent.
    This is a PASS-THROUGH test - we're verifying delegation, not logic.
    """
    # Arrange: Mock the supervisor
    mock_supervisor = AsyncMock()
    mock_supervisor.run.return_value = {"status": "success"}
    
    # Act: Call the pass-through function
    service = AgentService(supervisor=mock_supervisor)
    result = await service.process_request("test request")
    
    # Assert: Verify delegation occurred with correct parameters
    mock_supervisor.run.assert_called_once_with("test request")
    assert result == {"status": "success"}
    # ✅ CLEAR: We're testing delegation, not implementation
```

### 2. Mock vs Real Dependencies

```python
# DOCUMENT YOUR MOCKING STRATEGY
class TestDatabaseRepository:
    """
    Tests for database repository layer.
    
    MOCKING STRATEGY:
    - Database Session: MOCKED (using AsyncMock)
    - SQLAlchemy Models: MOCKED (using factory functions)
    - Business Logic: REAL (actual repository code)
    
    RATIONALE: We test repository logic without database overhead.
    """
    
    @pytest.fixture
    def mock_session(self):
        """Mock database session - simulates SQLAlchemy AsyncSession"""
        session = AsyncMock()
        session.add = MagicMock()  # Synchronous operation
        session.commit = AsyncMock()  # Async operation
        return session
```

### 3. Test Data Factories

```python
# CREATE CLEAR TEST DATA FACTORIES
class TestDataFactory:
    """Factory for creating consistent test data across tests"""
    
    @staticmethod
    def create_test_user(user_id: str = None, **overrides) -> dict:
        """
        Create a test user with sensible defaults.
        
        Args:
            user_id: Optional user ID (auto-generated if not provided)
            **overrides: Override any default values
            
        Returns:
            Complete user dictionary for testing
        """
        base_user = {
            "id": user_id or f"user_{datetime.now().timestamp()}",
            "email": "test@example.com",
            "name": "Test User",
            "created_at": datetime.now(),
            "is_active": True,
        }
        base_user.update(overrides)
        return base_user
```

### 4. Async Test Patterns

```python
# CLEAR ASYNC TEST STRUCTURE
@pytest.mark.asyncio
class TestAsyncOperations:
    """Test async operations with clear setup/teardown"""
    
    async def asyncSetUp(self):
        """Async setup - runs before each test"""
        self.db_connection = await create_test_database()
        self.test_data = await self.seed_test_data()
        
    async def asyncTearDown(self):
        """Async teardown - runs after each test"""
        await self.db_connection.close()
        await cleanup_test_data()
        
    async def test_concurrent_operations(self):
        """
        Test multiple concurrent operations.
        
        TEST SCENARIO:
        1. Create 10 concurrent requests
        2. Verify all complete without race conditions
        3. Check final state consistency
        """
        # Create concurrent tasks
        tasks = [
            self.make_request(f"request_{i}") 
            for i in range(10)
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results) == 10
        assert all(r["status"] == "success" for r in results)
```

## Test Documentation Standards

### Every Test File Should Have:

```python
"""
Module: test_agent_service.py
Purpose: Test AgentService orchestration and lifecycle management

Test Categories:
- Unit: Mock all dependencies, test business logic
- Integration: Use real database, mock external APIs
- E2E: Full workflow testing with minimal mocks

Dependencies:
- Database: PostgreSQL (mocked in unit, real in integration)
- Redis: Mock in unit, real in integration
- LLM APIs: Always mocked except in E2E tests marked with @pytest.mark.real_llm

Performance Targets:
- Unit tests: < 100ms each
- Integration tests: < 1s each
- E2E tests: < 10s each
"""
```

### Every Test Class Should Have:

```python
class TestAgentLifecycle:
    """
    Test agent lifecycle management.
    
    SCOPE: Unit testing of agent state transitions
    MOCKS: All external dependencies (database, Redis, LLMs)
    FOCUS: State machine correctness and error handling
    
    Test Matrix:
    - States: IDLE -> STARTING -> RUNNING -> STOPPING -> TERMINATED
    - Errors: Network failures, timeout, invalid transitions
    - Concurrency: Multiple agents, race conditions
    """
```

### Every Complex Test Should Have:

```python
async def test_complex_workflow(self):
    """
    Test complete user journey from login to task completion.
    
    SCENARIO:
    1. User logs in with valid credentials
    2. Creates new conversation thread
    3. Sends message requiring multi-agent collaboration
    4. Agents process request with tool usage
    5. Response is delivered via WebSocket
    6. Thread is saved to database
    
    ASSERTIONS:
    - Auth token is valid (line 45)
    - Thread created in database (line 52)
    - All agents complete successfully (line 67)
    - WebSocket message delivered (line 73)
    - Database state is consistent (line 81)
    
    PERFORMANCE: Should complete in < 5 seconds
    """
```

## Anti-Patterns to Avoid

### 1. Mystery Mocks
```python
# ❌ BAD: Unclear what's being mocked
mock = MagicMock()
mock.return_value = {"data": "test"}

# ✅ GOOD: Clear mock purpose
mock_llm_client = MagicMock(spec=AnthropicClient)
mock_llm_client.generate.return_value = {"response": "Generated text"}
```

### 2. Implicit Test Dependencies
```python
# ❌ BAD: Hidden dependency on test order
def test_create_user(self):
    self.user_id = create_user()  # Sets class variable
    
def test_delete_user(self):
    delete_user(self.user_id)  # Depends on test_create_user running first

# ✅ GOOD: Explicit setup
def test_delete_user(self):
    # Arrange: Create user explicitly for this test
    user_id = create_user()
    
    # Act: Delete the user
    result = delete_user(user_id)
    
    # Assert
    assert result == True
```

### 3. Overly Complex Mocks
```python
# ❌ BAD: Mock does too much
mock_service = MagicMock()
mock_service.process.side_effect = lambda x: {
    "result": x.upper() if isinstance(x, str) else str(x),
    "timestamp": datetime.now(),
    "metadata": {"processed": True}
}

# ✅ GOOD: Simple, predictable mocks
mock_service = MagicMock()
mock_service.process.return_value = {"result": "SUCCESS", "processed": True}
```

## Test Execution Guidelines

### Running Tests by Category
```bash
# Quick validation (smoke tests)
python test_runner.py --level smoke

# Development testing (unit tests)
python test_runner.py --level unit

# Feature validation (integration)
python test_runner.py --level integration

# Full validation (comprehensive)
python test_runner.py --level comprehensive
```

### Test Selection Patterns
```bash
# Run specific test file
pytest app/tests/services/test_agent_service.py -v

# Run tests matching pattern
pytest -k "test_concurrent" -v

# Run only critical path tests
pytest -m critical -v

# Run with coverage
pytest --cov=app --cov-report=html
```

## Performance Testing

### Clear Performance Test Structure
```python
@pytest.mark.performance
async def test_agent_handles_load():
    """
    Load test: Agent handles 100 concurrent requests.
    
    PERFORMANCE REQUIREMENTS:
    - Throughput: > 50 requests/second
    - Latency p50: < 100ms
    - Latency p99: < 500ms
    - Error rate: < 1%
    
    LOAD PATTERN:
    - Ramp up: 10 requests/second for 10 seconds
    - Sustain: 100 concurrent requests for 30 seconds
    - Cool down: Monitor for 10 seconds
    """
    results = await run_load_test(
        target=agent_service.process,
        concurrent_requests=100,
        duration_seconds=30
    )
    
    assert results.throughput > 50
    assert results.latency_p50 < 0.1
    assert results.latency_p99 < 0.5
    assert results.error_rate < 0.01
```

## Debugging Tests

### Add Debug Helpers
```python
def debug_test_state(test_name: str, **state):
    """Helper to debug test state during development"""
    if os.getenv("DEBUG_TESTS"):
        print(f"\n=== DEBUG: {test_name} ===")
        for key, value in state.items():
            print(f"  {key}: {value}")
        print("=" * 40)

# Usage in tests
async def test_complex_scenario(self):
    result = await some_operation()
    
    debug_test_state(
        "test_complex_scenario",
        result=result,
        expected="success",
        actual_state=self.agent.state
    )
    
    assert result == "success"
```

## Test Maintenance

### Regular Test Review Checklist
- [ ] Remove obsolete tests for deleted features
- [ ] Update mocks when interfaces change
- [ ] Consolidate duplicate test logic into fixtures
- [ ] Update test documentation when behavior changes
- [ ] Review and update performance baselines
- [ ] Check for flaky tests and fix root causes

### Test Health Metrics
- Coverage: Minimum 97% for critical paths
- Execution time: Total suite < 10 minutes
- Flakiness: < 1% failure rate for passing tests
- Maintenance: Update tests with every feature change