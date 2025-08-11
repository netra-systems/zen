# Netra AI Platform - Test Report

**Generated:** 2025-08-11T06:56:39.060481  
**Test Level:** comprehensive - Full test suite with coverage (10-15 minutes)  
**Purpose:** Pre-release validation, full system testing

## Summary

| Component | Status | Duration | Exit Code |
|-----------|--------|----------|-----------|
| Backend   | [FAILED] | 180.56s | 3 |
| Frontend  | [FAILED] | 36.82s | 1 |

**Overall Status:** [FAILED]  
**Total Duration:** 217.37s  
**Final Exit Code:** 3

## Test Level Details

- **Description:** Full test suite with coverage (10-15 minutes)
- **Purpose:** Pre-release validation, full system testing
- **Timeout:** 900s
- **Coverage Enabled:** Yes

## Configuration

### Backend Args
```
--coverage --parallel=auto --html-output
```

### Frontend Args  
```
--coverage
```

## Test Output

### Backend Output
```
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: all
  Parallel: auto
  Coverage: enabled
  Fail Fast: disabled
  Environment: testing

Running command:
  pytest app/tests tests integration_tests -v -n auto --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 --html=reports/tests/report.html --self-contained-html --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.3.2, pluggy-1.5.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.3.2', 'pluggy': '1.5.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '1.1.0', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-1.1.0, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
created: 14/14 workers
14 workers [1433 items]

scheduling tests via LoadScheduling

app\tests\agents\test_data_sub_agent.py::TestErrorHandling::test_max_retries_exceeded 
app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_9_variation_9 
app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_scheduler_initialization 
app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_1_complete_agent_lifecycle_request_to_completion 
app\tests\clickhouse\test_query_correctness.py::TestPerformanceMetricsQueries::test_aggregation_level_functions 
app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_2_variation_4 
app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_4_variation_9 
app\tests\agents\test_triage_sub_agent.py::TestCleanup::test_cleanup_with_metrics 
app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_7_variation_4 
app\tests\agents\test_triage_sub_agent.py::TestEntityExtraction::test_extract_time_ranges 
app\tests\clickhouse\test_performance_edge_cases.py::TestLargeDatasetPerformance::test_statistics_query_on_million_records 
app\tests\core\test_error_handling.py::TestErrorHandlerFunctions::test_get_http_status_code_function 
app\tests\core\test_error_handling.py::TestNetraExceptions::test_configuration_error 
app\tests\core\test_config_manager.py::TestConfigValidator::test_get_validation_report_success 
[gw12][36m [  0%] [0m[32mPASSED[0m app\tests\clickhouse\test_query_correctness.py::TestPerformanceMetricsQueries::test_aggregation_level_functions 
[gw10][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_config_manager.py::TestConfigValidator::test_get_validation_report_success 
[gw6][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_scheduler_initialization 
[gw9][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_error_handling.py::TestNetraExceptions::test_configuration_error 
app\tests\clickhouse\test_query_correctness.py::TestAnomalyDetectionQueries::test_anomaly_detection_query_structure 
[gw11][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_error_handling.py::TestErrorHandlerFunctions::test_get_http_status_code_function 
app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_schedule_next_run_calculation 
app\tests\core\test_config_manager.py::TestConfigValidator::test_get_validation_report_failure 
app\tests\core\test_error_handling.py::TestNetraExceptions::test_validation_error_with_errors 
[gw6][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_schedule_next_run_calculation 
app\tests\core\test_error_handling.py::TestErrorHandlerFunctions::test_netra_exception_handler 
[gw9][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_error_handling.py::TestNetraExceptions::test_validation_error_with_errors 
app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_schedule_should_run 
[gw6][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_sche...(truncated)
```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> jest --coverage --coverageDirectory=../reports/frontend-coverage

---------------------------------|---------|----------|---------|---------|----------------------------------------------------------------------
File                             | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s                                                    
---------------------------------|---------|----------|---------|---------|----------------------------------------------------------------------
All files                        |    51.4 |    79.84 |   41.75 |    51.4 |                                                                      
 frontend                        |     100 |        0 |     100 |     100 |                                                                      
  config.ts                      |     100 |        0 |     100 |     100 | 2-3                                                                  
 frontend/app                    |      45 |      100 |       0 |      45 |                                                                      
  layout.tsx                     |   57.14 |      100 |       0 |   57.14 | 17-28                                                                
  page.tsx                       |   34.37 |      100 |       0 |   34.37 | 10-30                                                                
 frontend/app/chat               |   69.23 |      100 |       0 |   69.23 |                                                                      
  page.tsx                       |   69.23 |      100 |       0 |   69.23 | 8-11                                                                 
 frontend/auth                   |   28.91 |      100 |       0 |   28.91 |                                                                      
  components.tsx                 |   19.44 |      100 |       0 |   19.44 | 8-36                                                                 
  context.tsx                    |   17.21 |      100 |       0 |   17.21 | 22-122                                                               
  index.ts                       |     100 |      100 |     100 |     100 |                                                                      
  service.ts                     |   29.46 |      100 |       0 |   29.46 | 11-16,19-43,46-47,50-52,55-56,59-60,63-64,67-68,71-74,77-101,104-109 
  types.ts                       |     100 |      100 |     100 |     100 |                                                                      
 frontend/components             |   44.72 |    95.65 |    37.5 |   44.72 |                                                                      
  AppWithLayout.tsx              |     100 |      100 |     100 |     100 |                                                                      
  ChatHistorySection.tsx         |    6.98 |      100 |       0 |    6.98 | 20-272                                                               
  Footer.tsx                     |     100 |      100 |     100 |     100 |                                                                      
  Header.tsx                     |   48.14 |      100 |       0 |   48.14 | 14-27                                                                
  Icons.tsx                      |     100 |      100 |     100 |     100 |                                                                      
  LoginButton.tsx                |   18.51 |      100 |       0 |   18.51 | 6-27                                                                 
  NavLinks.tsx                   |   45.71 |      100 |       0 |   45.71 | 33-70                                                                
  Sidebar.tsx                    |   26.92 |      100 |       0 |   26.92 | 8-26                                                                 
  SubAgentStatus.tsx             |     100 |    94.11 |     100 |     100 | 43                                                                   
 frontend/components/chat        |   49.88 |    76.11 |   73.68 |   49.88 |                                                                      
  ChatHeader.tsx                 |   95.89 |       60 |     100 |   95.89 | 16,19,41,43,45-46                                                    
  ExamplePrompts.tsx             |     100 |      100 |     100 |     100 |                                                                      
  MainChat.tsx                   |   13.15 |      100 |       0 |   13.15 | 14-112                                                               
  MessageInput.tsx               |     4.4 |      100 |       0 |     4.4 | 14-295                                                               
  MessageItem.tsx                |   91.66 |       75 |     100 |   91.66 | 28-41,119                                                            
  MessageList.tsx                |    6.55 |      100 |       0 |    6.55 | 9...(truncated)
```

---
*Generated by Netra AI Unified Test Runner*
