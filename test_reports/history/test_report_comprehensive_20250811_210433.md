# Netra AI Platform - Test Report

**Generated:** 2025-08-11T21:04:33.869639  
**Test Level:** comprehensive - Full test suite with coverage (10-15 minutes)  
**Purpose:** Pre-release validation, full system testing

## Test Summary

**Total Tests:** 350  
**Passed:** 168  
**Failed:** 182  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 156 | 150 | 6 | 0 | 0 | 62.14s | [FAILED] |
| Frontend  | 194 | 18 | 176 | 0 | 0 | 52.29s | [FAILED] |

## Environment and Configuration

- **Test Level:** comprehensive
- **Description:** Full test suite with coverage (10-15 minutes)
- **Purpose:** Pre-release validation, full system testing
- **Timeout:** 900s
- **Coverage Enabled:** Yes
- **Total Duration:** 114.43s
- **Exit Code:** 2

### Backend Configuration
```
--coverage --parallel=6 --html-output --fail-fast
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
  Parallel: 6
  Coverage: enabled
  Fail Fast: enabled
  Environment: development

Running command:
  pytest app/tests tests integration_tests -v -n 6 -x --maxfail=1 --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 --html=reports/tests/report.html --self-contained-html --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 6/6 workers
6 workers [2733 items]

scheduling tests via LoadScheduling

app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_1_complete_agent_lifecycle_request_to_completion 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_retry_success_first_try 
app\tests\agents\test_supervisor_advanced.py::test_supervisor_concurrent_requests 
app\tests\agents\test_triage_sub_agent.py::TestEntryConditions::test_entry_conditions_invalid_request 
app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestClickHouseArrayOperations::test_validate_query_catches_errors 
app\tests\core\test_config_manager.py::TestConfigManager::test_load_configuration_validation_failure 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestClickHouseArrayOperations::test_validate_query_catches_errors 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_config_manager.py::TestConfigManager::test_load_configuration_validation_failure 
app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestClickHouseArrayOperations::test_query_interceptor_fixes_queries 
app\tests\core\test_config_manager.py::TestConfigManager::test_get_config_caching 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supervisor_advanced.py::test_supervisor_concurrent_requests 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_config_manager.py::TestConfigManager::test_get_config_caching 
app\tests\core\test_config_manager.py::TestConfigManager::test_reload_config 
app\tests\agents\test_supervisor_agent.py::test_supervisor_runs_sub_agents_in_order 
[gw5][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_triage_sub_agent.py::TestEntryConditions::test_entry_conditions_invalid_request 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_retry_success_first_try 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_retry_success_after_failures 
app\tests\agents\test_triage_sub_agent.py::TestPydanticModels::test_triage_result_validation 
[gw5][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_triage_sub_agent.py::TestPydanticModels::test_triage_result_validation 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_config_manager.py::TestConfigManager::test_reload_config 
app\tests\core\test_config_manager.py::TestConfigurationFunctions::test_get_config 
app\tests\agents\test_triage_sub_agent.py::TestPydanticModels::test_triage_result_confidence_validation 
[gw5][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_triage_sub_agent.py::TestPydanticModels::test_triage_result_confidence_validation 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestClickHouseArrayOperations::test_query_interceptor_fixes_queries 
app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestRealisticLogIngestion::test_streaming_log_ingestion 
app\tests\agents\test_triage_sub_agent.py::TestPydanticModels::test_key_parameters_model 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_config_manager.py::TestConfigurationFunctions::test_get_config 
[gw5][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_triage_sub_agent.py::TestPydanticModels::test_key_parameters_model 
app\tests\core\test_config_manager.py::TestConfigurationFunctions::test_reload_config 
app\tests\agents\test_triage_sub_agent.py::TestPydanticModels::test_user_intent_model 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_config_manager.py::TestConfigurationFunctions::test_reload_config 
[gw5][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_triage_sub_agent.py::TestPydanticModels::test_user_intent_model 
app\tests\core\test_config_manager.py::TestConfigurationIntegration::test_full_configuration_flow 
app\tests\agents\test_triage_sub_agent.py::TestCleanup::test_cleanup_with_metrics 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supervisor_agent.py::test_supervisor_runs_sub_agents_in_order 
app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routes_to_triage_for_classification 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_1_complete_agent_lifecycle_request_to_completion 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_config_manager.py::TestConfigurationIntegration::test_full_configuration_flow 
app\tests\core\test_config_manager.py::TestConfigurationIntegration::test_testing_configuration 
app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_2_websocket_real_time_streaming 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_config_manager.py::TestConfigurationIntegration::test_testing_configuration 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routes_to_triage_for_classification 
app\tests\core\test_config_manager.py::TestConfigurationIntegration::test_configuration_error_handling 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestRealisticLogIngestion::test_streaming_log_ingestion 
app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestRealisticLogIngestion::test_log_pattern_recognition 
app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routes_to_optimization_for_ai_workloads 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestRealisticLogIngestion::test_log_pattern_recognition 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_config_manager.py::TestConfigurationIntegration::test_configuration_error_handling 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routes_to_optimization_for_ai_workloads 
app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestLLMMetricsAggregation::test_llm_cost_optimization_query 
app\tests\core\test_core_infrastructure_11_20.py::TestConfigValidator::test_valid_config_passes_validation 
app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routes_to_data_for_analysis_queries 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestLLMMetricsAggregation::test_llm_cost_optimization_query 
app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestLLMMetricsAggregation::test_llm_usage_patterns 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_core_infrastructure_11_20.py::TestConfigValidator::test_valid_config_passes_validation 
app\tests\core\test_core_infrastructure_11_20.py::TestConfigValidator::test_invalid_database_url_rejected 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestLLMMetricsAggregation::test_llm_usage_patterns 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routes_to_data_for_analysis_queries 
app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routing_with_conditional_pipeline 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_2_websocket_real_time_streaming 
app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_3_supervisor_orchestration_logic 
app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestPerformanceMetricsWithClickHouse::test_metrics_extraction_with_arrays 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\core\test_core_infrastructure_11_20.py::TestConfigValidator::test_invalid_database_url_rejected 
[gw4][36m [  1%] [0m[32mPASSED[0m app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestPerformanceMetricsWithClickHouse::test_metrics_extraction_with_arrays 
app\tests\clickhouse\test_realistic_clickhouse_operations.py::TestTimeSeriesAnalysis::test_moving_average_calculation 
app\tests\core\test_core_in...(truncated)
```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> jest --coverage --coverageDirectory=../reports/frontend-coverage

