# MCP Chat Interface Integration - Implementation Plan

## Executive Summary
Integrate MCP (Model Context Protocol) client capabilities into the existing chat interface, enabling users to access external tools and resources through natural language interactions via the supervisor, triage, and data agents.

## Current State Analysis

### Existing Components to Extend
1. **Supervisor Agent** (`app/agents/supervisor/`)
   - Already routes messages to sub-agents
   - Needs MCP tool discovery and routing logic

2. **Triage Agent** (`app/agents/triage_sub_agent/`)
   - Has error handling and diagnostic capabilities
   - Needs MCP tool execution for external diagnostics

3. **Data Agent** (`app/agents/data_sub_agent/`)
   - Handles data queries and processing
   - Needs MCP integration for external data sources

4. **WebSocket System** (`app/websocket/`, `frontend/providers/WebSocketProvider.tsx`)
   - Existing message handling infrastructure
   - Needs new MCP-specific message types

5. **MCP Client Core** (`app/mcp_client/`)
   - Basic MCP client implementation exists
   - Needs agent integration layer

## Implementation Phases

### Phase 1: Agent MCP Integration Layer (Priority: CRITICAL)

#### 1.1 Create MCP Context Manager
**File**: `app/agents/mcp_integration/context_manager.py` (NEW - ≤300 lines)
```python
# Manages MCP context for agents
# - Tool discovery caching
# - Server connection pooling
# - Permission checking
# - Context injection for agents
```

#### 1.2 Extend Supervisor Agent
**Files to modify**:
- `app/agents/supervisor/agent.py` - Add MCP intent detection (≤8 line functions)
- `app/agents/supervisor/state_manager.py` - Add MCP state tracking
- `app/agents/supervisor/websocket_notifier.py` - Add MCP message types

**New capabilities**:
- Detect MCP-related queries in user messages
- Query available MCP tools from registry
- Route to appropriate sub-agent with MCP context
- Aggregate multi-server MCP results

#### 1.3 Extend Triage Agent
**Files to modify**:
- `app/agents/triage_sub_agent/executor.py` - Add MCP tool execution
- `app/agents/triage_sub_agent/result_processor.py` - Process MCP results

**New capabilities**:
- Execute GitHub MCP tools for issue management
- Access documentation servers via MCP
- Analyze external logs via filesystem MCP

#### 1.4 Extend Data Agent
**Files to modify**:
- `app/agents/data_sub_agent/agent.py` - Add MCP data source support
- `app/agents/data_sub_agent/query_builder.py` - Build MCP queries
- `app/agents/data_sub_agent/execution_engine.py` - Execute MCP operations

**New capabilities**:
- Query external databases via MCP
- Process files from filesystem MCP
- Transform MCP data results

### Phase 2: WebSocket Protocol Extensions (Priority: HIGH)

#### 2.1 Add MCP Message Types
**File**: `app/schemas/websocket_server_messages.py`
```python
# Add new message types:
# - MCPToolDiscoveryMessage
# - MCPToolExecutionMessage  
# - MCPToolResultMessage
```

#### 2.2 Frontend WebSocket Handlers
**Files to modify**:
- `frontend/store/websocket-event-handlers.ts` - Add MCP event handlers
- `frontend/types/websocket-event-types.ts` - Add MCP event types
- `frontend/providers/WebSocketProvider.tsx` - Handle MCP messages

### Phase 3: UI Components (Priority: MEDIUM)

#### 3.1 MCP Status Indicators
**New files**:
- `frontend/components/chat/MCPToolIndicator.tsx` (≤300 lines)
- `frontend/components/chat/MCPServerStatus.tsx` (≤300 lines)
- `frontend/components/chat/MCPResultCard.tsx` (≤300 lines)

#### 3.2 Integrate into Existing Components
**Files to modify**:
- `frontend/components/chat/MessageItem.tsx` - Show MCP tool usage
- `frontend/components/chat/ChatHeader.tsx` - Display MCP server status
- `frontend/components/chat/layers/` - Render MCP results in layers

