/**
 * Unique ID Generator - SSOT Implementation for Frontend
 * 
 * CLAUDE.md Compliance:
 * - Single Source of Truth for all ID generation across frontend
 * - Fixes React key warnings from duplicate Date.now() timestamps
 * - Prevents cascade failures from inconsistent ID generation patterns
 * - Enables proper React reconciliation for chat interface (90% revenue impact)
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Infrastructure supporting all user tiers)
 * - Business Goal: Chat UI/UX reliability and user experience
 * - Value Impact: Prevents React rendering bugs that could damage user trust
 * - Strategic Impact: CRITICAL - Chat stability directly protects platform revenue
 * 
 * FIXES IDENTIFIED IN FIVE WHYS ANALYSIS:
 * 1. React Key Duplication - Date.now() returns identical timestamps in rapid succession
 * 2. No Collision Detection - No mechanism to ensure generated IDs are actually unique
 * 3. No Fallback Mechanisms - Single point of failure for uniqueness
 */

/**
 * Global counter for ID generation
 * Ensures uniqueness even within same millisecond
 */
let globalIdCounter = 0;

/**
 * Reset counter function for testing
 * Allows tests to have predictable ID generation
 */
export const resetGlobalCounter = (): void => {
  globalIdCounter = 0;
};

/**
 * Core unique ID generation function
 * Triple collision protection: timestamp + counter + random
 * 
 * @param prefix - String prefix for the ID (e.g., 'user', 'message', 'thread')
 * @param includeRandom - Whether to include random component (default: true)
 * @returns Guaranteed unique ID string
 */
export const generateUniqueId = (prefix: string = 'id', includeRandom: boolean = true): string => {
  const timestamp = Date.now();
  const counter = ++globalIdCounter;
  
  if (includeRandom) {
    const random = Math.random().toString(36).substr(2, 9);
    return `${prefix}-${timestamp}-${counter}-${random}`;
  }
  
  return `${prefix}-${timestamp}-${counter}`;
};

/**
 * Message ID generation for chat interface
 * Specialized for user/assistant message components
 * 
 * @param messageType - 'user' | 'assistant' | 'system'
 * @param threadId - Optional thread ID for context
 * @returns Unique message ID
 */
export const generateUniqueMessageId = (messageType: 'user' | 'assistant' | 'system', threadId?: string): string => {
  const baseId = generateUniqueId(messageType);
  return threadId ? `${baseId}-${threadId}` : baseId;
};

/**
 * Thread ID generation for conversation management
 * 
 * @param userId - Optional user ID for context
 * @returns Unique thread ID
 */
export const generateUniqueThreadId = (userId?: string): string => {
  const baseId = generateUniqueId('thread');
  return userId ? `${baseId}-${userId}` : baseId;
};

/**
 * Agent execution ID generation
 * For tracking agent workflows and tool executions
 * 
 * @param agentType - Type of agent (e.g., 'optimization', 'data', 'triage')
 * @param threadId - Thread context for the agent
 * @returns Unique agent execution ID
 */
export const generateUniqueAgentId = (agentType: string, threadId?: string): string => {
  const baseId = generateUniqueId(`agent-${agentType}`);
  return threadId ? `${baseId}-${threadId}` : baseId;
};

/**
 * Tool execution ID generation
 * For tracking individual tool invocations within agent workflows
 * 
 * @param toolName - Name of the tool being executed
 * @param agentId - Parent agent execution ID
 * @returns Unique tool execution ID
 */
export const generateUniqueToolId = (toolName: string, agentId?: string): string => {
  const baseId = generateUniqueId(`tool-${toolName}`);
  return agentId ? `${baseId}-${agentId}` : baseId;
};

/**
 * WebSocket event ID generation
 * For tracking WebSocket messages and events
 * 
 * @param eventType - Type of event (e.g., 'agent_started', 'tool_completed')
 * @param contextId - Context identifier (thread, agent, etc.)
 * @returns Unique event ID
 */
export const generateUniqueEventId = (eventType: string, contextId?: string): string => {
  const baseId = generateUniqueId(`event-${eventType}`);
  return contextId ? `${baseId}-${contextId}` : baseId;
};

/**
 * Component key generation for React rendering
 * Ensures unique keys for dynamic components in lists
 * 
 * @param componentType - Type of component (e.g., 'message', 'tool-result')
 * @param index - Optional list index for additional context
 * @returns Unique React key
 */
export const generateUniqueReactKey = (componentType: string, index?: number): string => {
  const baseId = generateUniqueId(componentType);
  return index !== undefined ? `${baseId}-${index}` : baseId;
};

