/**
 * UNIFIED Tool Types - Single Source of Truth
 * 
 * Consolidates ALL tool-related types from:
 * - types/domains/tools.ts
 * - types/Tool.ts
 * - types/tools.ts
 * - types/backend_schema_tools.ts
 * - types/websocket-event-types.ts
 * 
 * CRITICAL: This file replaces ALL other tool type definitions
 * Use ONLY these types for tool operations
 */

// Re-export ALL tool types from domains (the authoritative source)
export type {
  // Core tool types
  ToolStatus,
  ToolInput,
  ToolResult,
  ReferenceItem,
  
  // WebSocket tool communication
  ToolCallPayload,
  ToolResultPayload,
  
  // Frontend UI tool types
  ToolCompleted,
  ToolStarted,
  ToolResultData
} from '../domains/tools';

// Re-export all utility functions
export {
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
} from '../domains/tools';

// Re-export default utilities
export { default as ToolUtils } from '../domains/tools';