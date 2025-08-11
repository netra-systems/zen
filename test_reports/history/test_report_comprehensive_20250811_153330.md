# Netra AI Platform - Test Report

**Generated:** 2025-08-11T15:33:30.265938  
**Test Level:** comprehensive - Full test suite with coverage (10-15 minutes)  
**Purpose:** Pre-release validation, full system testing

## Test Summary

**Total Tests:** 250  
**Passed:** 15  
**Failed:** 234  
**Skipped:** 0  
**Errors:** 1  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 1 | 0 | 0 | 0 | 1 | 35.06s | [FAILED] |
| Frontend  | 249 | 15 | 234 | 0 | 0 | 58.77s | [FAILED] |

## Environment and Configuration

- **Test Level:** comprehensive
- **Description:** Full test suite with coverage (10-15 minutes)
- **Purpose:** Pre-release validation, full system testing
- **Timeout:** 900s
- **Coverage Enabled:** Yes
- **Total Duration:** 93.83s
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
[31m[1m_____ ERROR collecting tests/database/test_repositories_comprehensive.py ______[0m
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
..\..\..\..\miniconda3\Lib\site-packages\_pytest\assertion\rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\miniconda3\Lib\site-packages\_pytest\assertion\rewrite.py:357: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\miniconda3\Lib\ast.py:52: in parse
    return compile(source, filename, mode, flags,
E     File "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\database\test_repositories_comprehensive.py", line 530
E       # Test 84 and 85 removed - cache_service and session_service don't exist
E   SyntaxError: invalid syntax
- Generated html report: file:///C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/reports/tests/report.html -
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m app\tests\database\test_repositories_comprehensive.py
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m============================== [31m[1m1 error[0m[31m in 24.77s[0m[31m ==============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 34.16s

[Report] HTML Report: reports/tests/report.html
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================


```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> jest --coverage --coverageDirectory=../reports/frontend-coverage

---------------------------------|---------|----------|---------|---------|---------------------------------------------------------------------------------------------------
File                             | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s                                                                                 
---------------------------------|---------|----------|---------|---------|---------------------------------------------------------------------------------------------------
All files                        |   64.72 |    81.62 |   49.62 |   64.72 |                                                                                                   
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
- =================================== ERRORS ====================================
- [31m[1m_____ ERROR collecting tests/database/test_repositories_comprehensive.py ______[0m
- [31mERROR[0m app\tests\database\test_repositories_comprehensive.py
- [FAIL] TESTS FAILED with exit code 2 after 34.16s

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/hooks/useKeyboardShortcuts.test.tsx
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/components/ChatWindow.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/CorpusAdmin.test.tsx
- FAIL __tests__/components/ChatComponents.test.tsx
- FAIL __tests__/components/AppWithLayout.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx (5.052 s)
- FAIL __tests__/components/AdminChat.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/auth/context.test.tsx (5.519 s)
- FAIL __tests__/imports/external-imports.test.tsx (5.733 s)
- FAIL __tests__/imports/internal-imports.test.tsx (7.128 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (10.857 s)
- FAIL __tests__/system/startup.test.tsx (12.608 s)
- FAIL __tests__/components/chat/MainChat.test.tsx (13.365 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (26.817 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (52.307 s)
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/hooks/useKeyboardShortcuts.test.tsx
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/components/ChatWindow.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/CorpusAdmin.test.tsx
- FAIL __tests__/components/ChatComponents.test.tsx
- FAIL __tests__/components/AppWithLayout.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx (5.052 s)
- FAIL __tests__/components/AdminChat.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/auth/context.test.tsx (5.519 s)
- FAIL __tests__/imports/external-imports.test.tsx (5.733 s)
- FAIL __tests__/imports/internal-imports.test.tsx (7.128 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (10.857 s)
- FAIL __tests__/system/startup.test.tsx (12.608 s)
- FAIL __tests__/components/chat/MainChat.test.tsx (13.365 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (26.817 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (52.307 s)


---
*Generated by Netra AI Unified Test Runner v3.0*
