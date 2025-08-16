# Netra AI Platform - Test Report

**Generated:** 2025-08-16T10:43:01.551313  
**Test Level:** agents - Agent-specific unit tests (2-3 minutes)  
**Purpose:** Quick validation of agent functionality during development

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
| Backend   | 0 | 0 | 0 | 0 | 0 | 6.11s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** agents
- **Description:** Agent-specific unit tests (2-3 minutes)
- **Purpose:** Quick validation of agent functionality during development
- **Timeout:** 180s
- **Coverage Enabled:** No
- **Total Duration:** 6.11s
- **Exit Code:** 4

### Backend Configuration
```
app/tests/agents/test_data_sub_agent.py tests/test_actions_sub_agent.py -v --fail-fast --parallel=4
```

### Frontend Configuration
```

```

## Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: all
  Parallel: 4
  Coverage: disabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests/agents/test_data_sub_agent.py tests/test_actions_sub_agent.py -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
Loaded .env.development file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development
Loaded .env.development.local file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development.local
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 5.27s
================================================================================

2025-08-16 10:42:58.392 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-16 10:42:58.393 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-16 10:42:58.393 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-16 10:42:58.393 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-16 10:42:58.394 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-16 10:42:58.394 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-16 10:42:58.394 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-16 10:42:58.394 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-16 10:42:58.394 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-16 10:42:58.394 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-16 10:42:58.395 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-16 10:42:58.395 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-16 10:42:58.395 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-16 10:42:58.395 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set Gemini API key for LLM configs
2025-08-16 10:42:58.395 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 13 env vars
2025-08-16 10:42:58.396 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-16 10:42:58.396 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-16 10:42:58.397 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 9 secrets from environment variables
2025-08-16 10:42:58.397 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: gemini-api-key, jwt-secret-key, fernet-key
2025-08-16 10:42:58.397 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 9 secrets loaded
2025-08-16 10:42:58.398 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 9 secrets
2025-08-16 10:42:58.398 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 9 secrets (from 9 loaded)
2025-08-16 10:42:58.399 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 3 (gemini-api-key, jwt-secret-key, fernet-key)
2025-08-16 10:42:58.400 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-16 10:42:58.417 | DEBUG    | logging:handle:1028 | loaded lazy attr 'SafeConfigParser': <class 'configparser.ConfigParser'>
2025-08-16 10:42:58.417 | DEBUG    | logging:handle:1028 | loaded lazy attr 'NativeStringIO': <class '_io.StringIO'>
2025-08-16 10:42:58.417 | DEBUG    | logging:handle:1028 | loaded lazy attr 'BytesIO': <class '_io.BytesIO'>
2025-08-16 10:42:58.435 | DEBUG    | logging:handle:1028 | registered 'bcrypt' handler: <class 'passlib.handlers.bcrypt.bcrypt'>
2025-08-16 10:42:58.768 | INFO     | app.db.postgres_core:_create_and_setup_engine:258 | PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling
2025-08-16 10:42:58.885 | DEBUG    | app.services.metrics.agent_metrics:__init__:24 | Initialized AgentMetricsCollector with buffer size 5000
2025-08-16 10:42:59.362 | DEBUG    | logging:handle:1028 | Using orjson library for writing JSON byte strings
2025-08-16 10:42:59.427 | DEBUG    | logging:handle:1028 | Looking up time zone info from registry
2025-08-16 10:42:59.863 | INFO     | app.core.unified_logging:_emit_log:117 | SyntheticDataService initialized successfully
2025-08-16 10:43:00.333 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-16 10:43:00.347 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-16 10:43:00.371 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
2025-08-16 10:43:00.402 | INFO     | app.services.quality_gate.quality_gate_core:__init__:34 | Quality Gate Service initialized
2025-08-16 10:43:00.402 | INFO     | app.services.quality_monitoring.service:__init__:48 | Quality Monitoring Service initialized
2025-08-16 10:43:00.402 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\conftest.py'.
app\tests\conftest.py:52: in <module>
    from app.main import app
app\main.py:48: in <module>
    app = create_app()
          ^^^^^^^^^^^^
app\core\app_factory.py:168: in create_app
    register_api_routes(app)
app\core\app_factory.py:77: in register_api_routes
    _import_and_register_routes(app)
app\core\app_factory.py:82: in _import_and_register_routes
    route_modules = _import_route_modules()
                    ^^^^^^^^^^^^^^^^^^^^^^^
app\core\app_factory.py:100: in _import_route_modules
    from app.routes.factory_status import router as factory_status_router
app\routes\factory_status.py:14: in <module>
    from app.services.factory_status.factory_status_integration import (
app\services\factory_status\factory_status_integration.py:9: in <module>
    from app.services.factory_status.spec_compliance_scorer import (
app\services\factory_status\spec_compliance_scorer.py:15: in <module>
    from app.core.interfaces_monitoring import ComplianceMetrics
E   ModuleNotFoundError: No module named 'app.core.interfaces_monitoring'
--- Logging error in Loguru Handler #1 ---
Record was: {'elapsed': datetime.timedelta(seconds=3, microseconds=468006), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='\u2139\ufe0f'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=2716, name='MainProcess'), 'thread': (id=38324, name='MainThread'), 'time': datetime(2025, 8, 16, 10, 43, 0, 924718, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}
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

```
---
*Generated by Netra AI Unified Test Runner v3.0*
