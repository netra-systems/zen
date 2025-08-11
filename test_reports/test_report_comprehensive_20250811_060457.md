# Netra AI Platform - Test Report

**Generated:** 2025-08-11T06:04:57.491174  
**Test Level:** comprehensive - Full test suite with coverage (10-15 minutes)  
**Purpose:** Pre-release validation, full system testing

## Summary

| Component | Status | Duration | Exit Code |
|-----------|--------|----------|-----------|
| Backend   | [FAILED] | 142.30s | 1 |
| Frontend  | [FAILED] | 0.13s | 1 |

**Overall Status:** [FAILED]  
**Total Duration:** 142.43s  
**Final Exit Code:** 1

## Test Level Details

- **Description:** Full test suite with coverage (10-15 minutes)
- **Purpose:** Pre-release validation, full system testing
- **Timeout:** 900s
- **Coverage Enabled:** Yes

## Configuration

### Backend Args
```
--coverage --parallel=auto --html-output
```

### Frontend Args  
```
--coverage
```

## Test Output

### Backend Output
```
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: all
  Parallel: auto
  Coverage: enabled
  Fail Fast: disabled
  Environment: testing

Running command:
  pytest app/tests tests integration_tests -v -n auto --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 --html=reports/tests/report.html --self-contained-html --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.3.2, pluggy-1.5.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.3.2', 'pluggy': '1.5.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '1.1.0', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-1.1.0, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
created: 14/14 workers
[gw0] node down: Traceback (most recent call last):
  File "C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\_pytest\config\__init__.py", line 710, in _importconftest
    mod = import_path(
          ^^^^^^^^^^^^
  File "C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\_pytest\pathlib.py", line 582, in import_path
    importlib.import_module(module_name)
  File "C:\Users\antho\miniconda3\Lib\importlib\__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\_pytest\assertion\rewrite.py", line 174, in exec_module
    exec(co, module.__dict__)
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\conftest.py", line 37, in <module>
    from app.main import app
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\main.py", line 296, in <module>
    from app.routes import supply, generation, admin, references, health, corpus, synthetic_data, config, demo, unified_tools
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\routes\unified_tools.py", line 7, in <module>
    from app.db.postgres import get_db
ImportError: cannot import name 'get_db' from 'app.db.postgres' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\db\postgres.py)

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "C:\Users\antho\miniconda3\Lib\site-packages\execnet\gateway_base.py", line 1291, in executetask
    exec(co, loc)
  File "C:\Users\antho\miniconda3\Lib\site-packages\xdist\remote.py", line 420, in <module>
    config = _prepareconfig(args, None)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\_pytest\config\__init__.py", line 341, in _prepareconfig
    config = pluginmanager.hook.pytest_cmdline_parse(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pluggy\_hooks.py", line 513, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pluggy\_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pluggy\_callers.py", line 139, in _multicall
    raise exception.with_traceback(exception.__traceback__)
  File "C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pluggy\_callers.py", line 122, in _multicall
    teardown.throw(exception)  # type: ignore[union-at...(truncated)
```

### Frontend Output
```
================================================================================
NETRA AI PLATFORM - FRONTEND TEST RUNNER
================================================================================

================================================================================
Running Jest Tests
--------------------------------------------------------------------------------
Running: npm run test -- --coverage --coverageDirectory=../reports/frontend-coverage
--------------------------------------------------------------------------------

Traceback (most recent call last):
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\scripts\test_frontend.py", line 495, in <module>
    main()
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\scripts\test_frontend.py", line 470, in main
    test_result = run_jest_tests(args, isolation_manager)
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\scripts\test_frontend.py", line 149, in run_jest_tests
    result = subprocess.run(
             ^^^^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\subprocess.py", line 548, in run
    with Popen(*popenargs, **kwargs) as process:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\subprocess.py", line 1026, in __init__
    self._execute_child(args, executable, preexec_fn, close_fds,
  File "C:\Users\antho\miniconda3\Lib\subprocess.py", line 1538, in _execute_child
    hp, ht, pid, tid = _winapi.CreateProcess(executable, args,
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [WinError 2] The system cannot find the file specified

```

---
*Generated by Netra AI Unified Test Runner*
