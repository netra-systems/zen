# Issue #1210: Comprehensive Remediation Plan for extra_headers → additional_headers Migration

**EXECUTIVE SUMMARY:** Complete migration plan to fix 161 Python files using deprecated `extra_headers` parameter to use `additional_headers` for Python 3.13 websockets compatibility.

**BUSINESS IMPACT:** Critical for $500K+ ARR Golden Path WebSocket functionality - prevents runtime failures and ensures Python 3.13 compatibility.

---

## IMMEDIATE PROBLEM

**Root Cause:** The failing test `tests/e2e_staging/test_golden_path_websocket_events.py` uses deprecated `extra_headers` parameter in websockets.connect() calls, which causes:
```
TypeError: connect() got an unexpected keyword argument 'extra_headers'
```

**Scope:** 161 Python files across the entire codebase require migration.

---

## PHASE 1: IMMEDIATE FIX (Mission Critical)

### 1.1 Fix Failing Test File
**Target:** `/Users/anthony/Desktop/netra-apex/tests/e2e_staging/test_golden_path_websocket_events.py`

**Changes Required:**
- Line 135: `extra_headers={"Authorization": f"Bearer {auth_token}"}`
- Line 372: `extra_headers={"Authorization": f"Bearer {auth_token}"}`  
- Line 446: `extra_headers={"Authorization": f"Bearer {auth_token}"}`

**Action:**
```python
# OLD (deprecated):
async with websockets.connect(
    f"{STAGING_WS_URL}",
    extra_headers={"Authorization": f"Bearer {auth_token}"}
) as websocket:

# NEW (Python 3.13 compatible):
async with websockets.connect(
    f"{STAGING_WS_URL}",
    additional_headers={"Authorization": f"Bearer {auth_token}"}
) as websocket:
```

### 1.2 Fix Critical Test Framework File
**Target:** `/Users/anthony/Desktop/netra-apex/test_framework/ssot/websocket.py`

**Changes Required:**
- Line 313: `"extra_headers": test_headers,`

**Action:**
```python
# OLD:
connection_params = {
    "extra_headers": test_headers,
    "ping_interval": 20,
    "ping_timeout": 10,
    "close_timeout": 10
}

# NEW:
connection_params = {
    "additional_headers": test_headers,
    "ping_interval": 20,
    "ping_timeout": 10,
    "close_timeout": 10
}
```

### 1.3 Immediate Validation
```bash
# Test the specific failing file
python -m pytest tests/e2e_staging/test_golden_path_websocket_events.py -v

# Verify no immediate regressions
python tests/unified_test_runner.py --category e2e --fast-fail
```

---

## PHASE 2: SYSTEMATIC REMEDIATION (Complete Migration)

### 2.1 Search and Replace Strategy

**Step 1: Identify All Affected Files**
```bash
# Find all project files (excluding virtual environments)
find /Users/anthony/Desktop/netra-apex -path "*/.venv" -prune -o -path "*/venv" -prune -o -path "*/.test_venv" -prune -o -path "*/backup" -prune -o -path "*/google-cloud-sdk" -prune -o -name "*.py" -type f -exec grep -l "extra_headers" {} \;
```

**Step 2: Pattern Analysis**
Common patterns to replace:
1. `extra_headers=` → `additional_headers=`
2. `"extra_headers":` → `"additional_headers":`
3. `'extra_headers':` → `'additional_headers':`

### 2.2 Automated Fix Script

