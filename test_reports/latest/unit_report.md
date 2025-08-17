# Netra AI Platform - Test Report

**Generated:** 2025-08-17T11:57:37.225608  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

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
| Backend   | 0 | 0 | 0 | 0 | 0 | 7.92s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.26s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 8.18s
- **Exit Code:** 15

### Backend Configuration
```
--category unit -v --coverage --fail-fast --parallel=4 --markers not real_services
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
  pytest app/tests/services app/tests/core -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services -p test_framework.pytest_bad_test_plugin --test-component backend
================================================================================
Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
Loaded .env.development file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development
Loaded .env.development.local file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development.local
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 7.04s
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================

2025-08-17 11:57:33.266 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-17 11:57:33.267 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-17 11:57:33.267 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-17 11:57:33.267 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-17 11:57:33.267 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-17 11:57:33.267 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-17 11:57:33.268 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-17 11:57:33.268 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-17 11:57:33.268 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-17 11:57:33.268 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-17 11:57:33.268 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-17 11:57:33.268 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-17 11:57:33.268 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-17 11:57:33.268 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 12 env vars
2025-08-17 11:57:33.268 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-17 11:57:33.268 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-17 11:57:33.268 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 8 secrets from environment variables
2025-08-17 11:57:33.268 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: jwt-secret-key, fernet-key
2025-08-17 11:57:33.268 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 8 secrets loaded
2025-08-17 11:57:33.268 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 8 secrets
2025-08-17 11:57:33.268 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 8 secrets (from 8 loaded)
2025-08-17 11:57:33.268 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 2 (jwt-secret-key, fernet-key)
2025-08-17 11:57:33.268 | WARNING  | app.core.unified_logging:_emit_log:117 | Critical secrets not found in loaded secrets: 1 (gemini-api-key)
2025-08-17 11:57:33.268 | WARNING  | app.core.unified_logging:_emit_log:117 | LLM configuration warnings: Gemini API key is not configured (required for all LLM operations)
2025-08-17 11:57:33.268 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-17 11:57:33.300 | DEBUG    | logging:handle:1028 | loaded lazy attr 'SafeConfigParser': <class 'configparser.ConfigParser'>
2025-08-17 11:57:33.300 | DEBUG    | logging:handle:1028 | loaded lazy attr 'NativeStringIO': <class '_io.StringIO'>
2025-08-17 11:57:33.300 | DEBUG    | logging:handle:1028 | loaded lazy attr 'BytesIO': <class '_io.BytesIO'>
2025-08-17 11:57:33.342 | DEBUG    | logging:handle:1028 | registered 'bcrypt' handler: <class 'passlib.handlers.bcrypt.bcrypt'>
2025-08-17 11:57:33.591 | INFO     | app.db.postgres_core:_create_and_setup_engine:258 | PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling
2025-08-17 11:57:33.793 | DEBUG    | app.services.metrics.agent_metrics:__init__:24 | Initialized AgentMetricsCollector with buffer size 5000
2025-08-17 11:57:34.799 | DEBUG    | logging:handle:1028 | Using orjson library for writing JSON byte strings
2025-08-17 11:57:34.860 | DEBUG    | logging:handle:1028 | Looking up time zone info from registry
2025-08-17 11:57:35.082 | INFO     | logging:handle:1028 | Session middleware config: same_site=lax, https_only=False, environment=development
2025-08-17 11:57:35.149 | INFO     | app.core.unified_logging:_emit_log:117 | SyntheticDataService initialized successfully
2025-08-17 11:57:35.921 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
2025-08-17 11:57:36.003 | INFO     | app.services.quality_gate.quality_gate_core:__init__:34 | Quality Gate Service initialized
2025-08-17 11:57:36.003 | INFO     | app.services.quality_monitoring.service:__init__:48 | Quality Monitoring Service initialized
2025-08-17 11:57:36.003 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\conftest.py'.
app\tests\conftest.py:52: in <module>
    from app.main import app
app\main.py:71: in <module>
    app = create_app()
          ^^^^^^^^^^^^
app\core\app_factory.py:277: in create_app
    _configure_app_routes(app)
app\core\app_factory.py:290: in _configure_app_routes
    register_api_routes(app)
app\core\app_factory.py:95: in register_api_routes
    _import_and_register_routes(app)
app\core\app_factory.py:100: in _import_and_register_routes
    route_modules = _import_route_modules()
                    ^^^^^^^^^^^^^^^^^^^^^^^
app\core\app_factory.py:190: in _import_route_modules
    factory_routers = _import_factory_routers()
                      ^^^^^^^^^^^^^^^^^^^^^^^^^
app\core\app_factory.py:165: in _import_factory_routers
    status_routers = _import_factory_status_routers()
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
app\core\app_factory.py:172: in _import_factory_status_routers
    from app.routes.factory_status import router as factory_status_router
app\routes\factory_status\router.py:9: in <module>
    from .report_routes import (
app\routes\factory_status\report_routes.py:9: in <module>
    from .business_logic import get_cached_reports, get_latest_report_id, generate_new_report
app\routes\factory_status\business_logic.py:5: in <module>
    from app.services.factory_status.report_builder import ReportBuilder, FactoryStatusReport
app\services\factory_status\report_builder.py:12: in <module>
    from app.services.factory_status.git_commit_parser import GitCommitParser
app\services\factory_status\git_commit_parser.py:14: in <module>
    from app.services.factory_status.mock_data_generator import MockDataGenerator
E   ModuleNotFoundError: No module named 'app.services.factory_status.mock_data_generator'
--- Logging error in Loguru Handler #1 ---
Record was: {'elapsed': datetime.timedelta(seconds=4, microseconds=783171), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='\u2139\ufe0f'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=54668, name='MainProcess'), 'thread': (id=1444, name='MainThread'), 'time': datetime(2025, 8, 17, 11, 57, 36, 428686, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}
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

'hooks' is not recognized as an internal or external command,
operable program or batch file.

```
---
*Generated by Netra AI Unified Test Runner v3.0*
