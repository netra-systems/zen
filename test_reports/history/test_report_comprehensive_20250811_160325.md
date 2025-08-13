# Netra AI Platform - Test Report

**Generated:** 2025-08-11T15:35:51.206808  
**Test Level:** comprehensive - Full test suite with coverage (10-15 minutes)  
**Purpose:** Pre-release validation, full system testing

## Test Summary

**Total Tests:** 263  
**Passed:** 15  
**Failed:** 247  
**Skipped:** 0  
**Errors:** 1  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 1 | 0 | 0 | 0 | 1 | 42.82s | [FAILED] |
| Frontend  | 262 | 15 | 247 | 0 | 0 | 61.14s | [FAILED] |

## Environment and Configuration

- **Test Level:** comprehensive
- **Description:** Full test suite with coverage (10-15 minutes)
- **Purpose:** Pre-release validation, full system testing
- **Timeout:** 900s
- **Coverage Enabled:** Yes
- **Total Duration:** 103.96s
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

=================================== ERRORS ====================================
[31m[1m____________________ ERROR collecting test_mcp_service.py _____________________[0m
import file mismatch:
imported module 'test_mcp_service' has this __file__ attribute:
  C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\mcp\test_mcp_service.py
which is not the same as the test file we want to collect:
  C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\test_mcp_service.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
- Generated html report: file:///C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/reports/tests/report.html -
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m app\test_mcp_service.py
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m============================== [31m[1m1 error[0m[31m in 32.16s[0m[31m ==============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 41.89s

[Report] HTML Report: reports/tests/report.html
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================


```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> jest --coverage --coverageDirectory=../reports/frontend-coverage

---------------------------------|---------|----------|---------|---------|----------------------------------------------------------------------------------------------------------
File                             | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s                                                                                        
---------------------------------|---------|----------|---------|---------|----------------------------------------------------------------------------------------------------------
All files                        |   64.24 |    73.95 |   56.78 |   64.24 |                                                                                                          
 frontend                        |     100 |      100 |     100 |     100 |                                                                                                          
  config.ts                      |     100 |      100 |     100 |     100 |                                                                                                          
 frontend/app                    |   68.33 |      100 |      20 |   68.33 |                                                                                                          
  layout.tsx                     |   92.85 |      100 |   33.33 |   92.85 | 10,12                                                                                                    
  page.tsx                       |   46.87 |      100 |       0 |   46.87 | 8-9,18-32                                                                                                
 frontend/app/chat               |   69.23 |      100 |       0 |   69.23 |                                                                                                          
  page.tsx                       |   69.23 |      100 |       0 |   69.23 | 10-13                                                                                                    
 frontend/auth                   |   89.79 |    98.33 |   89.47 |   89.79 |                                                                                                          
  components.tsx                 |     100 |      100 |     100 |     100 |                                                                                                          
  context.tsx                    |    75.4 |    95.83 |   66.66 |    75.4 | 77-92,108-117,119-122                                                                                    
  index.ts                       |     100 |      100 |     100 |     100 |                                                                                                          
  service.ts                     |     100 |      100 |     100 |     100 |                                                                                                          
  types.ts                       |     100 |      100 |     100 |     100 |                                                                                                          
 frontend/components             |   85.84 |    87.73 |   68.57 |   85.84 |                                                                                                          
  AppWithLayout.tsx              |   38.46 |      100 |       0 |   38.46 | 16-39                                                                                                    
  ChatHistorySection.tsx         |   98.89 |    87.87 |     100 |   98.89 | 41,45-46                                                                                                 
  CorpusAdmin.tsx                |     100 |      100 |     100 |     100 |                                                                                                          
  ErrorFallback.tsx              |     100 |       80 |     100 |     100 | 17                                                                                                       
  Footer.tsx                     |     100 |      100 |       0 |     100 |                                                                                                          
  Header.tsx                     |   77.77 |      100 |   33.33 |   77.77 | 22-27                                                                                                    
  Icons.tsx                      |   38.09 |      100 |   33.33 |   38.09 | 12-31,37-42                                                                                              
  LoginButton.tsx                |   66.66 |    66.66 |   33.33 |   66.66 | 19-27                                                                                                    
  NavLinks.tsx                   |      60 |    66.66 |   33.33 |      60 | 8-9,45-70                                                                                                
  SubAgentStatus.tsx             |     100 |    89.47 |     100 |     100 | 21,53                                                                                                    
 frontend/components/chat        |   69.53 |    66.49 |   80.39 |   69.53 |                                                                                                          
  ChatHeader.tsx                 |   95.89 |       60 |     100 |   95.89 | 16,19,41,43,45-46                                                                                        
  ChatSidebar.tsx                |   14.02 |    38.46 |      60 |   14.02 | 31,56-385                                                                                                
  ExamplePrompts.tsx             |     100 |    92.85 |     100 |     100 | 18                                                                                                       
  MainChat.tsx                   |   95.52 |    70.37 |   83.33 |   95.52 | 39,43,60,100-102                                                                                         
  MessageInput.tsx               |   93.06 |    74.41 |     100 |   93.06 | 51-53,104-105,124-129,131-140                                                                            
  MessageItem.tsx                |   91.66 |       75 |     100 |   91.66 | 28-41,119                                                                                                
  MessageList.tsx                |   86.06 |    71.42 |   66.66 |   86.06 | 26-38,93-94,108-109                                                                                      
  OverflowPanel.tsx              |   39.37 |    47.36 |      50 |   39.37 | 28,41,48-49,60-62,87-95,103-122,128,151-287                                                              
  PersistentResponseCard.tsx     |   83.47 |    83.33 |     100 |   83.47 | 102-121                                                                                                  
  RawJsonView.tsx                |   56.25 |      100 |       0 |   56.25 | 10-16                                                                                                    
  ThinkingIndicator.tsx          |   95.23 |    38.46 |     100 |   95.23 | 31,33,35,44,46,48                                                                                        
 frontend/components/chat/layers |   57.45 |    59.09 |   66.66 |   57.45 |                                                                                                          
  FastLayer.tsx                  |     100 |    88.88 |     100 |     100 | 16                                                                                                       
  MediumLayer.tsx                |   34.01 |    38.46 |      50 |   34.01 | 13-14,31,34,55-147                                                                                       
 frontend/components/ui          |   84.63 |    63.81 |   60.86 |   84.63 |                                                                                                          
  accordion.tsx                  |   83.33 |    58.82 |      50 |   83.33 | 13-17,19,21,51,63-65                                                                                     
  alert.tsx                      |   88.13 |    53.84 |   57.14 |   88.13 | 8,10,12,43-44,46,51                                                                                      
  avatar.tsx                     |     100 |      100 |     100 |     100 |                                                                                                          
  badge.tsx                      |   91.66 |       60 |   66.66 |   91.66 | 9-11                                                                                                     
  button.tsx                     |     100 |       50 |     100 |     100 | 45                                                                                                       
  card.tsx                       |     100 |      100 |     100 |     100 |                                                                                                          
  collapsible.tsx                |     100 |      100 |     100 |     100 |                                                                                                          
  dropdown-menu.tsx              |      46 |    61.11 |   21.05 |      46 | 12,14-16,18,20,24-25,27-28,32-35,37,39-40,42,87-96,103-115,121-136,142-156,161-196                       
  input.tsx                      |   91.66 |    57.14 |      75 |   91.66 | 23-24                                                                                                    
  label.tsx                      |   95.23 |    66.66 |      50 |   95.23 | 6                                                                                                        
  progress.tsx                   |   94.28 |    66.66 |      75 |  ...(truncated)
```

## Error Summary

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m____________________ ERROR collecting test_mcp_service.py _____________________[0m
- [31mERROR[0m app\test_mcp_service.py
- [FAIL] TESTS FAILED with exit code 2 after 41.89s

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/hooks/useKeyboardShortcuts.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/ChatWindow.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/CorpusAdmin.test.tsx (5.049 s)
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/components/AppWithLayout.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx (5.21 s)
- FAIL __tests__/integration/advanced-integration.test.tsx (5.385 s)
- FAIL __tests__/auth/context.test.tsx (5.784 s)
- FAIL __tests__/components/ChatComponents.test.tsx
- FAIL __tests__/imports/internal-imports.test.tsx (6.963 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (10.536 s)
- FAIL __tests__/system/startup.test.tsx (13.1 s)
- FAIL __tests__/components/chat/MainChat.test.tsx (13.828 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (27.061 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (53.227 s)
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/hooks/useKeyboardShortcuts.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/ChatWindow.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/CorpusAdmin.test.tsx (5.049 s)
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/components/AppWithLayout.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx (5.21 s)
- FAIL __tests__/integration/advanced-integration.test.tsx (5.385 s)
- FAIL __tests__/auth/context.test.tsx (5.784 s)
- FAIL __tests__/components/ChatComponents.test.tsx
- FAIL __tests__/imports/internal-imports.test.tsx (6.963 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (10.536 s)
- FAIL __tests__/system/startup.test.tsx (13.1 s)
- FAIL __tests__/components/chat/MainChat.test.tsx (13.828 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (27.061 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (53.227 s)


---
*Generated by Netra AI Unified Test Runner v3.0*
