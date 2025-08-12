# Netra AI Platform - Test Report

**Generated:** 2025-08-11T20:55:43.773822  
**Test Level:** comprehensive - Full test suite with coverage (10-15 minutes)  
**Purpose:** Pre-release validation, full system testing

## Test Summary

**Total Tests:** 272  
**Passed:** 86  
**Failed:** 186  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 75 | 69 | 6 | 0 | 0 | 52.62s | [FAILED] |
| Frontend  | 197 | 17 | 180 | 0 | 0 | 51.55s | [FAILED] |

## Environment and Configuration

- **Test Level:** comprehensive
- **Description:** Full test suite with coverage (10-15 minutes)
- **Purpose:** Pre-release validation, full system testing
- **Timeout:** 900s
- **Coverage Enabled:** Yes
- **Total Duration:** 104.17s
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
6 workers [2716 items]

scheduling tests via LoadScheduling

app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_1_complete_agent_lifecycle_request_to_completion 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_retry_success_first_try 
app\tests\agents\test_supervisor_advanced.py::test_supervisor_concurrent_requests 
app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAdvancedEntityExtraction::test_extract_time_ranges_complex 
app\tests\core\test_async_utils.py::TestAsyncResourceManager::test_register_resource_during_shutdown 
app\tests\core\test_core_infrastructure_11_20.py::TestLoggingManager::test_logging_configuration 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_async_utils.py::TestAsyncResourceManager::test_register_resource_during_shutdown 
app\tests\core\test_async_utils.py::TestAsyncResourceManager::test_cleanup_all 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supervisor_advanced.py::test_supervisor_concurrent_requests 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_retry_success_first_try 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_async_utils.py::TestAsyncResourceManager::test_cleanup_all 
app\tests\core\test_async_utils.py::TestAsyncResourceManager::test_cleanup_all_idempotent 
app\tests\agents\test_supervisor_agent.py::test_supervisor_runs_sub_agents_in_order 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_retry_success_after_failures 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_async_utils.py::TestAsyncResourceManager::test_cleanup_all_idempotent 
app\tests\core\test_async_utils.py::TestAsyncResourceManager::test_cleanup_handles_exceptions 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_async_utils.py::TestAsyncResourceManager::test_cleanup_handles_exceptions 
[gw5][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_core_infrastructure_11_20.py::TestLoggingManager::test_logging_configuration 
app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_initialization 
app\tests\core\test_core_infrastructure_11_20.py::TestLoggingManager::test_structured_logging 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_initialization 
app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_submit_task_success 
[gw5][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_core_infrastructure_11_20.py::TestLoggingManager::test_structured_logging 
app\tests\core\test_core_infrastructure_11_20.py::TestResourceManager::test_resource_tracking 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supervisor_agent.py::test_supervisor_runs_sub_agents_in_order 
app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routes_to_triage_for_classification 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routes_to_triage_for_classification 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_submit_task_success 
app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_submit_task_exception 
app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routes_to_optimization_for_ai_workloads 
[gw4][36m [  0%] [0m[32mPASSED[0m app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_submit_task_exception 
app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_submit_task_during_shutdown 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routes_to_optimization_for_ai_workloads 
app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routes_to_data_for_analysis_queries 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routes_to_data_for_analysis_queries 
app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routing_with_conditional_pipeline 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorConsolidatedAgentRouting::test_routing_with_conditional_pipeline 
app\tests\agents\test_supervisor_consolidated_comprehensive.py::TestSupervisorErrorCascadePrevention::test_prevents_cascade_on_single_agent_failure 
[gw5][36m [  0%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestResourceManager::test_resource_tracking 
[gw2][36m [  0%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAdvancedEntityExtraction::test_extract_time_ranges_complex 
[gw4][36m [  0%] [0m[31mFAILED[0m app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_submit_task_during_shutdown 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_retry_success_after_failures 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_retry_all_failures 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_retry_all_failures 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_batch_safe_mixed_results 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_batch_safe_mixed_results 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_batch_safe_with_exception 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_batch_safe_with_exception 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_cache_hit 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_cache_hit 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_cache_different_keys 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_with_cache_different_keys 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_and_stream 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_and_stream 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_and_persist 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_and_persist 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_handle_supervisor_request_process_data 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_handle_supervisor_request_process_data 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_handle_supervisor_request_no_callback 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_handle_supervisor_request_no_callback 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_concurrent 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_concurrent 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_concurrent_empty 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_concurrent_empty 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_stream 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_process_stream 
app\tes...(truncated)
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
- [gw5][36m [  0%] [0m[31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::TestResourceManager::test_resource_tracking
- [gw2][36m [  0%] [0m[31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::TestAdvancedEntityExtraction::test_extract_time_ranges_complex
- [gw4][36m [  0%] [0m[31mFAILED[0m app\tests\core\test_async_utils.py::TestAsyncTaskPool::test_submit_task_during_shutdown
- [gw1][36m [  1%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgent::test_load_state
- [gw3][36m [  2%] [0m[31mFAILED[0m app\tests\agents\test_supply_researcher_agent.py::TestSupplyResearcherAgent::test_execute_agent
- [gw0][36m [  2%] [0m[31mFAILED[0m app\tests\agents\test_agent_e2e_critical.py::TestAgentE2ECritical::test_1_complete_agent_lifecycle_request_to_completion
- 6.411 | ERROR    | app.agents.supervisor_consolidated:_execute_agent_with_retry:407 | Agent TriageSubAgent failed (attempt 2): 'AgentExecutionContext' object has no attribute 'pipeline'
- 2025-08-11 20:54:40.425 | ERROR    | app.agents.supervisor_consolidated:_execute_agent_with_retry:407 | Agent TriageSubAgent failed (attempt 3): 'AgentExecutionContext' object has no attribute 'pipeline'
- 2025-08-11 20:54:48.437 | ERROR    | app.agents.supervisor_consolidated:_execute_agent_with_retry:407 | Agent TriageSubAgent failed (attempt 4): 'AgentExecutionContext' object has no attribute 'pipeline'
- [31mFAILED[0m app\tests\core\test_core_infrastructure_11_20.py::[1mTestResourceManager::test_resource_tracking[0m - AttributeError: 'ResourceTracker' object has no attribute 'track_resource'
- [31mFAILED[0m app\tests\agents\test_triage_sub_agent_comprehensive.py::[1mTestAdvancedEntityExtraction::test_extract_time_ranges_complex[0m - AssertionError: assert 1 >= 2
- [31mFAILED[0m app\tests\core\test_async_utils.py::[1mTestAsyncTaskPool::test_submit_task_during_shutdown[0m - TypeError: unbound method dict.keys() needs an argument
- [31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::[1mTestDataSubAgent::test_load_state[0m - AssertionError: assert False
- [31mFAILED[0m app\tests\agents\test_supply_researcher_agent.py::[1mTestSupplyResearcherAgent::test_execute_agent[0m - pydantic_core._pydantic_core.ValidationError: 1 validation error for DeepAg...
- [31mFAILED[0m app\tests\agents\test_agent_e2e_critical.py::[1mTestAgentE2ECritical::test_1_complete_agent_lifecycle_request_to_completion[0m - Exception: Agent TriageSubAgent failed after 4 attempts: 'AgentExecutionCon...
- [FAIL] TESTS FAILED with exit code 2 after 51.75s

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/components/chat/ChatHeader.test.tsx
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/auth/context.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx
- FAIL __tests__/imports/internal-imports.test.tsx (5.553 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (9.115 s)
- FAIL __tests__/system/startup.test.tsx (12.088 s)
- FAIL __tests__/components/chat/MainChat.test.tsx (12.745 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (25.888 s)
- FAIL __tests__/components/ChatComponents.test.tsx (30.799 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (46.122 s)
- FAIL __tests__/components/chat/ChatHeader.test.tsx
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/auth/context.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx
- FAIL __tests__/imports/internal-imports.test.tsx (5.553 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (9.115 s)
- FAIL __tests__/system/startup.test.tsx (12.088 s)
- FAIL __tests__/components/chat/MainChat.test.tsx (12.745 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (25.888 s)
- FAIL __tests__/components/ChatComponents.test.tsx (30.799 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (46.122 s)


---
*Generated by Netra AI Unified Test Runner v3.0*
