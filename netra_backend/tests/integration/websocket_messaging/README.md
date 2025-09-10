# WebSocket Messaging Integration Tests

## Overview

This directory contains comprehensive integration tests for the WebSocket messaging flow that validates the complete "Golden Path" user journey from message reception through agent execution to response delivery.

## Business Value

**Critical for $500K+ ARR Protection**: These tests validate the primary delivery mechanism for our AI value - the WebSocket-based chat functionality that represents 90% of our delivered business value to users.

## Test Coverage

### Core Message Flow Tests
- **Message Reception & Parsing**: Validates JSON parsing, size limits (8192 bytes), and format normalization
- **Message Routing**: Tests MessageRouter → AgentHandler → MessageHandlerService flow
- **Authentication Validation**: Ensures user context isolation and security during message processing
- **Agent Execution**: Validates all 5 critical WebSocket events for business value delivery
- **Response Delivery**: Tests final response delivery and database persistence

### Critical WebSocket Events Validation
The tests ensure all 5 mission-critical events are delivered:
1. `agent_started` - User engagement indication
2. `agent_thinking` - Real-time AI reasoning transparency  
3. `tool_executing` - Tool usage visibility
4. `tool_completed` - Tool results delivery
5. `agent_completed` - Final response ready notification

### Error Handling & Edge Cases
- Malformed JSON message handling
- Oversized message rejection (>8192 bytes)
- Authentication failures and security violations
- Connection state validation during messaging
- Concurrent user message processing with isolation

## Test Architecture

### Base Test Class
```python
class TestWebSocketMessagingFlowComprehensive(BaseIntegrationTest)
```

### Key Components Tested
- `MessageRouter` - Routes messages to appropriate handlers
- `AgentHandler` - Processes agent-related messages
- `MessageHandlerService` - Core message processing service
- `ExecutionEngineFactory` - Creates user-isolated execution engines
- `UserExecutionContext` - Maintains user context and security

### Test Fixtures
- `real_services_fixture` - Provides real PostgreSQL and Redis connections
- Real WebSocket connections when available, graceful fallback to MockWebSocketConnection
- SSOT authentication and user context creation

## Running the Tests

### Integration Test with Real Services
```bash
# Run complete WebSocket messaging flow tests
python tests/unified_test_runner.py --category integration --real-services --test-file netra_backend/tests/integration/websocket_messaging/test_websocket_messaging_flow_comprehensive_integration.py

# Run with coverage
python tests/unified_test_runner.py --category integration --real-services --coverage --test-file netra_backend/tests/integration/websocket_messaging/

# Fast feedback mode (essential tests only)
python tests/unified_test_runner.py --execution-mode fast_feedback --test-file netra_backend/tests/integration/websocket_messaging/test_websocket_messaging_flow_comprehensive_integration.py::TestWebSocketMessagingFlowComprehensive::test_complete_message_flow_with_agent_execution
```

### Local Development Testing
```bash
# Ensure Docker services are running
python tests/unified_test_runner.py --real-services --category integration websocket_messaging

# Test specific scenarios
pytest netra_backend/tests/integration/websocket_messaging/ -v -k "test_error_handling_malformed_messages"
```

## Test Scenarios

### 1. Complete Message Flow (`test_complete_message_flow_with_agent_execution`)
**Purpose**: Validates the entire Golden Path from WebSocket reception to agent response
**Business Value**: Ensures core chat functionality delivers AI insights to users
**Coverage**: Message parsing, routing, authentication, agent execution, event delivery

### 2. Error Handling (`test_error_handling_malformed_messages`) 
**Purpose**: Validates robust error handling for malformed/invalid messages
**Business Value**: Protects user experience from system failures and invalid input
**Coverage**: JSON parsing errors, missing fields, invalid types, null values

### 3. Concurrent Processing (`test_concurrent_message_processing`)
**Purpose**: Validates multi-user isolation and concurrent message handling
**Business Value**: Ensures system scales to handle multiple users simultaneously  
**Coverage**: User context isolation, concurrent execution, response attribution

