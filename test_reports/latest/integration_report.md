# Netra AI Platform - Test Report

**Generated:** 2025-08-15T10:40:34.913198  
**Test Level:** integration - Integration tests for component interaction (3-5 minutes)  
**Purpose:** Feature validation, API testing

## Test Summary

**Total Tests:** 12  
**Passed:** 10  
**Failed:** 2  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 12 | 10 | 2 | 0 | 0 | 30.08s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.96s | [FAILED] |

## Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 31.04s
- **Exit Code:** 2

### Backend Configuration
```
--category integration -v --coverage --fail-fast --parallel=4 --markers not real_services
```

### Frontend Configuration
```
--category integration
```

## Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: integration
  Parallel: 4
  Coverage: enabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest integration_tests app/tests/routes -vv -n 4 -x --maxfail=1 --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 4/4 workers
4 workers [86 items]

scheduling tests via LoadScheduling

integration_tests/test_app.py::test_read_main 
integration_tests/test_health.py::test_ready_endpoint_clickhouse_failure 
integration_tests/test_generation_service.py::test_save_and_get_corpus 
app/tests/routes/test_apex_optimizer_agent_route.py::test_apex_optimizer_agent[I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.] 
[gw1][36m [  1%] [0m[31mFAILED[0m integration_tests/test_generation_service.py::test_save_and_get_corpus 
[gw2][36m [  2%] [0m[32mPASSED[0m app/tests/routes/test_apex_optimizer_agent_route.py::test_apex_optimizer_agent[I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.] 
app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_endpoint_requires_authentication 
[gw2][36m [  3%] [0m[32mPASSED[0m app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_endpoint_requires_authentication 
app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_role_verification 
[gw2][36m [  4%] [0m[32mPASSED[0m app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_role_verification 
app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_user_management 
[gw2][36m [  5%] [0m[32mPASSED[0m app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_user_management 
app/tests/routes/test_api_routes_21_30.py::TestAgentRoute::test_agent_message_processing 
[gw2][36m [  6%] [0m[32mPASSED[0m app/tests/routes/test_api_routes_21_30.py::TestAgentRoute::test_agent_message_processing 
[gw0][36m [  8%] [0m[32mPASSED[0m integration_tests/test_app.py::test_read_main 
integration_tests/test_app.py::test_generation_api 
[gw3][36m [  9%] [0m[31mFAILED[0m integration_tests/test_health.py::test_ready_endpoint_clickhouse_failure 
[gw0][36m [ 10%] [0m[32mPASSED[0m integration_tests/test_app.py::test_generation_api 
integration_tests/test_app.py::test_analysis_api 
[gw0][36m [ 11%] [0m[32mPASSED[0m integration_tests/test_app.py::test_analysis_api 
integration_tests/test_generation_service.py::test_content_generation_with_custom_table 
[gw0][36m [ 12%] [0m[32mPASSED[0m integration_tests/test_generation_service.py::test_content_generation_with_custom_table 
integration_tests/test_generation_service.py::test_synthetic_data_generation_with_table_selection 
[gw0][36m [ 13%] [0m[32mPASSED[0m integration_tests/test_generation_service.py::test_synthetic_data_generation_with_table_selection Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
Loaded .env.development file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development
Loaded .env.development.local file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development.local


================================== FAILURES ===================================
[31m[1m__________________________ test_save_and_get_corpus ___________________________[0m
[gw1] win32 -- Python 3.12.4 C:\Users\antho\miniconda3\python.exe
[1m[31mintegration_tests\test_generation_service.py[0m:136: in test_save_and_get_corpus
    [0m[94mawait[39;49;00m save_corpus_to_clickhouse(test_corpus, table_name)[90m[39;49;00m
[1m[31mapp\services\generation_service.py[0m:150: in save_corpus_to_clickhouse
    [0m[94mawait[39;49;00m db.disconnect()[90m[39;49;00m
[1m[31mE   TypeError: object MagicMock can't be used in 'await' expression[0m
---------------------------- Captured stderr setup ----------------------------
2025-08-15 10:40:29.881 | DEBUG    | logging:handle:1028 | Using proactor: IocpProactor
----------------------------- Captured log setup ------------------------------
[35mDEBUG   [0m asyncio:proactor_events.py:634 Using proactor: IocpProactor
---------------------------- Captured stderr call -----------------------------
2025-08-15 10:40:29.907 | INFO     | app.services.generation_service:save_corpus_to_clickhouse:143 | Successfully saved corpus to ClickHouse table: test_corpus_94cd5b404a3348e9b5831978fc4affa2
-------------------------- Captured stderr teardown ---------------------------
2025-08-15 10:40:29.965 | DEBUG    | logging:handle:1028 | Using proactor: IocpProactor
---------------------------- Captured log teardown ----------------------------
[35mDEBUG   [0m asyncio:proactor_events.py:634 Using proactor: IocpProactor
[31m[1m___________________ test_ready_endpoint_clickhouse_failure ____________________[0m
[gw3] win32 -- Python 3.12.4 C:\Users\antho\miniconda3\python.exe
[1m[31mintegration_tests\test_health.py[0m:74: in test_ready_endpoint_clickhouse_failure
    [0m[94massert[39;49;00m response.status_code == [94m503[39;49;00m[90m[39;49;00m
[1m[31mE   assert 200 == 503[0m
[1m[31mE    +  where 200 = <Response [200 OK]>.status_code[0m
---------------------------- Captured stderr setup ----------------------------
2025-08-15 10:40:29.914 | DEBUG    | logging:handle:1028 | Using proactor: IocpProactor
2025-08-15 10:40:29.930 | INFO     | app.startup:initialize_logging:58 | Application startup...
2025-08-15 10:40:29.932 | INFO     | logging:handle:1028 | Multiprocessing configured with method: spawn
2025-08-15 10:40:29.932 | INFO     | app.startup:setup_multiprocessing_env:66 | pytest detected in sys.modules
2025-08-15 10:40:29.933 | INFO     | app.startup:initialize_core_services:141 | Loading key manager...
2025-08-15 10:40:29.933 | INFO     | app.startup:initialize_core_services:143 | Key manager loaded.
2025-08-15 10:40:29.952 | INFO     | app.core.unified_logging:_emit_log:117 | Startup checks skipped (SKIP_STARTUP_CHECKS=true)
2025-08-15 10:40:30.017 | INFO     | app.agents.supervisor.agent_registry:register:70 | Registered agent: triage
2025-08-15 10:40:30.018 | INFO     | app.agents.supervisor.agent_registry:register:70 | Registered agent: data
2025-08-15 10:40:30.019 | INFO     | app.agents.supervisor.agent_registry:register:70 | Registered agent: optimization
2025-08-15 10:40:30.020 | INFO     | app.agents.supervisor.agent_registry:register:70 | Registered agent: actions
2025-08-15 10:40:30.021 | INFO     | app.agents.supervisor.agent_registry:register:70 | Registered agent: reporting
2025-08-15 10:40:30.023 | INFO     | app.agents.supervisor.agent_registry:register:70 | Registered agent: synthetic_data
2025-08-15 10:40:30.026 | INFO     | app.agents.supervisor.agent_registry:register:70 | Registered agent: corpus_admin
2025-08-15 10:40:30.030 | INFO     | app.startup:log_startup_complete:285 | System Ready (Took 0.10s).
----------------------------- Captured log setup ------------------------------
[35mDEBUG   [0m asyncio:proactor_events.py:634 Using proactor: IocpProactor
[32mINFO    [0m app.utils.multiprocessing_cleanup:multiprocessing_cleanup.py:140 Multiprocessing configured with method: spawn
---------------------------- Captured stderr call -----------------------------
2025-08-15 10:40:30.055 | INFO     | app.core.request_context:log_request_details:68 | Request: GET /health/ready | Status: 200 | Duration: 8.14ms | Trace: f6df606e-7f69-4f2d-bf7e-85441c6a6f4c
2025-08-15 10:40:30.061 | INFO     | logging:handle:1028 | HTTP Request: GET http://testserver/health/ready "HTTP/1.1 200 OK"
------------------------------ Captured log call ------------------------------
[32mINFO    [0m httpx:_client.py:1025 HTTP Request: GET http://testserver/health/ready "HTTP/1.1 200 OK"
-------------------------- Captured stderr teardown ---------------------------
2025-08-15 10:40:30.104 | INFO     | app.shutdown:shutdown_cleanup:17 | Application shutdown initiated...
2025-08-15 10:40:30.104 | INFO     | logging:handle:1028 | Multiprocessing resources cleaned up
2025-08-15 10:40:30.207 | INFO     | app.background:shutdown:20 | Shutting down background tasks...
2025-08-15 10:40:30.208 | INFO     | app.background:shutdown:25 | Background tasks shut down.
2025-08-15 10:40:30.208 | INFO     | app.agents.base:shutdown:342 | Shutting down Supervisor
2025-08-15 10:4...(truncated)
```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> jest --forceExit --detectOpenHandles --testMatch **/__tests__/integration/**/*.test.[jt]s?(x)

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

'jest' is not recognized as an internal or external command,
operable program or batch file.

```

## Error Summary

### Backend Errors
- [gw1][36m [  1%] [0m[31mFAILED[0m integration_tests/test_generation_service.py::test_save_and_get_corpus
- [gw3][36m [  9%] [0m[31mFAILED[0m integration_tests/test_health.py::test_ready_endpoint_clickhouse_failure
- [31mFAILED[0m integration_tests/test_generation_service.py::[1mtest_save_and_get_corpus[0m - TypeError: object MagicMock can't be used in 'await' expression
- [31mFAILED[0m integration_tests/test_health.py::[1mtest_ready_endpoint_clickhouse_failure[0m - assert 200 == 503
- [FAIL] TESTS FAILED with exit code 2 after 29.11s


---
*Generated by Netra AI Unified Test Runner v3.0*
