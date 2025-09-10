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

- [ ] **Step 1: Discover and Plan Test**
  - [ ] Find existing tests protecting against breaking changes
  - [ ] Plan required test suites focused on ideal SSOT state

- [ ] **Step 2: Execute Test Plan** 
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

## Next Actions

1. Spawn sub-agent for Step 1: Discover existing tests and plan SSOT test strategy
2. Focus on tests that validate WebSocket database factory functionality
3. Plan tests for consolidated DatabaseManager SSOT patterns