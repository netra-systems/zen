# Netra AI Platform - Test Report

**Generated:** 2025-08-15T23:52:10.097356  
**Test Level:** smoke - Quick smoke tests for basic functionality (< 30 seconds)  
**Purpose:** Pre-commit validation, basic health checks

## Test Summary

**Total Tests:** 2  
**Passed:** 1  
**Failed:** 1  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 2 | 1 | 1 | 0 | 0 | 7.51s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** smoke
- **Description:** Quick smoke tests for basic functionality (< 30 seconds)
- **Purpose:** Pre-commit validation, basic health checks
- **Timeout:** 30s
- **Coverage Enabled:** No
- **Total Duration:** 7.51s
- **Exit Code:** 1

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
  pytest app/tests/routes/test_health_route.py app/tests/core/test_error_handling.py::TestNetraExceptions::test_configuration_error app/tests/core/test_config_manager.py::TestConfigManager::test_initialization app/tests/services/test_security_service.py::test_encrypt_and_decrypt tests/test_system_startup.py::TestSystemStartup::test_configuration_loading -v -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m not real_services
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
app/tests/routes/test_health_route.py::test_health_endpoint_direct [31mFAILED[0m[31m [ 28%][0m

================================== FAILURES ===================================
[31m[1m_________________________ test_health_endpoint_direct _________________________[0m
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\antho\miniconda3\Lib\site-packages\starlette\_utils.py", line 77, in collapse_excgroups
  |     yield
  |   File "C:\Users\antho\miniconda3\Lib\site-packages\starlette\middleware\base.py", line 183, in __call__
  |     async with anyio.create_task_group() as task_group:
  |   File "C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\anyio\_backends\_asyncio.py", line 772, in __aexit__
  |     raise BaseExceptionGroup(
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\runner.py", line 344, in from_call
    |     result: TResult | None = func()
    |                              ^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\runner.py", line 246, in <lambda>
    |     lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\logging.py", line 850, in pytest_runtest_call
    |     yield
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\capture.py", line 900, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 53, in run_old_style_hookwrapper
    |     return result.get_result()
    |            ^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_result.py", line 103, in get_result
    |     raise exc.with_traceback(tb)
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 38, in run_old_style_hookwrapper
    |     res = yield
    |           ^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 53, in run_old_style_hookwrapper
    |     return result.get_result()
    |            ^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_result.py", line 103, in get_result
    |     raise exc.with_traceback(tb)
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 38, in run_old_style_hookwrapper
    |     res = yield
    |           ^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\skipping.py", line 263, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |           ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\runner.py", line 178, in pytest_runtest_call
    |     item.runtest()
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\python.py", line 1671, in runtest
    |     self.ihook.pytest_pyfunc_call(pyfuncitem=self)
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 53, in run_old_style_hookwrapper
    |     return result.get_result()
    |            ^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_result.py", line 103, in get_result
    |     raise exc.with_traceback(tb)
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 38, in run_old_style_hookwrapper
    |     res = yield
    |           ^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |           ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\python.py", line 157, in pytest_pyfunc_call
    |     result = testfunction(**testargs)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\routes\test_health_route.py", line 40, in test_health_endpoint_direct
    |     response = client.get("/health/live")
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\starlette\testclient.py", line 479, in get
    |     return super().get(
    |            ^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\httpx\_client.py", line 1053, in get
    |     return self.request(
    |            ^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\starlette\testclient.py", line 451, in request
    |     return super().request(
    |            ^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\httpx\_client.py", line 825, in request
    |     return self.send(request, auth=auth, follow_redirects=follow_redirects)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\httpx\_client.py", line 914, in send
    |     response = self._send_handling_auth(
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\httpx\_client.py", line 942, in _send_handling_auth
    |     response = self._send_handling_redirects(
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\antho\miniconda3\Lib\site-packages\httpx\_client.py", line 979, in _send_handling_redirects
    |     response = self._send_single_request(request)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\U...(truncated)
```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- app/tests/routes/test_health_route.py::test_health_endpoint_direct [31mFAILED[0m[31m [ 28%][0m
- 2025-08-15 23:52:08.448 | ERROR    | app.core.error_handlers:_handle_unknown_exception:222 | Unhandled exception: 'NoneType' object has no attribute 'encode'
- [31mFAILED[0m app/tests/routes/test_health_route.py::[1mtest_health_endpoint_direct[0m - AttributeError: 'NoneType' object has no attribute 'encode'
- [FAIL] TESTS FAILED with exit code 1 after 6.72s


---
*Generated by Netra AI Unified Test Runner v3.0*
