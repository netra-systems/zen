/**
 * Test Helpers Index - Centralized export for test helper utilities
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: All development teams
 * - Business Goal: Streamline test helper imports
 * - Value Impact: Eliminates import path confusion
 * - Revenue Impact: Reduces debugging time for test setup issues
 */

// ============================================================================
// WEBSOCKET TEST UTILITIES - Core WebSocket testing infrastructure
// ============================================================================

export {
  WebSocketTestManager,
  createWebSocketManager,
  createLegacyWebSocketManager,
  createMultipleWebSocketManagers,
  safeWebSocketCleanup,
  globalWebSocketCleanup
} from './websocket-test-manager';

export * from './websocket-test-helpers';
export * from './websocket-test-utilities';

// ============================================================================
// COMPONENT AND STATE HELPERS - Testing setup and management
// ============================================================================

export * from './test-component-helpers';
export * from './test-setup-helpers';
export * from './test-timing-utilities';

// ============================================================================
// FEATURE AND STATE HELPERS - Application-specific testing
// ============================================================================

export * from './feature-flag-helpers';
export * from './first-load-helpers';
export * from './first-load-mock-setup';
export * from './initial-state-helpers';
export * from './initial-state-mock-components';