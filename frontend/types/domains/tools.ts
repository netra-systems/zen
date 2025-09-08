/**
 * Tools Domain: Consolidated Tool-Related Types
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - Single source of truth for all tool-related types
 * - Maximum file size: 300 lines
 * - Functions ≤8 lines each
 * - Backend-aligned type definitions
 * 
 * BVJ: Consolidated tool types = better type safety = fewer runtime errors
 * 
 * This module consolidates all tool-related types from:
 * - backend_schema_tools.ts (ToolStatus, ToolInput, ToolResult, ReferenceItem)
 * - backend-sync/payloads.ts (ToolCallPayload, ToolResultPayload)
 * - Tool.ts and tools.ts (legacy compatibility)
 */

// Import base types for consistency
import { BaseWebSocketPayload } from '../shared/base';
import type { ReferenceItem } from '../backend_schema_tools';

// Re-export ReferenceItem for consumers of this module
export { ReferenceItem };

// ============================================================================
// CORE TOOL ENUMS AND TYPES
// ============================================================================

/**
 * Tool execution status aligned with backend enum.
 * Represents the complete lifecycle of tool execution.
 */
export type ToolStatus = 
  | "success" 
  | "error" 
  | "partial_success" 
  | "in_progress" 
  | "complete";

// ============================================================================
// BACKEND SCHEMA TOOL TYPES - Core tool execution interfaces
// ============================================================================

/**
 * Tool input definition - what gets passed to a tool.
 * Aligned with backend ToolInput schema.
 */
export interface ToolInput {
  tool_name: string;
  args?: unknown[];
  kwargs?: {
    [k: string]: unknown;
  };
}

/**
 * Tool execution result - what comes back from a tool.
 * Aligned with backend ToolResult schema.
 */
export interface ToolResult {
  tool_input: ToolInput;
  status?: ToolStatus;
  message?: string;
  payload?: unknown;
  start_time?: number;
  end_time?: number | null;
}


// ============================================================================
// WEBSOCKET TOOL PAYLOADS - Real-time tool communication
// ============================================================================

/**
 * WebSocket payload for tool calls.
 * Used when initiating tool execution via WebSocket.
 */
export interface ToolCallPayload extends BaseWebSocketPayload {
  tool_name: string;
  parameters?: Record<string, unknown>;
  call_id: string;
}

/**
 * WebSocket payload for tool results.
 * Used when returning tool execution results via WebSocket.
 */
export interface ToolResultPayload extends BaseWebSocketPayload {
  call_id: string;
  result?: string | Record<string, unknown>;
  error?: string;
  execution_time_ms?: number;
}

// ============================================================================
// EXTENDED TOOL INTERFACES - Enhanced for frontend usage
// ============================================================================

/**
 * Tool execution completion event.
 * Simplified interface for UI event handling.
 */
export interface ToolCompleted {
  tool_name: string;
  result: ToolResultData;
  run_id?: string;
}

/**
 * Tool execution start event.
 * Minimal interface for UI status tracking.
 */
export interface ToolStarted {
  tool_name: string;
  run_id?: string;
}

/**
 * Structured tool result data for UI consumption.
 * Enhanced version with additional metadata.
 */
export interface ToolResultData {
  output?: string;
  data?: {
    [key: string]: unknown;
  };
  errors?: string[];
  warnings?: string[];
  metadata?: {
    [key: string]: unknown;
  };
}

// ============================================================================
// UTILITY FUNCTIONS - Each function ≤8 lines
// ============================================================================

/**
 * Validates if a value is a valid ToolStatus.
 */
export function isValidToolStatus(value: string): value is ToolStatus {
  const validStatuses: ToolStatus[] = [
    "success", "error", "partial_success", "in_progress", "complete"
  ];
  return validStatuses.includes(value as ToolStatus);
}

/**
 * Checks if tool execution is complete.
 */
export function isToolComplete(status: ToolStatus): boolean {
  return status === "success" || 
         status === "error" || 
         status === "complete";
}

/**
 * Checks if tool execution is in progress.
 */
export function isToolInProgress(status: ToolStatus): boolean {
  return status === "in_progress";
}

/**
 * Checks if tool execution was successful.
 */
export function isToolSuccessful(status: ToolStatus): boolean {
  return status === "success" || 
         status === "partial_success" || 
         status === "complete";
}

/**
 * Creates a basic ToolInput with minimal parameters.
 */
export function createToolInput(
  toolName: string,
  kwargs?: Record<string, unknown>
): ToolInput {
  return {
    tool_name: toolName,
    kwargs
  };
}

/**
 * Creates a ToolResult with execution timing.
 */
export function createToolResult(
  toolInput: ToolInput,
  status: ToolStatus,
  options: Partial<ToolResult> = {}
): ToolResult {
  return {
    tool_input: toolInput,
    status,
    start_time: options.start_time || Date.now(),
    ...options
  };
}

/**
 * Creates a ToolCallPayload for WebSocket communication.
 */
export function createToolCallPayload(
  toolName: string,
  callId: string,
  parameters?: Record<string, unknown>
): ToolCallPayload {
  return {
    tool_name: toolName,
    call_id: callId,
    parameters,
    timestamp: new Date().toISOString()
  };
}

/**
 * Creates a ToolResultPayload for WebSocket communication.
 */
export function createToolResultPayload(
  callId: string,
  result?: string | Record<string, unknown>,
  error?: string,
  executionTimeMs?: number
): ToolResultPayload {
  return {
    call_id: callId,
    result,
    error,
    execution_time_ms: executionTimeMs,
    timestamp: new Date().toISOString()
  };
}

// ============================================================================
// TYPE GUARDS - Runtime type checking
// ============================================================================

/**
 * Type guard for ToolCallPayload.
 */
export function isToolCallPayload(obj: unknown): obj is ToolCallPayload {
  if (typeof obj !== 'object' || obj === null) return false;
  const payload = obj as ToolCallPayload;
  return typeof payload.tool_name === 'string' &&
         typeof payload.call_id === 'string';
}

/**
 * Type guard for ToolResultPayload.
 */
export function isToolResultPayload(obj: unknown): obj is ToolResultPayload {
  if (typeof obj !== 'object' || obj === null) return false;
  const payload = obj as ToolResultPayload;
  return typeof payload.call_id === 'string';
}

// ============================================================================
// DEFAULT EXPORT - All tool utilities
// ============================================================================

export default {
  // Validation functions
  isValidToolStatus,
  isToolComplete,
  isToolInProgress,
  isToolSuccessful,
  
  // Creation functions
  createToolInput,
  createToolResult,
  createToolCallPayload,
  createToolResultPayload,
  
  // Type guards
  isToolCallPayload,
  isToolResultPayload
};