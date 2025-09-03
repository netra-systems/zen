# Tool Dispatcher Migration Guide

## Overview

This guide documents the consolidation of Tool Dispatcher implementations to eliminate SSOT violations and establish a single, unified implementation.

## Migration Status

### Phase 1: MCPToolExecutor Renaming ✅ COMPLETE

**Changes Made:**
- `agent_mcp_bridge.py`: `MCPToolExecutor` → `AgentMCPToolExecutor`
- `mcp_client_tool_executor.py`: `MCPToolExecutor` → `ServiceMCPToolExecutor`
- Added backward compatibility aliases
- Updated all imports

**Files Modified:**
- netra_backend/app/services/agent_mcp_bridge.py
- netra_backend/app/services/mcp_client_tool_executor.py
- netra_backend/app/services/mcp_client_service.py

### Phase 2: Tool Dispatcher Consolidation 🚧 IN PROGRESS

**Current State:**
- Multiple implementations identified (882+ lines of duplication)
- Consolidation strategy defined
- Migration plan established

**Target Architecture:**
```
ToolDispatcher (unified core)
    ├── Factory enforcement (no direct instantiation)
    ├── Request-scoped isolation
    ├── WebSocket event integration
    ├── Permission layer
    └── Metrics & monitoring

AdminToolDispatcher (valid extension)
    └── Extends ToolDispatcher with admin features
```

## Breaking Changes

### MCPToolExecutor Renaming

**Old Import:**
```python
from netra_backend.app.services.agent_mcp_bridge import MCPToolExecutor
from netra_backend.app.services.mcp_client_tool_executor import MCPToolExecutor
```

**New Import:**
```python
# For agent-layer with permissions
from netra_backend.app.services.agent_mcp_bridge import AgentMCPToolExecutor

# For service-layer with DB tracking
from netra_backend.app.services.mcp_client_tool_executor import ServiceMCPToolExecutor

# Backward compatibility (DEPRECATED - will be removed)
from netra_backend.app.services.agent_mcp_bridge import MCPToolExecutor  # Alias to AgentMCPToolExecutor
from netra_backend.app.services.mcp_client_tool_executor import MCPToolExecutor  # Alias to ServiceMCPToolExecutor
```

### Tool Dispatcher Consolidation (Upcoming)

**Current Imports (All Valid):**
```python
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher  # Facade
from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher  # Core
from netra_backend.app.agents.tool_dispatcher_unified import UnifiedToolDispatcher  # Will be removed
from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher  # Pattern reference
```

**Future Import (After Consolidation):**
```python
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher  # Single source
```

## Migration Steps for Developers

### Step 1: Update MCPToolExecutor Imports

If your code uses MCPToolExecutor, determine which layer you need:

1. **Agent Layer (with permissions):** Use `AgentMCPToolExecutor`
2. **Service Layer (with DB tracking):** Use `ServiceMCPToolExecutor`

### Step 2: Prepare for Tool Dispatcher Consolidation

No immediate action required. Continue using existing imports. The consolidation will maintain backward compatibility.

### Step 3: Test Your Components

Run the following tests to ensure your components work with the changes:

```bash
# Test MCP functionality
python tests/agents/test_mcp_integration.py

# Test Tool Dispatcher functionality
python tests/agents/test_tool_dispatcher_core_operations.py

# Test WebSocket events
python tests/mission_critical/test_websocket_agent_events_suite.py
```

## Factory Pattern Requirements

**CRITICAL:** Tool Dispatchers MUST be created via factory methods to ensure proper isolation:

```python
# WRONG - Direct instantiation
dispatcher = ToolDispatcher(...)  # Will raise RuntimeError

# CORRECT - Factory creation
dispatcher = ToolDispatcher.create_request_scoped_dispatcher(
    user_context=user_context,
    websocket_manager=websocket_manager
)

# CORRECT - Via factory class
from netra_backend.app.agents.tool_executor_factory import ToolExecutorFactory
factory = ToolExecutorFactory()
dispatcher = factory.create_tool_dispatcher(user_context)
```

## WebSocket Integration Requirements

All Tool Dispatchers MUST integrate with WebSocket for agent events:

```python
# Required events
- agent_started
- agent_thinking
- tool_executing
- tool_completed
- agent_completed

# Integration via AgentRegistry
from netra_backend.app.agents.agent_registry import AgentRegistry
registry = AgentRegistry()
registry.set_websocket_manager(websocket_manager)
```

## Testing Checklist

Before deploying changes, ensure:

- [ ] All agent tests pass
- [ ] WebSocket events are delivered correctly
- [ ] MCP tools execute successfully
- [ ] Concurrent user isolation works
- [ ] Admin operations function properly
- [ ] No performance degradation

## Rollback Plan

If issues arise:

1. **MCPToolExecutor:** The backward compatibility aliases allow immediate rollback
2. **Tool Dispatcher:** The facade pattern allows switching implementations without code changes

## Timeline

- **Phase 1:** MCPToolExecutor renaming - ✅ COMPLETE
- **Phase 2:** Tool Dispatcher consolidation - In Progress (ETA: 2-3 days)
- **Phase 3:** Testing and validation - Upcoming (ETA: 1-2 days)
- **Phase 4:** Cleanup and documentation - Future (ETA: 1 day)

## Support

For questions or issues during migration:
- Review the analysis in `TOOL_DISPATCHER_CONSOLIDATION_ANALYSIS.md`
- Check the deduplication report in `TOOL_DISPATCHER_DEDUPLICATION_REPORT.md`
- Run the compliance check: `python scripts/check_architecture_compliance.py`

## Deprecation Schedule

- **MCPToolExecutor aliases:** Will be removed in 30 days
- **UnifiedToolDispatcher:** Will be removed after successful consolidation
- **Legacy factory patterns:** Will be unified in Phase 2