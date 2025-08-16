# Netra AI Platform - Test Report

**Generated:** 2025-08-15T19:57:25.555365  
**Test Level:** smoke - Quick smoke tests for basic functionality (< 30 seconds)  
**Purpose:** Pre-commit validation, basic health checks

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
| Backend   | 0 | 0 | 0 | 0 | 0 | 3.54s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** smoke
- **Description:** Quick smoke tests for basic functionality (< 30 seconds)
- **Purpose:** Pre-commit validation, basic health checks
- **Timeout:** 30s
- **Coverage Enabled:** No
- **Total Duration:** 3.54s
- **Exit Code:** 4

### Backend Configuration
```
--category smoke --fail-fast --markers not real_services
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
  Category: smoke
  Parallel: disabled
  Coverage: disabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests/routes/test_health_route.py app/tests/core/test_error_handling.py::TestNetraExceptions::test_configuration_error app/tests/core/test_config_manager.py::TestConfigManager::test_initialization app/tests/services/test_security_service.py::test_encrypt_and_decrypt tests/test_system_startup.py::TestSystemStartup::test_configuration_loading -v -x --maxfail=1 -m not real_services --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
Loaded .env.development file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development
Loaded .env.development.local file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development.local
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 2.94s
================================================================================

2025-08-15 19:57:24.596 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-15 19:57:24.596 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-15 19:57:24.596 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-15 19:57:24.596 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-15 19:57:24.596 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-15 19:57:24.596 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-15 19:57:24.596 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-15 19:57:24.596 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-15 19:57:24.596 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-15 19:57:24.596 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-15 19:57:24.596 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-15 19:57:24.596 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-15 19:57:24.596 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-15 19:57:24.598 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set Gemini API key for LLM configs
2025-08-15 19:57:24.598 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 13 env vars
2025-08-15 19:57:24.598 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-15 19:57:24.598 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-15 19:57:24.598 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 9 secrets from environment variables
2025-08-15 19:57:24.598 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: gemini-api-key, jwt-secret-key, fernet-key
2025-08-15 19:57:24.598 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 9 secrets loaded
2025-08-15 19:57:24.598 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 9 secrets
2025-08-15 19:57:24.598 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 9 secrets (from 9 loaded)
2025-08-15 19:57:24.598 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 3 (gemini-api-key, jwt-secret-key, fernet-key)
2025-08-15 19:57:24.598 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-15 19:57:24.617 | DEBUG    | logging:handle:1028 | loaded lazy attr 'SafeConfigParser': <class 'configparser.ConfigParser'>
2025-08-15 19:57:24.618 | DEBUG    | logging:handle:1028 | loaded lazy attr 'NativeStringIO': <class '_io.StringIO'>
2025-08-15 19:57:24.618 | DEBUG    | logging:handle:1028 | loaded lazy attr 'BytesIO': <class '_io.BytesIO'>
2025-08-15 19:57:24.631 | DEBUG    | logging:handle:1028 | registered 'bcrypt' handler: <class 'passlib.handlers.bcrypt.bcrypt'>
2025-08-15 19:57:24.860 | INFO     | app.db.postgres_core:_initialize_async_engine:184 | PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling
2025-08-15 19:57:24.949 | DEBUG    | app.services.metrics.agent_metrics:__init__:24 | Initialized AgentMetricsCollector with buffer size 5000
ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\conftest.py'.
app\tests\conftest.py:52: in <module>
    from app.main import app
app\main.py:46: in <module>
    from app.core.app_factory import create_app
app\core\app_factory.py:9: in <module>
    from app.core.lifespan_manager import lifespan
app\core\lifespan_manager.py:8: in <module>
    from app.startup_module import run_complete_startup
app\startup_module.py:29: in <module>
    from app.monitoring.performance_monitor import performance_monitor
app\monitoring\__init__.py:6: in <module>
    from .alert_manager_compact import AlertManager, alert_manager
app\monitoring\alert_manager_compact.py:18: in <module>
    from .alert_notifications import NotificationManager
E   ImportError: cannot import name 'NotificationManager' from 'app.monitoring.alert_notifications' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\monitoring\alert_notifications.py)
--- Logging error in Loguru Handler #1 ---
Record was: {'elapsed': datetime.timedelta(seconds=1, microseconds=290950), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='\u2139\ufe0f'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=39416, name='MainProcess'), 'thread': (id=52524, name='MainThread'), 'time': datetime(2025, 8, 15, 19, 57, 25, 190483, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}
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
