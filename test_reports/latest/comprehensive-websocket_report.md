# Netra AI Platform - Test Report

**Generated:** 2025-08-15T13:35:46.734356  
**Test Level:** comprehensive-websocket - WebSocket comprehensive tests (5-10 minutes)  
**Purpose:** Deep validation of WebSocket functionality

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
| Backend   | 2 | 0 | 0 | 1 | 1 | 29.28s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** comprehensive-websocket
- **Description:** WebSocket comprehensive tests (5-10 minutes)
- **Purpose:** Deep validation of WebSocket functionality
- **Timeout:** 600s
- **Coverage Enabled:** Yes
- **Total Duration:** 29.28s
- **Exit Code:** 2

### Backend Configuration
```
--coverage --parallel=2 -k websocket or ws_manager --fail-fast
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
  Parallel: 2
  Coverage: enabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests tests integration_tests -v -n 2 -x --maxfail=1 --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -k websocket or ws_manager --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 2/2 workers

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
[31m======================== [33m1 skipped[0m, [31m[1m1 error[0m[31m in 19.96s[0m[31m =========================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 28.30s
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================

C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\llm\test_llm_integration_real.py:26: PytestCollectionWarning: cannot collect test class 'TestResponseModel' because it has a __init__ constructor (from: app/tests/llm/test_llm_integration_real.py)
  class TestResponseModel(BaseModel):
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\llm\test_llm_integration_real.py:26: PytestCollectionWarning: cannot collect test class 'TestResponseModel' because it has a __init__ constructor (from: app/tests/llm/test_llm_integration_real.py)
  class TestResponseModel(BaseModel):
2025-08-15 13:35:21.552 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-15 13:35:21.553 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-15 13:35:21.553 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-15 13:35:21.553 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-15 13:35:21.554 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-15 13:35:21.554 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-15 13:35:21.554 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-15 13:35:21.554 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-15 13:35:21.554 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-15 13:35:21.554 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-15 13:35:21.555 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-15 13:35:21.555 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-15 13:35:21.555 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-15 13:35:21.555 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set Gemini API key for LLM configs
2025-08-15 13:35:21.555 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 13 env vars
2025-08-15 13:35:21.555 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-15 13:35:21.556 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-15 13:35:21.556 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 9 secrets from environment variables
2025-08-15 13:35:21.556 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: gemini-api-key, jwt-secret-key, fernet-key
2025-08-15 13:35:21.558 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 9 secrets loaded
2025-08-15 13:35:21.558 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 9 secrets
2025-08-15 13:35:21.559 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 9 secrets (from 9 loaded)
2025-08-15 13:35:21.560 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 3 (gemini-api-key, jwt-secret-key, fernet-key)
2025-08-15 13:35:21.560 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-15 13:35:21.590 | DEBUG    | logging:handle:1028 | loaded lazy attr 'SafeConfigParser': <class 'configparser.ConfigParser'>
2025-08-15 13:35:21.591 | DEBUG    | logging:handle:1028 | loaded lazy attr 'NativeStringIO': <class '_io.StringIO'>
2025-08-15 13:35:21.591 | DEBUG    | logging:handle:1028 | loaded lazy attr 'BytesIO': <class '_io.BytesIO'>
2025-08-15 13:35:21.634 | DEBUG    | logging:handle:1028 | registered 'bcrypt' handler: <class 'passlib.handlers.bcrypt.bcrypt'>
2025-08-15 13:35:21.936 | INFO     | app.db.postgres:<module>:237 | PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling
2025-08-15 13:35:23.071 | DEBUG    | logging:handle:1028 | Using orjson library for writing JSON byte strings
2025-08-15 13:35:23.132 | DEBUG    | logging:handle:1028 | Looking up time zone info from registry
2025-08-15 13:35:23.753 | INFO     | app.core.unified_logging:_emit_log:117 | SyntheticDataService initialized successfully
2025-08-15 13:35:24.716 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-15 13:35:24.741 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-15 13:35:24.787 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
2025-08-15 13:35:24.900 | INFO     | app.services.quality_gate.quality_gate_core:__init__:34 | Quality Gate Service initialized
2025-08-15 13:35:24.901 | INFO     | app.services.quality_monitoring.service:__init__:48 | Quality Monitoring Service initialized
2025-08-15 13:35:24.901 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
--- Logging error in Loguru Handler #5 ---
Record was: {'elapsed': datetime.timedelta(seconds=15, microseconds=482555), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='ℹ️'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=38012, name='MainProcess'), 'thread': (id=42168, name='MainThread'), 'time': datetime(2025, 8, 15, 13, 35, 44, 351580, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}
Traceback (most recent call last):
  File "C:\Users\antho\miniconda3\Lib\site-packages\loguru\_handler.py", line 315, in _queued_writer
    self._sink.write(message)
  File "C:\Users\antho\miniconda3\Lib\site-packages\loguru\_simple_sinks.py", line 16, in write
    self._stream.write(message)
ValueError: I/O operation on closed file.
--- End of logging error ---
--- Logging error in Loguru Handler #5 ---
Record was: {'elapsed': datetime.timedelta(seconds=15, microseconds=649869), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'han...(truncated)
```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m____ ERROR collecting app/tests/performance/test_corpus_generation_perf.py ____[0m
- [31mERROR[0m app/tests/performance/test_corpus_generation_perf.py
- [FAIL] TESTS FAILED with exit code 2 after 28.30s


---
*Generated by Netra AI Unified Test Runner v3.0*
