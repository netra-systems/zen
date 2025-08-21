# Netra AI Platform - Test Report

**Generated:** 2025-08-21T10:38:13.630274  
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
| Backend   | 0 | 0 | 0 | 0 | 0 | 4.93s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.34s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 5.27s
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
[FAIL] TESTS FAILED with exit code 4 after 4.15s
================================================================================

ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\conftest.py'.
netra_backend\tests\conftest.py:59: in <module>
    from netra_backend.app.routes.mcp.main import app
netra_backend\app\routes\mcp\__init__.py:8: in <module>
    from netra_backend.app.routes.mcp.main import router
netra_backend\app\routes\mcp\main.py:13: in <module>
    from netra_backend.app.auth_integration.auth import get_current_user, get_current_user_optional
netra_backend\app\auth_integration\__init__.py:87: in <module>
    from netra_backend.app.services.synthetic_data.validators import (
netra_backend\app\services\synthetic_data\__init__.py:5: in <module>
    from netra_backend.app.services.synthetic_data.core_service import SyntheticDataService, synthetic_data_service
netra_backend\app\services\synthetic_data\core_service.py:9: in <module>
    from netra_backend.app.services.synthetic_data.synthetic_data_service_main import SyntheticDataService, synthetic_data_service
netra_backend\app\services\synthetic_data\synthetic_data_service_main.py:7: in <module>
    from netra_backend.app.services.synthetic_data.generation_coordinator import GenerationCoordinator
netra_backend\app\services\synthetic_data\generation_coordinator.py:8: in <module>
    from netra_backend.app.services.synthetic_data.core_service_base import CoreServiceBase
netra_backend\app\services\synthetic_data\core_service_base.py:13: in <module>
    from netra_backend.app.services.synthetic_data.job_manager import JobManager
netra_backend\app\services\synthetic_data\job_manager.py:11: in <module>
    from netra_backend.app.services.websocket.ws_manager import manager
netra_backend\app\services\websocket\ws_manager.py:14: in <module>
    from netra_backend.app.ws_manager import (
netra_backend\app\ws_manager.py:21: in <module>
    from netra_backend.app.websocket.connection import ConnectionInfo
netra_backend\app\websocket\connection.py:14: in <module>
    from netra_backend.app.websocket.connection_manager import ModernConnectionManager, get_connection_manager
netra_backend\app\websocket\connection_manager.py:19: in <module>
    from netra_backend.app.websocket.connection_executor import ConnectionExecutionOrchestrator
netra_backend\app\websocket\connection_executor.py:13: in <module>
    from netra_backend.app.agents.base.interface import (
netra_backend\app\agents\base\__init__.py:15: in <module>
    from netra_backend.app.agents.base_agent import BaseSubAgent
netra_backend\app\agents\base_agent.py:9: in <module>
    from netra_backend.app.routes.unified_tools.schemas import SubAgentLifecycle
netra_backend\app\routes\unified_tools\__init__.py:5: in <module>
    from netra_backend.app.routes.unified_tools.router import router
netra_backend\app\routes\unified_tools\router.py:20: in <module>
    from netra_backend.app.core.error_handlers import (
netra_backend\app\core\error_handlers\__init__.py:13: in <module>
    from netra_backend.app.agents import AgentErrorHandler, ExecutionErrorHandler
E   ImportError: cannot import name 'AgentErrorHandler' from 'netra_backend.app.agents' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\__init__.py)

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
