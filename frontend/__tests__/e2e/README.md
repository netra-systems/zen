# End-to-End (E2E) Testing for Netra Apex

## Overview

This directory contains comprehensive E2E tests for Netra Apex frontend, implementing production-ready test scenarios that validate critical user journeys and performance requirements.

## Business Value Justification (BVJ)

- **Segment**: All (Free → Enterprise)
- **Goal**: Prevent revenue loss from bugs, increase conversion through reliability
- **Value Impact**: 20% reduction in customer churn due to bugs
- **Revenue Impact**: +$50K MRR from improved reliability and trust

## Test Coverage

### Critical Path Tests (P0)

#### 1. Complete Conversation Flow (`complete-conversation.test.tsx`)
- **Purpose**: Tests end-to-end user journey from login to logout
- **Coverage**: Authentication → Thread Creation → Messaging → Persistence → Logout
- **Performance**: Complete flow must finish under 30 seconds
- **Key Validations**:
  - WebSocket connection establishment < 1s
  - Message delivery confirmation
  - AI response streaming < 2s
  - 60 FPS performance maintenance
  - Memory leak prevention
  - Network interruption recovery

#### 2. Multi-Tab Synchronization (`multi-tab-sync.test.tsx`)
- **Purpose**: Tests real-time state synchronization across browser tabs
- **Coverage**: Thread sync, message sync, deletion sync, concurrent operations
- **Performance**: Synchronization must complete within 5 seconds
- **Key Validations**:
  - New threads appear in all tabs
  - Messages sync in real-time
  - Thread deletions propagate
  - Concurrent message handling
  - State persistence across tab navigation

#### 3. Performance Load Testing (`performance-load.test.tsx`)
- **Purpose**: Tests application performance under heavy load conditions
- **Coverage**: 1000+ threads, 10000+ messages, rapid interactions
- **Performance**: Must maintain responsiveness and smooth operation
- **Key Validations**:
  - Thread switching < 500ms
  - Smooth scrolling (60 FPS)
  - Memory usage < 500MB
  - No performance degradation under load
  - Data integrity maintenance

## Test Architecture

### Helper Utilities (`utils/e2e-test-helpers.ts`)

Provides reusable functions following 8-line function rule:

```typescript
// Authentication
authenticateUser(page: Page, user?: TestUser): Promise<TestUser>
waitForWebSocketConnection(page: Page): Promise<void>

// Messaging
createThread(page: Page, name?: string): Promise<string>
sendMessage(page: Page, message: string): Promise<void>
waitForAIResponse(page: Page): Promise<void>

// Performance
measurePagePerformance(page: Page): Promise<PerformanceThresholds>
validatePerformance(metrics, thresholds): void

// Network Simulation
simulateNetworkCondition(page: Page, condition): Promise<void>
```

### Configuration (`playwright.config.ts`)

- **Browsers**: Chrome, Firefox, Safari, Mobile Chrome, Mobile Safari
- **Timeouts**: 30s per test, 10s per action
- **Retries**: 1 (local), 2 (CI)
- **Workers**: 4 (local), 2 (CI)
- **Reports**: HTML, JSON, JUnit

## Running Tests

### Local Development

```bash
# Install Playwright browsers (first time)
npx playwright install

# Run all E2E tests
npm run e2e:test

# Run tests with UI (interactive)
npm run e2e:test:ui

# Run tests in headed mode (visible browser)
npm run e2e:test:headed

# Debug specific test
npm run e2e:test:debug -- complete-conversation
```

### CI/CD Integration

Tests run automatically in GitHub Actions with:
- Cross-browser testing
- Performance regression detection
- Screenshot/video capture on failure
- Test result reporting

## Performance Targets

### Response Time Targets
- **WebSocket Connection**: < 1 second
- **Thread Creation**: < 200ms
- **Message Delivery**: < 3 seconds
- **AI Response Start**: < 2 seconds
- **Complete Flow**: < 30 seconds

### Performance Thresholds
- **Frame Rate**: > 55 FPS (target 60 FPS)
- **Memory Usage**: < 500MB
- **Thread Switching**: < 500ms
- **Memory Growth**: < 50MB per extended session

## Test Data Patterns

### User Generation
```typescript
const testUser = createTestUser('suffix');
// Creates unique user: test-{timestamp}{suffix}@netrasystems.ai
```

### Message Patterns
```typescript
const messages = generateTestMessages(100, 'Load Test');
// Creates: ["Load Test message 1", "Load Test message 2", ...]
```

### Performance Monitoring
```typescript
const metrics = await measurePagePerformance(page);
validatePerformance(metrics, {
  maxResponseTime: 2000,
  maxMemoryMB: 500,
  minFrameRate: 55
});
```

## Error Handling

### Network Resilience
- Offline mode simulation
- Connection interruption recovery
- Automatic reconnection testing
- Message queue validation

### Session Management
- Token expiration handling
- Session timeout recovery
- Multi-tab authentication sync
- Cleanup validation

## Debugging

### Common Issues

1. **WebSocket Connection Failures**
   ```bash
   # Check connection status indicator
   await expect(page.locator('[data-testid="connection-status"]'))
     .toContainText('Connected');
   ```

2. **Performance Degradation**
   ```bash
   # Monitor frame rate
   const frameRate = await monitorFrameRate(page);
   expect(frameRate).toBeGreaterThan(55);
   ```

3. **Memory Leaks**
   ```bash
   # Measure memory growth
   const metrics = await measurePagePerformance(page);
   expect(metrics.maxMemoryMB).toBeLessThan(500);
   ```

### Debug Mode

```bash
# Run specific test with debug mode
npm run e2e:test:debug -- --grep "conversation flow"

# Set breakpoints in test code
await page.pause(); // Opens Playwright Inspector
```

## Test Maintenance

### Function Size Compliance
- Every function ≤ 8 lines (MANDATORY)
- Every file ≤ 300 lines (MANDATORY)
- Clear single responsibility per function

### Type Safety
- Full TypeScript typing
- Interfaces for all test data
- Strong typing for helper functions

### Code Quality
- No test stubs in production
- Real implementations only
- Comprehensive error handling

## Monitoring and Reporting

### Metrics Tracked
- Test execution time trends
- Performance regression detection
- Cross-browser compatibility
- Memory usage patterns

### Success Criteria
- ✅ 100% critical path coverage
- ✅ All tests complete < 30 seconds
- ✅ No flaky tests (100% reliability)
- ✅ Performance targets met
- ✅ Zero production bugs in tested paths

## Integration with Existing Tests

### Relationship to Jest Tests
- E2E tests complement unit/integration tests
- Focus on user journeys vs implementation details
- Shared test utilities where appropriate

### Relationship to Cypress Tests
- Playwright E2E tests run in parallel with Cypress
- Playwright focuses on performance and multi-tab scenarios
- Both test suites validate different aspects

## Future Enhancements

### Planned Additions
- Visual regression testing
- Accessibility validation
- Mobile-specific scenarios
- API mocking for isolated testing

### Performance Improvements
- Test parallelization optimization
- Smart test selection based on changes
- Performance benchmark tracking

This E2E test suite ensures Netra Apex delivers reliable, high-performance user experiences across all critical workflows, directly protecting and enabling revenue growth.