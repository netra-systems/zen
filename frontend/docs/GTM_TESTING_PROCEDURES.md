# GTM Testing Procedures and Best Practices

## Table of Contents
1. [Testing Overview](#testing-overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Automated Testing Procedures](#automated-testing-procedures)
4. [Manual Testing Procedures](#manual-testing-procedures)
5. [Performance Testing Procedures](#performance-testing-procedures)
6. [Validation and Verification](#validation-and-verification)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## Testing Overview

The GTM testing strategy employs a multi-layered approach to ensure comprehensive coverage:

- **Unit Tests**: Test individual GTM components and hooks in isolation
- **Integration Tests**: Verify GTM interactions with authentication, WebSocket, and other systems
- **E2E Tests**: Validate complete user journeys with GTM tracking
- **Performance Tests**: Ensure GTM doesn't negatively impact application performance
- **Manual Tests**: Human verification of GTM functionality across environments

## Test Environment Setup

### Prerequisites

1. **Node.js Environment**
   ```bash
   node --version  # Should be >= 18.0.0
   npm --version   # Should be >= 8.0.0
   ```

2. **Install Dependencies**
   ```bash
   npm install
   npm install --save-dev @testing-library/react @testing-library/jest-dom
   npm install --save-dev cypress
   ```

3. **Environment Configuration**
   Create test environment files:
   ```bash
   # .env.test
   NEXT_PUBLIC_GTM_CONTAINER_ID=GTM-WKP28PNQ
   NEXT_PUBLIC_GTM_ENABLED=true
   NEXT_PUBLIC_GTM_DEBUG=true
   NEXT_PUBLIC_ENVIRONMENT=test
   ```

4. **GTM Preview Setup**
   - Open Google Tag Manager
   - Navigate to your container (GTM-WKP28PNQ)
   - Click "Preview" to enable debug mode
   - Enter your test URL (usually http://localhost:3000)

### Test Data Setup

1. **Mock Data Configuration**
   ```javascript
   // test-utils/gtm-test-data.ts
   export const mockGTMEvents = {
     auth: {
       login: {
         event: 'user_login',
         event_category: 'authentication',
         auth_method: 'email',
         is_new_user: false,
         user_tier: 'free'
       },
       signup: {
         event: 'user_signup',
         event_category: 'authentication',
         auth_method: 'email',
         is_new_user: true,
         user_tier: 'free'
       }
     },
     engagement: {
       chatStart: {
         event: 'chat_started',
         event_category: 'engagement',
         session_duration: 0
       },
       messageSent: {
         event: 'message_sent',
         event_category: 'engagement',
         message_length: 25,
         thread_id: 'thread_123'
       }
     }
   };
   ```

## Automated Testing Procedures

### Unit Testing

#### Running Unit Tests
```bash
# Run all GTM unit tests
npm test -- --testPathPattern="gtm" --verbose

# Run specific test suites
npm test -- GTMProvider.test.tsx
npm test -- useGTM.test.tsx
npm test -- useGTMEvent.test.tsx
npm test -- useGTMDebug.test.tsx

# Run tests in watch mode
npm test -- --watch --testPathPattern="gtm"

# Run tests with coverage
npm test -- --coverage --testPathPattern="gtm"
```

#### Unit Test Structure
```javascript
describe('GTM Component/Hook Name', () => {
  beforeEach(() => {
    // Setup mocks and test environment
    mockDataLayer = [];
    global.window = { dataLayer: mockDataLayer };
  });

  describe('Feature Group', () => {
    it('should perform specific functionality', async () => {
      // Arrange - Setup test conditions
      // Act - Perform the action
      // Assert - Verify the results
    });
  });

  afterEach(() => {
    // Cleanup
    jest.clearAllMocks();
  });
});
```

#### Key Testing Patterns
1. **Provider Testing Pattern**
   ```javascript
   const renderWithGTM = (component, config = {}) => {
     return render(
       <GTMProvider enabled={true} config={config}>
         {component}
       </GTMProvider>
     );
   };
   ```

2. **Event Tracking Verification**
   ```javascript
   // Verify event was pushed to dataLayer
   await waitFor(() => {
     const event = mockDataLayer.find(item => item.event === 'expected_event');
     expect(event).toBeDefined();
     expect(event.event_category).toBe('expected_category');
   });
   ```

3. **Performance Measurement**
   ```javascript
   const startTime = Date.now();
   // Perform action
   const endTime = Date.now();
   expect(endTime - startTime).toBeLessThan(100); // Should complete within 100ms
   ```

### Integration Testing

#### Running Integration Tests
```bash
# Run all integration tests
npm test -- --testPathPattern="integration" --verbose

# Run specific integration test suites
npm test -- gtm-auth-flow.integration.test.tsx
npm test -- gtm-websocket-events.integration.test.tsx

# Run integration tests with real-time monitoring
npm test -- --testPathPattern="integration" --verbose --detectOpenHandles
```

#### Integration Test Scenarios

1. **Authentication Flow Testing**
   ```javascript
   it('should track complete login flow', async () => {
     // Setup: Render auth components with GTM
     // Action: Perform login sequence
     // Verify: Check login events in dataLayer
     // Verify: Confirm user context in subsequent events
   });
   ```

2. **WebSocket Event Correlation**
   ```javascript
   it('should correlate WebSocket events with GTM tracking', async () => {
     // Setup: Mock WebSocket and GTM
     // Action: Send/receive WebSocket messages
     // Verify: GTM events match WebSocket activity
     // Verify: Thread IDs are consistent across events
   });
   ```

### End-to-End Testing

#### Running E2E Tests
```bash
# Run all GTM E2E tests
npm run cy:run -- --spec="cypress/e2e/gtm-*.cy.ts"

# Run specific E2E test
npm run cy:run -- --spec="cypress/e2e/gtm-analytics-flow.cy.ts"

# Run E2E tests in interactive mode
npm run cy:open
```

#### E2E Test Structure
```javascript
describe('GTM Analytics Flow', () => {
  beforeEach(() => {
    // Setup GTM mocking
    cy.visit('/', {
      onBeforeLoad: (win) => {
        win.dataLayer = [];
        // Setup GTM mocks
      }
    });
  });

  it('should track user journey events', () => {
    // Navigate through application
    // Verify GTM events at each step
    // Check event correlation and data integrity
  });
});
```

#### Key E2E Testing Patterns

1. **GTM Mock Setup**
   ```javascript
   cy.visit('/', {
     onBeforeLoad: (win) => {
       win.dataLayer = [];
       win.gtag = cy.stub().as('gtag');
       
       const originalPush = win.dataLayer.push;
       win.dataLayer.push = function(...args) {
         // Capture events for verification
         return originalPush.apply(this, args);
       };
     }
   });
   ```

2. **Event Verification Pattern**
   ```javascript
   // Perform action that should trigger GTM event
   cy.get('[data-testid="login-btn"]').click();
   
   // Verify the event was tracked
   cy.window().then((win) => {
     const loginEvent = win.dataLayer.find(item => item.event === 'user_login');
     expect(loginEvent).to.exist;
     expect(loginEvent.auth_method).to.equal('email');
   });
   ```

3. **Performance Monitoring**
   ```javascript
   cy.window().then((win) => {
     win.performance.mark('test-start');
   });
   // Perform actions
   cy.window().then((win) => {
     win.performance.mark('test-end');
     const measure = win.performance.measure('test-duration', 'test-start', 'test-end');
     expect(measure.duration).to.be.lessThan(2000);
   });
   ```

## Manual Testing Procedures

### GTM Preview Mode Testing

#### Setup GTM Preview
1. **Enable Preview Mode**
   - Open Google Tag Manager
   - Select container GTM-WKP28PNQ
   - Click "Preview" button
   - Enter application URL (e.g., http://localhost:3000)
   - Click "Start" to begin preview session

2. **Verify Connection**
   - Navigate to your application
   - Confirm GTM Preview pane appears
   - Check that "Connected" status is displayed
   - Verify correct container ID is shown

#### Event Verification Process

1. **Authentication Events**
   ```
   Action: Login with email/password
   Expected GTM Event: user_login
   Verify:
   - Event appears in GTM Preview
   - auth_method = 'email'
   - is_new_user = false/true
   - user_tier is set correctly
   ```

2. **Engagement Events**
   ```
   Action: Start new chat session
   Expected GTM Event: chat_started
   Verify:
   - Event appears with correct category
   - session_duration = 0 for new sessions
   - thread_id is present
   ```

3. **Conversion Events**
   ```
   Action: Upgrade to premium plan
   Expected GTM Events: plan_upgraded, payment_completed
   Verify:
   - Both events appear in sequence
   - transaction_value is correct
   - transaction_id is unique
   - plan_type matches selection
   ```

#### Tag Firing Verification

1. **Check Tag Configuration**
   - In GTM Preview, click on event
   - Verify which tags fired
   - Check tag configuration details
   - Confirm no unwanted tags fired

2. **Variable Population**
   - Check that all variables populate correctly
   - Verify custom dimensions are set
   - Confirm user properties are accurate

### Cross-Browser Testing

#### Browser Test Matrix
| Browser | Version | Desktop | Mobile | Notes |
|---------|---------|---------|---------|--------|
| Chrome | Latest | ✓ | ✓ | Primary test browser |
| Firefox | Latest | ✓ | ✓ | Secondary test browser |
| Safari | Latest | ✓ | ✓ | Important for iOS users |
| Edge | Latest | ✓ | - | Windows compatibility |

#### Testing Procedure per Browser
1. **Initial Load Test**
   - Open application in browser
   - Check browser console for errors
   - Verify GTM script loads successfully
   - Confirm dataLayer is initialized

2. **Core Functionality Test**
   - Perform login/logout sequence
   - Start chat session and send messages
   - Navigate between pages
   - Trigger conversion events

3. **Performance Check**
   - Monitor page load times
   - Check for memory leaks
   - Verify smooth user interactions
   - Test on slower connections

#### Mobile-Specific Testing
1. **Touch Events**
   - Verify touch interactions trigger events
   - Test swipe gestures if applicable
   - Check responsive design tracking

2. **Performance on Mobile**
   - Test on slower mobile networks
   - Verify acceptable load times
   - Check memory usage on mobile devices

### Network Conditions Testing

#### Slow Connection Testing
```bash
# Using Chrome DevTools Network throttling
1. Open DevTools > Network tab
2. Select "Slow 3G" from throttling dropdown
3. Refresh page and test GTM functionality
4. Verify events queue and send when connection improves
```

#### Offline/Online Testing
1. **Offline Simulation**
   - Disable network connection
   - Perform actions that should trigger events
   - Verify events are queued locally

2. **Online Recovery**
   - Re-enable network connection
   - Confirm queued events are sent
   - Verify no data loss occurred

## Performance Testing Procedures

### Automated Performance Tests

#### Running Performance Tests
```bash
# Run all performance tests
npm test -- --testPathPattern="performance" --verbose

# Run specific performance test suites
npm test -- gtm-performance-impact.test.tsx
npm test -- gtm-memory-leak-detection.test.tsx

# Run performance tests with detailed output
npm test -- --testPathPattern="performance" --verbose --detectOpenHandles
```

#### Performance Benchmarks

1. **Script Loading Performance**
   - Target: < 100ms for GTM script load
   - Measurement: From script request to onLoad event
   - Failure Threshold: > 300ms

2. **Event Processing Performance**
   - Target: < 5ms per event
   - Measurement: Time from pushEvent call to dataLayer update
   - Failure Threshold: > 50ms per event

3. **Memory Usage**
   - Target: < 5MB additional memory for GTM
   - Measurement: Heap size increase after GTM load
   - Failure Threshold: > 20MB increase

#### Memory Leak Detection

1. **Automated Detection**
   ```javascript
   // Memory leak test pattern
   it('should not leak memory during component lifecycle', async () => {
     const initialMemory = getMemoryUsage();
     
     // Perform mount/unmount cycles
     for (let i = 0; i < 10; i++) {
       const { unmount } = render(<GTMComponent />);
       // Use component
       unmount();
     }
     
     const finalMemory = getMemoryUsage();
     expect(finalMemory - initialMemory).toBeLessThan(MEMORY_THRESHOLD);
   });
   ```

2. **Manual Memory Testing**
   - Use Chrome DevTools Memory tab
   - Take heap snapshots before and after testing
   - Look for detached DOM nodes
   - Check for growing event listeners

### Performance Monitoring Setup

#### Browser Performance Tools
1. **Chrome DevTools**
   - Performance tab for CPU profiling
   - Memory tab for heap analysis
   - Network tab for resource monitoring
   - Lighthouse for overall performance

2. **Performance Measurement Code**
   ```javascript
   // Add to test components
   const performanceObserver = new PerformanceObserver((list) => {
     for (const entry of list.getEntries()) {
       if (entry.name.includes('gtm')) {
         console.log(`GTM Performance: ${entry.name} took ${entry.duration}ms`);
       }
     }
   });
   performanceObserver.observe({ entryTypes: ['measure'] });
   ```

## Validation and Verification

### Data Accuracy Verification

#### Event Structure Validation
```javascript
const validateEventStructure = (event) => {
  // Required fields
  expect(event.event).toBeDefined();
  expect(event.timestamp).toBeDefined();
  
  // Data types
  expect(typeof event.event).toBe('string');
  expect(typeof event.timestamp).toBe('string');
  
  // Format validation
  expect(event.event).toMatch(/^[a-z_]+$/); // Snake case
  expect(event.timestamp).toMatch(ISO_DATE_REGEX);
};
```

#### Business Logic Validation
1. **User Journey Tracking**
   - Verify user ID consistency across session
   - Check session ID maintenance
   - Confirm funnel progression tracking

2. **Revenue Tracking**
   - Validate transaction values
   - Check currency formatting
   - Verify conversion attribution

### Analytics Integration Verification

#### Google Analytics 4 Verification
1. **Real-time Reports Check**
   - Open GA4 real-time reports
   - Perform test actions
   - Verify events appear in real-time
   - Check event parameters are correct

2. **Debug View Verification**
   - Enable GA4 Debug View
   - Send test events
   - Verify event structure in debug interface
   - Check custom dimensions and metrics

#### Custom Analytics Verification
1. **DataLayer Export**
   ```javascript
   // Export dataLayer for analysis
   const exportDataLayer = () => {
     const events = window.dataLayer.filter(item => item.event);
     const csv = convertToCSV(events);
     downloadCSV(csv, 'gtm-events.csv');
   };
   ```

2. **Event Correlation Analysis**
   - Check user ID consistency
   - Verify session continuity
   - Confirm timestamp accuracy
   - Validate event sequencing

## Troubleshooting

### Common Issues and Solutions

#### GTM Script Not Loading
**Symptoms**: No GTM events, missing dataLayer
**Diagnosis**:
```javascript
// Check in browser console
console.log('GTM Loaded:', !!window.google_tag_manager);
console.log('DataLayer:', window.dataLayer);
```
**Solutions**:
- Verify container ID is correct
- Check Content Security Policy
- Ensure network connectivity
- Verify environment variables

#### Events Not Firing
**Symptoms**: Events missing from GTM Preview
**Diagnosis**:
```javascript
// Check event structure
window.dataLayer.forEach((item, index) => {
  console.log(`Event ${index}:`, item);
});
```
**Solutions**:
- Verify event has required 'event' property
- Check for JavaScript errors
- Ensure GTM is properly initialized
- Verify event triggers in GTM

#### Performance Issues
**Symptoms**: Slow page load, high memory usage
**Diagnosis**:
```javascript
// Check performance metrics
performance.getEntriesByType('navigation').forEach(entry => {
  console.log('Load Time:', entry.loadEventEnd - entry.loadEventStart);
});
```
**Solutions**:
- Use async script loading
- Implement event batching
- Optimize event payload size
- Add performance monitoring

### Debug Mode Utilities

#### GTM Debug Console
```javascript
// Add to browser console for debugging
window.gtmDebug = {
  showEvents: () => {
    console.table(window.dataLayer.filter(item => item.event));
  },
  
  showLatestEvents: (count = 5) => {
    const events = window.dataLayer.filter(item => item.event).slice(-count);
    console.table(events);
  },
  
  validateEvent: (event) => {
    const required = ['event', 'timestamp'];
    const missing = required.filter(field => !event[field]);
    if (missing.length > 0) {
      console.warn('Missing required fields:', missing);
    }
    return missing.length === 0;
  }
};
```

#### Performance Debug Utilities
```javascript
// Memory usage monitor
window.gtmPerf = {
  getMemoryUsage: () => {
    if (performance.memory) {
      return {
        used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
        total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
        limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024)
      };
    }
    return 'Memory API not available';
  },
  
  trackEventPerformance: (eventName, fn) => {
    const start = performance.now();
    const result = fn();
    const end = performance.now();
    console.log(`${eventName} took ${end - start}ms`);
    return result;
  }
};
```

## Best Practices

### Test Development Best Practices

1. **Test Structure**
   - Use descriptive test names
   - Follow Arrange-Act-Assert pattern
   - Keep tests focused and independent
   - Use appropriate test doubles (mocks, stubs, spies)

2. **Mock Strategy**
   - Mock external dependencies (GTM script, network calls)
   - Use realistic mock data
   - Keep mocks simple and focused
   - Clean up mocks after each test

3. **Performance Testing**
   - Set realistic performance budgets
   - Test with production-like data volumes
   - Include mobile and slow network scenarios
   - Monitor memory usage patterns

### Testing Environment Best Practices

1. **Environment Isolation**
   - Use separate GTM containers for test environments
   - Isolate test data from production analytics
   - Use environment-specific configuration
   - Implement proper cleanup procedures

2. **Test Data Management**
   - Use consistent test data across test types
   - Implement test data factories
   - Clean up test data after runs
   - Use realistic but anonymized data

3. **Continuous Integration**
   - Run tests on every commit
   - Include performance regression testing
   - Set up proper test reporting
   - Implement test failure notifications

### Monitoring and Alerting

1. **Test Result Monitoring**
   - Track test pass rates over time
   - Monitor test execution times
   - Alert on test failures
   - Track coverage metrics

2. **Performance Monitoring**
   - Set up performance budgets
   - Monitor memory usage trends
   - Track GTM script load times
   - Alert on performance regressions

3. **Analytics Monitoring**
   - Monitor event delivery rates
   - Track data quality metrics
   - Set up anomaly detection
   - Implement business metric validation

---

**Document Version**: 1.0  
**Last Updated**: 2025-08-28  
**Review Schedule**: Monthly  
**Owner**: QA Team  
**Reviewers**: Development Team, Analytics Team