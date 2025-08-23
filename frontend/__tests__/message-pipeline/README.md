# Message Pipeline Test Suite

This comprehensive test suite verifies the complete end-to-end message pipeline from UI interaction to backend integration. It covers all critical flows, error scenarios, and edge cases to ensure the chat functionality works reliably in production.

## Test Structure

### 1. MessageInput.pipeline.test.tsx
Tests the MessageInput component's complete functionality:
- **User Input Validation**: Message validation, character limits, authentication states
- **Keyboard Navigation**: Enter key handling, message history navigation, shortcuts
- **Processing States**: Loading states, disabled states during processing
- **Integration Points**: Store integration, hook connections, event handling
- **Accessibility**: ARIA labels, keyboard navigation, screen reader compatibility

### 2. useMessageSending.pipeline.test.tsx
Tests the useMessageSending hook's complete pipeline:
- **Message Validation**: Authentication checks, content validation, rate limiting
- **Thread Management**: Thread creation, existing thread handling, title generation
- **WebSocket Integration**: Message type selection (start_agent vs user_message)
- **Optimistic Updates**: Immediate UI feedback, message status management
- **Error Handling**: Network failures, service errors, retry mechanisms
- **State Synchronization**: Store updates, consistent state management

### 3. OptimisticMessageManager.pipeline.test.tsx
Tests the OptimisticMessageManager service:
- **Message Lifecycle**: Creation, updates, status transitions, cleanup
- **Backend Reconciliation**: Message matching, conflict resolution, timeout handling
- **Subscription System**: State notifications, callback management, error handling
- **Retry Logic**: Failure detection, exponential backoff, maximum attempts
- **Performance**: Large message volumes, memory management, concurrent updates
- **Edge Cases**: Malformed data, race conditions, cleanup scenarios

### 4. WebSocketProvider.pipeline.test.tsx
Tests the WebSocketProvider's complete integration:
- **Connection Management**: Establishment, authentication, secure URLs
- **Token Management**: Refresh logic, synchronization, failure handling
- **Message Processing**: Deduplication, reconciliation integration, buffer management
- **Status Updates**: Connection state changes, error propagation
- **Context API**: Provider functionality, consumer error handling
- **Lifecycle Management**: Cleanup, reconnection, concurrent operations

### 5. MessagePipeline.integration.test.tsx
Tests the complete end-to-end integration:
- **Happy Path Flow**: User input → optimistic updates → WebSocket → backend → reconciliation
- **Thread Management**: New thread creation, existing thread messaging
- **Error Recovery**: Network failures, authentication issues, service errors
- **State Consistency**: Cross-store synchronization, data integrity
- **Real-time Updates**: Streaming responses, concurrent operations
- **Performance**: High-volume scenarios, memory optimization

### 6. ErrorHandlingAndRetry.pipeline.test.tsx
Tests comprehensive error scenarios:
- **Network Failures**: Connection loss, intermittent failures, timeout handling
- **Authentication Errors**: Token expiry, refresh failures, security violations
- **Service Errors**: Backend unavailability, malformed responses, rate limiting
- **Retry Mechanisms**: Exponential backoff, maximum attempts, manual retry
- **User Feedback**: Error messages, recovery flows, graceful degradation
- **Edge Cases**: Concurrent failures, memory cleanup, component lifecycle

### 7. OptimisticUIAndReconciliation.pipeline.test.tsx
Tests optimistic UI updates and reconciliation:
- **Immediate Updates**: User message visibility, AI thinking indicators
- **Status Transitions**: Pending → confirmed/failed, processing → completed
- **Streaming Responses**: Real-time content updates, interruption handling
- **Reconciliation**: Backend matching, conflict resolution, partial updates
- **Performance**: Large volumes, memory optimization, throttling
- **UI Synchronization**: Cross-component consistency, state management

### 8. EdgeCasesAndConcurrency.pipeline.test.tsx
Tests complex scenarios and boundary conditions:
- **Concurrency**: Multiple users, rapid messages, race conditions
- **Memory Management**: Large volumes, cleanup strategies, leak prevention
- **Network Disruption**: Intermittent failures, recovery patterns
- **Chaos Testing**: Random disruptions, stability under stress
- **Browser Environment**: Focus changes, visibility events, lifecycle management
- **Performance Boundaries**: Load testing, memory constraints, optimization

## Critical Flows Tested

### 1. Happy Path Message Flow
```
User types message → MessageInput validates → useMessageSending processes →
OptimisticMessageManager creates optimistic messages → WebSocket sends to backend →
Backend confirms → Reconciliation updates UI → Final state consistency
```

### 2. Error Recovery Flow
```
Message fails to send → OptimisticMessageManager marks as failed →
Retry mechanism activates → Exponential backoff → Success or max retries →
User feedback and recovery options
```

### 3. Thread Management Flow
```
First message → Thread creation → Active thread setting →
Subsequent messages → Existing thread usage → Thread rename automation
```

