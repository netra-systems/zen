# Agent Testing Strategy

## Overview
Comprehensive testing strategy for the Netra AI platform's multi-agent system, ensuring robust validation of all agent functionality with 100% critical path coverage.

## Test Suite Architecture

### Core Agent Test Suites

#### 1. TriageSubAgent (`tests/test_triage_sub_agent.py`)
**Coverage:** 26 tests
- **Initialization:** Agent setup with/without Redis
- **Entry Conditions:** Request validation
- **Caching:** Cache hit/miss scenarios
- **Categorization:** Cost/performance optimization detection
- **Enrichment:** Entity extraction, intent detection, tool recommendations
- **Error Handling:** Fallback mechanisms, retry logic
- **WebSocket:** Status updates and logging

#### 2. DataSubAgent (`tests/test_data_sub_agent.py`)
**Coverage:** 25 tests
- **Initialization:** Component setup, Redis integration
- **Cache Operations:** Schema caching with TTL
- **ClickHouse:** Data fetching and query execution
- **Execution Flow:** Main processing pipeline
- **WebSocket Updates:** Real-time status streaming
- **Health Monitoring:** Circuit breaker status

#### 3. ActionsToMeetGoalsSubAgent (`tests/test_actions_sub_agent.py`)
**Coverage:** 25 tests
- **Initialization:** Agent and reliability setup
- **Entry Conditions:** Prerequisites validation
- **JSON Processing:** Extraction and fallback recovery
- **Action Planning:** Goal decomposition
- **Prompt Handling:** Large prompt management
- **Fallback Strategy:** Default structure generation

#### 4. ReportingSubAgent (`tests/test_reporting_sub_agent.py`)
**Coverage:** 21 tests
- **Report Generation:** Complete/partial data handling
- **Formatting:** Executive summary creation
- **Data Aggregation:** Multi-agent result compilation
- **Error Handling:** Missing data scenarios
- **Streaming:** WebSocket update delivery

## Testing Principles

### 1. Module Architecture Compliance
- **450-line Limit:** All test files ≤300 lines
- **25-line Functions:** All test functions ≤8 lines
- **Single Responsibility:** Each test validates one aspect

### 2. Comprehensive Coverage
- **Positive Tests:** Valid inputs and expected flows
- **Negative Tests:** Error conditions and edge cases
- **Integration Tests:** Component interactions
- **Performance Tests:** Timeout and circuit breaker behavior

### 3. Mock Strategy
```python
# Consistent mocking pattern across all tests
@pytest.fixture
def mock_component():
    mock = MagicMock()
    mock.async_method = AsyncMock()
    return mock
```

### 4. State Management
```python
# Use real DeepAgentState objects for realistic testing
from app.agents.state import DeepAgentState

state = DeepAgentState(
    user_request="test request",
    triage_result=mock_triage_result,
    data_result=mock_data_result
)
```

## Test Execution Guidelines

### Running Individual Suites
```bash
# Run specific agent test suite
python -m pytest tests/test_triage_sub_agent.py -v

# Run with coverage
python -m pytest tests/test_data_sub_agent.py --cov=app.agents.data_sub_agent
```

### Running All Agent Tests
```bash
# Run all agent test suites
python -m pytest tests/test_*_agent.py -v

# Run with detailed output
python -m pytest tests/test_*_agent.py -v --tb=short
```

### Integration with CI/CD
```yaml
# GitHub Actions configuration
- name: Run Agent Tests
  run: |
    python -m pytest tests/test_*_agent.py \
      --junitxml=test-results/agent-tests.xml \
      --cov=app.agents \
      --cov-report=xml
```

## Key Testing Patterns

### 1. Async Testing
```python
@pytest.mark.asyncio
async def test_async_operation(agent):
    result = await agent.execute(state, "run-id", False)
    assert result is not None
```

### 2. Circuit Breaker Testing
```python
async def test_circuit_breaker_opens(agent):
    agent.reliability.circuit_breaker.fail()
    status = agent.get_circuit_breaker_status()
    assert status["state"] == "open"
```

### 3. Cache Testing
```python
async def test_cache_expiry(agent):
    agent._schema_cache_timestamps["table"] = time.time() - 3600
    result = await agent._get_cached_schema("table")
    assert result is None  # Cache expired
```

