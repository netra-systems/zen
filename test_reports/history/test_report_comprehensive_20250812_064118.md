# Netra AI Platform - Test Report

**Generated:** 2025-08-12T05:10:01.694065  
**Test Level:** comprehensive - Full test suite with coverage (10-15 minutes)  
**Purpose:** Pre-release validation, full system testing

## Test Summary

**Total Tests:** 189  
**Passed:** 18  
**Failed:** 171  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 0 | 0 | 0 | 0 | 0 | 907.84s | [TIMEOUT] |
| Frontend  | 189 | 18 | 171 | 0 | 0 | 75.84s | [FAILED] |

## Environment and Configuration

- **Test Level:** comprehensive
- **Description:** Full test suite with coverage (10-15 minutes)
- **Purpose:** Pre-release validation, full system testing
- **Timeout:** 900s
- **Coverage Enabled:** Yes
- **Total Duration:** 983.68s
- **Exit Code:** 1

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
Tests timed out after 900s
```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> jest --coverage --coverageDirectory=../reports/frontend-coverage

---------------------------------|---------|----------|---------|---------|--------------------------------------------------------------------------------------------------------------
File                             | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s                                                                                            
---------------------------------|---------|----------|---------|---------|--------------------------------------------------------------------------------------------------------------
All files                        |   68.03 |    78.13 |   50.72 |   68.03 |                                                                                                              
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
 frontend/components/chat        |   77.64 |    71.95 |   74.41 |   77.64 |                                                                                                              
  ChatHeader.tsx                 |   95.89 |       60 |     100 |   95.89 | 16,19,41,43,45-46                                                                                            
  ChatSidebar.tsx                |    3.11 |      100 |       0 |    3.11 | 13-385                                                                                                       
  ChatWindow.tsx                 |     100 |      100 |     100 |     100 |                                                                                                              
  ExamplePrompts.tsx             |     100 |      100 |     100 |     100 |                                                                                                              
  MainChat.tsx                   |   96.26 |      100 |      25 |   96.26 | 54-58                                                                                                        
  MessageInput.tsx               |   93.06 |     73.8 |     100 |   93.06 | 51-53,104-105,124-129,131-140                                                                                
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
  label.tsx                      |     100 |      100 |     100 |     100 |                                                                                                              
  progress.tsx                   |   25.71 |      100 |       0 |   25.71 | 8-33                                                                                                         
  scroll-area.tsx                |   ...(truncated)
```

## Error Summary

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/utils/test-utils.tsx
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/auth/context.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx
- FAIL __tests__/imports/internal-imports.test.tsx
- FAIL __tests__/components/ChatHistorySection.test.tsx (7.828 s)
- FAIL __tests__/system/startup.test.tsx (11.856 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/components/chat/MainChat.test.tsx (12.2 s)
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (26.122 s)
- FAIL __tests__/components/ChatComponents.test.tsx (26.763 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (67.661 s)
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/utils/test-utils.tsx
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/auth/context.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx
- FAIL __tests__/imports/internal-imports.test.tsx
- FAIL __tests__/components/ChatHistorySection.test.tsx (7.828 s)
- FAIL __tests__/system/startup.test.tsx (11.856 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/components/chat/MainChat.test.tsx (12.2 s)
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (26.122 s)
- FAIL __tests__/components/ChatComponents.test.tsx (26.763 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (67.661 s)


---
*Generated by Netra AI Unified Test Runner v3.0*
