# Netra AI Platform - Test Report

**Generated:** 2025-08-11T15:26:20.707410  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 261  
**Passed:** 14  
**Failed:** 247  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 0 | 0 | 0 | 0 | 0 | 120.03s | [TIMEOUT] |
| Frontend  | 261 | 14 | 247 | 0 | 0 | 47.96s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 167.99s
- **Exit Code:** 1

### Backend Configuration
```
--category unit -v --coverage
```

### Frontend Configuration
```
--category unit
```

## Test Output

### Backend Output
```
Tests timed out after 120s
```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> jest __tests__/unit components/**/*.test.tsx hooks/**/*.test.ts

  Invalid testPattern __tests__/unit|components/**/*.test.tsx|hooks/**/*.test.ts supplied. Running all tests instead.
  Invalid testPattern __tests__/unit|components/**/*.test.tsx|hooks/**/*.test.ts supplied. Running all tests instead.
================================================================================
NETRA AI PLATFORM - FRONTEND TEST RUNNER
================================================================================

================================================================================
Running Jest Tests
--------------------------------------------------------------------------------
Running: npm run test -- __tests__/unit components/**/*.test.tsx hooks/**/*.test.ts
--------------------------------------------------------------------------------

================================================================================
[FAIL] CHECKS FAILED with exit code 1
================================================================================

