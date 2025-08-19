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