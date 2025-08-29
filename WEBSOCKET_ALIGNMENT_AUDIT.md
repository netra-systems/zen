# WebSocket Frontend-Backend Alignment Audit Report

## Executive Summary
Comprehensive audit of WebSocket message types, handling patterns, and thread management between frontend and backend systems.

## Key Findings

### 1. Message Type Alignment Issues

#### Backend Message Types (Python)
Location: `netra_backend/app/websocket_core/types.py`
```python
class MessageType(str, Enum):
    # Connection lifecycle
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    PING = "ping"
    PONG = "pong"
    
    # User messages
    USER_MESSAGE = "user_message"
    SYSTEM_MESSAGE = "system_message"
    ERROR_MESSAGE = "error_message"
    
    # Agent communication
    START_AGENT = "start_agent"
    AGENT_RESPONSE = "agent_response"
    AGENT_PROGRESS = "agent_progress"
    AGENT_ERROR = "agent_error"
    
    # Thread/conversation
    THREAD_UPDATE = "thread_update"
    THREAD_MESSAGE = "thread_message"
    
    # Broadcasting
    BROADCAST = "broadcast"
    ROOM_MESSAGE = "room_message"
    
    # JSON-RPC (MCP compatibility)
    JSONRPC_REQUEST = "jsonrpc_request"
    JSONRPC_RESPONSE = "jsonrpc_response"
    JSONRPC_NOTIFICATION = "jsonrpc_notification"
```

#### Frontend Message Types (TypeScript)
Location: `frontend/types/shared/enums.ts`
```typescript
export enum WebSocketMessageType {
    // Different naming convention and additional types
    START_AGENT = 'start_agent',
    USER_MESSAGE = 'user_message',
    CHAT_MESSAGE = 'chat_message',  // Not in backend
    AGENT_STARTED = 'agent_started',  // Different from backend
    AGENT_COMPLETED = 'agent_completed',  // Different from backend
    AGENT_THINKING = 'agent_thinking',  // Not in backend
    TOOL_EXECUTING = 'tool_executing',  // Not in backend
    // ... many more differences
}
```

### 2. Critical Misalignments Found

#### A. Field Name Mismatch
- **Backend sends**: `data` field in messages
- **Frontend expects**: `payload` field
- **Current Fix**: Frontend transforms `data` → `payload` in `webSocketService.ts:101-103`

#### B. Message Type Nomenclature Differences
| Backend | Frontend | Impact |
|---------|----------|--------|
| `agent_response` | `agent_completed` | Agent completion events misaligned |
| `agent_progress` | `agent_update` | Progress tracking mismatch |
| N/A | `chat_message` | Frontend-only type |
| N/A | `agent_thinking` | Frontend-only type |
| `thread_update` | `thread_updated` | Subtle naming difference |

#### C. Error Message Structure
- **Backend**: Sends `type: "error"` with nested `error` object
- **Frontend**: Expects `type: "error_message"` or handles as special case
- Both systems handle differently, creating inconsistency

### 3. Thread Handling Analysis

#### Backend Thread Management
- Uses `thread_id` in connection info
- `send_to_thread()` method broadcasts to all connections in thread
- Thread context stored in `connections` dictionary

#### Frontend Thread Management
- Maintains `thread_id` in WebSocket message headers
- No direct thread broadcasting concept
- Thread state managed separately in stores

### 4. Message Sending Patterns

#### Backend → Frontend Flow
1. Backend uses `WebSocketManager.send_message()` or `send_to_user()`
2. Messages serialized with `_serialize_message_safely()`
3. Sent as JSON with mixed field names (`data` vs `payload`)
4. No consistent message envelope structure

#### Frontend → Backend Flow
1. Frontend uses `webSocketService.send()`
2. Messages follow `WebSocketMessage` interface
3. Consistent use of `type` and `payload` fields
4. Handles rate limiting and queuing

### 5. Error Handling Discrepancies

#### Backend Error Handling
```python
async def send_error(self, user_id: str, error_message: str, error_code: str = "GENERAL_ERROR"):
    error_msg = {
        "type": "error",
        "error": {
            "code": error_code,
            "message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
```

#### Frontend Error Handling
- Expects `error_message` type or special handling for `error` type
- Different error code formats and recovery mechanisms
- Token expiry handling differs significantly

### 6. Connection Lifecycle Management

#### Authentication Flow Issues
- Backend expects JWT in WebSocket subprotocol
- Frontend sends JWT via subprotocol but has fallback mechanisms
- Development mode handling inconsistent

#### Heartbeat/Ping-Pong Misalignment
- Both implement heartbeat but with different intervals
- Message types slightly different (`heartbeat` vs `ping`)
- Acknowledgment patterns vary

## Recommendations

### Immediate Actions Required

1. **Standardize Message Structure**
   - Use consistent field names (`payload` everywhere)
   - Create shared TypeScript/Python type definitions
   - Implement message validation layer

2. **Align Message Types**
   - Create unified enum with same values in both systems
   - Remove duplicate/unused message types
   - Document each message type's purpose

3. **Fix Error Handling**
   - Standardize error message format
   - Implement consistent error codes
   - Align recovery mechanisms

4. **Thread Management**
   - Implement consistent thread broadcasting
   - Standardize thread context handling
   - Fix thread_id propagation

### Long-term Improvements

1. **Protocol Definition**
   - Create OpenAPI/AsyncAPI specification for WebSocket protocol
   - Generate types from specification
   - Implement protocol versioning

2. **Testing**
   - Add end-to-end WebSocket tests
   - Create message validation tests
   - Implement protocol compliance tests

3. **Monitoring**
   - Add message type metrics
   - Track alignment failures
   - Monitor error rates by type

## Severity Assessment

- **Critical**: Field name mismatch (data/payload) - causes silent failures
- **High**: Message type misalignment - prevents proper event handling
- **Medium**: Error structure differences - impacts error recovery
- **Low**: Naming convention differences - cosmetic but confusing

## Test Coverage Gaps

1. No tests validating message structure alignment
2. Missing end-to-end WebSocket flow tests
3. No protocol compliance validation
4. Thread broadcasting not tested comprehensively

## Conclusion

The WebSocket implementation has significant alignment issues between frontend and backend that need immediate attention. The most critical issue is the field name mismatch (data vs payload) which is currently patched in the frontend but should be fixed at the source. Message type standardization and error handling alignment should be prioritized to ensure reliable real-time communication.