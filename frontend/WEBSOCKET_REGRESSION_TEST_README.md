# WebSocket Agent Response Regression Tests

## Overview
This test suite ensures that the critical bug where `agent_response` WebSocket messages were not displayed in the UI never resurfaces.

## Background
**Critical Bug Fixed**: Frontend was missing a handler for `agent_response` messages, causing agent responses to not display in the chat UI. This was a HIGH severity issue affecting core chat functionality.

## Test Coverage

### 1. Unit Tests (`__tests__/websocket-agent-response-handler.test.ts`)
- Tests `extractAgentResponseData` function with various payload formats
- Tests `createAgentResponseMessage` function 
- Tests `handleAgentResponse` event handler
- Verifies handler registration in event registry

### 2. Integration Tests (`__tests__/websocket-message-alignment.test.ts`)
- Ensures ALL backend message types have frontend handlers
- Specifically verifies `agent_response` handler exists
- Checks handler aliases and backward compatibility
- Prevents new message types from being added without handlers

### 3. E2E Tests (`cypress/e2e/websocket-agent-response-regression.cy.ts`)
- Tests actual UI display of agent responses
- Tests multiple response formats
- Tests rapid message handling
- Tests connection recovery scenarios

## Running the Tests

### Run All Regression Tests
```bash
npm run test:websocket-regression
```

### Run Individual Test Suites
```bash
# Unit tests only
npm test -- __tests__/websocket-agent-response-handler.test.ts

# Integration tests only  
npm test -- __tests__/websocket-message-alignment.test.ts

# E2E tests only
npm run cypress:run -- --spec "cypress/e2e/websocket-agent-response-regression.cy.ts"
```

## Critical Checks

The regression suite verifies:

1. ✅ `handleAgentResponse` function exists in `websocket-agent-handlers.ts`
2. ✅ `agent_response` is registered in `websocket-event-handlers-main.ts`
3. ✅ Agent responses display in the chat UI
4. ✅ No console errors about unknown message types
5. ✅ All payload formats are handled correctly

## When to Run

**MUST run these tests:**
- Before any deployment
- After modifying WebSocket handlers
- After updating frontend message handling
- When adding new message types
- During CI/CD pipeline

## Expected Output

```
[SUCCESS] All Regression Tests Passed! 🎉
✓ Agent response handler is properly implemented
✓ Frontend can handle all backend message types  
✓ Agent responses display correctly in UI
```

## If Tests Fail

1. Check that `handleAgentResponse` exists in `frontend/store/websocket-agent-handlers.ts`
2. Verify `agent_response` is registered in `frontend/store/websocket-event-handlers-main.ts`
3. Ensure the handler is properly exported and imported
4. Check for TypeScript errors in handler functions
5. Review the error logs for specific failure details

## Prevention Strategy

To prevent similar issues:
1. Always add frontend handlers for new backend message types
2. Run alignment tests when modifying WebSocket communication
3. Add console warnings for unknown message types
4. Maintain comprehensive test coverage for all message types

## Related Documentation

- Bug Report: `WEBSOCKET_AGENT_RESPONSE_ISSUE_REPORT.md`
- Learning: `SPEC/learnings/websocket_agent_response_missing_handler.xml`
- Architecture: `docs/websocket_architecture.md`

## Contact

For issues with these tests, check:
- Frontend WebSocket handlers: `frontend/store/websocket-*.ts`
- Backend WebSocket routes: `netra_backend/app/routes/websocket.py`
- Test files in `frontend/__tests__/` and `frontend/cypress/e2e/`