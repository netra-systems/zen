# Complete Agent Flow Trace: Frontend to Backend and Back

## Executive Summary
This document traces the complete flow of an agent request from frontend initiation through WebSocket connection, backend processing, and event streaming back to the frontend with every parameter and configuration detail.

## 1. Frontend Agent Request Initiation

### 1.1 User Action Trigger
**Location**: `frontend/hooks/useAgent.ts:10-18`
```typescript
const sendUserMessage = useCallback((text: string) => {
  const message = {
    type: 'user_message' as const,
    payload: {
      content: text,  // User's input text
    },
  };
  webSocket?.sendMessage(message);
}, [webSocket]);
```

**Parameters**:
- `text`: User's message content (string)
- `type`: Fixed as 'user_message' or 'start_agent'
- `payload.content`: The actual message text
- Optional: `thread_id`, `context`, `settings` for start_agent

### 1.2 WebSocket Provider Message Preparation
**Location**: `frontend/providers/WebSocketProvider.tsx:40-106`

The WebSocketProvider handles:
- Message reconciliation via `reconciliationService.processConfirmation(newMessage)`
- Thread management (creates/updates `thread_id`)
- Message persistence via `chatStatePersistence`
- Duplicate detection using `message_id`
- Message queuing (max 500 messages retained)

**Key Data Structures**:
```typescript
interface WebSocketMessage {
  type: string;
  payload: {
    content?: string;
    thread_id?: string;
    message_id?: string;
    timestamp?: number;
    result?: string;
  };
}
```

## 2. WebSocket Connection Establishment

### 2.1 Connection Setup
**Location**: `frontend/providers/WebSocketProvider.tsx:115-200`

**Connection Flow**:
1. **URL Construction**:
   - Base: `appConfig.wsUrl` or `${appConfig.apiUrl.replace(/^http/, 'ws')}/ws`
   - Secure URL via `webSocketService.getSecureUrl(baseWsUrl)`
   - Auth via JWT in subprotocol or header

2. **Connection Parameters**:
   ```typescript
   {
     token: currentToken || undefined,
     refreshToken: async () => unifiedAuthService.getWebSocketAuthConfig().refreshToken(),
     onOpen: () => connectionStateRef.current = 'connected',
     onError: (error) => handleAuthError(error),
     heartbeat_interval: 30-45 seconds (env-dependent),
     max_message_size: 8192 bytes
   }
   ```

### 2.2 Authentication
**Backend Location**: `netra_backend/app/routes/websocket.py:153-280`

**Authentication Methods**:
1. **Subprotocol**: `Sec-WebSocket-Protocol: jwt.<base64url_encoded_token>`
2. **Authorization Header**: `Bearer <jwt_token>`

**Process**:
1. Accept WebSocket with subprotocol if available (line 157-168)
2. Authenticate via `secure_websocket_context` (line 283)
3. Register connection with manager (line 301)
4. Start heartbeat monitoring (line 310-314)

## 3. Backend WebSocket Message Routing

### 3.1 Message Reception and Routing
**Location**: `netra_backend/app/routes/websocket.py:438-581`

**Message Flow**:
1. **Receive**: `raw_message = await websocket.receive_text()` (line 473-476)
2. **Validate Size**: Max 8192 bytes (line 482-487)
3. **Parse JSON**: `message_data = json.loads(raw_message)` (line 491)
4. **Route**: `await message_router.route_message(user_id, websocket, message_data)` (line 506)

### 3.2 Agent Handler Registration
**Location**: `netra_backend/app/routes/websocket.py:179-279`

**Handler Setup**:
```python
# Create handler with dependencies
message_handler_service = MessageHandlerService(supervisor, thread_service, ws_manager)
agent_handler = AgentMessageHandler(message_handler_service, websocket)

# Register with router
message_router.add_handler(agent_handler)
```

## 4. Agent Message Processing

### 4.1 AgentMessageHandler Processing
**Location**: `netra_backend/app/websocket_core/agent_handler.py:50-198`