### 4. WebSocket Testing
```python
async def test_websocket_update(agent, mock_ws):
    await agent._send_update("run-id", {"status": "processing"})
    mock_ws.send_message.assert_called_once()
```

## Test Data Management

### Fixtures
- **Common fixtures:** Defined in `conftest.py`
- **Agent-specific fixtures:** Defined in individual test files
- **Mock data:** Consistent across test suites

### Sample Data Structures
```python
# Consistent test data patterns
SAMPLE_OPTIMIZATION = {
    "optimization_type": "cost_reduction",
    "recommendations": ["Optimize resource allocation"],
    "cost_savings": 5000.0
}

SAMPLE_ACTION_PLAN = {
    "actions": [
        {"step": 1, "action": "Analyze current state"},
        {"step": 2, "action": "Implement optimization"}
    ]
}
```

## Error Scenarios Coverage

### 1. Network Failures
- Connection timeouts
- Service unavailability
- Partial response handling

### 2. Data Validation
- Invalid input formats
- Missing required fields
- Type mismatches

### 3. Resource Constraints
- Memory limitations
- Large data handling
- Concurrent request limits

### 4. Dependency Failures
- Redis unavailability
- ClickHouse connection issues
- LLM service errors

## Performance Testing

### Response Time Validation
```python
async def test_performance_threshold(agent):
    start = time.time()
    await agent.execute(state, "run-id", False)
    duration = time.time() - start
    assert duration < 5.0  # 5 second threshold
```

### Memory Usage
```python
def test_memory_efficiency(agent):
    import tracemalloc
    tracemalloc.start()
    # Execute operation
    current, peak = tracemalloc.get_traced_memory()
    assert peak < 100_000_000  # 100MB limit
```

## Maintenance Guidelines

### 1. Test Updates
- Update tests when agent logic changes
- Add tests for new features
- Remove obsolete test cases

### 2. Mock Maintenance
- Keep mocks synchronized with interfaces
- Update mock responses for API changes
- Document mock behavior

### 3. Coverage Monitoring
- Maintain >80% code coverage
- Focus on critical paths
- Document uncovered edge cases

## Integration with test_runner.py

### Configuration
```python
# Add to test_runner.py
AGENT_TEST_SUITES = [
    "tests/test_triage_sub_agent.py",
    "tests/test_data_sub_agent.py", 
    "tests/test_actions_sub_agent.py",
    "tests/test_reporting_sub_agent.py"
]

async def run_agent_tests():
    """Run all agent test suites."""
    for suite in AGENT_TEST_SUITES:
        result = await run_test_suite(suite)
        if not result.success:
            logger.error(f"Agent test suite failed: {suite}")
            return False
    return True
```

### Execution Levels
- **Unit:** Individual agent methods
- **Integration:** Agent interactions
- **E2E:** Complete workflow validation

## Success Metrics

### Coverage Targets
- **Line Coverage:** >80%
- **Branch Coverage:** >70%
- **Critical Path:** 100%

### Performance Targets
- **Test Execution:** <30 seconds total
- **Individual Tests:** <1 second each
- **Setup/Teardown:** <100ms

### Quality Metrics
- **Zero flaky tests**
- **All tests deterministic**
- **Clear failure messages**

## Continuous Improvement

### Regular Reviews
- Weekly test suite health checks
- Monthly coverage analysis
- Quarterly performance review

### Documentation Updates
- Keep test documentation current
- Document new patterns
- Update examples regularly

## Troubleshooting

### Common Issues
1. **Import Errors:** Check module paths and dependencies
2. **Async Warnings:** Ensure proper event loop handling
3. **Mock Failures:** Verify mock setup matches actual interfaces
4. **Timeout Errors:** Adjust timeout values for CI environment

### Debug Commands
```bash
# Verbose output
python -m pytest tests/test_triage_sub_agent.py -vvv

# Stop on first failure
python -m pytest tests/test_data_sub_agent.py -x

# Run specific test
python -m pytest tests/test_actions_sub_agent.py::TestInitialization::test_agent_initialization
```

## Conclusion
This comprehensive testing strategy ensures robust validation of all agent functionality while maintaining code quality standards and enabling rapid development cycles.