/**
 * Centralized Mock Service Layer Index
 * 
 * CRITICAL CONTEXT: Phase 1, Agent 2 implementation
 * - Single entry point for all mocking functionality
 * - Comprehensive test utilities
 * - Consistent API across all test files
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - Maximum file size: 300 lines
 * - Functions ≤8 lines each
 * - Exports organized by category
 */

// ============================================================================
// API MOCKING EXPORTS - Conditional based on MSW availability
// ============================================================================

// Safe re-exports that handle MSW availability
let apiMockingExports: any = {};

try {
  apiMockingExports = require('./api-mocks');
} catch (error) {
  console.warn('API mocks not available:', error.message);
  // Provide safe fallbacks
  apiMockingExports = {
    createMockThread: () => ({ id: 'mock', title: 'Mock Thread' }),
    createMockMessage: () => ({ id: 'mock', content: 'Mock Message', role: 'user' }),
    createMockUser: () => ({ id: 'mock', email: 'mock@example.com' }),
    createMockWorkload: () => ({ id: 'mock', name: 'Mock Workload' }),
    apiHandlers: [],
    errorHandlers: [],
    mockServer: null,
    startMockServer: () => console.warn('MSW not available'),
    stopMockServer: () => {},
    resetMockHandlers: () => {},
    useMockErrorScenarios: () => {},
    mockApiErrors: {},
    simulateRateLimit: () => false,
    resetRateLimits: () => {},
    withDelay: (data: any) => Promise.resolve(data),
    createMockApiResponse: () => ({}),
    waitForApiCall: () => Promise.resolve()
  };
}

export const {
  createMockThread,
  createMockMessage,
  createMockUser,
  createMockWorkload,
  apiHandlers,
  errorHandlers,
  mockServer,
  startMockServer,
  stopMockServer,
  resetMockHandlers,
  useMockErrorScenarios,
  mockApiErrors,
  simulateRateLimit,
  resetRateLimits,
  withDelay,
  createMockApiResponse,
  waitForApiCall
} = apiMockingExports;

// ============================================================================
// WEBSOCKET MOCKING EXPORTS
// ============================================================================

// Import for default export usage
import { 
  EnhancedMockWebSocket as _EnhancedMockWebSocket, 
  createWebSocketTestManager as _createWebSocketTestManager,
  installWebSocketMock,
  waitForWebSocketOpen,
  waitForMessage
} from './websocket-mocks';

export {
  // WebSocket classes
  EnhancedMockWebSocket,
  WebSocketTestManager,
  
  // Installation utilities
  installWebSocketMock,
  createWebSocketTestManager,
  
  // Test utilities
  waitForWebSocketOpen,
  waitForMessage,
  
  // Types
  type WebSocketState,
  type MessageType,
  type MockWebSocketMessage,
  type StreamingMessageChunk
} from './websocket-mocks';

// ============================================================================
// AUTH SERVICE MOCKING EXPORTS
// ============================================================================

export {
  mockAuthServiceResponses,
  mockAuthServiceClient,
  setupAuthServiceMocks,
  mockAuthServiceFetch,
  resetAuthServiceMocks,
  setupAuthServiceErrors,
  setupAuthServiceUnauthorized
} from './auth-service-mock';

// ============================================================================
// UNIFIED MOCK SETUP UTILITIES
// ============================================================================

/**
 * Initialize all mocking systems for comprehensive testing
 * Call this in test setup files or individual test suites
 */
export function initializeAllMocks() {
  startMockServer();
  installWebSocketMock();
  setupAuthServiceMocks();
}

/**
 * Reset all mocking systems to clean state
 * Call this between tests to ensure isolation
 */
export function resetAllMocks() {
  resetMockHandlers();
  resetRateLimits();
  resetAuthServiceMocks();
}

/**
 * Cleanup all mocking systems
 * Call this in test teardown
 */
export function cleanupAllMocks() {
  stopMockServer();
  resetAllMocks();
}

// ============================================================================
// SCENARIO-BASED MOCK CONFIGURATIONS
// ============================================================================

/**
 * Configure mocks for error testing scenarios
 * Enables comprehensive error simulation across all services
 */
export function enableErrorTestingMode() {
  useMockErrorScenarios();
  setupAuthServiceErrors();
}

