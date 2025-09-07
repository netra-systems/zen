# WebSocket Classes MRO (Method Resolution Order) Report
Generated: 2025-09-04T12:24:47.315886
================================================================================

## WebSocketManager (Primary)
**Module:** `netra_backend.app.websocket_core.manager`
**Direct Parents:** object
**Abstract:** No
**Has __init__:** Yes
**Public Methods:** 15

### Method Resolution Order (MRO):
└─ WebSocketManager
  └─ object

### Key Methods and Sources:
- **From WebSocketManager:** check_connection_health, cleanup_connection_scope, connect_user, disconnect_user, enhanced_ping_connection, get_connection_id_by_websocket, get_connection_scope, get_stats, record_pong_received, send_message
  ... and 5 more

----------------------------------------

## WebSocketHeartbeatManager
**Module:** `netra_backend.app.websocket_core.manager`
**Direct Parents:** object
**Abstract:** No
**Has __init__:** Yes
**Public Methods:** 4

### Method Resolution Order (MRO):
└─ WebSocketHeartbeatManager
  └─ object

### Key Methods and Sources:
- **From WebSocketHeartbeatManager:** register_connection, start, stop, unregister_connection

----------------------------------------

## ConnectionScopedWebSocketManager
**Module:** `netra_backend.app.websocket.manager`
**Direct Parents:** object
**Abstract:** No
**Has __init__:** Yes
**Public Methods:** 13

### Method Resolution Order (MRO):
└─ ConnectionScopedWebSocketManager
  └─ object

### Key Methods and Sources:
- **From ConnectionScopedWebSocketManager:** add_event_callback, cleanup, get_connection_stats, get_global_stats, handle_incoming_message, initialize, is_connection_healthy, send_agent_completed, send_agent_error, send_agent_started
  ... and 3 more

----------------------------------------

## IsolatedWebSocketEventEmitter
**Module:** `netra_backend.app.websocket_core.isolated_event_emitter`
**Direct Parents:** object
**Abstract:** No
**Has __init__:** Yes
**Public Methods:** 12

### Method Resolution Order (MRO):
└─ IsolatedWebSocketEventEmitter
  └─ object

### Key Methods and Sources:
- **From IsolatedWebSocketEventEmitter:** cleanup, create_for_user, emit_agent_completed, emit_agent_started, emit_agent_thinking, emit_tool_completed, emit_tool_executing, get_event_stats, notify_agent_completed, notify_agent_error
  ... and 2 more

----------------------------------------

## WebSocketEventEmitter
**Module:** `netra_backend.app.services.websocket_event_emitter`
**Direct Parents:** object
**Abstract:** No
**Has __init__:** Yes
**Public Methods:** 11

### Method Resolution Order (MRO):
└─ WebSocketEventEmitter
  └─ object

### Key Methods and Sources:
- **From WebSocketEventEmitter:** dispose, get_context, get_metrics, notify_agent_completed, notify_agent_error, notify_agent_started, notify_agent_thinking, notify_custom, notify_progress_update, notify_tool_completed
  ... and 1 more

----------------------------------------

## WebSocketEventEmitterFactory
**Module:** `netra_backend.app.services.websocket_event_emitter`
**Direct Parents:** object
**Abstract:** No
**Has __init__:** No (inherited)
**Public Methods:** 2

### Method Resolution Order (MRO):
└─ WebSocketEventEmitterFactory
  └─ object

### Key Methods and Sources:
- **From WebSocketEventEmitterFactory:** create_emitter, create_scoped_emitter

----------------------------------------

## WebSocketEmitterPool
**Module:** `netra_backend.app.services.websocket_emitter_pool`
**Direct Parents:** object
**Abstract:** No
**Has __init__:** Yes
**Public Methods:** 6

### Method Resolution Order (MRO):
└─ WebSocketEmitterPool
  └─ object

### Key Methods and Sources:
- **From WebSocketEmitterPool:** OptimizedUserWebSocketEmitter, acquire, cleanup_inactive_emitters, get_statistics, release, shutdown

----------------------------------------

## UserWebSocketEmitter
**Module:** `netra_backend.app.services.user_websocket_emitter`
**Direct Parents:** object
**Abstract:** No
**Has __init__:** Yes
**Public Methods:** 9

### Method Resolution Order (MRO):
└─ UserWebSocketEmitter
  └─ object

### Key Methods and Sources:
- **From UserWebSocketEmitter:** get_stats, notify_agent_completed, notify_agent_error, notify_agent_started, notify_agent_thinking, notify_custom, notify_progress_update, notify_tool_completed, notify_tool_executing

----------------------------------------

## Inheritance Relationships Summary

### Common Ancestors:
- object

## Method Overlap Analysis

### Methods Present in Multiple Classes:
- **cleanup**: ConnectionScopedWebSocketManager, IsolatedWebSocketEventEmitter
- **get_stats**: WebSocketManager (Primary), UserWebSocketEmitter
- **notify_agent_completed**: IsolatedWebSocketEventEmitter, WebSocketEventEmitter, UserWebSocketEmitter
- **notify_agent_error**: IsolatedWebSocketEventEmitter, WebSocketEventEmitter, UserWebSocketEmitter
- **notify_agent_started**: IsolatedWebSocketEventEmitter, WebSocketEventEmitter, UserWebSocketEmitter
- **notify_agent_thinking**: WebSocketEventEmitter, UserWebSocketEmitter
- **notify_custom**: WebSocketEventEmitter, UserWebSocketEmitter
- **notify_progress_update**: WebSocketEventEmitter, UserWebSocketEmitter
- **notify_tool_completed**: WebSocketEventEmitter, UserWebSocketEmitter
- **notify_tool_executing**: WebSocketEventEmitter, UserWebSocketEmitter
- **shutdown**: WebSocketManager (Primary), WebSocketEmitterPool

## Consolidation Recommendations

### Priority 1: Merge Similar Patterns
- UserWebSocketEmitter variants can be unified
- WebSocketEventEmitter and IsolatedWebSocketEventEmitter share emission logic

### Priority 2: Extract Common Behavior
- Connection management logic from ConnectionScopedWebSocketManager
- Heartbeat logic already in WebSocketManager
- Pool management from WebSocketEmitterPool

### Priority 3: Maintain Critical Patterns
- AgentWebSocketBridge pattern (not analyzed here but critical)
- Per-user isolation from ConnectionScopedWebSocketManager
- Factory pattern from WebSocketEventEmitterFactory

## Risk Warnings

⚠️ **Critical Considerations:**
1. WebSocketManager uses singleton pattern - must preserve or safely migrate
2. ConnectionScopedWebSocketManager explicitly avoids singleton - reconcile patterns
3. Multiple inheritance paths could cause method shadowing
4. Factory patterns must be preserved for dependency injection