**Create Migration Script:**
```python
#!/usr/bin/env python3
"""
Issue #1210: extra_headers → additional_headers migration script
Systematically updates all WebSocket parameter usage
"""

import os
import re
import sys
from pathlib import Path

def migrate_file(file_path):
    """Migrate a single file from extra_headers to additional_headers"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace all patterns
        patterns = [
            (r'\bextra_headers\s*=', 'additional_headers='),
            (r'"extra_headers"\s*:', '"additional_headers":'),
            (r"'extra_headers'\s*:", "'additional_headers':"),
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Migrated: {file_path}")
            return True
        else:
            print(f"⏭️  No changes: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error migrating {file_path}: {e}")
        return False

def main():
    """Run migration on all affected files"""
    project_root = Path(__file__).parent
    
    # Find all affected Python files
    cmd = [
        'find', str(project_root),
        '-path', '*/.venv', '-prune', '-o',
        '-path', '*/venv', '-prune', '-o', 
        '-path', '*/.test_venv', '-prune', '-o',
        '-path', '*/backup', '-prune', '-o',
        '-path', '*/google-cloud-sdk', '-prune', '-o',
        '-name', '*.py', '-type', 'f',
        '-exec', 'grep', '-l', 'extra_headers', '{}', ';'
    ]
    
    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error finding files: {result.stderr}")
        return 1
    
    files = result.stdout.strip().split('\n')
    files = [f for f in files if f.strip()]  # Remove empty lines
    
    print(f"Found {len(files)} files to migrate")
    
    migrated_count = 0
    for file_path in files:
        if migrate_file(file_path):
            migrated_count += 1
    
    print(f"\n✅ Migration complete: {migrated_count}/{len(files)} files updated")
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

### 2.3 Batch Processing Strategy

**Priority Order:**
1. **Mission Critical Tests** (tests/mission_critical/, tests/e2e_staging/)
2. **Test Framework** (test_framework/)
3. **E2E Tests** (tests/e2e/)
4. **Integration Tests** (tests/integration/)
5. **Backend Tests** (netra_backend/tests/)
6. **Scripts** (scripts/)
7. **Other Test Files** (tests/)

**Processing Command:**
```bash
# Run migration script
python issue_1210_migration_script.py

# Verify changes with git diff
git diff --stat
```

---

## PHASE 3: VALIDATION AND SAFETY

### 3.1 Automated Testing Validation

**Test Execution Strategy:**
```bash
# 1. Test mission critical functionality first
python tests/mission_critical/test_websocket_agent_events_suite.py

# 2. Test the originally failing file
python -m pytest tests/e2e_staging/test_golden_path_websocket_events.py -v

# 3. Run WebSocket-specific tests
python tests/unified_test_runner.py --category integration --pattern "*websocket*" --fast-fail

# 4. Full E2E test suite
python tests/unified_test_runner.py --category e2e --real-services --execution-mode nightly

# 5. Staging environment validation
python -m pytest tests/e2e/staging/ -v
```

### 3.2 Regression Prevention

**Pre-Commit Validation:**
```bash
# Create validation script
cat > validate_websocket_params.py << 'EOF'
#!/usr/bin/env python3
"""Validate no extra_headers usage remains in codebase"""
import subprocess
import sys

