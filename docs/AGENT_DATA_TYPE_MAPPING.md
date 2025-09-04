# Agent Data Type Mapping Document

## Problem Statement
The frontend is showing "agent-undefined" and "unknown" for agent names because of a data structure mismatch between backend WebSocket events and frontend payload mappers.

## Backend WebSocket Event Structure

### Agent Events (from `netra_backend/app/services/websocket_event_emitter.py`)

```python
# Agent Started Event
{
    "type": "agent_started",
    "run_id": "thread_xxx_run_xxx",
    "timestamp": "2025-09-04T01:19:41.137752+00:00",
    "thread_id": "thread_xxx",
    "agent_name": "triage",  # ← CRITICAL: At top level, NOT in payload
    "payload": {
        "status": "started",
        "context": {...},
        "message": "triage has started processing your request"
    }
}

# Agent Thinking Event
{
    "type": "agent_thinking",
    "run_id": "thread_xxx_run_xxx", 
    "timestamp": "2025-09-04T01:19:41.137752+00:00",
    "thread_id": "thread_xxx",
    "agent_name": "data",  # ← At top level
    "payload": {
        "reasoning": "Finalizing triage results...",
        "step_number": null,
        "progress_percentage": null,
        "status": "thinking"
    }
}

# Agent Completed Event
{
    "type": "agent_completed",
    "run_id": "thread_xxx_run_xxx",
    "timestamp": "2025-09-04T01:19:41.137752+00:00", 
    "thread_id": "thread_xxx",
    "agent_name": "optimizer",  # ← At top level
    "payload": {
        "status": "completed",
        "result": {...},
        "execution_time_ms": 1234,
        "message": "optimizer has completed processing your request"
    }
}

# Tool Executing Event
{
    "type": "tool_executing",
    "run_id": "thread_xxx_run_xxx",
    "timestamp": "2025-09-04T01:19:41.137752+00:00",
    "thread_id": "thread_xxx", 
    "agent_name": "data",  # ← At top level
    "payload": {
        "tool_name": "analyze_metrics",
        "parameters": {...},
        "status": "executing",
        "message": "data is using analyze_metrics"
    }
}

# Tool Completed Event
{
    "type": "tool_completed",
    "run_id": "thread_xxx_run_xxx",
    "timestamp": "2025-09-04T01:19:41.137752+00:00",
    "thread_id": "thread_xxx",
    "agent_name": "data",  # ← At top level
    "payload": {
        "tool_name": "analyze_metrics",
        "result": {...},
        "execution_time_ms": 500,
        "status": "completed",
        "message": "data completed analyze_metrics"
    }
}
```

## Frontend Current Implementation Issues

### Problem in `frontend/utils/event-payload-mapper.ts`

The mappers are receiving only the `payload` portion of the event, but trying to access `agent_name` which is at the top level:

```typescript
// CURRENT BROKEN CODE
export const mapAgentStartedPayload = (backendPayload: any) => {
  return {
    agent_id: backendPayload.agent_name || backendPayload.agent_id,  // ← This is undefined!
    agent_type: backendPayload.agent_name || backendPayload.agent_type,  // ← This is undefined!
    // backendPayload here is just the payload, not the full event
  };
};
```

### Problem in `frontend/store/websocket-agent-handlers.ts`

```typescript
// The handler passes only event.payload, losing agent_name
export const extractAgentStartedData = (payload: any) => {
  const mappedPayload = mapEventPayload('agent_started', payload); // ← Only payload, no agent_name!
  const agentId = mappedPayload.agent_id || `agent-${mappedPayload.run_id}` || 'unknown';
  // Results in "agent-undefined" or "unknown"
};
```

## Required Fixes

### Fix 1: Update Event Payload Mappers
The mappers need to receive the full event, not just the payload:

```typescript
// FIXED CODE
export const mapAgentStartedPayload = (fullEvent: any) => {
  return {
    agent_id: fullEvent.agent_name || fullEvent.payload?.agent_id || 'unknown',
    agent_type: fullEvent.agent_name || fullEvent.payload?.agent_type || 'unknown',
    run_id: fullEvent.run_id,
    timestamp: fullEvent.timestamp,
    status: fullEvent.payload?.status || 'started',
    message: fullEvent.payload?.message || `Agent ${fullEvent.agent_name || 'Unknown'} started`
  };
};
```

### Fix 2: Update Handler to Pass Full Event
```typescript
export const extractAgentStartedData = (event: any) => {
  const mappedPayload = mapEventPayload('agent_started', event); // Pass full event
  const agentId = mappedPayload.agent_id || 'unknown';
  const timestamp = mappedPayload.timestamp ? parseTimestamp(mappedPayload.timestamp) : Date.now();
  const runId = mappedPayload.run_id || generateUniqueId('run');
  return { agentId, timestamp, runId };
};
```

## Agent Type Naming Conventions

### Backend Agent Names (from execution)
- `triage` - Triage agent
- `data` - Data analysis agent  
- `optimizer` - Optimization agent
- `supply_research` - Supply research agent
- `action_plan` - Action planning agent
- `report` - Report generation agent

### Frontend Display Names
Should be properly formatted versions of the backend names:
- `triage` → "Triage Agent"
- `data` → "Data Analysis"
- `optimizer` → "Optimizer"
- `supply_research` → "Supply Research"
- `action_plan` → "Action Plan"
- `report` → "Report Generator"

## Summary of Data Flow

1. **Backend sends**: Full event with `agent_name` at top level + `payload` nested
2. **Frontend receives**: Full event structure via WebSocket
3. **Frontend routes**: Event to appropriate handler based on `event.type`
4. **Handler extracts**: Currently passes only `event.payload` to mapper (BROKEN)
5. **Mapper transforms**: Tries to access `agent_name` from payload (FAILS)
6. **UI displays**: "agent-undefined" or "unknown" due to missing data

## Implementation Priority

1. **CRITICAL**: Fix the payload mappers to handle full event structure
2. **CRITICAL**: Update handlers to pass full event to mappers
3. **IMPORTANT**: Add proper type definitions for WebSocket events
4. **NICE TO HAVE**: Create display name formatting utilities