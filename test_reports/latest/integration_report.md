# Netra AI Platform - Test Report

**Generated:** 2025-08-17T19:19:36.808946  
**Test Level:** integration - Integration tests for component interaction (3-5 minutes)  
**Purpose:** Feature validation, API testing

## Test Summary

**Total Tests:** 0  
**Passed:** 0  
**Failed:** 0  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 0 | 0 | 0 | 0 | 0 | 8.98s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.14s | [FAILED] |

## Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 9.13s
- **Exit Code:** 4

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
  pytest integration_tests app/tests/routes -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services -p test_framework.pytest_bad_test_plugin --test-component backend
================================================================================
Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
Loaded .env.development file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development
Loaded .env.development.local file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development.local
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 8.02s
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================

2025-08-17 19:19:33.515 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-17 19:19:33.515 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-17 19:19:33.515 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-17 19:19:33.515 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-17 19:19:33.515 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-17 19:19:33.515 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-17 19:19:33.515 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-17 19:19:33.515 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-17 19:19:33.515 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-17 19:19:33.515 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-17 19:19:33.515 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-17 19:19:33.522 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-17 19:19:33.522 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-17 19:19:33.522 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 12 env vars
2025-08-17 19:19:33.522 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-17 19:19:33.522 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-17 19:19:33.523 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 8 secrets from environment variables
2025-08-17 19:19:33.523 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: jwt-secret-key, fernet-key
2025-08-17 19:19:33.523 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 8 secrets loaded
2025-08-17 19:19:33.523 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 8 secrets
2025-08-17 19:19:33.525 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 8 secrets (from 8 loaded)
2025-08-17 19:19:33.525 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 2 (jwt-secret-key, fernet-key)
2025-08-17 19:19:33.525 | WARNING  | app.core.unified_logging:_emit_log:117 | Critical secrets not found in loaded secrets: 1 (gemini-api-key)
2025-08-17 19:19:33.526 | WARNING  | app.core.unified_logging:_emit_log:117 | LLM configuration warnings: Gemini API key is not configured (required for all LLM operations)
2025-08-17 19:19:33.526 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-17 19:19:33.843 | INFO     | app.db.postgres_core:_create_and_setup_engine:258 | PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling
2025-08-17 19:19:34.091 | DEBUG    | app.services.metrics.agent_metrics:__init__:24 | Initialized AgentMetricsCollector with buffer size 5000
2025-08-17 19:19:35.371 | DEBUG    | logging:handle:1028 | Using orjson library for writing JSON byte strings
2025-08-17 19:19:35.446 | DEBUG    | logging:handle:1028 | Looking up time zone info from registry
ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\conftest.py'.
app\tests\conftest.py:52: in <module>
    from app.main import app
app\main.py:78: in <module>
    from app.core.app_factory import create_app
app\core\app_factory.py:9: in <module>
    from app.core.lifespan_manager import lifespan
app\core\lifespan_manager.py:9: in <module>
    from app.shutdown import run_complete_shutdown
app\shutdown.py:12: in <module>
    from app.ws_manager import manager as websocket_manager
app\ws_manager.py:33: in <module>
    class WebSocketManager:
app\ws_manager.py:133: in WebSocketManager
    def connection_manager(self) -> ConnectionManager:
                                    ^^^^^^^^^^^^^^^^^
E   NameError: name 'ConnectionManager' is not defined
--- Logging error in Loguru Handler #1 ---
Record was: {'elapsed': datetime.timedelta(seconds=4, microseconds=836391), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='\u2139\ufe0f'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=53580, name='MainProcess'), 'thread': (id=3340, name='MainThread'), 'time': datetime(2025, 8, 17, 19, 19, 36, 85009, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}
Traceback (most recent call last):
  File "C:\Users\antho\miniconda3\Lib\site-packages\loguru\_handler.py", line 315, in _queued_writer
    self._sink.write(message)
  File "C:\Users\antho\miniconda3\Lib\site-packages\loguru\_simple_sinks.py", line 16, in write
    self._stream.write(message)
ValueError: I/O operation on closed file.
--- End of logging error ---

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
---
*Generated by Netra AI Unified Test Runner v3.0*
