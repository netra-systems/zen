/**
 * Shared Types Index
 * 
 * Single source of truth for all shared type definitions.
 * This index exports all core types used across the frontend application.
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - All shared types must be exported from this index
 * - Maximum file size: 100 lines (index file)
 * - Import order: base -> enums -> validation -> specialized
 */

// Base types and interfaces
export * from './base';

// Core enums and constants
export * from './enums';

// Validation types and utilities
export * from './validation';

// Re-export commonly used types for convenience
export type {
  BaseEntity,
  BaseTimestampEntity,
  BaseMessage,
  BaseMetadata,
  User,
  MessageAttachment,
  MessageReaction,
  MessageMetadata,
  MessageRole,
  MessageStatus
} from './base';

export {
  MessageType,
  AgentStatus,
  WebSocketMessageType,
  isValidMessageType,
  isValidAgentStatus,
  isValidWebSocketMessageType
} from './enums';

export type {
  BaseValidationResult,
  ValidationResultWithErrors,
  ValidationResultWithWarnings,
  HydrationValidationResult,
  ConfigValidationResult,
  EventValidationResult,
  AuthValidationResult,
  FieldValidationResult,
  BulkValidationResult,
  ValidationResult
} from './validation';

export {
  createValidResult,
  createInvalidResult,
  createConfigValidationResult,
  createHydrationValidationResult,
  createEventValidationResult,
  createAuthValidationResult,
  combineValidationResults,
  hasValidationErrors,
  getValidationErrors,
  isHydrationValidationResult,
  isConfigValidationResult,
  isEventValidationResult,
  isAuthValidationResult
} from './validation';