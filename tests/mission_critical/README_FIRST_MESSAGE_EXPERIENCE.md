# First Message Experience Test Suite

## CRITICAL: User Activation & Conversion Testing

This test suite validates the **most important user touchpoint** - the first message a new user sends to Netra Apex. This interaction determines whether users activate, convert to paid tiers, or churn immediately.

## Business Impact

- **Revenue**: User activation drives conversion to paid tiers ($500K+ ARR)
- **Retention**: Poor first experience = immediate churn
- **Growth**: First impression determines word-of-mouth and expansion
- **Value Delivery**: 90% of platform value delivered through chat

## What This Suite Tests

### 1. Happy Path First Message (`test_happy_path_first_message`)
- New user sends first message
- System processes through complete agent pipeline
- All required WebSocket events sent in correct order
- User receives substantive AI response within 45 seconds
- Complete user isolation via factory patterns

### 2. Concurrent Users (`test_concurrent_first_messages`)
- 5+ users send first messages simultaneously
- Each user gets properly isolated context
- No data leakage between users
- All users receive correct, personalized responses
- System maintains performance under concurrent load

### 3. Service Degradation (`test_first_message_with_service_degradation`)
- First message during slow LLM/database conditions
- System sends regular "thinking" updates (2-5s intervals)
- User kept informed during processing
- Response eventually completes despite delays
- No timeout errors exposed to user

### 4. Rapid Messages (`test_rapid_first_messages`)
- User sends multiple messages in quick succession
- Messages queued and processed in order
- No messages lost or duplicated
- Context maintained across messages
- All messages receive responses

### 5. Malformed Input (`test_malformed_first_message`)
- Empty messages
- Very long messages (>10KB)
- Special characters/emojis
- Potential injection attempts
- All handled gracefully with user-friendly errors

### 6. Load Testing (`test_load_50_concurrent_users`)
- 50+ concurrent first-time users
- 90%+ success rate maintained
- P99 response time < 60 seconds
- System remains stable under load

## Required WebSocket Events

Per `SPEC/first_message_experience.xml`, these events MUST be sent in order:

1. **message_received** (< 100ms) - Confirms processing started
2. **agent_started** (< 500ms) - AI agent begins work
3. **agent_thinking** (2-5s intervals) - Real-time reasoning visibility
4. **tool_executing** - Tool usage transparency
5. **tool_completed** - Tool results display
6. **agent_completed** (< 45s) - Final response ready
7. **response_complete** - Full cycle finished

## Running the Tests

### Prerequisites

```bash
# Ensure Docker services are running
python scripts/docker_manual.py start

# Or use unified test runner (starts Docker automatically)
python tests/unified_test_runner.py --real-services
```

### Run Full Suite

```bash
# Run complete first message test suite
pytest tests/mission_critical/test_first_message_experience.py -v

# Run with detailed output
pytest tests/mission_critical/test_first_message_experience.py -v -s

# Run specific test
pytest tests/mission_critical/test_first_message_experience.py::TestFirstMessageExperience::test_happy_path_first_message -v
```

### Run with Test Runner

```bash
# Include in mission critical tests
python tests/unified_test_runner.py --category mission-critical --real-services

# Run just first message tests
python tests/unified_test_runner.py --pattern "test_first_message*" --real-services
```

## Success Criteria

### SLO Requirements
- **Response Time**: P99 < 45 seconds
- **Success Rate**: 99.9% availability
- **Concurrent Users**: Support 50+ simultaneous
- **Event Latency**: < 200ms between events

### Business Value Validation
- Response contains substantive AI content (>50 chars)
- Demonstrates problem-solving capability
- User context properly isolated
- All WebSocket events enhance user experience
- Error messages are helpful, never technical

## Failure Impact

**ANY FAILURE IN THIS SUITE BLOCKS DEPLOYMENT**

Failures indicate:
- Users won't get value from first interaction
- Immediate churn risk
- Revenue loss from failed conversions
- Damaged brand reputation

## Integration Points

This suite validates integration with:
- `UserExecutionContext` - User isolation factory
- `ExecutionEngine` - Agent processing pipeline
- `WebSocketNotifier` - Event generation
- `UnifiedWebSocketManager` - Real-time communication
- `AgentRegistry` - Agent instantiation with context
- `EnhancedToolExecutionEngine` - Tool execution with notifications

## Related Documentation

- **Specification**: `SPEC/first_message_experience.xml`
- **Architecture**: `USER_CONTEXT_ARCHITECTURE.md`
- **Agent Patterns**: `docs/GOLDEN_AGENT_INDEX.md`
- **WebSocket Events**: `SPEC/learnings/websocket_agent_integration_critical.xml`
- **Test Architecture**: `tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md`

## Monitoring & Alerts

In production, monitor:
- First message success rate
- Response time percentiles (P50, P95, P99)
- WebSocket event delivery rate
- User isolation violations
- Error message quality

## Development Guidelines

When modifying first message flow:
1. **ALWAYS** run this test suite first
2. **NEVER** remove or bypass WebSocket events
3. **MAINTAIN** user isolation via factory patterns
4. **PRESERVE** business value delivery
5. **TEST** with real services (Docker, LLM, databases)

## Contact

For issues or improvements:
- Create issue with `first-message` label
- Tag `@platform-team` for urgent issues
- Reference this test suite in PRs affecting user experience