# Issue #785 Test Execution Guide - React Error #438

## Overview

This guide provides comprehensive instructions for executing tests related to Issue #785 (React Error #438) - the incorrect use of `React.use()` with Promise-based parameters in Next.js 15.

## Problem Summary

**Root Cause**: Line 41 in `/frontend/app/chat/[threadId]/page.tsx` uses `React.use(params)` where `params` is a Promise in Next.js 15, but React.use() expects a synchronous value.

**Error**: `Cannot read properties of undefined (reading 'threadId')` or similar React.use() related errors.

## Test Files Created

### 1. Unit Tests (Priority 1) - MUST FAIL FIRST
```
frontend/__tests__/unit/chat/thread-page-params.test.tsx
frontend/__tests__/unit/chat/react-use-params-fix.test.tsx
```

### 2. Integration Tests (Priority 2)  
```
frontend/__tests__/integration/chat-thread-navigation.test.tsx
```

### 3. E2E Tests (Priority 3)
```
tests/e2e/chat-thread-navigation.test.ts
```

## Test Execution Commands

### Running Unit Tests (Failing)
```bash
# Run specific failing test for React.use() issue
npm run test:unit -- --testNamePattern="React Error #438 Reproduction"

# Run all thread page parameter tests
npm run test:unit -- __tests__/unit/chat/thread-page-params.test.tsx

# Run React.use() fix demonstration tests
npm run test:unit -- __tests__/unit/chat/react-use-params-fix.test.tsx
```

### Running Integration Tests
```bash
# Run chat thread navigation integration tests
npm run test:integration -- __tests__/integration/chat-thread-navigation.test.tsx

# Run with verbose output to see failure details
npm run test:integration -- --verbose __tests__/integration/chat-thread-navigation.test.tsx
```

### Running E2E Tests (Staging GCP)
```bash
# Run E2E tests against staging environment
npm run e2e:test -- tests/e2e/chat-thread-navigation.test.ts

# Run with UI for debugging
npm run e2e:test:ui -- tests/e2e/chat-thread-navigation.test.ts

# Run with headed browser for visual debugging
npm run e2e:test:headed -- tests/e2e/chat-thread-navigation.test.ts
```

## Expected Test Results

### BEFORE Fix Implementation

**Unit Tests**: ❌ **SHOULD FAIL**
```
FAIL __tests__/unit/chat/thread-page-params.test.tsx
  ● React Error #438 Reproduction › should FAIL with React.use() when params is a Promise
    Cannot read properties of undefined (reading 'threadId')
```

**Integration Tests**: ❌ **SHOULD FAIL**  
```
FAIL __tests__/integration/chat-thread-navigation.test.tsx
  ● FAILING SCENARIOS - Promise Params › should FAIL to navigate with Promise-based params
    React.use() error detected
```

**E2E Tests**: ❌ **SHOULD FAIL**
```
FAIL tests/e2e/chat-thread-navigation.test.ts
  ● should FAIL when navigating directly to thread URL
    Error boundary visible - React.use() error occurred
```

### AFTER Fix Implementation

**Unit Tests**: ✅ **SHOULD PASS**
```
PASS __tests__/unit/chat/react-use-params-fix.test.tsx
  ● CORRECT IMPLEMENTATION › should handle Promise params correctly
    ✓ Thread content rendered successfully
```

**Integration Tests**: ✅ **SHOULD PASS**
```
PASS __tests__/integration/chat-thread-navigation.test.tsx
  ● Thread Loading Flow Integration › should transition to loading state
    ✓ Navigation flow completed successfully
```

**E2E Tests**: ✅ **SHOULD PASS**
```
PASS tests/e2e/chat-thread-navigation.test.ts
  ● User Experience Flow › should maintain thread context during navigation
    ✓ Thread navigation working in staging environment
```

## Test Categories & Strategy

### 1. **Failure Reproduction Tests** (Critical)
- **Purpose**: Demonstrate the exact React Error #438 scenario
- **Files**: `thread-page-params.test.tsx`, `react-use-params-fix.test.tsx`
- **Expected**: MUST FAIL before fix, PASS after fix
- **Commands**:
  ```bash
  npm run test:unit -- --testNamePattern="FAILING.*React.use"
  ```

### 2. **Fix Validation Tests** (Critical)
- **Purpose**: Validate the correct implementation approach
- **Files**: `react-use-params-fix.test.tsx`
- **Expected**: Show correct vs incorrect patterns
- **Commands**:
  ```bash
  npm run test:unit -- --testNamePattern="CORRECT IMPLEMENTATION"
  ```

