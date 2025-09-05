# Critical Updates for Resilient Reporting Prompts

## Latest Code State Review

After reviewing the codebase, here are critical updates that need to be reflected in all prompts:

### 1. Unified Classes Actually Present

**CONFIRMED UNIFIED CLASSES:**
- `UnifiedTriageAgent` - Located at `netra_backend/app/agents/triage/unified_triage_agent.py`
- `UnifiedDataAgent` - Located at `netra_backend/app/agents/data/unified_data_agent.py`
- `UnifiedWebSocketManager` - Located at `netra_backend/app/websocket_core/unified_manager.py`
- `UnifiedDockerManager` - Located at `test_framework/unified_docker_manager.py`

**CRITICAL TOOLS:**
- `EnhancedToolExecutionEngine` - For WebSocket event wrapping
- `AgentWebSocketBridge` - For agent-WebSocket communication
- `WebSocketNotifier` - Deprecated but may still exist in tests

### 2. Correct Import Paths

```python
# WebSocket Management
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

# Triage Agent (SSOT)
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent

# Data Agent (SSOT)
from netra_backend.app.agents.data.unified_data_agent import UnifiedDataAgent

# Docker Management (Test Framework)
from test_framework.unified_docker_manager import UnifiedDockerManager

# Agent Registry & Factory
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory

# WebSocket Bridge
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# Tool Execution
from netra_backend.app.agents.unified_tool_execution import EnhancedToolExecutionEngine
```

### 3. Critical Integration Points

**WebSocket Event Chain:**
1. `AgentRegistry.set_websocket_manager()` - Enhances tool dispatcher
2. `ExecutionEngine` must have `WebSocketNotifier` initialized
3. `EnhancedToolExecutionEngine` wraps tool execution with events

**Factory Pattern Requirements:**
- ALL agents MUST be created via factory pattern
- UserExecutionContext is MANDATORY for isolation
- No global state allowed

### 4. Missing from Current Prompts

**ADD TO ALL IMPLEMENTATION PROMPTS:**

```python
# Critical: Check for existing unified implementations
UNIFIED_CLASSES = {
    'triage': 'netra_backend.app.agents.triage.unified_triage_agent.UnifiedTriageAgent',
    'data': 'netra_backend.app.agents.data.unified_data_agent.UnifiedDataAgent',
    'websocket': 'netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager',
    'docker': 'test_framework.unified_docker_manager.UnifiedDockerManager'
}

# Verify imports before implementation
for name, import_path in UNIFIED_CLASSES.items():
    try:
        module_path, class_name = import_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[class_name])
        cls = getattr(module, class_name)
        print(f"✓ {name}: {cls}")
    except ImportError:
        print(f"✗ {name}: Not found at {import_path}")
```

### 5. ReportingSubAgent Dependencies

**Current ReportingSubAgent uses:**
- `BaseAgent` as parent class
- `UserExecutionContext` for isolation
- `LLMResponseParser` and `JSONErrorFixer` from unified_json_handler
- `CacheHelpers` for cache key generation
- `DatabaseSessionManager` for session isolation

**Must integrate with:**
- `UnifiedTriageAgent` (provides triage_result)
- `UnifiedDataAgent` (provides data_result)
- `DataHelperAgent` (fallback for missing data)
- `WorkflowOrchestrator` (handles execution flow)

### 6. Test Infrastructure Updates

**Current test framework uses:**
- `UnifiedDockerManager` for Docker operations
- Real services by default (mocks forbidden)
- `unified_test_runner.py` as main test entry point
- Mission critical tests in `tests/mission_critical/`

### 7. Legacy Code to Remove

**Files that may need removal/consolidation:**
- `netra_backend/app/agents/demo_service/reporting.py` (if duplicate)
- Any reporting logic outside of `reporting_sub_agent.py`
- Old WebSocketNotifier usage (replace with AgentWebSocketBridge)
- Direct Docker commands (use UnifiedDockerManager)

### 8. Critical WebSocket Events

**MUST maintain these events:**
```python
REQUIRED_EVENTS = [
    'agent_started',
    'agent_thinking', 
    'tool_executing',
    'tool_completed',
    'agent_completed'
]
```

### 9. Workflow Execution Order

**CRITICAL - Correct order per AGENT_EXECUTION_ORDER_REASONING.md:**
1. Triage (UnifiedTriageAgent)
2. Data (UnifiedDataAgent)
3. Optimization
4. Actions
5. Reporting (ReportingSubAgent)

**When Reporting fails:**
- Do NOT restart workflow
- Trigger DataHelperAgent directly
- Provide partial report + data request

### 10. Update Requirements for Each Prompt

**Team 00 (Orchestration):**
- ✓ Add unified class verification step
- ✓ Reference correct import paths

**Team 01 (PM Requirements):**
- ✓ Confirm integration with UnifiedTriageAgent and UnifiedDataAgent
- ✓ Add dependency on UnifiedWebSocketManager

**Team 02 (Design Architecture):**
- ✓ Include UnifiedWebSocketEmitter in design
- ✓ Reference EnhancedToolExecutionEngine

**Team 03 (QA Testing):**
- ✓ Use UnifiedDockerManager for all Docker operations
- ✓ Reference unified_test_runner.py

**Team 04 (Core Implementation):**
- ✓ Import from correct unified modules
- ✓ Use AgentWebSocketBridge not WebSocketNotifier

**Team 05 (Checkpoint System):**
- ✓ Integrate with UnifiedWebSocketManager
- ✓ Use factory pattern from agent_instance_factory

**Team 06 (Data Helper Fallback):**
- ✓ Reference correct DataHelperAgent location
- ✓ Integrate with WorkflowOrchestrator properly

## Action Items

All prompts should be updated to:
1. Reference the correct unified class locations
2. Use proper import statements
3. Integrate with existing SSOT implementations
4. Remove any legacy references
5. Maintain WebSocket event chain
6. Use factory patterns consistently
7. Test with UnifiedDockerManager