---------------------------------|---------|----------|---------|---------|--------------------------------------------------------------------------------------------------------------
File                             | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s                                                                                            
---------------------------------|---------|----------|---------|---------|--------------------------------------------------------------------------------------------------------------
All files                        |   68.08 |     78.2 |   50.72 |   68.08 |                                                                                                              
 frontend                        |     100 |        0 |     100 |     100 |                                                                                                              
  config.ts                      |     100 |        0 |     100 |     100 | 2-3                                                                                                          
 frontend/app                    |    45.9 |      100 |       0 |    45.9 |                                                                                                              
  layout.tsx                     |   58.62 |      100 |       0 |   58.62 | 18-29                                                                                                        
  page.tsx                       |   34.37 |      100 |       0 |   34.37 | 10-30                                                                                                        
 frontend/app/chat               |   69.23 |      100 |       0 |   69.23 |                                                                                                              
  page.tsx                       |   69.23 |      100 |       0 |   69.23 | 8-11                                                                                                         
 frontend/auth                   |   65.64 |    96.66 |   13.33 |   65.64 |                                                                                                              
  components.tsx                 |     100 |      100 |     100 |     100 |                                                                                                              
  context.tsx                    |   81.96 |    95.23 |   33.33 |   81.96 | 72-77,94-99,102-111                                                                                          
  index.ts                       |     100 |      100 |     100 |     100 |                                                                                                              
  service.ts                     |   29.46 |      100 |       0 |   29.46 | 11-16,19-43,46-47,50-52,55-56,59-60,63-64,67-68,71-74,77-101,104-109                                         
  types.ts                       |     100 |      100 |     100 |     100 |                                                                                                              
 frontend/components             |    88.8 |    98.86 |   86.36 |    88.8 |                                                                                                              
  AppWithLayout.tsx              |     100 |      100 |     100 |     100 |                                                                                                              
  ChatHistorySection.tsx         |     100 |      100 |     100 |     100 |                                                                                                              
  ErrorFallback.tsx              |     100 |      100 |     100 |     100 |                                                                                                              
  Footer.tsx                     |     100 |      100 |     100 |     100 |                                                                                                              
  Header.tsx                     |   48.14 |      100 |       0 |   48.14 | 14-27                                                                                                        
  Icons.tsx                      |     100 |      100 |     100 |     100 |                                                                                                              
  LoginButton.tsx                |   18.51 |      100 |       0 |   18.51 | 6-27                                                                                                         
  NavLinks.tsx                   |   41.53 |      100 |       0 |   41.53 | 28-65                                                                                                        
  SubAgentStatus.tsx             |     100 |    94.11 |     100 |     100 | 43                                                                                                           
 frontend/components/chat        |   77.64 |     72.1 |   74.41 |   77.64 |                                                                                                              
  ChatHeader.tsx                 |   95.89 |       60 |     100 |   95.89 | 16,19,41,43,45-46                                                                                            
  ChatSidebar.tsx                |    3.11 |      100 |       0 |    3.11 | 13-385                                                                                                       
  ChatWindow.tsx                 |     100 |      100 |     100 |     100 |                                                                                                              
  ExamplePrompts.tsx             |     100 |      100 |     100 |     100 |                                                                                                              
  MainChat.tsx                   |   96.26 |      100 |      25 |   96.26 | 54-58                                                                                                        
  MessageInput.tsx               |   93.06 |    74.41 |     100 |   93.06 | 51-53,104-105,124-129,131-140                                                                                
  MessageItem.tsx                |   91.66 |       76 |     100 |   91.66 | 28-41,119                                                                                                    
  MessageList.tsx                |   86.06 |    69.23 |   66.66 |   86.06 | 26-38,62-63,108-109                                                                                          
  OverflowPanel.tsx              |   86.41 |       75 |   16.66 |   86.41 | 54-60,67-88,93-98,132-133,218-219                                                                            
  PersistentResponseCard.tsx     |   99.67 |    65.78 |     100 |   99.67 | 97                                                                                                           
  RawJsonView.tsx                |   56.25 |      100 |       0 |   56.25 | 10-16                                                                                                        
  ThinkingIndicator.tsx          |   95.23 |    38.46 |     100 |   95.23 | 31,33,35,44,46,48                                                                                            
 frontend/components/chat/layers |   39.03 |      100 |      50 |   39.03 |                                                                                                              
  FastLayer.tsx                  |     100 |      100 |     100 |     100 |                                                                                                              
  MediumLayer.tsx                |    5.44 |      100 |       0 |    5.44 | 9-147                                                                                                        
 frontend/components/ui          |   84.03 |    88.23 |   54.16 |   84.03 |                                                                                                              
  accordion.tsx                  |   19.69 |      100 |       0 |   19.69 | 9-13,15-26,28-48,50-64                                                                                       
  alert.tsx                      |     100 |      100 |     100 |     100 |                                                                                                              
  avatar.tsx                     |     100 |      100 |     100 |     100 |                                                                                                              
  badge.tsx                      |   86.11 |      100 |       0 |   86.11 | 30-34                                                                                                        
  button.tsx                     |     100 |       50 |     100 |     100 | 45                                                                                                           
  card.tsx                       |     100 |      100 |     100 |     100 |                                                                                                              
  collapsible.tsx                |     100 |      100 |     100 |     100 |                                                                                                              
  dropdown-menu.tsx              |      95 |      100 |       0 |      95 | 172-181                                                                                                      
  input.tsx                      |     100 |      100 |     100 |     100 |                                                                                                              
  label.tsx                      |   ...(truncated)
