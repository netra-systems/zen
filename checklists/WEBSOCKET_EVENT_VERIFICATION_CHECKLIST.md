# WebSocket Event Verification Checklist

## Critical WebSocket Events (MUST ALL WORK)

These 5 events are MANDATORY for chat business value:

### 1. agent_started
- [ ] Sent when agent begins processing
- [ ] Contains: agent_id, user_id, timestamp, agent_type
- [ ] User sees: "Agent is starting..."
- [ ] Timing: Within 100ms of agent invocation

### 2. agent_thinking  
- [ ] Sent during agent reasoning
- [ ] Contains: agent_id, thinking_content, step_number
- [ ] User sees: Real-time reasoning steps
- [ ] Timing: Every 1-2 seconds during processing

### 3. tool_executing
- [ ] Sent before tool execution
- [ ] Contains: tool_name, tool_args, execution_id
- [ ] User sees: "Executing [tool_name]..."
- [ ] Timing: Immediately before tool call

### 4. tool_completed
- [ ] Sent after tool execution
- [ ] Contains: tool_name, result_summary, execution_id
- [ ] User sees: Tool results
- [ ] Timing: Immediately after tool returns

### 5. agent_completed
- [ ] Sent when agent finishes
- [ ] Contains: agent_id, final_response, execution_time
- [ ] User sees: Complete response
- [ ] Timing: At end of agent execution

## Integration Points to Verify

### AgentWebSocketBridge
- [ ] Instance created successfully
  ```python
  bridge = AgentWebSocketBridge.get_instance()
  status = await bridge.get_status()
  assert status['state'] == 'ACTIVE'
  ```
- [ ] Integration initialized
  ```python
  await bridge.ensure_integration()
  ```
- [ ] Health monitoring active
  ```python
  assert bridge._health_monitor_task and not bridge._health_monitor_task.done()
  ```

### AgentRegistry
- [ ] WebSocket manager set
  ```python
  from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
  registry = AgentRegistry()
  assert registry._websocket_manager is not None
  ```
- [ ] Tool dispatcher enhanced
  ```python
  assert hasattr(registry._tool_dispatcher, 'notify_tool_execution')
  ```

### ExecutionEngine
- [ ] WebSocketNotifier present
  ```python
  # In execution engine
  assert self.websocket_notifier is not None
  ```
- [ ] User context available
  ```python
  assert self.user_context and self.user_context.user_id
  ```

### WebSocketManager
- [ ] Connections tracked per user
  ```python
  manager = WebSocketManager()
  connections = manager.get_user_connections(user_id)
  assert len(connections) > 0
  ```
- [ ] Broadcasting scoped to user
  ```python
  # Should only send to specific user
  await manager.send_to_user(user_id, message)
  ```

## Testing Procedures

### 1. Unit Test Verification
```bash
# Run WebSocket-specific tests
python -m pytest netra_backend/tests/websocket/ -v
python -m pytest tests/e2e/test_websocket_events.py -v
```

### 2. Mission Critical Test
```bash
# This is THE test for WebSocket events
python tests/mission_critical/test_websocket_agent_events_suite.py
```
Expected output:
- All 5 events detected
- Correct order maintained
- No missing events

### 3. Manual E2E Verification
1. Start all services:
   ```bash
   python tests/unified_test_runner.py --real-services --keep-alive
   ```
2. Open frontend: http://localhost:3000
3. Login with test account
4. Send message: "Analyze this data"
5. Verify in browser console:
   ```javascript
   // Should see WebSocket events
   ws.onmessage = (event) => console.log('WS Event:', JSON.parse(event.data))
   ```

### 4. Multi-User Isolation Test
1. Open two browser sessions (incognito + normal)
2. Login as different users
3. Send messages simultaneously
4. Verify:
   - [ ] User A doesn't see User B's events
   - [ ] User B doesn't see User A's events
   - [ ] Both users get their own events

## Common Issues and Fixes

### Issue: No WebSocket Events
**Check**:
```python
# In agent execution
bridge = AgentWebSocketBridge.get_instance()
print(await bridge.get_status())
```
**Fix**: 
```python
await bridge.ensure_integration(force_reinit=True)
```

### Issue: Events Out of Order
**Check**: Event timestamps and sequence
```bash
grep "WebSocket event" logs/backend.log | grep user_id
```
**Fix**: Ensure synchronous event sending in critical paths

### Issue: Missing tool_executing/tool_completed
**Check**: EnhancedToolExecutionEngine wrapper
```python
# Should wrap tool execution
assert 'EnhancedToolExecutionEngine' in str(type(engine))
```
**Fix**: Verify AgentRegistry.set_websocket_manager() called

### Issue: Events Sent to Wrong User
**Check**: User context in execution
```python
print(f"User context: {execution_context.user_id}")
print(f"WebSocket target: {websocket_message['user_id']}")
```
**Fix**: Ensure user_id properly propagated through context

## Performance Requirements

- [ ] Event latency < 100ms
- [ ] No event drops under load (10+ concurrent users)
- [ ] Memory usage stable (no event queue growth)
- [ ] Reconnection handled gracefully
- [ ] Fallback execution works without WebSocket

## WebSocket Connection Lifecycle

### Connection Establishment
1. [ ] Client connects with auth token
2. [ ] Server validates JWT
3. [ ] Connection registered for user_id
4. [ ] Heartbeat initiated

### During Agent Execution
1. [ ] agent_started sent immediately
2. [ ] agent_thinking sent periodically
3. [ ] tool_executing before each tool
4. [ ] tool_completed after each tool
5. [ ] agent_completed at end

### Connection Loss Handling
1. [ ] Events queued during disconnection
2. [ ] Client auto-reconnects
3. [ ] Queued events delivered on reconnection
4. [ ] No duplicate events sent

## Monitoring and Alerting

### Metrics to Track
- [ ] WebSocket connections per user
- [ ] Events sent per minute
- [ ] Event delivery success rate
- [ ] Average event latency
- [ ] Failed event sends

### Alert Conditions
- [ ] No events sent for 60 seconds during agent execution
- [ ] Event delivery failure rate > 1%
- [ ] WebSocket connection pool exhausted
- [ ] Memory growth in event queues

## Validation Commands

### Quick Check
```bash
# Check if WebSocket events are working
curl -X POST http://localhost:8000/api/agents/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"agent_type": "data_analyst", "message": "test"}'
# Should see events in logs
```

### Full Validation
```bash
# Run complete WebSocket test suite
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/e2e/test_websocket_multi_user.py
python tests/e2e/test_agent_websocket_integration.py
```

### Production Monitoring
```bash
# Check WebSocket events in production logs
gcloud logging read "resource.type=cloud_run_revision AND WebSocket event" --limit 50
```

## Critical Files

These files MUST be correct for WebSocket events to work:

1. `netra_backend/app/services/agent_websocket_bridge.py` - Bridge orchestration
2. `netra_backend/app/websocket/connection_manager.py` - Connection management
3. `netra_backend/app/agents/supervisor/agent_registry.py` - Agent registration
4. `netra_backend/app/websocket_core/agent_handler.py` - Event handling
5. `frontend/src/providers/WebSocketProvider.tsx` - Client connection
6. `tests/mission_critical/test_websocket_agent_events_suite.py` - Validation test

## Sign-off Checklist

Before marking WebSocket as working:
- [ ] All 5 critical events firing
- [ ] Multi-user isolation verified
- [ ] Performance requirements met
- [ ] Mission critical test passing
- [ ] No errors in logs
- [ ] Frontend receiving and displaying events

Verified by: _______________
Date/Time: _______________
Environment: _______________