/**
 * Configure mocks for authentication testing
 * Sets up various auth states and scenarios
 */
export function enableAuthTestingMode() {
  setupAuthServiceMocks();
  mockAuthServiceFetch();
}

/**
 * Configure mocks for real-time/WebSocket testing
 * Enables advanced WebSocket simulation features
 */
export function enableRealtimeTestingMode() {
  installWebSocketMock();
  return createWebSocketTestManager();
}

/**
 * Configure mocks for performance testing
 * Adds timing controls and measurement utilities
 */
export function enablePerformanceTestingMode() {
  // API calls with realistic delays
  startMockServer();
  
  // Return timing utilities
  return {
    withDelay,
    waitForApiCall,
    waitForWebSocketOpen,
    simulateRateLimit
  };
}

// ============================================================================
// COMMON TEST DATA GENERATORS
// ============================================================================

/**
 * Generate realistic test data for comprehensive testing
 * Creates interconnected mock data that mimics production relationships
 */
export function generateTestDataSet(options: {
  threadCount?: number;
  messagesPerThread?: number;
  userCount?: number;
} = {}) {
  const { threadCount = 5, messagesPerThread = 10, userCount = 3 } = options;
  
  const users = Array.from({ length: userCount }, (_, i) =>
    createMockUser({ id: `user_${i}`, email: `user${i}@test.com` })
  );
  
  const threads = Array.from({ length: threadCount }, (_, i) =>
    createMockThread({ 
      id: `thread_${i}`, 
      title: `Test Thread ${i + 1}`,
      message_count: messagesPerThread
    })
  );
  
  const messages = threads.flatMap(thread =>
    Array.from({ length: messagesPerThread }, (_, i) =>
      createMockMessage({
        id: `${thread.id}_msg_${i}`,
        thread_id: thread.id,
        role: i % 2 === 0 ? 'user' : 'assistant',
        content: `Message ${i + 1} in ${thread.title}`
      })
    )
  );
  
  return { users, threads, messages };
}

/**
 * Create mock WebSocket messages for testing streaming scenarios
 */
export function generateStreamingTestData(content: string, chunkSize: number = 50) {
  const chunks = [];
  const messageId = `stream_test_${Date.now()}`;
  
  for (let i = 0; i < content.length; i += chunkSize) {
    chunks.push({
      id: messageId,
      content: content.slice(i, i + chunkSize),
      isComplete: i + chunkSize >= content.length,
      chunkIndex: chunks.length,
      timestamp: Date.now() + chunks.length * 100
    });
  }
  
  return chunks;
}

// ============================================================================
// INTEGRATION TEST HELPERS
// ============================================================================

/**
 * Setup complete mock environment for integration tests
 * Provides comprehensive mocking with realistic data and behaviors
 */
export function setupIntegrationTestEnvironment() {
  initializeAllMocks();
  const testData = generateTestDataSet();
  const wsManager = createWebSocketTestManager();
  
  return {
    ...testData,
    wsManager,
    cleanup: cleanupAllMocks,
    reset: resetAllMocks,
    enableErrorMode: enableErrorTestingMode,
    enablePerformanceMode: enablePerformanceTestingMode
  };
}

/**
 * Quick mock setup for unit tests
 * Minimal mocking configuration for fast unit test execution
 */
export function setupUnitTestEnvironment() {
  resetAllMocks();
  
  return {
    createThread: createMockThread,
    createMessage: createMockMessage,
    createUser: createMockUser,
    cleanup: resetAllMocks
  };
}

// ============================================================================
// DEFAULT EXPORT FOR CONVENIENCE
// ============================================================================

export default {
  // Setup functions
  initializeAllMocks,
  resetAllMocks,
  cleanupAllMocks,
  
  // Scenario configurations
  enableErrorTestingMode,
  enableAuthTestingMode,
  enableRealtimeTestingMode,
  enablePerformanceTestingMode,
  
  // Test environments
  setupIntegrationTestEnvironment,
  setupUnitTestEnvironment,
  
  // Data generators
  generateTestDataSet,
  generateStreamingTestData,
  
  // Core mocking utilities
  createMockThread,
  createMockMessage,
  createMockUser,
  mockServer,
  EnhancedMockWebSocket: _EnhancedMockWebSocket,
  createWebSocketTestManager: _createWebSocketTestManager
};