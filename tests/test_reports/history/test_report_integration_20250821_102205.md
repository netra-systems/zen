# Netra AI Platform - Test Report

**Generated:** 2025-08-21T10:20:48.965316  
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
| Backend   | 0 | 0 | 0 | 0 | 0 | 10.11s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.84s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 10.95s
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
  Coverage: enabled
  Fail Fast: enabled
  Environment: test

Running command:
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini integration_tests app/tests/routes -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services
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
[31m[1m
WARNING: Failed to generate report: No data to report.

[0m[31m[1m
ERROR: Coverage failure: total of 0.00 is less than fail-under=70.00
[0m
================================================================================
BAD TEST DETECTION REPORT
================================================================================

Total Bad Tests Detected: 0
Total Test Runs Analyzed: 16

================================================================================


=============================== tests coverage ================================
__________________________________ coverage ___________________________________

__________________________ coverage: failed workers ___________________________

The following workers failed to return coverage data, ensure that pytest-cov is installed on these workers.
gw0
gw1
gw2
gw3
[31m[1mFAIL Required test coverage of 70% not reached. Total coverage: 0.00%
[0m[33m============================ [33mno tests ran[0m[33m in 5.25s[0m[33m ============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 1 after 9.35s
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================

C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pytest_cov\plugin.py:358: CovReportWarning: Failed to generate report: No data to report.

  warnings.warn(CovReportWarning(message), stacklevel=1)
2025-08-21 10:20:41.565 | WARNING  | netra_backend.app.core.unified_logging:_emit_log:117 | Failed to load GCP secrets: 'SecretManager' object has no attribute 'load_all_secrets'

```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> node run-jest.js --config jest.config.simple.cjs --forceExit --detectOpenHandles --testMatch **/__tests__/integration/**/*.test.[jt]s?(x)


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
