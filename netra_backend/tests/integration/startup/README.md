# WebSocket Phase Integration Tests

## Overview

This directory contains comprehensive integration tests for the **WebSocket Phase** of the system startup sequence. These tests validate that all WebSocket infrastructure components are properly initialized and configured to enable real-time chat communication between users and AI agents.

## Business Value Justification

- **Segment**: Platform/Internal
- **Business Goal**: Platform Stability & Chat Value Delivery  
- **Value Impact**: Ensures WebSocket infrastructure properly supports revenue-generating chat interactions
- **Strategic Impact**: Validates system readiness for delivering real-time AI business value to users

## Test Coverage

### Core WebSocket Components (25 Tests)

1. **UnifiedWebSocketManager Initialization** 
   - Connection storage and management
   - Thread-safe operations
   - Connection health monitoring
   - Multi-user connection tracking

2. **WebSocketManagerFactory Setup**
   - Factory pattern for user isolation
   - Resource limit enforcement
   - Manager lifecycle management
   - Connection timeout handling

3. **WebSocket Connection Handler**
   - Connection lifecycle management
   - Health checks and monitoring
   - Automatic cleanup of expired connections
   - Connection state validation

4. **WebSocket Authentication Middleware**
   - JWT token validation
   - User scope verification
   - Secure connection establishment
   - Authorization enforcement

5. **WebSocket CORS Middleware**
   - Cross-origin request validation
   - Security header management
   - Origin whitelist enforcement
   - Credential handling

6. **WebSocket Rate Limiting**
   - Per-user rate limit enforcement
   - Subscription tier-based limits
   - Burst protection
   - Fair usage policies

7. **WebSocket Message Handling**
   - Message type routing (start_agent, user_message, chat)
   - Payload validation
   - Error handling and recovery
   - Message processing statistics

8. **WebSocket Agent Handler Integration**
   - Agent execution lifecycle events
   - Real-time status updates
   - Tool execution notifications
   - Business outcome delivery

9. **WebSocket User Context Extraction**
   - Multi-user isolation
   - Context validation
   - Session management
   - Security boundary enforcement

10. **WebSocket Error Recovery Handler**
    - Connection failure recovery
    - Message queuing and replay
    - Automatic reconnection
    - Error notification system

11. **WebSocket Performance Monitor**
    - Message latency tracking
    - Connection performance metrics  
    - SLA compliance monitoring
    - Performance alerting

12. **WebSocket Reconnection Manager**
    - Network failure handling
    - Session state preservation
    - Exponential backoff
    - Priority reconnection for enterprise users

13. **WebSocket Message Buffer**
    - Reliable message delivery
    - Priority handling for critical messages
    - Persistence during network issues
    - Buffer size management

14. **WebSocket Event Validation Framework**
    - Critical event validation
    - Business context verification
    - Event schema enforcement
    - Compliance checking

15. **WebSocket Broadcast Capabilities**
    - System-wide notifications
    - Targeted messaging by subscription tier
    - Delivery confirmation
    - Broadcast performance optimization

## Critical Chat Events (5 Required Events)

The tests validate the **5 critical WebSocket events** required for chat business value delivery:

1. **`agent_started`** - User knows AI is working on their problem
2. **`agent_thinking`** - Real-time AI reasoning visibility
3. **`tool_executing`** - Shows AI using tools to solve problems  
4. **`tool_completed`** - Demonstrates problem-solving progress
5. **`agent_completed`** - Delivers final business value to user

These events are **MANDATORY** for revenue-generating chat interactions.

## Test Architecture

### Base Test Class
- **`WebSocketPhaseIntegrationTest`** - Extends `EnhancedBaseIntegrationTest`
- Provides WebSocket-specific test utilities
- Mock WebSocket components for testing without server dependencies
- Business value validation helpers
- Multi-user simulation capabilities

### Mock Components
- **`MockWebSocket`** - Simulates WebSocket connections without server
- **`MockLLMManager`** - Provides realistic business value responses
- **`MockDatabaseConnection`** - Realistic business data for testing
- **`BusinessValueMetrics`** - Tracks business outcome delivery

### Test Categories (Markers)

Tests are organized with pytest markers for selective execution:

- `@pytest.mark.websocket` - WebSocket infrastructure tests
- `@pytest.mark.startup` - System startup sequence tests  
- `@pytest.mark.business_value` - Business value delivery validation
- `@pytest.mark.multi_user` - Multi-user isolation tests
- `@pytest.mark.chat_events` - Critical chat event tests
- `@pytest.mark.performance` - Performance and reliability tests
- `@pytest.mark.security` - Security and authentication tests
- `@pytest.mark.error_recovery` - Error handling tests

## Running the Tests

### Quick Start

