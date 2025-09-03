# WebSocket SSOT Consolidation Plan
## Single Source of Truth Architecture Remediation
### Date: 2025-09-02

---

## EXECUTIVE SUMMARY

**Mission**: Achieve SSOT by consolidating duplicate implementations, not creating new ones
**Current State**: Multiple competing factory patterns causing confusion
**Target State**: One canonical implementation per concept
**Timeline**: 2 days (consolidation + validation)
**Business Impact**: Reduced complexity, easier maintenance, faster development

---

## PHASE 1: FACTORY CONSOLIDATION (Day 1)

### 1.1 ExecutionEngine Factory - MERGE & DELETE

**CURRENT DUPLICATION**:
- `execution_factory.py` (668 lines) - More complete, has ExecutionEngineFactory
- `execution_engine_factory.py` (525 lines) - Smaller, also has ExecutionEngineFactory  
- Both in `/netra_backend/app/agents/supervisor/`

**SSOT DECISION**:
```yaml
KEEP:
  file: netra_backend/app/agents/supervisor/execution_factory.py
  reason: Larger, more complete implementation with full lifecycle management
  class: ExecutionEngineFactory

DELETE:
  file: netra_backend/app/agents/supervisor/execution_engine_factory.py
  reason: Duplicate, smaller implementation
  
MIGRATION:
  - Merge any unique features from execution_engine_factory.py into execution_factory.py
  - Update all imports from execution_engine_factory to execution_factory
  - No new files needed - consolidate into existing
```

### 1.2 WebSocket Factory - USE EXISTING

**CURRENT SITUATION**:
- `websocket_bridge_factory.py` - WebSocketBridgeFactory (working)
- `websocket_factory.py` (routes) - Integration endpoints (working)

**SSOT DECISION**:
```yaml
KEEP:
  primary: netra_backend/app/services/websocket_bridge_factory.py
  reason: Already provides per-user isolation via UserWebSocketEmitter
  
ENHANCE:
  - Add any missing methods needed
  - Don't create WebSocketManagerFactory - use WebSocketBridgeFactory
  
NO_NEW_FILES:
  - Don't create services/websocket_factory.py
  - Don't create services/execution_factory.py
```

### 1.3 Tool Dispatcher - ALREADY UNIFIED

**CURRENT STATE**: ✅ Already SSOT compliant
- `tool_dispatcher_unified.py` - UnifiedToolDispatcher (SSOT)
- `tool_dispatcher.py` - Legacy, imports from unified

**SSOT DECISION**:
```yaml
KEEP_AS_IS:
  file: netra_backend/app/agents/tool_dispatcher_unified.py
  classes:
    - UnifiedToolDispatcher
    - UnifiedToolDispatcherFactory
    
NO_NEW_FILES:
  - Don't create enhanced_tool_execution.py
  - Don't create EnhancedToolExecutionEngine
```

---

## PHASE 2: IMPORT & REFERENCE UPDATES (Day 1)

### 2.1 Update Import References

**FILES TO UPDATE** (check and update imports):
```python
# Find all files importing from execution_engine_factory
grep -r "from.*execution_engine_factory import" --include="*.py"

# Update to import from execution_factory instead
# FROM: from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
# TO:   from netra_backend.app.agents.supervisor.execution_factory import ExecutionEngineFactory
```

**Key Files to Check**:
- `netra_backend/app/dependencies.py`
- `netra_backend/app/routes/agents_execute.py`
- `netra_backend/app/agents/supervisor/agent_registry.py`
- Any test files using ExecutionEngineFactory

### 2.2 Fix Agent Registry Issues

**FILE**: `netra_backend/app/agents/supervisor/agent_registry.py`

```python
# Line 189 - Fix None run_id usage
# CURRENT:
agent.set_websocket_bridge(self.websocket_bridge, None)

# CHANGE TO:
agent.set_websocket_bridge(self.websocket_bridge, context.run_id or str(uuid.uuid4()))
```

### 2.3 Clean Execution Engine Warnings

**FILE**: `netra_backend/app/agents/supervisor/execution_engine.py`

```python
# Lines 272-273 - Remove legacy warning or make it debug level
# CURRENT:
logger.warning("Using legacy ExecutionEngine with global state...")

# CHANGE TO:
logger.debug("Using ExecutionEngine fallback path")
```

---

## PHASE 3: VALIDATION & TESTING (Day 2)

### 3.1 Validation Checklist

```yaml
FACTORY_VALIDATION:
  execution:
    - [ ] execution_engine_factory.py deleted
    - [ ] All imports updated to execution_factory.py
    - [ ] No import errors
    - [ ] ExecutionEngineFactory works
    
  websocket:
    - [ ] WebSocketBridgeFactory is sole factory
    - [ ] No new websocket factories created
    - [ ] Per-user isolation verified
    
  tools:
    - [ ] UnifiedToolDispatcher remains SSOT
    - [ ] No enhanced_tool_execution.py created
    - [ ] Tool events still working

FUNCTIONAL_VALIDATION:
  - [ ] All 5 WebSocket events emitted
  - [ ] User isolation maintained
  - [ ] No shared state between users
  - [ ] Tests pass
```

### 3.2 Test Execution

