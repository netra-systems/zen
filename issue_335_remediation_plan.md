# Issue #335 WebSocket Race Condition Remediation Plan

## Executive Summary

Issue #335 represents a critical WebSocket race condition where messages are sent to connections that are closing or closed, resulting in "Cannot call send once a close message has been sent" errors. This impacts the $500K+ ARR Golden Path functionality by causing WebSocket event delivery failures during agent execution.

## Root Cause Analysis

**Identified Problem**: Missing `is_closing` flag validation in `unified_manager.py` send methods causes race condition between broadcast operations and connection close operations.

**Evidence**:
- 4 tests currently failing, demonstrating the race condition exists
- SPEC learnings document (`websocket_errors.xml` lines 101-173) provides the exact solution pattern
- Tests show concurrent send/close operations fail with "send after close" errors

**Pattern from SPEC** (Lines 140-147):
```python
if (not conn_info.is_closing and
    conn_info.websocket.client_state == WebSocketState.CONNECTED and
    conn_info.websocket.application_state == WebSocketState.CONNECTED):
    await conn_info.websocket.send_json(message)
```

## Technical Implementation Plan

### 1. Connection State Validation Enhancement

**Target File**: `netra_backend/app/websocket_core/unified_manager.py`

**Enhanced `send_message` method** (~line 2882):
```python
async def send_message(self, connection_id: str, message: dict) -> bool:
    try:
        connection = self.get_connection(connection_id)
        if not connection:
            logger.warning(f"send_message failed: connection {connection_id} not found")
            return False

        if not connection.websocket:
            logger.warning(f"send_message failed: connection {connection_id} has no websocket")
            return False

        # NEW: Check is_closing flag to prevent race condition
        if hasattr(connection, 'is_closing') and connection.is_closing:
            logger.debug(f"send_message prevented: connection {connection_id} is closing")
            return False

        # NEW: Check WebSocket state to prevent send after close
        if hasattr(connection.websocket, 'client_state') and \
           hasattr(connection.websocket, 'application_state'):
            from starlette.websockets import WebSocketState
            if (connection.websocket.client_state != WebSocketState.CONNECTED or
                connection.websocket.application_state != WebSocketState.CONNECTED):
                logger.debug(f"send_message prevented: WebSocket not in CONNECTED state")
                return False

        safe_message = _serialize_message_safely(message)
        await connection.websocket.send_json(safe_message)

        logger.debug(f"✅ Message sent successfully to connection {connection_id}")
        return True

    except Exception as e:
        # Treat send-after-close as expected behavior, not error
        if "close" in str(e).lower():
            logger.debug(f"Send prevented due to closed connection {connection_id}: {e}")
        else:
            logger.error(f"❌ send_message failed for connection {connection_id}: {e}")
        return False
```

**Enhanced `broadcast` method** (~line 1503):
```python
async def broadcast(self, message: Dict[str, Any]) -> None:
    safe_message = _serialize_message_safely(message)
    for connection in list(self._connections.values()):
        try:
            # NEW: Check is_closing flag before sending
            if hasattr(connection, 'is_closing') and connection.is_closing:
                logger.debug(f"Broadcast skipped for closing connection {connection.connection_id}")
                continue

            # NEW: Check WebSocket state
            if hasattr(connection.websocket, 'client_state') and \
               hasattr(connection.websocket, 'application_state'):
                from starlette.websockets import WebSocketState
                if (connection.websocket.client_state != WebSocketState.CONNECTED or
                    connection.websocket.application_state != WebSocketState.CONNECTED):
                    logger.debug(f"Broadcast skipped for non-connected WebSocket {connection.connection_id}")
                    continue

            await connection.websocket.send_json(safe_message)
        except Exception as e:
            # Treat send-after-close as expected, remove connection
            if "close" in str(e).lower():
                logger.debug(f"Broadcast failed due to closed connection, removing: {connection.connection_id}")
            else:
                logger.error(f"Failed to broadcast to {connection.connection_id}: {e}")
            await self.remove_connection(connection.connection_id)
```

