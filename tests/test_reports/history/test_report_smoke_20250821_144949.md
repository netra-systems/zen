# Netra AI Platform - Test Report

**Generated:** 2025-08-21T14:48:51.862253  
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
| Backend   | 0 | 0 | 0 | 0 | 0 | 5.35s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## 3. Environment and Configuration

- **Test Level:** smoke
- **Description:** Quick smoke tests for basic functionality (< 30 seconds)
- **Purpose:** Pre-commit validation, basic health checks
- **Timeout:** 30s
- **Coverage Enabled:** Yes
- **Total Duration:** 5.35s
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
[FAIL] TESTS FAILED with exit code 4 after 4.61s
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
netra_backend\app\routes\admin.py:60: in <module>
    @router.post("/settings/log_table")
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\fastapi\routing.py:995: in decorator
    self.add_api_route(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\fastapi\routing.py:934: in add_api_route
    route = route_class(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\fastapi\routing.py:555: in __init__
    self.dependant = get_dependant(path=self.path_format, call=self.endpoint)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\fastapi\dependencies\utils.py:285: in get_dependant
    param_details = analyze_param(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\fastapi\dependencies\utils.py:488: in analyze_param
    field = create_model_field(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\fastapi\utils.py:98: in create_model_field
    raise fastapi.exceptions.FastAPIError(
E   fastapi.exceptions.FastAPIError: Invalid args for response field! Hint: check that <module 'netra_backend.app.schemas.User' from 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\netra_backend\\app\\schemas\\User.py'> is a valid Pydantic field type. If you are using a return type annotation that is not a valid Pydantic field (e.g. Union[Response, dict, None]) you can disable generating the response model from the type annotation with the path operation decorator parameter response_model=None. Read more: https://fastapi.tiangolo.com/tutorial/response-model/

```

### Frontend Output
```

```

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
