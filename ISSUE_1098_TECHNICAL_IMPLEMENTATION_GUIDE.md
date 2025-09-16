# Issue #1098 Technical Implementation Guide: Atomic Factory Legacy Elimination

**Date**: September 15, 2025
**Purpose**: Detailed technical steps for implementing the remediation plan
**Constraint**: Use only existing SSOT methods, no new scripts
**Validation**: Phase 2 tests must pass after completion

## TECHNICAL PREREQUISITES

### 1. Verification Commands (Run First)
```bash
# Confirm current violation counts match Phase 2 evidence
python tests/unit/websocket_factory_legacy/test_factory_existence_validation.py
python tests/unit/websocket_factory_legacy/test_import_violations_detection.py

# Baseline Golden Path status
python tests/mission_critical/test_websocket_agent_events_suite.py
```

### 2. SSOT Pattern Reference
```python
# CANONICAL PATTERNS (TARGET STATE)
from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager
from netra_backend.app.websocket_core.manager import WebSocketManager  # Compatibility
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility
```

## PHASE 1: FILE SYSTEM CLEANUP (ATOMIC COMMIT 1)

### 1.1 Factory File Deletion (Atomic Operation)
```bash
# Navigate to project root
cd C:\netra-apex

# Verify files exist (should show 5 files)
ls -la netra_backend/app/websocket_core/websocket_manager_factory.py
ls -la netra_backend/app/factories/websocket_bridge_factory.py
ls -la netra_backend/app/services/websocket_bridge_factory.py
ls -la netra_backend/app/routes/websocket_factory.py
ls -la netra_backend/app/websocket_core/websocket_manager_factory_compat.py

# Delete factory files (one by one for safety)
rm netra_backend/app/websocket_core/websocket_manager_factory.py
rm netra_backend/app/factories/websocket_bridge_factory.py
rm netra_backend/app/services/websocket_bridge_factory.py
rm netra_backend/app/routes/websocket_factory.py
rm netra_backend/app/websocket_core/websocket_manager_factory_compat.py

# Verify deletion (should show "No such file or directory")
ls -la netra_backend/app/websocket_core/websocket_manager_factory.py
```

### 1.2 Backup File Cleanup
```bash
# Find and remove backup files
find . -name "*websocket*factory*.backup*" -type f
find . -name "*websocket*factory*.backup*" -type f -delete

find . -name "*websocket*factory*.ssot_elimination_backup" -type f
find . -name "*websocket*factory*.ssot_elimination_backup" -type f -delete
```

### 1.3 Cache File Cleanup
```bash
# Clear Python cache files
find . -path "*/__pycache__/*" -name "*websocket*factory*.pyc" -delete

# Force recompilation to clear any references
python -Bc "import py_compile; import os; [py_compile.compile(f, doraise=True) for f in []]"
```

### 1.4 Phase 1 Validation
```bash
# This should now pass (6/6 tests)
python tests/unit/websocket_factory_legacy/test_factory_existence_validation.py

# Verify Golden Path still works
python tests/mission_critical/test_websocket_agent_events_suite.py
```

### 1.5 Atomic Commit 1
```bash
git add -A
git commit -m "Phase 1: Complete WebSocket factory file elimination for Issue #1098

- Delete 5 factory files (1,582 lines removed)
- Clean backup files and Python cache
- Factory existence validation tests now pass
- Golden Path functionality preserved

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

## PHASE 2: IMPORT MIGRATION (ATOMIC COMMITS 2-3)

### 2.1 Critical File Analysis (Use Existing Tools)
```bash
# Use existing SSOT method to find violations
python scripts/query_string_literals.py search "websocket_manager_factory"
python scripts/query_string_literals.py search "websocket_bridge_factory"
python scripts/query_string_literals.py search "websocket_factory"
```

### 2.2 Critical Files Priority Order

#### 2.2.1 dependencies.py (26 violations - HIGHEST PRIORITY)
**Location**: `netra_backend/app/dependencies.py`

**BEFORE patterns to find:**
```python
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
```

**AFTER replacements (SSOT patterns):**
```python
from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager as WebSocketManager
# Replace create_websocket_manager() calls with WebSocketManager() direct instantiation
```

#### 2.2.2 routes/websocket.py (WebSocket endpoint)
**BEFORE patterns:**
```python
from netra_backend.app.routes.websocket_factory import get_websocket_manager
```

**AFTER replacements:**
```python
from netra_backend.app.websocket_core.manager import WebSocketManager
```

#### 2.2.3 Agent Files (Agent execution infrastructure)
**Common BEFORE patterns:**
```python
from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridge
from netra_backend.app.factories.websocket_bridge_factory import create_websocket_bridge
```

**AFTER replacements:**
```python
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as WebSocketBridge
```

### 2.3 Systematic Replacement Method

#### 2.3.1 Pattern Detection (Use Existing Grep)
```bash
# Find files with each pattern (use existing tools)
grep -r "from.*websocket_manager_factory" --include="*.py" .
grep -r "import.*websocket_manager_factory" --include="*.py" .
grep -r "from.*websocket.*factory" --include="*.py" .
grep -r "import.*websocket.*factory" --include="*.py" .
```

#### 2.3.2 File-by-File Replacement Strategy
For each file identified:

1. **Read the file** to understand context
2. **Apply SSOT pattern mapping**:
   ```python
   # MAPPING TABLE
   "websocket_manager_factory" → "netra_backend.app.websocket_core.canonical_import_patterns"
   "websocket_bridge_factory" → "netra_backend.app.websocket_core.unified_emitter"
   "websocket_factory" → "netra_backend.app.websocket_core.manager"
   ```
3. **Update function calls** to match new imports
4. **Test the change** locally

#### 2.3.3 Test Infrastructure Updates
**BEFORE (Factory test patterns):**
```python
from netra_backend.app.websocket_core.websocket_manager_factory import create_test_manager
```

**AFTER (SSOT test patterns):**
```python
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility
from netra_backend.app.websocket_core.canonical_import_patterns import create_test_user_context
```

### 2.4 Validation After Each Critical File
```bash
# After each critical file change
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/e2e/staging/test_staging_golden_path_ssot.py
```

### 2.5 Atomic Commit 2 (Critical Files)
```bash
git add netra_backend/app/dependencies.py netra_backend/app/routes/websocket.py [other critical files]
git commit -m "Phase 2A: Fix critical WebSocket factory imports for Issue #1098

