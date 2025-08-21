# Netra AI Platform - Test Report

**Generated:** 2025-08-21T14:03:54.488615  
**Test Level:** integration - Integration tests for component interaction (3-5 minutes)  

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
| Backend   | 0 | 0 | 0 | 0 | 0 | 5.77s | [FAILED] |
| Frontend  | 1 | 0 | 1 | 0 | 0 | 3.32s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 9.10s
- **Exit Code:** 15

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
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini netra_backend/tests/integration netra_backend/tests/routes -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m not real_services
================================================================================
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 5.07s
================================================================================

C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataSample" shadows an attribute in parent "BaseModel"
  warnings.warn(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataCatalog" shadows an attribute in parent "BaseModel"
  warnings.warn(
ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\conftest.py'.
netra_backend\tests\conftest.py:65: in <module>
    from netra_backend.app.main import app
netra_backend\app\main.py:91: in <module>
    from netra_backend.app.core.app_factory import create_app
netra_backend\app\core\app_factory.py:9: in <module>
    from netra_backend.app.core.lifespan_manager import lifespan
netra_backend\app\core\lifespan_manager.py:9: in <module>
    from netra_backend.app.shutdown import run_complete_shutdown
netra_backend\app\shutdown.py:12: in <module>
    from netra_backend.app.services.websocket.ws_manager import manager as websocket_manager
netra_backend\app\services\websocket\ws_manager.py:47: in __getattr__
    mgr, _, _, _ = _lazy_import()
                   ^^^^^^^^^^^^^^
netra_backend\app\services\websocket\ws_manager.py:29: in _lazy_import
    from netra_backend.app.ws_manager import (
netra_backend\app\ws_manager.py:245: in <module>
    manager = get_manager()
              ^^^^^^^^^^^^^
netra_backend\app\ws_manager.py:241: in get_manager
    _manager = WebSocketManager()
               ^^^^^^^^^^^^^^^^^^
netra_backend\app\ws_manager.py:38: in __new__
    cls._instance._initialize_unified_delegation()
netra_backend\app\ws_manager.py:45: in _initialize_unified_delegation
    self._unified_manager = get_unified_manager()
                            ^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\websocket\unified\manager.py:410: in get_unified_manager
    _unified_manager = UnifiedWebSocketManager()
                       ^^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\websocket\unified\manager.py:65: in __init__
    self._initialize_core_components()
netra_backend\app\websocket\unified\manager.py:73: in _initialize_core_components
    self.connection_manager = ConnectionManager()
                              ^^^^^^^^^^^^^^^^^^^
netra_backend\app\websocket\connection.py:56: in __init__
    self._modern_manager = Modernget_connection_manager()
                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   NameError: name 'Modernget_connection_manager' is not defined

```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> node run-jest.js --config jest.config.simple.cjs --forceExit --detectOpenHandles --testMatch **/__tests__/integration/**/*.test.[jt]s?(x)


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
      at Object.setupAuthStore (__tests__/integration/logout-websocket.test.tsx:72:21)

  ● Logout WebSocket Disconnection Tests › WebSocket Timing Requirements › should complete logout even if WebSocket is slow

    TypeError: _authStore.useAuthStore.mockReturnValue is not a function

    [0m [90m 38 |[39m     setError[33m:[39m jest[33m.[39mfn()[33m,[39m
     [90m 39 |[39m   }[33m;[39m
    [31m[1m>[22m[39m[90m 40 |[39m   (useAuthStore [36mas[39m jest[33m.[39m[33mMock[39m)[33m.[39mmockReturnValue(mockStore)[33m;[39m
     [90m    |[39m                               [31m[1m^[22m[39m
     [90m 41 |[39m   [36mreturn[39m mockStore[33m;[39m
     [90m 42 |[39m }[33m;[39m
     [90m 43 |[39m[0m

      at mockReturnValue (__tests__/integration/logout-websocket.test.tsx:40:31)
      at Object.setupAuthStore (__tests__...(truncated)
```

## 5. Error Details

### Frontend Errors
- FAIL __tests__/integration/logout-websocket.test.tsx
- FAIL __tests__/integration/logout-websocket.test.tsx

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
