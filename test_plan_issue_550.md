# Test Plan: Issue #550 - test_framework Module Import Failures

## Executive Summary

**Issue:** Direct Python execution of test files fails with `ModuleNotFoundError: No module named 'test_framework'` when developers try to run tests in isolation for debugging purposes.

**Root Cause:** Direct Python execution doesn't automatically apply pytest's `pythonpath` configuration from `pyproject.toml`, breaking the import path resolution.

**Business Impact:** Blocks Golden Path E2E auth test development workflow, affecting $500K+ ARR validation processes.

## Test Strategy

### Phase 1: Reproduction Tests (Must Fail Initially)
Create comprehensive tests that reproduce the current import failure scenarios to establish baseline behavior.

### Phase 2: Solution Validation Tests  
Test multiple solution approaches and validate they work across different scenarios.

### Phase 3: Regression Prevention Tests
Ensure fixes don't break existing workflows and maintain compatibility.

## Test Categories

### 1. Direct Python Execution Tests (Category: Reproduction)

**Test Files to Create:**
- `tests/infrastructure/test_direct_python_execution_imports.py`
- `tests/infrastructure/test_test_framework_import_resolution.py`

**Test Scenarios:**
```python
# Test 1: Current Failure Scenario
def test_direct_python_execution_fails_without_pythonpath():
    """Reproduces the ModuleNotFoundError when running test files directly"""
    # Execute: python tests/e2e/test_golden_path_auth_e2e.py
    # Expected: ModuleNotFoundError: No module named 'test_framework'
    
# Test 2: Different Directory Context Failure  
def test_import_fails_from_subdirectory():
    """Test import failure when executed from different directories"""
    # Execute from tests/e2e/: python test_golden_path_auth_e2e.py
    # Expected: ModuleNotFoundError
    
# Test 3: sys.path Context
def test_sys_path_missing_project_root():
    """Verify project root not in sys.path during direct execution"""
    # Expected: Project root path not found in sys.path
```

### 2. pytest Configuration Tests (Category: Integration)

**Test Files to Create:**
- `tests/infrastructure/test_pytest_pythonpath_configuration.py`

**Test Scenarios:**
```python
# Test 1: pyproject.toml Configuration
def test_pytest_pythonpath_configured():
    """Verify pyproject.toml has correct pythonpath setting"""
    # Expected: pythonpath = ["."] in [tool.pytest.ini_options]
    
# Test 2: pytest Import Resolution
def test_pytest_resolves_test_framework_imports():
    """Verify pytest can resolve test_framework imports"""
    # Execute: python -m pytest tests/e2e/test_golden_path_auth_e2e.py::TestGoldenPathAuthE2E --collect-only
    # Expected: No import errors during collection
```

### 3. Solution Approach Tests (Category: Integration)

**Test Files to Create:**
- `tests/infrastructure/test_sys_path_modification_solutions.py`
- `tests/infrastructure/test_developer_workflow_solutions.py`

**Test Scenarios:**

#### Approach 1: sys.path Modification
```python
def test_sys_path_insert_fixes_imports():
    """Test sys.path.insert(0, project_root) solution"""
    # Pattern: sys.path.insert(0, str(Path(__file__).parent.parent))
    
def test_unified_test_runner_pattern():
    """Validate unified test runner's path setup approach"""
    # Test pattern from lines 8-10 of unified_test_runner.py
```

#### Approach 2: PYTHONPATH Environment Variable
```python  
def test_pythonpath_environment_variable():
    """Test PYTHONPATH=. solution"""
    # Execute: PYTHONPATH=. python tests/e2e/test_golden_path_auth_e2e.py
    # Expected: Import success
    
def test_developer_workaround_validates():
    """Confirm current workaround still works"""
    # Current working solution from issue description
```

#### Approach 3: Test File Modifications
```python
def test_modified_imports_in_test_files():
    """Test adding sys.path modification to test files directly"""
    # Add boilerplate to beginning of test files
```

### 4. Golden Path E2E Auth Tests Validation (Category: E2E)

**Test Files to Create:**
- `tests/infrastructure/test_golden_path_auth_accessibility.py`

**Test Scenarios:**
```python
def test_all_affected_files_executable():
    """Verify all affected Golden Path auth test files can execute"""
    affected_files = [
        "tests/e2e/test_golden_path_auth_e2e.py",
        "tests/e2e/test_authentication_golden_path_complete.py", 
        "tests/e2e/golden_path/test_websocket_auth_service_integration_e2e.py",
        "tests/mission_critical/test_golden_path_websocket_authentication.py"
    ]
    # Execute each file directly, expect success after fix

def test_developer_debugging_workflow():
    """Validate developers can run individual tests for debugging"""
    # Test isolated test execution for development iteration
```

### 5. Cross-Environment Compatibility Tests (Category: Integration)

