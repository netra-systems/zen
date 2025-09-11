# GitHub Issue: pytest-timeout Missing Dependency Causing Unit Test Failures

**Title:** `[BUG] pytest-timeout missing dependency causing unit test execution failures`

## Impact
Unit test execution fails during timeout scenarios, preventing reliable CI/CD pipeline execution and affecting $500K+ ARR golden path validation.

## Current Behavior
- Unit tests hang indefinitely when encountering timeout scenarios
- Bulk unit test execution hangs at 50.77s consistently  
- pytest-timeout configuration exists in pytest.ini (`--timeout=30`) but dependency is missing
- Individual test execution bypasses collection phase issues

## Expected Behavior
- Unit tests should timeout gracefully after 30 seconds as configured
- pytest-timeout should handle long-running tests properly
- CI/CD pipeline should complete reliably without hanging

## Reproduction Steps
1. Run bulk unit test execution: `python tests/unified_test_runner.py`
2. Tests hang at 50.77s mark
3. Check pytest configuration shows `--timeout=30` but pytest-timeout module not installed
4. Individual test files work: `pytest netra_backend/tests/unit/specific_test.py -v`

## Technical Details
- **File:** `netra_backend/pytest.ini:4` - Contains `--timeout=30` option
- **Root Cause:** pytest-timeout exists in `logs/requirements-dev.txt:5` but missing from main `requirements.txt`
- **Environment:** Local development and CI environments
- **Evidence:** 
  - `logs/requirements-dev.txt:5` contains `pytest-timeout>=2.1.0`
  - `requirements.txt` only has `pytest>=8.4.1` and `pytest-asyncio>=1.1.0` (lines 134-136)
  - No requirements-dev.txt in project root
- **Related Issues:** 
  - Documented in `BULK_UNIT_TEST_FAILURE_INVESTIGATION_REPORT.md`
  - Referenced in `TEST_REPRODUCTION_REPORT_ISSUE_128.md`

## Root Cause Analysis (Five Whys Method)
1. **Why do unit tests hang?** Tests with long asyncio.sleep() calls exceed timeout limits
2. **Why doesn't pytest timeout work?** pytest-timeout package is not accessible during normal installation
3. **Why isn't pytest-timeout accessible?** It exists in `logs/requirements-dev.txt` but missing from main `requirements.txt`
4. **Why wasn't this caught earlier?** Development environment may have manually installed it, bypassing the issue
5. **Why do we need centralized requirements?** To ensure consistent dependencies across all environments

## Evidence from Codebase
- `BULK_UNIT_TEST_FAILURE_INVESTIGATION_REPORT.md` - Documents systematic fixes including timeout issues
- Multiple tests contain excessive sleep durations (10-60 seconds)
- GitHub workflow `.github/workflows/startup-validation-tests.yml:55` installs pytest-timeout
- Configuration exists but dependency missing in main requirements

## Proposed Solution
1. **Immediate:** Add `pytest-timeout>=2.1.0` to main `requirements.txt` (Testing section)
2. **Alternative:** Create `requirements-dev.txt` in project root and reference existing `logs/requirements-dev.txt`
3. **Validation:** Run bulk unit test execution to confirm timeout behavior
4. **Long-term:** Establish max 5s limit for timeout simulation tests

## Business Value
- **Development Velocity:** Restore reliable CI/CD pipeline execution
- **Quality Assurance:** Enable proper timeout testing without hanging
- **Platform Stability:** Prevent deployment pipeline failures

## Files to Modify
**Option 1 (Recommended):**
- `requirements.txt` - Add `pytest-timeout>=2.1.0` to Testing section (after line 136)

**Option 2 (Alternative):**
- Create `requirements-dev.txt` in project root
- Copy content from `logs/requirements-dev.txt` or create symbolic link

## Testing Checklist
- [ ] pytest-timeout installed successfully
- [ ] Bulk unit test execution completes without hanging
- [ ] Timeout behavior preserved (tests still timeout as intended)  
- [ ] CI/CD pipeline validates timeout functionality
- [ ] No regression in individual test execution

## Priority: HIGH
This blocks reliable unit test execution and affects core development workflows.

---
**Related Documentation:**
- `BULK_UNIT_TEST_FAILURE_INVESTIGATION_REPORT.md`
- `TEST_REPRODUCTION_REPORT_ISSUE_128.md` 
- `PYTEST_MARKER_CONFIGURATION_BUG_FIX_REPORT.md`

**Labels:** `bug`, `high`, `testing`