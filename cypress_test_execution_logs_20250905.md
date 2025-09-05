# Cypress Test Execution Logs Report
## Date: 2025-09-05
## Time: 12:18-12:23 UTC

## Command Executed
```bash
cd frontend && npm run cypress:run
```

## Initial Cypress Run Output
```
> netra-frontend-apex-v1@0.1.0 cypress:run
> cypress run --headless

================================================================================

  (Run Starting)

  ┌────────────────────────────────────────────────────────────────────────────────────────────────┐
  │ Cypress:        14.5.4                                                                         │
  │ Browser:        Electron 130 (headless)                                                        │
  │ Node Version:   v22.19.0 (/usr/local/bin/node)                                                 │
  │ Specs:          127 found (agent-feedback-retry-recovery.cy.ts, agent-handoff-supervisor-recov │
  │                 ery.cy.ts, agent-interaction-flow.cy.ts, agent-optimization-workflow.cy.ts, ag │
  │                 ent-workflow-websockets.cy.ts, apex_optimizer_agent_v3.cy.ts, auth-alignment-t │
  │                 est.cy.ts, auth-lifecycl...)                                                   │
  │ Searched:       cypress/e2e/**/*.{js,jsx,ts,tsx}                                               │
  │ Experiments:    experimentalMemoryManagement=true                                              │
  └────────────────────────────────────────────────────────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────────────────────────────────────────
                                                                                                    
  Running:  agent-feedback-retry-recovery.cy.ts                                           (1 of 127)

  Agent Communication Resilience
    User Experience During System Issues
      1) should handle user requests gracefully when backend services are temporarily unavailable
      2) should provide helpful feedback and recovery options when system is busy

We detected that the Electron Renderer process just crashed.

We have failed the current spec but will continue running the next spec.

This can happen for a number of different reasons.

If you're running lots of tests on a memory intense application.
  - Try increasing the CPU/memory on the machine you're running on.
  - Try enabling experimentalMemoryManagement in your config file.
  - Try lowering numTestsKeptInMemory in your config file during 'cypress open'.

You can learn more here:

https://on.cypress.io/renderer-process-crashed
```

## Docker Status Logs (Before Test)
```
2025-09-05 12:18:58 | INFO | ✅ Using existing development containers with 6 services
2025-09-05 12:18:58 | INFO | ✅ Environment 'netra-dev-existing' started successfully
2025-09-05 12:18:58 | INFO | Available ports: {'frontend': 3000, 'backend': 8000, 'auth': 8081, 'postgres': 5433, 'redis': 6380, 'clickhouse': 8124}
2025-09-05 12:18:59 | INFO | ✅ All services are healthy
```

## Critical Auth Flow Test Logs
```
DevTools listening on ws://127.0.0.1:56615/devtools/browser/a21bcad2-2066-4238-a923-467f3ed45420
Opening `/dev/tty` failed (6): Device not configured

================================================================================

  (Run Starting)

  ┌────────────────────────────────────────────────────────────────────────────────────────────────┐
  │ Cypress:        14.5.4                                                                         │
  │ Browser:        Electron 130 (headless)                                                        │
  │ Node Version:   v22.19.0 (/usr/local/bin/node)                                                 │
  │ Specs:          1 found (critical-auth-flow.cy.ts)                                             │
  │ Searched:       cypress/e2e/critical-auth-flow.cy.ts                                           │
  │ Experiments:    experimentalMemoryManagement=true                                              │
  └────────────────────────────────────────────────────────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────────────────────────────────────────
                                                                                                    
  Running:  critical-auth-flow.cy.ts                                                        (1 of 1)

  Critical Authentication Flow - UnifiedAuthService
    1) should display login page with correct authentication UI based on environment
    2) should redirect unauthenticated users from protected routes
    3) should handle authentication state with current token structure
    4) should handle authentication loading states and development login flow
    5) should handle authentication callback flow with current error handling
    6) should handle logout flow with current auth structure and WebSocket cleanup
    7) should handle WebSocket authentication endpoints if implemented

  0 passing (14s)
  7 failing

  1) Critical Authentication Flow - UnifiedAuthService
       should display login page with correct authentication UI based on environment:
     CypressError: Timed out retrying after 10000ms: `cy.wait()` timed out waiting `10000ms` for the 1st request to the route: `getPublicConfig`. No request ever occurred.
```

## Connection Failure Logs
```
  2) Critical Authentication Flow - UnifiedAuthService
       should redirect unauthenticated users from protected routes:
     CypressError: `cy.visit()` failed trying to load:

http://localhost:3000/chat

We attempted to make an http request to this URL but the request failed without a response.

We received this error at the network level:

  > Error: connect ECONNREFUSED 127.0.0.1:3000

Common situations why this would fail:
  - you don't have internet access
  - you forgot to run / boot your web server
  - your web server isn't accessible
  - you have weird network configuration settings on your computer
```

## Docker Status After Test Failures
```
2025-09-05 12:21:49 | ERROR | ❌ Docker is not running
```

## System Environment Details
- **Platform**: macOS (Darwin 24.6.0)
- **Node Version**: v22.19.0
- **Cypress Version**: 14.5.4
- **Browser**: Electron 130 (headless)
- **Working Directory**: /Users/anthony/Documents/GitHub/netra-apex

## Log Sources Identified
1. **Cypress Runner**: All test execution logs come from `npx cypress run` command
2. **Docker Manager**: Logs from `python scripts/docker_manual.py` using UnifiedDockerManager
3. **DevTools**: Browser DevTools listening on various WebSocket ports (auto-generated)
4. **System Errors**: macOS `/dev/tty` configuration warnings

## Key Infrastructure Issues
1. Docker containers stop during Cypress test execution
2. Electron renderer process crashes due to memory issues
3. Network connectivity failures (ECONNREFUSED) to localhost:3000
4. WebSocket connection instability

## Configuration Analysis
- **Base URL**: http://localhost:3000 (configured in cypress.config.ts:31)
- **Backend URL**: http://localhost:8000
- **Auth URL**: http://localhost:8081
- **Memory Management**: Enabled (experimentalMemoryManagement=true)
- **Tests Kept In Memory**: 1 (numTestsKeptInMemory=1)