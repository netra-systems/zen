# Netra AI Platform - Test Report

**Generated:** 2025-08-15T13:19:36.159477  
**Test Level:** comprehensive-database - Database comprehensive tests (10-15 minutes)  
**Purpose:** Deep validation of all database operations

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
| Backend   | 2 | 0 | 0 | 1 | 1 | 22.37s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** comprehensive-database
- **Description:** Database comprehensive tests (10-15 minutes)
- **Purpose:** Deep validation of all database operations
- **Timeout:** 900s
- **Coverage Enabled:** Yes
- **Total Duration:** 22.37s
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
[31m[1m____ ERROR collecting app/tests/performance/test_corpus_generation_perf.py ____[0m
ImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\performance\test_corpus_generation_perf.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\..\miniconda3\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
app\tests\performance\test_corpus_generation_perf.py:16: in <module>
    from app.services.synthetic_data.service import SyntheticDataService
E   ModuleNotFoundError: No module named 'app.services.synthetic_data.service'
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m app/tests/performance/test_corpus_generation_perf.py
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m======================== [33m1 skipped[0m, [31m[1m1 error[0m[31m in 14.58s[0m[31m =========================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 21.66s
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================

C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\llm\test_llm_integration_real.py:26: PytestCollectionWarning: cannot collect test class 'TestResponseModel' because it has a __init__ constructor (from: app/tests/llm/test_llm_integration_real.py)
  class TestResponseModel(BaseModel):
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\llm\test_llm_integration_real.py:26: PytestCollectionWarning: cannot collect test class 'TestResponseModel' because it has a __init__ constructor (from: app/tests/llm/test_llm_integration_real.py)
  class TestResponseModel(BaseModel):
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\llm\test_llm_integration_real.py:26: PytestCollectionWarning: cannot collect test class 'TestResponseModel' because it has a __init__ constructor (from: app/tests/llm/test_llm_integration_real.py)
  class TestResponseModel(BaseModel):
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\llm\test_llm_integration_real.py:26: PytestCollectionWarning: cannot collect test class 'TestResponseModel' because it has a __init__ constructor (from: app/tests/llm/test_llm_integration_real.py)
  class TestResponseModel(BaseModel):
2025-08-15 13:19:17.279 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-15 13:19:17.280 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-15 13:19:17.280 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-15 13:19:17.280 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-15 13:19:17.280 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-15 13:19:17.280 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-15 13:19:17.280 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-15 13:19:17.281 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-15 13:19:17.281 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-15 13:19:17.281 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-15 13:19:17.281 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-15 13:19:17.282 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-15 13:19:17.282 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-15 13:19:17.282 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set Gemini API key for LLM configs
2025-08-15 13:19:17.282 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 13 env vars
2025-08-15 13:19:17.283 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-15 13:19:17.284 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-15 13:19:17.285 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 9 secrets from environment variables
2025-08-15 13:19:17.285 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: gemini-api-key, jwt-secret-key, fernet-key
2025-08-15 13:19:17.285 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 9 secrets loaded
2025-08-15 13:19:17.285 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 9 secrets
2025-08-15 13:19:17.286 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 9 secrets (from 9 loaded)
2025-08-15 13:19:17.286 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 3 (gemini-api-key, jwt-secret-key, fernet-key)
2025-08-15 13:19:17.286 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-15 13:19:17.311 | DEBUG    | logging:handle:1028 | loaded lazy attr 'SafeConfigParser': <class 'configparser.ConfigParser'>
2025-08-15 13:19:17.311 | DEBUG    | logging:handle:1028 | loaded lazy attr 'NativeStringIO': <class '_io.StringIO'>
2025-08-15 13:19:17.311 | DEBUG    | logging:handle:1028 | loaded lazy attr 'BytesIO': <class '_io.BytesIO'>
2025-08-15 13:19:17.348 | DEBUG    | logging:handle:1028 | registered 'bcrypt' handler: <class 'passlib.handlers.bcrypt.bcrypt'>
2025-08-15 13:19:17.613 | INFO     | app.db.postgres:<module>:236 | PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling
2025-08-15 13:19:18.698 | DEBUG    | logging:handle:1028 | Using orjson library for writing JSON byte strings
2025-08-15 13:19:18.759 | DEBUG    | logging:handle:1028 | Looking up time zone info from registry
2025-08-15 13:19:19.303 | INFO     | app.core.unified_logging:_emit_log:117 | SyntheticDataService initialized successfully
2025-08-15 13:19:20.104 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-15 13:19:20.125 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-15 13:19:20.158 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
2025-08-15 13:19:20.243 | INFO     | app.services.quality_gate.quality_gate_core:__init__:34 | Quality Gate Service initialized
2025-08-15 13:19:20.243 | INFO     | app.services.quality_monitoring.service:__init__:48 | Quality Monitoring Service initialized
2025-08-15 13:19:20.243 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
--- Logging error in Loguru Handler #5 ---
Record was: {'elapsed': datetime.timedelta(seconds=11, microseconds=438057), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='ℹ️'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=16392, name='MainProcess'), 'thread': (id=45152, name='MainThread'), 'time': datetime(2025, 8, 15, 13, 19, 34, 488181, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylig...(truncated)
```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m____ ERROR collecting app/tests/performance/test_corpus_generation_perf.py ____[0m
- [31mERROR[0m app/tests/performance/test_corpus_generation_perf.py
- [FAIL] TESTS FAILED with exit code 2 after 21.66s


---
*Generated by Netra AI Unified Test Runner v3.0*
