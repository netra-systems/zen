# Netra AI Platform - Test Report

**Generated:** 2025-08-21T12:23:40.111896  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  

## 1. Test Summary

[FAILED] **OVERALL STATUS**

### Test Counts (Extracted from pytest output)
- **Total Tests:** 0
- **Passed:** 0 
- **Failed:** 0
- **Skipped:** 0
- **Errors:** 0

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 0 | 0 | 0 | 0 | 0 | 6.80s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.39s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 7.19s
- **Exit Code:** 255

### Backend Configuration
```
--category unit -v --coverage --fail-fast --parallel=4 --markers not real_services
```

### Frontend Configuration
```
--category unit
```

## 4. Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: unit
  Parallel: 4
  Coverage: disabled
  Fail Fast: enabled
  Environment: test

Running command:
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini netra_backend/tests/services netra_backend/tests/core -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m not real_services
================================================================================
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 5.76s
================================================================================

C:\Users\antho\miniconda3\Lib\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataSample" shadows an attribute in parent "BaseModel"
  warnings.warn(
C:\Users\antho\miniconda3\Lib\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataCatalog" shadows an attribute in parent "BaseModel"
  warnings.warn(
ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\conftest.py'.
netra_backend\tests\conftest.py:59: in <module>
    import pytest
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
================================================================================
NETRA AI PLATFORM - FRONTEND TEST RUNNER
================================================================================

================================================================================
Running Jest Tests
--------------------------------------------------------------------------------
Running: npm run test -- --forceExit --detectOpenHandles --testMatch **/__tests__/@(components|hooks|store|services|lib|utils)/**/*.test.[jt]s?(x)
--------------------------------------------------------------------------------

================================================================================
[FAIL] CHECKS FAILED with exit code 255
================================================================================

Cleaning up test processes...

'hooks' is not recognized as an internal or external command,
operable program or batch file.

```

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
