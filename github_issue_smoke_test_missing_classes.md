# test-infrastructure-regression | P2 | Smoke Test Missing Class Definitions Blocking Test Discovery

## Impact
Smoke test infrastructure degraded with missing critical test classes preventing basic system validation. While not immediately blocking production, this represents systematic test infrastructure erosion affecting deployment confidence and quality gates.

## Current Behavior
Smoke test collection fails due to missing test class definitions:

```
tests/smoke/ - Missing test class definitions:
  - TestResourceManagement (expected in resource management smoke tests)
  - TestCorpusLifecycle (expected in corpus lifecycle smoke tests)

Collection Phase: FAILED
Test Discovery: 0 smoke tests found (expected: 10-15 tests)
```

**Collection Results:**
- ❌ **Missing TestResourceManagement class** (resource management validation blocked)
- ❌ **Missing TestCorpusLifecycle class** (corpus operations validation blocked)
- ⚠️ **0 smoke tests discovered** (complete smoke test coverage lost)
- 🚨 **Test framework regression** (systematic infrastructure degradation)

## Expected Behavior
Smoke tests should provide basic system validation coverage:
- ✅ TestResourceManagement class exists and contains resource validation tests
- ✅ TestCorpusLifecycle class exists and contains corpus operation tests
- ✅ Smoke test suite discovers and executes 10-15 basic validation tests
- ✅ Fast execution time (<30 seconds) for quick deployment validation

## Reproduction Steps
1. Execute smoke test collection:
   ```bash
   python tests/unified_test_runner.py --category smoke
   ```
2. Observe missing test class definitions during discovery
3. Verify 0 smoke tests collected (expected 10-15)
4. Check for TestResourceManagement and TestCorpusLifecycle classes

## Technical Details
- **Missing Classes:** `TestResourceManagement`, `TestCorpusLifecycle`
- **Expected Location:** `tests/smoke/` directory
- **Test Framework:** `tests/unified_test_runner.py`
- **Collection Result:** 0 tests discovered
- **Business Impact:** No basic system validation before deployments
- **Test Categories Affected:** Resource management, corpus lifecycle operations

## Root Cause Analysis
Based on test infrastructure investigation:

1. **Class Definition Removal:** TestResourceManagement and TestCorpusLifecycle classes deleted or relocated
2. **Smoke Test Framework Migration:** Recent test infrastructure changes may have removed smoke test implementations
3. **Import Path Changes:** Test classes may exist but not discoverable due to import/naming changes
4. **SSOT Consolidation Impact:** Test consolidation efforts may have inadvertently removed smoke test classes

## Business Risk Assessment
- **Priority:** P2 (Medium) - Not immediately blocking but reduces deployment confidence
- **Quality Gates:** No basic system validation before production releases
- **Deployment Risk:** Cannot quickly validate core resource and corpus operations
- **Development Velocity:** Longer feedback cycles without fast smoke test validation

## Proposed Resolution Strategy

### Phase 1: Investigation and Discovery (1-2 hours)
1. **Search for Missing Classes:**
   ```bash
   grep -r "TestResourceManagement" . --include="*.py"
   grep -r "TestCorpusLifecycle" . --include="*.py"
   find . -name "*smoke*" -type f
   ```

2. **Analyze Test Infrastructure Changes:**
   - Review recent commits affecting test infrastructure
   - Check SSOT consolidation changes that may have removed classes
   - Identify if classes were renamed or relocated

### Phase 2: Smoke Test Restoration (2-4 hours)
1. **Restore Missing Test Classes:**
   ```python
   # tests/smoke/test_resource_management.py
   class TestResourceManagement:
       def test_basic_resource_allocation(self):
           """Smoke test for basic resource management"""

   # tests/smoke/test_corpus_lifecycle.py
   class TestCorpusLifecycle:
       def test_corpus_creation_basic(self):
           """Smoke test for corpus creation flow"""
   ```

2. **Implement Basic Smoke Tests:**
   - Resource management: allocation, deallocation, basic operations
   - Corpus lifecycle: creation, deletion, basic CRUD operations
   - Integration with existing test framework patterns

### Phase 3: Validation and Integration (1-2 hours)
1. **Test Discovery Validation:**
   ```bash
   python tests/unified_test_runner.py --category smoke --collect-only
   ```

2. **Smoke Test Execution:**
   ```bash
   python tests/unified_test_runner.py --category smoke
   ```

3. **CI/CD Integration:**
   - Ensure smoke tests run in deployment pipeline
   - Add smoke test validation to deployment gates

## Implementation Plan

### TestResourceManagement Class
```python
class TestResourceManagement:
    """Smoke tests for resource management operations"""

    def test_resource_allocation_basic(self):
        """Verify basic resource allocation works"""

    def test_resource_cleanup_basic(self):
        """Verify basic resource cleanup works"""

    def test_resource_limits_respected(self):
        """Verify resource limits are enforced"""
```

### TestCorpusLifecycle Class
```python
class TestCorpusLifecycle:
    """Smoke tests for corpus lifecycle operations"""

    def test_corpus_creation_basic(self):
        """Verify basic corpus creation works"""

    def test_corpus_deletion_basic(self):
        """Verify basic corpus deletion works"""

    def test_corpus_access_basic(self):
        """Verify basic corpus access works"""
```

## Related Issues
- **Issue #596:** Unit test infrastructure improvements (positive progress model)
- **Test Infrastructure SSOT:** Check if smoke tests were consolidated elsewhere
- **Deployment Pipeline:** Smoke tests needed for quality gates

## Success Criteria
- ✅ TestResourceManagement class implemented with 3-5 basic tests
- ✅ TestCorpusLifecycle class implemented with 3-5 basic tests
- ✅ Smoke test discovery finds 10-15 tests
- ✅ Smoke test execution completes in <30 seconds
- ✅ CI/CD pipeline includes smoke test validation

## Monitoring and Prevention
1. **Test Class Monitoring:** Alert on missing expected test classes during collection
2. **Coverage Tracking:** Monitor smoke test coverage to prevent future regressions
3. **CI/CD Integration:** Fail builds if smoke test classes missing

---
🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>