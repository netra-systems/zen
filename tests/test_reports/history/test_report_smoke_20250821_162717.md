# Netra AI Platform - Test Report

**Generated:** 2025-08-21T16:23:54.643314  
**Test Level:** smoke - Quick smoke tests for basic functionality (< 30 seconds)  

## 1. Test Summary

[FAILED] **OVERALL STATUS**

### Test Counts (Extracted from pytest output)
- **Total Tests:** 15
- **Passed:** 6 
- **Failed:** 1
- **Skipped:** 0
- **Errors:** 0

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 15 | 6 | 1 | 0 | 0 | 12.57s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## 3. Environment and Configuration

- **Test Level:** smoke
- **Description:** Quick smoke tests for basic functionality (< 30 seconds)
- **Purpose:** Pre-commit validation, basic health checks
- **Timeout:** 30s
- **Coverage Enabled:** Yes
- **Total Duration:** 12.57s
- **Exit Code:** 1

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
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\pytest.ini netra_backend/tests/routes/test_health_route.py netra_backend/tests/core/test_error_handling.py::TestNetraExceptions::test_configuration_error netra_backend/tests/core/test_config_manager.py::TestSecretManager::test_initialization netra_backend/tests/services/test_security_service.py::test_encrypt_and_decrypt netra_backend/tests/e2e/test_system_startup.py::TestSystemStartup -v -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m not real_services
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.5.3', 'langsmith': '0.4.15', 'asyncio': '1.1.0', 'cov': '6.2.1', 'mock': '3.14.1', 'xdist': '3.8.0', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'timeout': '2.4.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.5.3, langsmith-0.4.15, asyncio-1.1.0, cov-6.2.1, mock-3.14.1, xdist-3.8.0, html-4.1.1, json-report-1.5.0, metadata-3.1.1, timeout-2.4.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=session, asyncio_default_test_loop_scope=function
[1mcollecting ... [0mcollected 15 items

netra_backend\tests\routes\test_health_route.py::test_basic_import [32mPASSED[0m[32m [  6%][0m
netra_backend\tests\routes\test_health_route.py::test_health_endpoint_direct [32mPASSED[0m[32m [ 13%][0m
netra_backend\tests\routes\test_health_route.py::test_live_endpoint [32mPASSED[0m[32m [ 20%][0m
netra_backend\tests\core\test_error_handling.py::TestNetraExceptions::test_configuration_error [32mPASSED[0m[32m [ 26%][0m
netra_backend\tests\core\test_config_manager.py::TestSecretManager::test_initialization [32mPASSED[0m[32m [ 33%][0m
netra_backend\tests\services\test_security_service.py::test_encrypt_and_decrypt [32mPASSED[0m[32m [ 40%][0m
netra_backend\tests\e2e\test_system_startup.py::TestSystemStartup::test_dev_launcher_starts_all_services [31mFAILED[0m[31m [ 46%][0m

================================== FAILURES ===================================
[31m[1m___________ TestSystemStartup.test_dev_launcher_starts_all_services ___________[0m
[1m[31mnetra_backend\tests\e2e\test_system_startup.py[0m:98: in test_dev_launcher_starts_all_services
    [0m[94mawait[39;49;00m launcher.start()[90m[39;49;00m
          ^^^^^^^^^^^^^^[90m[39;49;00m
[1m[31mE   AttributeError: 'DevLauncher' object has no attribute 'start'[0m

[33mDuring handling of the above exception, another exception occurred:[0m
[1m[31mnetra_backend\tests\e2e\test_system_startup.py[0m:110: in test_dev_launcher_starts_all_services
    [0m[94mawait[39;49;00m launcher.shutdown()[90m[39;49;00m
          ^^^^^^^^^^^^^^^^^[90m[39;49;00m
[1m[31mE   AttributeError: 'DevLauncher' object has no attribute 'shutdown'[0m
----------------------------- Captured log setup ------------------------------
[35mDEBUG   [0m asyncio:selector_events.py:64 Using selector: SelectSelector
[35mDEBUG   [0m asyncio:selector_events.py:64 Using selector: SelectSelector
[32mINFO    [0m dev_launcher.service_config:service_config.py:350 Configuration loaded from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.dev_services.json
[32mINFO    [0m dev_launcher.service_config:service_config.py:515 Loaded existing service configuration
[35mDEBUG   [0m asyncio:selector_events.py:64 Using selector: SelectSelector
---------------------------- Captured stdout call -----------------------------
\U0001f50d DISCOVER | POSTGRESQL: sqlite+aiosqlite:///:memory:\n\U0001f50d DISCOVER | CLICKHOUSE: clickhouse://default:***@localhost:8123/netra_dev\n\U0001f50d DISCOVER | REDIS: redis://localhost:6379/1\n\U0001f50d WEBSOCKET | Discovered endpoint: backend_ws -> ws://localhost:8000/ws
------------------------------ Captured log call ------------------------------
[32mINFO    [0m dev_launcher.health_monitor:health_monitor.py:139 HealthMonitor initialized (check_interval: 30s)
[32mINFO    [0m dev_launcher.health_monitor:health_monitor.py:141 Windows process verification enabled
[32mINFO    [0m dev_launcher.process_manager:process_manager.py:58 ProcessManager initialized for win32
[32mINFO    [0m dev_launcher.process_manager:process_manager.py:60 Enhanced Windows process tree management enabled
[32mINFO    [0m dev_launcher.database_connector:database_connector.py:130 Discovered 3 database connections
[32mINFO    [0m dev_launcher.websocket_validator:websocket_validator.py:78 Discovered 1 WebSocket endpoints
[32mINFO    [0m dev_launcher.launcher:launcher.py:165 Signal handlers registered for graceful shutdown
[36m[1m=========================== short test summary info ===========================[0m
[31mFAILED[0m netra_backend\tests\e2e\test_system_startup.py::[1mTestSystemStartup::test_dev_launcher_starts_all_services[0m - AttributeError: 'DevLauncher' object has no attribute 'shutdown'
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
[31m========================= [31m[1m1 failed[0m, [32m6 passed[0m[31m in 2.43s[0m[31m =========================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 1 after 11.17s
================================================================================


```

### Frontend Output
```

```

## 5. Error Details

### Backend Errors
- netra_backend\tests\e2e\test_system_startup.py::TestSystemStartup::test_dev_launcher_starts_all_services [31mFAILED[0m[31m [ 46%][0m
- [31mFAILED[0m netra_backend\tests\e2e\test_system_startup.py::[1mTestSystemStartup::test_dev_launcher_starts_all_services[0m - AttributeError: 'DevLauncher' object has no attribute 'shutdown'
- [FAIL] TESTS FAILED with exit code 1 after 11.17s

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
