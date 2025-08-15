# Netra AI Platform - Test Report

**Generated:** 2025-08-15T18:49:01.875504  
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
| Backend   | 0 | 0 | 0 | 0 | 0 | 6.93s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** smoke
- **Description:** Quick smoke tests for basic functionality (< 30 seconds)
- **Purpose:** Pre-commit validation, basic health checks
- **Timeout:** 30s
- **Coverage Enabled:** No
- **Total Duration:** 6.93s
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
Loaded test environment from /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/.env.test
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
Loaded .env file from /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/.env
Loaded .env.development file from /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/.env.development
Loaded .env.development.local file from /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/.env.development.local
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 6.31s
================================================================================

2025-08-15 18:49:00.258 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-15 18:49:00.258 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-15 18:49:00.258 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-15 18:49:00.258 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-15 18:49:00.259 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-15 18:49:00.259 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-15 18:49:00.259 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-15 18:49:00.259 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-15 18:49:00.259 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-15 18:49:00.259 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-15 18:49:00.259 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-15 18:49:00.259 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-15 18:49:00.259 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-15 18:49:00.259 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set Gemini API key for LLM configs
2025-08-15 18:49:00.259 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 13 env vars
2025-08-15 18:49:00.259 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-15 18:49:00.260 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-15 18:49:00.260 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 9 secrets from environment variables
2025-08-15 18:49:00.260 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: gemini-api-key, jwt-secret-key, fernet-key
2025-08-15 18:49:00.260 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 9 secrets loaded
2025-08-15 18:49:00.260 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 9 secrets
2025-08-15 18:49:00.260 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 9 secrets (from 9 loaded)
2025-08-15 18:49:00.260 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 3 (gemini-api-key, jwt-secret-key, fernet-key)
2025-08-15 18:49:00.260 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-15 18:49:00.537 | DEBUG    | logging:handle:968 | loaded lazy attr 'SafeConfigParser': <class 'configparser.ConfigParser'>
2025-08-15 18:49:00.538 | DEBUG    | logging:handle:968 | loaded lazy attr 'NativeStringIO': <class '_io.StringIO'>
2025-08-15 18:49:00.538 | DEBUG    | logging:handle:968 | loaded lazy attr 'BytesIO': <class '_io.BytesIO'>
ImportError while loading conftest '/mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/app/tests/conftest.py'.
app/tests/conftest.py:52: in <module>
    from app.main import app
app/main.py:46: in <module>
    from app.core.app_factory import create_app
app/core/app_factory.py:9: in <module>
    from app.core.lifespan_manager import lifespan
app/core/lifespan_manager.py:8: in <module>
    from app.startup_module import run_complete_startup
app/startup_module.py:18: in <module>
    from app.services.security_service import SecurityService
app/services/security_service.py:8: in <module>
    from datetime import datetime, timedelta, UTC
E   ImportError: cannot import name 'UTC' from 'datetime' (/usr/lib/python3.10/datetime.py)
--- Logging error in Loguru Handler #1 ---
Record was: {'elapsed': datetime.timedelta(seconds=4, microseconds=433499), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='/usr/lib/python3.10/logging/__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='ℹ️'), 'line': 968, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=110, name='MainProcess'), 'thread': (id=126221594890240, name='MainThread'), 'time': datetime(2025, 8, 15, 18, 49, 1, 493868, tzinfo=datetime.timezone(datetime.timedelta(0), 'UTC'))}
Traceback (most recent call last):
  File "/usr/local/lib/python3.10/dist-packages/loguru/_handler.py", line 315, in _queued_writer
    self._sink.write(message)
  File "/usr/local/lib/python3.10/dist-packages/loguru/_simple_sinks.py", line 16, in write
    self._stream.write(message)
ValueError: I/O operation on closed file.
--- End of logging error ---

```

### Frontend Output
```

```
---
*Generated by Netra AI Unified Test Runner v3.0*
