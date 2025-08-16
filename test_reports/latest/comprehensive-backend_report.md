# Netra AI Platform - Test Report

**Generated:** 2025-08-15T23:46:05.834174  
**Test Level:** comprehensive-backend - Comprehensive backend tests only (15-20 minutes)  
**Purpose:** Full backend validation without frontend

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
| Backend   | 1 | 0 | 0 | 0 | 1 | 29.28s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** comprehensive-backend
- **Description:** Comprehensive backend tests only (15-20 minutes)
- **Purpose:** Full backend validation without frontend
- **Timeout:** 1200s
- **Coverage Enabled:** Yes
- **Total Duration:** 29.28s
- **Exit Code:** 2

### Backend Configuration
```
app/tests tests integration_tests --coverage --parallel=6 --html-output --fail-fast
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
  Parallel: 6
  Coverage: enabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests tests integration_tests -v -n 6 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 --html=reports/tests/report.html --self-contained-html
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 6/6 workers

=================================== ERRORS ====================================
[31m[1m___ ERROR collecting app/tests/agents/test_supply_researcher_agent_core.py ____[0m
ImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\agents\test_supply_researcher_agent_core.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\..\miniconda3\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
app\tests\agents\test_supply_researcher_agent_core.py:9: in <module>
    from app.agents.supply_researcher_sub_agent import (
app\agents\supply_researcher_sub_agent.py:10: in <module>
    from .supply_researcher import (
app\agents\supply_researcher\__init__.py:8: in <module>
    from .agent import SupplyResearcherAgent
app\agents\supply_researcher\agent.py:15: in <module>
    from app.services.supply_research_service import SupplyResearchService
app\services\supply_research_service.py:15: in <module>
    from .supply_research.supply_item_operations import SupplyItemOperations
app\services\supply_research\__init__.py:6: in <module>
    from .scheduler_models import ScheduleFrequency, ResearchSchedule
app\services\supply_research\scheduler_models.py:9: in <module>
    from app.agents.supply_researcher_sub_agent import ResearchType
E   ImportError: cannot import name 'ResearchType' from partially initialized module 'app.agents.supply_researcher_sub_agent' (most likely due to a circular import) (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\agents\supply_researcher_sub_agent.py)
- Generated html report: file:///C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/reports/tests/report.html -
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m app/tests/agents/test_supply_researcher_agent_core.py
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m============================== [31m[1m1 error[0m[31m in 18.27s[0m[31m ==============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 28.26s

[Report] HTML Report: reports/tests/report.html
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================

2025-08-15 23:45:41.742 | INFO     | app.core.unified_logging:_emit_log:117 | Loading configuration for: testing
2025-08-15 23:45:41.743 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set database_url from DATABASE_URL
2025-08-15 23:45:41.744 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set redis_url from REDIS_URL
2025-08-15 23:45:41.744 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set clickhouse_url from CLICKHOUSE_URL
2025-08-15 23:45:41.744 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set secret_key from SECRET_KEY
2025-08-15 23:45:41.744 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set jwt_secret_key from JWT_SECRET_KEY
2025-08-15 23:45:41.744 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set fernet_key from FERNET_KEY
2025-08-15 23:45:41.744 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set log_level from LOG_LEVEL
2025-08-15 23:45:41.744 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set environment from ENVIRONMENT
2025-08-15 23:45:41.744 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse host: localhost
2025-08-15 23:45:41.744 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse port: 9000
2025-08-15 23:45:41.745 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse password
2025-08-15 23:45:41.745 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set ClickHouse user: default
2025-08-15 23:45:41.745 | DEBUG    | app.core.unified_logging:_emit_log:117 | Set Gemini API key for LLM configs
2025-08-15 23:45:41.747 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 13 env vars
2025-08-15 23:45:41.747 | INFO     | app.core.unified_logging:_emit_log:117 | Loading secrets...
2025-08-15 23:45:41.749 | INFO     | app.core.unified_logging:_emit_log:117 | Starting secret=REDACTED process for environment: development
2025-08-15 23:45:41.749 | INFO     | app.core.unified_logging:_emit_log:117 | Loaded 9 secrets from environment variables
2025-08-15 23:45:41.750 | DEBUG    | app.core.unified_logging:_emit_log:117 | Critical secrets present in env: gemini-api-key, jwt-secret-key, fernet-key
2025-08-15 23:45:41.750 | INFO     | app.core.unified_logging:_emit_log:117 | Using only environment variables for secrets (local development mode): 9 secrets loaded
2025-08-15 23:45:41.751 | INFO     | app.core.unified_logging:_emit_log:117 | Applying 9 secrets
2025-08-15 23:45:41.752 | INFO     | app.core.unified_logging:_emit_log:117 | Applied 9 secrets (from 9 loaded)
2025-08-15 23:45:41.752 | INFO     | app.core.unified_logging:_emit_log:117 | Critical secrets loaded: 3 (gemini-api-key, jwt-secret-key, fernet-key)
2025-08-15 23:45:41.753 | INFO     | app.core.unified_logging:_emit_log:117 | Configuration validation completed successfully
2025-08-15 23:45:41.782 | DEBUG    | logging:handle:1028 | loaded lazy attr 'SafeConfigParser': <class 'configparser.ConfigParser'>
2025-08-15 23:45:41.782 | DEBUG    | logging:handle:1028 | loaded lazy attr 'NativeStringIO': <class '_io.StringIO'>
2025-08-15 23:45:41.782 | DEBUG    | logging:handle:1028 | loaded lazy attr 'BytesIO': <class '_io.BytesIO'>
2025-08-15 23:45:41.836 | DEBUG    | logging:handle:1028 | registered 'bcrypt' handler: <class 'passlib.handlers.bcrypt.bcrypt'>
2025-08-15 23:45:42.395 | INFO     | app.db.postgres_core:_create_and_setup_engine:258 | PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling
2025-08-15 23:45:42.678 | DEBUG    | app.services.metrics.agent_metrics:__init__:24 | Initialized AgentMetricsCollector with buffer size 5000
2025-08-15 23:45:43.748 | DEBUG    | logging:handle:1028 | Using orjson library for writing JSON byte strings
2025-08-15 23:45:43.822 | DEBUG    | logging:handle:1028 | Looking up time zone info from registry
2025-08-15 23:45:44.660 | INFO     | app.core.unified_logging:_emit_log:117 | SyntheticDataService initialized successfully
2025-08-15 23:45:45.616 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-15 23:45:45.650 | INFO     | logging:handle:1028 | UnifiedToolRegistry initialized
2025-08-15 23:45:45.703 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
2025-08-15 23:45:45.795 | INFO     | app.services.quality_gate.quality_gate_core:__init__:34 | Quality Gate Service initialized
2025-08-15 23:45:45.795 | INFO     | app.services.quality_monitoring.service:__init__:48 | Quality Monitoring Service initialized
2025-08-15 23:45:45.795 | INFO     | app.services.fallback_response.response_generator:__init__:25 | Response Generator initialized
--- Logging error in Loguru Handler #1 ---
Record was: {'elapsed': datetime.timedelta(seconds=11, microseconds=973866), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='INFO', no=20, icon='ℹ️'), 'line': 1028, 'message': 'Multiprocessing resources cleaned up', 'module': '__init__', 'name': 'logging', 'process': (id=37880, name='MainProcess'), 'thread': (id=24696, name='MainThread'), 'time': datetime(2025, 8, 15, 23, 46, 2, 796124, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Tim...(truncated)
```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m___ ERROR collecting app/tests/agents/test_supply_researcher_agent_core.py ____[0m
- [31mERROR[0m app/tests/agents/test_supply_researcher_agent_core.py
- [FAIL] TESTS FAILED with exit code 2 after 28.26s


---
*Generated by Netra AI Unified Test Runner v3.0*
