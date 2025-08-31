# Jest Timeout Configuration - SSOT

This directory contains the centralized configuration for Jest test timeouts, implementing a Single Source of Truth (SSOT) pattern.

## Problem Solved

Previously, test files had:
- Duplicate `jest.setTimeout()` calls in the same function
- Inconsistent timeout values across similar test types
- No clear standard for what timeout to use when

## Solution

### 1. Centralized Configuration
All timeout values are defined in `test-timeouts.ts`:
- `TEST_TIMEOUTS.DEFAULT` (10s) - Standard tests
- `TEST_TIMEOUTS.UNIT` (5s) - Fast unit tests
- `TEST_TIMEOUTS.INTEGRATION` (15s) - Integration tests
- `TEST_TIMEOUTS.E2E` (30s) - End-to-end tests
- `TEST_TIMEOUTS.WEBSOCKET` (10s) - WebSocket tests
- And more...

### 2. Usage Patterns

#### In Test Files
```typescript
import { TEST_TIMEOUTS, setTestTimeout } from '@/__tests__/config/test-timeouts';

describe('My Test Suite', () => {
  // Set timeout for entire suite
  beforeAll(() => {
    setTestTimeout(TEST_TIMEOUTS.INTEGRATION);
  });
  
  // Or at the top of the describe block
  setTestTimeout(TEST_TIMEOUTS.WEBSOCKET);
});
```

#### With Anti-Hang Utilities
```typescript
import { setupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { TEST_TIMEOUTS } from '@/__tests__/config/test-timeouts';

describe('WebSocket Tests', () => {
  // Anti-hang automatically sets the timeout
  setupAntiHang(TEST_TIMEOUTS.WEBSOCKET);
});
```

#### Individual Test Timeout
```typescript
import { testWithTimeout, TEST_TIMEOUTS } from '@/__tests__/config/test-timeouts';

testWithTimeout(
  'should handle large data processing',
  async () => {
    // test code
  },
  TEST_TIMEOUTS.PERFORMANCE
);
```

### 3. Global Default
The global default timeout is set in `jest.setup.js` using:
```javascript
const { setupGlobalTestTimeout } = require('./__tests__/config/test-timeouts');
setupGlobalTestTimeout(); // Sets to TEST_TIMEOUTS.DEFAULT (10s)
```

## Migration

To migrate existing tests:
1. Remove all duplicate `jest.setTimeout()` calls
2. Import the appropriate helpers from `test-timeouts.ts`
3. Use `setupAntiHang()` with the appropriate timeout constant
4. Or use `setTestTimeout()` at the suite level

A migration script is available at `scripts/refactor-jest-timeouts.js`

## Benefits

1. **No Duplication**: Single timeout definition per test suite
2. **Consistency**: Same timeout for similar test types
3. **Maintainability**: Change timeouts in one place
4. **Clarity**: Named constants indicate test type expectations
5. **Performance**: Prevents accidentally long timeouts