**Key Steps**:
1. **Thread Association Update** (lines 54-68):
   ```python
   if thread_id:
       ws_manager.update_connection_thread(connection_id, thread_id)
   ```

2. **Database Session Management** (lines 71-90):
   ```python
   async for db_session in get_request_scoped_db_session():
       success = await self._route_agent_message(user_id, message, db_session)
   ```

3. **Message Type Routing** (lines 104-110):
   - `START_AGENT` → `_handle_start_agent()`
   - `USER_MESSAGE`/`CHAT` → `_handle_user_message()`

### 4.2 MessageHandlerService Processing
**Location**: `netra_backend/app/services/message_handlers.py:88-306`

**Processing Flow for start_agent**:
1. **Thread Management** (lines 96-110):
   - Get/create thread
   - Update WebSocket connection-thread mapping
   
2. **Agent Request Processing** (lines 143-177):
   ```python
   # Create user message
   await self._create_user_message(thread, user_request, user_id, db_session)
   
   # Create run
   run = await self._create_run(thread, db_session)
   
   # Configure supervisor with WebSocket manager
   self._configure_supervisor(user_id, thread, db_session)
   if self.websocket_manager:
       self.supervisor.agent_registry.set_websocket_manager(self.websocket_manager)
   
   # Execute supervisor
   response = await self._execute_supervisor(user_request, thread, user_id, run, db_session)
   ```

3. **Run-Thread Mapping Registration** (lines 217-246):
   ```python
   bridge = await get_agent_websocket_bridge()
   await bridge.register_run_thread_mapping(
       run_id=run.id,
       thread_id=thread.id,
       metadata={"user_id": user_id, "user_request": user_request[:100]}
   )
   ```

## 5. SupervisorAgent Execution

### 5.1 UserExecutionContext Pattern
**Location**: `netra_backend/app/agents/supervisor_consolidated.py:122-200`

**Execution with Complete Isolation**:
```python
async def execute(self, context: UserExecutionContext, stream_updates: bool = False):
    # Validate context
    context = validate_user_context(context)
    
    # Create isolated WebSocket emitter
    websocket_emitter = IsolatedWebSocketEventEmitter.create_for_user(
        user_id=context.user_id,
        thread_id=context.thread_id,
        run_id=context.run_id,
        websocket_manager=self.websocket_bridge.websocket_manager
    )
    
    # Create isolated tool system
    tool_system = await UserContextToolFactory.create_user_tool_system(
        context=context,
        tool_classes=tool_classes,
        websocket_bridge_factory=websocket_bridge_factory
    )
    
    # Store isolated components
    self.tool_dispatcher = tool_system['dispatcher']
    self.user_tool_registry = tool_system['registry']
```

### 5.2 WebSocket Event Emission Points
**Critical Events** (as per `netra_backend/app/websocket_core/agent_handler.py`):

1. **agent_started**: When agent begins processing
2. **agent_thinking**: Real-time reasoning visibility
3. **tool_executing**: Tool usage transparency
4. **tool_completed**: Tool results display
5. **agent_completed**: Final response ready

## 6. Tool Execution and Events

### 6.1 Tool Dispatcher Architecture
**Location**: `netra_backend/app/agents/tool_dispatcher.py`

**Request-Scoped Tool Dispatcher Creation**:
```python
def create_request_scoped_tool_dispatcher(
    user_context: UserExecutionContext,
    websocket_manager: Optional[WebSocketManager] = None,
    tools: Optional[List[BaseTool]] = None
) -> UnifiedToolDispatcher:
    return UnifiedToolDispatcherFactory.create_for_request(
        user_context=user_context,
        websocket_manager=websocket_manager,
        tools=tools
    )
```

**Features**:
- Per-request isolation (no shared state)
- WebSocket events for ALL tool executions
- Clean separation: Registry, Execution, Events, Permissions

## 7. WebSocket Events Back to Frontend

