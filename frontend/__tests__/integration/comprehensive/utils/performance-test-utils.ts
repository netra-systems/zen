/**
 * Performance Test Utilities
 * Utilities for testing performance, conflict resolution, and operation history
 */

// Performance thresholds for various operations
export const PERFORMANCE_THRESHOLDS = {
  RENDER: 100,           // Max render time in ms
  INTERACTION: 50,       // Max interaction response time in ms
  WEBSOCKET: 200,        // Max WebSocket message processing time in ms
  STATE_UPDATE: 30,      // Max state update time in ms
  CONFLICT_RESOLUTION: 500, // Max conflict resolution time in ms
  HISTORY_OPERATION: 100    // Max history operation time in ms
};

// Conflict type definitions
interface Conflict {
  id: string;
  type: 'content' | 'state' | 'order';
  localValue: any;
  remoteValue: any;
  timestamp: number;
}

// Operation history types
interface HistoryEntry {
  id: string;
  operation: 'add' | 'update' | 'delete';
  data: any;
  timestamp: number;
  userId: string;
}

// History management state
const operationHistory: HistoryEntry[] = [];
let historyPointer = -1;

/**
 * Create a conflict scenario
 */
export function createConflict(
  type: 'content' | 'state' | 'order',
  localValue: any,
  remoteValue: any
): Conflict {
  return {
    id: `conflict-${Date.now()}-${Math.random()}`,
    type,
    localValue,
    remoteValue,
    timestamp: Date.now()
  };
}

/**
 * Resolve content conflicts using last-write-wins strategy
 */
export function resolveConflictContent(conflict: Conflict): any {
  // Simple last-write-wins strategy
  // In real implementation, this would use more sophisticated CRDT or OT algorithms
  return conflict.timestamp > Date.now() - 1000 
    ? conflict.localValue 
    : conflict.remoteValue;
}

/**
 * Add operation to history
 */
export function addToHistory(
  operation: 'add' | 'update' | 'delete',
  data: any,
  userId: string = 'test-user'
): void {
  const entry: HistoryEntry = {
    id: `history-${Date.now()}-${Math.random()}`,
    operation,
    data,
    timestamp: Date.now(),
    userId
  };
  
  // If we're not at the end of history, remove everything after current position
  if (historyPointer < operationHistory.length - 1) {
    operationHistory.splice(historyPointer + 1);
  }
  
  operationHistory.push(entry);
  historyPointer = operationHistory.length - 1;
}

/**
 * Trim history to maintain performance
 */
export function trimHistory(maxEntries: number = 100): void {
  if (operationHistory.length > maxEntries) {
    const toRemove = operationHistory.length - maxEntries;
    operationHistory.splice(0, toRemove);
    historyPointer = Math.max(0, historyPointer - toRemove);
  }
}

/**
 * Check if undo is available
 */
export function canUndo(): boolean {
  return historyPointer > 0;
}

/**
 * Check if redo is available
 */
export function canRedo(): boolean {
  return historyPointer < operationHistory.length - 1;
}

/**
 * Perform undo operation
 */
export function undo(): HistoryEntry | null {
  if (canUndo()) {
    historyPointer--;
    return operationHistory[historyPointer];
  }
  return null;
}

/**
 * Perform redo operation
 */
export function redo(): HistoryEntry | null {
  if (canRedo()) {
    historyPointer++;
    return operationHistory[historyPointer];
  }
  return null;
}

/**
 * Clear history
 */
export function clearHistory(): void {
  operationHistory.length = 0;
  historyPointer = -1;
}

/**
 * Measure performance of an operation
 */
export async function measurePerformance<T>(
  operation: () => T | Promise<T>,
  threshold: number
): Promise<{ result: T; duration: number; withinThreshold: boolean }> {
  const start = performance.now();
  const result = await operation();
  const duration = performance.now() - start;
  
  return {
    result,
    duration,
    withinThreshold: duration <= threshold
  };
}

/**
 * Simulate network latency
 */
export function simulateLatency(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Create mock collaborative session
 */
export function createCollaborativeSession(userId: string = 'test-user') {
  return {
    userId,
    sessionId: `session-${Date.now()}`,
    participants: [userId],
    startTime: Date.now(),
    operations: [] as HistoryEntry[]
  };
}