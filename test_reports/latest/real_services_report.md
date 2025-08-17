# Netra AI Platform - Test Report

**Generated:** 2025-08-16T20:23:21.752187  
**Test Level:** real_services - Tests requiring real external services (LLM, DB, Redis, ClickHouse)  
**Purpose:** Validation with actual service dependencies

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
| Backend   | 2 | 0 | 0 | 1 | 1 | 10.58s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** real_services
- **Description:** Tests requiring real external services (LLM, DB, Redis, ClickHouse)
- **Purpose:** Validation with actual service dependencies
- **Timeout:** 1800s
- **Coverage Enabled:** No
- **Total Duration:** 10.58s
- **Exit Code:** 1

### Backend Configuration
```
-m real_services -v --fail-fast
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
  pytest app/tests tests integration_tests -vv -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m real_services
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
[1mcollecting ... [0mcollected 4513 items / 1 error / 1 skipped

=================================== ERRORS ====================================
[31m[1m______________ ERROR collecting tests/test_real_data_services.py ______________[0m
'real_data' not found in `markers` configuration option
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m app\tests\test_real_data_services.py - Failed: 'real_data' not found in `markers` configuration option
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
[31m========================= [33m1 skipped[0m, [31m[1m1 error[0m[31m in 5.05s[0m[31m =========================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 1 after 9.61s
================================================================================

--- Logging error in Loguru Handler #7 ---
Record was: {'elapsed': datetime.timedelta(seconds=8, microseconds=171028), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='\u2139\ufe0f'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=41416, name='MainProcess'), 'thread': (id=1760, name='MainThread'), 'time': datetime(2025, 8, 16, 20, 23, 21, 11313, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}
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
- [31m[1m______________ ERROR collecting tests/test_real_data_services.py ______________[0m
- [31mERROR[0m app\tests\test_real_data_services.py - Failed: 'real_data' not found in `markers` configuration option
- [FAIL] TESTS FAILED with exit code 1 after 9.61s


---
*Generated by Netra AI Unified Test Runner v3.0*
