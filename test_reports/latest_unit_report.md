# Netra AI Platform - Test Report

**Generated:** 2025-08-11T14:20:42.647631  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Summary

| Component | Status | Duration | Exit Code |
|-----------|--------|----------|-----------|
| Backend   | [FAILED] | 8.61s | 2 |
| Frontend  | [FAILED] | 48.06s | 1 |

**Overall Status:** [FAILED]  
**Total Duration:** 56.67s  
**Final Exit Code:** 2

## Test Level Details

- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 360s
- **Coverage Enabled:** No

## Configuration

### Backend Args
```
--category unit -v
```

### Frontend Args  
```
--category unit
```

## Test Output

### Backend Output
```
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: unit
  Parallel: disabled
  Coverage: disabled
  Fail Fast: disabled
  Environment: testing

Running command:
  pytest app/tests/services app/tests/core -vv --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
[1mcollecting ... [0mcollected 1182 items / 1 error

=================================== ERRORS ====================================
[31m[1m_____________ ERROR collecting tests/services/test_mcp_service.py _____________[0m
[31mImportError while importing test module 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\tests\services\test_mcp_service.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
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
..\..\..\..\miniconda3\Lib\site-packages\_pytest\assertion\rewrite.py:186: in exec_module
    exec(co, module.__dict__)
app\tests\services\test_mcp_service.py:11: in <module>
    from app.services.mcp_service import MCPService, MCPMessage, MCPProtocol, MCPError
E   ImportError: cannot import name 'MCPMessage' from 'app.services.mcp_service' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\services\mcp_service.py)[0m
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m app\tests\services\test_mcp_service.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
[31m============================== [31m[1m1 error[0m[31m in 1.51s[0m[31m ===============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 7.72s
================================================================================


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

PASS __tests__/components/chat/MessageItem.test.tsx
PASS __tests__/components/chat/PersistentResponseCard.test.tsx
PASS __tests__/auth/components.test.tsx
FAIL __tests__/hooks/useChatWebSocket.test.ts
  ● useChatWebSocket › should initialize with default state

    expect(received).toBe(expected) // Object.is equality

    Expected: "function"
    Received: "undefined"

    [0m [90m 63 |[39m     expect(result[33m.[39mcurrent[33m.[39merrors)[33m.[39mtoEqual([])[33m;[39m
     [90m 64 |[39m     expect(result[33m.[39mcurrent[33m.[39mworkflowProgress[33m.[39mcurrent_step)[33m.[39mtoBe([35m0[39m)[33m;[39m
    [31m[1m>[22m[39m[90m 65 |[39m     expect([36mtypeof[39m result[33m.[39mcurrent[33m.[39mregisterTool)[33m.[39mtoBe([32m'function'[39m)[33m;[39m
     [90m    |[39m                                                [31m[1m^[22m[39m
     [90m 66 |[39m     expect([36mtypeof[39m result[33m.[39mcurrent[33m.[39mexecuteTool)[33m.[39mtoBe([32m'function'[39m)[33m;[39m
     [90m 67 |[39m   })[33m;[39m
     [90m 68 |[39m[0m

      at Object.toBe (__tests__/hooks/useChatWebSocket.test.ts:65:48)

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
     [90m 148 |[39m ...(truncated)
```

---
*Generated by Netra AI Unified Test Runner*
