# Netra AI Platform - Test Report

**Generated:** 2025-08-12T12:38:50.982516  
**Test Level:** comprehensive - Full test suite with coverage (30-45 minutes)  
**Purpose:** Pre-release validation, full system testing

## Test Summary

**Total Tests:** 298  
**Passed:** 18  
**Failed:** 278  
**Skipped:** 1  
**Errors:** 1  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 2 | 0 | 0 | 1 | 1 | 28.64s | [FAILED] |
| Frontend  | 296 | 18 | 278 | 0 | 0 | 40.45s | [FAILED] |

## Environment and Configuration

- **Test Level:** comprehensive
- **Description:** Full test suite with coverage (30-45 minutes)
- **Purpose:** Pre-release validation, full system testing
- **Timeout:** 2700s
- **Coverage Enabled:** Yes
- **Total Duration:** 69.10s
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
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 6/6 workers

=================================== ERRORS ====================================
[31m[1m_______ ERROR collecting app/tests/test_real_services_comprehensive.py ________[0m
ImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\test_real_services_comprehensive.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\..\miniconda3\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
app\tests\test_real_services_comprehensive.py:31: in <module>
    from app.services.database.user_repository import UserRepository
E   ModuleNotFoundError: No module named 'app.services.database.user_repository'
- Generated html report: file:///C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/reports/tests/report.html -
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m app/tests/test_real_services_comprehensive.py
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m======================== [33m1 skipped[0m, [31m[1m1 error[0m[31m in 19.76s[0m[31m =========================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 27.86s

[Report] HTML Report: reports/tests/report.html
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================


```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> jest --coverage --coverageDirectory=../reports/frontend-coverage

---------------------------------|---------|----------|---------|---------|--------------------------------------------------------------------------------------------------------------
File                             | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s                                                                                            
---------------------------------|---------|----------|---------|---------|--------------------------------------------------------------------------------------------------------------
All files                        |   65.11 |    79.08 |   49.82 |   65.11 |                                                                                                              
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
 frontend/components             |    93.2 |    98.85 |      90 |    93.2 |                                                                                                              
  AppWithLayout.tsx              |     100 |      100 |     100 |     100 |                                                                                                              
  ChatHistorySection.tsx         |     100 |      100 |     100 |     100 |                                                                                                              
  Footer.tsx                     |     100 |      100 |     100 |     100 |                                                                                                              
  Header.tsx                     |   48.14 |      100 |       0 |   48.14 | 14-27                                                                                                        
  Icons.tsx                      |     100 |      100 |     100 |     100 |                                                                                                              
  LoginButton.tsx                |   18.51 |      100 |       0 |   18.51 | 6-27                                                                                                         
  SubAgentStatus.tsx             |     100 |    94.11 |     100 |     100 | 43                                                                                                           
 frontend/components/chat        |   66.85 |    75.63 |   71.11 |   66.85 |                                                                                                              
  AgentStatusPanel.tsx           |    6.06 |      100 |       0 |    6.06 | 21-361                                                                                                       
  ChatHeader.tsx                 |   95.89 |       60 |     100 |   95.89 | 16,19,41,43,45-46                                                                                            
  ChatHistory.tsx                |    18.6 |      100 |       0 |    18.6 | 7-41                                                                                                         
  ChatSidebar.tsx                |    3.11 |      100 |       0 |    3.11 | 13-385                                                                                                       
  ChatWindow.tsx                 |     100 |      100 |     100 |     100 |                                                                                                              
  ExamplePrompts.tsx             |     100 |      100 |     100 |     100 |                                                                                                              
  MainChat.tsx                   |   96.26 |      100 |      25 |   96.26 | 54-58                                                                                                        
  MessageInput.tsx               |   94.71 |       88 |     100 |   94.71 | 51-53,104-105,127,131-140                                                                                    
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
- =================================== ERRORS ====================================
- [31m[1m_______ ERROR collecting app/tests/test_real_services_comprehensive.py ________[0m
- [31mERROR[0m app/tests/test_real_services_comprehensive.py
- [FAIL] TESTS FAILED with exit code 2 after 27.86s

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/utils/test-utils.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/setup/websocket-mock.ts
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/auth/context.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx
- FAIL __tests__/imports/internal-imports.test.tsx (5.463 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (10.574 s)
- FAIL __tests__/system/startup.test.tsx (12.126 s)
- FAIL __tests__/components/chat/MainChat.test.tsx (12.935 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/components/chat/MessageInput.test.tsx (18.754 s)
- FAIL __tests__/integration/comprehensive-integration.test.tsx (25.818 s)
- FAIL __tests__/components/ChatComponents.test.tsx (34.302 s)
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/utils/test-utils.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/setup/websocket-mock.ts
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/auth/context.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx
- FAIL __tests__/imports/internal-imports.test.tsx (5.463 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (10.574 s)
- FAIL __tests__/system/startup.test.tsx (12.126 s)
- FAIL __tests__/components/chat/MainChat.test.tsx (12.935 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/components/chat/MessageInput.test.tsx (18.754 s)
- FAIL __tests__/integration/comprehensive-integration.test.tsx (25.818 s)
- FAIL __tests__/components/ChatComponents.test.tsx (34.302 s)


---
*Generated by Netra AI Unified Test Runner v3.0*
