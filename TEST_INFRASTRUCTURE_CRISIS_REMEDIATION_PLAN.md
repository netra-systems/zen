# Test Infrastructure Crisis Remediation Plan

**Date:** 2025-09-17
**Priority:** P0 - Business Critical
**Impact:** 339 corrupted test files blocking Golden Path validation

## Executive Summary

Based on comprehensive analysis, the test infrastructure crisis stems from automated refactoring that introduced systematic corruption patterns:

1. **"formatted_string" placeholders** replacing proper f-strings
2. **Syntax errors** with unmatched braces `}`, parentheses mismatch
3. **Indentation errors** from malformed code transformations
4. **Encoding issues** (charmap codec errors)

**Business Impact:** Cannot validate Golden Path user flow (login → AI responses), preventing $500K+ ARR protection.

## Root Cause Analysis (Five Whys)

1. **Why are 339 test files corrupted?** → Automated refactoring introduced systematic syntax errors
2. **Why did automated refactoring corrupt files?** → String replacement patterns were too broad and replaced valid code with placeholders
3. **Why weren't these caught immediately?** → Test collection failures weren't properly distinguished from actual test failures
4. **Why did the corruption spread to so many files?** → Bulk refactoring tools operated on entire codebase without validation
5. **Why wasn't there rollback protection?** → Backups exist but restoration process unclear

## Corruption Pattern Analysis

### Primary Patterns Identified:
1. **"formatted_string" Substitution:**
   ```python
   # Corrupted:
   response = client.get("formatted_string")

   # Should be:
   response = client.get(f"/oauth/callback?state={state}&code={code}")
   ```

2. **Unmatched Braces/Parentheses:**
   ```python
   # Corrupted:
   json=}
   custom_env = }
   connection_params = { )

   # Should be:
   json={"key": "value"}
   custom_env = {"STAGING": "true"}
   connection_params = {"host": "localhost"}
   ```

3. **Indentation Errors:**
   ```python
   # Corrupted (unexpected unindent/indent):
   def test_function():
       assert True
   assert False  # Wrong indentation

   # Should be:
   def test_function():
       assert True
       assert False
   ```

## Phase 1: Golden Path Critical Tests (Priority 1)

### Target Files (5-10 maximum for immediate fix):

**Auth Service Critical:**
- `auth_service/tests/test_oauth_state_validation.py` ✅ EXISTS
- `auth_service/tests/test_auth_comprehensive.py` ✅ EXISTS
- `auth_service/tests/test_redis_staging_connectivity_fixes.py` ✅ EXISTS

**WebSocket Agent Events Critical:**
- `tests/mission_critical/test_websocket_agent_events_suite.py` ⚠️ MISSING
- `tests/e2e/golden_path/test_websocket_agent_events_validation.py` ⚠️ MISSING

**Alternative WebSocket Tests (that exist):**
- Search for actual existing WebSocket tests in `/c/netra-apex/tests/mission_critical/` that contain "websocket" and "agent"

### Automated Fix Script Strategy

```python
# fix_test_corruption.py - Automated Pattern Fixes

import re
import os
import ast
from pathlib import Path

CORRUPTION_PATTERNS = {
    # Pattern 1: formatted_string replacement
    r'"formatted_string"': lambda match, context: restore_formatted_string(context),

    # Pattern 2: Unmatched braces
    r'json=\}': 'json={}',
    r'custom_env = \}': 'custom_env = {}',
    r'connection_params = \{ \)': 'connection_params = {}',

    # Pattern 3: Missing quotes in dictionary values
    r'{\s*(\w+):\s*(\w+)\s*}': r'{\1: "\2"}',

    # Pattern 4: Fix common OAuth callback patterns
    r'client\.get\("formatted_string"\)': restore_oauth_callback,
}

def restore_formatted_string(context):
    """Restore formatted strings based on context"""
    if 'oauth' in context and 'callback' in context:
        return f'client.get(f"/oauth/callback?state={{state}}&code={{code}}")'
    elif 'auth' in context and 'login' in context:
        return f'client.post("/auth/login", json={{"email": "test@example.com"}})'
    # Add more context-specific restorations
    return '"RESTORE_NEEDED"'  # Flag for manual review

def fix_file_corruption(file_path):
    """Fix corruption patterns in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Apply automated fixes
        fixed_content = content
        for pattern, replacement in CORRUPTION_PATTERNS.items():
            if callable(replacement):
                # Context-aware replacement
                fixed_content = pattern_replace_with_context(fixed_content, pattern, replacement)
            else:
                # Simple string replacement
                fixed_content = re.sub(pattern, replacement, fixed_content)

        # Validate syntax before writing
        try:
            ast.parse(fixed_content)

            # Create backup before fixing
            backup_path = f"{file_path}.backup_corruption_fix"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Write fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)

            return True, "Fixed successfully"
        except SyntaxError as e:
            return False, f"Syntax error after fix: {e}"

    except Exception as e:
        return False, f"Error processing file: {e}"
```

