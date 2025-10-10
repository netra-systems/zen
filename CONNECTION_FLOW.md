# WebSocket Connection Flow

## Overview
This document describes the linear, gated connection flow for the WebSocket CLI client. The connection process ensures both handshake completion and `connection_established` event receipt before allowing message transmission.

## Connection Flow Diagram

```mermaid
sequenceDiagram
    participant CLI as CLI Client
    participant Server as Backend Server
    participant Listener as Event Listener (Background)

    Note over CLI,Server: Phase 1: WebSocket Connection
    CLI->>Server: Connect WebSocket (auth via subprotocol/query/header)
    Server-->>CLI: WebSocket Connected

    Note over CLI,Server: Phase 2: Handshake
    CLI->>CLI: Wait for handshake from server
    Server->>CLI: handshake_response (with thread_id)
    CLI->>Server: handshake_acknowledged
    Server->>CLI: handshake_complete
    CLI->>CLI: Set connected = True

    Note over CLI,Listener: Phase 3: Start Event Listener
    CLI->>Listener: asyncio.create_task(receive_events())
    Listener->>Server: Start listening for events

    Note over CLI,Server: Phase 4: Connection Establishment
    Server->>Listener: connection_established event
    Listener->>CLI: Set connection_established_received = True

    Note over CLI: Phase 5: Ready Gate
    loop Wait for connection_established (max 5 seconds)
        CLI->>CLI: Check connection_established_received
        alt Event received
            CLI->>CLI: Set ready_to_send_events = True
            Note over CLI: ✅ Ready to send messages
        else Timeout
            CLI->>CLI: Log warning, continue anyway
        end
    end

    Note over CLI,Server: Phase 6: Normal Operation
    CLI->>Server: Send user messages (only if ready_to_send_events = True)
    Server->>Listener: Stream events
    Listener->>CLI: Process and display events
```

## Flow States

### 1. Initial State
- `connected`: False
- `connection_established_received`: False
- `ready_to_send_events`: False

### 2. After Handshake
- `connected`: True ✅
- `connection_established_received`: False
- `ready_to_send_events`: False

### 3. After connection_established
- `connected`: True ✅
- `connection_established_received`: True ✅
- `ready_to_send_events`: True ✅

## Key Implementation Details

### Linear Flow in `connect()` Method
```python
# Step 1: Perform handshake
handshake_success = await self._perform_handshake()
if handshake_success:
    self.connected = True

    # Step 2: Start event listener immediately
    asyncio.create_task(self.receive_events())

    # Step 3: Wait for connection_established
    timeout = 5.0
    while not self.connection_established_received:
        if timeout_exceeded:
            break
        await asyncio.sleep(0.1)

    # Step 4: Set ready flag
    if self.connection_established_received:
        self.ready_to_send_events = True
```

### Event Listener (`receive_events()`)
- Runs continuously in background after handshake
- Captures `connection_established` event when sent by server
- Sets `connection_established_received = True` flag

### Message Sending Gate
Before sending any message, the CLI checks:
```python
if not self.ready_to_send_events:
    # Wait for connection_established event
    # Or timeout and raise error
```

## Benefits of This Approach

1. **Linear & Simple**: Clear sequential flow without complex branching
2. **No Race Conditions**: Event listener starts before server sends `connection_established`
3. **Gated Access**: Messages can only be sent after full establishment
4. **Timeout Protection**: 5-second timeout prevents indefinite waiting
5. **Clean State Management**: Three boolean flags with clear progression

## Server Requirements

The backend server must:
1. Send `handshake_response` during HANDSHAKING phase
2. Send `connection_established` event after handshake completion
3. Only process user messages after both events are acknowledged

## Error Handling

- If handshake fails: Connection aborts
- If `connection_established` times out: Warning logged, continues with degraded state
- If WebSocket disconnects: All flags reset, must reconnect from beginning