### 4. Message Queue Processing (`test_message_queue_processing_and_priority`)
**Purpose**: Validates message queuing and priority handling under load
**Business Value**: Ensures responsive user experience under high message volume
**Coverage**: Queue processing, priority handling, message ordering

## Critical Validations

### WebSocket Events (Business Value Delivery)
Every test that triggers agent execution MUST validate all 5 WebSocket events using:
```python
assert_websocket_events_sent(events_received, [
    "agent_started", "agent_thinking", "tool_executing", 
    "tool_completed", "agent_completed"
])
```

### Authentication & Security
All tests validate:
- User ID consistency throughout message flow
- Authentication token validation
- User context isolation between concurrent users
- Authorization for message processing

### Performance & Reliability
Tests validate:
- Message processing within reasonable timeframes (<30s for integration tests)
- Error recovery and graceful degradation
- Connection state validation
- Resource cleanup after processing

## Dependencies

### Required Services
- **PostgreSQL** (real database for user context and persistence)
- **Redis** (real cache for session state)
- **WebSocket endpoint** (real or mock connection)

### SSOT Imports
- `test_framework.base_integration_test.BaseIntegrationTest`
- `test_framework.fixtures.real_services.real_services_fixture`
- `test_framework.websocket_helpers.assert_websocket_events_sent`
- `shared.isolated_environment.get_env`
- `shared.id_generation.UnifiedIdGenerator`

## Integration with Golden Path

These tests directly validate the Golden Path user flow documented in `GOLDEN_PATH_USER_FLOW_COMPLETE.md`:

1. **Phase 1**: WebSocket connection and authentication
2. **Phase 2**: Message reception and routing  
3. **Phase 3**: Agent orchestration and execution
4. **Phase 4**: Results delivery and persistence

## Troubleshooting

### Common Issues

**WebSocket Connection Failures**
- Ensure backend service is running on port 8000
- Check Docker services are up: `python tests/unified_test_runner.py --real-services --health-check`
- Verify WebSocket endpoint is accessible: `curl http://localhost:8000/health`

**Event Collection Timeouts**
- Increase event collection timeout for slow environments
- Check agent execution is not blocked by missing LLM credentials
- Verify all 5 events are being sent by agent implementation

**Authentication Errors**
- Ensure test user context is properly created in real database
- Verify JWT token format and user ID consistency
- Check user context isolation is working correctly

### Debug Commands

```bash
# Check service health
python tests/unified_test_runner.py --real-services --health-check

# Run with verbose logging
python tests/unified_test_runner.py --category integration --test-file netra_backend/tests/integration/websocket_messaging/ --verbose

# Debug specific test
pytest netra_backend/tests/integration/websocket_messaging/test_websocket_messaging_flow_comprehensive_integration.py::TestWebSocketMessagingFlowComprehensive::test_complete_message_flow_with_agent_execution -v -s --pdb
```

## Success Criteria

A successful test run validates:
- ✅ Complete message flow from WebSocket to agent execution
- ✅ All 5 critical WebSocket events delivered
- ✅ User authentication and context isolation
- ✅ Error handling and recovery
- ✅ Multi-user concurrent processing
- ✅ Message queue processing and priority
- ✅ Response delivery and persistence
- ✅ Business value delivery through actionable AI insights

## Related Documentation

- [GOLDEN_PATH_USER_FLOW_COMPLETE.md](../../../GOLDEN_PATH_USER_FLOW_COMPLETE.md) - Complete Golden Path flow
- [TEST_CREATION_GUIDE.md](../../../../reports/testing/TEST_CREATION_GUIDE.md) - SSOT test creation patterns
- [User Context Architecture](../../../../reports/archived/USER_CONTEXT_ARCHITECTURE.md) - Factory patterns and isolation
- [Test Architecture Visual Overview](../../../TEST_ARCHITECTURE_VISUAL_OVERVIEW.md) - Complete test infrastructure guide