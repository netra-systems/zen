## Problem Summary

Mission critical test import errors are preventing execution of Golden Path validation tests, blocking verification of the core user flow (login → AI responses) that represents 90% of platform value.

## Business Impact

**CRITICAL BLOCKING ISSUE:**
- ❌ Cannot validate Golden Path user flow (login → get AI responses)
- ❌ Blocks protection of $500K+ ARR dependent on chat functionality
- ❌ Prevents verification of WebSocket agent events (5 business-critical events)
- ❌ Mission critical test suite cannot execute for system health validation
- ❌ SSOT compliance validation blocked for websocket_core module

**Business Priority:** Chat functionality delivers 90% of platform value - this directly blocks our ability to validate core system reliability.

## Technical Details

### Import Error 1: WebSocket Manager Access
```python
ImportError: cannot import name 'get_websocket_manager' from 'netra_backend.app.websocket_core'
```

**Affected Pattern:**
```python
from netra_backend.app.websocket_core import get_websocket_manager
```

### Import Error 2: Test User Context Factory
```python
ImportError: cannot import name 'create_test_user_context' from 'netra_backend.app.websocket_core.canonical_import_patterns'
```

**Affected Pattern:**
```python
from netra_backend.app.websocket_core.canonical_import_patterns import create_test_user_context
```

### Affected Test Files (22+ Mission Critical Tests)
- `tests/mission_critical/test_websocket_agent_events_suite.py`
- `tests/mission_critical/test_websocket_state_regression.py`
- `tests/mission_critical/test_singleton_removal_phase2.py`
- `netra_backend/tests/critical/test_websocket_state_regression.py`
- `netra_backend/tests/integration/critical_paths/test_websocket_silent_failures.py`
- And 17+ additional mission critical test files

## Root Cause Analysis

**SSOT Consolidation Incomplete Export Patterns:**
1. Recent SSOT consolidation in websocket_core module
2. Export patterns not properly defined in `__init__.py` files
3. Canonical import patterns module missing required exports
4. Factory methods not exposed through proper module interfaces

## Scope of Fix Required

**Import Path Fixes Needed:**
1. ✅ Update `netra_backend/app/websocket_core/__init__.py` with proper exports
2. ✅ Ensure `canonical_import_patterns.py` exports required factory methods
3. ✅ Validate all mission critical test imports can resolve
4. ✅ Run import validation: `python -c "from netra_backend.app.websocket_core import get_websocket_manager; print('SUCCESS')"`
5. ✅ Execute mission critical test suite to verify Golden Path validation

## Acceptance Criteria

- [ ] All import statements in mission critical tests resolve successfully
- [ ] `python tests/mission_critical/test_websocket_agent_events_suite.py` executes without import errors
- [ ] Golden Path validation can run end-to-end
- [ ] WebSocket agent events validation operational
- [ ] SSOT compliance maintained throughout fix

## Priority Justification

**P0 CRITICAL** - This directly blocks validation of core business functionality representing 90% of platform value and protecting $500K+ ARR. Without these tests, we cannot verify system health for Golden Path user flows.

## Related Documentation

- `docs/GOLDEN_PATH_USER_FLOW_COMPLETE.md` - Complete user journey analysis
- `CLAUDE.md` - Golden Path mission requirements
- `reports/DEFINITION_OF_DONE_CHECKLIST.md` - WebSocket module validation requirements
- `SPEC/learnings/websocket_agent_integration_critical.xml` - WebSocket integration patterns