**Test Files to Create:**
- `tests/infrastructure/test_cross_environment_import_compatibility.py`

**Test Scenarios:**
```python
def test_import_resolution_all_environments():
    """Test import resolution works in development, CI, and staging"""
    
def test_unified_test_runner_still_works():
    """Ensure unified test runner continues working after fixes"""
    # Execute: python tests/unified_test_runner.py --category e2e --pattern "golden_path_auth"
    
def test_pytest_execution_still_works():
    """Ensure direct pytest execution continues working"""
    # Execute: python -m pytest tests/e2e/test_golden_path_auth_e2e.py
```

## Test Execution Methodology

### Execution Environment
- **No Docker Required**: All tests run as unit/integration level
- **Python Path Setup**: Tests validate path configuration behavior
- **Real Import Testing**: Use actual import statements, not mocks

### Test Execution Commands

**Phase 1 - Reproduction Tests (Should Fail Initially):**
```bash
# These MUST fail before fixes are applied
python tests/infrastructure/test_direct_python_execution_imports.py
python tests/infrastructure/test_test_framework_import_resolution.py

# Manual reproduction commands
python tests/e2e/test_golden_path_auth_e2e.py  # Should fail
cd tests/e2e && python test_golden_path_auth_e2e.py  # Should fail
```

**Phase 2 - Solution Validation (Should Pass After Fixes):**
```bash
# Test sys.path modification approach
python tests/infrastructure/test_sys_path_modification_solutions.py

# Test PYTHONPATH approach  
PYTHONPATH=. python tests/e2e/test_golden_path_auth_e2e.py  # Should work

# Test pytest configuration
python -m pytest tests/infrastructure/test_pytest_pythonpath_configuration.py
```

**Phase 3 - Regression Prevention:**
```bash
# Ensure existing workflows continue working
python tests/unified_test_runner.py --category e2e --pattern "golden_path_auth"
python -m pytest tests/e2e/test_golden_path_auth_e2e.py
```

## Solution Implementation Recommendations

### Primary Solution: Test File Boilerplate
Add path setup boilerplate to the beginning of all test files (similar to unified_test_runner.py):

```python
#!/usr/bin/env python
import sys
from pathlib import Path

# Setup path for test_framework imports
PROJECT_ROOT = Path(__file__).parent.parent.absolute()  # Adjust parent count based on file location
sys.path.insert(0, str(PROJECT_ROOT))

# Now safe to import test_framework modules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
```

### Secondary Solutions:
1. **Developer Documentation**: Update testing guide with PYTHONPATH workaround
2. **IDE Configuration**: Provide setup instructions for development environments
3. **Script Wrapper**: Create wrapper script for direct test execution

## Success Criteria

### Phase 1 Completion (Reproduction):
- [ ] All reproduction tests fail as expected (proving the issue exists)
- [ ] Manual reproduction commands demonstrate the exact error
- [ ] Test coverage includes all affected Golden Path auth files

### Phase 2 Completion (Solution Validation):
- [ ] All affected test files can execute directly without PYTHONPATH workaround
- [ ] Developer debugging workflow restored (isolated test execution works)
- [ ] pytest execution continues working normally  
- [ ] unified_test_runner continues working normally

### Phase 3 Completion (Regression Prevention):
- [ ] All existing test execution patterns continue working
- [ ] CI/CD pipeline unaffected by changes
- [ ] No performance degradation in test discovery or execution

## Test Documentation

### Test Execution Report Template:
```markdown
## Test Execution Results - Issue #550

### Environment:
- OS: [macOS/Linux/Windows]
- Python Version: [3.x.x]
- Project Root: [absolute path]

### Phase 1 - Reproduction (Before Fix):
- test_direct_python_execution_fails_without_pythonpath: [PASS/FAIL - Should FAIL]
- Manual reproduction: [PASS/FAIL - Should FAIL]

### Phase 2 - Solution Validation (After Fix):  
- test_sys_path_insert_fixes_imports: [PASS/FAIL - Should PASS]
- Manual execution: [PASS/FAIL - Should PASS]

### Phase 3 - Regression Prevention:
- pytest execution: [PASS/FAIL - Should PASS]
- unified_test_runner execution: [PASS/FAIL - Should PASS]
```

## Risk Assessment

### Low Risk:
- Adding sys.path modification to test files (follows established pattern)
- pytest configuration already correct

### Medium Risk:
- Path setup differences between development environments
- Test file modifications might affect IDE behavior

### Mitigation Strategies:
- Test across multiple environments (macOS, Linux, Windows)
- Validate with different Python versions (3.9, 3.10, 3.11)
- Ensure backwards compatibility with existing workflows

---

**Test Plan Created:** 2025-09-13  
**Issue Priority:** P1 (High) - Blocks Golden Path development workflow  
**Expected Implementation Time:** 2-4 hours  
**Validation Time:** 1-2 hours