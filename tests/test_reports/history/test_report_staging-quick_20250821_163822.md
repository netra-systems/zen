# Netra AI Platform - Test Report

**Generated:** 2025-08-21T10:46:05.344730  
**Test Level:** staging-quick - Quick staging validation tests (2-3 minutes)  

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
| Backend   | 0 | 0 | 0 | 0 | 0 | 12.42s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## 3. Environment and Configuration

- **Test Level:** staging-quick
- **Description:** Quick staging validation tests (2-3 minutes)
- **Purpose:** Fast staging health check for deployment verification
- **Timeout:** 180s
- **Coverage Enabled:** No
- **Total Duration:** 12.42s
- **Exit Code:** 4

### Backend Configuration
```
netra_backend/tests/integration/staging_config/test_secret_manager_integration.py netra_backend/tests/integration/staging_config/test_health_checks.py -v --fail-fast
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
  Parallel: disabled
  Coverage: disabled
  Fail Fast: enabled
  Environment: test

Running command:
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini netra_backend/tests/integration/staging_config/test_secret_manager_integration.py netra_backend/tests/integration/staging_config/test_health_checks.py -vv -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 10.56s
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
netra_backend\app\agents\base_agent.py:18: in <module>
    from netra_backend.app.agents.agent_communication import AgentCommunicationMixin
netra_backend\app\agents\agent_communication.py:12: in <module>
    from netra_backend.app.routes.unified_tools.schemas import SubAgentUpdate, SubAgentState
E   ImportError: cannot import name 'SubAgentUpdate' from 'netra_backend.app.routes.unified_tools.schemas' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\routes\unified_tools\schemas.py)

```

### Frontend Output
```

```

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
