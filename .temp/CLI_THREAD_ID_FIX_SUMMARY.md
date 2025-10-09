# CLI Thread ID Acknowledgment Fix

## Problem
The CLI was incorrectly acknowledging WebSocket connections with the wrong thread ID. When the backend sent a `handshake_response` with its thread ID (e.g., `thread_cli_25_e1cf9405`), the CLI was instead acknowledging with a connection ID (e.g., `ws_conn_100bdd8f3a44fc72_1760038639328_20_4c253ab0`).

## Root Cause
The issue was in the `_process_any_handshake_response` method in `scripts/agent_cli.py`. The method was incorrectly treating `connection_established` events as handshake responses and sending `session_acknowledged` messages for them with the wrong ID.

## The Fix
Modified the `connection_established` handler in `_process_any_handshake_response` (scripts/agent_cli.py:3102-3125) to:
1. **NOT** treat `connection_established` as a handshake response
2. **NOT** send `session_acknowledged` for this event
3. Return `False` to indicate it's still waiting for the actual `handshake_response`

### Before (Incorrect)
```python
elif response_type == 'connection_established':
    # Extract connection_id and use it as thread_id (WRONG!)
    connection_id = connection_data.get('connection_id')
    self.current_thread_id = connection_id

    # Send acknowledgment with connection_id (WRONG!)
    ack_message = {
        "type": "session_acknowledged",
        "thread_id": connection_id,  # Using wrong ID!
    }
    await self.ws.send(json.dumps(ack_message))
    return True
```

### After (Correct)
```python
elif response_type == 'connection_established':
    # connection_established is NOT a handshake response!
    # Just log it and keep waiting for handshake_response
    self.debug.debug_print(
        "Received connection_established - waiting for handshake_response",
        DebugLevel.VERBOSE,
        style="yellow"
    )

    # DO NOT send session_acknowledged here!
    return False  # Still waiting for handshake_response
```

## How It Works Now
1. Backend sends `connection_established` → CLI logs it but does NOT acknowledge
2. CLI sends `handshake_request`
3. Backend sends `handshake_response` with `thread_id: "thread_cli_25_e1cf9405"`
4. CLI extracts the backend's thread_id and sends `session_acknowledged` with the SAME thread_id
5. Both sides now agree on the thread_id for proper event routing

## Testing
Created `test_thread_id_fix.py` to verify the fix:
- Simulates a backend that sends both `connection_established` and `handshake_response`
- Verifies the CLI only acknowledges the `handshake_response` with the correct thread_id
- Fails if CLI uses the connection_id instead

## Impact
This fix ensures:
- ✅ CLI always uses the backend-provided thread_id
- ✅ Events are properly routed with the correct thread_id
- ✅ No more mismatched thread IDs causing agent execution failures
- ✅ The handshake protocol works as designed