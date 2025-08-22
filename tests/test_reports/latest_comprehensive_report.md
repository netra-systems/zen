# Netra AI Platform - Test Report

**Generated:** 2025-08-21T14:06:23.458944  
**Test Level:** comprehensive - Full test suite with coverage including staging tests (30-45 minutes)  

## 1. Test Summary

[FAILED] **OVERALL STATUS**

### Test Counts (Extracted from pytest output)
- **Total Tests:** 1
- **Passed:** 0 
- **Failed:** 1
- **Skipped:** 0
- **Errors:** 0

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 0 | 0 | 0 | 0 | 0 | 4.51s | [FAILED] |
| Frontend  | 1 | 0 | 1 | 0 | 0 | 3.06s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** comprehensive
- **Description:** Full test suite with coverage including staging tests (30-45 minutes)
- **Purpose:** Pre-release validation, full system testing including staging environment
- **Timeout:** 2700s
- **Coverage Enabled:** Yes
- **Total Duration:** 7.57s
- **Exit Code:** 4

### Backend Configuration
```
netra_backend/tests tests integration_tests --coverage --parallel=6 --html-output --fail-fast
```

### Frontend Configuration
```
--coverage
```

## 4. Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: all
  Parallel: 6
  Coverage: disabled
  Fail Fast: enabled
  Environment: test

Running command:
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini netra_backend/tests tests integration_tests -v -n 6 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --html=reports/tests/report.html --self-contained-html
================================================================================
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 3.69s

[Report] HTML Report: reports/tests/report.html
================================================================================

C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataSample" shadows an attribute in parent "BaseModel"
  warnings.warn(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataCatalog" shadows an attribute in parent "BaseModel"
  warnings.warn(
ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\conftest.py'.
netra_backend\tests\conftest.py:70: in <module>
    from netra_backend.app.config import settings
netra_backend\app\config.py:25: in <module>
    from netra_backend.app.core.configuration.base import (
netra_backend\app\core\configuration\__init__.py:24: in <module>
    from netra_backend.app.core.configuration.base import (
netra_backend\app\core\configuration\base.py:24: in <module>
    from netra_backend.app.schemas.Config import AppConfig
netra_backend\app\schemas\__init__.py:590: in <module>
    from .strict_types import (
netra_backend\app\schemas\strict_types.py:13: in <module>
    from netra_backend.app.agents.triage_sub_agent.models import TriageResult
netra_backend\app\agents\triage_sub_agent\__init__.py:7: in <module>
    from netra_backend.app.agents.triage_sub_agent.core import TriageCore
netra_backend\app\agents\triage_sub_agent\core.py:15: in <module>
    from netra_backend.app.agents.config import agent_config
netra_backend\app\agents\config.py:7: in <module>
    from netra_backend.app.core.config import get_config
netra_backend\app\core\config.py:17: in <module>
    from netra_backend.app.core.configuration.base import (
E   ImportError: cannot import name 'config_manager' from partially initialized module 'netra_backend.app.core.configuration.base' (most likely due to a circular import) (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\core\configuration\base.py)

```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> node run-jest.js --config jest.config.simple.cjs --forceExit --detectOpenHandles --coverage --coverageDirectory=../reports/frontend-coverage

------------------------|---------|----------|---------|---------|------------------------------------------------
File                    | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s                              
------------------------|---------|----------|---------|---------|------------------------------------------------
All files               |    7.23 |     1.42 |    2.15 |    7.48 |                                                
 __tests__/mocks        |    4.68 |        0 |    1.36 |    4.91 |                                                
  auth-service-mock.ts  |    2.27 |        0 |       0 |    2.38 | 56-189                                         
  websocket-mocks.ts    |     5.4 |        0 |    1.81 |    5.67 | 49,56-356,369-403                              
 __tests__/setup        |   22.72 |        0 |       0 |   25.64 |                                                
  auth-service-setup.ts |      10 |        0 |       0 |      10 | 10-31,56-118                                   
  test-providers.tsx    |      50 |      100 |       0 |   77.77 | 52-54                                          
 lib                    |   13.41 |    11.11 |    7.69 |    14.1 |                                                
  logger.ts             |   13.41 |    11.11 |    7.69 |    14.1 | 74-78,84-311                                   
 services               |    4.71 |        0 |       0 |    4.88 |                                                
  webSocketService.ts   |    4.71 |        0 |       0 |    4.88 | 83-1323                                        
 store                  |   15.38 |        0 |       4 |   15.78 |                                                
  authStore.ts          |   15.38 |        0 |       4 |   15.78 | 43-105,114-117,121-124,128-132,136-137,142-143 
 utils                  |    7.14 |        0 |    8.33 |     7.4 |                                                
  debug-logger.ts       |    7.14 |        0 |    8.33 |     7.4 | 26-95,104                                      
------------------------|---------|----------|---------|---------|------------------------------------------------
================================================================================
NETRA AI PLATFORM - FRONTEND TEST RUNNER
================================================================================

================================================================================
Running Jest Tests
--------------------------------------------------------------------------------
Running: npm run test -- --forceExit --detectOpenHandles --coverage --coverageDirectory=../reports/frontend-coverage
--------------------------------------------------------------------------------

================================================================================
[FAIL] CHECKS FAILED with exit code 1
================================================================================

Cleaning up test processes...

FAIL __tests__/integration/logout-websocket.test.tsx
  ● Logout WebSocket Disconnection Tests › WebSocket Disconnection › should disconnect WebSocket on logout

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 40 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 41 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 42 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 43 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 44 |[39m }[33m;[39m
     [90m 45 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:42:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:74:21)

  ● Logout WebSocket Disconnection Tests › WebSocket Disconnection › should verify WebSocket is disconnected

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 40 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 41 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 42 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 43 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 44 |[39m }[33m;[39m
     [90m 45 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:42:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:74:21)

  ● Logout WebSocket Disconnection Tests › WebSocket Disconnection › should clear WebSocket message queue

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 40 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 41 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 42 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 43 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 44 |[39m }[33m;[39m
     [90m 45 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:42:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:74:21)

  ● Logout WebSocket Disconnection Tests › WebSocket Disconnection › should handle WebSocket disconnection errors

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 40 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 41 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 42 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 43 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 44 |[39m }[33m;[39m
     [90m 45 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:42:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:74:21)

  ● Logout WebSocket Disconnection Tests › WebSocket State Cleanup › should ensure WebSocket connection is terminated

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 40 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 41 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 42 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 43 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 44 |[39m }[33m;[39m
     [90m 45 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:42:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:74:21)

  ● Logout WebSocket Disconnection Tests › WebSocket State Cleanup › should prevent new WebSocket messages after logout

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 40 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 41 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 42 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 43 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 44 |[39m }[33m;[39m
     [90m 45 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:42:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:74:21)

  ● Logout WebSocket Disconnection Tests › WebSocket State Cleanup › should clear any pending WebSocket operations

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 40 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 41 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 42 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 43 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 44 |[39m }[33m;[39m
     [90m 45 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:42:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:74:21)

  ● Logout WebSocket Disconnection Tests › WebSocket State Cleanup › should ensure clean WebSocket state for next session

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 40 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 41 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 42 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 43 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 44 |[39m }[33m;[39m
     [90m 45 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:42:31)
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:74:21)

  ● Logout WebSocket Disconnection Tests › WebSocket Timing Requirements › should complete WebSocket disconnect within 25ms

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 40 |[39m     setError[33m:[39...(truncated)
```

## 5. Error Details

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/integration/logout-websocket.test.tsx
- FAIL __tests__/integration/logout-websocket.test.tsx

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
