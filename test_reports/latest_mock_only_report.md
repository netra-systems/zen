# Netra AI Platform - Test Report

**Generated:** 2025-08-12T11:14:02.043452  
**Test Level:** mock_only - Tests using only mocks, no external dependencies  
**Purpose:** Fast CI/CD validation without external dependencies

## Test Summary

**Total Tests:** 8  
**Passed:** 0  
**Failed:** 0  
**Skipped:** 0  
**Errors:** 8  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 8 | 0 | 0 | 0 | 8 | 61.53s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Coverage Summary

**Overall Coverage:** 30.1%
**Backend Coverage:** 30.1%  

## Environment and Configuration

- **Test Level:** mock_only
- **Description:** Tests using only mocks, no external dependencies
- **Purpose:** Fast CI/CD validation without external dependencies
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 61.53s
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
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: all
  Parallel: 8
  Coverage: enabled
  Fail Fast: disabled
  Environment: development

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
ERROR: Coverage failure: total of 30.05 is less than fail-under=70.00
[0m
=================================== ERRORS ====================================
[31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
'real_llm' not found in `markers` configuration option
[31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
'real_llm' not found in `markers` configuration option
[31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
'real_llm' not found in `markers` configuration option
[31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
'real_llm' not found in `markers` configuration option
[31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
'real_llm' not found in `markers` configuration option
[31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
'real_llm' not found in `markers` configuration option
[31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
'real_llm' not found in `markers` configuration option
[31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
'real_llm' not found in `markers` configuration option
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.12.4-final-0 _______________

Name                                                                                 Stmts   Miss   Cover   Missing
-------------------------------------------------------------------------------------------------------------------
app\__init__.py                                                                          1      0 100.00%
app\agents\__init__.py                                                                   0      0 100.00%
app\agents\actions_to_meet_goals_sub_agent.py                                           44     30  31.82%   24-25, 29, 34-94, 102, 125
app\agents\admin_tool_dispatcher.py                                                    125    125   0.00%   4-269
app\agents\admin_tools.py                                                              142    142   0.00%   12-458
app\agents\base.py                                                                      99     77  22.22%   25-34, 38-50, 54-78, 82-122, 131, 135, 138, 141, 145-169, 173-174, 178-181
app\agents\corpus_admin_sub_agent.py                                                   209    125  40.19%   97-103, 112-129, 133-220, 225-279, 291-312, 317-349, 357-388, 394-423, 436-470, 483, 495, 505-519, 530-532, 543, 554-565, 578, 597-602
app\agents\data_sub_agent.py                                                           478    395  17.36%   68-77, 122, 158, 187, 216-231, 247-279, 291-319, 334-362, 367-378, 383-392, 402-440, 450-527, 538-554, 578-622, 642-688, 706-710, 715-872, 881-883, 887-893, 897-903, 907-914, 918-922, 926, 930-933, 937, 941-948, 952-962, 966-976, 980-981, 985-988, 992-998, 1002-1006, 1010-1017, 1021-1052, 1057-1089, 1093-1116, 1120-1129
app\agents\demo_agent.py                                                                77     77   0.00%   13-331
app\agents\optimizations_core_sub_agent.py                                              26     14  46.15%   24-25, 29, 34-59
app\agents\prompts.py                                                                    6      0 100.00%
app\agents\prompts_enhanced.py                                                          15     15   0.00%   16-660
app\agents\quality_supervisor.py                                                       139    139   0.00%   17-397
app\agents\reporting_sub_agent.py                                                       26     14  46.15%   24-25, 29, 37-64
app\agents\state.py                                                                     15      0 100.00%
app\agents\supervisor_admin_init.py                                                     61     61   0.00%   4-194
app\agents\supervisor_consolidated.py                                                  243    171  29.63%   84-105, 115-122, 126-128, 132-133, 138, 143, 157-248, 255-276, 284-326, 335-418, 424-453, 463-474, 481-491, 498-509, 513, 517, 531, 544, 557, 570-577, 581-592, 596
app\agents\supply_researcher_sub_agent.py                                              217    181  16.59%   45-63, 74-114, 124-184, 195-225, 246-289, 297-317, 325-394, 401-409, 418-535, 543-572
app\agents\synthetic_data_sub_agent.py                                                 164    108  34.15%   71-77, 81, 157-173, 177-267, 271-312, 321-334, 338, 361-411, 425-468, 472-474, 478-483
app\agents\tool_dispatcher.py                                                           66     49  25.76%   21-26, 31-38, 42-54, 58, 61-71, 92-114, 121, 125, 136-164
app\agents\triage_sub_agent.py                                                         317    223  29.65%   104-106, 110-115, 129-131, 135-147, 151-159, 163-205, 209-259, 263-269, 273-305, 313-342, 346-358, 376-423, 427-441, 445-590, 599-606
app\agents\utils.py                                                                    240    231   3.75%   30-72, 85-167, 181-288, 302-401, 416-523
app\auth\__init__.py                                                                     0      0 100.00%
app\auth\auth.py                                                                        12      0 100.00%
app\auth\auth_dependencies.py                                                           78     48  38.46%   21-40, 47, 54-68, 75-80, 85-94, 101-106, 114-119, 128-134
app\auth\environment_config.py                                                          75     37  50.67%   47-58, 62-74, 78, 95, 112-131, 148, 165-180, 184-192, 196-204
app\auth\oauth_proxy.py                                                                105    105   0.00%   3-233
app\background.py                                                                       18     10  44.44%   10, 14-16, 20-25
app\core\__init__.py                                                                     0      0 100.00%
app\core\async_utils.py                                                                273    204  25.27%   28-31, 35-46, 60-74, 78-87, 91-92, 97, 101-122, 129-132, 136-152, 158-162, 170-176, 186-205, 212-213, 222-246, 253-256, 260-266, 270-272, 277, 282, 293-304, 316-323, 327-355, 360, 365, 378-386, 390-392, 397-425, 429-446, 456, 461, 466-472, 477-482
app\core\config_validator.py                                                           108     48  55.56%   33-38, 50-51, 53, 65, 71, 79, 82-85, 89, 94, 96, 99, 108-109, 112, 120, 122, 128-129, 133, 136, 139-142, 151, 158, 160, 163, 167-183
app\core\error_context.py                                                              108     71  34.26%   22-23, 28, 33-35, 40-41, 46, 51-52, 57, 62-64, 69, 74-88, 93-96, 109-118, 123-138, 143-158, 168-179, 184-189
app\core\error_handlers.py                                                             103     64  37.86%   71-96, 107-113, 131-138, 159-173, 192-205, 223-225, 242-254, 259-288, 301, 306, 313-326, 334-336, 344-346, 354-356
app\core\exceptions.py                                                                 165     61  63.03%   92-101, 105, 118, 130-134, 150, 163, 176, 189, 204, 216, 229-233, 247-251, 265, 281, 294-298, 313-317, 333, 346-352, 365-369, 382-386, 403, 415, 427, 439, 454, 465, 478, 492, 505-511
app\core\fallback_handler.py                                                           257    190  26.07%   45-46, 59, 229-261, 267-292, 296-298, 309-311, 322, 334, 344, 354, 366, 376, 387-393, 398-400, 404-416, 420-436, 440-451, 455-461, 465-473, 477-490, 494-505, 509, 521-527, 531-534, 538-545, 549, 557, 567-575, 579-582, 586-598, 602, 611-617, 621-630, 634, 643, 652, 661-663, 667-676, 680, 690, 708-737
app\core\resource_manager.py                                                           210    210   0.00%   3-368
app\core\secret_manager.py                                                             111     72  35.14%   30, 55-74, 79-85, 89-166, 170-184, 224
app\core\service_interfaces.py                                                         243    149  38.68%...(truncated)
```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- ERROR: Coverage failure: total of 30.05 is less than fail-under=70.00
- =================================== ERRORS ====================================
- [31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
- [31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
- [31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
- [31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
- [31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
- [31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
- [31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
- [31m[1m_____ ERROR collecting app/tests/agents/test_example_prompts_e2e_real.py ______[0m
- [31mERROR[0m app/tests/agents/test_example_prompts_e2e_real.py - Failed: 'real_llm' not found in `markers` configuration option
- [31mERROR[0m app/tests/agents/test_example_prompts_e2e_real.py - Failed: 'real_llm' not found in `markers` configuration option
- [31mERROR[0m app/tests/agents/test_example_prompts_e2e_real.py - Failed: 'real_llm' not found in `markers` configuration option
- [31mERROR[0m app/tests/agents/test_example_prompts_e2e_real.py - Failed: 'real_llm' not found in `markers` configuration option
- [31mERROR[0m app/tests/agents/test_example_prompts_e2e_real.py - Failed: 'real_llm' not found in `markers` configuration option
- [31mERROR[0m app/tests/agents/test_example_prompts_e2e_real.py - Failed: 'real_llm' not found in `markers` configuration option
- [31mERROR[0m app/tests/agents/test_example_prompts_e2e_real.py - Failed: 'real_llm' not found in `markers` configuration option
- [31mERROR[0m app/tests/agents/test_example_prompts_e2e_real.py - Failed: 'real_llm' not found in `markers` configuration option
- [FAIL] TESTS FAILED with exit code 1 after 60.41s


---
*Generated by Netra AI Unified Test Runner v3.0*