### Manual Fix Requirements

**Complex Cases Needing Manual Intervention:**
1. **Context-dependent formatted strings** where automated restoration is ambiguous
2. **Multi-line corruption** spanning function definitions
3. **Import statement corruption** affecting module structure
4. **Test fixture corruption** requiring domain knowledge

### Validation Strategy

```bash
# Validation Pipeline
1. Syntax Check: python -m py_compile [file]
2. Import Check: python -c "import [module]"
3. Test Collection: python -m pytest --collect-only [file]
4. Basic Execution: python -m pytest [file] --maxfail=1
```

## Phase 2: WebSocket and Agent Tests

### Target Directory: `/c/netra-apex/tests/mission_critical/`
Focus on files containing both "websocket" and "agent" in filename.

### Specific Corruption Fixes:
- Restore WebSocket event delivery validation
- Fix agent message handler tests
- Repair WebSocket auth integration tests

## Phase 3: Integration Tests

### Target Directories:
- `/c/netra-apex/tests/integration/`
- `/c/netra-apex/netra_backend/tests/integration/`
- `/c/netra-apex/auth_service/tests/integration/`

## Phase 4: Unit Tests

**Lower priority** - Focus on files with highest business impact first.

## Service Startup Plan

### Backend Service (Port 8000)
**Issue:** Import conflicts preventing startup (Issue #1308)
```bash
# Resolution steps:
1. Fix SessionManager SSOT violations
2. Resolve cross-service import dependencies
3. Update configuration (JWT_SECRET vs JWT_SECRET_KEY)
4. Start service: python -m netra_backend.main
```

### Auth Service (Port 8081)
**Issue:** JWT configuration drift
```bash
# Resolution steps:
1. Align JWT_SECRET_KEY configuration
2. Fix Redis connectivity for staging
3. Start service: python -m auth_service.main
```

## Risk Mitigation Strategies

### 1. Backup Protection
- ✅ Backups exist in `/c/netra-apex/backups/`
- Create additional backup before any fixes: `cp -r tests tests_backup_20250917`

### 2. Incremental Validation
- Fix 1 file → Test → Validate → Next file
- Never fix more than 5 files without validation

### 3. Rollback Strategy
```bash
# Quick rollback if fixes fail:
git stash  # Stash current changes
git checkout HEAD~1  # Go back one commit
# Or restore from backups:
cp -r backups/test_remediation_20250915_224946/system_snapshot/tests .
```

### 4. Success Criteria

**Phase 1 Success (Golden Path):**
- [ ] 5+ critical test files have valid syntax
- [ ] Test collection succeeds for critical files
- [ ] Auth service starts on port 8081
- [ ] Backend service starts on port 8000
- [ ] Basic Golden Path test execution succeeds

**Phase 2 Success (WebSocket):**
- [ ] WebSocket agent event tests collect successfully
- [ ] 5 critical WebSocket events can be validated
- [ ] Agent message handling tests execute

**Phase 3 Success (Integration):**
- [ ] Integration test collection improves >50%
- [ ] Service-to-service communication tests work

**Phase 4 Success (Complete):**
- [ ] <50 corrupted files remaining (down from 339)
- [ ] Test collection success rate >90%
- [ ] Golden Path e2e test passes

## Execution Timeline

**Day 1 (Today):**
- Phase 1: Fix 5 Golden Path critical tests
- Start backend and auth services
- Validate basic Golden Path functionality

**Day 2:**
- Phase 2: Fix WebSocket agent event tests
- Restore WebSocket event validation capability

**Day 3:**
- Phase 3: Fix integration tests
- Validate service communication

**Day 4:**
- Phase 4: Fix remaining unit tests
- Complete system validation

## Monitoring and Validation

### Real-time Validation Commands:
```bash
# Quick syntax check:
find tests -name "*.py" -exec python -m py_compile {} \; 2>&1 | wc -l

# Test collection health:
python tests/unified_test_runner.py --collect-only --quiet

# Golden Path validation:
python tests/mission_critical/test_websocket_agent_events_suite.py  # When fixed

# Service health:
curl http://localhost:8000/health
curl http://localhost:8081/health
```

### Success Metrics:
- **Syntax Errors:** Reduce from 339 to <50
- **Test Collection:** Improve from <1% to >90%
- **Golden Path:** User login → AI response flow validated
- **Service Uptime:** Both auth and backend services operational

---

**Next Actions:**
1. ✅ Create automated fix script for common patterns
2. ✅ Identify 5 Golden Path critical files to fix first
3. ✅ Start with auth service test files (they exist and are critical)
4. ✅ Fix backend/auth service startup issues
5. ✅ Validate fixes incrementally

**Business Priority:** Getting Golden Path working is worth ANY technical debt - focus on minimal fixes to enable user login → AI responses flow validation.