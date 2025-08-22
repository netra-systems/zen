# Netra AI Platform - Test Report

**Generated:** 2025-08-21T14:50:39.325574  
**Test Level:** smoke - Quick smoke tests for basic functionality (< 30 seconds)  

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
| Backend   | 0 | 0 | 0 | 0 | 0 | 4.97s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## 3. Environment and Configuration

- **Test Level:** smoke
- **Description:** Quick smoke tests for basic functionality (< 30 seconds)
- **Purpose:** Pre-commit validation, basic health checks
- **Timeout:** 30s
- **Coverage Enabled:** Yes
- **Total Duration:** 4.97s
- **Exit Code:** 4

### Backend Configuration
```
--category smoke --fail-fast --coverage --markers not real_services
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
  Category: smoke
  Parallel: disabled
  Coverage: disabled
  Fail Fast: enabled
  Environment: test

Running command:
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini netra_backend/tests/routes/test_health_route.py netra_backend/tests/core/test_error_handling.py::TestNetraExceptions::test_configuration_error netra_backend/tests/core/test_config_manager.py::TestConfigManager::test_initialization netra_backend/tests/services/test_security_service.py::test_encrypt_and_decrypt netra_backend/tests/e2e/test_system_startup.py::TestSystemStartup::test_configuration_loading -v -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m not real_services
================================================================================
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 4.22s
================================================================================

C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataSample" shadows an attribute in parent "BaseModel"
  warnings.warn(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataCatalog" shadows an attribute in parent "BaseModel"
  warnings.warn(
ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\conftest.py'.
netra_backend\tests\conftest.py:82: in <module>
    from netra_backend.app.main import app
netra_backend\app\main.py:93: in <module>
    app = create_app()
          ^^^^^^^^^^^^
netra_backend\app\core\app_factory.py:131: in create_app
    _configure_app_routes(app)
netra_backend\app\core\app_factory.py:144: in _configure_app_routes
    register_api_routes(app)
netra_backend\app\core\app_factory.py:101: in register_api_routes
    _import_and_register_routes(app)
netra_backend\app\core\app_factory.py:106: in _import_and_register_routes
    route_modules = import_all_route_modules()
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\core\app_factory_route_imports.py:144: in import_all_route_modules
    basic_modules = import_basic_route_modules()
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\core\app_factory_route_imports.py:5: in import_basic_route_modules
    route_imports = _import_core_routes()
                    ^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\core\app_factory_route_imports.py:11: in _import_core_routes
    from netra_backend.app.routes import (
netra_backend\app\routes\demo.py:8: in <module>
    from netra_backend.app.routes.demo_handlers import (
netra_backend\app\routes\demo_handlers.py:4: in <module>
    from netra_backend.app.routes.demo_handlers_analytics import (
netra_backend\app\routes\demo_handlers_analytics.py:4: in <module>
    from netra_backend.app.services.demo_service import DemoService
netra_backend\app\services\demo_service.py:6: in <module>
    from netra_backend.app.services.demo import (
netra_backend\app\services\demo\__init__.py:5: in <module>
    from netra_backend.app.services.demo.demo_service import DemoService, get_demo_service
netra_backend\app\services\demo\demo_service.py:6: in <module>
    from netra_backend.app.services.agent_service import AgentService
netra_backend\app\services\agent_service.py:9: in <module>
    from netra_backend.app.services.agent_service_compat import (
netra_backend\app\services\agent_service_compat.py:11: in <module>
    from netra_backend.app.services.agent_service_factory import get_agent_service
netra_backend\app\services\agent_service_factory.py:12: in <module>
    from netra_backend.app.services.agent_service_core import AgentService
netra_backend\app\services\agent_service_core.py:14: in <module>
    from netra_backend.app.agents.supervisor_consolidated import (
netra_backend\app\agents\supervisor_consolidated.py:24: in <module>
    from netra_backend.app.agents.base.executor import BaseExecutionEngine
netra_backend\app\agents\base\executor.py:20: in <module>
    from netra_backend.app.agents.base.errors import (
E   ImportError: cannot import name 'ExecutionErrorHandler' from 'netra_backend.app.agents.base.errors' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\base\errors.py)

```

### Frontend Output
```

```

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