### 2. Connection State Management Enhancement

**Enhanced connection removal** to set `is_closing` flag immediately:
```python
async def remove_connection(self, connection_id: str) -> bool:
    try:
        connection = self.get_connection(connection_id)
        if connection:
            # NEW: Set is_closing flag immediately
            if hasattr(connection, 'is_closing'):
                connection.is_closing = True

            # Proceed with existing removal logic
            # ... existing code ...
    except Exception as e:
        logger.error(f"Error removing connection {connection_id}: {e}")
        return False
```

### 3. Graceful Degradation Implementation

**Error Classification**:
- Send-after-close errors: Log as DEBUG (expected behavior)
- Connection not found errors: Log as WARNING (recoverable)
- Unexpected errors: Log as ERROR (requires investigation)

**State Validation Chain**:
1. Connection exists check
2. WebSocket exists check
3. `is_closing` flag check (NEW)
4. WebSocket state check (NEW)
5. Message serialization
6. Send operation with exception handling

## Test Validation Strategy

**Current Failing Tests** (should pass after implementation):
1. `test_concurrent_send_and_close_operations` - Race condition reproduction
2. `test_websocket_connection_is_closing_flag_gap` - Flag validation testing
3. `test_websocket_manager_send_during_close_race_condition` - Manager-level prevention
4. `test_connection_state_transitions_during_race_condition` - State management validation

**Expected Results**:
- All 4 currently failing tests should pass
- No "send after close" errors in logs during normal disconnection
- WebSocket events continue to be delivered reliably during agent execution
- Golden Path user flow remains unaffected

## SSOT Compliance

**Maintains Existing Architecture**:
- Uses existing `unified_manager.py` SSOT patterns
- Follows WebSocket SSOT interface compliance
- Preserves backward compatibility for all existing imports
- Maintains User Context Factory pattern for multi-user isolation

**No Breaking Changes**:
- All existing method signatures preserved
- Additional validation only, no behavior changes for stable connections
- Error handling enhancement only (graceful degradation)

## Business Impact Protection

**$500K+ ARR Safeguarding**:
- Prevents WebSocket event delivery failures during agent execution
- Maintains reliable real-time chat functionality
- Ensures all 5 critical agent events delivered (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- Protects Golden Path user flow integrity

**Performance Considerations**:
- Minimal overhead: Only 2-3 additional boolean checks per send operation
- No new async operations or locks introduced
- Maintains existing throughput characteristics
- Graceful degradation prevents error propagation

## Implementation Priority

**Phase 1: Core Race Condition Fix (Immediate)**
1. Implement `is_closing` flag validation in `send_message` method
2. Implement `is_closing` flag validation in `broadcast` method
3. Enhance error handling to treat send-after-close as DEBUG level

**Phase 2: State Management Enhancement (Follow-up)**
1. Ensure `is_closing` flag is set during connection removal
2. Add WebSocket state validation checks
3. Implement graceful degradation patterns

**Phase 3: Validation (Testing)**
1. Run existing failing tests to confirm they pass
2. Execute comprehensive WebSocket test suite
3. Validate Golden Path functionality remains intact

## Risk Mitigation

**Low Risk Implementation**:
- Only adds validation checks, doesn't change core logic
- Maintains all existing interfaces and method signatures
- Preserves backward compatibility completely
- Uses patterns already documented in SPEC learnings

**Rollback Plan**:
- Changes are isolated to validation logic only
- Can be reverted by removing the additional validation checks
- No database or state persistence changes required

## Success Criteria

1. **Immediate**: All 4 failing race condition tests pass
2. **Functional**: No "send after close" errors during normal disconnection
3. **Business**: Golden Path WebSocket events deliver reliably
4. **Performance**: No measurable performance degradation
5. **Stability**: No regressions in existing WebSocket functionality

This remediation plan provides a targeted, low-risk solution to Issue #335 while maintaining full backward compatibility and protecting the critical Golden Path business functionality.