```bash
# Run all WebSocket startup integration tests
python run_websocket_startup_tests.py --all --verbose

# Run specific test categories  
python run_websocket_startup_tests.py --chat-events --multi-user

# Run with fast-fail (stop on first failure)
python run_websocket_startup_tests.py --websocket --startup --fast-fail
```

### Using pytest directly

```bash
# Run all tests
pytest test_websocket_phase_comprehensive.py -v

# Run specific test methods
pytest test_websocket_phase_comprehensive.py::WebSocketPhaseIntegrationTest::test_websocket_critical_chat_events -v

# Run tests by marker
pytest -m "chat_events or multi_user" -v

# Run with coverage
pytest --cov=netra_backend.app.websocket_core test_websocket_phase_comprehensive.py
```

### Test Categories

```bash
# WebSocket infrastructure only
python run_websocket_startup_tests.py --websocket

# Multi-user isolation tests
python run_websocket_startup_tests.py --multi-user

# Critical chat events validation
python run_websocket_startup_tests.py --chat-events

# Performance and reliability
python run_websocket_startup_tests.py --performance

# Security and authentication  
python run_websocket_startup_tests.py --security

# Error recovery capabilities
python run_websocket_startup_tests.py --error-recovery
```

## Test Environment Configuration

The tests use the following environment configuration:

```bash
ENVIRONMENT=test
TESTING=true
WEBSOCKET_TEST_MODE=integration
USE_MOCK_COMPONENTS=false     # Use real components
DISABLE_EXTERNAL_DEPENDENCIES=true
USE_WEBSOCKET_SUPERVISOR_V3=true
```

## Key Integration Points Tested

### 1. WebSocket Manager Integration
- UnifiedWebSocketManager with Factory pattern
- Thread-safe connection management
- User isolation enforcement
- Connection health monitoring

### 2. Authentication Integration  
- JWT token validation pipeline
- User context extraction and validation
- Security boundary enforcement
- Multi-user session isolation

### 3. Agent Execution Integration
- WebSocket event generation for agent lifecycle
- Real-time progress updates
- Tool execution notifications
- Business outcome delivery via WebSocket

### 4. Error Recovery Integration
- Connection failure detection
- Message queuing and replay
- Automatic reconnection handling
- User notification system

### 5. Performance Monitoring Integration
- Real-time performance metrics
- SLA compliance checking
- Alert system integration
- Performance optimization

## Business Value Validation

Each test includes **Business Value Justification (BVJ)** and validates:

1. **User Experience** - Events provide real-time feedback
2. **Enterprise Features** - Subscription tier-specific capabilities
3. **Security** - Multi-user isolation and data protection
4. **Reliability** - Error recovery and performance monitoring
5. **Scalability** - Resource limits and performance optimization

### Business Outcome Assertions

Tests validate specific business outcomes:
- Cost optimization recommendations delivered
- Performance improvements quantified  
- Risk assessments completed
- Compliance reports generated
- Resource utilization optimized

## Troubleshooting

### Common Issues

1. **WebSocket Connection Errors**
   ```bash
   # Tests use MockWebSocket - no real server needed
   # Check test environment configuration
   ```

2. **Multi-user Isolation Failures** 
   ```bash
   # Verify UserExecutionContext creation
   # Check factory isolation logic
   ```

3. **Event Timing Issues**
   ```bash
   # Review event sequence validation
   # Check async/await patterns
   ```

4. **Performance Test Failures**
   ```bash
   # Verify performance thresholds
   # Check system resource availability
   ```

### Debug Mode

```bash
# Run with debug logging
python run_websocket_startup_tests.py --all --verbose

# Run single test with detailed output
pytest test_websocket_phase_comprehensive.py::WebSocketPhaseIntegrationTest::test_websocket_critical_chat_events -vvs
```

## Test Reporting

Test results include:
- Component initialization tracking
- Business value delivery metrics
- Performance measurements
- Security validation results
- Error recovery statistics
- Multi-user isolation verification

## Integration with CI/CD

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run WebSocket Startup Integration Tests
  run: |
    cd netra_backend/tests/integration/startup
    python run_websocket_startup_tests.py --all --fast-fail
```

## Compliance and Security

Tests validate compliance with:
- Enterprise security requirements
- Multi-user data isolation standards
- Performance SLA requirements
- Error recovery best practices
- Authentication and authorization policies

## Contributing

When adding new WebSocket components:

1. Add initialization test in appropriate category
2. Include business value validation  
3. Add multi-user isolation test if applicable
4. Include performance validation
5. Add error recovery test if needed
6. Update this README with new test coverage

## Related Documentation

- [User Context Architecture](../../../reports/archived/USER_CONTEXT_ARCHITECTURE.md)
- [WebSocket Modernization Report](../../../reports/archived/WEBSOCKET_MODERNIZATION_REPORT.md)  
- [Agent Architecture Guide](../../../docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)
- [Test Architecture Overview](../../TEST_ARCHITECTURE_VISUAL_OVERVIEW.md)