# Netra AI Platform - Test Report

**Generated:** 2025-08-15T21:06:45.288800  
**Test Level:** comprehensive-database - Database comprehensive tests (10-15 minutes)  
**Purpose:** Deep validation of all database operations

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
| Backend   | 1 | 0 | 0 | 0 | 1 | 20.01s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** comprehensive-database
- **Description:** Database comprehensive tests (10-15 minutes)
- **Purpose:** Deep validation of all database operations
- **Timeout:** 900s
- **Coverage Enabled:** Yes
- **Total Duration:** 20.01s
- **Exit Code:** 2

### Backend Configuration
```
--coverage --parallel=4 -k database or repository or clickhouse or postgres --fail-fast
```

### Frontend Configuration
```

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
  Category: all
  Parallel: 4
  Coverage: enabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests tests integration_tests -v -n 4 -x --maxfail=1 --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -k database or repository or clickhouse or postgres --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
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
[31m[1m_________ ERROR collecting app/tests/clickhouse/test_data_manager.py __________[0m
ImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\clickhouse\test_data_manager.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\..\miniconda3\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
app\tests\clickhouse\test_data_manager.py:10: in <module>
    from .data_models import LLMEvent, WorkloadMetric, LogEntry
E   ImportError: attempted relative import with no known parent package
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m app/tests/clickhouse/test_data_manager.py
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m============================== [31m[1m1 error[0m[31m in 11.57s[0m[31m ==============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 19.19s
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================

2025-08-15 21:06:28.896 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-15 21:06:28.898 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-15 21:06:28.899 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-15 21:06:28.899 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-15 21:06:28.899 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-15 21:06:28.899 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-15 21:06:28.899 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-15 21:06:28.899 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-15 21:06:28.900 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-15 21:06:28.900 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-15 21:06:28.900 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-15 21:06:28.900 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-15 21:06:28.900 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-15 21:06:28.901 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set Gemini API key for LLM configs
2025-08-15 21:06:28.901 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 13 env vars
2025-08-15 21:06:28.901 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-15 21:06:28.902 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-15 21:06:28.903 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 9 secrets from environment variables
2025-08-15 21:06:28.903 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: gemini-api-key, jwt-secret-key, fernet-key
2025-08-15 21:06:28.903 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 9 secrets loaded
2025-08-15 21:06:28.903 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 9 secrets
2025-08-15 21:06:28.904 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 9 secrets (from 9 loaded)
2025-08-15 21:06:28.904 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 3 (gemini-api-key, jwt-secret-key, fernet-key)
2025-08-15 21:06:28.904 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-15 21:06:28.927 | DEBUG    | logging:handle:1028 | loaded lazy attr 'SafeConfigParser': <class 'configparser.ConfigParser'>
2025-08-15 21:06:28.927 | DEBUG    | logging:handle:1028 | loaded lazy attr 'NativeStringIO': <class '_io.StringIO'>
2025-08-15 21:06:28.927 | DEBUG    | logging:handle:1028 | loaded lazy attr 'BytesIO': <class '_io.BytesIO'>
2025-08-15 21:06:28.964 | DEBUG    | logging:handle:1028 | registered 'bcrypt' handler: <class 'passlib.handlers.bcrypt.bcrypt'>
2025-08-15 21:06:29.412 | INFO     | app.db.postgres_core:_create_and_setup_engine:258 | PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling
2025-08-15 21:06:29.627 | DEBUG    | app.services.metrics.agent_metrics:__init__:24 | Initialized AgentMetricsCollector with buffer size 5000
2025-08-15 21:06:30.405 | DEBUG    | logging:handle:1028 | Using orjson library for writing JSON byte strings
2025-08-15 21:06:30.469 | DEBUG    | logging:handle:1028 | Looking up time zone info from registry
2025-08-15 21:06:31.100 | INFO     | app.core.unified_logging:_emit_log:117 | SyntheticDataService initialized successfully
2025-08-15 21:06:32.026 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-15 21:06:32.048 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-15 21:06:32.078 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
2025-08-15 21:06:32.160 | INFO     | app.services.quality_gate.quality_gate_core:__init__:34 | Quality Gate Service initialized
2025-08-15 21:06:32.160 | INFO     | app.services.quality_monitoring.service:__init__:48 | Quality Monitoring Service initialized
2025-08-15 21:06:32.160 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
Exception ignored in atexit callback: <bound method MultiprocessingResourceManager.cleanup_all of <app.utils.multiprocessing_cleanup.MultiprocessingResourceManager object at 0x000001AF028FFE60>>
Traceback (most recent call last):
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\utils\multiprocessing_cleanup.py", line 63, in cleanup_all
Exception ignored in atexit callback: <bound method MultiprocessingResourceManager.cleanup_all of <app.utils.multiprocessing_cleanup.MultiprocessingResourceManager object at 0x0000023E9C833EC0>>
Traceback (most recent call last):
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\utils\multiprocessing_cleanup.py", line 63, in cleanup_all
Exception ignored in atexit callback: <bound method MultiprocessingResourceManager.cleanup_all of <app.utils.multiprocessing_cleanup.MultiprocessingResourceManager object at 0x00000216F8F87A10>>
Traceback (most recent call last):
  File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\utils\multiprocessing_cleanup.py", line 63, in cleanup_all
    self._cleanup_processes()
    self._cleanup_processes()
    self._cleanup_processes()
    ^^^^^^^^^^^^^^^^^^^^^^^
    ^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'MultiprocessingResourceManager' object has no attribute '_cleanup_processes'
AttributeError: 'MultiprocessingResourceManager' object has no attribute '_cleanup_processes'
    ^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'MultiprocessingResourceManager' object has no attribute '_cleanup_processes'
Exception ignored in atexit callback: <bound method MultiprocessingResourceManager.cleanup_all of <app.utils.multiprocessing_cleanup.MultiprocessingResourceManager object at 0x000001AAEEB73F80>>
Traceback (most r...(truncated)
```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m_________ ERROR collecting app/tests/clickhouse/test_data_manager.py __________[0m
- [31mERROR[0m app/tests/clickhouse/test_data_manager.py
- [FAIL] TESTS FAILED with exit code 2 after 19.19s


---
*Generated by Netra AI Unified Test Runner v3.0*
