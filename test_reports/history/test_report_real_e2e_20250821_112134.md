# Netra AI Platform - Test Report

**Generated:** 2025-08-21T11:08:35.658095  
**Test Level:** real_e2e - Full end-to-end tests with real LLM and services (20-30 minutes)  

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
| Backend   | 0 | 0 | 0 | 0 | 0 | 5.56s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## 3. Environment and Configuration

- **Test Level:** real_e2e
- **Description:** Full end-to-end tests with real LLM and services (20-30 minutes)
- **Purpose:** Complete user journey validation with actual services
- **Timeout:** 1800s
- **Coverage Enabled:** No
- **Total Duration:** 5.56s
- **Exit Code:** 4

### Backend Configuration
```
-m real_e2e -v --fail-fast --parallel=2
```

### Frontend Configuration
```

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
  Parallel: 2
  Coverage: disabled
  Fail Fast: enabled
  Environment: test

Running command:
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini netra_backend/tests tests integration_tests -vv -n 2 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m real_e2e
================================================================================
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 4.77s
================================================================================

C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\base\monitoring.py:68: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  "system_start_time": datetime.utcnow(),
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\base\monitoring.py:68: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  "system_start_time": datetime.utcnow(),
ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\conftest.py'.
netra_backend\tests\conftest.py:59: in <module>
    from netra_backend.app.routes.mcp.main import app
netra_backend\app\routes\mcp\__init__.py:8: in <module>
    from netra_backend.app.routes.mcp.main import router
netra_backend\app\routes\mcp\main.py:25: in <module>
    from netra_backend.app.routes.mcp.handlers import MCPHandlers
netra_backend\app\routes\mcp\handlers.py:11: in <module>
    from netra_backend.app.routes.mcp.handlers_server import handle_server_info
netra_backend\app\routes\mcp\handlers_server.py:4: in <module>
    from netra_backend.app.services.mcp_service import MCPService
netra_backend\app\services\mcp_service.py:20: in <module>
    from netra_backend.app.services.agent_service import AgentService
netra_backend\app\services\agent_service.py:8: in <module>
    from netra_backend.app.services.agent_service_core import AgentService
netra_backend\app\services\agent_service_core.py:13: in <module>
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
netra_backend\app\agents\supervisor_consolidated.py:24: in <module>
    from netra_backend.app.agents.base.executor import BaseExecutionEngine
netra_backend\app\agents\base\executor.py:26: in <module>
    from netra_backend.app.agents.base.reliability import ReliabilityManager
netra_backend\app\agents\base\reliability.py:33: in <module>
    from netra_backend.app.agents.base.rate_limiter import RateLimiter
netra_backend\app\agents\base\rate_limiter.py:17: in <module>
    from netra_backend.app.websocket.rate_limiter import RateLimiter as CoreRateLimiter
netra_backend\app\websocket\__init__.py:13: in <module>
    from netra_backend.app.websocket.heartbeat_manager import HeartbeatManager
netra_backend\app\websocket\heartbeat_manager.py:13: in <module>
    from netra_backend.app.services.synthetic_data.error_handler import ErrorHandler as WebSocketErrorHandler
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
    self._modern_manager = ModernConnectionManager()
                           ^^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\websocket\connection_manager.py:37: in __init__
    self.orchestrator = ConnectionExecutionOrchestrator()
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\websocket\connection_executor.py:284: in __init__
    self.executor = ConnectionExecutor()
                    ^^^^^^^^^^^^^^^^^^^^
netra_backend\app\websocket\connection_executor.py:29: in __init__
    self._initialize_components()
netra_backend\app\websocket\connection_executor.py:34: in _initialize_components
    self._initialize_execution_engine()
netra_backend\app\websocket\connection_executor.py:44: in _initialize_execution_engine
    from netra_backend.app.agents.base.executor import BaseExecutionEngine
E   ImportError: cannot import name 'BaseExecutionEngine' from partially initialized module 'netra_backend.app.agents.base.executor' (most likely due to a circular import) (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\base\executor.py)

```

### Frontend Output
```

```

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
