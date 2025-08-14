# Netra AI Platform - Test Report

**Generated:** 2025-08-14T09:08:52.634730  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 217  
**Passed:** 194  
**Failed:** 3  
**Skipped:** 20  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 217 | 194 | 3 | 20 | 0 | 35.01s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.47s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 35.48s
- **Exit Code:** 15

### Backend Configuration
```
--category unit -v --coverage --fail-fast --parallel=4 --markers not real_services
```

### Frontend Configuration
```
--category unit
```

## Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: unit
  Parallel: 4
  Coverage: enabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests/services app/tests/core -vv -n 4 -x --maxfail=1 --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 4/4 workers
[gw0] node down: Traceback (most recent call last):
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\config\__init__.py", line 712, in _importconftest
    mod = import_path(
          ^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\pathlib.py", line 587, in import_path
    importlib.import_module(module_name)
  File "C:\Users\antho\miniconda3\Lib\importlib\__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\assertion\rewrite.py", line 186, in exec_module
    exec(co, module.__dict__)
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\conftest.py", line 52, in <module>
    from app.main import app
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\main.py", line 46, in <module>
    from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\agents\supervisor_consolidated.py", line 12, in <module>
    from app.agents.base import BaseSubAgent
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\agents\base.py", line 10, in <module>
    from app.agents.state import DeepAgentState
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\agents\state.py", line 95, in <module>
    class DeepAgentState(BaseModel):
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\agents\state.py", line 125, in DeepAgentState
    @validator('optimizations_result')
     ^^^^^^^^^
NameError: name 'validator' is not defined

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "C:\Users\antho\miniconda3\Lib\site-packages\execnet\gateway_base.py", line 1291, in executetask
    exec(co, loc)
  File "C:\Users\antho\miniconda3\Lib\site-packages\xdist\remote.py", line 420, in <module>
    config = _prepareconfig(args, None)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\config\__init__.py", line 342, in _prepareconfig
    config = pluginmanager.hook.pytest_cmdline_parse(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 167, in _multicall
    raise exception
  File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
    teardown.throw(exception)
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\helpconfig.py", line 112, in pytest_cmdline_parse
    config = yield
             ^^^^^
  File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
          ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\config\__init__.py", line 1146, in pytest_cmdline_parse
    self.parse(args)
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\config\__init__.py", line 1527, in parse
    self._preparse(args, addopts=addopts)
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\config\__init__.py", line 1431, in _preparse
    self.hook.pytest_load_initial_conftests(
  File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 167, in _multicall
    raise exception
  File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
    teardown.throw(exception)
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\capture.py", line 173, in pytest_load_initial_conftests
    yield
  File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
          ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\config\__init__.py", line 1228, in pytest_load_initial_conftests
    self.pluginmanager._set_initial_conftests(
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\config\__init__.py", line 583, in _set_initial_conftests
    self._try_load_conftest(
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\config\__init__.py", line 621, in _try_load_conftest
    self._loadconftestmodules(
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\config\__init__.py", line 661, in _loadconftestmodules
    mod = self._importconftest(
          ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\config\__init__.py", line 720, in _importconftest
    raise ConftestImportFailure(conftestpath, cause=e) from e
_pytest.config.ConftestImportFailure: NameError: name 'validator' is not defined (from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\conftest.py)


replacing crashed worker gw0
[gw1] node down: Traceback (most recent call last):
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\config\__init__.py", line 712, in _importconftest
    mod = import_path(
          ^^^^^^^^^^^^
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\pathlib.py", line 587, in import_path
    importlib.import_module(module_name)
  File "C:\Users\antho\miniconda3\Lib\importlib\__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\assertion\rewrite.py", line 186, in exec_module
    exec(co, module.__dict__)
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\conftest.py", line 52, in <module>
    from app.main import app
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\main.py", line 46, in <module>
    from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\agents\supervisor_consolidated.py", line 12, in <module>
    from app.agents.base import BaseSubAgent
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\agents\base.py", line 10, in <module>
    from app.agents.state import DeepAgentState
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\agents\state.py", line 95, in <module>
    class DeepAgentState(BaseModel):
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\agents\state.py", line 125, in DeepAgentState
    @validator('optimizations_result')
     ^^^^^^^^^
NameError: name 'validator' is not defined

The above exception was the direct cause of the fo...(truncated)
```

### Frontend Output
```

'hooks' is not recognized as an internal or external command,
operable program or batch file.

```

## Error Summary

### Backend Errors
- [gw6][36m [  1%] [0m[31mFAILED[0m app\tests\services\synthetic_data\test_table_operations.py::TestTableOperations::test_ingest_batch_with_data
- [gw7][36m [  6%] [0m[31mFAILED[0m app\tests\services\test_corpus_service_comprehensive.py::TestIndexOptimization::test_index_performance_monitoring
- [gw5][36m [ 12%] [0m[31mFAILED[0m app\tests\services\synthetic_data\test_table_operations.py::TestTableOperations::test_create_destination_table
- [31mFAILED[0m app\tests\services\synthetic_data\test_table_operations.py::[1mTestTableOperations::test_ingest_batch_with_data[0m - AttributeError: 'SyntheticDataService' object has no attribute '_ingest_batch'. Did you mean: 'ingest_batch'?
- [31mFAILED[0m app\tests\services\test_corpus_service_comprehensive.py::[1mTestIndexOptimization::test_index_performance_monitoring[0m - AttributeError: 'CorpusService' object has no attribute 'get_performance_metrics'
- [31mFAILED[0m app\tests\services\synthetic_data\test_table_operations.py::[1mTestTableOperations::test_create_destination_table[0m - AttributeError: 'SyntheticDataService' object has no attribute '_create_destination_table'
- [FAIL] TESTS FAILED with exit code 2 after 34.13s


---
*Generated by Netra AI Unified Test Runner v3.0*