/**
 * Batch ID generation for bulk operations
 * Generates multiple unique IDs efficiently
 * 
 * @param prefix - Common prefix for all IDs
 * @param count - Number of IDs to generate
 * @returns Array of unique IDs
 */
export const generateBatchUniqueIds = (prefix: string, count: number): string[] => {
  const ids: string[] = [];
  const timestamp = Date.now();
  
  for (let i = 0; i < count; i++) {
    const counter = ++globalIdCounter;
    const random = Math.random().toString(36).substr(2, 9);
    ids.push(`${prefix}-${timestamp}-${counter}-${random}`);
  }
  
  return ids;
};

/**
 * ID validation function
 * Validates that an ID follows the expected format
 * 
 * @param id - ID string to validate
 * @param expectedPrefix - Expected prefix (optional)
 * @returns Boolean indicating if ID is valid
 */
export const isValidUniqueId = (id: string, expectedPrefix?: string): boolean => {
  if (!id || typeof id !== 'string') return false;
  
  // Basic format check: prefix-timestamp-counter-random (or prefix-timestamp-counter)
  const parts = id.split('-');
  if (parts.length < 3) return false;
  
  // Check prefix if provided
  if (expectedPrefix && parts[0] !== expectedPrefix) return false;
  
  // Check timestamp is numeric
  const timestamp = parseInt(parts[1], 10);
  if (isNaN(timestamp) || timestamp <= 0) return false;
  
  // Check counter is numeric
  const counter = parseInt(parts[2], 10);
  if (isNaN(counter) || counter <= 0) return false;
  
  return true;
};

/**
 * Extract components from generated ID
 * Useful for debugging and analytics
 * 
 * @param id - Generated unique ID
 * @returns Object with ID components or null if invalid
 */
export const parseUniqueId = (id: string): { prefix: string; timestamp: number; counter: number; random?: string } | null => {
  if (!isValidUniqueId(id)) return null;
  
  const parts = id.split('-');
  const result = {
    prefix: parts[0],
    timestamp: parseInt(parts[1], 10),
    counter: parseInt(parts[2], 10),
    random: parts[3] // May be undefined for IDs without random component
  };
  
  return result;
};

/**
 * Get ID age in milliseconds
 * Useful for cache invalidation and analytics
 * 
 * @param id - Generated unique ID
 * @returns Age in milliseconds or -1 if invalid ID
 */
export const getIdAge = (id: string): number => {
  const parsed = parseUniqueId(id);
  if (!parsed) return -1;
  
  return Date.now() - parsed.timestamp;
};

/**
 * Test utilities for predictable ID generation
 * Only used in test environment
 */
export const TestIdUtils = {
  /**
   * Reset all counters for test isolation
   */
  reset: (): void => {
    resetGlobalCounter();
  },
  
  /**
   * Generate predictable ID for testing
   */
  createTestId: (prefix: string, sequenceNumber: number): string => {
    return `${prefix}-test-${sequenceNumber}`;
  },
  
  /**
   * Create a series of test IDs
   */
  createTestIdSeries: (prefix: string, count: number): string[] => {
    const ids: string[] = [];
    for (let i = 1; i <= count; i++) {
      ids.push(`${prefix}-test-${i}`);
    }
    return ids;
  },
  
  /**
   * Validate ID uniqueness in an array
   */
  validateUniquenesInArray: (ids: string[]): boolean => {
    const seen = new Set<string>();
    for (const id of ids) {
      if (seen.has(id)) return false;
      seen.add(id);
    }
    return true;
  }
};

/**
 * Convenience function for simple message ID generation
 * Used by WebSocketProvider and other components that need basic message IDs
 * 
 * @param messageType - Optional message type prefix (defaults to 'message')
 * @returns Unique message ID
 */
export const generateMessageId = (messageType: string = 'message'): string => {
  return generateUniqueId(messageType);
};

/**
 * Temporary ID generation for optimistic updates
 * Creates IDs that are clearly marked as temporary for reconciliation
 * 
 * @param prefix - Prefix for the temporary ID
 * @returns Unique temporary ID with 'temp' marker
 */
export const generateTemporaryId = (prefix: string): string => {
  return generateUniqueId(`temp-${prefix}`);
};

/**
 * Default exports for common use cases
 */
export default {
  generateUniqueId,
  generateUniqueMessageId,
  generateUniqueThreadId,
  generateUniqueAgentId,
  generateUniqueToolId,
  generateUniqueEventId,
  generateUniqueReactKey,
  generateBatchUniqueIds,
  generateMessageId,
  generateTemporaryId,
  isValidUniqueId,
  parseUniqueId,
  getIdAge,
  TestIdUtils
};