def check_extra_headers():
    cmd = [
        'find', '.',
        '-path', '*/.venv', '-prune', '-o',
        '-path', '*/venv', '-prune', '-o', 
        '-path', '*/.test_venv', '-prune', '-o',
        '-path', '*/backup', '-prune', '-o',
        '-name', '*.py', '-type', 'f',
        '-exec', 'grep', '-n', 'extra_headers', '{}', ';'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0 and result.stdout.strip():
        print("❌ Found remaining extra_headers usage:")
        print(result.stdout)
        return 1
    else:
        print("✅ No extra_headers usage found - migration complete")
        return 0

if __name__ == '__main__':
    sys.exit(check_extra_headers())
EOF

python validate_websocket_params.py
```

### 3.3 Staging Environment Validation

**Critical Staging Tests:**
```bash
# Test Golden Path functionality
python -m pytest tests/e2e_staging/test_golden_path_websocket_events.py

# Test WebSocket authentication flows
python -m pytest tests/integration/staging_auth/ -v

# Test multi-user WebSocket isolation
python -m pytest tests/e2e/websocket/ -k "staging" -v
```

---

## PHASE 4: ROLLBACK AND RECOVERY

### 4.1 Rollback Strategy

**Git Preparation:**
```bash
# Create branch for changes
git checkout -b issue-1210-websocket-parameter-migration
git add .
git commit -m "Issue #1210: Migrate extra_headers to additional_headers for Python 3.13 compatibility

- Updated 161 Python files with deprecated extra_headers parameter
- Changed all websockets.connect() calls to use additional_headers
- Maintains backward compatibility with websockets library
- Ensures Python 3.13 compatibility for $500K+ ARR WebSocket functionality

🤖 Generated with Claude Code"
```

**Rollback Commands:**
```bash
# If issues are discovered, immediate rollback
git checkout develop-long-lived
git branch -D issue-1210-websocket-parameter-migration

# Alternative: revert specific files
git checkout HEAD~1 -- tests/e2e_staging/test_golden_path_websocket_events.py
```

### 4.2 Safety Checkpoints

**Checkpoint 1: After Phase 1 (Mission Critical)**
```bash
# Verify core functionality works
python tests/mission_critical/test_websocket_agent_events_suite.py
```

**Checkpoint 2: After Phase 2 (Full Migration)**
```bash
# Verify no breaking changes
python tests/unified_test_runner.py --categories smoke unit integration --fast-fail
```

**Checkpoint 3: Before Production (Final Validation)**
```bash
# Complete staging validation
python tests/unified_test_runner.py --category e2e --env staging --real-services
```

---

## SUCCESS CRITERIA

### Immediate Success (Phase 1)
- [ ] `tests/e2e_staging/test_golden_path_websocket_events.py` passes without parameter errors
- [ ] No `extra_headers` parameter errors in mission-critical tests
- [ ] WebSocket authentication flows work in staging environment

### Complete Success (All Phases)
- [ ] All 161 identified files successfully migrated
- [ ] Zero `extra_headers` usage remaining in project Python files
- [ ] All WebSocket tests passing with `additional_headers`
- [ ] Staging environment fully functional
- [ ] No regression in Golden Path WebSocket functionality
- [ ] Python 3.13 compatibility verified

### Business Value Validation
- [ ] $500K+ ARR Golden Path chat functionality operational
- [ ] WebSocket events delivered correctly for all users
- [ ] Multi-user isolation maintained
- [ ] Real-time agent communication working
- [ ] No customer-facing WebSocket failures

---

## MONITORING AND METRICS

### Technical Metrics
- **Files Migrated:** Target 161/161 (100%)
- **Test Success Rate:** Maintain >95% WebSocket test success
- **Parameter Validation:** 0 remaining `extra_headers` usage
- **Staging Health:** All staging WebSocket tests passing

### Business Metrics  
- **Golden Path Success Rate:** Maintain 100% chat initiation success
- **WebSocket Connection Success:** >99% connection establishment rate
- **Event Delivery:** 100% critical WebSocket events delivered
- **User Experience:** No degradation in real-time responsiveness

---

## TIMELINE

**Phase 1 (Mission Critical):** 30 minutes
- Fix failing test file
- Fix test framework file
- Immediate validation

**Phase 2 (Full Migration):** 2 hours
- Create and run migration script
- Batch process all 161 files
- Git commit changes

**Phase 3 (Validation):** 1 hour
- Run comprehensive test suites
- Staging environment validation
- Regression testing

**Phase 4 (Monitoring):** Ongoing
- Post-deployment monitoring
- Success criteria validation
- Performance tracking

**Total Estimated Time:** 3.5 hours for complete remediation

---

## RISK MITIGATION

### High-Risk Areas
1. **Test Framework Changes:** Could break multiple test suites
   - **Mitigation:** Test framework changes first, validate immediately
2. **Staging Environment:** Production-like environment failures
   - **Mitigation:** Stage-by-stage validation with rollback ready
3. **Mass File Changes:** Potential for introduction of syntax errors
   - **Mitigation:** Automated script with error handling and validation

### Low-Risk Areas
1. **Parameter Name Change:** Simple string replacement
2. **Websockets Library:** Well-documented parameter migration
3. **Backward Compatibility:** No functional logic changes required

---

This comprehensive remediation plan ensures systematic, safe migration of all `extra_headers` usage to `additional_headers`, maintaining business value while achieving Python 3.13 compatibility.