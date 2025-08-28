/**
 * Test Utils Index - Centralized Export Hub
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: All development teams
 * - Business Goal: Streamline test development workflow
 * - Value Impact: 50% faster test creation
 * - Revenue Impact: Reduces development time costs
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - File size: ≤100 lines (utility index)
 * - Clean exports with clear organization
 * - Single import point for all test utilities
 */

// ============================================================================
// CORE TEST UTILITIES - Main testing framework extensions
// ============================================================================

// Main test utilities (providers, mocks, etc.)
export * from './test-utils';

// ============================================================================
// DOMAIN-SPECIFIC TEST HELPERS - Specialized utilities
// ============================================================================

// Message testing utilities
export * from './message-test-helpers';

// Thread testing utilities  
export * from './thread-test-helpers';

// Authentication testing utilities
export * from './auth-test-helpers';

// ============================================================================
// NEW TEST UTILITIES - Enhanced testing capabilities
// ============================================================================

// Enhanced render functions and utilities
export * from './test-helpers';

// Mock data factories for consistent testing
export * from './mock-factories';

// Custom Jest matchers for better assertions
export * from './custom-matchers';

// ============================================================================
// HELPER UTILITIES - Specialized testing helpers
// ============================================================================

// Test helpers from helpers directory (WebSocket, components, etc.)
export * from '../helpers';

// ============================================================================
// CONVENIENCE RE-EXPORTS - Common patterns
// ============================================================================

// Common imports for most tests
export {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
  renderHook,
  cleanup
} from '@testing-library/react';

export { jest } from '@jest/globals';

// ============================================================================
// TYPE EXPORTS - For TypeScript test files
// ============================================================================

export type {
  Message,
  ChatMessage,
  MessageRole,
  MessageMetadata,
  MessageAttachment
} from './message-test-helpers';

export type {
  Thread,
  ThreadState,
  ThreadMetadata
} from './thread-test-helpers';

export type {
  TestUser,
  AuthEndpoints,
  AuthConfigResponse
} from './auth-test-helpers';

// New utility types
export type {
  MockUser,
  MockThread,
  MockMessage,
  MockWebSocketMessage,
  MockStoreState,
  TestRenderOptions,
  PerformanceMetrics
} from './test-helpers';