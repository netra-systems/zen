# CRITICAL: WebSocket Thread Routing and Message Delivery Fix
## Multi-Agent Team Mission

**SEVERITY: CRITICAL**
**IMPACT: Complete breakdown of real-time communication, user messages not delivered**
**TIMELINE: Immediate fix required - core chat functionality broken**

## Team Composition

### 1. Thread Registry Agent
**Mission:** Fix thread_id to connection mapping
**Context:** Messages failing with "No connections found for thread thread_13679e4dcc38403a_run_1756919162904_9adf1f09"
**Deliverables:**
- Audit thread registration logic
- Fix run_id vs thread_id mismatch
- Implement thread registry persistence

### 2. WebSocket Bridge Agent
**Mission:** Repair WebSocketManager.send_message API
**Context:** AttributeError: 'WebSocketManager' object has no attribute 'send_message'
**Deliverables:**
- Fix method name mismatch (send_message vs send_to_thread)
- Ensure consistent API across all callers
- Add deprecation warnings for old methods

### 3. Message Routing Agent
**Mission:** Ensure messages reach correct user connections
**Context:** assistant_message and agent events not reaching users
**Deliverables:**
- Trace message flow from agent to WebSocket
- Fix user_id to thread_id mapping
- Implement message delivery confirmation

### 4. Connection Lifecycle Agent
**Mission:** Manage WebSocket connection state properly
**Context:** Connections lost between thread registration and message sending
**Deliverables:**
- Implement connection heartbeat
- Add reconnection logic
- Ensure clean connection cleanup

## Critical Files to Investigate

```
netra_backend/app/services/agent_websocket_bridge.py - Message routing logic
netra_backend/app/routes/websocket.py - Connection management
netra_backend/app/core/execution_tracker.py - Thread registry
netra_backend/app/agents/supervisor/agent_execution_core.py - Event emission
netra_backend/app/services/websocket_manager.py - Core WebSocket manager
```

## Diagnostic Requirements

1. **Add Comprehensive Logging:**
   ```python
   # Log at every step:
   - Thread registration: thread_id, run_id, user_id
   - Connection establishment: connection_id, user_id
   - Message routing: from_thread, to_thread, message_type
   - Delivery status: success/failure with reason
   ```

2. **Create Debug Endpoints:**
   - GET /debug/websocket/connections - List all active connections
   - GET /debug/websocket/threads - List all registered threads
   - GET /debug/websocket/mappings - Show thread-to-connection mappings

## Test Requirements

1. **Unit Tests:**
   - Test thread registration with various ID formats
   - Test message routing with multiple connections
   - Test connection cleanup on disconnect

2. **Integration Tests:**
   - Full agent execution with WebSocket delivery
   - Multi-user concurrent connections
   - Connection recovery after network interruption

3. **E2E Tests:**
   - User sends message → Agent processes → Response delivered
   - Multiple agents sending events simultaneously
   - Graceful degradation when WebSocket unavailable

## Success Criteria

- [ ] Zero "No connections found" errors in logs
- [ ] All agent events reach frontend
- [ ] Message delivery latency < 100ms
- [ ] Thread registry maintains consistency
- [ ] 100% message delivery success rate

## Coordination Protocol

1. Thread Registry Agent fixes ID mapping FIRST
2. WebSocket Bridge Agent fixes API mismatch SECOND
3. Message Routing Agent implements delivery THIRD
4. Connection Lifecycle Agent adds resilience LAST
5. All agents validate with E2E tests TOGETHER

## Critical Debugging Commands

```bash
# Monitor WebSocket connections in real-time
watch -n 1 'curl -s localhost:8000/debug/websocket/connections | jq'

# Test message delivery
python scripts/test_websocket_delivery.py --user-id test --message "ping"

# Check thread registry state
redis-cli HGETALL "thread_registry"
```

## Emergency Fallback

If WebSocket remains broken:
1. Implement polling fallback for message retrieval
2. Queue messages in Redis with TTL
3. Add REST endpoint for message history
4. Alert users of degraded real-time mode