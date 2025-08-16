# Netra AI Platform - Test Report

**Generated:** 2025-08-15T21:05:39.537462  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 4  
**Passed:** 3  
**Failed:** 1  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 4 | 3 | 1 | 0 | 0 | 30.33s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.32s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 30.66s
- **Exit Code:** 255

### Backend Configuration
```
--category unit -v --coverage --fail-fast --parallel=4 --markers not real_services -k app/routes -k test_api -k test_auth
```

### Frontend Configuration
```
--category unit
```

## Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: unit
  Parallel: 4
  Coverage: enabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests/services app/tests/core -vv -n 4 -x --maxfail=1 --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services -k test_auth --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 4/4 workers
4 workers [4 items]

scheduling tests via LoadScheduling

app\tests\core\test_error_handling.py::TestNetraExceptions::test_authorization_error 
app\tests\core\test_core_infrastructure_11_20.py::TestCustomExceptions::test_authentication_error 
app\tests\core\test_missing_tests_validation.py::TestCustomExceptions::test_authentication_exception_details 
app\tests\core\test_error_handling.py::TestNetraExceptions::test_authentication_error 
[gw0][36m [ 25%] [0m[32mPASSED[0m app\tests\core\test_core_infrastructure_11_20.py::TestCustomExceptions::test_authentication_error 
[gw2][36m [ 50%] [0m[32mPASSED[0m app\tests\core\test_error_handling.py::TestNetraExceptions::test_authentication_error 
[gw1][36m [ 75%] [0m[32mPASSED[0m app\tests\core\test_error_handling.py::TestNetraExceptions::test_authorization_error 
[gw3][36m [100%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_validation.py::TestCustomExceptions::test_authentication_exception_details Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
Loaded .env.development file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development
Loaded .env.development.local file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development.local


================================== FAILURES ===================================
[31m[1m_________ TestCustomExceptions.test_authentication_exception_details __________[0m
[gw3] win32 -- Python 3.12.4 C:\Users\antho\miniconda3\python.exe
[1m[31mapp\tests\core\test_missing_tests_validation.py[0m:214: in test_authentication_exception_details
    [0mexc = AuthenticationError([90m[39;49;00m
[1m[31mapp\core\exceptions_auth.py[0m:11: in __init__
    [0m[96msuper[39;49;00m().[92m__init__[39;49;00m([90m[39;49;00m
[1m[31mE   TypeError: NetraException.__init__() got an unexpected keyword argument 'auth_method'[0m
[36m[1m=========================== short test summary info ===========================[0m
[31mFAILED[0m app\tests\core\test_missing_tests_validation.py::[1mTestCustomExceptions::test_authentication_exception_details[0m - TypeError: NetraException.__init__() got an unexpected keyword argument 'auth_method'
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m======================== [31m[1m1 failed[0m, [32m3 passed[0m[31m in 21.31s[0m[31m =========================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 29.51s
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================

2025-08-15 21:05:12.451 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-15 21:05:12.451 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-15 21:05:12.452 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-15 21:05:12.452 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-15 21:05:12.452 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-15 21:05:12.452 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-15 21:05:12.452 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-15 21:05:12.453 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-15 21:05:12.453 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-15 21:05:12.453 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-15 21:05:12.453 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-15 21:05:12.453 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-15 21:05:12.453 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-15 21:05:12.453 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set Gemini API key for LLM configs
2025-08-15 21:05:12.453 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 13 env vars
2025-08-15 21:05:12.453 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-15 21:05:12.456 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-15 21:05:12.456 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 9 secrets from environment variables
2025-08-15 21:05:12.456 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: gemini-api-key, jwt-secret-key, fernet-key
2025-08-15 21:05:12.456 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 9 secrets loaded
2025-08-15 21:05:12.457 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 9 secrets
2025-08-15 21:05:12.457 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 9 secrets (from 9 loaded)
2025-08-15 21:05:12.457 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 3 (gemini-api-key, jwt-secret-key, fernet-key)
2025-08-15 21:05:12.457 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-15 21:05:12.479 | DEBUG    | logging:handle:1028 | loaded lazy attr 'SafeConfigParser': <class 'configparser.ConfigParser'>
2025-08-15 21:05:12.479 | DEBUG    | logging:handle:1028 | loaded lazy attr 'NativeStringIO': <class '_io.StringIO'>
2025-08-15 21:05:12.479 | DEBUG    | logging:handle:1028 | loaded lazy attr 'BytesIO': <class '_io.BytesIO'>
2025-08-15 21:05:12.512 | DEBUG    | logging:handle:1028 | registered 'bcrypt' handler: <class 'passlib.handlers.bcrypt.bcrypt'>
2025-08-15 21:05:12.975 | INFO     | app.db.postgres_core:_create_and_setup_engine:258 | PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling
2025-08-15 21:05:13.181 | DEBUG    | app.services.metrics.agent_metrics:__init__:24 | Initialized AgentMetricsCollector with buffer size 5000
2025-08-15 21:05:13.967 | DEBUG    | logging:handle:1028 | Using orjson library for writing JSON byte strings
2025-08-15 21:05:14.026 | DEBUG    | logging:handle:1028 | Looking up time zone info from registry
2025-08-15 21:05:14.804 | INFO     | app.core.unified_logging:_emit_log:117 | SyntheticDataService initialized successfully
2025-08-15 21:05:15.964 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-15 21:05:15.988 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-15 21:05:16.025 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
2025-08-15 21:05:16.110 | INFO     | app.services.quality_gate.quality_gate_core:__init__:34 | Quality Gate Service initialized
2025-08-15 21:05:16.110 | INFO     | app.services.quality_monitoring.service:__init__:48 | Quality Monitoring Service initialized
2025-08-15 21:05:16.110 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
--- Logging error in Loguru Handler #1 ---
Record was: {'elapsed': datetime.timedelta(seconds=16, microseconds=961511), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='ℹ️'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=22076, name='MainProcess'), 'thread': (id=21560, name='MainThread'), 'time': datetime(2025, 8, 15, 21, 5, 36, 123843, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}
--- Logging error in Loguru Handler #1 ---
Record was: {'elapsed': datetime.timedelta(seconds=16, microseconds=839192), 'exception': None...(truncated)
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

## Error Summary

### Backend Errors
- [gw3][36m [100%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_validation.py::TestCustomExceptions::test_authentication_exception_details Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
- [31mFAILED[0m app\tests\core\test_missing_tests_validation.py::[1mTestCustomExceptions::test_authentication_exception_details[0m - TypeError: NetraException.__init__() got an unexpected keyword argument 'auth_method'
- [FAIL] TESTS FAILED with exit code 2 after 29.51s


---
*Generated by Netra AI Unified Test Runner v3.0*
