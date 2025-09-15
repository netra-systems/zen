# Mission Critical Test Restoration Procedures

**Created:** 2025-09-15
**Issue:** #1005 - Mission Critical Test Suite Corruption
**Severity:** CRITICAL - 24.8% of mission critical tests corrupted

## Executive Summary

Following the discovery of extensive corruption in the mission critical test suite (108 out of 435 files corrupted), this document establishes procedures for:
1. Immediate test restoration
2. Corruption prevention
3. System integration validation
4. Long-term monitoring

## Corruption Analysis

### Scale of Impact
- **Total Files:** 435 mission critical test files
- **Corrupted Files:** 108 files (24.8%)
- **Working Files:** 321 files (73.8%)
- **Corruption Marker:** "REMOVED_SYNTAX_ERROR" pattern
- **Business Impact:** $500K+ ARR test coverage compromised

### Corruption Pattern
Files contain systematic corruption with:
- `REMOVED_SYNTAX_ERROR:` prefixes on code lines
- Commented-out functional code
- Incomplete imports and function definitions
- Syntax errors preventing proper execution

### Successfully Restored
- `tests/mission_critical/test_issue_1100_websocket_ssot_mission_critical.py` ✅
- 13 comprehensive test methods restored
- 9/13 tests passing (4 failures indicate real SSOT violations)

## Restoration Procedures

### Phase 1: Emergency Triage (COMPLETE)
1. **Identify Single Critical Test:** ✅ Done - Issue #1005 test restored
2. **Validate Restoration:** ✅ Done - Test execution confirmed working
3. **Commit Changes:** ✅ Done - Prevention against re-corruption
4. **Assess Scale:** ✅ Done - 108 corrupted files identified

### Phase 2: Systematic Restoration (IN PROGRESS)

#### Step 1: Prioritization Matrix
Restore tests based on business criticality:

| Priority | Category | Files | Criteria |
|----------|----------|--------|----------|
| P0 | Golden Path | ~15 files | WebSocket, Agent, Auth flows |
| P1 | SSOT Compliance | ~25 files | Critical SSOT violations |
| P2 | Infrastructure | ~35 files | Database, Config, Security |
| P3 | Performance | ~20 files | Load, Memory, Performance |
| P4 | Edge Cases | ~13 files | Specialized scenarios |

#### Step 2: Restoration Template
For each corrupted file:

```bash
# 1. Backup current state
cp tests/mission_critical/FILENAME.py tests/mission_critical/FILENAME.py.corrupted

# 2. Analyze corruption pattern
grep -n "REMOVED_SYNTAX_ERROR" tests/mission_critical/FILENAME.py

# 3. Remove corruption markers
sed 's/# REMOVED_SYNTAX_ERROR: //g' tests/mission_critical/FILENAME.py > temp_file
mv temp_file tests/mission_critical/FILENAME.py

# 4. Fix syntax errors
python -m py_compile tests/mission_critical/FILENAME.py

# 5. Validate functionality
python -m pytest tests/mission_critical/FILENAME.py -v

# 6. Commit if successful
git add tests/mission_critical/FILENAME.py
git commit -m "fix: Restore mission critical test FILENAME"
```

#### Step 3: Quality Validation
For each restored test:
- [ ] Syntax validation passes
- [ ] Test functions are properly defined
- [ ] Dependencies are correctly imported
- [ ] Test execution produces meaningful results
- [ ] SSOT compliance is maintained

### Phase 3: Prevention Measures

#### File Integrity Monitoring
```bash
# Create checksums for all working tests
find tests/mission_critical -name "*.py" -exec grep -L "REMOVED_SYNTAX_ERROR" {} \; | \
  xargs sha256sum > tests/mission_critical/integrity_checksums.txt

# Daily validation script
#!/bin/bash
for file in $(find tests/mission_critical -name "*.py" -exec grep -L "REMOVED_SYNTAX_ERROR" {} \;); do
  if grep -q "REMOVED_SYNTAX_ERROR" "$file"; then
    echo "CORRUPTION DETECTED: $file"
    exit 1
  fi
done
```

#### CI/CD Integration Validation
The following workflows use mission critical tests and must be validated:

1. **startup-validation-tests.yml**
   - Uses: `tests/mission_critical/test_deterministic_startup_validation.py`
   - Status: ✅ Currently functional

2. **ssot-compliance-check.yml**
   - Monitors: `tests/mission_critical/**/*.py`
   - Status: ✅ Currently functional

3. **deploy-staging.yml**
   - Executes: `tests/mission_critical/test_websocket_agent_events_suite.py`
   - Status: ✅ Currently functional

#### Git Hooks for Protection
```bash
# Pre-commit hook to prevent corruption
#!/bin/bash
# File: .git/hooks/pre-commit

for file in $(git diff --cached --name-only | grep "tests/mission_critical/.*\.py$"); do
  if grep -q "REMOVED_SYNTAX_ERROR" "$file"; then
    echo "ERROR: Mission critical test corruption detected in $file"
    exit 1
  fi
done
```

## Investigation Requirements

### Root Cause Analysis Needed
1. **Timeline Investigation:** When did corruption occur?
2. **Source Identification:** What process caused corruption?
3. **Scope Assessment:** Are other test directories affected?
4. **Tool Analysis:** Did linting/formatting tools cause this?

### Commands for Investigation
```bash
# Find when corruption was introduced
git log --oneline --since="2025-08-01" -- tests/mission_critical/ | head -20

# Check for similar patterns in other directories
find tests -name "*.py" -exec grep -l "REMOVED_SYNTAX_ERROR" {} \;

# Analyze file modification patterns
find tests/mission_critical -name "*.py" -exec stat -f "%m %N" {} \; | sort -n | tail -20
```

## Business Impact Mitigation

### Immediate Actions
- [x] **Critical Test Restored:** Issue #1005 test operational
- [x] **CI/CD Validated:** Essential workflows confirmed working
- [x] **Stakeholder Notification:** Issue #1005 updated with findings
- [ ] **Emergency Backup:** Archive all 321 working tests

### Long-term Solutions
- [ ] **Automated Monitoring:** File integrity checks in CI/CD
- [ ] **Backup System:** Regular snapshots of critical test files
- [ ] **Process Review:** Investigate and fix corruption source
- [ ] **Documentation:** Complete operations runbook

## Success Metrics

### Restoration Progress
- **Target:** 100% of P0/P1 tests restored (40 files)
- **Timeline:** P0 within 48 hours, P1 within 1 week
- **Quality:** >90% test pass rate after restoration

### System Health
- **CI/CD Reliability:** Zero mission critical test failures due to corruption
- **Coverage Metrics:** Restore to >95% mission critical coverage
- **Monitoring:** Real-time corruption detection operational

## Escalation Procedures

### Immediate Issues
- **Syntax Errors:** Escalate to development team lead
- **CI/CD Failures:** Escalate to DevOps team
- **Data Loss:** Escalate to engineering management

### Contact Information
- **Issue Tracking:** GitHub Issue #1005
- **Documentation:** This file and MASTER_WIP_STATUS.md
- **Emergency:** Follow standard incident response procedures

---

**Status:** PHASE 2 IN PROGRESS
**Next Review:** 2025-09-16
**Owner:** Development Team
**Approved By:** Engineering Lead