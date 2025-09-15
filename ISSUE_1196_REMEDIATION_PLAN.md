# Issue #1196 - SSOT Import Path Fragmentation Remediation Plan

**Generated:** 2025-09-15
**Status:** 📋 **PLANNING PHASE** - DO NOT EXECUTE YET
**Business Impact:** $500K+ ARR Golden Path blocked by import fragmentation causing initialization race conditions
**Severity:** 🚨 **CRITICAL** - 1,772 WebSocket variations, 97 ExecutionEngine variations, 28 AgentRegistry variations

---

## Executive Summary

This plan addresses the massive import path fragmentation discovered in Issue #1196 testing:
- **WebSocket Manager**: 1,772 import variations (30.5x worse than expected)
- **ExecutionEngine**: 97 import variations (6.5x worse than expected)
- **AgentRegistry**: 28 import variations (already addressed in Issue #863)
- **Cross-service patterns**: 1,591 unique patterns
- **Performance impact**: Up to 26.81x slower imports

The remediation will be executed in 4 phases to ensure system stability while consolidating to SSOT patterns.

---

## Phase 1: WebSocket Manager Consolidation (Highest Priority)

### Current State Analysis
- **Variations Found**: 1,772 different import patterns
- **Files Affected**: Estimated 200+ files across all services
- **Business Risk**: Initialization race conditions affecting real-time chat functionality

### Canonical SSOT Import Path
```python
# CANONICAL - Single Source of Truth
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, get_websocket_manager
from netra_backend.app.websocket_core.websocket_manager import WebSocketConnection, WebSocketManagerMode
```

### Import Patterns to Replace
```python
# DEPRECATED - All these must be replaced:
from netra_backend.app.websocket_core import WebSocketManager  # Missing .websocket_manager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager  # Wrong module
from netra_backend.app.websocket_core.factory import WebSocketManagerFactory  # Factory pattern deprecated
from netra_backend.app.core.websocket import WebSocketManager  # Wrong path
from netra_backend.app.websocket import WebSocketManager  # Incomplete path
# ... and 1,767 other variations
```

### Files to Modify (Priority Order)
1. **Core Service Files**:
   - `/netra_backend/app/dependencies.py`
   - `/netra_backend/app/main.py`
   - `/netra_backend/app/routes/websocket.py`
   - `/netra_backend/app/agents/supervisor_agent_modern.py`

2. **Agent Integration**:
   - `/netra_backend/app/agents/base_agent.py`
   - `/netra_backend/app/agents/supervisor/workflow_orchestrator.py`
   - `/netra_backend/app/services/agent_websocket_bridge.py`

3. **Test Files** (200+ files):
   - All files in `/tests/` with WebSocket imports
   - All files in `/netra_backend/tests/` with WebSocket imports

### Migration Strategy
1. **Create compatibility shim** (temporary):
   ```python
   # In websocket_manager.py, add temporary compatibility exports
   # This prevents breaking changes during migration
   UnifiedWebSocketManager = WebSocketManager  # Temporary alias
   ```

2. **Systematic replacement using sed**:
   ```bash
   # Create backup first
   find . -name "*.py" -exec cp {} {}.backup \;

   # Replace common patterns
   find . -name "*.py" -exec sed -i 's/from netra_backend\.app\.websocket_core import WebSocketManager/from netra_backend.app.websocket_core.websocket_manager import WebSocketManager/g' {} \;
   ```

3. **Manual verification** for complex patterns

### Backward Compatibility
- Add deprecation warnings to old import paths
- Maintain temporary aliases for 1 sprint
- Log usage of deprecated paths for tracking

---

## Phase 2: ExecutionEngine Consolidation

### Current State Analysis
- **Variations Found**: 97 different import patterns
- **Files Affected**: Estimated 50+ files
- **Performance Impact**: 18.20x slower initialization

### Canonical SSOT Import Path
```python
# CANONICAL - Based on SSOT_IMPORT_REGISTRY.md
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
```

### Import Patterns to Replace
```python
# DEPRECATED - All these must be replaced:
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine  # Old module
from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine  # Wrong location
from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory  # Factory deprecated
# ... and 94 other variations
```

### Files to Modify (Priority Order)
1. **Core Dependencies**:
   - `/netra_backend/app/dependencies.py`
   - `/netra_backend/app/agents/supervisor/agent_instance_factory.py`

2. **Agent Files**:
   - `/netra_backend/app/agents/supervisor_ssot.py`
   - `/netra_backend/app/agents/base_agent.py`
   - All agent implementation files

3. **Test Files**:
   - Mission critical tests
   - Integration tests
   - Unit tests

### Migration Strategy
1. **Update execution_engine.py** to re-export from user_execution_engine.py
2. **Batch replacement** using automated tools
3. **Validate factory pattern** integrity

---

## Phase 3: AgentRegistry Standardization

### Current State Analysis
- **Variations Found**: 28 different import patterns
- **Status**: Already addressed in Issue #863 Phase 3
- **Performance Impact**: 26.81x slower imports

### Canonical SSOT Import Path
```python
# CANONICAL - Per Issue #863 resolution
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, AgentType, AgentStatus, AgentInfo, get_agent_registry
```

### Verification Required
- Ensure Issue #863 changes are fully propagated
- Update any remaining non-canonical imports
- Verify performance consistency

---

## Phase 4: Registry Documentation Fix

### Broken Import Paths to Fix
1. **UnifiedWebSocketManager**:
   - Remove references to `unified_manager` module
   - Update to canonical `websocket_manager` imports

2. **ExecutionEngine deprecated path**:
   - Remove references to old `execution_engine` module
   - Update to `user_execution_engine` imports

### Files to Update
- `/docs/SSOT_IMPORT_REGISTRY.md`
- Any documentation referencing old import paths

---

## Risk Mitigation Strategy

### 1. Pre-Migration Validation
```bash
# Create comprehensive import inventory
python scripts/analyze_imports.py --component all > import_inventory_before.json

# Run all tests to establish baseline
python tests/unified_test_runner.py --real-services
```

### 2. Staged Rollout
- **Day 1**: Add compatibility shims and deprecation warnings
- **Day 2-3**: Migrate core service files (10% of changes)
- **Day 4-5**: Migrate agent files (30% of changes)
- **Day 6-7**: Migrate test files (60% of changes)
- **Day 8**: Remove compatibility shims

### 3. Continuous Validation
```bash
# After each phase, validate:
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/unit/ssot/test_import_path_fragmentation_issue_1196.py
```

### 4. Rollback Plan
- Keep `.backup` files for all modified files
- Ability to restore from git if needed
- Compatibility shims allow gradual migration

---

## Success Metrics

### Quantitative Metrics
| Metric | Current | Target | Success Criteria |
|--------|---------|--------|------------------|
| WebSocket Import Variations | 1,772 | 1 | Single canonical path |
| ExecutionEngine Variations | 97 | 1 | Single canonical path |
| AgentRegistry Variations | 28 | 1 | Already achieved |
| Cross-Service Patterns | 1,591 | <10 | Minimal service-specific patterns |
| Import Performance Variance | 26.81x | <1.1x | <10% variance |
| Broken Registry Imports | 2 | 0 | 100% accuracy |

### Qualitative Metrics
- ✅ Golden Path stability improved
- ✅ No initialization race conditions
- ✅ Developer confusion eliminated
- ✅ Maintainability significantly improved

### Test Validation
```bash
# These tests should PASS after remediation:
python -m pytest tests/unit/ssot/test_import_path_fragmentation_issue_1196.py
python -m pytest tests/integration/test_ssot_import_registry_compliance_1196.py
```

---

## Implementation Tools

### Automated Import Replacement Script
```python
# scripts/fix_import_fragmentation.py
import os
import re
from pathlib import Path

REPLACEMENTS = {
    # WebSocket Manager
    r'from\s+netra_backend\.app\.websocket_core\s+import\s+WebSocketManager':
        'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',

    # ExecutionEngine
    r'from\s+netra_backend\.app\.agents\.supervisor\.execution_engine\s+import\s+ExecutionEngine':
        'from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine',

    # Add more patterns...
}

def fix_imports(file_path):
    """Fix import statements in a single file"""
    # Implementation here
    pass
```

### Validation Script
```python
# scripts/validate_ssot_imports.py
def validate_imports():
    """Ensure all imports use canonical paths"""
    # Scan codebase
    # Report non-canonical imports
    # Return success/failure
    pass
```

---

## Timeline and Resources

### Estimated Timeline
- **Phase 1 (WebSocket)**: 3 days
- **Phase 2 (ExecutionEngine)**: 2 days
- **Phase 3 (AgentRegistry)**: 1 day (verification only)
- **Phase 4 (Documentation)**: 1 day
- **Validation & Testing**: 2 days
- **Total**: 9 days

### Required Resources
- 1 Senior Engineer for implementation
- 1 QA Engineer for validation
- CI/CD pipeline time for test runs

---

## Post-Implementation Actions

1. **Update SSOT_IMPORT_REGISTRY.md** with verified canonical paths
2. **Add import linting rules** to prevent future fragmentation
3. **Create import style guide** for developers
4. **Add pre-commit hooks** to enforce SSOT imports
5. **Document lessons learned** in SPEC/learnings/

---

## Approval and Sign-off

**Status**: ⏳ Awaiting approval to proceed

### Review Checklist
- [ ] Risk assessment reviewed
- [ ] Rollback plan approved
- [ ] Success metrics agreed
- [ ] Timeline acceptable
- [ ] Resources available

### Next Steps
1. Review and approve this plan
2. Create feature branch for implementation
3. Begin Phase 1 WebSocket consolidation
4. Daily progress updates on Issue #1196

---

**Note**: This plan prioritizes stability and business continuity. The phased approach ensures Golden Path functionality remains operational throughout the migration.