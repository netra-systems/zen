# WebSocket Architecture Extraction Report
Date: 2025-09-04
Mission: Consolidate WebSocket infrastructure for MISSION CRITICAL Chat Value

## Executive Summary
Current WebSocket infrastructure has significant duplication with multiple implementations of WebSocketManagers and Emitters. This report documents all existing implementations to ensure value preservation during consolidation.

## CRITICAL: The 5 Mission-Critical Events
These events MUST be preserved during consolidation:
1. **agent_started** - User sees agent began processing
2. **agent_thinking** - Real-time reasoning visibility
3. **tool_executing** - Tool usage transparency
4. **tool_completed** - Tool results display
5. **agent_completed** - Response ready notification

## Current Architecture Analysis

### WebSocketManager Implementations Found

#### 1. PRIMARY: `netra_backend/app/websocket_core/manager.py`
- **Class**: `WebSocketManager` (Line 264-2025+)
- **Type**: Enhanced Unified Manager (Claims to be SSOT)
- **Features**:
  - Singleton pattern implementation
  - Protocol abstraction for modern websockets
  - Enhanced heartbeat monitoring
  - Comprehensive health checking
  - Connection pooling (size=10)
  - Max 3 connections per user
  - Max 100 total connections
  - TTL cache (3 minutes)
- **Business Value**: Claims to eliminate 90+ redundant files
- **Status**: CANONICAL - Keep as base for UnifiedWebSocketManager

#### 2. CONNECTION-SCOPED: `netra_backend/app/websocket/manager.py`
- **Class**: `ConnectionScopedWebSocketManager` (Line 93+)
- **Type**: Per-connection isolation manager
- **Features**:
  - Created per-connection (NOT singleton)
  - User isolation enforced
  - Blocks cross-user events
  - Connection-specific handlers
  - Audit logging
- **Value**: Zero cross-user leakage pattern
- **Status**: MERGE isolation logic into unified

#### 3. HEARTBEAT: `netra_backend/app/websocket_core/manager.py`
- **Class**: `WebSocketHeartbeatManager` (Line 2025)
- **Type**: Specialized heartbeat management
- **Status**: Already part of main WebSocketManager

### Emitter Implementations Found

#### 1. `netra_backend/app/websocket_core/isolated_event_emitter.py`
- **Class**: `IsolatedWebSocketEventEmitter` (Line 55)
- **Purpose**: User-isolated event emission
- **Status**: MERGE into UnifiedEmitter

#### 2. `netra_backend/app/agents/supervisor/agent_instance_factory.py`
- **Class**: `UserWebSocketEmitter` (Line 59)
- **Purpose**: Agent-specific emitter in factory
- **Status**: MERGE pattern into UnifiedEmitter

#### 3. `netra_backend/app/services/websocket_event_emitter.py`
- **Class**: `WebSocketEventEmitter` (Line 47)
- **Class**: `WebSocketEventEmitterFactory` (Line 635)
- **Purpose**: Event emitter with factory pattern
- **Status**: MERGE factory pattern

#### 4. `netra_backend/app/services/websocket_emitter_pool.py`
- **Class**: `WebSocketEmitterPool` (Line 45)
- **Class**: `OptimizedUserWebSocketEmitter` (Line 54)
- **Purpose**: Pooled emitter management
- **Status**: INTEGRATE pool into factory

#### 5. `netra_backend/app/services/websocket_bridge_factory.py`
- **Class**: `UserWebSocketEmitter` (Line 391)
- **Purpose**: Bridge pattern emitter
- **Status**: PRESERVE bridge pattern

#### 6. `netra_backend/app/services/user_websocket_emitter.py`
- **Class**: `UserWebSocketEmitter` (Line 27)
- **Purpose**: User-specific emitter
- **Status**: MERGE into UnifiedEmitter

### Protocol/Interface Definitions Found

#### 1. `netra_backend/app/agents/base/interface.py`
- **Class**: `WebSocketManagerProtocol` (Line 136)
- **Type**: Protocol definition

#### 2. `netra_backend/app/agents/interfaces.py`
- **Class**: `WebSocketManagerProtocol` (Line 76)
- **Type**: Duplicate protocol definition

#### 3. `netra_backend/app/core/interfaces_websocket.py`
- **Class**: `WebSocketManagerInterface` (Line 36)
- **Type**: Interface definition

#### 4. `netra_backend/app/schemas/strict_types.py`
- **Class**: `StrictWebSocketManager` (Line 81)
- **Type**: Strict protocol definition

### Key Integration Points

#### AgentWebSocketBridge Pattern (PRESERVE)
From `SPEC/learnings/websocket_agent_integration_critical.xml`:
- Bridge pattern successfully implemented
- 60% reduction in glue code
- Idempotent operations
- Health monitoring
- Graceful degradation

#### Critical Event Flow
1. Agent starts → `agent_started` event
2. Agent processes → `agent_thinking` events
3. Tool execution → `tool_executing` event
4. Tool completes → `tool_completed` event  
5. Agent finishes → `agent_completed` event

### Value Extraction Requirements

Before deleting any implementation, extract:
1. **Connection isolation logic** from ConnectionScopedWebSocketManager
2. **Heartbeat patterns** from WebSocketHeartbeatManager
3. **Pool management** from WebSocketEmitterPool
4. **Factory patterns** from WebSocketEventEmitterFactory
5. **Bridge integration** from AgentWebSocketBridge
6. **User-specific logic** from all UserWebSocketEmitter variants

### Risk Analysis

#### High Risk Areas
1. **Multi-user isolation**: Must preserve per-connection scoping
2. **Event delivery**: All 5 critical events must work
3. **Agent integration**: AgentWebSocketBridge pattern critical
4. **Thread safety**: Async/concurrent access patterns
5. **Backward compatibility**: Existing code depends on current interfaces

#### Mitigation Strategy
1. Create UnifiedWebSocketManager extending current WebSocketManager
2. Add connection-scoping from ConnectionScopedWebSocketManager
3. Integrate all emitter patterns into UnifiedWebSocketEmitter
4. Preserve AgentWebSocketBridge exactly as-is
5. Test each consolidation step with mission critical tests

## Consolidation Plan

### Target Architecture
```
netra_backend/app/websocket_core/
├── unified_manager.py          # Single WebSocketManager
├── unified_emitter.py          # Single WebSocketEmitter
└── agent_bridge.py            # Preserved AgentWebSocketBridge
```

### Phase 1: Create Unified Implementations
1. UnifiedWebSocketManager based on websocket_core/manager.py
2. Add connection-scoping features from websocket/manager.py
3. UnifiedWebSocketEmitter consolidating all emitter patterns
4. Integrate EmitterPool into factory pattern

### Phase 2: Migration
1. Update all imports to use unified implementations
2. Add deprecation warnings to old implementations
3. Run mission critical tests after each change
4. Verify all 5 events working

### Phase 3: Cleanup
1. Remove duplicate protocol definitions
2. Delete old manager implementations
3. Delete old emitter implementations
4. Update documentation

## Success Criteria
- [ ] Single UnifiedWebSocketManager implementation
- [ ] Single UnifiedWebSocketEmitter implementation
- [ ] All 5 critical events working
- [ ] Multi-user isolation preserved
- [ ] AgentWebSocketBridge pattern intact
- [ ] Zero WebSocket event loss
- [ ] Mission critical tests passing
- [ ] 13+ files reduced to 2-3 unified files

## Next Steps
1. Generate MRO report for inheritance analysis
2. Design detailed UnifiedWebSocketManager API
3. Implement consolidation with continuous testing
4. Document all breaking changes
5. Create migration guide for dependent code