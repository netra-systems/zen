# Netra AI Platform - Test Report

**Generated:** 2025-08-21T16:18:08.556451  
**Test Level:** smoke - Quick smoke tests for basic functionality (< 30 seconds)  

## 1. Test Summary

[FAILED] **OVERALL STATUS**

### Test Counts (Extracted from pytest output)
- **Total Tests:** 2
- **Passed:** 0 
- **Failed:** 0
- **Skipped:** 0
- **Errors:** 2

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 2 | 0 | 0 | 0 | 2 | 8.82s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## 3. Environment and Configuration

- **Test Level:** smoke
- **Description:** Quick smoke tests for basic functionality (< 30 seconds)
- **Purpose:** Pre-commit validation, basic health checks
- **Timeout:** 30s
- **Coverage Enabled:** Yes
- **Total Duration:** 8.82s
- **Exit Code:** 4

### Backend Configuration
```
--category smoke --fail-fast --coverage --markers not real_services
```

### Frontend Configuration
```

```

## 4. Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: smoke
  Parallel: disabled
  Coverage: disabled
  Fail Fast: enabled
  Environment: test

Running command:
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\pytest.ini netra_backend/tests/routes/test_health_route.py netra_backend/tests/core/test_error_handling.py::TestNetraExceptions::test_configuration_error netra_backend/tests/core/test_config_manager.py::TestConfigManager::test_initialization netra_backend/tests/services/test_security_service.py::test_encrypt_and_decrypt netra_backend/tests/e2e/test_system_startup.py::TestSystemStartup::test_configuration_loading -v -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m not real_services
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.5.3', 'langsmith': '0.4.15', 'asyncio': '1.1.0', 'cov': '6.2.1', 'mock': '3.14.1', 'xdist': '3.8.0', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'timeout': '2.4.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.5.3, langsmith-0.4.15, asyncio-1.1.0, cov-6.2.1, mock-3.14.1, xdist-3.8.0, html-4.1.1, json-report-1.5.0, metadata-3.1.1, timeout-2.4.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=session, asyncio_default_test_loop_scope=function
[1mcollecting ... [0mcollected 0 items / 2 errors

=================================== ERRORS ====================================
[31m[1m__________ ERROR collecting tests/services/test_security_service.py ___________[0m
[31mImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\services\test_security_service.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\..\miniconda3\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\tests\services\test_security_service.py:17: in <module>
    from schemas import AppConfig
E   ModuleNotFoundError: No module named 'schemas'[0m
[31m[1m________________________ ERROR collecting test session ________________________[0m
[1m[31m..\..\..\..\AppData\Roaming\Python\Python312\site-packages\pluggy\_hooks.py[0m:512: in __call__
    [0m[94mreturn[39;49;00m [96mself[39;49;00m._hookexec([96mself[39;49;00m.name, [96mself[39;49;00m._hookimpls.copy(), kwargs, firstresult)[90m[39;49;00m
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^[90m[39;49;00m
[1m[31m..\..\..\..\AppData\Roaming\Python\Python312\site-packages\pluggy\_manager.py[0m:120: in _hookexec
    [0m[94mreturn[39;49;00m [96mself[39;49;00m._inner_hookexec(hook_name, methods, kwargs, firstresult)[90m[39;49;00m
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^[90m[39;49;00m
[1m[31m..\..\..\..\AppData\Roaming\Python\Python312\site-packages\_pytest\main.py[0m:652: in pytest_collectstart
    [0m[94mraise[39;49;00m [96mself[39;49;00m.Failed([96mself[39;49;00m.shouldfail)[90m[39;49;00m
[1m[31mE   _pytest.main.Failed: stopping after 1 failures[0m
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m netra_backend\tests\services\test_security_service.py
[31mERROR[0m netra_backend - _pytest.main.Failed: stopping after 1 failures
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 2 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
[31m============================== [31m[1m2 errors[0m[31m in 0.95s[0m[31m ==============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 7.76s
================================================================================

ERROR: not found: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\core\test_config_manager.py::TestConfigManager::test_initialization
(no match in any of [<Module test_config_manager.py>])

ERROR: found no collectors for C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\services\test_security_service.py::test_encrypt_and_decrypt


```

### Frontend Output
```

```

## 5. Error Details

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m__________ ERROR collecting tests/services/test_security_service.py ___________[0m
- [31m[1m________________________ ERROR collecting test session ________________________[0m
- [31mERROR[0m netra_backend\tests\services\test_security_service.py
- [31mERROR[0m netra_backend - _pytest.main.Failed: stopping after 1 failures
- [FAIL] TESTS FAILED with exit code 4 after 7.76s
- ERROR: not found: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\core\test_config_manager.py::TestConfigManager::test_initialization
- ERROR: found no collectors for C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\services\test_security_service.py::test_encrypt_and_decrypt

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