### 7.1 Backend Event Emission
**Location**: `netra_backend/app/websocket_core/unified_manager.py:112-127`

```python
async def emit_critical_event(self, user_id: str, event_type: str, data: Dict[str, Any]):
    message = {
        "type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await self.send_to_user(user_id, message)
```

### 7.2 Frontend Event Reception
**Location**: `frontend/services/webSocketService.ts:117-186`

**Message Type Validation**:
```typescript
// Agent message types
const agentTypes = [
  'agent_started', 'tool_executing', 'agent_thinking', 
  'partial_result', 'agent_completed', 'agent_response', 
  'agent_progress', 'agent_error'
];

// Backend to frontend field mapping
if (!obj.payload && obj.data) {
  obj.payload = obj.data;  // Convert backend 'data' to frontend 'payload'
}
```

### 7.3 WebSocket Provider Event Processing
**Location**: `frontend/providers/WebSocketProvider.tsx:41-105`

**Event Processing Flow**:
1. **Message Reception**: Via WebSocket `onmessage` handler
2. **Reconciliation**: `reconciliationService.processConfirmation(newMessage)`
3. **Thread Updates**: Update `currentThreadIdRef` for thread events
4. **State Updates**: Update React state via `setMessages()`
5. **Persistence**: Save to `chatStatePersistence` for user/assistant messages

## 8. Complete Parameter Flow Summary

### Request Flow Parameters:
```
Frontend → Backend:
{
  type: "user_message" | "start_agent",
  payload: {
    content: string,
    thread_id?: string,
    context?: object,
    settings?: object,
    references?: array
  }
}

Backend Processing:
- user_id: From JWT auth
- thread_id: Created/validated
- run_id: Generated for execution
- db_session: Request-scoped AsyncSession
- websocket: Active WebSocket instance
- connection_id: Unique connection identifier

Backend → Frontend Events:
{
  type: "agent_started" | "agent_thinking" | "tool_executing" | etc,
  data/payload: {
    agent_name?: string,
    thought?: string,
    tool_name?: string,
    tool_args?: object,
    result?: any,
    error?: string,
    thread_id: string,
    message_id?: string,
    timestamp: ISO string
  }
}
```

### Configuration Parameters:

**WebSocket Configuration**:
- `heartbeat_interval`: 25-45 seconds (env-dependent)
- `connection_timeout`: 300-900 seconds
- `max_message_size`: 8192 bytes
- `max_message_rate`: 30-1000 msg/min (env-dependent)
- `max_connections_per_user`: 3

**Execution Configuration**:
- `MAX_CONCURRENT_AGENTS`: 10
- `AGENT_EXECUTION_TIMEOUT`: 30 seconds
- `MAX_HISTORY_SIZE`: 100 messages
- Message retention: 500 messages (frontend)

## 9. Critical Integration Points

### 9.1 Thread Association
The thread_id is critical for routing WebSocket events back to the correct user connection. It's established at multiple points:
1. Frontend sends thread_id in message
2. AgentMessageHandler updates connection-thread mapping
3. MessageHandlerService confirms association before processing
4. SupervisorAgent maintains association through execution

### 9.2 WebSocket Manager Propagation
The WebSocketManager must be passed through the entire chain:
1. Set on MessageHandlerService constructor
2. Passed to SupervisorAgent via agent_registry
3. Used by AgentInstanceFactory for sub-agents
4. Available to ToolDispatcher for tool events

### 9.3 Database Session Lifecycle
Each request gets its own AsyncSession:
- Created via `get_request_scoped_db_session()`
- Passed through UserExecutionContext
- Auto-closed after request completion
- Never shared between requests

## Conclusion

The agent flow implements complete user isolation through:
- Request-scoped database sessions
- Per-user WebSocket emitters
- Isolated tool dispatchers
- Thread-based event routing
- Factory-enforced component creation

This architecture supports concurrent multi-user execution with zero context leakage and real-time event streaming.