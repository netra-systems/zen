# Frontend Test Failures Report
Generated: 2025-08-28

## Test Summary
- **Total Test Suites**: 442
- **Failed Test Suites**: 289
- **Passed Test Suites**: 152
- **Skipped Test Suites**: 1
- **Total Tests**: 5,242
- **Failed Tests**: 2,411
- **Passed Tests**: 2,803
- **Skipped Tests**: 28
- **Runtime Errors**: 53 test suites

## Critical Issues

### 1. ChatHeader Component Import Issue
**Files Affected**: Multiple test files
**Error**: `Element type is invalid: expected a string (for built-in components) or a class/function (for composite components) but got: undefined`
**Root Cause**: ChatHeader component has an undefined import in its render method
**Impact**: Prevents rendering of chat-related components

### 2. WebSocketTestManager Import Issue
**Files Affected**: All WebSocket-related tests
**Error**: `TypeError: _websockettestmanager.WebSocketTestManager.createWebSocketManager is not a function`
**Root Cause**: Missing or improperly exported WebSocketTestManager utility
**Impact**: All WebSocket tests fail

### 3. Memory Leak Detection Failures
**Files Affected**: `__tests__/critical/memory-exhaustion.test.tsx`
**Issues**:
- Timers not properly cleaned up
- WebSocket connections not closed
- Component unmount cleanup issues

## Failed Test Categories

### First-Time User Tests (`initial-chat.test.tsx`)
- ❌ Shows example prompts for first-time users
- ❌ Handles message sending for first-time user
- ❌ Shows processing state when user sends first message
- ❌ Transitions from empty state to chat after first message
- ❌ Shows message input is always available for interaction
- ❌ Disables input when user is not authenticated

### Memory Exhaustion Tests (`memory-exhaustion.test.tsx`)
- ❌ Detects uncleaned intervals and timers
- ❌ Detects WebSocket connection leaks
- ❌ Recovers gracefully from memory pressure
- ❌ Verifies proper component unmount cleanup

### WebSocket Tests (Multiple Files)
All WebSocket tests failing due to missing WebSocketTestManager utility:
- `websocket-complete.test.tsx`
- `websocket-lifecycle.test.tsx`
- `websocket-messaging.test.tsx`
- `websocket-performance.test.tsx`
- `websocket-large-messages.test.tsx`
- `websocket-stress.test.tsx`
- And many more...

### Integration Tests
Many integration tests failing due to:
- Missing DOM elements (data-testid not found)
- Component rendering issues
- Async timing issues
- Authentication state problems

## Common Error Patterns

### 1. Missing Test IDs
```
Unable to find an element by: [data-testid="example-prompts"]
Unable to find an element by: [data-testid="response-card"]
Unable to find an element by: [data-testid="message-input"]
```

### 2. Component Not Rendering
Many tests show empty body content:
```html
<body>
  <div />
</body>
```
Or loading state stuck:
```html
<body>
  <div class="flex h-full items-center justify-center">
    <div>Loading chat...</div>
  </div>
</body>
```

### 3. Cleanup Issues
```javascript
TypeError: Cannot read properties of undefined (reading 'cleanup')
```

### 4. Mock Function Not Called
```
expect(jest.fn()).toHaveBeenCalled()
Expected number of calls: >= 1
Received number of calls: 0
```

## Priority Fixes

### High Priority
1. **Fix ChatHeader component import** - Blocking many tests
2. **Fix WebSocketTestManager utility** - Blocking all WebSocket tests
3. **Fix memory leak cleanup in tests** - Critical for CI/CD

### Medium Priority
4. Add missing test IDs to components
5. Fix authentication mock setup in tests
6. Fix async timing issues in integration tests

### Low Priority
7. Update snapshot tests
8. Fix warning suppressions
9. Optimize test performance

## Next Steps

1. **Immediate Actions**:
   - Check ChatHeader component exports and imports
   - Locate or recreate WebSocketTestManager utility
   - Review test cleanup hooks

2. **Investigation Needed**:
   - Why are components not rendering in tests?
   - Are there missing providers or context wrappers?
   - Are mock setups incomplete?

3. **Test Infrastructure**:
   - Review jest.setup.js configuration
   - Check test utility imports
   - Verify mock implementations

## Files to Review

### Component Files
- `components/chat/ChatHeader.tsx` - Check exports
- `components/chat/MainChat.tsx` - Check ChatHeader import
- `components/chat/ExamplePrompts.tsx` - Verify test IDs

### Test Utilities
- `__tests__/utils/WebSocketTestManager.ts` - Missing or broken
- `jest.setup.js` - Check global mocks
- Test helper files for proper exports

### Configuration
- `jest.config.unified.cjs` - Check module resolution
- `tsconfig.json` - Check path mappings

## Running Specific Test Categories

```bash
# Run only passing tests
npm test -- --testPathIgnorePatterns="initial-chat|memory-exhaustion|websocket"

# Run a specific test file
npm test -- --testPathPattern="<filename>"

# Run with coverage for passing tests only
npm test -- --coverage --testPathIgnorePatterns="initial-chat|memory-exhaustion|websocket"
```

## Environment Notes
- Tests are running in Windows environment
- Some path-related issues may be OS-specific
- Console warnings about `act()` indicate async state updates

## Tracking Progress

Use this document to track fixes:
- [ ] ChatHeader import issue resolved
- [ ] WebSocketTestManager utility fixed
- [ ] Memory leak tests passing
- [ ] First-time user tests passing
- [ ] All WebSocket tests passing
- [ ] Integration tests stabilized