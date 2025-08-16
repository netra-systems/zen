# Netra AI Platform - Test Report

**Generated:** 2025-08-15T19:41:11.093126  
**Test Level:** integration - Integration tests for component interaction (3-5 minutes)  
**Purpose:** Feature validation, API testing

## Test Summary

**Total Tests:** 1  
**Passed:** 0  
**Failed:** 0  
**Skipped:** 0  
**Errors:** 1  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 1 | 0 | 0 | 0 | 1 | 23.03s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 38.84s | [FAILED] |

## Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 61.87s
- **Exit Code:** 15

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
Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
Loaded .env.development file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development
Loaded .env.development.local file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development.local
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

=================================== ERRORS ====================================
[31m[1m_______________ ERROR collecting integration_tests/test_app.py ________________[0m
ImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\integration_tests\test_app.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\..\miniconda3\Lib\site-packages\_pytest\python.py:498: in importtestmodule
    mod = import_path(
..\..\..\..\miniconda3\Lib\site-packages\_pytest\pathlib.py:587: in import_path
    importlib.import_module(module_name)
..\..\..\..\miniconda3\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen importlib._bootstrap>:1387: in _gcd_import
    ???
<frozen importlib._bootstrap>:1360: in _find_and_load
    ???
<frozen importlib._bootstrap>:1331: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:935: in _load_unlocked
    ???
..\..\..\..\miniconda3\Lib\site-packages\_pytest\assertion\rewrite.py:186: in exec_module
    exec(co, module.__dict__)
integration_tests\test_app.py:9: in <module>
    from app.dependencies import get_async_db
E   ImportError: cannot import name 'get_async_db' from 'app.dependencies' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\dependencies.py)
------------------------------- Captured stdout -------------------------------
Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
Loaded .env.development file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development
Loaded .env.development.local file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development.local
------------------------------- Captured stderr -------------------------------
2025-08-15 19:40:23.345 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-15 19:40:23.346 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set Gemini API key for LLM configs
2025-08-15 19:40:23.346 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 13 env vars
2025-08-15 19:40:23.346 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-15 19:40:23.346 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-15 19:40:23.352 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 9 secrets from environment variables
2025-08-15 19:40:23.352 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: gemini-api-key, jwt-secret-key, fernet-key
2025-08-15 19:40:23.352 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 9 secrets loaded
2025-08-15 19:40:23.353 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 9 secrets
2025-08-15 19:40:23.354 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 9 secrets (from 9 loaded)
2025-08-15 19:40:23.354 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 3 (gemini-api-key, jwt-secret-key, fernet-key)
2025-08-15 19:40:23.354 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-15 19:40:23.387 | DEBUG    | logging:handle:1028 | loaded lazy attr 'SafeConfigParser': <class 'configparser.ConfigParser'>
2025-08-15 19:40:23.388 | DEBUG    | logging:handle:1028 | loaded lazy attr 'NativeStringIO': <class '_io.StringIO'>
2025-08-15 19:40:23.388 | DEBUG    | logging:handle:1028 | loaded lazy attr 'BytesIO': <class '_io.BytesIO'>
2025-08-15 19:40:23.437 | DEBUG    | logging:handle:1028 | registered 'bcrypt' handler: <class 'passlib.handlers.bcrypt.bcrypt'>
2025-08-15 19:40:23.740 | INFO     | app.db.postgres_core:_initialize_async_engine:159 | PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling
2025-08-15 19:40:24.009 | DEBUG    | app.services.metrics.agent_metrics:__init__:24 | Initialized AgentMetricsCollector with buffer size 5000
2025-08-15 19:40:25.310 | DEBUG    | logging:handle:1028 | Using orjson library for writing JSON byte strings
2025-08-15 19:40:25.390 | DEBUG    | logging:handle:1028 | Looking up time zone info from registry
2025-08-15 19:40:26.230 | INFO     | app.core.unified_logging:_emit_log:117 | SyntheticDataService initialized successfully
2025-08-15 19:40:27.517 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-15 19:40:27.554 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-15 19:40:27.610 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
2025-08-15 19:40:27.746 | INFO     | app.services.quality_gate.quality_gate_core:__init__:34 | Quality Gate Service initialized
2025-08-15 19:40:27.751 | INFO     | app.services.quality_monitoring.service:__init__:48 | Quality Monitoring Service initialized
2025-08-15 19:40:27.751 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m integration_tests/test_app.py
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m============================== [31m[1m1 error[0m[31m in 13.15s[0m[31m ==============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 22.13s
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================

2025-08-15 19:40:13.691 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-15 19:40:13.692 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-15 19:40:13.692 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-15 19:40:13.692 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-15 19:40:13.692 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-15 19:40:13.693 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key fr...(truncated)
```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> jest --forceExit --detectOpenHandles --testMatch **/__tests__/integration/**/*.test.[jt]s?(x)



```

## Error Summary

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m_______________ ERROR collecting integration_tests/test_app.py ________________[0m
- [31mERROR[0m integration_tests/test_app.py
- [FAIL] TESTS FAILED with exit code 2 after 22.13s


---
*Generated by Netra AI Unified Test Runner v3.0*
