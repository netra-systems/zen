# GitHub Issue: ImportError TestCorpusLifecycle class not found after rename

## Issue Summary

**ImportError in ClickHouse tests:** `cannot import name 'TestCorpusLifecycle' from 'netra_backend.tests.clickhouse.test_corpus_lifecycle'`

**Root Cause:** Class `TestCorpusLifecycle` was renamed to `CorpusLifecycleTests` in commit `c3e5934cb` but the import statements were not updated accordingly.

## Affected Files

### Primary Import Error
- **File:** `netra_backend/tests/clickhouse/test_corpus_generation_coverage_index.py:20-22`
- **Error:** Attempting to import non-existent `TestCorpusLifecycle` and `TestWorkloadTypesCoverage`

### Source File Changes
- **File:** `netra_backend/tests/clickhouse/test_corpus_lifecycle.py`
- **Change:** `TestCorpusLifecycle` → `CorpusLifecycleTests`
- **Change:** `TestWorkloadTypesCoverage` → `WorkloadTypesCoverageTests`

## Error Details

```python
# Current failing import in test_corpus_generation_coverage_index.py:20-22
from netra_backend.tests.clickhouse.test_corpus_lifecycle import (
    TestCorpusLifecycle,        # ❌ Class no longer exists
    TestWorkloadTypesCoverage,  # ❌ Class no longer exists
)
```

```bash
ImportError: cannot import name 'TestCorpusLifecycle' from 'netra_backend.tests.clickhouse.test_corpus_lifecycle' (C:\netra-apex\netra_backend\tests\clickhouse\test_corpus_lifecycle.py)
```

## Expected Behavior

Import statements should reference the correct renamed classes:

```python
# Fixed import should be:
from netra_backend.tests.clickhouse.test_corpus_lifecycle import (
    CorpusLifecycleTests as TestCorpusLifecycle,         # ✅ Correct class name with alias
    WorkloadTypesCoverageTests as TestWorkloadTypesCoverage, # ✅ Correct class name with alias
)
```

## Impact Analysis

**Severity:** Medium
**Component:** Test Infrastructure
**Business Impact:** ClickHouse test execution failures affecting SSOT compliance validation

**Affected Test Categories:**
- ClickHouse corpus lifecycle tests
- Test coverage index validation
- SSOT compliance test runs

## Root Cause Analysis

**Commit Analysis:**
- **Commit:** `c3e5934cb` with message "a"
- **Change Type:** Class renaming as part of SSOT compliance effort
- **Missing Step:** Import statements in dependent files were not updated

**Why This Happened:**
1. Bulk renaming operation for SSOT compliance
2. Import dependencies not tracked/updated systematically
3. No automated import validation in CI pipeline

## Reproduction Steps

```bash
# 1. Attempt to import the old class name
python -c "from netra_backend.tests.clickhouse.test_corpus_lifecycle import TestCorpusLifecycle"

# 2. Run the failing test file
python -m pytest netra_backend/tests/clickhouse/test_corpus_generation_coverage_index.py -v

# 3. Check current class names in source file
grep "^class.*:" netra_backend/tests/clickhouse/test_corpus_lifecycle.py
```

## Proposed Solution

### Option 1: Update Import with Aliases (Recommended)
Maintain backward compatibility while using new class names:

```python
from netra_backend.tests.clickhouse.test_corpus_lifecycle import (
    CorpusLifecycleTests as TestCorpusLifecycle,
    WorkloadTypesCoverageTests as TestWorkloadTypesCoverage,
)
```

### Option 2: Direct Import Update
Update to use new class names directly:

```python
from netra_backend.tests.clickhouse.test_corpus_lifecycle import (
    CorpusLifecycleTests as TestBatchProcessing,
    WorkloadTypesCoverageTests as TestContentGeneration,
)
```

## Validation Plan

1. **Fix Import:** Update import statements in `test_corpus_generation_coverage_index.py`
2. **Test Execution:** Verify ClickHouse tests run successfully
3. **SSOT Compliance:** Run `python scripts/check_architecture_compliance.py`
4. **Regression Check:** Execute full test suite to ensure no other import dependencies

## Additional Context

**SSOT Migration Context:** This appears to be part of the ongoing SSOT (Single Source of Truth) compliance effort where test class names are being standardized for architectural consistency.

**Related Files to Check:**
- Other files that might import from `test_corpus_lifecycle.py`
- Similar import patterns in the codebase that might need updating

## Labels
- `bug` - Import error preventing test execution
- `test-infrastructure` - Affects test framework
- `ssot-compliance` - Related to SSOT architectural migration
- `medium-priority` - Non-blocking but affects test reliability

## Definition of Done
- [ ] Import statements updated and working
- [ ] ClickHouse tests execute successfully
- [ ] No new import errors introduced
- [ ] SSOT compliance maintained
- [ ] Full test suite passes

---

🤖 **Generated with [Claude Code](https://claude.ai/code)**

**Co-Authored-By:** Claude <noreply@anthropic.com>