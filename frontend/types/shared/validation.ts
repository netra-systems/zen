/**
 * Shared Validation Types
 * 
 * Business Value Justification:
 * - Segment: All (Free, Early, Mid, Enterprise)  
 * - Business Goal: Code consistency & development velocity
 * - Value Impact: Eliminates duplicate validation type definitions across codebase
 * - Strategic Impact: Single source of truth for validation patterns reduces bugs and improves maintainability
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - Single source of truth for validation interfaces
 * - Maximum file size: 300 lines
 * - Functions ≤8 lines each
 * - Use clear, descriptive names for specialized validation types
 */

import { BaseEntity } from './base';

// BASE VALIDATION INTERFACES

/**
 * Base validation result interface - foundation for all validation types
 */
export interface BaseValidationResult {
  readonly isValid: boolean;
  readonly timestamp?: string;
}

/**
 * Validation result with error messages
 */
export interface ValidationResultWithErrors extends BaseValidationResult {
  readonly errors: readonly string[];
}

/**
 * Validation result with warnings and errors
 */
export interface ValidationResultWithWarnings extends ValidationResultWithErrors {
  readonly warnings: readonly string[];
}

// SPECIALIZED VALIDATION TYPES

/**
 * Hydration validation result for server/client state synchronization
 * Used by: HydrationValidator class
 */
export interface HydrationValidationResult extends ValidationResultWithWarnings {
  readonly mismatches: readonly string[];
  readonly serverState?: unknown;
  readonly clientState?: unknown;
}

/**
 * Configuration validation result for form/config validation
 * Used by: ConfigurationBuilder components
 */
export interface ConfigValidationResult {
  readonly valid: boolean;
  readonly errors: readonly string[];
}

/**
 * WebSocket event validation result
 * Used by: WebSocketDebugger service
 */
export interface EventValidationResult extends ValidationResultWithErrors {
  readonly eventType?: string;
  readonly isExpected: boolean;
  readonly metadata?: Record<string, unknown>;
}

/**
 * Authentication validation result
 * Used by: UnifiedAuthService
 */
export interface AuthValidationResult extends ValidationResultWithErrors {
  readonly isAuthenticated: boolean;
  readonly user?: BaseEntity;
  readonly sessionValid?: boolean;
  readonly tokenExpired?: boolean;
}

/**
 * Generic field validation result for individual form fields
 */
export interface FieldValidationResult extends ValidationResultWithErrors {
  readonly fieldName: string;
  readonly value?: unknown;
  readonly required?: boolean;
}

/**
 * Bulk validation result for validating multiple items
 */
export interface BulkValidationResult extends BaseValidationResult {
  readonly totalItems: number;
  readonly validItems: number;
  readonly invalidItems: number;
  readonly results: readonly BaseValidationResult[];
  readonly summary?: string;
}

// TYPE ALIASES FOR BACKWARD COMPATIBILITY

/**
 * @deprecated Use ConfigValidationResult instead
 * Kept for backward compatibility with existing code
 */
export type ValidationResult = ConfigValidationResult;

// VALIDATION UTILITIES

/**
 * Create a successful validation result
 */
export function createValidResult<T extends BaseValidationResult>(
  additionalData?: Partial<Omit<T, 'isValid'>>
): T {
  return {
    isValid: true,
    timestamp: new Date().toISOString(),
    ...additionalData
  } as T;
}

/**
 * Create a failed validation result with errors
 */
export function createInvalidResult<T extends ValidationResultWithErrors>(
  errors: string[],
  additionalData?: Partial<Omit<T, 'isValid' | 'errors'>>
): T {
  return {
    isValid: false,
    errors: errors as readonly string[],
    timestamp: new Date().toISOString(),
    ...additionalData
  } as T;
}

/**
 * Create a config validation result
 */
export function createConfigValidationResult(
  valid: boolean,
  errors: string[] = []
): ConfigValidationResult {
  return {
    valid,
    errors: errors as readonly string[]
  };
}

/**
 * Create a hydration validation result
 */
export function createHydrationValidationResult(
  isValid: boolean,
  mismatches: string[] = [],
  warnings: string[] = [],
  serverState?: unknown,
  clientState?: unknown
): HydrationValidationResult {
  return {
    isValid,
    mismatches: mismatches as readonly string[],
    warnings: warnings as readonly string[],
    errors: mismatches as readonly string[], // mismatches are errors
    serverState,
    clientState,
    timestamp: new Date().toISOString()
  };
}

/**
 * Create an event validation result
 */
export function createEventValidationResult(
  isValid: boolean,
  isExpected: boolean,
  errors: string[] = [],
  eventType?: string,
  metadata?: Record<string, unknown>
): EventValidationResult {
  return {
    isValid,
    isExpected,
    errors: errors as readonly string[],
    eventType,
    metadata,
    timestamp: new Date().toISOString()
  };
}

/**
 * Create an auth validation result
 */
export function createAuthValidationResult(
  isValid: boolean,
  isAuthenticated: boolean,
  errors: string[] = [],
  user?: BaseEntity,
  sessionValid?: boolean,
  tokenExpired?: boolean
): AuthValidationResult {
  return {
    isValid,
    isAuthenticated,
    errors: errors as readonly string[],
    user,
    sessionValid,
    tokenExpired,
    timestamp: new Date().toISOString()
  };
}

/**
 * Combine multiple validation results
 */
export function combineValidationResults(
  results: readonly BaseValidationResult[]
): BulkValidationResult {
  const totalItems = results.length;
  const validItems = results.filter(r => r.isValid).length;
  const invalidItems = totalItems - validItems;
  const isValid = invalidItems === 0;
  
  return {
    isValid,
    totalItems,
    validItems,
    invalidItems,
    results,
    summary: `${validItems}/${totalItems} items valid`,
    timestamp: new Date().toISOString()
  };
}

/**
 * Check if validation result has errors
 */
export function hasValidationErrors(
  result: BaseValidationResult
): result is ValidationResultWithErrors {
  return 'errors' in result && Array.isArray((result as ValidationResultWithErrors).errors);
}

/**
 * Extract all error messages from validation result
 */
export function getValidationErrors(result: BaseValidationResult): string[] {
  if (hasValidationErrors(result)) {
    return [...result.errors];
  }
  return [];
}

// TYPE GUARDS

/**
 * Check if result is a hydration validation result
 */
export function isHydrationValidationResult(
  result: BaseValidationResult
): result is HydrationValidationResult {
  return 'mismatches' in result && 'warnings' in result;
}

/**
 * Check if result is a config validation result
 */
export function isConfigValidationResult(
  result: unknown
): result is ConfigValidationResult {
  return typeof result === 'object' && result !== null &&
    'valid' in result && 'errors' in result;
}

/**
 * Check if result is an event validation result
 */
export function isEventValidationResult(
  result: BaseValidationResult
): result is EventValidationResult {
  return 'isExpected' in result && 'eventType' in result;
}

/**
 * Check if result is an auth validation result
 */
export function isAuthValidationResult(
  result: BaseValidationResult
): result is AuthValidationResult {
  return 'isAuthenticated' in result;
}

// DEFAULT EXPORT

export default {
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
};