### 4. Authentication Flow
```
Token validation → WebSocket authentication → Token refresh on expiry →
Connection recovery → Message pipeline continuation
```

### 5. Optimistic Update Flow
```
User action → Immediate UI update → Backend processing indication →
Streaming response updates → Backend confirmation → Reconciliation →
Final UI state
```

## Test Scenarios Coverage

### Core Functionality
- ✅ Message sending and receiving
- ✅ Thread creation and management
- ✅ Optimistic UI updates
- ✅ WebSocket communication
- ✅ Authentication and authorization

### Error Handling
- ✅ Network failures and recovery
- ✅ Authentication failures
- ✅ Backend service errors
- ✅ Retry mechanisms and backoff
- ✅ Graceful degradation

### Performance and Scalability
- ✅ High message volumes
- ✅ Concurrent operations
- ✅ Memory management
- ✅ Performance boundaries
- ✅ Long-running sessions

### Edge Cases
- ✅ Race conditions
- ✅ Component lifecycle events
- ✅ Browser environment variations
- ✅ Malformed data handling
- ✅ Resource constraints

### User Experience
- ✅ Immediate feedback
- ✅ Status indicators
- ✅ Error messages
- ✅ Recovery flows
- ✅ Accessibility compliance

## Running the Tests

### Individual Test Suites
```bash
# Run specific test file
npm test MessageInput.pipeline.test.tsx
npm test useMessageSending.pipeline.test.tsx
npm test OptimisticMessageManager.pipeline.test.tsx
npm test WebSocketProvider.pipeline.test.tsx
npm test MessagePipeline.integration.test.tsx
npm test ErrorHandlingAndRetry.pipeline.test.tsx
npm test OptimisticUIAndReconciliation.pipeline.test.tsx
npm test EdgeCasesAndConcurrency.pipeline.test.tsx
```

### Complete Pipeline Test Suite
```bash
# Run all pipeline tests
npm test -- __tests__/message-pipeline/

# Run with coverage
npm test -- __tests__/message-pipeline/ --coverage

# Run with verbose output
npm test -- __tests__/message-pipeline/ --verbose

# Run in watch mode for development
npm test -- __tests__/message-pipeline/ --watch
```

### Performance Testing
```bash
# Run performance-focused tests
npm test -- __tests__/message-pipeline/ --testNamePattern="performance|memory|load"

# Run concurrency tests
npm test -- __tests__/message-pipeline/ --testNamePattern="concurrent|race|chaos"
```

## Test Configuration

The tests use the following configuration:
- **Jest**: Test runner with React Testing Library
- **Fake Timers**: For testing timeouts and delays
- **Mock Services**: Comprehensive mocking of WebSocket, backend services
- **User Events**: Realistic user interaction simulation
- **Performance Monitoring**: Memory usage and execution time tracking

## Debugging Tests

### Common Issues
1. **Timer-related test failures**: Ensure proper `act()` wrapping and timer advancement
2. **Async operation conflicts**: Use `waitFor()` for async state changes
3. **Mock inconsistencies**: Reset mocks between tests with `beforeEach()`
4. **Memory leaks in tests**: Clean up subscriptions and clear optimistic state

### Debug Commands
```bash
# Run single test with debugging
npm test -- --testNamePattern="specific test name" --verbose

# Run with Jest debugging
node --inspect-brk node_modules/.bin/jest --runInBand __tests__/message-pipeline/

# Generate test coverage report
npm test -- __tests__/message-pipeline/ --coverage --coverageReporters=html
```

## Test Metrics and Goals

### Coverage Targets
- **Line Coverage**: > 90%
- **Branch Coverage**: > 85%
- **Function Coverage**: > 95%
- **Statement Coverage**: > 90%

### Performance Targets
- **Test Execution**: < 30 seconds for full suite
- **Memory Usage**: < 512MB peak during testing
- **Concurrent Operations**: Handle 100+ simultaneous messages
- **Error Recovery**: < 5 second recovery time

### Quality Metrics
- **Test Reliability**: > 99% pass rate
- **Edge Case Coverage**: > 50 unique edge cases
- **Error Scenario Coverage**: > 20 different error types
- **Integration Points**: 100% of component interfaces tested

## Maintenance

### Adding New Tests
1. Follow the existing test structure and naming conventions
2. Include comprehensive JSDoc documentation
3. Cover happy path, error cases, and edge cases
4. Add performance considerations for complex scenarios
5. Update this README with new test descriptions

### Updating Tests
1. Maintain backward compatibility with existing test patterns
2. Update mock configurations when service interfaces change
3. Adjust performance targets based on system improvements
4. Keep test data factories in sync with type definitions

This test suite ensures the message pipeline is production-ready, reliable, and maintainable. It provides confidence that the chat functionality will work correctly across all supported scenarios and environments.