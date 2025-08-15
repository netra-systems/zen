# Netra AI Platform - Test Report

**Generated:** 2025-08-15T14:49:36.801851  
**Test Level:** smoke - Quick smoke tests for basic functionality (< 30 seconds)  
**Purpose:** Pre-commit validation, basic health checks

## Test Summary

**Total Tests:** 7  
**Passed:** 7  
**Failed:** 0  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [PASSED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 7 | 7 | 0 | 0 | 0 | 5.91s | [PASSED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** smoke
- **Description:** Quick smoke tests for basic functionality (< 30 seconds)
- **Purpose:** Pre-commit validation, basic health checks
- **Timeout:** 30s
- **Coverage Enabled:** No
- **Total Duration:** 5.91s
- **Exit Code:** 0

### Backend Configuration
```
--category smoke --fail-fast --markers not real_services
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
  Category: smoke
  Parallel: disabled
  Coverage: disabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests/routes/test_health_route.py app/tests/core/test_error_handling.py::TestNetraExceptions::test_configuration_error app/tests/core/test_config_manager.py::TestConfigManager::test_initialization app/tests/services/test_security_service.py::test_encrypt_and_decrypt tests/test_system_startup.py::TestSystemStartup::test_configuration_loading -v -x --maxfail=1 -m not real_services --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
[1mcollecting ... [0mcollected 7 items

app/tests/routes/test_health_route.py::test_basic_import [32mPASSED[0m[32m          [ 14%][0m
app/tests/routes/test_health_route.py::test_health_endpoint_direct [32mPASSED[0m[32m [ 28%][0m
app/tests/routes/test_health_route.py::test_live_endpoint [32mPASSED[0m[32m         [ 42%][0m
app/tests/core/test_error_handling.py::TestNetraExceptions::test_configuration_error [32mPASSED[0m[32m [ 57%][0m
app/tests/core/test_config_manager.py::TestConfigManager::test_initialization [32mPASSED[0m[32m [ 71%][0m
app/tests/services/test_security_service.py::test_encrypt_and_decrypt [32mPASSED[0m[32m [ 85%][0m
tests/test_system_startup.py::TestSystemStartup::test_configuration_loading [32mPASSED[0m[32m [100%][0m

[32m============================== [32m[1m7 passed[0m[32m in 0.24s[0m[32m ==============================[0m
================================================================================
[PASS] ALL TESTS PASSED in 5.14s
================================================================================

--- Logging error in Loguru Handler #1 ---
Record was: {'elapsed': datetime.timedelta(seconds=3, microseconds=395017), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='\u2139\ufe0f'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=40372, name='MainProcess'), 'thread': (id=8792, name='MainThread'), 'time': datetime(2025, 8, 15, 14, 49, 36, 190852, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}
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
---
*Generated by Netra AI Unified Test Runner v3.0*
