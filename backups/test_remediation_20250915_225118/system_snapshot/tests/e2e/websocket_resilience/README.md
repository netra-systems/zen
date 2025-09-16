# WebSocket Resilience E2E Tests

This directory contains comprehensive end-to-end tests for WebSocket resilience and context preservation in the Netra Apex AI Optimization Platform.

## Business Value
- **Prevents $50K+ MRR churn** from reliability issues
- **Ensures 99.9% session continuity** guaranteeing customer trust
- **Validates enterprise-grade reliability** for mission-critical AI workloads

## Test Suite Overview

### Test 1: Client Reconnection Preserves Context (`test_1_reconnection_preserves_context.py`)

Comprehensive test suite validating that WebSocket clients can disconnect and reconnect using the same session token while preserving:
- Agent context and conversation history
- Memory and processing state  
- Tool call history and workflow state
- User preferences and variables

#### Test Cases Included:

1. **Basic Reconnection with Valid Token**
   - Validates conversation history preservation
   - Tests immediate context availability
   - Performance: < 1 second restoration time

2. **Agent Memory and Context Preservation**
   - Ensures workflow state continuity
   - Validates tool call history
   - Tests complex agent state restoration

3. **Cross-Location Reconnections**
   - Different IP addresses and geolocations
   - Mobile user simulation
   - Security validation without false positives

4. **Multiple Sequential Reconnections**
   - Stress testing with 10+ reconnection cycles
   - Memory leak detection
   - Performance consistency validation

5. **Disconnection Period Handling**
   - Brief (< 30 seconds): Full preservation
   - Medium (30s - 5 minutes): Degraded but available
   - Extended (> 5 minutes): Timeout and clean session

## Running the Tests

### Prerequisites
```bash
pip install pytest pytest-asyncio websockets
```

### Run All WebSocket Resilience Tests
```bash
# From project root
python -m pytest tests/e2e/websocket_resilience/ -v

# With detailed logging
python -m pytest tests/e2e/websocket_resilience/ -v --log-cli-level=INFO

# Run specific test
python -m pytest tests/e2e/websocket_resilience/test_1_reconnection_preserves_context.py::test_basic_reconnection_preserves_conversation_history -v
```

### Run with Coverage
```bash
python -m pytest tests/e2e/websocket_resilience/ --cov=app.websocket --cov-report=html
```

## Test Architecture

### Mock Services
- **MockAuthService**: Simulates authentication and token validation
- **MockAgentContext**: Manages agent state and conversation history  
- **WebSocketTestClient**: Custom WebSocket client with reconnection capabilities

### Key Features
- **Async Testing**: Full async/await support with pytest-asyncio
- **State Preservation**: Comprehensive state tracking and validation
- **Performance Monitoring**: Connection timing and resource usage tracking
- **Error Simulation**: Network failures, timeouts, and edge cases
- **Resource Cleanup**: Automatic connection and context cleanup

### Test Fixtures
```python
@pytest.fixture
async def websocket_test_client(session_token):
    """WebSocket test client with session management"""

@pytest.fixture
async def mock_auth_service():
    """Mock authentication service with token validation"""

@pytest.fixture 
async def mock_agent_context():
    """Mock agent context with conversation history"""

@pytest.fixture
async def established_conversation():
    """Fixture with complete conversation setup"""
```

## Expected Results

### Performance Benchmarks
- **Connection Time**: < 500ms average
- **Context Restoration**: < 1 second
- **Cross-Location Reconnection**: < 10% latency increase
- **Multiple Reconnections**: < 2% performance degradation per cycle

### Reliability Metrics
- **Consistency Rate**: 100% across all test scenarios
- **Memory Usage**: < 5% increase after 10 reconnection cycles
- **Error Rate**: 0% reconnection failures under normal conditions
- **Context Preservation**: 100% for brief disconnections, 95%+ for medium

### Validation Criteria
```python
# Conversation History
assert len(retrieved_history) == original_count
assert all(msg['id'] in original_ids for msg in retrieved_history)

# Agent Context
assert restored_context.memory_variables == original_memory_variables
assert restored_context.workflow_step == expected_step

# Performance
assert connection_time < 0.5  # 500ms
assert context_restoration_time < 1.0  # 1 second
```

## Integration with CI/CD

### GitHub Actions Integration
```yaml
- name: Run WebSocket Resilience Tests
  run: |
    python -m pytest tests/e2e/websocket_resilience/ \
      --junitxml=test-results/websocket-resilience.xml \
      --cov=app.websocket \
      --cov-report=xml
```

### Test Categories
- `@pytest.mark.websocket_resilience`: All resilience tests
- `@pytest.mark.reconnection`: Reconnection-specific tests
- `@pytest.mark.performance`: Performance benchmark tests
- `@pytest.mark.context_preservation`: Context state tests

## Troubleshooting

### Common Issues

1. **Connection Timeout Errors**
   ```python
   # Increase timeout in test configuration
   client = WebSocketTestClient(uri, token, timeout=30)
   ```

2. **Mock Service State Conflicts**
   ```python
   # Ensure proper cleanup in fixtures
   await client.disconnect()
   mock_service.reset_state()
   ```

3. **Async Test Failures**
   ```python
   # Use proper async/await patterns
   @pytest.mark.asyncio
   async def test_function():
       result = await async_operation()
   ```

### Debug Mode
```bash
# Run with debug logging
python -m pytest tests/e2e/websocket_resilience/ -v -s --log-cli-level=DEBUG
```

## Contributing

### Adding New Test Cases
1. Follow the established naming convention: `test_<scenario>_<expected_outcome>`
2. Include comprehensive docstrings with BVJ (Business Value Justification)
3. Use the established fixtures for consistency
4. Add performance benchmarks where applicable
5. Include negative test cases for error scenarios

### Test Documentation
- Update this README for new test categories
- Document expected performance benchmarks
- Include troubleshooting guidance for complex scenarios

## Related Documentation
- [WebSocket Reliability Specification](../../../SPEC/websocket_reliability.xml)
- [WebSocket Communication Specification](../../../SPEC/websocket_communication.xml)
- [Test Plan](../../../test_plans/websocket_resilience/test_1_reconnection_context_plan.md)