### Phase 4: Service Layer Integration (Priority: HIGH)

#### 4.1 MCP Service Extensions
**Files to modify**:
- `app/services/mcp_client_service.py` - Add agent-friendly methods
- `app/services/mcp_client_tool_executor.py` - Add permission checks
- `app/services/mcp_client_connection_manager.py` - Add health monitoring

#### 4.2 Create Agent-MCP Bridge
**New file**: `app/services/agent_mcp_bridge.py` (≤300 lines)
```python
# Bridge between agents and MCP client
# - Tool discovery for agents
# - Execution with context
# - Result transformation
# - Error handling
```

### Phase 5: Security & Permissions (Priority: CRITICAL)

#### 5.1 Permission Model
**Files to modify**:
- `app/auth/enhanced_auth_security.py` - Add MCP permissions
- `app/middleware/security_headers.py` - Validate MCP requests

#### 5.2 Tool Access Control
**New file**: `app/mcp_client/access_control.py` (≤300 lines)
```python
# Role-based MCP tool access
# - Admin: all tools
# - Developer: approved tools
# - Viewer: read-only results
```

## Module Breakdown (300-line compliance)

### New Modules Required (13 files, all ≤300 lines):
1. `app/agents/mcp_integration/context_manager.py`
2. `app/agents/mcp_integration/intent_detector.py`
3. `app/agents/mcp_integration/tool_mapper.py`
4. `app/services/agent_mcp_bridge.py`
5. `app/mcp_client/access_control.py`
6. `app/schemas/mcp_messages.py`
7. `frontend/components/chat/MCPToolIndicator.tsx`
8. `frontend/components/chat/MCPServerStatus.tsx`
9. `frontend/components/chat/MCPResultCard.tsx`
10. `frontend/hooks/useMCPTools.ts`
11. `frontend/services/mcp-client-service.ts`
12. `frontend/types/mcp-types.ts`
13. `frontend/utils/mcp-formatter.ts`

### Files to Extend (must maintain ≤300 lines):
- Split if approaching limit before adding MCP features
- Each function must remain ≤8 lines

## Testing Strategy

### Unit Tests
- `app/tests/agents/test_mcp_integration.py`
- `app/tests/services/test_agent_mcp_bridge.py`
- `frontend/__tests__/chat/mcp-components.test.tsx`

### Integration Tests
- `app/tests/e2e/test_mcp_chat_flow.py`
- `app/tests/e2e/test_mcp_multi_agent.py`

### E2E Scenarios
1. User queries external database via chat
2. User requests GitHub issue creation
3. User analyzes external log files
4. Multi-server coordination test

## Migration Path

### Step 1: Non-breaking additions
- Add new MCP modules without touching existing code
- Deploy MCP client infrastructure

### Step 2: Agent enhancements
- Extend agents with MCP capabilities
- Maintain backward compatibility

### Step 3: UI integration
- Add MCP indicators and status
- Progressive enhancement approach

### Step 4: Full activation
- Enable MCP features for users
- Monitor and optimize

## Success Metrics
- MCP tool discovery < 100ms (cached)
- Tool execution overhead < 50ms
- Zero regression in existing functionality
- 95% test coverage for new code
- All files ≤300 lines, all functions ≤8 lines

## Risk Mitigation
- Feature flag for MCP integration
- Graceful fallback if MCP servers unavailable
- Comprehensive error handling
- Security audit before production

## Timeline Estimate
- Phase 1: 2 days (Critical path)
- Phase 2: 1 day (Parallel with Phase 1)
- Phase 3: 1 day (After Phase 2)
- Phase 4: 1 day (Parallel with Phase 3)
- Phase 5: 1 day (Must complete before activation)
- Testing: 2 days (Throughout)

**Total: 5-6 days with parallel work**

## Next Steps
1. Review and approve plan
2. Create feature branch
3. Implement Phase 1 (Agent Integration)
4. Deploy to staging for testing
5. Iterate based on feedback