# Netra AI Platform - Test Report

**Generated:** 2025-08-15T10:43:04.873763  
**Test Level:** mock_only - Tests using only mocks, no external dependencies  
**Purpose:** Fast CI/CD validation without external dependencies

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
| Backend   | 2 | 0 | 0 | 1 | 1 | 66.28s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Coverage Summary

**Overall Coverage:** 32.9%
**Backend Coverage:** 32.9%  

## Environment and Configuration

- **Test Level:** mock_only
- **Description:** Tests using only mocks, no external dependencies
- **Purpose:** Fast CI/CD validation without external dependencies
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 66.28s
- **Exit Code:** 1

### Backend Configuration
```
-m mock_only -v --coverage --parallel=8
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
  Parallel: 8
  Coverage: enabled
  Fail Fast: disabled
  Environment: testing

Running command:
  pytest app/tests tests integration_tests -vv -n 8 --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m mock_only --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 8/8 workers
8 workers [0 items]

scheduling tests via LoadScheduling
[31m[1m
ERROR: Coverage failure: total of 32.86 is less than fail-under=70.00
[0m
=================================== ERRORS ====================================
[31m[1m____ ERROR collecting app/tests/performance/test_corpus_generation_perf.py ____[0m
ImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\performance\test_corpus_generation_perf.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\..\miniconda3\Lib\site-packages\_pytest\python.py:498: in importtestmodule
    mod = import_path(
..\..\..\..\miniconda3\Lib\site-packages\_pytest\pathlib.py:587: in import_path
    importlib.import_module(module_name)
..\..\..\..\miniconda3\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen importlib._bootstrap>:1387: in _gcd_import
    ???
<frozen importlib._bootstrap>:1360: in _find_and_load
    ???
<frozen importlib._bootstrap>:1331: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:935: in _load_unlocked
    ???
..\..\..\..\miniconda3\Lib\site-packages\_pytest\assertion\rewrite.py:186: in exec_module
    exec(co, module.__dict__)
app\tests\performance\test_corpus_generation_perf.py:16: in <module>
    from app.services.synthetic_data.service import SyntheticDataService
E   ModuleNotFoundError: No module named 'app.services.synthetic_data.service'
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.12.4-final-0 _______________

Name                                                                                 Stmts   Miss   Cover   Missing
-------------------------------------------------------------------------------------------------------------------
app\__init__.py                                                                          1      0 100.00%
app\agents\__init__.py                                                                   0      0 100.00%
app\agents\actions_to_meet_goals_sub_agent.py                                          119     80  32.77%   27-32, 36, 41-44, 48-56, 60-66, 70-71, 78, 86-89, 93-95, 99-100, 104-107, 111-116, 120-121, 126-131, 135-140, 144-145, 153-154, 162, 167-169, 174-180, 184, 197, 206, 217-220, 224, 228
app\agents\admin_tool_dispatcher\__init__.py                                             2      0 100.00%
app\agents\admin_tool_dispatcher\admin_tool_execution.py                                68     68   0.00%   17-196
app\agents\admin_tool_dispatcher\corpus_models.py                                       23     23   0.00%   8-39
app\agents\admin_tool_dispatcher\corpus_tool_handlers.py                                86     86   0.00%   8-220
app\agents\admin_tool_dispatcher\corpus_tools.py                                        43     43   0.00%   8-98
app\agents\admin_tool_dispatcher\corpus_validators.py                                   32     32   0.00%   8-52
app\agents\admin_tool_dispatcher\dispatcher_core.py                                    123     89  27.64%   35-44, 48-50, 54-59, 63-65, 69-74, 78-79, 86-87, 93-94, 100-106, 114, 131, 143-150, 163, 167-174, 178-181, 185-188, 192-198, 202-218, 222-223, 234, 245-273, 277-284
app\agents\admin_tool_dispatcher\tool_handlers.py                                      107    107   0.00%   17-265
app\agents\admin_tool_dispatcher\validation.py                                         110    110   0.00%   17-228
app\agents\admin_tool_executors.py                                                     113    113   0.00%   19-228
app\agents\admin_tool_permissions.py                                                    82     82   0.00%   19-171
app\agents\artifact_validator.py                                                       151    110  27.15%   22-24, 56-67, 73-84, 90-101, 106-113, 117-122, 127-136, 141-150, 154-161, 165-172, 178, 189-200, 205-208, 213-236
app\agents\base.py                                                                     170    125  26.47%   23-32, 36-45, 49-70, 74, 78-79, 89-90, 100-111, 115-121, 125-136, 140-141, 145-147, 151-162, 171, 175, 179-186, 190, 197-198, 202, 212, 220, 229, 237, 244, 248-269, 273-294, 301-303, 308-334, 337-338, 342-345
app\agents\config.py                                                                    32      0 100.00%
app\agents\corpus_admin\__init__.py                                                      6      0 100.00%
app\agents\corpus_admin\agent.py                                                       118     81  31.36%   27-35, 39-45, 49-55, 61-67, 73-78, 82-83, 87-93, 97-101, 105-106, 120-125, 131-133, 137-138, 152-154, 158-162, 177-183, 187, 196, 209-210, 214, 230-232, 236, 246, 253-255, 262-270
app\agents\corpus_admin\discovery.py                                                   124    124   0.00%   8-208
app\agents\corpus_admin\error_handler.py                                               207    207   0.00%   7-644
app\agents\corpus_admin\models.py                                                       55      0 100.00%
app\agents\corpus_admin\operations.py                                                    2      0 100.00%
app\agents\corpus_admin\operations_analysis.py                                          59     39  33.90%   22-23, 33-40, 49-52, 68-69, 84, 99-104, 116-123, 127-134, 138-139, 143-147, 151, 160
app\agents\corpus_admin\operations_crud.py                                              48     30  37.50%   24-25, 35-42, 51-56, 65-70, 79, 94, 106-110, 124-142
app\agents\corpus_admin\operations_execution.py                                         34     17  50.00%   22, 32-39, 48-56, 66-67, 77-78, 90-91, 100, 110, 124, 139-140
app\agents\corpus_admin\operations_handler.py                                           31     18  41.94%   23-25, 34-53, 57, 84
app\agents\corpus_admin\parsers.py                                                      23     11  52.17%   21, 25-31, 35, 71-73, 82
app\agents\corpus_admin\suggestions.py                                                 145    145   0.00%   8-301
app\agents\corpus_admin\validators.py                                                   45     30  33.33%   17, 29-35, 39-47, 51, 55-56, 60, 65, 76, 89-93, 97-99, 103
app\agents\corpus_admin_sub_agent.py                                                     2      0 100.00%
app\agents\data_sub_agent\__init__.py                                                   14      0 100.00%
app\agents\data_sub_agent\agent.py                                                     266    176  33.83%   39-40, 43, 50-53, 57-59, 70, 78-83, 87-91, 95-97, 101, 109, 117-121, 126-128, 132-135, 139-144, 148-152, 156-157, 161-163, 167, 174-176, 180-186, 190-191, 195-196, 204, 210-214, 221-225, 229-230, 236-239, 244, 250-252, 256, 263-265, 269, 275, 281-286, 290-293, 299-303, 307, 315, 319, 323-327, 331-335, 339-340, 344-349, 353, 362, 366-369, 374, 378-382, 386-391, 395, 406-408, 412-416, 420-424, 428-431, 435-437, 441-445, 449, 458-461, 465-469
app\agents\data_sub_agent\agent_backup.py                                              221    221   0.00%   3-542
app\agents\data_sub_agent\agent_core.py                                                 60     60   0.00%   3-122
app\agents\data_sub_agent\agent_test.py                                                  3      3   0.00%   3-7
app\agents\data_sub_agent\analysis_engine.py                                            76     64  15.79%   14-31, 48-80, 92-120, 135-163
app\agents\data_sub_agent\analysis_operations.py                                        91     91   0.00%   3-266
app\agents\data_sub_agent\clickhouse_operations.py                                      39     31  20.51%   16-25, 37-75
app\agents\data_sub_agent\clickhouse_recovery.py                                        69     69   0.00%   6-148
app\agents\data_sub_agent\data_analysis_ops.py                                          88     88   0.00%   3-267
app\agents\data_sub_agent\data_fetching.py                                              88     88   0.00%   3-211
app\agents\data_sub_agent\da...(truncated)
```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- ERROR: Coverage failure: total of 32.86 is less than fail-under=70.00
- =================================== ERRORS ====================================
- [31m[1m____ ERROR collecting app/tests/performance/test_corpus_generation_perf.py ____[0m
- [31mERROR[0m app/tests/performance/test_corpus_generation_perf.py
- [FAIL] TESTS FAILED with exit code 1 after 65.49s


---
*Generated by Netra AI Unified Test Runner v3.0*
