# WebSocket Event Audit Report

## Executive Summary
An audit of the backend WebSocket event emission reveals multiple inconsistent payload structures for the same event types. This causes the frontend to fail to display agent messages properly.

## Critical Findings

### 1. `agent_thinking` Event Inconsistencies

The backend has **THREE different implementations** sending different payload structures:

#### Implementation A: WebSocketEventEmitter (websocket_event_emitter.py)
```python
# Sends reasoning in nested payload
event_data = {
    "agent_name": agent_name,
    "payload": {
        "reasoning": reasoning,  # <-- Nested in payload.reasoning
        "step_number": step_number,
        "progress_percentage": progress_percentage,
        "status": "thinking"
    }
}
```

#### Implementation B: UserWebSocketEmitter (user_websocket_emitter.py)
```python
# Sends thought in payload with message at root
event = {
    "type": "agent_thinking",
    "run_id": self.run_id,
    "thread_id": self.thread_id,
    "agent_name": agent_name,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "payload": {
        "thought": thought,  # <-- Different field name: "thought" vs "reasoning"
        "step": step,
        "message": f"{agent_name} is analyzing: {thought[:100]}..."  # Message in payload
    }
}
```

#### Implementation C: IsolatedEventEmitter (isolated_event_emitter.py)
```python
# Sends message at root level
await self._emit_event(
    event_type="agent_thinking", 
    data={
        "agent_name": agent_name,
        "message": message  # <-- Message at root level, not in payload
    }
)
```

### 2. `agent_started` Event Inconsistencies

Similar inconsistencies exist for agent_started events:

#### WebSocketEventEmitter
- Sends minimal data with status in payload

#### UserWebSocketEmitter  
- Sends comprehensive payload with message field

### 3. `agent_completed` Event Inconsistencies

#### WebSocketEventEmitter
- Sends result data with execution_time_ms

#### UserWebSocketEmitter
- Sends result with success flag and message

## Impact

These inconsistencies cause:
1. **Frontend fails to display agent messages** - The frontend mapper expects different fields than what backend sends
2. **Lost reasoning information** - Agent thinking messages show generic "Processing..." instead of actual reasoning
3. **Inconsistent user experience** - Different code paths send different event structures

## Root Causes

1. **Multiple parallel implementations** - Three different WebSocket emitter classes with no shared interface
2. **No event schema validation** - Events are sent as raw dictionaries without type checking
3. **Incomplete migration** - The system appears to be mid-migration from singleton to per-user emitters

## Recommendations

### Immediate Fix (Frontend Compatibility)
Update the frontend `event-payload-mapper.ts` to handle ALL backend variations (already completed).

### Short-term Backend Fixes

1. **Standardize field names**:
   - Use `message` consistently for user-facing text
   - Use `reasoning` or `thought` consistently (pick one)
   - Always nest detailed data in `payload`

2. **Update all emitters to use same structure**:
```python
# Proposed standard structure
{
    "type": "agent_thinking",
    "run_id": run_id,
    "thread_id": thread_id,
    "agent_name": agent_name,
    "message": user_facing_message,  # Always at root for consistency
    "timestamp": timestamp,
    "payload": {
        "reasoning": detailed_reasoning,
        "step_number": step_number,
        "progress_percentage": progress,
        "status": "thinking"
    }
}
```

### Long-term Architecture Fix

1. **Create WebSocket Event Types** - Use Pydantic models for type safety:
```python
class AgentThinkingEvent(BaseModel):
    type: Literal["agent_thinking"] = "agent_thinking"
    run_id: str
    thread_id: str
    agent_name: str
    message: str
    timestamp: datetime
    payload: AgentThinkingPayload
```

2. **Single Source of Truth** - Create one `WebSocketEventFactory` that all emitters use
3. **Validate Events** - Ensure all events match schema before sending
4. **Complete Migration** - Finish migrating from singleton to per-user emitters

## Affected Files

### Backend Files Needing Updates:
- `netra_backend/app/services/websocket_event_emitter.py`
- `netra_backend/app/services/user_websocket_emitter.py`  
- `netra_backend/app/websocket_core/isolated_event_emitter.py`
- `netra_backend/app/services/websocket_bridge_factory.py`
- `netra_backend/app/agents/supervisor/agent_instance_factory.py`

### Frontend Files Already Updated:
- `frontend/utils/event-payload-mapper.ts` ✅
- `frontend/store/websocket-agent-handlers.ts` ✅

## Testing Requirements

1. Create integration tests that verify event structure consistency
2. Add schema validation tests for all WebSocket events
3. Test with real WebSocket connections to ensure events display properly

## Business Impact

- **Current State**: Users see generic "Processing..." instead of meaningful agent updates
- **After Fix**: Users will see actual agent reasoning and detailed progress
- **Value**: Increases transparency and trust in AI agent operations

## Priority

**HIGH** - This directly impacts the core chat experience which delivers 90% of platform value according to CLAUDE.md