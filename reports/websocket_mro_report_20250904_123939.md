# WebSocket Classes MRO Analysis Report
Generated: 2025-09-04T12:39:36.010117

## Executive Summary
This report analyzes the Method Resolution Order (MRO) of WebSocket classes 
to identify consolidation opportunities and prevent method shadowing issues.

## Detailed Class Analysis

### UnifiedWebSocketManager
- **Module**: `netra_backend.app.websocket_core.unified_manager`
- **Direct Base Classes**: object
- **MRO**: UnifiedWebSocketManager → object
- **Method Count**: 17
- **Attribute Count**: 8
- **Overridden Methods**: 2
  - `__init__` (from object)
  - `__new__` (from object)
- **Key Methods**:
  - ✅ `emit_critical_event`

### WebSocketConnection
- **Module**: `netra_backend.app.websocket_core.unified_manager`
- **Direct Base Classes**: object
- **MRO**: WebSocketConnection → object
- **Method Count**: 1
- **Attribute Count**: 0
- **Overridden Methods**: 1
  - `__init__` (from object)
- **Key Methods**:

### UnifiedWebSocketEmitter
- **Module**: `netra_backend.app.websocket_core.unified_emitter`
- **Direct Base Classes**: object
- **MRO**: UnifiedWebSocketEmitter → object
- **Method Count**: 22
- **Attribute Count**: 4
- **Overridden Methods**: 1
  - `__init__` (from object)
- **Key Methods**:
  - ✅ `notify_agent_started`
  - ✅ `emit_agent_started`
  - ✅ `emit_agent_thinking`
  - ✅ `emit_tool_executing`
  - ✅ `emit_tool_completed`
  - ✅ `emit_agent_completed`

### WebSocketEmitterFactory
- **Module**: `netra_backend.app.websocket_core.unified_emitter`
- **Direct Base Classes**: object
- **MRO**: WebSocketEmitterFactory → object
- **Method Count**: 2
- **Attribute Count**: 0
- **Key Methods**:

### WebSocketEmitterPool
- **Module**: `netra_backend.app.websocket_core.unified_emitter`
- **Direct Base Classes**: object
- **MRO**: WebSocketEmitterPool → object
- **Method Count**: 6
- **Attribute Count**: 0
- **Overridden Methods**: 1
  - `__init__` (from object)
- **Key Methods**:

### UserWebSocketEmitter
- **Module**: `netra_backend.app.agents.supervisor.agent_instance_factory`
- **Direct Base Classes**: object
- **MRO**: UserWebSocketEmitter → object
- **Method Count**: 9
- **Attribute Count**: 0
- **Overridden Methods**: 1
  - `__init__` (from object)
- **Key Methods**:
  - ✅ `notify_agent_started`

### AgentWebSocketBridge
- **Module**: `netra_backend.app.services.agent_websocket_bridge`
- **Direct Base Classes**: MonitorableComponent
- **MRO**: AgentWebSocketBridge → MonitorableComponent → ABC → object
- **Method Count**: 59
- **Attribute Count**: 0
- **Overridden Methods**: 8
  - `__init__` (from MonitorableComponent)
  - `get_health_status` (from MonitorableComponent)
  - `get_metrics` (from MonitorableComponent)
  - `notify_health_change` (from MonitorableComponent)
  - `register_monitor_observer` (from MonitorableComponent)
- **Key Methods**:
  - ✅ `notify_agent_started`

## Consolidation Opportunities

### Duplicate Method Patterns
These methods appear in multiple classes (consolidation candidates):

- `acquire`: UnifiedWebSocketEmitter, WebSocketEmitterPool
- `cleanup`: UnifiedWebSocketEmitter, UserWebSocketEmitter
- `create_scoped_emitter`: WebSocketEmitterFactory, AgentWebSocketBridge
- `get_stats`: UnifiedWebSocketManager, UnifiedWebSocketEmitter
- `notify_agent_completed`: UnifiedWebSocketEmitter, UserWebSocketEmitter, AgentWebSocketBridge
- `notify_agent_error`: UnifiedWebSocketEmitter, UserWebSocketEmitter, AgentWebSocketBridge
- `notify_agent_started`: UnifiedWebSocketEmitter, UserWebSocketEmitter, AgentWebSocketBridge
- `notify_agent_thinking`: UnifiedWebSocketEmitter, UserWebSocketEmitter, AgentWebSocketBridge
- `notify_custom`: UnifiedWebSocketEmitter, AgentWebSocketBridge
- `notify_progress_update`: UnifiedWebSocketEmitter, AgentWebSocketBridge
- `notify_tool_completed`: UnifiedWebSocketEmitter, UserWebSocketEmitter, AgentWebSocketBridge
- `notify_tool_executing`: UnifiedWebSocketEmitter, UserWebSocketEmitter, AgentWebSocketBridge
- `release`: UnifiedWebSocketEmitter, WebSocketEmitterPool
- `shutdown`: UnifiedWebSocketManager, WebSocketEmitterPool, AgentWebSocketBridge

### Critical Event Implementation Status
- ✅ `agent_started`: UnifiedWebSocketEmitter, UserWebSocketEmitter, AgentWebSocketBridge
- ✅ `agent_thinking`: UnifiedWebSocketEmitter, UserWebSocketEmitter, AgentWebSocketBridge
- ✅ `tool_executing`: UnifiedWebSocketEmitter, UserWebSocketEmitter, AgentWebSocketBridge
- ✅ `tool_completed`: UnifiedWebSocketEmitter, UserWebSocketEmitter, AgentWebSocketBridge
- ✅ `agent_completed`: UnifiedWebSocketEmitter, UserWebSocketEmitter, AgentWebSocketBridge

## Recommendations

1. **UnifiedWebSocketManager** is the SSOT for WebSocket management
2. **UnifiedWebSocketEmitter** is the SSOT for event emission
3. **UserWebSocketEmitter** in agent_instance_factory should delegate to UnifiedWebSocketEmitter
4. **AgentWebSocketBridge** correctly uses the bridge pattern for integration
5. All 5 critical events MUST be preserved during consolidation