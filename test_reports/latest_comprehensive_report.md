# Netra AI Platform - Test Report

**Generated:** 2025-08-11T15:22:05.087150  
**Test Level:** comprehensive - Full test suite with coverage (10-15 minutes)  
**Purpose:** Pre-release validation, full system testing

## Test Summary

**Total Tests:** 2989  
**Passed:** 1749  
**Failed:** 978  
**Skipped:** 41  
**Errors:** 221  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 2727 | 1735 | 730 | 41 | 221 | 214.09s | [FAILED] |
| Frontend  | 262 | 14 | 248 | 0 | 0 | 77.22s | [FAILED] |

## Environment and Configuration

- **Test Level:** comprehensive
- **Description:** Full test suite with coverage (10-15 minutes)
- **Purpose:** Pre-release validation, full system testing
- **Timeout:** 900s
- **Coverage Enabled:** Yes
- **Total Duration:** 291.30s
- **Exit Code:** 3

### Backend Configuration
```
--coverage --parallel=auto --html-output
```

### Frontend Configuration
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
  Environment: development

Running command:
  pytest app/tests tests integration_tests -v -n auto --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 --html=reports/tests/report.html --self-contained-html --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 14/14 workers
14 workers [2874 items]

scheduling tests via LoadScheduling

app\tests\agents\test_data_sub_agent_comprehensive.py::TestAnalysisEngine::test_detect_trend_decreasing 
app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_1_complete_agent_lifecycle_request_to_completion 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_transform_data_invalid_json 
app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_0 
app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_1 
app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestAgentUtilsHelperFunctions::test_parallel_execution_helper 
app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAsyncOperations::test_concurrent_executions 
app\tests\agents\test_triage_sub_agent.py::TestToolRecommendation::test_recommend_tools_for_cost_optimization 
app\tests\clickhouse\test_performance_edge_cases.py::TestMetricsCalculation::test_trend_detection_insufficient_data 
app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_submit_task_during_shutdown 
app\tests\core\test_core_infrastructure_11_20.py::TestErrorHandlers::test_error_response_structure 
app\tests\core\test_async_utils_complete.py::TestAsyncResourceManagerComplete::test_full_lifecycle 
app\tests\core\test_error_handling.py::TestErrorHandlerFunctions::test_netra_exception_handler 
app\tests\core\test_missing_tests_11_30.py::TestConfigValidator::test_weak_jwt_secret_in_production_rejected 
[gw12][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_core_infrastructure_11_20.py::TestErrorHandlers::test_error_response_structure 
[gw6][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_triage_sub_agent.py::TestToolRecommendation::test_recommend_tools_for_cost_optimization 
app\tests\core\test_core_infrastructure_11_20.py::TestErrorHandlers::test_http_exception_handler 
app\tests\agents\test_triage_sub_agent.py::TestToolRecommendation::test_recommend_tools_for_performance 
[gw6][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_triage_sub_agent.py::TestToolRecommendation::test_recommend_tools_for_performance 
[gw13][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_missing_tests_11_30.py::TestConfigValidator::test_weak_jwt_secret_in_production_rejected 
app\tests\agents\test_triage_sub_agent.py::TestFallbackCategorization::test_fallback_with_optimize_keyword 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_transform_data_invalid_json 
app\tests\core\test_missing_tests_11_30.py::TestConfigValidator::test_validation_report_generation 
[gw11][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_error_handling.py::TestErrorHandlerFunctions::test_netra_exception_handler 
[gw9][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAsyncOperations::test_concurrent_executions 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_transform_data_non_json 
app\tests\core\test_error_handling.py::TestErrorHandlerFunctions::test_validation_exception_handler 
[gw13][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_missing_tests_11_30.py::TestConfigValidator::test_validation_report_generation 
app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAsyncOperations::test_websocket_streaming_updates 
[gw11][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_error_handling.py::TestErrorHandlerFunctions::test_validation_exception_handler 
app\tests\core\test_missing_tests_11_30.py::TestErrorContext::test_trace_id_management 
[gw13][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_missing_tests_11_30.py::TestErrorContext::test_trace_id_management 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_transform_data_non_json 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_enrich_data_basic 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_enrich_data_basic 
app\tests\core\test_missing_tests_11_30.py::TestErrorContext::test_request_id_context 
app\tests\core\test_error_handling.py::TestErrorHandlerFunctions::test_http_exception_handler 
[gw11][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_error_handling.py::TestErrorHandlerFunctions::test_http_exception_handler 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_enrich_data_external 
app\tests\core\test_error_handling.py::TestErrorHandlerFunctions::test_general_exception_handler 
[gw13][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_missing_tests_11_30.py::TestErrorContext::test_request_id_context 
app\tests\core\test_missing_tests_11_30.py::TestErrorContext::test_user_id_context 
[gw13][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_missing_tests_11_30.py::TestErrorContext::test_user_id_context 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_enrich_data_external 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_enrich_data_no_source 
[gw11][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_error_handling.py::TestErrorHandlerFunctions::test_general_exception_handler 
app\tests\core\test_error_handling.py::TestErrorResponseModel::test_error_response_creation 
[gw11][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_error_handling.py::TestErrorResponseModel::test_error_response_creation 
[gw3][36m [  0%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_1 
app\tests\core\test_missing_tests_11_30.py::TestErrorHandlers::test_retry_on_transient_error 
app\tests\core\test_error_handling.py::TestErrorResponseModel::test_error_response_with_details 
app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_2 
[gw4][36m [  0%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_0 
app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_1 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_enrich_data_no_source 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_batch 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_batch 
[gw11][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_error_handling.py::TestErrorResponseModel::test_error_response_with_details 
app\tests\core\test_error_handling.py::TestErrorResponseModel::test_error_response_serialization 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_batch_empty 
[gw6][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_triage_sub_agent.py::TestFallbackCategorization::test_fallback_with_optimize_keyword 
app\tests\agents\test_triage_sub_agent.py::TestFallbackCategorization::test_fallback_with_unknown_request 
[gw6][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_triage_sub_agent.py::TestFallbackCategorization::test_fallback_with_unknown_request 
[gw11][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_error_handling.py::TestErrorResponseModel::test_error_response_serialization 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_batch_empty 
app\tests\core\test_fallback_handler.py::TestFallbackHandler::test_initialization 
app\tests\agents\test_triage_sub_agent.py::TestJSONExtraction::test_extract_valid_json 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_apply_operation 
[gw11][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_fallback_handler.py::TestFallbackHandler::test_initialization 
app\tests\core\test_fallback_handler.py::TestFallbackHandler::test_generate_fallback_triage_failure 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_apply_operation 
app\tests\ag...(truncated)
```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> jest --coverage --coverageDirectory=../reports/frontend-coverage

---------------------------------|---------|----------|---------|---------|---------------------------------------------------------------------------------------------------
File                             | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s                                                                                 
---------------------------------|---------|----------|---------|---------|---------------------------------------------------------------------------------------------------
All files                        |   64.72 |    79.12 |   49.24 |   64.72 |                                                                                                   
 frontend                        |     100 |        0 |     100 |     100 |                                                                                                   
  config.ts                      |     100 |        0 |     100 |     100 | 2-3                                                                                               
 frontend/app                    |      45 |      100 |       0 |      45 |                                                                                                   
  layout.tsx                     |   57.14 |      100 |       0 |   57.14 | 17-28                                                                                             
  page.tsx                       |   34.37 |      100 |       0 |   34.37 | 10-30                                                                                             
 frontend/app/chat               |   69.23 |      100 |       0 |   69.23 |                                                                                                   
  page.tsx                       |   69.23 |      100 |       0 |   69.23 | 8-11                                                                                              
 frontend/auth                   |   92.51 |    98.21 |   86.66 |   92.51 |                                                                                                   
  components.tsx                 |     100 |      100 |     100 |     100 |                                                                                                   
  context.tsx                    |   81.96 |    95.23 |   33.33 |   81.96 | 72-77,94-99,102-111                                                                               
  index.ts                       |     100 |      100 |     100 |     100 |                                                                                                   
  service.ts                     |     100 |      100 |     100 |     100 |                                                                                                   
  types.ts                       |     100 |      100 |     100 |     100 |                                                                                                   
 frontend/components             |   85.25 |    98.79 |    82.6 |   85.25 |                                                                                                   
  AppWithLayout.tsx              |   33.33 |      100 |       0 |   33.33 | 14-39                                                                                             
  ChatHistorySection.tsx         |     100 |      100 |     100 |     100 |                                                                                                   
  CorpusAdmin.tsx                |     100 |      100 |     100 |     100 |                                                                                                   
  ErrorFallback.tsx              |     100 |      100 |     100 |     100 |                                                                                                   
  Footer.tsx                     |     100 |      100 |     100 |     100 |                                                                                                   
  Header.tsx                     |   48.14 |      100 |       0 |   48.14 | 14-27                                                                                             
  Icons.tsx                      |     100 |      100 |     100 |     100 |                                                                                                   
  LoginButton.tsx                |   18.51 |      100 |       0 |   18.51 | 6-27                                                                                              
  NavLinks.tsx                   |   45.71 |      100 |       0 |   45.71 | 33-70                                                                                             
  SubAgentStatus.tsx             |     100 |    94.11 |     100 |     100 | 43                                                                                                
 frontend/components/chat        |   70.38 |    74.28 |   69.44 |   70.38 |                                                                                                   
  ChatHeader.tsx                 |   95.89 |       60 |     100 |   95.89 | 16,19,41,43,45-46                                                                                 
  ChatSidebar.tsx                |    3.11 |      100 |       0 |    3.11 | 13-385                                                                                            
  ExamplePrompts.tsx             |     100 |      100 |     100 |     100 |                                                                                                   
  MainChat.tsx                   |   96.26 |      100 |      25 |   96.26 | 54-58                                                                                             
  MessageInput.tsx               |   93.06 |    74.41 |     100 |   93.06 | 51-53,104-105,124-129,131-140                                                                     
  MessageItem.tsx                |   91.66 |       75 |     100 |   91.66 | 28-41,119                                                                                         
  MessageList.tsx                |    6.55 |      100 |       0 |    6.55 | 9-122                                                                                             
  OverflowPanel.tsx              |   86.41 |       75 |   16.66 |   86.41 | 54-60,67-88,93-98,132-133,218-219                                                                 
  PersistentResponseCard.tsx     |     100 |      100 |     100 |     100 |                                                                                                   
  RawJsonView.tsx                |   56.25 |      100 |       0 |   56.25 | 10-16                                                                                             
  ThinkingIndicator.tsx          |   95.23 |    38.46 |     100 |   95.23 | 31,33,35,44,46,48                                                                                 
 frontend/components/chat/layers |   39.03 |      100 |      50 |   39.03 |                                                                                                   
  FastLayer.tsx                  |     100 |      100 |     100 |     100 |                                                                                                   
  MediumLayer.tsx                |    5.44 |      100 |       0 |    5.44 | 9-147                                                                                             
 frontend/components/ui          |   82.93 |    93.33 |   54.16 |   82.93 |                                                                                                   
  accordion.tsx                  |   19.69 |      100 |       0 |   19.69 | 9-13,15-26,28-48,50-64                                                                            
  alert.tsx                      |     100 |      100 |     100 |     100 |                                                                                                   
  avatar.tsx                     |     100 |      100 |     100 |     100 |                                                                                                   
  badge.tsx                      |   86.11 |      100 |       0 |   86.11 | 30-34                                                                                             
  button.tsx                     |     100 |       50 |     100 |     100 | 45                                                                                                
  card.tsx                       |     100 |      100 |     100 |     100 |                                                                                                   
  collapsible.tsx                |     100 |      100 |     100 |     100 |                                                                                                   
  dropdown-menu.tsx              |      95 |      100 |       0 |      95 | 172-181                                                                                           
  input.tsx                      |      50 |      100 |     100 |      50 | 9-20                                                                                              
  label.tsx                      |     100 |      100 |     100 |     100 |                                                                                                   
  progress.tsx                   |   25.71 |      100 |       0 |   25.71 | 8-33                                                                                              
  scroll-area.tsx                |     100 |      100 |     100 |     100 |                                                                                                   
  select.tsx                     |     100 |      100 |     100 |     100 |                    ...(truncated)
```

## Error Summary

### Backend Errors
- [gw3][36m [  0%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_1
- [gw4][36m [  0%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_0
- [gw3][36m [  1%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_2
- [gw4][36m [  1%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_1
- [gw3][36m [  1%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_3
- [gw4][36m [  1%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_2
- [gw5][36m [  1%] [0m[31mFAILED[0m app\tests\clickhouse\test_performance_edge_cases.py::TestMetricsCalculation::test_trend_detection_insufficient_data
- [gw3][36m [  1%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_4
- [gw4][36m [  1%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_3
- [gw2][36m [  1%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestAnalysisEngine::test_detect_trend_decreasing
- [gw9][36m [  1%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAsyncOperations::test_websocket_streaming_updates
- [gw8][36m [  2%] [0m[31mFAILED[0m app\tests\core\test_async_utils_complete.py::TestAsyncResourceManagerComplete::test_full_lifecycle
- [gw12][36m [  2%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestErrorHandlers::test_http_exception_handler
- [gw10][36m [  2%] [0m[31mFAILED[0m app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_submit_task_during_shutdown
- [gw13][36m [  2%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestErrorHandlers::test_retry_on_transient_error
- [gw4][36m [  2%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_4
- [gw3][36m [  2%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_5
- [gw12][36m [  2%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestCustomExceptions::test_netra_exception_structure
- [gw6][36m [  2%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent.py::TestJSONExtraction::test_repair_json_with_trailing_comma
- [gw9][36m [  2%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAsyncOperations::test_async_cleanup_operations
- [gw13][36m [  2%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestErrorHandlers::test_fallback_strategy_activation
- [gw12][36m [  2%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestCustomExceptions::test_authentication_error
- [gw11][36m [  2%] [0m[31mFAILED[0m app\tests\core\test_fallback_handler.py::TestFallbackHandler::test_detect_domain_optimization
- [gw4][36m [  2%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_5
- [gw3][36m [  2%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_6
- [gw6][36m [  2%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent.py::TestJSONExtraction::test_extract_json_with_single_quotes
- [gw2][36m [  2%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestAnalysisEngine::test_detect_seasonality_with_pattern
- [gw9][36m [  2%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestPydanticModelValidation::test_triage_result_comprehensive_validation
- [gw12][36m [  2%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestLoggingManager::test_logging_configuration
- [gw11][36m [  3%] [0m[31mFAILED[0m app\tests\core\test_fallback_handler.py::TestFallbackHandler::test_extract_error_reason
- [gw3][36m [  3%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_7
- [gw4][36m [  3%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_6
- [gw10][36m [  3%] [0m[31mFAILED[0m app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_submit_background_task_during_shutdown
- [gw2][36m [  3%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestAnalysisEngine::test_detect_seasonality_no_pattern
- [gw12][36m [  3%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestResourceManager::test_resource_tracking
- [gw6][36m [  3%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent.py::TestCaching::test_cache_miss_and_store
- [gw13][36m [  3%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestErrorHandlers::test_circuit_breaker_opens
- [gw11][36m [  3%] [0m[31mFAILED[0m app\tests\core\test_fallback_handler.py::TestFallbackHandler::test_summarize_partial_data
- [gw4][36m [  3%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_7
- [gw3][36m [  3%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_8
- [gw12][36m [  3%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestResourceManager::test_resource_limits
- [gw12][36m [  3%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestSchemaSync::test_schema_validation
- [gw13][36m [  3%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestCustomExceptions::test_netra_exception_hierarchy
- [gw4][36m [  3%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_8
- [gw3][36m [  3%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_9
- [gw8][36m [  3%] [0m[31mFAILED[0m app\tests\core\test_async_utils_complete.py::TestAsyncTaskPoolComplete::test_complete_task_pool_lifecycle
- [gw6][36m [  3%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent.py::TestExecuteMethod::test_successful_execution
- [gw11][36m [  3%] [0m[31mFAILED[0m app\tests\core\test_fallback_handler.py::TestFallbackHandler::test_format_optimization_results
- [gw12][36m [  3%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestSchemaSync::test_migration_safety_checks
- [gw9][36m [  4%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestPydanticModelValidation::test_triage_result_edge_case_validation
- [gw2][36m [  4%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestAnalysisEngine::test_identify_outliers_zscore_method
- [gw4][36m [  4%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_3_variation_9
- [gw12][36m [  4%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestSecretManager::test_secret_encryption
- [gw3][36m [  4%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_9_variation_0
- [gw9][36m [  4%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestPydanticModelValidation::test_extracted_entities_complex_validation
- [gw12][36m [  4%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestSecretManager::test_secret_validation
- [gw6][36m [  4%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent.py::TestExecuteMethod::test_execution_with_retry
- [gw13][36m [  4%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestCustomExceptions::test_exception_with_context
- [gw11][36m [  5%] [0m[31mFAILED[0m app\tests\core\test_fallback_handler.py::TestFallbackHandler::test_list_completed_sections
- [gw12][36m [  5%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestUnifiedLogging::test_log_correlation
- [gw4][36m [  5%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_4_variation_0
- [gw3][36m [  5%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_9_variation_1
- [gw13][36m [  5%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestCustomExceptions::test_exception_serialization
- [gw12][36m [  5%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestUnifiedLogging::test_log_aggregation
- [gw6][36m [  5%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent.py::TestExecuteMethod::test_execution_with_fallback
- [gw11][36m [  5%] [0m[31mFAILED[0m app\tests\core\test_fallback_handler.py::TestFallbackHandler::test_extract_key_findings
- [gw4][36m [  5%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_4_variation_1
- [gw3][36m [  5%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_9_variation_2
- [gw12][36m [  5%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestStartupChecks::test_database_check
- [gw12][36m [  6%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestStartupChecks::test_service_health_checks
- [gw13][36m [  6%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestLoggingManager::test_log_level_configuration
- [gw4][36m [  6%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_4_variation_2
- [gw9][36m [  6%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestPydanticModelValidation::test_user_intent_comprehensive
- [gw3][36m [  6%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_9_variation_3
- [gw6][36m [  6%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent.py::TestExecuteMethod::test_execution_with_websocket_updates
- [gw4][36m [  7%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_4_variation_3
- [gw13][36m [  7%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestLoggingManager::test_log_rotation_setup
- [gw3][36m [  7%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_9_variation_4
- [gw9][36m [  7%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestPerformanceOptimization::test_hash_generation_performance
- [gw4][36m [  7%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_4_variation_4
- [gw13][36m [  7%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestLoggingManager::test_structured_logging_format
- [gw3][36m [  7%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_9_variation_5
- [gw2][36m [  7%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_detect_anomalies_found
- [gw4][36m [  7%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_4_variation_5
- [gw9][36m [  8%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestEdgeCasesAndBoundaryConditions::test_empty_and_whitespace_requests
- [gw3][36m [  8%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_9_variation_6
- [gw13][36m [  8%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestResourceManager::test_resource_allocation
- [gw1][36m [  8%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_load_state
- [gw4][36m [  8%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_4_variation_6
- [gw9][36m [  8%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestEdgeCasesAndBoundaryConditions::test_extremely_long_requests
- [gw3][36m [  8%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_9_variation_7
- [gw12][36m [  8%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestStartupChecks::test_graceful_degradation
- [gw13][36m [  8%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestResourceManager::test_resource_cleanup_on_exhaustion
- [gw4][36m [  8%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_4_variation_7
- [gw6][36m [  8%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent.py::TestCleanup::test_cleanup_with_metrics
- [gw3][36m [  8%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_9_variation_8
- [gw1][36m [  9%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_1_variation_0
- [gw7][36m [  9%] [0m[31mFAILED[0m app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_execute_agent
- [gw9][36m [  9%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestEdgeCasesAndBoundaryConditions::test_malformed_json_responses
- [gw2][36m [  9%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_execute_optimize_intent
- [gw13][36m [  9%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestResourceManager::test_resource_release
- [gw4][36m [  9%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_4_variation_8
- [gw3][36m [  9%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_9_variation_9
- [gw1][36m [  9%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_1_variation_1
- [gw7][36m [  9%] [0m[31mFAILED[0m app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_process_scheduled_research
- [gw6][36m [  9%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAdvancedInitialization::test_initialization_configuration_values
- [gw13][36m [  9%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestSchemaSync::test_schema_validation
- [gw2][36m [ 10%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_execute_analyze_intent
- [gw4][36m [ 10%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_4_variation_9
- [gw11][36m [ 10%] [0m[31mFAILED[0m app\tests\core\test_fallback_handler.py::TestFallbackHandler::test_generate_fallback_template_formatting_error
- [gw1][36m [ 10%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_1_variation_2
- [gw6][36m [ 10%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestValidationPatterns::test_sql_injection_patterns
- [gw13][36m [ 10%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestSchemaSync::test_migration_safety_check
- [gw4][36m [ 10%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_5_variation_0
- [gw11][36m [ 10%] [0m[31mFAILED[0m app\tests\core\test_fallback_handler.py::TestFallbackHandler::test_format_fallback_data_serialization_error
- [gw1][36m [ 10%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_1_variation_3
- [gw2][36m [ 10%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_execute_monitor_intent
- [gw6][36m [ 10%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestValidationPatterns::test_script_injection_patterns
- [gw4][36m [ 11%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_5_variation_1
- [gw13][36m [ 11%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestSchemaSync::test_schema_diff_detection
- [gw12][36m [ 11%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestMigrationRunnerSafety::test_migration_rollback
- [gw1][36m [ 11%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_1_variation_4
- [gw6][36m [ 11%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestValidationPatterns::test_command_injection_patterns
- [gw4][36m [ 11%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_5_variation_2
- [gw12][36m [ 11%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestMigrationRunnerSafety::test_migration_transaction_safety
- [gw13][36m [ 11%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestSecretManager::test_secret_encryption_decryption
- [gw2][36m [ 11%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_execute_general_intent
- [gw1][36m [ 11%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_1_variation_5
- [gw6][36m [ 11%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAdvancedEntityExtraction::test_extract_complex_model_names
- [gw12][36m [ 11%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestDatabaseHealthChecks::test_health_monitoring
- [gw4][36m [ 12%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_5_variation_3
- [gw7][36m [ 12%] [0m[31mFAILED[0m app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_api_failure_handling
- [gw13][36m [ 12%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestSecretManager::test_secret_rotation
- [gw1][36m [ 12%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_1_variation_6
- [gw12][36m [ 12%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestDatabaseHealthChecks::test_alert_thresholds
- [gw6][36m [ 12%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAdvancedEntityExtraction::test_extract_comprehensive_metrics
- [gw2][36m [ 12%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_execute_with_exception_fallback
- [gw4][36m [ 12%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_5_variation_4
- [gw12][36m [ 12%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestCacheInvalidationStrategy::test_cache_invalidation
- [gw13][36m [ 12%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestSecretManager::test_secure_secret_storage
- [gw1][36m [ 12%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_1_variation_7
- [gw6][36m [ 12%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAdvancedEntityExtraction::test_extract_numerical_thresholds_complex
- [gw4][36m [ 12%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_5_variation_5
- [gw7][36m [ 12%] [0m[31mFAILED[0m app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_redis_cache_integration
- [gw12][36m [ 12%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestCacheInvalidationStrategy::test_ttl_management
- [gw2][36m [ 12%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_execute_with_invalid_llm_response
- [gw11][36m [ 12%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestSupplyRoute::test_supply_data_enrichment
- [gw1][36m [ 12%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_1_variation_8
- [gw13][36m [ 12%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestUnifiedLogging::test_correlation_id_propagation
- [gw12][36m [ 12%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestSessionManagement::test_session_lifecycle
- [gw9][36m [ 12%] [0m[31mFAILED[0m app\tests\clickhouse\test_corpus_generation_coverage.py::TestCorpusLifecycle::test_corpus_creation_workflow
- [gw7][36m [ 12%] [0m[31mFAILED[0m app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_e2e_admin_chat_supply_update
- [gw6][36m [ 13%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAdvancedEntityExtraction::test_extract_time_ranges_complex
- [gw4][36m [ 13%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_5_variation_6
- [gw1][36m [ 13%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_1_variation_9
- [gw12][36m [ 13%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestSessionManagement::test_session_timeout
- [gw13][36m [ 13%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestUnifiedLogging::test_log_aggregation_from_multiple_sources
- [gw4][36m [ 13%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_5_variation_7
- [gw6][36m [ 13%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAdvancedIntentDetermination::test_intent_confidence_scoring
- [gw1][36m [ 13%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_2_variation_0
- [gw4][36m [ 13%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_5_variation_8
- [gw13][36m [ 13%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestUnifiedLogging::test_structured_context_addition
- [gw6][36m [ 13%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAdvancedIntentDetermination::test_intent_context_awareness
- [gw1][36m [ 14%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_2_variation_1
- [gw9][36m [ 14%] [0m[31mFAILED[0m app\tests\clickhouse\test_corpus_generation_coverage.py::TestCorpusLifecycle::test_corpus_status_transitions
- [gw4][36m [ 14%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_5_variation_9
- [gw13][36m [ 14%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestStartupChecks::test_database_connectivity_check
- [gw6][36m [ 14%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAdvancedToolRecommendation::test_recommend_tools_category_matching
- [gw9][36m [ 14%] [0m[31mFAILED[0m app\tests\clickhouse\test_corpus_generation_coverage.py::TestCorpusLifecycle::test_corpus_deletion_workflow
- [gw1][36m [ 14%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_2_variation_2
- [gw4][36m [ 14%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_6_variation_0
- [gw13][36m [ 14%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestStartupChecks::test_external_service_health_check
- [gw6][36m [ 14%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestCachingMechanisms::test_cache_key_generation
- [gw1][36m [ 14%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_2_variation_3
- [gw7][36m [ 15%] [0m[31mFAILED[0m app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearchIntegration::test_full_research_workflow
- [gw4][36m [ 15%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_6_variation_1
- [gw13][36m [ 15%] [0m[31mERROR[0m app\tests\core\test_missing_tests_11_30.py::TestStartupChecks::test_graceful_degradation_on_failure
- [gw1][36m [ 15%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_2_variation_4
- [gw4][36m [ 15%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_6_variation_2
- [gw1][36m [ 15%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_2_variation_5
- [gw11][36m [ 16%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestSupplyRoute::test_supply_chain_validation
- [gw4][36m [ 16%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_6_variation_3
- [gw1][36m [ 16%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_2_variation_6
- [gw13][36m [ 16%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestAdminRoute::test_admin_endpoint_requires_auth
- [gw2][36m [ 16%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_without_metadata_attribute
- [gw4][36m [ 16%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_6_variation_4
- [gw1][36m [ 16%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_2_variation_7
- [gw2][36m [ 16%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_exception_types
- [gw4][36m [ 16%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_6_variation_5
- [gw9][36m [ 16%] [0m[31mFAILED[0m app\tests\clickhouse\test_corpus_generation_coverage.py::TestContentGeneration::test_content_generation_job_flow
- [gw1][36m [ 16%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_2_variation_8
- [gw4][36m [ 16%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_6_variation_6
- [gw1][36m [ 17%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_2_variation_9
- [gw4][36m [ 17%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_6_variation_7
- [gw9][36m [ 17%] [0m[31mFAILED[0m app\tests\clickhouse\test_corpus_generation_coverage.py::TestBatchProcessing::test_batch_content_upload
- [gw11][36m [ 17%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestSyntheticDataRoute::test_synthetic_data_generation
- [gw4][36m [ 17%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_6_variation_8
- [gw4][36m [ 18%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_6_variation_9
- [gw7][36m [ 18%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestMCPRoute::test_mcp_message_handling
- [gw13][36m [ 18%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestAdminRoute::test_admin_endpoint_requires_admin_role
- [gw2][36m [ 18%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_cost_analyzer.py::TestCostAnalyzer::test_cost_analyzer_async_execution
- [gw4][36m [ 18%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_7_variation_0
- [gw4][36m [ 18%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_7_variation_1
- [gw1][36m [ 18%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestThreadRepositoryOperations::test_thread_crud_operations
- [gw7][36m [ 18%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestMCPRoute::test_mcp_tool_execution
- [gw1][36m [ 18%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestThreadRepositoryOperations::test_soft_delete_functionality
- [gw4][36m [ 18%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_7_variation_2
- [gw1][36m [ 18%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestMessageRepositoryQueries::test_message_pagination
- [gw4][36m [ 18%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_7_variation_3
- [gw11][36m [ 18%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestSyntheticDataRoute::test_synthetic_data_validation
- [gw1][36m [ 18%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestMessageRepositoryQueries::test_complex_message_queries
- [gw1][36m [ 18%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestUserRepositoryAuth::test_password_hashing
- [gw9][36m [ 18%] [0m[31mFAILED[0m app\tests\clickhouse\test_corpus_generation_coverage.py::TestCorpusCloning::test_corpus_clone_workflow
- [gw4][36m [ 19%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_7_variation_4
- [gw1][36m [ 19%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestUserRepositoryAuth::test_authentication_flow
- [gw13][36m [ 19%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestAdminRoute::test_admin_can_access_admin_endpoints
- [gw2][36m [ 19%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_cost_analyzer.py::TestCostAnalyzer::test_cost_analyzer_rounding_edge_cases
- [gw4][36m [ 19%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_7_variation_5
- [gw7][36m [ 19%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestQualityRoute::test_quality_metrics_retrieval
- [gw1][36m [ 19%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestOptimizationRepositoryStorage::test_optimization_versioning
- [gw1][36m [ 19%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestOptimizationRepositoryStorage::test_optimization_history
- [gw4][36m [ 19%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_7_variation_6
- [gw1][36m [ 19%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestMetricRepositoryAggregation::test_metric_aggregation
- [gw4][36m [ 19%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_7_variation_7
- [gw1][36m [ 19%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestMetricRepositoryAggregation::test_time_series_queries
- [gw4][36m [ 19%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_7_variation_8
- [gw11][36m [ 19%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestSyntheticDataRoute::test_synthetic_data_templates
- [gw7][36m [ 19%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestQualityRoute::test_quality_aggregation
- [gw4][36m [ 19%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_7_variation_9
- [gw13][36m [ 19%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestAgentRoute::test_agent_message_processing
- [gw7][36m [ 19%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestQualityRoute::test_quality_alerts
- [gw4][36m [ 19%] [0m[31mERROR[0m app\tests\agents\test_example_prompts_e2e_real.py::TestExamplePromptsE2ERealLLM::test_prompt_8_variation_0
- [gw2][36m [ 20%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_basic_functionality
- [gw4][36m [ 20%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_register_resource_overwrite
- [gw7][36m [ 20%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestSupplyRoute::test_supply_research
- [gw11][36m [ 20%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestThreadsRouteExtended::test_thread_pagination
- [gw13][36m [ 20%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestAgentRoute::test_agent_response_streaming
- [gw4][36m [ 20%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_threads_resource_list
- [gw2][36m [ 20%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_empty_logs
- [gw1][36m [ 20%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestClickHouseConnectionPool::test_connection_pooling
- [gw4][36m [ 20%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_threads_resource_specific
- [gw1][36m [ 20%] [0m[31mFAILED[0m app\tests\database\test_repositories_comprehensive.py::TestClickHouseConnectionPool::test_query_timeout
- [gw4][36m [ 20%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_threads_resource_invalid_path
- [gw7][36m [ 20%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestSupplyRoute::test_supply_data_enrichment
- [gw7][36m [ 20%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestSupplyRoute::test_supply_validation
- [gw4][36m [ 20%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_agents_resource_list
- [gw11][36m [ 20%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestThreadsRouteExtended::test_thread_search
- [gw4][36m [ 20%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_agents_resource_state
- [gw2][36m [ 20%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_single_log
- [gw4][36m [ 20%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_agents_resource_invalid_path
- [gw13][36m [ 20%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestAgentRoute::test_agent_error_handling
- [gw4][36m [ 20%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_corpus_resource
- [gw13][36m [ 20%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestConfigRoute::test_config_update_validation
- [gw4][36m [ 20%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_corpus_search_resource
- [gw7][36m [ 20%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestSyntheticDataRoute::test_synthetic_data_generation
- [gw4][36m [ 20%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_metrics_workload_resource
- [gw2][36m [ 21%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_high_latency_values
- [gw11][36m [ 21%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestThreadsRouteExtended::test_thread_archival
- [gw4][36m [ 21%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_metrics_optimization_resource
- [gw4][36m [ 21%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_metrics_invalid_type
- [gw13][36m [ 21%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestConfigRoute::test_config_update_persistence
- [gw4][36m [ 21%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_synthetic_data_schemas
- [gw4][36m [ 21%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_synthetic_data_generated
- [gw7][36m [ 21%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestSyntheticDataRoute::test_synthetic_data_validation
- [gw2][36m [ 21%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_zero_latency
- [gw11][36m [ 21%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestThreadsRouteExtended::test_thread_export
- [gw13][36m [ 21%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestConfigRoute::test_config_retrieval
- [gw4][36m [ 21%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_supply_models
- [gw7][36m [ 21%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestSyntheticDataRoute::test_synthetic_data_templates
- [gw4][36m [ 21%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_read_supply_providers
- [gw2][36m [ 21%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_sub_millisecond_latency
- [gw4][36m [ 21%] [0m[31mFAILED[0m app\tests\mcp\test_resource_manager.py::TestResourceManager::test_access_logging_success
- [gw13][36m [ 22%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestCorpusRoute::test_corpus_create_operation
- [gw7][36m [ 23%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestThreadsRoute::test_thread_creation
- [gw11][36m [ 23%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestDatabaseRepositoryTransactions::test_nested_transaction_handling
- [gw2][36m [ 23%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentLifecycleManagement::test_agent_task_failure_handling
- [gw4][36m [ 23%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestUnitOfWork::test_uow_transaction_commit
- [gw11][36m [ 23%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestDatabaseRepositoryTransactions::test_batch_operation_transaction_consistency
- [gw13][36m [ 23%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestCorpusRoute::test_corpus_search_functionality
- [gw11][36m [ 23%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestDatabaseRepositoryTransactions::test_deadlock_detection_and_retry
- [gw4][36m [ 23%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestUnitOfWork::test_uow_transaction_rollback
- [gw11][36m [ 23%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestDatabaseRepositoryTransactions::test_connection_recovery_handling
- [gw4][36m [ 23%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestUnitOfWork::test_uow_nested_transactions
- [gw7][36m [ 23%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestThreadsRoute::test_thread_pagination
- [gw7][36m [ 23%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestThreadsRoute::test_thread_archival
- [gw11][36m [ 23%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestTransactionPerformanceAndScaling::test_high_concurrency_transactions
- [gw4][36m [ 23%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestUnitOfWork::test_uow_concurrent_access
- [gw11][36m [ 24%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestTransactionPerformanceAndScaling::test_batch_transaction_performance
- [gw4][36m [ 24%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_create
- [gw13][36m [ 24%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestCorpusRoute::test_corpus_update_operation
- [gw11][36m [ 24%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestTransactionPerformanceAndScaling::test_transaction_memory_usage
- [gw4][36m [ 24%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_bulk_create
- [gw11][36m [ 24%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestTransactionPerformanceAndScaling::test_transaction_resource_cleanup
- [gw4][36m [ 24%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_get_by_id
- [gw4][36m [ 24%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_get_many
- [gw4][36m [ 24%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_update
- [gw4][36m [ 24%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_delete
- [gw4][36m [ 25%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_soft_delete
- [gw11][36m [ 25%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_generate_optimization_fallback_low_quality
- [gw4][36m [ 25%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_pagination
- [gw4][36m [ 25%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestMessageRepository::test_get_messages_by_thread
- [gw5][36m [ 25%] [0m[31mFAILED[0m app\tests\clickhouse\test_query_correctness.py::TestAnomalyDetectionQueries::test_anomaly_detection_query_structure
- [gw4][36m [ 25%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestMessageRepository::test_get_messages_with_pagination
- [gw11][36m [ 25%] [0m[31mFAILED[0m app\tests\services\test_llm_cache_service.py::test_llm_cache_service_initialization
- [gw5][36m [ 25%] [0m[31mFAILED[0m app\tests\clickhouse\test_query_correctness.py::TestUsagePatternQueries::test_usage_patterns_query_structure
- [gw11][36m [ 26%] [0m[31mFAILED[0m app\tests\services\test_llm_cache_service.py::test_cache_set_and_get
- [gw4][36m [ 26%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestMessageRepository::test_get_latest_messages
- [gw13][36m [ 26%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestLLMCacheRoute::test_cache_invalidation
- [gw11][36m [ 26%] [0m[31mFAILED[0m app\tests\services\test_llm_cache_service.py::test_cache_expiration
- [gw5][36m [ 26%] [0m[31mFAILED[0m app\tests\clickhouse\test_query_correctness.py::TestCorrelationQueries::test_correlation_analysis_query
- [gw11][36m [ 26%] [0m[31mFAILED[0m app\tests\services\test_llm_cache_service.py::test_cache_size_limit
- [gw11][36m [ 26%] [0m[31mFAILED[0m app\tests\services\test_llm_cache_service.py::test_cache_stats
- [gw4][36m [ 26%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestThreadRepository::test_get_threads_by_user
- [gw2][36m [ 26%] [0m[31mERROR[0m app\tests\services\test_apex_optimizer_tool_selection.py::TestApexOptimizerToolSelection::test_tool_selection_cost_optimization
- [gw4][36m [ 26%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestThreadRepository::test_get_active_threads
- [gw5][36m [ 26%] [0m[31mFAILED[0m app\tests\clickhouse\test_query_correctness.py::TestNestedArrayQueries::test_nested_array_existence_check
- [gw2][36m [ 26%] [0m[31mFAILED[0m app\tests\services\test_apex_optimizer_tool_selection.py::TestApexOptimizerToolSelection::test_tool_selection_latency_optimization
- [gw5][36m [ 26%] [0m[31mFAILED[0m app\tests\clickhouse\test_query_correctness.py::TestErrorHandling::test_null_safety_in_calculations
- [gw4][36m [ 26%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestThreadRepository::test_archive_thread
- [gw2][36m [ 26%] [0m[31mFAILED[0m app\tests\services\test_apex_optimizer_tool_selection.py::TestApexOptimizerToolSelection::test_tool_selection_cache_optimization
- [gw4][36m [ 26%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestRunRepository::test_create_run_with_tools
- [gw2][36m [ 27%] [0m[31mFAILED[0m app\tests\services\test_apex_optimizer_tool_selection.py::TestApexOptimizerToolSelection::test_tool_selection_model_analysis
- [gw4][36m [ 27%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestRunRepository::test_update_run_status
- [gw11][36m [ 27%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerProviderSwitching::test_provider_registration
- [gw2][36m [ 27%] [0m[31mFAILED[0m app\tests\services\test_apex_optimizer_tool_selection.py::TestApexOptimizerToolSelection::test_tool_selection_multi_objective
- [gw13][36m [ 27%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestLLMCacheRoute::test_cache_metrics_retrieval
- [gw4][36m [ 27%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestRunRepository::test_get_active_runs
- [gw2][36m [ 27%] [0m[31mFAILED[0m app\tests\services\test_apex_optimizer_tool_selection.py::TestApexOptimizerToolSelection::test_tool_selection_empty_query
- [gw4][36m [ 27%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestReferenceRepository::test_create_reference_with_metadata
- [gw2][36m [ 27%] [0m[31mERROR[0m app\tests\services\test_apex_optimizer_tool_selection.py::TestApexOptimizerToolSelection::test_tool_selection_llm_failure
- [gw4][36m [ 28%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestReferenceRepository::test_get_references_by_message
- [gw2][36m [ 28%] [0m[31mERROR[0m app\tests\services\test_apex_optimizer_tool_selection.py::TestApexOptimizerToolSelection::test_tool_selection_invalid_json_response
- [gw1][36m [ 28%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseArraySyntaxFixer::test_complex_query_array_fix
- [gw4][36m [ 28%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestReferenceRepository::test_search_references
- [gw2][36m [ 28%] [0m[31mFAILED[0m app\tests\services\test_apex_optimizer_tool_selection.py::TestApexOptimizerToolSelection::test_custom_tool_selection
- [gw11][36m [ 28%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerProviderSwitching::test_provider_health_check_success
- [gw1][36m [ 28%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseArraySyntaxFixer::test_array_access_with_expressions
- [gw4][36m [ 28%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestDatabaseRepositoryTransactions::test_successful_transaction_commit
- [gw13][36m [ 28%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestLLMCacheRoute::test_selective_cache_clear
- [gw4][36m [ 28%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestDatabaseRepositoryTransactions::test_transaction_rollback_on_integrity_error
- [gw1][36m [ 28%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseArraySyntaxFixer::test_edge_case_array_patterns
- [gw5][36m [ 28%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_calculate_relevance_with_context
- [gw4][36m [ 28%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestDatabaseRepositoryTransactions::test_transaction_rollback_on_sql_error
- [gw4][36m [ 28%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestDatabaseRepositoryTransactions::test_transaction_rollback_on_unexpected_error
- [gw1][36m [ 28%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_fixes_and_executes_query
- [gw5][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_calculate_clarity_scores
- [gw4][36m [ 29%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestDatabaseRepositoryTransactions::test_concurrent_transaction_isolation
- [gw11][36m [ 29%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerProviderSwitching::test_provider_health_check_failure
- [gw1][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_passes_through_correct_queries
- [gw5][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_calculate_redundancy_detection
- [gw1][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_handles_client_errors
- [gw4][36m [ 29%] [0m[31mERROR[0m app\tests\services\test_database_repository_transactions.py::TestDatabaseRepositoryTransactions::test_transaction_timeout_handling
- [gw5][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_calculate_hallucination_risk
- [gw1][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_statistics_tracking
- [gw13][36m [ 29%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestMCPRoute::test_mcp_message_routing
- [gw1][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_can_be_disabled
- [gw13][36m [ 29%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestMCPRoute::test_mcp_protocol_validation
- [gw1][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_with_query_parameters
- [gw11][36m [ 29%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerProviderSwitching::test_round_robin_provider_selection
- [gw1][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_concurrent_interceptor_usage
- [gw4][36m [ 29%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerProviderSwitching::test_provider_statistics_collection
- [gw1][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_statistics_reset
- [gw5][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_store_metrics_in_memory_and_redis
- [gw1][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_get_statistics
- [gw1][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_end_to_end_query_processing
- [gw11][36m [ 29%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerProviderSwitching::test_weighted_provider_selection
- [gw13][36m [ 30%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestMCPRoute::test_mcp_error_response
- [gw1][36m [ 30%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_batch_query_processing
- [gw1][36m [ 30%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_regex_pattern_comprehensive_coverage
- [gw4][36m [ 30%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerLoadBalancing::test_response_time_based_load_balancing
- [gw5][36m [ 30%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_validate_batch_processing
- [gw1][36m [ 30%] [0m[31mERROR[0m app\tests\services\test_clickhouse_service.py::TestClickHouseConnection::test_client_initialization
- [gw5][36m [ 30%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_validate_batch_with_context
- [gw11][36m [ 30%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerProviderSwitching::test_failover_invoke_success
- [gw13][36m [ 30%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestQualityRoute::test_quality_metrics_retrieval
- [gw4][36m [ 30%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerLoadBalancing::test_adaptive_load_balancing
- [gw5][36m [ 30%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_pattern_compilation_in_init
- [gw11][36m [ 31%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerProviderSwitching::test_failover_invoke_preferred_provider
- [gw1][36m [ 31%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestCompleteMetricsCalculation::test_calculate_metrics_complete_workflow
- [gw13][36m [ 31%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestQualityRoute::test_quality_metrics_aggregation
- [gw4][36m [ 31%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerLoadBalancing::test_geographic_load_balancing
- [gw1][36m [ 31%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestActionabilityEdgeCases::test_actionability_with_file_paths
- [gw1][36m [ 31%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestQuantificationPatterns::test_quantification_metric_names
- [gw5][36m [ 31%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestMetricsStorage::test_store_metrics_redis_with_ttl
- [gw13][36m [ 31%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestQualityRoute::test_quality_threshold_alerts
- [gw11][36m [ 31%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerProviderSwitching::test_failover_invoke_provider_failure
- [gw4][36m [ 31%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerStructuredOutput::test_structured_output_with_failover
- [gw4][36m [ 32%] [0m[31mFAILED[0m app\tests\services\test_message_handlers.py::test_handle_start_agent
- [gw1][36m [ 32%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestRelevanceCalculation::test_relevance_technical_terms_matching
- [gw13][36m [ 32%] [0m[31mFAILED[0m app\tests\core\test_missing_tests_11_30.py::TestSupplyRoute::test_supply_research_endpoint
- [gw11][36m [ 32%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerProviderSwitching::test_failover_all_providers_fail
- [gw13][36m [ 32%] [0m[31mFAILED[0m app\tests\mcp\test_websocket_transport.py::TestWebSocketConnection::test_send_json_disconnected
- [gw1][36m [ 32%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestCompletenessCalculation::test_completeness_general_type
- [gw5][36m [ 32%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestIntegrationScenarios::test_complete_optimization_workflow
- [gw5][36m [ 33%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestIntegrationScenarios::test_poor_content_improvement_cycle
- [gw5][36m [ 33%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestQualityMonitoringService::test_initialization_with_custom_config
- [gw11][36m [ 33%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerProviderSwitching::test_provider_cooldown_period
- [gw1][36m [ 33%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestNoveltyCalculation::test_novelty_redis_error_handling
- [gw13][36m [ 33%] [0m[31mFAILED[0m app\tests\mcp\test_websocket_transport.py::TestWebSocketTransport::test_message_processing
- [gw13][36m [ 33%] [0m[31mFAILED[0m app\tests\mcp\test_websocket_transport.py::TestWebSocketTransport::test_json_decode_error_handling
- [gw13][36m [ 34%] [0m[31mFAILED[0m app\tests\mcp\test_websocket_transport.py::TestWebSocketTransport::test_initialization_adds_transport_info
- [gw13][36m [ 34%] [0m[31mFAILED[0m app\tests\mcp\test_websocket_transport.py::TestWebSocketTransport::test_concurrent_request_processing
- [gw11][36m [ 34%] [0m[31mERROR[0m app\tests\services\test_llm_manager_provider_switching.py::TestLLMManagerProviderSwitching::test_concurrent_provider_switching
- [gw1][36m [ 34%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestNoveltyCalculation::test_novelty_large_cache
- [gw1][36m [ 34%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestClarityCalculation::test_clarity_very_long_sentences
- [gw1][36m [ 34%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestClarityCalculation::test_clarity_nested_parentheses
- [gw13][36m [ 35%] [0m[31mFAILED[0m app\tests\mcp\test_websocket_transport.py::TestWebSocketTransport::test_broadcast_to_all
- [gw1][36m [ 35%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service_comprehensive.py::TestRedundancyCalculation::test_redundancy_high_overlap
- [gw5][36m [ 35%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestQualityMonitoringService::test_initialization_with_metrics_collector
- [gw9][36m [ 35%] [0m[31mFAILED[0m app\tests\clickhouse\test_corpus_generation_coverage.py::TestMetadataTracking::test_corpus_metadata_creation
- [gw5][36m [ 35%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestMetricsCollection::test_collect_response_quality_metrics
- [gw11][36m [ 35%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_validate_high_quality_optimization_content
- [gw13][36m [ 35%] [0m[31mFAILED[0m app\tests\mcp\test_websocket_transport.py::TestWebSocketTransport::test_broadcast_to_all_with_exclude
- [gw2][36m [ 36%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_generate_data_analysis_fallback_parsing_error
- [gw5][36m [ 36%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestMetricsCollection::test_collect_system_metrics
- [gw2][36m [ 36%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_generate_action_plan_fallback_context_missing
- [gw11][36m [ 36%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_validate_data_analysis_with_metrics
- [gw2][36m [ 36%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_generate_report_fallback_validation_failed
- [gw1][36m [ 36%] [0m[31mFAILED[0m app\tests\services\test_redis_manager_operations.py::TestRedisManagerOperations::test_redis_connection_success
- [gw5][36m [ 36%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestMetricsCollection::test_collect_error_metrics
- [gw2][36m [ 36%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_generate_triage_fallback_timeout
- [gw11][36m [ 36%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_validate_action_plan_completeness
- [gw2][36m [ 36%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_generate_error_message_fallback_llm_error
- [gw11][36m [ 36%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_validate_with_strict_mode
- [gw2][36m [ 36%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_generate_fallback_with_circular_reasoning
- [gw9][36m [ 36%] [0m[31mFAILED[0m app\tests\clickhouse\test_corpus_generation_coverage.py::TestErrorRecovery::test_table_creation_failure_recovery
- [gw5][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestMetricsCollection::test_batch_metrics_collection
- [gw2][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_generate_fallback_with_hallucination_risk
- [gw1][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_supply_research_scheduler_comprehensive.py::TestResearchSchedule::test_update_after_run
- [gw11][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_validate_error_message_clarity
- [gw2][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_generate_fallback_with_rate_limit
- [gw5][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestQualityThresholds::test_set_quality_thresholds
- [gw11][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_validate_report_redundancy
- [gw2][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_generate_fallback_considers_retry_count
- [gw13][36m [ 37%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestAdminRoute::test_admin_role_verification
- [gw1][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_supply_research_scheduler_comprehensive.py::TestSchedulerInitialization::test_default_schedule_configurations
- [gw2][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_generate_fallback_includes_diagnostic_tips
- [gw11][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_domain_specific_term_recognition
- [gw5][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestQualityThresholds::test_validate_against_thresholds
- [gw13][36m [ 37%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestAdminRoute::test_admin_user_management
- [gw2][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_generate_fallback_with_previous_responses
- [gw11][36m [ 38%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_caching_mechanism
- [gw5][36m [ 38%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestQualityThresholds::test_dynamic_threshold_adjustment
- [gw2][36m [ 38%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_format_response_with_placeholders
- [gw2][36m [ 38%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_get_recovery_suggestions
- [gw11][36m [ 38%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_retry_suggestions_for_failed_validation
- [gw5][36m [ 38%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestAlerting::test_trigger_alert_on_threshold_breach
- [gw2][36m [ 38%] [0m[31mFAILED[0m app\tests\services\test_fallback_response_service.py::TestFallbackResponseService::test_fallback_response_quality
- [gw11][36m [ 38%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_hallucination_risk_detection
- [gw1][36m [ 38%] [0m[31mFAILED[0m app\tests\services\test_supply_research_scheduler_comprehensive.py::TestScheduledResearchExecution::test_check_and_notify_changes_new_models
- [gw11][36m [ 38%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_triage_content_validation
- [gw9][36m [ 39%] [0m[31mFAILED[0m app\tests\clickhouse\test_performance_edge_cases.py::TestLargeDatasetPerformance::test_time_window_query_optimization
- [gw11][36m [ 39%] [0m[31mFAILED[0m app\tests\services\test_state_persistence.py::TestStatePersistence::test_save_agent_state
- [gw13][36m [ 39%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestAgentRoute::test_agent_message_processing
- [gw11][36m [ 39%] [0m[31mFAILED[0m app\tests\services\test_state_persistence.py::TestStatePersistence::test_restore_agent_state
- [gw9][36m [ 39%] [0m[31mFAILED[0m app\tests\clickhouse\test_performance_edge_cases.py::TestEdgeCaseHandling::test_null_values_in_nested_arrays
- [gw13][36m [ 39%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestAgentRoute::test_agent_streaming_response
- [gw11][36m [ 39%] [0m[31mFAILED[0m app\tests\services\test_state_persistence.py::TestStatePersistence::test_cleanup_old_states
- [gw1][36m [ 39%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerJobs::test_job_execution_resource_cleanup
- [gw9][36m [ 39%] [0m[31mFAILED[0m app\tests\clickhouse\test_performance_edge_cases.py::TestEdgeCaseHandling::test_zero_standard_deviation_handling
- [gw11][36m [ 39%] [0m[31mFAILED[0m app\tests\services\test_state_persistence.py::TestStatePersistence::test_state_versioning
- [gw11][36m [ 40%] [0m[31mFAILED[0m app\tests\services\test_state_persistence.py::TestStatePersistence::test_concurrent_state_updates
- [gw1][36m [ 40%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerJobs::test_job_execution_timeout_handling
- [gw5][36m [ 40%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestAlerting::test_alert_rate_limiting
- [gw1][36m [ 40%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerJobs::test_job_execution_error_logging
- [gw11][36m [ 40%] [0m[31mFAILED[0m app\tests\services\test_supply_catalog_service.py::TestSupplyCatalogService::test_get_all_options
- [gw11][36m [ 40%] [0m[31mFAILED[0m app\tests\services\test_supply_catalog_service.py::TestSupplyCatalogService::test_get_option_by_id
- [gw13][36m [ 40%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestAgentRoute::test_agent_error_handling
- [gw1][36m [ 40%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerJobs::test_job_execution_metrics_tracking
- [gw11][36m [ 40%] [0m[31mFAILED[0m app\tests\services\test_supply_catalog_service.py::TestSupplyCatalogService::test_get_option_by_name
- [gw1][36m [ 40%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerRetryLogic::test_exponential_backoff_retry_timing
- [gw1][36m [ 41%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerRetryLogic::test_retry_state_persistence
- [gw6][36m [ 41%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestCachingMechanisms::test_cache_hit_performance
- [gw5][36m [ 41%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestAlerting::test_alert_escalation
- [gw9][36m [ 41%] [0m[31mFAILED[0m app\tests\clickhouse\test_performance_edge_cases.py::TestConcurrencyAndAsync::test_concurrent_corpus_operations
- [gw4][36m [ 41%] [0m[31mFAILED[0m app\tests\services\test_redis_manager_operations.py::TestRedisManagerPerformance::test_metrics_collection_accuracy
- [gw1][36m [ 41%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerRetryLogic::test_retry_circuit_breaker
- [gw11][36m [ 41%] [0m[31mFAILED[0m app\tests\services\test_supply_research_scheduler_comprehensive.py::TestResearchSchedule::test_calculate_next_run_weekly
- [gw1][36m [ 41%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerRetryLogic::test_retry_jitter_randomization
- [gw5][36m [ 41%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestMetricsAggregation::test_aggregate_metrics_by_time_window
- [gw13][36m [ 41%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestConfigRoute::test_config_retrieval
- [gw1][36m [ 41%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerConcurrency::test_concurrent_job_limit_enforcement
- [gw11][36m [ 42%] [0m[31mFAILED[0m app\tests\services\test_supply_research_scheduler_comprehensive.py::TestResearchSchedule::test_calculate_next_run_monthly
- [gw13][36m [ 42%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestConfigRoute::test_config_update_validation
- [gw2][36m [ 42%] [0m[31mFAILED[0m app\tests\services\test_supply_research_service_comprehensive.py::TestPriceChangeCalculations::test_calculate_price_changes_zero_old_value
- [gw1][36m [ 42%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerConcurrency::test_job_queue_management
- [gw5][36m [ 42%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestMetricsAggregation::test_calculate_statistics
- [gw13][36m [ 42%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestConfigRoute::test_config_persistence
- [gw4][36m [ 42%] [0m[31mFAILED[0m app\tests\services\test_schema_validation_service.py::TestSchemaValidationService::test_validate_schema
- [gw1][36m [ 42%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerConcurrency::test_deadlock_prevention
- [gw5][36m [ 42%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestMetricsAggregation::test_trend_analysis
- [gw2][36m [ 42%] [0m[31mFAILED[0m app\tests\services\test_supply_research_service_comprehensive.py::TestPriceChangeCalculations::test_calculate_price_changes_invalid_json
- [gw1][36m [ 43%] [0m[31mFAILED[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerPerformance::test_memory_usage_under_load
- [gw4][36m [ 43%] [0m[31mFAILED[0m app\tests\services\test_security_service.py::test_encrypt_and_decrypt
- [gw1][36m [ 43%] [0m[31mFAILED[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerPerformance::test_job_execution_performance_metrics
- [gw5][36m [ 43%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestQualityReporting::test_generate_quality_report
- [gw5][36m [ 44%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestQualityReporting::test_export_metrics_to_json
- [gw1][36m [ 44%] [0m[31mFAILED[0m app\tests\services\test_supply_research_service_comprehensive.py::TestServiceInitialization::test_initialization_with_redis
- [gw5][36m [ 44%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestQualityReporting::test_generate_sla_compliance_report
- [gw13][36m [ 44%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestCorpusRoute::test_corpus_create
- [gw5][36m [ 45%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestAnomalyDetection::test_detect_anomalies_zscore
- [gw5][36m [ 45%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestAnomalyDetection::test_detect_anomalies_iqr
- [gw11][36m [ 45%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestLegacyFunctions::test_legacy_generate_synthetic_data_task
- [gw5][36m [ 45%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestAnomalyDetection::test_real_time_anomaly_detection
- [gw13][36m [ 45%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestCorpusRoute::test_corpus_search
- [gw5][36m [ 45%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestPerformanceMonitoring::test_monitor_response_times
- [gw13][36m [ 45%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestCorpusRoute::test_corpus_bulk_operations
- [gw1][36m [ 45%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestGenerationWorker::test_generate_worker_success
- [gw5][36m [ 45%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestPerformanceMonitoring::test_monitor_throughput
- [gw5][36m [ 45%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestIntegration::test_integration_with_agent_service
- [gw11][36m [ 46%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestErrorScenarios::test_generate_with_anomalies_method
- [gw7][36m [ 46%] [0m[31mFAILED[0m app\tests\routes\test_auth_flow.py::test_login_redirect_in_production
- [gw13][36m [ 46%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestLLMCacheRoute::test_cache_metrics
- [gw2][36m [ 46%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestCorpusManagement::test_corpus_creation_with_clickhouse_table
- [gw1][36m [ 46%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestGenerationWorker::test_generate_worker_failure
- [gw1][36m [ 46%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestJobManagement::test_cancel_job_exists
- [gw5][36m [ 46%] [0m[31mFAILED[0m app\tests\services\test_quality_monitoring_service.py::TestIntegration::test_integration_with_database
- [gw5][36m [ 46%] [0m[31mERROR[0m app\tests\services\test_quality_monitoring_service.py::TestQualityMonitoringServiceReal::test_record_quality_event_real
- [gw5][36m [ 46%] [0m[31mERROR[0m app\tests\services\test_quality_monitoring_service.py::TestQualityMonitoringServiceReal::test_get_dashboard_data_real
- [gw2][36m [ 46%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestCorpusManagement::test_corpus_status_transitions
- [gw1][36m [ 46%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestJobManagement::test_cancel_job_not_exists
- [gw13][36m [ 46%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestLLMCacheRoute::test_cache_invalidation
- [gw5][36m [ 46%] [0m[31mFAILED[0m app\tests\services\test_supply_research_service_comprehensive.py::TestProviderComparison::test_get_provider_comparison_with_data
- [gw2][36m [ 46%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestCorpusManagement::test_corpus_content_upload_batch
- [gw13][36m [ 46%] [0m[31mFAILED[0m app\tests\routes\test_api_routes_21_30.py::TestLLMCacheRoute::test_selective_cache_invalidation
- [gw5][36m [ 46%] [0m[31mFAILED[0m app\tests\services\test_supply_research_service_comprehensive.py::TestAnomalyDetection::test_detect_anomalies_significant_price_changes
- [gw1][36m [ 46%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestPreviewGeneration::test_get_preview_no_corpus
- [gw2][36m [ 47%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestCorpusManagement::test_corpus_validation
- [gw5][36m [ 47%] [0m[31mFAILED[0m app\tests\services\test_supply_research_service_comprehensive.py::TestAnomalyDetection::test_detect_anomalies_stale_data
- [gw2][36m [ 47%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestCorpusManagement::test_corpus_availability_check
- [gw4][36m [ 48%] [0m[31mFAILED[0m app\tests\services\test_security_service_authentication_enhanced.py::TestSecurityServiceAuthenticationEnhanced::test_access_token_expiration
- [gw13][36m [ 48%] [0m[31mFAILED[0m app\tests\services\test_supply_research_scheduler_comprehensive.py::TestErrorHandling::test_redis_failures_during_execution
- [gw1][36m [ 48%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestAdvancedGenerationMethods::test_generate_with_temporal_patterns
- [gw5][36m [ 48%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestAdminVisibility::test_job_cancellation_by_admin
- [gw13][36m [ 48%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerJobs::test_schedule_job_execution_success
- [gw13][36m [ 48%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerJobs::test_schedule_job_execution_with_retry
- [gw13][36m [ 48%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerJobs::test_schedule_job_execution_max_retries_exceeded
- [gw5][36m [ 48%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestAdminVisibility::test_resource_usage_tracking
- [gw13][36m [ 48%] [0m[31mERROR[0m app\tests\services\test_supply_research_scheduler_jobs.py::TestSupplyResearchSchedulerJobs::test_concurrent_job_execution
- [gw2][36m [ 48%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestCorpusManagement::test_corpus_fallback_to_default
- [gw5][36m [ 48%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestIntegration::test_complete_generation_workflow
- [gw1][36m [ 48%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestAdvancedGenerationMethods::test_generate_with_errors
- [gw5][36m [ 48%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestIntegration::test_multi_tenant_generation
- [gw2][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestCorpusManagement::test_corpus_caching_mechanism
- [gw5][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestIntegration::test_real_time_streaming_pipeline
- [gw1][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestAdvancedGenerationMethods::test_generate_domain_specific
- [gw5][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestIntegration::test_failure_recovery_integration
- [gw2][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestCorpusManagement::test_corpus_deletion_cascade
- [gw5][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestIntegration::test_cross_component_validation
- [gw2][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestCorpusManagement::test_corpus_metadata_tracking
- [gw2][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestCorpusManagement::test_corpus_concurrent_access
- [gw1][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestAdvancedGenerationMethods::test_generate_with_distribution
- [gw5][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestIntegration::test_performance_under_load
- [gw2][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestDataGenerationEngine::test_workload_distribution_generation
- [gw5][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestIntegration::test_data_consistency_verification
- [gw1][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestAdvancedGenerationMethods::test_generate_with_custom_tools
- [gw5][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestIntegration::test_monitoring_integration
- [gw5][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestIntegration::test_security_and_access_control
- [gw2][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestDataGenerationEngine::test_temporal_pattern_generation
- [gw5][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestIntegration::test_cleanup_and_retention
- [gw2][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestDataGenerationEngine::test_tool_invocation_patterns
- [gw1][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestAdvancedGenerationMethods::test_generate_incremental
- [gw2][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestWebSocketUpdates::test_websocket_message_queuing
- [gw5][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestAdvancedFeatures::test_anomaly_injection_strategies
- [gw2][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestWebSocketUpdates::test_websocket_heartbeat
- [gw1][36m [ 49%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_comprehensive.py::TestAdvancedGenerationMethods::test_generate_from_corpus
- [gw2][36m [ 50%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestWebSocketUpdates::test_generation_completion_notification
- [gw2][36m [ 50%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestWebSocketUpdates::test_websocket_rate_limiting
- [gw5][36m [ 50%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestAdvancedFeatures::test_cross_correlation_generation
- [gw2][36m [ 50%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestDataQualityValidation::test_statistical_distribution_validation
- [gw2][36m [ 50%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestDataQualityValidation::test_temporal_consistency_validation
- [gw11][36m [ 50%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestDataGenerationEngine::test_generation_with_corpus_sampling
- [gw2][36m [ 50%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestDataQualityValidation::test_data_completeness_validation
- [gw11][36m [ 51%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestRealTimeIngestion::test_batch_ingestion_to_clickhouse
- [gw13][36m [ 51%] [0m[31mFAILED[0m app\tests\services\test_tool_permission_service_comprehensive.py::TestBusinessRequirements::test_check_business_requirements_feature_flags_pass
- [gw2][36m [ 51%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestDataQualityValidation::test_anomaly_detection_in_generated_data
- [gw5][36m [ 51%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestAdvancedFeatures::test_adaptive_generation_feedback
- [gw13][36m [ 51%] [0m[31mFAILED[0m app\tests\services\test_tool_permission_service_comprehensive.py::TestBusinessRequirements::test_check_business_requirements_feature_flags_fail
- [gw2][36m [ 51%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestDataQualityValidation::test_correlation_preservation
- [gw13][36m [ 51%] [0m[31mFAILED[0m app\tests\services\test_tool_permission_service_comprehensive.py::TestBusinessRequirements::test_check_business_requirements_all_conditions
- [gw2][36m [ 52%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestDataQualityValidation::test_quality_metrics_calculation
- [gw2][36m [ 52%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestDataQualityValidation::test_data_diversity_validation
- [gw13][36m [ 52%] [0m[31mFAILED[0m app\tests\services\test_tool_permission_service_comprehensive.py::TestUpgradePath::test_get_upgrade_path_already_highest_tier
- [gw2][36m [ 53%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestDataQualityValidation::test_validation_report_generation
- [gw5][36m [ 53%] [0m[31mFAILED[0m app\tests\services\test_thread_service.py::TestThreadService::TestCreateRun::test_create_run_success_minimal
- [gw13][36m [ 53%] [0m[31mFAILED[0m app\tests\services\test_tool_permission_service_comprehensive.py::TestIntegrationScenarios::test_pro_user_with_heavy_usage
- [gw5][36m [ 53%] [0m[31mFAILED[0m app\tests\services\test_thread_service.py::TestThreadService::TestCreateRun::test_create_run_success_full_params
- [gw13][36m [ 53%] [0m[31mFAILED[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryRegistration::test_register_single_tool
- [gw5][36m [ 53%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryDiscovery::test_discover_tools_by_category
- [gw5][36m [ 53%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryDiscovery::test_discover_tools_by_name_pattern
- [gw5][36m [ 53%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryDiscovery::test_discover_tools_by_tags
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryDiscovery::test_discover_tools_by_capability
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryDiscovery::test_discover_compatible_tools
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryDiscovery::test_discover_tools_fuzzy_search
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryDiscovery::test_discover_recently_used_tools
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryDiscovery::test_tool_recommendation_engine
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryValidation::test_tool_interface_validation
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryValidation::test_tool_metadata_validation
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryValidation::test_tool_security_validation
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryValidation::test_tool_performance_validation
- [gw13][36m [ 54%] [0m[31mFAILED[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryRegistration::test_register_multiple_tools_same_category
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryValidation::test_tool_compatibility_validation
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryValidation::test_tool_dependency_validation
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryValidation::test_tool_version_compatibility_validation
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryPerformance::test_large_scale_tool_registration
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryPerformance::test_tool_discovery_performance
- [gw2][36m [ 54%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestPerformanceScalability::test_high_throughput_generation
- [gw5][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryPerformance::test_concurrent_tool_access
- [gw13][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryRegistration::test_register_tools_multiple_categories
- [gw13][36m [ 54%] [0m[31mFAILED[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryRegistration::test_register_tool_with_metadata
- [gw13][36m [ 54%] [0m[31mFAILED[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryRegistration::test_register_duplicate_tool_handling
- [gw13][36m [ 54%] [0m[31mFAILED[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryRegistration::test_register_tool_validation_failure
- [gw13][36m [ 54%] [0m[31mFAILED[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryRegistration::test_register_tool_invalid_category
- [gw13][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryRegistration::test_bulk_tool_registration
- [gw13][36m [ 54%] [0m[31mFAILED[0m app\tests\services\test_tool_registry_registration.py::TestToolRegistryRegistration::test_tool_registration_rollback_on_error
- [gw13][36m [ 54%] [0m[31mERROR[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryManagement::test_cross_registry_tool_discovery
- [gw13][36m [ 55%] [0m[31mERROR[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryManagement::test_tool_orchestration_simple_chain
- [gw13][36m [ 55%] [0m[31mERROR[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryManagement::test_tool_orchestration_complex_chain
- [gw13][36m [ 55%] [0m[31mERROR[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryManagement::test_parallel_tool_orchestration
- [gw13][36m [ 55%] [0m[31mERROR[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryManagement::test_tool_lifecycle_management_state_transitions
- [gw6][36m [ 55%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestErrorHandlingAndRecovery::test_llm_timeout_handling
- [gw12][36m [ 55%] [0m[31mFAILED[0m app\tests\e2e\test_concurrent_user_load.py::TestConcurrentUserLoad::test_50_concurrent_users
- [gw0][36m [ 55%] [0m[31mFAILED[0m app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_1_complete_agent_lifecycle_request_to_completion
- [gw13][36m [ 55%] [0m[31mERROR[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryManagement::test_tool_lifecycle_history_tracking
- [gw13][36m [ 55%] [0m[31mERROR[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryManagement::test_tool_health_monitoring_individual
- [gw13][36m [ 55%] [0m[31mERROR[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryManagement::test_tool_health_monitoring_overall
- [gw13][36m [ 55%] [0m[31mERROR[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryManagement::test_tool_metrics_collection_individual
- [gw13][36m [ 55%] [0m[31mERROR[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryManagement::test_tool_metrics_aggregation
- [gw13][36m [ 55%] [0m[31mFAILED[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryOrchestration::test_conditional_tool_execution
- [gw4][36m [ 55%] [0m[31mFAILED[0m app\tests\services\test_security_service_authentication_enhanced.py::TestSecurityServiceOAuth::test_create_user_from_oauth_new_user
- [gw13][36m [ 56%] [0m[31mFAILED[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryOrchestration::test_tool_chain_error_handling
- [gw13][36m [ 56%] [0m[31mFAILED[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryOrchestration::test_tool_chain_timeout_handling
- [gw3][36m [ 56%] [0m[31mFAILED[0m app\tests\agents\test_subagent_workflow.py::test_subagent_workflow_end_to_end
- [gw4][36m [ 56%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerConnectionPooling::test_connection_cleanup_on_disconnect
- [gw13][36m [ 57%] [0m[31mFAILED[0m app\tests\services\test_unified_tool_registry_management.py::TestUnifiedToolRegistryOrchestration::test_concurrent_chain_execution
- [gw4][36m [ 57%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerConnectionPooling::test_heartbeat_mechanism
- [gw11][36m [ 57%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestRealTimeIngestion::test_ingestion_error_recovery
- [gw4][36m [ 57%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerConnectionPooling::test_concurrent_connection_management
- [gw4][36m [ 57%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerConnectionPooling::test_message_broadcasting_to_multiple_connections
- [gw11][36m [ 57%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestRealTimeIngestion::test_ingestion_deduplication
- [gw4][36m [ 57%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerConnectionPooling::test_connection_statistics_tracking
- [gw11][36m [ 57%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestRealTimeIngestion::test_table_creation_on_demand
- [gw11][36m [ 57%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestRealTimeIngestion::test_parallel_batch_ingestion
- [gw4][36m [ 57%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerPerformanceAndScaling::test_high_volume_connection_handling
- [gw11][36m [ 57%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestRealTimeIngestion::test_ingestion_with_transformation
- [gw11][36m [ 58%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestRealTimeIngestion::test_ingestion_circuit_breaker
- [gw11][36m [ 58%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestRealTimeIngestion::test_ingestion_progress_tracking
- [gw11][36m [ 58%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestWebSocketUpdates::test_websocket_connection_management
- [gw11][36m [ 58%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestWebSocketUpdates::test_generation_progress_broadcast
- [gw11][36m [ 58%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestWebSocketUpdates::test_batch_completion_notifications
- [gw11][36m [ 58%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestWebSocketUpdates::test_error_notification_handling
- [gw5][36m [ 58%] [0m[31mFAILED[0m app\tests\services\test_websocket_message_handler_routing.py::TestMessageQueueIntegration::test_message_queueing_for_routing
- [gw11][36m [ 58%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestWebSocketUpdates::test_websocket_reconnection_handling
- [gw5][36m [ 58%] [0m[31mFAILED[0m app\tests\services\test_websocket_message_handler_routing.py::TestMessageQueueIntegration::test_priority_queue_processing
- [gw5][36m [ 58%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerConnectionPooling::test_multiple_connections_same_user
- [gw11][36m [ 58%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestWebSocketUpdates::test_multiple_client_subscriptions
- [gw5][36m [ 59%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerConnectionPooling::test_connection_limit_enforcement
- [gw11][36m [ 59%] [0m[31mFAILED[0m app\tests\test_agents_comprehensive.py::TestDataSubAgent::test_data_agent_analysis
- [gw9][36m [ 59%] [0m[31mFAILED[0m app\tests\clickhouse\test_performance_edge_cases.py::TestConcurrencyAndAsync::test_async_table_creation_timeout
- [gw11][36m [ 59%] [0m[31mFAILED[0m app\tests\test_agents_comprehensive.py::TestAgentLifecycle::test_agent_execution_timing
- [gw11][36m [ 60%] [0m[31mFAILED[0m app\tests\test_database_session.py::TestClickHouseConnection::test_clickhouse_error_handling
- [gw9][36m [ 61%] [0m[31mFAILED[0m app\tests\clickhouse\test_performance_edge_cases.py::TestMetricsCalculation::test_statistics_with_empty_data
- [gw9][36m [ 61%] [0m[31mFAILED[0m app\tests\clickhouse\test_performance_edge_cases.py::TestMetricsCalculation::test_statistics_with_single_value
- [gw4][36m [ 61%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerPerformanceAndScaling::test_memory_usage_under_load
- [gw4][36m [ 61%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerPerformanceAndScaling::test_connection_recovery_after_failure
- [gw9][36m [ 61%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_exception_handling
- [gw4][36m [ 61%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerPerformanceAndScaling::test_heartbeat_performance_under_load
- [gw9][36m [ 61%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_async_execution
- [gw4][36m [ 61%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerPerformanceAndScaling::test_broadcast_performance
- [gw9][36m [ 61%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_large_dataset
- [gw4][36m [ 62%] [0m[31mFAILED[0m app\tests\services\test_ws_manager_connection_pool.py::TestWebSocketManagerPerformanceAndScaling::test_connection_statistics_accuracy
- [gw9][36m [ 62%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_varied_latencies
- [gw9][36m [ 62%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_partial_failure
- [gw1][36m [ 62%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestPerformanceScalability::test_query_optimization
- [gw11][36m [ 62%] [0m[31mFAILED[0m app\tests\test_external_imports.py::TestExternalImports::test_external_import[langchain_community.embeddings-langchain_community.embeddings]
- [gw11][36m [ 62%] [0m[31mFAILED[0m app\tests\test_external_imports.py::TestExternalImports::test_external_import[langchain_community.vectorstores-langchain_community.vectorstores]
- [gw9][36m [ 62%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_edge_case_rounding
- [gw13][36m [ 62%] [0m[31mFAILED[0m app\tests\test_admin.py::test_set_log_table_not_available
- [gw1][36m [ 63%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestErrorRecovery::test_corpus_unavailable_fallback
- [gw9][36m [ 63%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_negative_latencies
- [gw1][36m [ 63%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestErrorRecovery::test_clickhouse_connection_recovery
- [gw9][36m [ 63%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_mixed_response_formats
- [gw6][36m [ 63%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestErrorHandlingAndRecovery::test_llm_rate_limit_handling
- [gw1][36m [ 63%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestErrorRecovery::test_generation_checkpoint_recovery
- [gw6][36m [ 63%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestErrorHandlingAndRecovery::test_partial_llm_response_handling
- [gw9][36m [ 63%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_extreme_values
- [gw1][36m [ 63%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestErrorRecovery::test_circuit_breaker_operation
- [gw9][36m [ 64%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_latency_analyzer.py::TestLatencyAnalyzer::test_latency_analyzer_concurrent_execution_timing
- [gw1][36m [ 64%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestErrorRecovery::test_graceful_degradation
- [gw1][36m [ 65%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestAdminVisibility::test_generation_job_monitoring
- [gw9][36m [ 65%] [0m[31mFAILED[0m app\tests\services\test_agent_message_processing.py::TestAgentMessageProcessing::test_process_user_message
- [gw9][36m [ 65%] [0m[31mFAILED[0m app\tests\services\test_agent_message_processing.py::TestAgentMessageProcessing::test_handle_tool_execution
- [gw9][36m [ 65%] [0m[31mFAILED[0m app\tests\services\test_agent_message_processing.py::TestAgentMessageProcessing::test_message_validation
- [gw1][36m [ 65%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestAdminVisibility::test_alert_configuration
- [gw9][36m [ 66%] [0m[31mFAILED[0m app\tests\services\test_agent_service.py::test_run_agent
- [gw9][36m [ 67%] [0m[31mFAILED[0m app\tests\services\test_agent_service_advanced.py::test_agent_service_initialization
- [gw9][36m [ 68%] [0m[31mFAILED[0m app\tests\services\test_agent_service_advanced.py::test_agent_service_process_request
- [gw9][36m [ 69%] [0m[31mFAILED[0m app\tests\services\test_agent_service_advanced.py::test_agent_service_websocket_message_handling
- [gw6][36m [ 69%] [0m[31mFAILED[0m app\tests\test_json_extraction.py::TestTruncatedJSONRecovery::test_recover_missing_closing_brace
- [gw6][36m [ 69%] [0m[31mFAILED[0m app\tests\test_json_extraction.py::TestTruncatedJSONRecovery::test_recover_with_trailing_comma
- [gw3][36m [ 69%] [0m[31mFAILED[0m app\tests\mcp\test_server.py::TestMCPServer::test_rate_limiting
- [gw9][36m [ 70%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_agent_service_initialization
- [gw3][36m [ 70%] [0m[31mFAILED[0m app\tests\mcp\test_tool_registry.py::TestToolRegistry::test_register_tool_overwrite
- [gw6][36m [ 71%] [0m[31mFAILED[0m app\tests\test_realistic_data_integration.py::TestRealisticDataIntegration::test_synthetic_agent_with_realistic_data
- [gw9][36m [ 71%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_agent_run_execution
- [gw6][36m [ 72%] [0m[31mFAILED[0m app\tests\test_realistic_data_integration.py::TestRealisticDataIntegration::test_corpus_agent_with_realistic_data
- [gw1][36m [ 72%] [0m[31mFAILED[0m app\tests\test_internal_imports.py::TestInternalImports::test_circular_imports
- [gw3][36m [ 72%] [0m[31mFAILED[0m app\tests\test_startup_checks_robust.py::TestStartupChecker::test_check_configuration_invalid_secret
- [gw9][36m [ 72%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_agent_run_with_model_dump_fallback
- [gw3][36m [ 73%] [0m[31mFAILED[0m app\tests\test_startup_checks_robust.py::TestStartupChecker::test_check_clickhouse_success
- [gw9][36m [ 73%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_websocket_message_handling_start_agent
- [gw9][36m [ 74%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_websocket_message_handling_user_message
- [gw9][36m [ 75%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_websocket_message_handling_thread_operations
- [gw3][36m [ 75%] [0m[31mFAILED[0m app\tests\test_websocket_production_realistic.py::test_protocol_version_mismatch
- [gw9][36m [ 75%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_websocket_message_handling_stop_agent
- [gw9][36m [ 75%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_websocket_message_handling_unknown_type
- [gw9][36m [ 75%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_websocket_message_handling_json_error
- [gw4][36m [ 75%] [0m[31mFAILED[0m app\tests\test_admin.py::test_get_app_settings_as_superuser
- [gw9][36m [ 75%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_websocket_disconnect_handling
- [gw9][36m [ 75%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_concurrent_agent_execution
- [gw9][36m [ 75%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_message_parsing_string_input
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_heartbeat_loop_cancelled
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_heartbeat_loop_error
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_heartbeat_loop_connection_fails_check
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_handle_pong
- [gw6][36m [ 76%] [0m[31mFAILED[0m app\tests\test_websocket_production_realistic.py::test_concurrent_connection_limit_1000_users
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_handle_pong_no_connection
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_send_error
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_send_agent_log
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_send_tool_call
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_send_tool_result
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_broadcast_success
- [gw1][36m [ 76%] [0m[31mFAILED[0m app\tests\test_internal_imports.py::TestInternalImports::test_all_route_modules
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_broadcast_with_failures
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_broadcast_unexpected_error
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_broadcast_adds_timestamp
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_shutdown
- [gw9][36m [ 76%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_shutdown_with_close_errors
- [gw1][36m [ 76%] [0m[31mFAILED[0m app\tests\test_json_extraction.py::TestJSONExtraction::test_extract_json_with_single_quotes
- [gw1][36m [ 76%] [0m[31mFAILED[0m app\tests\test_json_extraction.py::TestTruncatedJSONRecovery::test_recover_deeply_truncated
- [gw1][36m [ 77%] [0m[31mFAILED[0m app\tests\test_json_extraction.py::TestPartialJSONExtraction::test_extract_partial_missing_required_fields
- [gw9][36m [ 77%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_get_stats
- [gw9][36m [ 77%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_get_connection_info
- [gw9][36m [ 77%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_get_connection_info_no_user
- [gw9][36m [ 77%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_connection_info_dataclass
- [gw9][36m [ 77%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_remove_dead_connections_during_send
- [gw0][36m [ 77%] [0m[31mFAILED[0m app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_2_websocket_real_time_streaming
- [gw9][36m [ 77%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_send_message_removes_dead_connections
- [gw1][36m [ 78%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestMessageSending::test_send_message_removes_dead_connections
- [gw9][36m [ 78%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_send_to_connection_exhausts_retries
- [gw9][36m [ 78%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_send_to_connection_no_retry_false
- [gw9][36m [ 78%] [0m[31mFAILED[0m app\tests\test_ws_manager.py::TestWebSocketManager::test_threading_lock
- [gw9][36m [ 78%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestConnectionManagement::test_connect_new_user
- [gw9][36m [ 78%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestConnectionManagement::test_connect_multiple_users
- [gw9][36m [ 78%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestHeartbeat::test_handle_pong
- [gw9][36m [ 79%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestHeartbeat::test_handle_pong_no_connection
- [gw9][36m [ 79%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestHeartbeat::test_heartbeat_loop_normal_operation
- [gw11][36m [ 79%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestStatistics::test_get_connection_info_multiple_connections
- [gw11][36m [ 79%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestEdgeCases::test_connect_with_same_websocket_different_users
- [gw9][36m [ 79%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestHeartbeat::test_heartbeat_loop_connection_state_changes
- [gw9][36m [ 79%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestHeartbeat::test_heartbeat_loop_cancelled
- [gw11][36m [ 79%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestEdgeCases::test_connection_id_uniqueness
- [gw11][36m [ 79%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestEdgeCases::test_websocket_state_transitions
- [gw9][36m [ 79%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestHeartbeat::test_heartbeat_loop_error
- [gw9][36m [ 80%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestHeartbeat::test_heartbeat_loop_connection_fails_alive_check
- [gw9][36m [ 80%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestSpecializedMessages::test_send_error
- [gw11][36m [ 80%] [0m[31mFAILED[0m app\tests\unit\test_threads_route.py::TestCreateThread::test_create_thread_success
- [gw9][36m [ 80%] [0m[31mFAILED[0m app\tests\test_ws_manager_comprehensive.py::TestSpecializedMessages::test_send_error_default_agent
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\unit\test_threads_route.py::TestAutoRenameThread::test_auto_rename_empty_metadata
- [gw9][36m [ 81%] [0m[31mFAILED[0m app\tests\unit\test_threads_route.py::TestCreateThread::test_create_thread_exception
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestDatetimeUtilsTimezone::test_timezone_conversions
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestDatetimeUtilsTimezone::test_dst_handling
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestStringUtilsSanitization::test_xss_prevention
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestStringUtilsSanitization::test_input_validation
- [gw9][36m [ 81%] [0m[31mFAILED[0m app\tests\unit\test_threads_route.py::TestGetThread::test_get_thread_success
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestJsonUtilsSerialization::test_custom_serialization
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestJsonUtilsSerialization::test_circular_reference_handling
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestFileUtilsOperations::test_file_operations
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestFileUtilsOperations::test_cleanup_on_error
- [gw9][36m [ 81%] [0m[31mFAILED[0m app\tests\unit\test_threads_route.py::TestGetThread::test_get_thread_not_found
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestCryptoUtilsHashing::test_hashing_algorithms
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestCryptoUtilsHashing::test_salt_generation
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestValidationUtilsSchemas::test_schema_validation
- [gw9][36m [ 81%] [0m[31mFAILED[0m app\tests\unit\test_threads_route.py::TestGetThread::test_get_thread_access_denied
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestValidationUtilsSchemas::test_error_messages
- [gw5][36m [ 81%] [0m[31mFAILED[0m app\tests\test_business_value_critical.py::TestBusinessValueCritical::test_1_cost_optimization_request
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestFormattingUtilsDisplay::test_data_formatting
- [gw11][36m [ 81%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestFormattingUtilsDisplay::test_localization
- [gw9][36m [ 82%] [0m[31mFAILED[0m app\tests\unit\test_threads_route.py::TestGetThread::test_get_thread_general_exception
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestMathUtilsCalculations::test_mathematical_operations
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestMathUtilsCalculations::test_precision_handling
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestNetworkUtilsRequests::test_network_utilities
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestNetworkUtilsRequests::test_retry_logic
- [gw9][36m [ 82%] [0m[31mFAILED[0m app\tests\unit\test_threads_route.py::TestUpdateThread::test_update_thread_success
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestPaginationUtilsCursors::test_cursor_pagination
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestPaginationUtilsCursors::test_edge_cases
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestRateLimiterThrottling::test_rate_limiting
- [gw9][36m [ 82%] [0m[31mFAILED[0m app\tests\unit\test_threads_route.py::TestUpdateThread::test_update_thread_empty_metadata
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestRateLimiterThrottling::test_bucket_algorithms
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestRetryUtilsBackoff::test_exponential_backoff
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestRetryUtilsBackoff::test_retry_strategies
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestMonitoringUtilsMetrics::test_metric_collection
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestMonitoringUtilsMetrics::test_metric_aggregation
- [gw9][36m [ 82%] [0m[31mFAILED[0m app\tests\unit\test_threads_route.py::TestUpdateThread::test_update_thread_not_found
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestDebugUtilsProfiling::test_profiling_utilities
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestDebugUtilsProfiling::test_performance_metrics
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestMigrationUtilsScripts::test_migration_utilities
- [gw11][36m [ 82%] [0m[31mFAILED[0m app\tests\utils\test_utils_comprehensive.py::TestMigrationUtilsScripts::test_data_transformation
- [gw9][36m [ 82%] [0m[31mFAILED[0m app\tests\unit\test_threads_route.py::TestUpdateThread::test_update_thread_access_denied
- [gw9][36m [ 83%] [0m[31mFAILED[0m app\tests\unit\test_threads_route.py::TestUpdateThread::test_update_thread_exception
- [gw9][36m [ 84%] [0m[31mFAILED[0m app\test_basic.py::test_async_function
- [gw9][36m [ 84%] [0m[31mFAILED[0m app\test_startup_checks.py::TestRunStartupChecks::test_run_startup_checks_success
- [gw9][36m [ 84%] [0m[31mFAILED[0m app\test_startup_checks.py::TestRunStartupChecks::test_run_startup_checks_critical_failure
- [gw9][36m [ 84%] [0m[31mFAILED[0m app\test_startup_checks.py::TestRunStartupChecks::test_run_startup_checks_non_critical_failure
- [gw3][36m [ 84%] [0m[31mFAILED[0m app\tests\test_websocket_production_realistic.py::test_memory_leak_detection_long_connections
- [gw3][36m [ 84%] [0m[31mFAILED[0m app\tests\test_websocket_production_realistic.py::test_rapid_connect_disconnect_cycles
- [gw9][36m [ 84%] [0m[31mFAILED[0m app\test_startup_checks.py::TestLoggingAndReporting::test_run_startup_checks_logs_results
- [gw9][36m [ 85%] [0m[31mFAILED[0m app\test_super_e2e.py::TestSystemE2E::test_04_websocket_connection
- [gw1][36m [ 85%] [0m[31mFAILED[0m app\test_super_e2e.py::TestSystemE2E::test_10_performance_metrics
- [gw14][36m [ 85%] [0m[31mFAILED[0m app\test_system_startup.py::TestSystemStartup::test_database_migration_on_startup
- [gw3][36m [ 85%] [0m[31mFAILED[0m app\test_system_startup.py::TestSystemStartup::test_authentication_system_startup
- [gw14][36m [ 85%] [0m[31mFAILED[0m app\test_system_startup.py::TestSystemStartup::test_redis_connection_startup
- [gw14][36m [ 85%] [0m[31mFAILED[0m app\test_system_startup.py::TestSystemStartup::test_service_container_initialization
- [gw14][36m [ 86%] [0m[31mFAILED[0m app\test_system_startup.py::TestSystemStartup::test_agent_system_initialization
- [gw14][36m [ 86%] [0m[31mFAILED[0m app\test_system_startup.py::TestSystemStartup::test_websocket_manager_initialization
- [gw14][36m [ 86%] [0m[31mFAILED[0m app\test_system_startup.py::TestSystemStartup::test_graceful_shutdown
- [gw14][36m [ 86%] [0m[31mERROR[0m app\test_system_startup.py::TestFirstTimeRun::test_default_admin_creation
- [gw14][36m [ 86%] [0m[31mERROR[0m app\test_system_startup.py::TestFirstTimeRun::test_oauth_provider_setup
- [gw14][36m [ 86%] [0m[31mERROR[0m app\test_system_startup.py::TestStartupSequence::test_startup_order
- [gw14][36m [ 86%] [0m[31mERROR[0m app\test_system_startup.py::TestStartupSequence::test_startup_with_retry
- [gw14][36m [ 86%] [0m[31mERROR[0m app\test_system_startup.py::TestStartupSequence::test_startup_timeout
- [gw14][36m [ 86%] [0m[31mERROR[0m app\test_system_startup.py::TestStartupSequence::test_partial_startup_recovery
- [gw14][36m [ 86%] [0m[31mFAILED[0m app\test_system_startup.py::TestErrorHandlingFix::test_supervisor_error_string_formatting
- [gw0][36m [ 86%] [0m[31mFAILED[0m app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_3_supervisor_orchestration_logic
- [gw9][36m [ 86%] [0m[31mFAILED[0m app\test_super_e2e.py::TestSystemE2E::test_05_navigate_to_demo
- [gw1][36m [ 86%] [0m[31mFAILED[0m app\test_super_e2e.py::TestSystemE2E::test_12_concurrent_users
- [gw3][36m [ 86%] [0m[31mFAILED[0m app\test_system_startup.py::TestSystemStartup::test_health_check_endpoint
- [gw14][36m [ 86%] [0m[31mFAILED[0m app\test_app.py::test_read_main
- [gw5][36m [ 86%] [0m[31mFAILED[0m app\tests\test_business_value_critical.py::TestBusinessValueCritical::test_2_performance_bottleneck_identification
- [gw9][36m [ 86%] [0m[31mFAILED[0m app\test_super_e2e.py::TestSystemE2E::test_07_get_agent_report
- [gw1][36m [ 86%] [0m[31mFAILED[0m app\test_super_e2e.py::TestSystemE2E::test_13_graceful_shutdown
- [gw1][36m [ 86%] [0m[31mFAILED[0m app\test_system_startup.py::TestSystemStartup::test_environment_validation
- [gw1][36m [ 86%] [0m[31mFAILED[0m app\test_system_startup.py::TestSystemStartup::test_configuration_loading
- [gw1][36m [ 86%] [0m[31mERROR[0m app\test_system_startup.py::TestSystemStartup::test_database_connection_startup
- [gw1][36m [ 86%] [0m[31mFAILED[0m app\tests\routes\test_config_endpoint.py::TestConfigEndpoint::test_get_public_config
- [gw1][36m [ 86%] [0m[31mFAILED[0m app\tests\routes\test_config_endpoint.py::TestConfigEndpoint::test_get_frontend_config
- [gw1][36m [ 87%] [0m[31mFAILED[0m app\tests\routes\test_config_endpoint.py::TestConfigEndpoint::test_update_config_authorized
- [gw1][36m [ 87%] [0m[31mFAILED[0m app\tests\routes\test_config_endpoint.py::TestConfigEndpoint::test_update_config_unauthorized
- [gw2][36m [ 87%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestPerformanceScalability::test_horizontal_scaling
- [gw1][36m [ 87%] [0m[31mFAILED[0m app\tests\routes\test_google_auth.py::test_google_auth
- [gw1][36m [ 87%] [0m[31mERROR[0m app\tests\services\test_clickhouse_service.py::TestClickHouseConnection::test_basic_query_execution
- [gw1][36m [ 87%] [0m[31mERROR[0m app\tests\services\test_clickhouse_service.py::TestClickHouseConnection::test_query_with_parameters
- [gw1][36m [ 87%] [0m[31mERROR[0m app\tests\services\test_clickhouse_service.py::TestBasicOperations::test_show_tables
- [gw1][36m [ 87%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusDocumentIndexing::test_index_single_document
- [gw1][36m [ 87%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusDocumentIndexing::test_batch_indexing_pipeline
- [gw1][36m [ 87%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusDocumentIndexing::test_reindex_corpus_with_new_model
- [gw1][36m [ 87%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusDocumentIndexing::test_incremental_indexing
- [gw1][36m [ 87%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusDocumentIndexing::test_document_deduplication
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusSearchRelevance::test_semantic_search
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusSearchRelevance::test_hybrid_search
- [gw9][36m [ 88%] [0m[31mFAILED[0m app\test_super_e2e.py::TestSystemE2E::test_08_view_thread_history
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusSearchRelevance::test_search_with_filters
- [gw9][36m [ 88%] [0m[31mFAILED[0m app\test_supervisor.py::test_supervisor_flow
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusSearchRelevance::test_relevance_feedback
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusSearchRelevance::test_search_result_reranking
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusManagement::test_create_corpus_with_validation
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusManagement::test_update_corpus_metadata
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusManagement::test_delete_corpus_cascade
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestCorpusManagement::test_corpus_statistics
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestDocumentProcessing::test_extract_document_metadata
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestDocumentProcessing::test_document_chunking
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestDocumentProcessing::test_document_enrichment
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestIndexOptimization::test_index_compaction
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestIndexOptimization::test_index_cache_warming
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestIndexOptimization::test_index_performance_monitoring
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestErrorHandling::test_handle_indexing_failure
- [gw16][36m [ 88%] [0m[31mFAILED[0m app\test_health.py::test_ready_endpoint_success
- [gw16][36m [ 88%] [0m[31mFAILED[0m app\test_health.py::test_ready_endpoint_db_failure
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestErrorHandling::test_recover_from_partial_batch_failure
- [gw16][36m [ 88%] [0m[31mFAILED[0m app\test_health.py::test_ready_endpoint_clickhouse_failure
- [gw1][36m [ 88%] [0m[31mERROR[0m app\tests\services\test_corpus_service_comprehensive.py::TestErrorHandling::test_search_fallback_on_vector_store_failure
- [gw0][36m [ 88%] [0m[31mFAILED[0m app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_5_state_persistence_and_recovery
- [gw9][36m [ 88%] [0m[31mFAILED[0m app\test_websocket.py::test_websocket_sends_message_to_agent_service
- [gw15][36m [ 89%] [0m[31mFAILED[0m app\test_generation_service.py::test_synthetic_data_generation_with_table_selection
- [gw2][36m [ 89%] [0m[31mFAILED[0m app\tests\services\test_synthetic_data_service_v3.py::TestPerformanceScalability::test_batch_size_optimization
- [gw2][36m [ 89%] [0m[31mFAILED[0m app\tests\services\test_tool_permission_service_comprehensive.py::TestGetUserPermissions::test_get_user_permissions_wildcard
- [gw16][36m [ 90%] [0m[31mFAILED[0m app\tests\test_admin.py::test_add_log_table_success
- [gw1][36m [ 90%] [0m[31mFAILED[0m app\tests\test_admin.py::test_remove_log_table_success
- [gw5][36m [ 90%] [0m[31mFAILED[0m app\tests\test_business_value_critical.py::TestBusinessValueCritical::test_3_model_comparison_and_selection
- [gw6][36m [ 90%] [0m[31mFAILED[0m app\tests\test_admin.py::test_remove_default_log_table
- [gw11][36m [ 90%] [0m[31mFAILED[0m app\test_super_e2e.py::TestSystemE2E::test_01_system_startup
- [gw2][36m [ 90%] [0m[31mFAILED[0m app\tests\test_admin.py::test_set_time_period_not_available
- [gw12][36m [ 90%] [0m[31mFAILED[0m app\tests\e2e\test_concurrent_user_load.py::TestConcurrentUserLoad::test_resource_pool_exhaustion_handling
- [gw11][36m [ 90%] [0m[31mFAILED[0m app\test_super_e2e.py::TestSystemE2E::test_02_user_registration
- [gw12][36m [ 90%] [0m[31mFAILED[0m app\tests\e2e\test_concurrent_user_load.py::TestConcurrentUserLoad::test_fair_queuing_mechanism
- [gw11][36m [ 90%] [0m[31mFAILED[0m app\test_super_e2e.py::TestSystemE2E::test_03_user_login
- [gw5][36m [ 90%] [0m[31mFAILED[0m app\tests\test_business_value_critical.py::TestBusinessValueCritical::test_4_real_time_streaming_updates
- [gw12][36m [ 90%] [0m[31mFAILED[0m app\tests\e2e\test_concurrent_user_load.py::TestConcurrentUserLoad::test_websocket_connection_limits
- [gw17][36m [ 91%] [0m[31mFAILED[0m app\tests\test_admin.py::test_set_default_log_table_for_context_table_not_available
- [gw11][36m [ 91%] [0m[31mFAILED[0m app\tests\test_agents_comprehensive.py::TestSupervisorAgent::test_supervisor_run_workflow
- [gw5][36m [ 91%] [0m[31mFAILED[0m app\tests\test_business_value_critical.py::TestBusinessValueCritical::test_5_batch_processing_optimization
- [gw19][36m [ 91%] [0m[31mFAILED[0m app\tests\test_agents_comprehensive.py::TestTriageSubAgent::test_triage_categorization
- [gw19][36m [ 91%] [0m[31mFAILED[0m app\tests\test_agents_comprehensive.py::TestTriageSubAgent::test_triage_invalid_response_handling
- [gw19][36m [ 91%] [0m[31mERROR[0m app\test_system_startup.py::TestSystemStartup::test_detailed_health_check
- [gw19][36m [ 91%] [0m[31mFAILED[0m app\test_system_startup.py::TestSystemStartup::test_startup_error_handling
- [gw24][36m [ 91%] [0m[31mFAILED[0m app\test_generation_service.py::test_run_synthetic_data_generation_job_e2e
- [gw24][36m [ 91%] [0m[31mFAILED[0m app\test_health.py::test_live_endpoint
- [gw20][36m [ 91%] [0m[31mFAILED[0m app\tests\test_admin.py::test_get_app_settings_as_regular_user
- [gw19][36m [ 91%] [0m[31mFAILED[0m app\test_app.py::test_analysis_api
- [gw23][36m [ 91%] [0m[31mFAILED[0m app\test_websocket.py::test_websocket_receives_message_from_server
- [gw24][36m [ 92%] [0m[31mFAILED[0m app\tests\test_admin.py::test_add_log_table_already_exists
- [gw11][36m [ 92%] [0m[31mFAILED[0m app\tests\test_agents_comprehensive.py::TestSupervisorAgent::test_supervisor_state_persistence
- [gw5][36m [ 92%] [0m[31mFAILED[0m app\tests\test_business_value_critical.py::TestBusinessValueCritical::test_7_error_recovery_resilience
- [gw18][36m [ 92%] [0m[31mFAILED[0m app\tests\test_agents_comprehensive.py::TestSupervisorAgent::test_supervisor_websocket_streaming
- [gw22][36m [ 92%] [0m[31mFAILED[0m app\tests\test_agents_comprehensive.py::TestIntegration::test_end_to_end_workflow
- [gw21][36m [ 92%] [0m[31mFAILED[0m app\tests\test_agents_comprehensive.py::TestIntegration::test_concurrent_agent_execution
- [gw18][36m [ 92%] [0m[31mFAILED[0m app\test_app.py::test_generation_api
- [gw0][36m [ 92%] [0m[31mFAILED[0m app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_6_error_handling_and_recovery
- [gw25][36m [ 92%] [0m[31mFAILED[0m app\tests\test_admin.py::test_set_time_period_success
- [gw5][36m [ 92%] [0m[31mFAILED[0m app\tests\test_business_value_critical.py::TestBusinessValueCritical::test_8_report_generation_with_insights
- [gw0][36m [ 92%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_defaults
- [gw0][36m [ 92%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestDataValidation::test_validate_required_fields
- [gw0][36m [ 92%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestDataValidation::test_validate_missing_fields
- [gw0][36m [ 92%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestDataValidation::test_validate_data_types
- [gw0][36m [ 92%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestDataTransformation::test_transform_text_data
- [gw0][36m [ 92%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestDataTransformation::test_transform_json_data
- [gw0][36m [ 92%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestDataTransformation::test_transform_with_pipeline
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestDataEnrichment::test_enrich_with_metadata
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestDataEnrichment::test_enrich_with_external_source
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestErrorHandling::test_retry_on_failure
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestErrorHandling::test_max_retries_exceeded
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestErrorHandling::test_graceful_degradation
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestCaching::test_cache_hit
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestCaching::test_cache_expiration
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestIntegration::test_integration_with_websocket
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestIntegration::test_integration_with_database
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestIntegration::test_integration_with_supervisor
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestPerformance::test_concurrent_processing
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestPerformance::test_memory_efficiency
- [gw11][36m [ 93%] [0m[31mFAILED[0m app\tests\test_admin.py::test_remove_default_log_table_for_context_success
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestStateManagement::test_state_persistence
- [gw0][36m [ 93%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestStateManagement::test_state_recovery
- [gw0][36m [ 94%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestAnalysisEngine::test_detect_trend_increasing
- [gw0][36m [ 94%] [0m[31mFAILED[0m app\tests\test_admin.py::test_set_default_log_table_for_context_success
- [gw22][36m [ 94%] [0m[31mFAILED[0m app\tests\test_admin.py::test_set_log_table_success
- [gw5][36m [ 94%] [0m[31mFAILED[0m app\tests\test_business_value_critical.py::TestBusinessValueCritical::test_10_end_to_end_optimization_workflow
- [gw21][36m [ 94%] [0m[31mFAILED[0m app\tests\test_agents_comprehensive.py::TestIntegration::test_error_recovery
- [gw12][36m [ 94%] [0m[31mFAILED[0m app\tests\e2e\test_concurrent_user_load.py::TestConcurrentUserLoad::test_gradual_load_increase
- [gw26][36m [ 94%] [0m[31mFAILED[0m app\tests\test_admin.py::test_remove_log_table_not_found
- [gw21][36m [ 94%] [0m[31mFAILED[0m app\test_generation_service.py::test_content_generation_with_custom_table
- INTERNALERROR> def worker_internal_error(
- INTERNALERROR>         self, node: WorkerController, formatted_error: str
- INTERNALERROR>     ) -> None:
- INTERNALERROR>         """
- INTERNALERROR>         pytest_internalerror() was called on the worker.
- INTERNALERROR>
- INTERNALERROR>         pytest_internalerror() arguments are an excinfo and an excrepr, which can't
- INTERNALERROR>         be serialized, so we go with a poor man's solution of raising an exception
- INTERNALERROR>         here ourselves using the formatted message.
- INTERNALERROR>         """
- INTERNALERROR>         self._active_nodes.remove(node)
- INTERNALERROR>         try:
- INTERNALERROR> >           assert False, formatted_error
- INTERNALERROR> E           AssertionError: Traceback (most recent call last):
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqlitedb.py", line 115, in _execute
- INTERNALERROR> E                 return self.con.execute(sql, parameters)    # type: ignore[arg-type]
- INTERNALERROR> E                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E             sqlite3.OperationalError: no such table: file
- INTERNALERROR> E
- INTERNALERROR> E             During handling of the above exception, another exception occurred:
- INTERNALERROR> E
- INTERNALERROR> E             Traceback (most recent call last):
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqlitedb.py", line 120, in _execute
- INTERNALERROR> E                 return self.con.execute(sql, parameters)    # type: ignore[arg-type]
- INTERNALERROR> E                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E             sqlite3.OperationalError: no such table: file
- INTERNALERROR> E
- INTERNALERROR> E             The above exception was the direct cause of the following exception:
- INTERNALERROR> E
- INTERNALERROR> E             Traceback (most recent call last):
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\main.py", line 289, in wrap_session
- INTERNALERROR> E                 session.exitstatus = doit(config, session) or 0
- INTERNALERROR> E                                      ^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\main.py", line 343, in _main
- INTERNALERROR> E                 config.hook.pytest_runtestloop(session=session)
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_hooks.py", line 512, in __call__
- INTERNALERROR> E                 return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
- INTERNALERROR> E                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_manager.py", line 120, in _hookexec
- INTERNALERROR> E                 return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
- INTERNALERROR> E                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 167, in _multicall
- INTERNALERROR> E                 raise exception
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
- INTERNALERROR> E                 teardown.throw(exception)
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\logging.py", line 801, in pytest_runtestloop
- INTERNALERROR> E                 return (yield)  # Run all the tests.
- INTERNALERROR> E                         ^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
- INTERNALERROR> E                 teardown.throw(exception)
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\terminal.py", line 688, in pytest_runtestloop
- INTERNALERROR> E                 result = yield
- INTERNALERROR> E                          ^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 152, in _multicall
- INTERNALERROR> E                 teardown.send(result)
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pytest_cov\plugin.py", line 346, in pytest_runtestloop
- INTERNALERROR> E                 self.cov_controller.finish()
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pytest_cov\engine.py", line 57, in ensure_topdir_wrapper
- INTERNALERROR> E                 return meth(self, *args, **kwargs)
- INTERNALERROR> E                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\pytest_cov\engine.py", line 471, in finish
- INTERNALERROR> E                 self.cov.save()
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\control.py", line 818, in save
- INTERNALERROR> E                 data = self.get_data()
- INTERNALERROR> E                        ^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\control.py", line 899, in get_data
- INTERNALERROR> E                 self._post_save_work()
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\control.py", line 930, in _post_save_work
- INTERNALERROR> E                 self._data.touch_files(paths, plugin_name)
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqldata.py", line 620, in touch_files
- INTERNALERROR> E                 self._file_id(filename, add=True)
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqldata.py", line 416, in _file_id
- INTERNALERROR> E                 self._file_map[filename] = con.execute_for_rowid(
- INTERNALERROR> E                                            ^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqlitedb.py", line 171, in execute_for_rowid
- INTERNALERROR> E                 with self.execute(sql, parameters) as cur:
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\contextlib.py", line 137, in __enter__
- INTERNALERROR> E                 return next(self.gen)
- INTERNALERROR> E                        ^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqlitedb.py", line 150, in execute
- INTERNALERROR> E                 cur = self._execute(sql, parameters)
- INTERNALERROR> E                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR> E               File "C:\Users\antho\miniconda3\Lib\site-packages\coverage\sqlitedb.py", line 138, in _execute
- INTERNALERROR> E                 raise DataError(f"Couldn't use data file {self.filename!r}: {msg}") from exc
- INTERNALERROR> E             coverage.exceptions.DataError: Couldn't use data file 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\.coverage.Anthony.40592.XwXuGJsx.wgw29': no such table: file
- INTERNALERROR> E           assert False
- INTERNALERROR>
- INTERNALERROR> ..\..\..\..\miniconda3\Lib\site-packages\xdist\dsession.py:232: AssertionError
- INTERNALERROR> Traceback (most recent call last):
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\main.py", line 289, in wrap_session
- INTERNALERROR>     session.exitstatus = doit(config, session) or 0
- INTERNALERROR>                          ^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\main.py", line 343, in _main
- INTERNALERROR>     config.hook.pytest_runtestloop(session=session)
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_hooks.py", line 512, in __call__
- INTERNALERROR>     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
- INTERNALERROR>            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_manager.py", line 120, in _hookexec
- INTERNALERROR>     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
- INTERNALERROR>            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 167, in _multicall
- INTERNALERROR>     raise exception
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
- INTERNALERROR>     teardown.throw(exception)
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\logging.py", line 801, in pytest_runtestloop
- INTERNALERROR>     return (yield)  # Run all the tests.
- INTERNALERROR>             ^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
- INTERNALERROR>     teardown.throw(exception)
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\_pytest\terminal.py", line 688, in pytest_runtestloop
- INTERNALERROR>     result = yield
- INTERNALERROR>              ^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
- INTERNALERROR>     teardown.throw(exception)
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pytest_cov\plugin.py", line 340, in pytest_runtestloop
- INTERNALERROR>     result = yield
- INTERNALERROR>              ^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\pluggy\_callers.py", line 121, in _multicall
- INTERNALERROR>     res = hook_impl.function(*args)
- INTERNALERROR>           ^^^^^^^^^^^^^^^^^^^^^^^^^
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\xdist\dsession.py", line 138, in pytest_runtestloop
- INTERNALERROR>     self.loop_once()
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\xdist\dsession.py", line 163, in loop_once
- INTERNALERROR>     call(**kwargs)
- INTERNALERROR>   File "C:\Users\antho\miniconda3\Lib\site-packages\xdist\dsession.py", line 218, in worker_workerfinished
- INTERNALERROR>     self._active_nodes.remove(node)
- INTERNALERROR> KeyError: <WorkerController gw29>
- [FAIL] TESTS FAILED with exit code 3 after 212.82s

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/hooks/useChatWebSocket.test.ts
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/hooks/useKeyboardShortcuts.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/CorpusAdmin.test.tsx (5.029 s)
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/ChatWindow.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx (5.804 s)
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/components/AppWithLayout.test.tsx
- FAIL __tests__/auth/context.test.tsx (5.93 s)
- FAIL __tests__/components/AdminChat.test.tsx
- FAIL __tests__/components/ChatComponents.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx (7.185 s)
- FAIL __tests__/imports/internal-imports.test.tsx (8.855 s)
- FAIL __tests__/system/startup.test.tsx (13.309 s)
- FAIL __tests__/components/chat/MainChat.test.tsx (13.971 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (14.985 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (27.548 s)
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/components/chat/MessageInput.test.tsx (69.024 s)
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/hooks/useChatWebSocket.test.ts
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/hooks/useKeyboardShortcuts.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/CorpusAdmin.test.tsx (5.029 s)
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/ChatWindow.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx (5.804 s)
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/components/AppWithLayout.test.tsx
- FAIL __tests__/auth/context.test.tsx (5.93 s)
- FAIL __tests__/components/AdminChat.test.tsx
- FAIL __tests__/components/ChatComponents.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx (7.185 s)
- FAIL __tests__/imports/internal-imports.test.tsx (8.855 s)
- FAIL __tests__/system/startup.test.tsx (13.309 s)
- FAIL __tests__/components/chat/MainChat.test.tsx (13.971 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (14.985 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (27.548 s)
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/components/chat/MessageInput.test.tsx (69.024 s)


---
*Generated by Netra AI Unified Test Runner v3.0*