```bash
# 1. Run mission critical tests
python tests/mission_critical/test_websocket_agent_events_suite.py

# 2. Run factory-specific tests
python -m pytest tests/ -k "factory" -v

# 3. Run E2E with real services
python tests/unified_test_runner.py --category e2e --real-services

# 4. Verify no import errors
python -c "from netra_backend.app.agents.supervisor.execution_factory import ExecutionEngineFactory; print('✅ Import successful')"
```

---

## PHASE 4: DOCUMENTATION UPDATE (Day 2)

### 4.1 Update Architecture Docs

**FILES TO UPDATE**:
- `USER_CONTEXT_ARCHITECTURE.md` - Update factory references
- `docs/GOLDEN_AGENT_INDEX.md` - Ensure points to correct factories
- `CLAUDE.md` - Update SSOT section with consolidated patterns

### 4.2 Update String Literals Index

```bash
# Regenerate string literals after consolidation
python scripts/scan_string_literals.py

# Verify factory strings
python scripts/query_string_literals.py validate "ExecutionEngineFactory"
```

---

## IMPLEMENTATION TASKS

### Task 1: Merge Execution Factories
```bash
# 1. Compare unique features
diff execution_engine_factory.py execution_factory.py

# 2. Merge any unique methods into execution_factory.py

# 3. Delete the duplicate
rm execution_engine_factory.py

# 4. Update imports globally
find . -name "*.py" -exec sed -i '' 's/execution_engine_factory/execution_factory/g' {} \;
```

### Task 2: Fix Agent Registry
```python
# In agent_registry.py line 189
# Add proper run_id handling instead of None
```

### Task 3: Validate Everything Works
```bash
# Run comprehensive validation
python tests/mission_critical/test_websocket_agent_events_suite.py
```

---

## SUCCESS CRITERIA

### SSOT Achieved When:

1. **ONE ExecutionEngineFactory**
   - ✅ Only in execution_factory.py
   - ✅ No execution_engine_factory.py exists
   - ✅ All imports point to single location

2. **ONE WebSocket Factory Pattern**
   - ✅ WebSocketBridgeFactory is sole factory
   - ✅ No WebSocketManagerFactory created
   - ✅ No competing patterns

3. **ONE Tool Dispatcher**
   - ✅ UnifiedToolDispatcher remains SSOT
   - ✅ No EnhancedToolExecutionEngine created
   - ✅ No duplicate tool patterns

4. **Clean Codebase**
   - ✅ No deprecation warnings in normal flow
   - ✅ No None run_id usage
   - ✅ No duplicate implementations

5. **Tests Pass**
   - ✅ Mission critical WebSocket tests pass
   - ✅ E2E tests pass
   - ✅ No import errors

---

## WHAT NOT TO DO

### ❌ DO NOT CREATE THESE FILES:
- `/netra_backend/app/services/execution_factory.py`
- `/netra_backend/app/services/websocket_factory.py`
- `/netra_backend/app/services/enhanced_tool_execution.py`

### ❌ DO NOT ADD THESE CLASSES:
- `ExecutionContextFactory` (use ExecutionEngineFactory)
- `WebSocketManagerFactory` (use WebSocketBridgeFactory)
- `EnhancedToolExecutionEngine` (use UnifiedToolDispatcher)

### ❌ DO NOT:
- Create new factory patterns
- Add more abstraction layers
- Duplicate existing functionality

---

## ROLLBACK PLAN

If issues arise during consolidation:

1. **Git Stash Changes**: `git stash`
2. **Restore Duplicate**: `git checkout -- execution_engine_factory.py`
3. **Document Issues**: Note what broke during consolidation
4. **Incremental Approach**: Consolidate one factory at a time

---

## TIMELINE

```
Day 1 Morning (4 hours):
- Merge execution factories
- Delete duplicate file
- Update all imports
- Fix agent_registry.py

Day 1 Afternoon (4 hours):
- Validate WebSocket factory usage
- Ensure tool dispatcher stays unified
- Run initial tests
- Fix any import errors

Day 2 Morning (4 hours):
- Run comprehensive test suite
- Fix any test failures
- Verify user isolation
- Performance testing

Day 2 Afternoon (4 hours):
- Update documentation
- Regenerate string literals
- Final validation
- Commit changes
```

---

## APPENDIX: Quick Commands

### Find Duplicates
```bash
# Find all ExecutionEngineFactory definitions
grep -r "class ExecutionEngineFactory" --include="*.py"

# Find all factory imports
grep -r "Factory" --include="*.py" | grep import

# Check for None run_id usage
grep -r "None.*run_id\|run_id.*None" --include="*.py"
```

### Validate SSOT
```bash
# Ensure no duplicate factories
find . -name "*factory*.py" -exec grep -l "class.*Factory" {} \;

# Check unified imports
python -c "from netra_backend.app.agents.tool_dispatcher_unified import UnifiedToolDispatcher"
```

### Test Commands
```bash
# Quick validation
python -m pytest tests/mission_critical/ -k "websocket" --tb=short

# Full suite
python tests/unified_test_runner.py --real-services
```

---

**END OF PLAN**

This plan focuses on CONSOLIDATION not CREATION. Follow it to achieve true SSOT.