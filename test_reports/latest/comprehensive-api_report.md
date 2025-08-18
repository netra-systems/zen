# Netra AI Platform - Test Report

**Generated:** 2025-08-17T18:07:47.405791  
**Test Level:** comprehensive-api - API comprehensive tests (10-15 minutes)  
**Purpose:** Deep validation of all API endpoints

## Test Summary

**Total Tests:** 2  
**Passed:** 0  
**Failed:** 0  
**Skipped:** 1  
**Errors:** 1  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 2 | 0 | 0 | 1 | 1 | 75.49s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** comprehensive-api
- **Description:** API comprehensive tests (10-15 minutes)
- **Purpose:** Deep validation of all API endpoints
- **Timeout:** 900s
- **Coverage Enabled:** Yes
- **Total Duration:** 75.49s
- **Exit Code:** 2

### Backend Configuration
```
--coverage --parallel=4 -k routes or api --fail-fast
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
  pytest app/tests tests integration_tests -v -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -k routes or api -p test_framework.pytest_bad_test_plugin --test-component backend
================================================================================
[BAD TEST DETECTOR] Initialized for backend tests
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 4/4 workers

================================================================================
BAD TEST DETECTION REPORT
================================================================================

Total Bad Tests Detected: 0
Total Test Runs Analyzed: 98

================================================================================


=================================== ERRORS ====================================
[31m[1m__________ ERROR collecting tests/unit/auth_service/test_helpers.py ___________[0m
ImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\unit\auth_service\test_helpers.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\..\miniconda3\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
app\tests\unit\auth_service\test_helpers.py:15: in <module>
    from app.auth.url_validators import (
E   ImportError: cannot import name 'validate_return_url_security' from 'app.auth.url_validators' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\auth\url_validators.py)
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m app\tests\unit\auth_service\test_helpers.py
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m=================== [33m1 skipped[0m, [31m[1m1 error[0m[31m in 60.11s (0:01:00)[0m[31m ====================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 74.27s
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================

2025-08-17 18:06:38.722 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-17 18:06:38.723 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-17 18:06:38.724 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-17 18:06:38.724 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-17 18:06:38.725 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-17 18:06:38.725 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-17 18:06:38.725 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-17 18:06:38.726 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-17 18:06:38.726 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-17 18:06:38.727 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-17 18:06:38.727 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-17 18:06:38.727 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-17 18:06:38.727 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-17 18:06:38.729 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 12 env vars
2025-08-17 18:06:38.730 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-17 18:06:38.730 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-17 18:06:38.731 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 8 secrets from environment variables
2025-08-17 18:06:38.732 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: jwt-secret-key, fernet-key
2025-08-17 18:06:38.733 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 8 secrets loaded
2025-08-17 18:06:38.733 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 8 secrets
2025-08-17 18:06:38.734 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 8 secrets (from 8 loaded)
2025-08-17 18:06:38.734 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 2 (jwt-secret-key, fernet-key)
2025-08-17 18:06:38.734 | WARNING  | app.core.unified_logging:_emit_log:117 | Critical secrets not found in loaded secrets: 1 (gemini-api-key)
2025-08-17 18:06:38.736 | WARNING  | app.core.unified_logging:_emit_log:117 | LLM configuration warnings: Gemini API key is not configured (required for all LLM operations)
2025-08-17 18:06:38.736 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-17 18:06:38.786 | DEBUG    | logging:handle:1028 | loaded lazy attr 'SafeConfigParser': <class 'configparser.ConfigParser'>
2025-08-17 18:06:38.786 | DEBUG    | logging:handle:1028 | loaded lazy attr 'NativeStringIO': <class '_io.StringIO'>
2025-08-17 18:06:38.786 | DEBUG    | logging:handle:1028 | loaded lazy attr 'BytesIO': <class '_io.BytesIO'>
2025-08-17 18:06:38.853 | DEBUG    | logging:handle:1028 | registered 'bcrypt' handler: <class 'passlib.handlers.bcrypt.bcrypt'>
2025-08-17 18:06:39.342 | INFO     | app.db.postgres_core:_create_and_setup_engine:258 | PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling
2025-08-17 18:06:39.750 | DEBUG    | app.services.metrics.agent_metrics:__init__:24 | Initialized AgentMetricsCollector with buffer size 5000
2025-08-17 18:06:41.707 | DEBUG    | logging:handle:1028 | Using orjson library for writing JSON byte strings
2025-08-17 18:06:41.871 | DEBUG    | logging:handle:1028 | Looking up time zone info from registry
2025-08-17 18:06:42.639 | INFO     | logging:handle:1028 | Session middleware config: same_site=lax, https_only=False, environment=development
2025-08-17 18:06:42.807 | INFO     | app.core.unified_logging:_emit_log:117 | SyntheticDataService initialized successfully
2025-08-17 18:06:43.808 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-17 18:06:43.896 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-17 18:06:44.294 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
2025-08-17 18:06:44.377 | INFO     | app.services.quality_gate.quality_gate_core:__init__:28 | Quality Gate Service initialized
2025-08-17 18:06:44.378 | INFO     | app.services.quality_monitoring.service:__init__:48 | Quality Monitoring Service initialized
2025-08-17 18:06:44.378 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
--- Logging error in Loguru Handler #7 ---
Record was: {'elapsed': datetime.timedelta(seconds=55, microseconds=43186), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='ℹ️'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=37052, name='MainProcess'), 'thread': (id=28036, name='MainThread'), 'time': datetime(2025, 8, 17, 18, 7, 44, 486105, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}
Traceback (most recent call last):
  File "C:\Users\antho\miniconda3\Lib\site-packages\loguru\_handler.py", line 315, in _queued_writer
    self._sink.write(message)
  File "C:\Users\antho\miniconda3\Lib\site-packages\loguru\_simple_sinks.py", line 16, in write
    self._st...(truncated)
```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m__________ ERROR collecting tests/unit/auth_service/test_helpers.py ___________[0m
- [31mERROR[0m app\tests\unit\auth_service\test_helpers.py
- [FAIL] TESTS FAILED with exit code 2 after 74.27s


---
*Generated by Netra AI Unified Test Runner v3.0*
