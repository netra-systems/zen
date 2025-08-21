# Netra AI Platform - Test Report

**Generated:** 2025-08-21T10:12:01.037530  
**Test Level:** integration - Integration tests for component interaction (3-5 minutes)  

## 1. Test Summary

[FAILED] **OVERALL STATUS**

### Test Counts (Extracted from pytest output)
- **Total Tests:** 0
- **Passed:** 0 
- **Failed:** 0
- **Skipped:** 0
- **Errors:** 0

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 0 | 0 | 0 | 0 | 0 | 6.65s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.78s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 7.43s
- **Exit Code:** 5

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
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini integration_tests app/tests/routes -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m not real_services
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
4 workers [0 items]

scheduling tests via LoadScheduling

================================================================================
BAD TEST DETECTION REPORT
================================================================================

Total Bad Tests Detected: 0
Total Test Runs Analyzed: 13

================================================================================


[33m============================ [33mno tests ran[0m[33m in 3.51s[0m[33m ============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 5 after 6.10s
================================================================================


```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> node run-jest.js --config jest.config.simple.cjs --forceExit --detectOpenHandles --testMatch **/__tests__/integration/**/*.test.[jt]s?(x)

================================================================================
NETRA AI PLATFORM - FRONTEND TEST RUNNER
================================================================================

================================================================================
Running Jest Tests
--------------------------------------------------------------------------------
Running: npm run test -- --forceExit --detectOpenHandles --testMatch **/__tests__/integration/**/*.test.[jt]s?(x)
--------------------------------------------------------------------------------

================================================================================
[FAIL] CHECKS FAILED with exit code 1
================================================================================

Cleaning up test processes...

Error: Can't find a root directory while resolving a config file path.
Provided path to resolve: jest.config.simple.cjs
cwd: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend
    at resolveConfigPath (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend\node_modules\jest-config\build\index.js:2448:11)
    at readInitialOptions (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend\node_modules\jest-config\build\index.js:1138:55)
    at readConfig (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend\node_modules\jest-config\build\index.js:918:13)
    at readConfigs (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend\node_modules\jest-config\build\index.js:1168:32)
    at runCLI (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend\node_modules\@jest\core\build\index.js:1393:43)
    at Object.run (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\frontend\node_modules\jest-cli\build\index.js:656:34)

```

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
