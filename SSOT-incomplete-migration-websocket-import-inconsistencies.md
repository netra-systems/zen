# SSOT Gardener Progress: WebSocket Import Inconsistencies

**Issue:** SSOT-incomplete-migration-websocket-import-inconsistencies  
**GitHub Link:** https://github.com/netra-systems/netra-apex/issues/212  
**Priority:** CRITICAL - Blocks Golden Path Reliability  
**Business Impact:** $500K+ ARR chat functionality at risk  

## SSOT Violation Summary

**CRITICAL #1: Import Path Inconsistencies**
- **Files Affected:** 593+ files import UnifiedWebSocketManager inconsistently
- **Root Cause:** Multiple import patterns bypass SSOT canonical imports
- **Business Risk:** Integration failures and unpredictable production behavior

### Evidence
```python
# VIOLATION: Multiple import sources for same functionality
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager  
from netra_backend.app.websocket_core.canonical_imports import WebSocketManagerFactory
```

**CRITICAL #2: Factory Pattern SSOT Violation**
- **Security Risk:** Multi-user data leakage potential from singleton patterns
- **Files:** `/netra_backend/app/websocket_core/websocket_manager_factory.py:783`

### Evidence
```python
# FOUND: Legacy singleton usage still present
from netra_backend.app.websocket_core import get_websocket_manager
manager = get_websocket_manager()  # 🚨 SECURITY VIOLATION
```

## Remediation Plan (Phase 1 - URGENT)

### 1. Import Standardization Campaign
- [ ] Run codebase-wide replacement of direct manager imports
- [ ] Update all files to use canonical imports: `from netra_backend.app.websocket_core.canonical_imports import`
- [ ] Validate no import bypasses SSOT validation

### 2. Factory Pattern Enforcement  
- [ ] Audit all `get_websocket_manager()` singleton usage
- [ ] Replace with factory pattern: `create_websocket_manager(user_context)`
- [ ] Ensure user isolation for multi-tenant security

## Test Plan
- [ ] Create failing tests that reproduce SSOT violations
- [ ] Validate import consistency across 593+ affected files
- [ ] Test WebSocket factory pattern prevents singleton usage
- [ ] Ensure Golden Path (login → AI responses) remains stable

## Status Log
- **2025-09-10 Initial:** SSOT audit completed, critical violations identified
- **2025-09-10 Issue Created:** GitHub issue #212 created and committed  
- **2025-09-10 Test Discovery:** Found extensive WebSocket test ecosystem (80+ test files)

## Test Discovery Results

### Critical Test Categories Found:
1. **Mission Critical (12+ files):** Business-critical WebSocket functionality
2. **E2E Tests (50+ files):** End-to-end WebSocket integration 
3. **Integration Tests (15+ files):** Component integration validation
4. **Security Tests (5+ files):** WebSocket security and isolation
5. **Stress Tests (3+ files):** Performance and load validation

### Key Tests That MUST Pass Post-SSOT:
- `tests/mission_critical/test_websocket_agent_events_suite.py` ⚠️ (Line 47: direct import violation)
- `tests/mission_critical/test_websocket_singleton_vulnerability.py` ⭐ (Perfect SSOT test - line 59: get_websocket_manager!)
- `tests/mission_critical/test_websocket_bridge_critical_flows.py`
- `tests/mission_critical/test_websocket_comprehensive_validation.py`
- `tests/e2e/test_websocket_dev_docker_connection.py`

### CRITICAL Discovery: SSOT Violations in Test Files!
**Evidence Found:**
1. **test_websocket_agent_events_suite.py:47** - Direct import: `from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager`
2. **test_websocket_singleton_vulnerability.py:59** - Singleton import: `get_websocket_manager`
3. **test_websocket_singleton_vulnerability.py:114** - Singleton usage: `manager1 = get_websocket_manager()`

### SSOT Test Strategy (60% existing + 20% new + 20% validation)

#### Phase 1: EXISTING TEST UPDATES (60% - Critical)
- [ ] Update 80+ test files to use canonical imports: `from netra_backend.app.websocket_core.canonical_imports import`  
- [ ] Replace `get_websocket_manager()` calls with factory pattern
- [ ] Ensure all existing functionality tests continue to pass

#### Phase 2: NEW SSOT VALIDATION TESTS (20% - Detection)
- [ ] Create `test_websocket_import_ssot_compliance.py` - validates all imports use canonical pattern
- [ ] Create `test_websocket_factory_pattern_enforcement.py` - ensures no singleton usage  
- [ ] Create `test_websocket_user_isolation_validation.py` - validates multi-user security

#### Phase 3: SSOT ENFORCEMENT TESTS (20% - Prevention)
- [ ] Create tests that FAIL if legacy import patterns are reintroduced
- [ ] Create regression tests for singleton vulnerabilities
- [ ] Create import consistency validation across 593+ affected files

## Success Metrics
- Reduce WebSocket import violations from 593 files to <50 files
- Achieve 95%+ SSOT compliance for WebSocket components
- Maintain Golden Path stability throughout remediation