# Netra AI Platform - Test Report

**Generated:** 2025-08-17T18:07:19.701599  
**Test Level:** real_e2e - [REAL E2E] Tests with actual LLM calls and services (15-20 minutes)  
**Purpose:** End-to-end validation with real LLM and service integrations

## Test Summary

**Total Tests:** 2  
**Passed:** 0  
**Failed:** 0  
**Skipped:** 1  
**Errors:** 1  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 2 | 0 | 0 | 1 | 1 | 25.35s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** real_e2e
- **Description:** [REAL E2E] Tests with actual LLM calls and services (15-20 minutes)
- **Purpose:** End-to-end validation with real LLM and service integrations
- **Timeout:** 3600s
- **Coverage Enabled:** No
- **Total Duration:** 25.35s
- **Exit Code:** 1

### Backend Configuration
```
-k real_ or _real -v --fail-fast
```

### Frontend Configuration
```

```

## Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: all
  Parallel: disabled
  Coverage: disabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests tests integration_tests -vv -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -k real_ or _real -p test_framework.pytest_bad_test_plugin --test-component backend
================================================================================
[BAD TEST DETECTOR] Initialized for backend tests
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
[1mcollecting ... [0mcollected 5364 items / 1 error / 1 skipped

================================================================================
BAD TEST DETECTION REPORT
================================================================================

Total Bad Tests Detected: 0
Total Test Runs Analyzed: 98

================================================================================


=================================== ERRORS ====================================
[31m[1m__________ ERROR collecting tests/unit/auth_service/test_helpers.py ___________[0m
[31mImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\unit\auth_service\test_helpers.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\..\miniconda3\Lib\site-packages\_pytest\python.py:498: in importtestmodule
    mod = import_path(
..\..\..\..\miniconda3\Lib\site-packages\_pytest\pathlib.py:587: in import_path
    importlib.import_module(module_name)
..\..\..\..\miniconda3\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen importlib._bootstrap>:1387: in _gcd_import
    ???
<frozen importlib._bootstrap>:1360: in _find_and_load
    ???
<frozen importlib._bootstrap>:1331: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:935: in _load_unlocked
    ???
..\..\..\..\miniconda3\Lib\site-packages\_pytest\assertion\rewrite.py:186: in exec_module
    exec(co, module.__dict__)
app\tests\unit\auth_service\test_helpers.py:15: in <module>
    from app.auth.url_validators import (
E   ImportError: cannot import name 'validate_return_url_security' from 'app.auth.url_validators' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\auth\url_validators.py)[0m
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m app\tests\unit\auth_service\test_helpers.py
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
[31m======================== [33m1 skipped[0m, [31m[1m1 error[0m[31m in 15.58s[0m[31m =========================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 1 after 23.84s
================================================================================

--- Logging error in Loguru Handler #7 ---
Record was: {'elapsed': datetime.timedelta(seconds=21, microseconds=177900), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='\u2139\ufe0f'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=2260, name='MainProcess'), 'thread': (id=17684, name='MainThread'), 'time': datetime(2025, 8, 17, 18, 7, 18, 476112, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}
Traceback (most recent call last):
  File "C:\Users\antho\miniconda3\Lib\site-packages\loguru\_handler.py", line 315, in _queued_writer
    self._sink.write(message)
  File "C:\Users\antho\miniconda3\Lib\site-packages\loguru\_simple_sinks.py", line 16, in write
    self._stream.write(message)
ValueError: I/O operation on closed file.
--- End of logging error ---

```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m__________ ERROR collecting tests/unit/auth_service/test_helpers.py ___________[0m
- [31mERROR[0m app\tests\unit\auth_service\test_helpers.py
- [FAIL] TESTS FAILED with exit code 1 after 23.84s


---
*Generated by Netra AI Unified Test Runner v3.0*
