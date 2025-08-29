# WebSocket Messaging Guide

## Overview
This guide covers proper WebSocket message routing in the Netra platform, particularly for agent-to-client communication.

## Key Concepts

### Message Recipients
WebSocket messages can be sent to three types of recipients:

1. **Thread-based** (Preferred for agents)
   - Use `send_to_thread(thread_id, message)`
   - All users in a thread receive the message
   - Best for agent execution updates

2. **User-based**
   - Use `send_to_user(user_id, message)`
   - Only specific user receives the message
   - Used for user-specific notifications

3. **Connection-based**
   - Direct connection messaging (internal use)

### ID Types and Usage

| ID Type | Format | Usage | WebSocket Support |
|---------|--------|-------|-------------------|
| `run_id` | `run_[uuid]` | Agent execution tracking | ❌ Not a valid recipient |
| `thread_id` | `thread_[id]` | Conversation threading | ✅ Use `send_to_thread()` |
| `user_id` | Various | User identification | ✅ Use `send_to_user()` |

## Common Pitfalls

### ❌ Incorrect: Using run_id as user_id
```python
# WRONG - run_id is not a user_id
await websocket_manager.send_message(run_id, message)
await websocket_manager.send_to_user(run_id, message)
```

### ✅ Correct: Using proper routing
```python
# Prefer thread-based messaging
if context.thread_id:
    await websocket_manager.send_to_thread(context.thread_id, message)
elif context.user_id:
    await websocket_manager.send_to_user(context.user_id, message)
```

## Agent Implementation

### ExecutionContext Usage
Agents should receive and use ExecutionContext for proper message routing:

```python
class MyAgent(BaseExecutionInterface):
    async def execute_core_logic(self, context: ExecutionContext):
        # Use context for WebSocket messaging
        if context.thread_id:
            await self.send_status_update(context, "processing", "Working...")
```

### Progress Updates
For progress tracking, pass context through the call chain:

```python
async def generate_data(self, profile, run_id, stream_updates, 
                       thread_id=None, user_id=None):
    # Pass IDs to progress tracker
    await self.progress_tracker.send_update(
        run_id, status, thread_id, user_id
    )
```

## WebSocket Manager Behavior

### Connection Checking
The manager validates connections before sending:

1. Checks if recipient has active connections
2. Buffers messages if retry is enabled
3. Returns success/failure status

### Logging Levels
- **DEBUG**: Expected missing connections (e.g., run_ids)
- **WARNING**: Unexpected missing connections (real users)
- **ERROR**: Connection or send failures

## Best Practices

1. **Always validate recipient type**
   ```python
   if user_id and not user_id.startswith("run_"):
       # Valid user_id for WebSocket
   ```

2. **Handle missing context gracefully**
   ```python
   if not (thread_id or user_id):
       logger.debug("No WebSocket recipient available")
       return
   ```

3. **Prefer thread messaging for agents**
   - Threads provide better context
   - Multiple users can monitor progress
   - Consistent with conversation model

4. **Pass context through call chains**
   - Don't lose thread_id/user_id in nested calls
   - Maintain ExecutionContext integrity

## Testing WebSocket Communication

### Unit Testing
```python
async def test_websocket_routing():
    manager = WebSocketManager()
    
    # Test thread routing
    result = await manager.send_to_thread("thread_123", message)
    assert result == expected
    
    # Test user routing
    result = await manager.send_to_user("user_456", message)
    assert result == expected
```

### Integration Testing
```python
async def test_agent_websocket_integration():
    context = ExecutionContext(
        run_id="run_123",
        thread_id="thread_456",
        user_id="user_789"
    )
    
    agent = MyAgent()
    result = await agent.execute(context)
    
    # Verify WebSocket messages were sent correctly
```

## Troubleshooting

### No WebSocket messages received
1. Check thread_id/user_id in ExecutionContext
2. Verify WebSocket connection is active
3. Check logging for routing decisions

### WARNING: No connections found
- For run_ids: Expected, ignore or use DEBUG level
- For user_ids: Check if user is connected
- For thread_ids: Verify thread exists and has participants

### Message buffering
- Messages are buffered when retry=True
- Buffered messages delivered on reconnection
- Check buffer status in Redis

## Related Documentation
- [WebSocket Architecture](../SPEC/websocket_communication.xml)
- [Agent Execution Patterns](../SPEC/ai_factory_patterns.xml)
- [Testing Guide](../SPEC/test_infrastructure_architecture.xml)