```

## Error Summary

### Backend Errors
- [gw5][36m [  2%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent.py::TestCleanup::test_cleanup_with_metrics
- [gw3][36m [  2%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestResourceManager::test_resource_tracking
- [gw4][36m [  2%] [0m[31mFAILED[0m app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_submit_task_during_shutdown
- [gw2][36m [  2%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_load_state
- [gw1][36m [  5%] [0m[31mFAILED[0m app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_concurrent_research_processing
- [gw0][36m [  5%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent.py::TestDataEnrichment::test_enrich_with_external_source
- [31mFAILED[0m app\tests\agents\test_triage_sub_agent.py::[1mTestCleanup::test_cleanup_with_metrics[0m - AssertionError: Expected 'debug' to have been called.
- [31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::[1mTestResourceManager::test_resource_tracking[0m - AttributeError: 'ResourceTracker' object has no attribute 'track_resource'
- [31mFAILED[0m app\tests\core\test_async_utils.py::[1mTestAsyncTaskPool::test_submit_task_during_shutdown[0m - TypeError: unbound method dict.keys() needs an argument
- [31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::[1mTestDataSubAgent::test_load_state[0m - AssertionError: assert False
- [31mFAILED[0m app\tests\agents\test_supply_researcher_agent.py::[1mTestSupplyResearcherAgent::test_concurrent_research_processing[0m - AssertionError: assert 0.5469999999986612 < ((5 * 0.1) * 0.8)
- [31mFAILED[0m app\tests\agents\test_data_sub_agent.py::[1mTestDataEnrichment::test_enrich_with_external_source[0m - AttributeError: <module 'app.agents.data_sub_agent' from 'C:\\Users\\antho\...
- [FAIL] TESTS FAILED with exit code 2 after 61.30s

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/auth/context.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx
- FAIL __tests__/imports/internal-imports.test.tsx (5.379 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (9.412 s)
- FAIL __tests__/system/startup.test.tsx (12.066 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/components/chat/MainChat.test.tsx (12.571 s)
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (25.627 s)
- FAIL __tests__/components/ChatComponents.test.tsx (30.535 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (46.912 s)
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/auth/context.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx
- FAIL __tests__/imports/internal-imports.test.tsx (5.379 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (9.412 s)
- FAIL __tests__/system/startup.test.tsx (12.066 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/components/chat/MainChat.test.tsx (12.571 s)
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (25.627 s)
- FAIL __tests__/components/ChatComponents.test.tsx (30.535 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (46.912 s)


---
*Generated by Netra AI Unified Test Runner v3.0*
