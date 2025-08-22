# Netra AI Platform - Test Report

**Generated:** 2025-08-21T16:08:13.722154  
**Test Level:** integration - Integration tests for component interaction (3-5 minutes)  

## 1. Test Summary

[FAILED] **OVERALL STATUS**

### Test Counts (Extracted from pytest output)
- **Total Tests:** 2
- **Passed:** 0 
- **Failed:** 1
- **Skipped:** 0
- **Errors:** 1

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 1 | 0 | 0 | 0 | 1 | 16.83s | [FAILED] |
| Frontend  | 1 | 0 | 1 | 0 | 0 | 2.30s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 19.12s
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
[31m[1m_ ERROR collecting tests/integration/critical_paths/test_agent_failure_recovery_cascade_l3.py _[0m
ImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\integration\critical_paths\test_agent_failure_recovery_cascade_l3.py'.
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
netra_backend\tests\integration\critical_paths\test_agent_failure_recovery_cascade_l3.py:34: in <module>
    from resilience.circuit_breaker import CircuitBreaker
E   ModuleNotFoundError: No module named 'resilience'
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m netra_backend\tests\integration\critical_paths\test_agent_failure_recovery_cascade_l3.py
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m============================== [31m[1m1 error[0m[31m in 9.67s[0m[31m ===============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 15.81s
================================================================================

C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\integration\critical_paths\test_agent_communication_basic_l3.py:35: PytestCollectionWarning: cannot collect test class 'TestAgentCommunicationBasic' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_communication_basic_l3.py)
  class TestAgentCommunicationBasic(L3IntegrationTest):
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\integration\critical_paths\test_agent_communication_basic_l3.py:35: PytestCollectionWarning: cannot collect test class 'TestAgentCommunicationBasic' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_communication_basic_l3.py)
  class TestAgentCommunicationBasic(L3IntegrationTest):
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\test_framework\testcontainers_utils.py:19: PytestCollectionWarning: cannot collect test class 'TestcontainerHelper' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_context_isolation_boundaries_l3.py)
  class TestcontainerHelper:
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\test_framework\testcontainers_utils.py:19: PytestCollectionWarning: cannot collect test class 'TestcontainerHelper' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_context_isolation_boundaries_l3.py)
  class TestcontainerHelper:
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\integration\critical_paths\test_agent_communication_basic_l3.py:35: PytestCollectionWarning: cannot collect test class 'TestAgentCommunicationBasic' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_communication_basic_l3.py)
  class TestAgentCommunicationBasic(L3IntegrationTest):
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\integration\critical_paths\test_agent_communication_basic_l3.py:35: PytestCollectionWarning: cannot collect test class 'TestAgentCommunicationBasic' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_communication_basic_l3.py)
  class TestAgentCommunicationBasic(L3IntegrationTest):
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\test_framework\testcontainers_utils.py:19: PytestCollectionWarning: cannot collect test class 'TestcontainerHelper' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_context_isolation_boundaries_l3.py)
  class TestcontainerHelper:
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\test_framework\testcontainers_utils.py:19: PytestCollectionWarning: cannot collect test class 'TestcontainerHelper' because it has a __init__ constructor (from: tests/integration/critical_paths/test_agent_context_isolation_boundaries_l3.py)
  class TestcontainerHelper:
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataSample" shadows an attribute in parent "BaseModel"
  warnings.warn(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataCatalog" shadows an attribute in parent "BaseModel"
  warnings.warn(

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

FAIL __tests__/integration/logout-websocket.test.tsx
  ● Logout WebSocket Disconnection Tests › WebSocket Disconnection › should disconnect WebSocket on logout

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 38 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 39 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 40 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 41 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 42 |[39m }[33m;[39m
     [90m 43 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:40:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:72:21)

  ● Logout WebSocket Disconnection Tests › WebSocket Disconnection › should verify WebSocket is disconnected

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 38 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 39 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 40 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 41 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 42 |[39m }[33m;[39m
     [90m 43 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:40:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:72:21)

  ● Logout WebSocket Disconnection Tests › WebSocket Disconnection › should clear WebSocket message queue

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 38 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 39 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 40 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 41 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 42 |[39m }[33m;[39m
     [90m 43 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:40:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:72:21)

  ● Logout WebSocket Disconnection Tests › WebSocket Disconnection › should handle WebSocket disconnection errors

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 38 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 39 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 40 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 41 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 42 |[39m }[33m;[39m
     [90m 43 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:40:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:72:21)

  ● Logout WebSocket Disconnection Tests › WebSocket State Cleanup › should ensure WebSocket connection is terminated

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 38 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 39 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 40 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 41 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 42 |[39m }[33m;[39m
     [90m 43 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:40:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:72:21)

  ● Logout WebSocket Disconnection Tests › WebSocket State Cleanup › should prevent new WebSocket messages after logout

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 38 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 39 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 40 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 41 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 42 |[39m }[33m;[39m
     [90m 43 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:40:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:72:21)

  ● Logout WebSocket Disconnection Tests › WebSocket State Cleanup › should clear any pending WebSocket operations

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 38 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 39 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 40 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 41 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 42 |[39m }[33m;[39m
     [90m 43 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:40:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:72:21)

  ● Logout WebSocket Disconnection Tests › WebSocket State Cleanup › should ensure clean WebSocket state for next session

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 38 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 39 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 40 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 41 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 42 |[39m }[33m;[39m
     [90m 43 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:40:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:72:21)

  ● Logout WebSocket Disconnection Tests › WebSocket Timing Requirements › should complete WebSocket disconnect within 25ms

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 38 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 39 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 40 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 41 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 42 |[39m }[33m;[39m
     [90m 43 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:40:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:72:21)

  ● Logout WebSocket Disconnection Tests › WebSocket Timing Requirements › should not block logout process if WebSocket fails

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 38 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 39 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 40 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 41 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 42 |[39m }[33m;[39m
     [90m 43 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:40:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:72:21)

  ● Logout WebSocket Disconnection Tests › WebSocket Timing Requirements › should handle WebSocket timeout gracefully

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 38 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 39 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 40 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 41 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 42 |[39m }[33m;[39m
     [90m 43 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:40:31)
      at Object.setupAuthStore (__tests__/integration/...(truncated)
```

## 5. Error Details

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m_ ERROR collecting tests/integration/critical_paths/test_agent_failure_recovery_cascade_l3.py _[0m
- [31mERROR[0m netra_backend\tests\integration\critical_paths\test_agent_failure_recovery_cascade_l3.py
- [FAIL] TESTS FAILED with exit code 2 after 15.81s

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/integration/logout-websocket.test.tsx
- FAIL __tests__/integration/logout-websocket.test.tsx

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
