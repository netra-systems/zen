# SSOT-incomplete-migration-websocket-factory-deprecation-blocking-golden-path

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/989

## Work Progress Tracker

### Step 0: SSOT AUDIT ✅ COMPLETED
**Status:** COMPLETED - Critical SSOT violation identified

**Findings:**
- **Critical Pattern:** `get_websocket_manager_factory()` deprecated function still actively exported through canonical_imports.py
- **Impact:** Blocks Golden Path (users login → AI responses) due to multiple WebSocket initialization patterns
- **Files Affected:**
  - `netra_backend/app/websocket_core/websocket_manager_factory.py` (deprecated compatibility layer)
  - `netra_backend/app/websocket_core/canonical_imports.py` (re-exports deprecated patterns)
  - Multiple test files validating deprecated instead of SSOT patterns

**Business Impact:** $500K+ ARR at risk due to potential race conditions and user isolation failures

### Step 1: DISCOVER AND PLAN TEST
**Status:** PENDING

**Discovered Tests:** TBD
**Test Plan:** TBD

### Step 2: EXECUTE TEST PLAN
**Status:** PENDING

### Step 3: PLAN REMEDIATION
**Status:** PENDING

### Step 4: EXECUTE REMEDIATION
**Status:** PENDING

### Step 5: TEST FIX LOOP
**Status:** PENDING

### Step 6: PR AND CLOSURE
**Status:** PENDING

---

## Technical Analysis

### Current Violation Details
1. **Deprecated Export**: `canonical_imports.py` line 34 imports and exports `get_websocket_manager_factory`
2. **Multiple Patterns**: Both deprecated factory pattern and SSOT direct instantiation coexist
3. **Test Infrastructure**: Tests validate deprecated patterns instead of ensuring they're removed

### SSOT Target State
- Remove all references to `get_websocket_manager_factory` from canonical exports
- Migrate all usage to direct `WebSocketManager(user_context=context)` instantiation
- Update test infrastructure to validate SSOT compliance only

### Migration Strategy
1. **Phase 1**: Remove deprecated exports from canonical_imports.py
2. **Phase 2**: Update any remaining production code to use SSOT patterns
3. **Phase 3**: Update tests to validate SSOT compliance rather than deprecated compatibility
4. **Phase 4**: Remove deprecated functions from websocket_manager_factory.py

---

*This file tracks the complete SSOT gardener process for Issue #989*