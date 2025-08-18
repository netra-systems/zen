# Netra AI Platform - Test Report

**Generated:** 2025-08-17T18:01:57.514154  
**Test Level:** comprehensive - Full test suite with coverage (30-45 minutes)  
**Purpose:** Pre-release validation, full system testing

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
| Backend   | 1 | 0 | 0 | 0 | 1 | 36.10s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.16s | [FAILED] |

## Environment and Configuration

- **Test Level:** comprehensive
- **Description:** Full test suite with coverage (30-45 minutes)
- **Purpose:** Pre-release validation, full system testing
- **Timeout:** 2700s
- **Coverage Enabled:** Yes
- **Total Duration:** 36.27s
- **Exit Code:** 2

### Backend Configuration
```
app/tests tests integration_tests --coverage --parallel=6 --html-output --fail-fast
```

### Frontend Configuration
```
--coverage
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
  Parallel: 6
  Coverage: enabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests tests integration_tests -v -n 6 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 --html=reports/tests/report.html --self-contained-html -p test_framework.pytest_bad_test_plugin --test-component backend
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
created: 6/6 workers

================================================================================
BAD TEST DETECTION REPORT
================================================================================

Total Bad Tests Detected: 0
Total Test Runs Analyzed: 93

================================================================================


=================================== ERRORS ====================================
[31m[1m_______ ERROR collecting tests/auth/test_auth_middleware_integration.py _______[0m
ImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\auth\test_auth_middleware_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\..\miniconda3\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
app\tests\auth\test_auth_middleware_integration.py:20: in <module>
    from app.auth.auth_service import app
E   ModuleNotFoundError: No module named 'app.auth.auth_service'
- Generated html report: file:///C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/reports/tests/report.html -
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m app\tests\auth\test_auth_middleware_integration.py
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m============================== [31m[1m1 error[0m[31m in 21.42s[0m[31m ==============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 35.04s

[Report] HTML Report: reports/tests/report.html
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================

2025-08-17 18:01:27.827 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-17 18:01:27.828 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-17 18:01:27.828 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-17 18:01:27.828 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-17 18:01:27.828 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-17 18:01:27.828 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-17 18:01:27.828 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-17 18:01:27.829 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-17 18:01:27.829 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-17 18:01:27.829 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-17 18:01:27.830 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-17 18:01:27.831 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-17 18:01:27.831 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-17 18:01:27.832 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 12 env vars
2025-08-17 18:01:27.832 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-17 18:01:27.833 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-17 18:01:27.835 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 8 secrets from environment variables
2025-08-17 18:01:27.836 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: jwt-secret-key, fernet-key
2025-08-17 18:01:27.836 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 8 secrets loaded
2025-08-17 18:01:27.837 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 8 secrets
2025-08-17 18:01:27.838 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 8 secrets (from 8 loaded)
2025-08-17 18:01:27.838 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 2 (jwt-secret-key, fernet-key)
2025-08-17 18:01:27.839 | WARNING  | app.core.unified_logging:_emit_log:117 | Critical secrets not found in loaded secrets: 1 (gemini-api-key)
2025-08-17 18:01:27.840 | WARNING  | app.core.unified_logging:_emit_log:117 | LLM configuration warnings: Gemini API key is not configured (required for all LLM operations)
2025-08-17 18:01:27.840 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-17 18:01:27.887 | DEBUG    | logging:handle:1028 | loaded lazy attr 'SafeConfigParser': <class 'configparser.ConfigParser'>
2025-08-17 18:01:27.887 | DEBUG    | logging:handle:1028 | loaded lazy attr 'NativeStringIO': <class '_io.StringIO'>
2025-08-17 18:01:27.888 | DEBUG    | logging:handle:1028 | loaded lazy attr 'BytesIO': <class '_io.BytesIO'>
2025-08-17 18:01:27.957 | DEBUG    | logging:handle:1028 | registered 'bcrypt' handler: <class 'passlib.handlers.bcrypt.bcrypt'>
2025-08-17 18:01:28.392 | INFO     | app.db.postgres_core:_create_and_setup_engine:258 | PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling
2025-08-17 18:01:28.773 | DEBUG    | app.services.metrics.agent_metrics:__init__:24 | Initialized AgentMetricsCollector with buffer size 5000
2025-08-17 18:01:30.427 | DEBUG    | logging:handle:1028 | Using orjson library for writing JSON byte strings
2025-08-17 18:01:30.535 | DEBUG    | logging:handle:1028 | Looking up time zone info from registry
2025-08-17 18:01:31.040 | INFO     | logging:handle:1028 | Session middleware config: same_site=lax, https_only=False, environment=development
2025-08-17 18:01:31.188 | INFO     | app.core.unified_logging:_emit_log:117 | SyntheticDataService initialized successfully
2025-08-17 18:01:32.708 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-17 18:01:32.770 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-17 18:01:32.927 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
2025-08-17 18:01:33.009 | INFO     | app.services.quality_gate.quality_gate_core:__init__:28 | Quality Gate Service initialized
2025-08-17 18:01:33.009 | INFO     | app.services.quality_monitoring.service:__init__:48 | Quality Monitoring Service initialized
2025-08-17 18:01:33.010 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
--- Logging error in Loguru Handler #2 ---
Record was: {'elapsed': datetime.timedelta(seconds=15, microseconds=870381), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='ℹ️'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=44796, name='MainProcess'), 'thread': (id=43136, name='MainThread'), 'time': datetime(2025, 8, 17, 18, 1, 55, 135024, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}
--- Logging error in Loguru Handler #2 ---
--- Logging error in Loguru Handler #2 ---
Record was: {'elapsed': datetime.timedelta(seconds=15, microseconds=466703), 'exception':...(truncated)
```

### Frontend Output
```

usage: test_frontend.py [-h]
                        [--category {unit,integration,components,hooks,store,websocket,auth,e2e,smoke}]
                        [--keyword KEYWORD] [--e2e] [--cypress-open] [--watch]
                        [--coverage] [--update-snapshots] [--lint] [--fix]
                        [--type-check] [--build] [--check-deps]
                        [--install-deps] [--verbose] [--isolation]
                        [--cleanup-on-exit]
                        [tests ...]
test_frontend.py: error: unrecognized arguments: --no-cov -x --maxfail=1

```

## Error Summary

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m_______ ERROR collecting tests/auth/test_auth_middleware_integration.py _______[0m
- [31mERROR[0m app\tests\auth\test_auth_middleware_integration.py
- [FAIL] TESTS FAILED with exit code 2 after 35.04s


---
*Generated by Netra AI Unified Test Runner v3.0*