FAIL __tests__/hooks/useChatWebSocket.test.ts
  ● useChatWebSocket › should handle agent_started message

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: true

    Number of calls: 0

    [0m [90m 81 |[39m     rerender()[33m;[39m
     [90m 82 |[39m     
    [31m[1m>[22m[39m[90m 83 |[39m     expect(mockChatStore[33m.[39msetProcessing)[33m.[39mtoHaveBeenCalledWith([36mtrue[39m)[33m;[39m
     [90m    |[39m                                         [31m[1m^[22m[39m
     [90m 84 |[39m     expect(mockUnifiedChatStore[33m.[39msetProcessing)[33m.[39mtoHaveBeenCalledWith([36mtrue[39m)[33m;[39m
     [90m 85 |[39m   })[33m;[39m
     [90m 86 |[39m[0m

      at Object.toHaveBeenCalledWith (__tests__/hooks/useChatWebSocket.test.ts:83:41)

  ● useChatWebSocket › should handle sub_agent_update message

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: "OptimizationAgent"

    Number of calls: 0

    [0m [90m 103 |[39m     rerender()[33m;[39m
     [90m 104 |[39m     
    [31m[1m>[22m[39m[90m 105 |[39m     expect(mockChatStore[33m.[39msetSubAgentName)[33m.[39mtoHaveBeenCalledWith([32m'OptimizationAgent'[39m)[33m;[39m
     [90m     |[39m                                           [31m[1m^[22m[39m
     [90m 106 |[39m     expect(mockChatStore[33m.[39msetSubAgentStatus)[33m.[39mtoHaveBeenCalledWith({
     [90m 107 |[39m       status[33m:[39m [32m'running'[39m[33m,[39m
     [90m 108 |[39m       tools[33m:[39m [[32m'analyzer'[39m[33m,[39m [32m'optimizer'[39m][0m

      at Object.toHaveBeenCalledWith (__tests__/hooks/useChatWebSocket.test.ts:105:43)

  ● useChatWebSocket › should handle agent_completed message

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: false

    Number of calls: 0

    [0m [90m 122 |[39m     rerender()[33m;[39m
     [90m 123 |[39m     
    [31m[1m>[22m[39m[90m 124 |[39m     expect(mockChatStore[33m.[39msetProcessing)[33m.[39mtoHaveBeenCalledWith([36mfalse[39m)[33m;[39m
     [90m     |[39m                                         [31m[1m^[22m[39m
     [90m 125 |[39m     expect(mockUnifiedChatStore[33m.[39msetProcessing)[33m.[39mtoHaveBeenCalledWith([36mfalse[39m)[33m;[39m
     [90m 126 |[39m     expect(mockChatStore[33m.[39maddMessage)[33m.[39mtoHaveBeenCalledWith(
     [90m 127 |[39m       expect[33m.[39mobjectContaining({[0m

      at Object.toHaveBeenCalledWith (__tests__/hooks/useChatWebSocket.test.ts:124:41)

  ● useChatWebSocket › should handle error message

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: false

    Number of calls: 0

    [0m [90m 147 |[39m     rerender()[33m;[39m
     [90m 148 |[39m     
    [31m[1m>[22m[39m[90m 149 |[39m     expect(mockChatStore[33m.[39msetProcessing)[33m.[39mtoHaveBeenCalledWith([36mfalse[39m)[33m;[39m
     [90m     |[39m                                         [31m[1m^[22m[39m
     [90m 150 |[39m     expect(mockChatStore[33m.[39maddMessage)[33m.[39mtoHaveBeenCalledWith(
     [90m 151 |[39m       expect[33m.[39mobjectContaining({
     [90m 152 |[39m         type[33m:[39m [32m'error'[39m[33m,[39m[0m

      at Object.toHaveBeenCalledWith (__tests__/hooks/useChatWebSocket.test.ts:149:41)

  ● useChatWebSocket › should handle tool_call message

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: ObjectContaining {"content": StringContaining "cost_analyzer", "type": "tool"}

    Number of calls: 0

    [0m [90m 172 |[39m     rerender()[33m;[39m
     [90m 173 |[39m     
    [31m[1m>[22m[39m[90m 174 |[39m     expect(mockChatStore[33m.[39maddMessage)[33m.[39mtoHaveBeenCalledWith(
     [90m     |[39m                                      [31m[1m^[22m[39m
     [90m 175 |[39m       expect[33m.[39mobjectContaining({
     [90m 176 |[39m         type[33m:[39m [32m'tool'[39m[33m,[39m
     [90m 177 |[39m         content[33m:[39m expect[33m.[39mstringContaining([32m'cost_analyzer'[39m)[0m

      at Object.toHaveBeenCalledWith (__tests__/hooks/useChatWebSocket.test.ts:174:38)

  ● useChatWebSocket › should register and execute tools

    expect(received).toContainEqual(expected) // deep equality

    Expected value: {"name": "test_tool", "version": "1.0"}
    Received array: []

    [0m [90m 188 |[39m     })[33m;[39m
     [90m 189 |[39m     
    [31m[1m>[22m[39m[90m 190 |[39m     expect(result[33m.[39mcurrent[33m.[39mregisteredTools)[33m.[39mtoContainEqual({ name[33m:[39m [32m'test_tool'[39m[33m,[39m version[33m:[39m [32m'1.0'[39m })[33m;[39m
     [90m     |[39m                                            [31m[1m^[22m[39m
     [90m 191 |[39m     
     [90m 192 |[39m     [90m// Execute a tool[39m
     [90m 193 |[39m     [36mlet[39m toolResult[33m;[39m[0m

      at Object.toContainEqual (__tests__/hooks/useChatWebSocket.test.ts:190:44)

  ● useChatWebSocket › should handle workflow_progress message

    expect(received).toEqual(expected) // deep equality

    - Expected  - 2
    + Received  + 2

      Object {
    -   "current_step": 3,
    -   "total_steps": 10,
    +   "current_step": 0,
    +   "total_steps": 3,
      }

    [0m [90m 215 |[39m     rerender()[33m;[39m
     [90m 216 |[39m     
    [31m[1m>[22m[39m[90m 217 |[39m     expect(result[33m.[39mcurrent[33m.[39mworkflowProgress)[33m.[39mtoEqual({
     [90m     |[39m                                             [31m[1m^[22m[39m
     [90m 218 |[39m       current_step[33m:[39m [35m3[39m[33m,[39m
     [90m 219 |[39m       total_steps[33m:[39m [35m10[39m
     [90m 220 |[39m     })[33m;[39m[0m

      at Object.toEqual (__tests__/hooks/useChatWebSocket.test.ts:217:45)

  ● useChatWebSocket › should handle message_chunk for streaming

    expect(received).toBe(expected) // Object.is equality

    Expected: "Partial response..."
    Received: ""

    [0m [90m 236 |[39m     rerender()[33m;[39m
     [90m 237 |[39m     
    [31m[1m>[22m[39m[90m 238 |[39m     expect(result[33m.[39mcurrent[33m.[39mstreamingMessage)[33m.[39mtoBe([32m'Partial response...'[39m)[33m;[39m
     [90m     |[39m                                             [31m[1m^[22m[39m
     [90m 239 |[39m     expect(result[33m.[39mcurrent[33m.[39misStreaming)[33m.[39mtoBe([36mtrue[39m)[33m;[39m
     [90m 240 |[39m   })[33m;[39m
     [90m 241 |[39m[0m

      at Object.toBe (__tests__/hooks/useChatWebSocket.test.ts:238:45)

  ● useChatWebSocket › should handle validation_result message

    expect(received).toEqual(expected) // deep equality

    - Expected  - 3
    + Received  + 1

    - Object {
    -   "memory_limit": true,
    - }
    + Object {}

    [0m [90m 255 |[39m     rerender()[33m;[39m
     [90m 256 |[39m     
    [31m[1m>[22m[39m[90m 257 |[39m     expect(result[33m.[39mcurrent[33m.[39mvalidationResults)[33m.[39mtoEqual({
     [90m     |[39m                                              [31m[1m^[22m[39m
     [90m 258 |[39m       memory_limit[33m:[39m [36mtrue[39m
     [90m 259 |[39m     })[33m;[39m
     [90m 260 |[39m   })[33m;[39m[0m

      at Object.toEqual (__tests__/hooks/useChatWebSocket.test.ts:257:46)

  ● useChatWebSocket › should handle approval_required message

    expect(received).toEqual(expected) // deep equality

    Expected: {"message": "Confirm deletion of resources", "sub_agent_name": "ResourceManager"}
    Received: null

    [0m [90m 275 |[39m     rerender()[33m;[39m
     [90m 276 |[39m     
    [31m[1m>[22m[39m[90m 277 |[39m     expect(result[33m.[39mcurrent[33m.[39mpendingApproval)[33m.[39mtoEqual({
     [90m     |[39m                                            [31m[1m^[22m[39m
     [90m 278 |[39m       message[33m:[39m [32m'Confirm deletion of resources'[39m[33m,[39m
     [90m 279 |[39m       sub_agent_name[33m:[39m [32m'ResourceManager'[39m
     [90m 280 |[39m     })[33m;[39m[0m

      at Object.toEqual (__tests__/hooks/useChatWebSocket.test.ts:277:44)

  ● useChatWebSocket › should clear errors

    expect(received).toHaveLength(expected)

    Expected length: 1
    Received length: 0
    Received array:  []

    [0m [90m 304 |[39m     rerender()[33m;[39m
     [90m 305 |[39m     
    [31m[1m>[22m[39m[90m 306 |[39m     expect(result[33m.[39mcurrent[33m.[39merrors)[33m.[39mtoHaveLength([35m1[39m)[33m;[39m
     [90m     |[39m                                   [31m[1m^[22m[39m
     [90m 307 |[39m     
     [90m 308 |[39m     [90m// Clear errors[39m
     [90m 309 |[39m     act(() [33m=>[39m {[0m

      at Object.toHaveLength (__tests__/hooks/useChatWebSocket.test.ts:306:35)

  ● useChatWebS...(truncated)
```

## Error Summary

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/hooks/useChatWebSocket.test.ts
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/hooks/useKeyboardShortcuts.test.tsx
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/ChatWindow.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/AppWithLayout.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/AdminChat.test.tsx
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/components/ChatComponents.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx
- FAIL __tests__/components/CorpusAdmin.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/auth/context.test.tsx
- FAIL __tests__/imports/internal-imports.test.tsx
- FAIL __tests__/components/ChatHistorySection.test.tsx (7.925 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/components/chat/MainChat.test.tsx (12.235 s)
- FAIL __tests__/system/startup.test.tsx (12.182 s)
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (25.473 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (42.567 s)
- FAIL __tests__/hooks/useChatWebSocket.test.ts
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/hooks/useKeyboardShortcuts.test.tsx
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/ChatWindow.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/AppWithLayout.test.tsx
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/AdminChat.test.tsx
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/components/ChatComponents.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx
- FAIL __tests__/components/CorpusAdmin.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/auth/context.test.tsx
- FAIL __tests__/imports/internal-imports.test.tsx
- FAIL __tests__/components/ChatHistorySection.test.tsx (7.925 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/components/chat/MainChat.test.tsx (12.235 s)
- FAIL __tests__/system/startup.test.tsx (12.182 s)
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (25.473 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (42.567 s)


---
*Generated by Netra AI Unified Test Runner v3.0*
