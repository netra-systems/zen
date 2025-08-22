# Netra AI Platform - Test Report

**Generated:** 2025-08-21T12:12:51.735793  
**Test Level:** integration - Integration tests for component interaction (3-5 minutes)  

## 1. Test Summary

[FAILED] **OVERALL STATUS**

### Test Counts (Extracted from pytest output)
- **Total Tests:** 4
- **Passed:** 0 
- **Failed:** 0
- **Skipped:** 0
- **Errors:** 4

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 4 | 0 | 0 | 0 | 4 | 16.86s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 19.16s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 36.02s
- **Exit Code:** 15

### Backend Configuration
```
--category integration -v --coverage --fail-fast --parallel=4 --markers not real_services
```

### Frontend Configuration
```
--category integration
```

## 4. Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: integration
  Parallel: 4
  Coverage: disabled
  Fail Fast: enabled
  Environment: test

Running command:
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini netra_backend/tests/integration netra_backend/tests/routes -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m not real_services
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.5.3', 'asyncio': '1.1.0', 'cov': '6.2.1', 'mock': '3.14.1', 'xdist': '3.8.0', 'langsmith': '0.4.10', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'timeout': '2.4.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.5.3, asyncio-1.1.0, cov-6.2.1, mock-3.14.1, xdist-3.8.0, langsmith-0.4.10, html-4.1.1, json-report-1.5.0, metadata-3.1.1, timeout-2.4.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
created: 4/4 workers

================================================================================
BAD TEST DETECTION REPORT
================================================================================

Total Bad Tests Detected: 0
Total Test Runs Analyzed: 127

================================================================================


=================================== ERRORS ====================================
[31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py _[0m
'l2_integration' not found in `markers` configuration option
[31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py _[0m
'l2_integration' not found in `markers` configuration option
[31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py _[0m
'l2_integration' not found in `markers` configuration option
[31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py _[0m
'l2_integration' not found in `markers` configuration option
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py - Failed: 'l2_integration' not found in `markers` configuration option
[31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py - Failed: 'l2_integration' not found in `markers` configuration option
[31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py - Failed: 'l2_integration' not found in `markers` configuration option
[31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py - Failed: 'l2_integration' not found in `markers` configuration option
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 4 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m============================== [31m[1m4 errors[0m[31m in 9.23s[0m[31m ==============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 15.76s
================================================================================

C:\Users\antho\miniconda3\Lib\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataSample" shadows an attribute in parent "BaseModel"
  warnings.warn(
C:\Users\antho\miniconda3\Lib\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataCatalog" shadows an attribute in parent "BaseModel"
  warnings.warn(

```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> node run-jest.js --config jest.config.simple.cjs --forceExit --detectOpenHandles --testMatch **/__tests__/integration/**/*.test.[jt]s?(x)



```

## 5. Error Details

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py _[0m
- [31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py _[0m
- [31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py _[0m
- [31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py _[0m
- [31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py - Failed: 'l2_integration' not found in `markers` configuration option
- [31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py - Failed: 'l2_integration' not found in `markers` configuration option
- [31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py - Failed: 'l2_integration' not found in `markers` configuration option
- [31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_audit_trail.py - Failed: 'l2_integration' not found in `markers` configuration option
- [FAIL] TESTS FAILED with exit code 2 after 15.76s

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