- Update dependencies.py (26 factory violations → SSOT patterns)
- Update routes/websocket.py (WebSocket endpoint)
- Update core agent files (WebSocket bridge integration)
- Golden Path functionality maintained
- Mission critical tests pass

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 2.6 Systematic Migration (Remaining Files)
Apply the same pattern replacement to remaining files in logical groups:

**Group 1**: Agent files
**Group 2**: Test files (non-critical)
**Group 3**: Utility files
**Group 4**: Documentation files

### 2.7 Atomic Commit 3 (Systematic Migration)
```bash
git add -A
git commit -m "Phase 2B: Complete systematic WebSocket factory import migration for Issue #1098

- Fix remaining 515+ import violations across 290+ files
- Replace all factory patterns with SSOT canonical imports
- Update test infrastructure to use SSOT patterns
- Import violation detection tests now pass (0 violations)
- System stability maintained throughout migration

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

## PHASE 3: FINAL VALIDATION (ATOMIC COMMIT 4)

### 3.1 Complete Test Suite Validation
```bash
# Both test suites should now pass completely
python tests/unit/websocket_factory_legacy/test_factory_existence_validation.py  # 6/6 PASS
python tests/unit/websocket_factory_legacy/test_import_violations_detection.py   # 5/5 PASS

# Golden Path validation
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/e2e/staging/test_staging_golden_path_ssot.py
```

### 3.2 System Health Checks
```bash
# Architecture compliance check
python scripts/check_architecture_compliance.py

# SSOT compliance validation (should find 0 factory references)
python scripts/query_string_literals.py validate "websocket_factory"
python scripts/query_string_literals.py search "websocket_manager_factory"
```

### 3.3 Documentation Updates
```bash
# Update SSOT registry (remove factory mappings)
# Update string literals index
python scripts/scan_string_literals.py
```

### 3.4 Final Atomic Commit
```bash
git add -A
git commit -m "Phase 3: Complete Issue #1098 remediation validation and cleanup

- All Phase 2 tests now pass (factory existence + import violations)
- Golden Path functionality confirmed operational
- SSOT compliance achieved (0 factory violations)
- Documentation updated to reflect completed migration
- System ready for production deployment

Resolves Issue #1098: WebSocket Factory Legacy Elimination

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

## VALIDATION CHECKPOINTS

### After Phase 1 (File Deletion)
- [ ] 5 factory files deleted
- [ ] Factory existence tests: 6/6 PASS
- [ ] Golden Path: OPERATIONAL

### After Phase 2A (Critical Files)
- [ ] dependencies.py updated
- [ ] routes/websocket.py updated
- [ ] Mission critical tests: PASS

### After Phase 2B (Systematic Migration)
- [ ] Import violation tests: 5/5 PASS
- [ ] 0 factory import violations detected
- [ ] Golden Path: OPERATIONAL

### After Phase 3 (Final Validation)
- [ ] All validation tests: PASS
- [ ] SSOT compliance: ACHIEVED
- [ ] System health: EXCELLENT
- [ ] Production ready: CONFIRMED

## ROLLBACK PROCEDURES

If any phase fails:

1. **Identify failure point** using git log
2. **Rollback to previous commit**:
   ```bash
   git reset --hard HEAD~1  # Roll back one commit
   ```
3. **Investigate issue** using existing tools
4. **Fix underlying problem** before re-attempting
5. **Re-run validation** before proceeding

## SUCCESS METRICS

### Technical Metrics
- **Files Deleted**: 5 factory files (1,582 lines)
- **Violations Fixed**: 541 import violations
- **Files Updated**: 293 files with SSOT imports
- **Tests Passing**: 11/11 Phase 2 tests

### Business Metrics
- **Golden Path**: Maintained throughout
- **System Stability**: No breaking changes
- **SSOT Compliance**: Complete for WebSocket factories
- **Production Readiness**: Achieved

This technical implementation guide provides the specific steps needed to execute the comprehensive remediation plan using only existing SSOT methods and tools.