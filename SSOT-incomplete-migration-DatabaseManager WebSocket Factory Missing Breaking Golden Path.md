# SSOT Incomplete Migration: DatabaseManager WebSocket Factory Missing Breaking Golden Path

**GitHub Issue:** [#204](https://github.com/netra-systems/netra-apex/issues/204)  
**Created:** 2025-09-10  
**Status:** DISCOVERY PHASE  
**Priority:** CRITICAL - Blocks complete golden path user flow  

## Issue Summary

WebSocket connections fail completely due to missing `get_db_session_factory` function, blocking $500K+ ARR chat functionality. Users cannot establish WebSocket connections required for AI responses.

## SSOT Violations Discovered

### 1. CRITICAL: Missing `get_db_session_factory` Function
- **File:** `/netra_backend/app/db/session.py` (function missing entirely)
- **Impact:** WebSocket connections fail with ImportError
- **Golden Path Block:** Complete - users cannot login → AI chat flow

### 2. HIGH: Duplicate DatabaseManager Classes  
- **Files:**
  - `/netra_backend/app/db/database_manager.py` (SSOT - Line 40)
  - `/netra_backend/app/database/__init__.py` (Duplicate - Line 173)  
  - `/auth_service/auth_core/database/database_manager.py` (Service variant)
- **Impact:** Inconsistent database access, connection pool conflicts

### 3. HIGH: Circular Import Dependencies
- **Files:** session.py ↔ database_manager.py ↔ database/__init__.py  
- **Impact:** Module initialization failures, WebSocket factory issues

## Process Progress

- [x] **Step 0: SSOT Audit** - COMPLETED
  - [x] Discovered TOP 3 critical DatabaseManager SSOT violations
  - [x] Created GitHub issue #204
  - [x] Created progress tracker file

- [x] **Step 1: Discover and Plan Test** - COMPLETED
  - [x] Found existing tests protecting against breaking changes (458+ test files)
  - [x] Planned required test suites focused on ideal SSOT state
  - [x] Identified gaps in SSOT validation testing
  - [x] Created comprehensive test strategy for ~20% new tests

- [x] **Step 2: Execute Test Plan** - COMPLETED
  - [x] Created 4 new mission-critical test files reproducing SSOT violations
  - [x] All tests inherit from SSOT framework (SSotBaseTestCase)
  - [x] Tests validate GitHub Issue #204 exact error reproduction
  - [x] Test execution verified - properly detect SSOT violations

- [ ] **Step 3: Plan Remediation**
- [ ] **Step 4: Execute Remediation**  
- [ ] **Step 5: Test Fix Loop**
- [ ] **Step 6: PR and Closure**

## Current Findings

**Immediate Remediation Required:**
1. **Fix missing `get_db_session_factory`** (Blocks all WebSocket chat)
2. **Consolidate duplicate DatabaseManager classes** (Fix auth/connection issues)
3. **Resolve circular import dependencies** (Prevent startup failures)

**Evidence of Impact:**
```python
# WebSocket import failures:
"cannot import name 'get_db_session_factory' from 'netra_backend.app.db.session'"

# Multiple DatabaseManager implementations:
- Main: database_manager.py (Lines 40-362) - Uses DatabaseURLBuilder  
- Database module: database/__init__.py (Lines 173-207) - Uses get_engine()
- Auth service: Different interface entirely
```

## Test Discovery Results (Step 1)

### Existing Test Coverage (1.1)
- **458+ test files** mention DatabaseManager
- **Key Infrastructure Tests:**
  - Database session integration tests (existing)
  - WebSocket database integration with REAL services
  - Request-scoped session factory tests
  - Mission critical database session isolation
  - Memory leak prevention for database sessions

### Test Gaps Identified (1.2)
- ❌ **NO TESTS** validate that `get_db_session_factory` should not exist
- ❌ **NO TESTS** verify only ONE DatabaseManager implementation exists
- ❌ **NO TESTS** detect circular import dependencies

### New Test Plan (~20% New Tests)
**4 New Test Files Planned:**
1. `test_database_ssot_function_violations.py` - Missing function detection tests
2. `test_database_manager_ssot_consolidation.py` - SSOT consolidation validation  
3. `test_database_import_dependency_resolution.py` - Import/dependency resolution
4. `test_database_golden_path_session_factory.py` - Golden path validation

**Test Strategy:**
- **Pre-SSOT:** Tests FAIL (reproduce current violations)
- **Post-SSOT:** Tests PASS (validate remediated state)
- **Integration:** Build on existing SSOT test framework
- **Execution:** No Docker required - unit/integration/staging e2e only

### Success Criteria
**Pre-Refactor (Must FAIL):**
- Import of `get_db_session_factory` fails with ImportError ❌
- Multiple DatabaseManager implementations detected ❌
- WebSocket factory creation blocked by missing function ❌

**Post-Refactor (Must PASS):**
- Single DatabaseManager implementation accessible ✅
- WebSocket factory creates database sessions successfully ✅
- Golden path: user login → database session → AI responses works ✅

## Test Files Created (Step 2)

**4 New Mission-Critical Test Files:**
1. **`test_database_ssot_function_violations.py`** - Missing function detection  
   - Reproduces exact GitHub Issue #204 error
   - Tests WebSocket factory failures with missing `get_db_session_factory`
   - Validates replacement function `get_database_manager` works

2. **`test_database_manager_ssot_consolidation.py`** - SSOT consolidation validation
   - Detects duplicate DatabaseManager implementations across 3 locations
   - AST-based codebase scanning for import consistency
   - Validates single source after SSOT remediation

3. **`test_database_import_dependency_resolution.py`** - Import/dependency resolution
   - Custom directed graph implementation for circular dependency detection
   - WebSocket factory import resolution validation
   - Startup sequence database initialization order testing

4. **`test_database_golden_path_session_factory.py`** - Golden path validation
   - Async WebSocket manager database session creation tests
   - User login database session flow validation
   - Agent execution database access testing

**Test Execution Commands:**
```bash
# Run all DatabaseManager SSOT tests
python -m pytest tests/mission_critical/test_database_* -v

# Run specific violation reproduction
python -m pytest tests/mission_critical/test_database_ssot_function_violations.py
```

**Status:** All tests pass collection and reproduce SSOT violations as designed ✅

## Next Actions

1. **CURRENT STEP:** Plan SSOT remediation strategy
2. Focus on fixing missing `get_db_session_factory` function first (blocks WebSocket)
3. Plan consolidation of duplicate DatabaseManager classes