### 3. **Integration Flow Tests** (Important)
- **Purpose**: Test complete navigation flow with real components
- **Files**: `chat-thread-navigation.test.tsx`
- **Expected**: Comprehensive user journey validation
- **Commands**:
  ```bash
  npm run test:integration -- --testNamePattern="Thread Loading Flow"
  ```

### 4. **E2E User Journey Tests** (Validation)
- **Purpose**: Test real user scenarios in staging environment
- **Files**: `chat-thread-navigation.test.ts`
- **Expected**: Production-like environment validation
- **Commands**:
  ```bash
  npm run e2e:test -- --grep "Chat Thread Navigation E2E"
  ```

## Fix Implementation Guide

### Current Code (BROKEN - Line 41):
```typescript
const ThreadPage: React.FC<ThreadPageProps> = ({ params }) => {
  const { threadId } = React.use(params); // ❌ FAILS - params is Promise
  // ... rest of component
};
```

### Fixed Code (Option 1 - useEffect):
```typescript
const ThreadPage: React.FC<ThreadPageProps> = ({ params }) => {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    params.then(({ threadId }) => {
      setThreadId(threadId);
      setLoading(false);
    });
  }, [params]);
  
  if (loading) return <LoadingComponent />;
  if (!threadId) return <ErrorComponent />;
  
  // ... rest of component with threadId
};
```

### Fixed Code (Option 2 - Suspense):
```typescript
const ThreadPageContent: React.FC<ThreadPageProps> = ({ params }) => {
  const { threadId } = use(params); // ✅ WORKS in Suspense
  // ... rest of component
};

const ThreadPage: React.FC<ThreadPageProps> = ({ params }) => {
  return (
    <Suspense fallback={<LoadingComponent />}>
      <ThreadPageContent params={params} />
    </Suspense>
  );
};
```

## Test Validation Checklist

### Before Starting Fix:
- [ ] All unit tests FAIL with React.use() errors
- [ ] Integration tests FAIL with Promise handling
- [ ] E2E tests show error boundaries or loading failures
- [ ] Console shows React Error #438 or similar

### After Implementing Fix:
- [ ] Unit tests PASS with correct parameter handling
- [ ] Integration tests PASS with smooth navigation flow
- [ ] E2E tests PASS with real user scenarios
- [ ] No React.use() errors in console
- [ ] Thread navigation works in staging environment

## Debugging Failed Tests

### Common Issues:

1. **Tests not failing as expected**:
   ```bash
   # Check if mocks are interfering
   npm run test:unit -- --clearCache
   npm run test:unit -- --no-cache __tests__/unit/chat/thread-page-params.test.tsx
   ```

2. **E2E tests timing out**:
   ```bash
   # Run with increased timeout
   npm run e2e:test:headed -- --timeout=60000 tests/e2e/chat-thread-navigation.test.ts
   ```

3. **Integration tests not finding components**:
   ```bash
   # Check component rendering with debug
   npm run test:integration -- --verbose --no-coverage
   ```

### Useful Debug Commands:

```bash
# See detailed test output
npm run test:unit -- --verbose --no-coverage

# Run specific test with full error details  
npm run test:unit -- --testNamePattern="should FAIL with React.use" --verbose

# Check staging environment connectivity
npm run e2e:test:debug -- tests/e2e/chat-thread-navigation.test.ts
```

## Environment Setup

### For Unit/Integration Tests:
```bash
# Install dependencies
npm install

# Clear Jest cache if needed
npm run test:clear-cache

# Run tests
npm run test:unit
```

### For E2E Tests:
```bash
# Set staging environment variables
export STAGING_BASE_URL=https://netra-staging.example.com
export STAGING_TEST_USER_EMAIL=test-user@netra.dev
export STAGING_TEST_USER_PASSWORD=test-password

# Install Playwright if needed
npx playwright install

# Run E2E tests
npm run e2e:test
```

## Success Metrics

### Test Coverage:
- **Unit Tests**: 100% coverage of React.use() error scenarios
- **Integration Tests**: Complete navigation flow coverage
- **E2E Tests**: Real user journey validation

### Performance:
- **Unit Tests**: < 5 seconds execution time
- **Integration Tests**: < 30 seconds execution time  
- **E2E Tests**: < 2 minutes execution time

### Business Value:
- ✅ Users can navigate to thread URLs without errors
- ✅ Browser refresh works correctly on thread pages
- ✅ Back/forward navigation maintains thread context
- ✅ Thread loading states provide clear user feedback

## Next Steps

1. **Run failing tests** to confirm issue reproduction
2. **Implement fix** using one of the suggested approaches
3. **Re-run tests** to verify fix effectiveness
4. **Deploy to staging** and validate with E2E tests
5. **Monitor production** for React.use() error reduction

---

*Generated for Issue #785 - React Error #438 Test Strategy*