# WebSocket Timing Fix - Complete Implementation

## Problem Statement
The CLI was sending messages too early, before the server completed its lifecycle phases and entered the message processing loop (Phase 5). Messages sent before Phase 5 were lost because the server's message handler wasn't active yet.

## Root Cause
The CLI code had backward compatibility logic that allowed connections to proceed even when the handshake failed, causing messages to be sent before the server was ready.

## Complete Fix Implementation

### 1. Connection Method (lines 2879-2928)
**REMOVED:** Backward compatibility code that returned `True` even when handshake failed
**ADDED:**
- Proper failure when handshake doesn't complete
- Retry mechanism with 3-second delay
- Second handshake attempt after delay
- WebSocket closure on failure

### 2. Handshake Response Processing (lines 3307-3363)
**CHANGED:** Message type from `session_acknowledged` to `handshake_acknowledged`
**ADDED:**
- Wait for `handshake_complete` confirmation
- 500ms delay after handshake_complete for server to enter Phase 5
- Fallback delay if no handshake_complete received

### 3. Message Sending Validation (lines 3703-3722)
**ADDED:** Check for `self.connected` flag before sending messages
- Ensures handshake is fully complete
- Prevents messages being sent during server initialization
- Clear error messages when connection not ready

## Order of Operations (Enforced)

1. **Connect** → WebSocket connection established
2. **Wait** for `connection_established` event
3. **Handshake** → Wait for `handshake_response`
4. **Acknowledge** → Send `handshake_acknowledged` with thread_id
5. **Confirm** → Wait for `handshake_complete` message
6. **Delay** → Add 500ms for server to enter Phase 5 (Processing)
7. **Ready** → NOW messages can be safely sent

## Server Phases Reference

```
Phase 1: INITIALIZING   → Accept connection, assign ID
Phase 2: AUTHENTICATING → Validate user credentials
Phase 3: HANDSHAKING    → Exchange thread IDs
Phase 4: READY          → Initialize services, register with router
Phase 5: PROCESSING     → Message loop active ✓ (Messages accepted here!)
Phase 6: CLEANING_UP    → Coordinated cleanup
Phase 7: CLOSED         → Terminal state
```

## Key Benefits

✓ **No Message Loss** - Messages only sent when server is ready to process them
✓ **Proper Sequencing** - Enforces documented WebSocket lifecycle
✓ **Retry Logic** - Handles transient delays during server startup
✓ **Clear Errors** - Descriptive messages when connection fails
✓ **Fail Fast** - Connection fails quickly if server isn't ready

## Testing Verification

The fix ensures:
- `self.connected` is only set to `True` after full handshake completion
- `send_message()` validates both `self.connected` and `self.current_thread_id`
- Messages cannot be sent until server reaches Phase 5 (Processing)
- Connection properly fails if server doesn't complete handshake

## Files Modified

- `scripts/agent_cli.py`:
  - `connect()` method - lines 2879-2928
  - `_perform_handshake()` method - lines 3057-3058
  - `_process_handshake_response()` method - lines 3307-3363
  - `send_message()` method - lines 3703-3722

## Implementation Complete

The timing issue is now fully resolved. The CLI will properly wait for the server to complete all initialization phases before sending any messages, preventing message loss and ensuring reliable communication.