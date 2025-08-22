# Netra AI Platform - Test Report

**Generated:** 2025-08-21T16:10:38.297013  
**Test Level:** integration - Integration tests for component interaction (3-5 minutes)  

## 1. Test Summary

[FAILED] **OVERALL STATUS**

### Test Counts (Extracted from pytest output)
- **Total Tests:** 1
- **Passed:** 0 
- **Failed:** 0
- **Skipped:** 0
- **Errors:** 1

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 1 | 0 | 0 | 0 | 1 | 19.30s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## 3. Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 19.30s
- **Exit Code:** 2

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
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\pytest.ini netra_backend/tests/integration netra_backend/tests/routes -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m not real_services
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.5.3', 'langsmith': '0.4.15', 'asyncio': '1.1.0', 'cov': '6.2.1', 'mock': '3.14.1', 'xdist': '3.8.0', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'timeout': '2.4.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.5.3, langsmith-0.4.15, asyncio-1.1.0, cov-6.2.1, mock-3.14.1, xdist-3.8.0, html-4.1.1, json-report-1.5.0, metadata-3.1.1, timeout-2.4.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=session, asyncio_default_test_loop_scope=function
created: 4/4 workers

=================================== ERRORS ====================================
[31m[1m_ ERROR collecting tests/integration/critical_paths/test_agent_lifecycle_management.py _[0m
ImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\integration\critical_paths\test_agent_lifecycle_management.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\_pytest\python.py:498: in importtestmodule
    mod = import_path(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\_pytest\pathlib.py:587: in import_path
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
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\_pytest\assertion\rewrite.py:186: in exec_module
    exec(co, module.__dict__)
netra_backend\tests\integration\critical_paths\test_agent_lifecycle_management.py:41: in <module>
    from netra_backend.app.core.config import Settings
E   ImportError: cannot import name 'Settings' from 'netra_backend.app.core.config' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\core\config.py)
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m netra_backend\tests\integration\critical_paths\test_agent_lifecycle_management.py
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m============================== [31m[1m1 error[0m[31m in 12.02s[0m[31m ==============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 18.08s
================================================================================

C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\integration\critical_paths\test_agent_communication_basic_l3.py:35: PytestCollectionWarning: cannot collect test class 'TestAgentCommunicationBasic' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_communication_basic_l3.py)
  class TestAgentCommunicationBasic(L3IntegrationTest):
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\integration\critical_paths\test_agent_communication_basic_l3.py:35: PytestCollectionWarning: cannot collect test class 'TestAgentCommunicationBasic' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_communication_basic_l3.py)
  class TestAgentCommunicationBasic(L3IntegrationTest):
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\integration\critical_paths\test_agent_communication_basic_l3.py:35: PytestCollectionWarning: cannot collect test class 'TestAgentCommunicationBasic' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_communication_basic_l3.py)
  class TestAgentCommunicationBasic(L3IntegrationTest):
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\integration\critical_paths\test_agent_communication_basic_l3.py:35: PytestCollectionWarning: cannot collect test class 'TestAgentCommunicationBasic' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_communication_basic_l3.py)
  class TestAgentCommunicationBasic(L3IntegrationTest):
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\test_framework\testcontainers_utils.py:19: PytestCollectionWarning: cannot collect test class 'TestcontainerHelper' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_context_isolation_boundaries_l3.py)
  class TestcontainerHelper:
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\test_framework\testcontainers_utils.py:19: PytestCollectionWarning: cannot collect test class 'TestcontainerHelper' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_context_isolation_boundaries_l3.py)
  class TestcontainerHelper:
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\test_framework\testcontainers_utils.py:19: PytestCollectionWarning: cannot collect test class 'TestcontainerHelper' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_context_isolation_boundaries_l3.py)
  class TestcontainerHelper:
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\test_framework\testcontainers_utils.py:19: PytestCollectionWarning: cannot collect test class 'TestcontainerHelper' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_context_isolation_boundaries_l3.py)
  class TestcontainerHelper:
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\test_framework\testcontainers_utils.py:19: PytestCollectionWarning: cannot collect test class 'TestcontainerHelper' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_failure_recovery_cascade_l3.py)
  class TestcontainerHelper:
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\test_framework\testcontainers_utils.py:19: PytestCollectionWarning: cannot collect test class 'TestcontainerHelper' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_failure_recovery_cascade_l3.py)
  class TestcontainerHelper:
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\test_framework\testcontainers_utils.py:19: PytestCollectionWarning: cannot collect test class 'TestcontainerHelper' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_failure_recovery_cascade_l3.py)
  class TestcontainerHelper:
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\test_framework\testcontainers_utils.py:19: PytestCollectionWarning: cannot collect test class 'TestcontainerHelper' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_failure_recovery_cascade_l3.py)
  class TestcontainerHelper:
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataSample" shadows an attribute in parent "BaseModel"
  warnings.warn(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataCatalog" shadows an attribute in parent "BaseModel"
  warnings.warn(

```

### Frontend Output
```

```

## 5. Error Details

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m_ ERROR collecting tests/integration/critical_paths/test_agent_lifecycle_management.py _[0m
- [31mERROR[0m netra_backend\tests\integration\critical_paths\test_agent_lifecycle_management.py
- [FAIL] TESTS FAILED with exit code 2 after 18.08s

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
