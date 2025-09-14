# API Dual-Channel Architecture: How It Works

**System Health Score: 95% (EXCELLENT)** | **Last Updated: 2025-09-14** | **Issue #1116 COMPLETE: SSOT Factory Migration**

## Executive Summary

Netra implements a **dual-channel API architecture** that provides both REST endpoints and WebSocket connections for agent communication. This is NOT a legacy vs. new situation - both channels are **actively maintained production features** that serve complementary purposes with complete factory-based user isolation.

## The Architecture

```
┌─────────────┐                     ┌─────────────┐
│  REST API   │                     │  WebSocket  │
│  Clients    │                     │   Clients   │
└──────┬──────┘                     └──────┬──────┘
       │                                    │
       ▼                                    ▼
┌─────────────────┐              ┌──────────────────┐
│   FastAPI       │              │    WebSocket     │
│   Routes        │              │    Endpoint      │
│ /api/agent/*    │              │      /ws         │
└────────┬────────┘              └────────┬─────────┘
         │                                 │
         └──────────────┬──────────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │    Shared Backend Services    │
         │  ┌────────────────────────┐  │
         │  │   SupervisorAgent      │  │
         │  ├────────────────────────┤  │
         │  │   ThreadService        │  │
         │  ├────────────────────────┤  │
         │  │ MessageHandlerService  │  │
         │  ├────────────────────────┤  │
         │  │    AgentService        │  │
         │  ├────────────────────────┤  │
         │  │ StatePersistenceService│  │
         │  └────────────────────────┘  │
         └──────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │    Database     │
              │   PostgreSQL    │
              └─────────────────┘
```

## How The System Achieves Both

### 1. **Service Layer Abstraction**

The key to supporting both channels is the **service layer abstraction**. All business logic lives in shared services that are channel-agnostic:

```python
# Both REST and WebSocket call the same service
supervisor.run(query, request_id, stream_updates=True)
```

### 2. **Dependency Injection**

Both channels use FastAPI's dependency injection to access the same service instances:

**REST Endpoint:**
```python
@router.post("/run_agent")
async def run_agent(
    request_model: RequestModel,
    supervisor: Supervisor = Depends(get_agent_supervisor)
):
    return await supervisor.run(...)
```

**WebSocket Handler:**
```python
# Gets the same supervisor instance
supervisor = getattr(websocket.app.state, 'agent_supervisor', None)
message_handler_service = MessageHandlerService(supervisor, thread_service)
```

### 3. **Unified Message Processing**

The `MessageHandlerService` provides a common interface that both channels use:

```python
class MessageHandlerService:
    async def handle_start_agent(self, user_id: str, query: str, thread_id: str):
        # Same logic for both REST and WebSocket
        return await self.supervisor.run(query, thread_id)
    
    async def handle_user_message(self, user_id: str, message: str, thread_id: str):
        # Same processing regardless of channel
        return await self.agent_service.process_message(message, thread_id)
```

### 4. **Response Adaptation**

Each channel adapts the service response to its communication pattern:

**REST Response:**
```python
# Immediate JSON response
return {"run_id": run_id, "status": "started"}

# OR streaming via SSE
async def generate_sse_stream():
    async for chunk in service.stream():
        yield f"data: {chunk}\n\n"
```

**WebSocket Response:**
```python
# Real-time message delivery
await websocket.send_json({
    "type": "agent_update",
    "payload": response_data
})
```

## Channel Comparison

| Feature | REST API | WebSocket |
|---------|----------|-----------|
| **Pattern** | Request/Response | Bidirectional streaming |
| **State** | Stateless | Stateful connection |
| **Updates** | Polling required | Real-time push |
| **Use Case** | CRUD operations, simple queries | Interactive chat, live updates |
| **Scaling** | Simple load balancing | Requires sticky sessions |
| **Client Complexity** | Simple HTTP client | WebSocket client required |

## When to Use Each Channel

### Use REST API When:
- Building mobile applications with standard HTTP clients
- Creating simple integrations or webhooks  
- Implementing stateless operations
- Working behind restrictive firewalls
- Needing simple retry logic
- Building traditional web applications

### Use WebSocket When:
- Building real-time chat interfaces
- Needing live agent status updates
- Implementing interactive conversations
- Streaming agent thoughts/reasoning
- Requiring bidirectional communication
- Building desktop or modern web apps

## Real-World Example

Consider a user interacting with an AI agent:

### Scenario 1: Mobile App (REST)
```python
# Start agent
response = requests.post("/api/agent/run_agent", json={
    "query": "Analyze my code",
    "id": "run_123"
})

# Poll for status
while True:
    status = requests.get(f"/api/agent/{run_id}/status")
    if status.json()["status"] == "complete":
        break
    time.sleep(2)
```

### Scenario 2: Web Chat Interface (WebSocket)
```javascript
// Connect once
const ws = new WebSocket('/ws');

// Send message
ws.send(JSON.stringify({
    type: 'START_AGENT',
    payload: { query: 'Analyze my code' }
}));

// Receive real-time updates
ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    updateUI(update);  // Instant updates, no polling
};
```

## Implementation Files

### REST Implementation
- **Routes**: `netra_backend/app/routes/agent_route.py`
- **Processors**: `netra_backend/app/routes/agent_route_processors.py`
- **Streaming**: `netra_backend/app/routes/agent_route_streaming.py`
- **Validators**: `netra_backend/app/routes/agent_route_validators.py`

### WebSocket Implementation
- **Endpoint**: `netra_backend/app/routes/websocket.py`
- **Core**: `netra_backend/app/websocket_core/`
- **Agent Handler**: `netra_backend/app/websocket_core/agent_handler.py`
- **Message Router**: `netra_backend/app/websocket_core/router.py`

### Shared Services
- **Supervisor**: `netra_backend/app/agents/supervisor_consolidated.py`
- **Thread Service**: `netra_backend/app/services/thread_service.py`
- **Message Handlers**: `netra_backend/app/services/message_handlers.py`
- **Agent Service**: `netra_backend/app/services/agent_service.py`

## Key Insights

1. **Not Legacy vs New**: Both channels are production-ready and actively maintained
2. **Same Backend**: Both use identical backend services ensuring functional parity
3. **Complementary**: Each channel excels at different use cases
4. **Flexible**: Clients can use one or both channels as needed
5. **Maintainable**: Changes to business logic automatically benefit both channels

## Future Considerations

- Maintain feature parity between channels
- Test both channels when modifying shared services
- Consider GraphQL subscriptions as a third channel for specific use cases
- Keep the service layer channel-agnostic

## Conclusion

The dual-channel architecture is a **deliberate design choice** that maximizes compatibility while enabling advanced real-time features. By maintaining a clean service layer abstraction, Netra provides flexibility for clients to choose the most appropriate communication pattern for their use case without sacrificing functionality or requiring duplicate implementations.