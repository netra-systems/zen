/**
 * UNIFIED Metrics Types - Single Source of Truth
 * 
 * Consolidates ALL metrics-related types from:
 * - types/performance-metrics.ts
 * - types/agent-types.ts (AgentMetrics)
 * - components/chat/layers/ExecutionMetricsSection.tsx
 * - components/chat/types/FinalReportTypes.ts
 * - hooks/useChatWebSocket.ts
 * - services/animation-engine.ts
 * 
 * CRITICAL: This file replaces ALL other metrics type definitions
 * Use ONLY these types for performance and agent metrics
 */

// ============================================================================
// PERFORMANCE METRICS (from performance-metrics.ts)
// ============================================================================

export type {
  PerformanceMetrics,
  MetricsOptions,
  PerformanceReport,
  PerformanceMonitorInterface,
  PerformanceCategory
} from '../performance-metrics';

export {
  DEFAULT_PERFORMANCE_METRICS,
  PERFORMANCE_THRESHOLDS,
  METRICS_FIELD_MAPPING
} from '../performance-metrics';

// ============================================================================
// AGENT METRICS (from agent-types.ts)
// ============================================================================

export type { AgentMetrics } from '../agent-types';

// ============================================================================
// EXECUTION METRICS (commonly used in components)
// ============================================================================

/**
 * Execution metrics for agent runs and tool executions
 * Standardized interface used across all execution contexts
 */
export interface ExecutionMetrics {
  // Core timing
  startTime: number;
  endTime?: number;
  duration?: number;
  
  // Performance tracking
  renderTime?: number;
  processingTime?: number;
  responseTime?: number;
  
  // Resource usage
  memoryUsage?: number;
  cpuUsage?: number;
  
  // API and token tracking
  apiCalls?: number;
  tokensUsed?: number;
  tokenCost?: number;
  
  // Success metrics
  successRate?: number;
  errorCount?: number;
  
  // Tool-specific metrics
  toolsExecuted?: number;
  toolExecutionTime?: number;
}

/**
 * Unified metrics interface combining all metric types
 * Used for comprehensive system monitoring
 */
export interface UnifiedMetrics {
  performance: PerformanceMetrics;
  agent?: AgentMetrics;
  execution?: ExecutionMetrics;
  timestamp: string;
  context?: string; // component or operation context
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Creates default execution metrics
 */
export function createExecutionMetrics(startTime?: number): ExecutionMetrics {
  return {
    startTime: startTime || Date.now(),
    errorCount: 0,
    successRate: 100
  };
}

/**
 * Updates execution metrics with completion data
 */
export function completeExecutionMetrics(
  metrics: ExecutionMetrics,
  success: boolean = true
): ExecutionMetrics {
  const endTime = Date.now();
  const duration = endTime - metrics.startTime;
  
  return {
    ...metrics,
    endTime,
    duration,
    successRate: success ? 100 : 0,
    errorCount: success ? 0 : 1
  };
}

/**
 * Combines performance and agent metrics into unified format
 */
export function createUnifiedMetrics(
  performance: PerformanceMetrics,
  agent?: AgentMetrics,
  execution?: ExecutionMetrics,
  context?: string
): UnifiedMetrics {
  return {
    performance,
    agent,
    execution,
    timestamp: new Date().toISOString(),
    context
  };
}

/**
 * Calculates average metrics from an array of execution metrics
 */
export function calculateAverageMetrics(metrics: ExecutionMetrics[]): ExecutionMetrics | null {
  if (metrics.length === 0) return null;
  
  const totals = metrics.reduce((acc, metric) => ({
    duration: (acc.duration || 0) + (metric.duration || 0),
    renderTime: (acc.renderTime || 0) + (metric.renderTime || 0),
    processingTime: (acc.processingTime || 0) + (metric.processingTime || 0),
    responseTime: (acc.responseTime || 0) + (metric.responseTime || 0),
    memoryUsage: (acc.memoryUsage || 0) + (metric.memoryUsage || 0),
    cpuUsage: (acc.cpuUsage || 0) + (metric.cpuUsage || 0),
    apiCalls: (acc.apiCalls || 0) + (metric.apiCalls || 0),
    tokensUsed: (acc.tokensUsed || 0) + (metric.tokensUsed || 0),
    tokenCost: (acc.tokenCost || 0) + (metric.tokenCost || 0),
    successRate: (acc.successRate || 0) + (metric.successRate || 0),
    errorCount: (acc.errorCount || 0) + (metric.errorCount || 0),
    toolsExecuted: (acc.toolsExecuted || 0) + (metric.toolsExecuted || 0),
    toolExecutionTime: (acc.toolExecutionTime || 0) + (metric.toolExecutionTime || 0),
  }), {} as Record<string, number>);
  
  const count = metrics.length;
  const averageStartTime = Math.min(...metrics.map(m => m.startTime));
  
  return {
    startTime: averageStartTime,
    duration: Math.round(totals.duration / count),
    renderTime: Math.round(totals.renderTime / count),
    processingTime: Math.round(totals.processingTime / count),
    responseTime: Math.round(totals.responseTime / count),
    memoryUsage: Math.round(totals.memoryUsage / count),
    cpuUsage: Math.round(totals.cpuUsage / count),
    apiCalls: Math.round(totals.apiCalls / count),
    tokensUsed: Math.round(totals.tokensUsed / count),
    tokenCost: totals.tokenCost / count,
    successRate: totals.successRate / count,
    errorCount: Math.round(totals.errorCount / count),
    toolsExecuted: Math.round(totals.toolsExecuted / count),
    toolExecutionTime: Math.round(totals.toolExecutionTime / count),
  };
}

// ============================================================================
// TYPE GUARDS
// ============================================================================

/**
 * Type guard for ExecutionMetrics
 */
export function isExecutionMetrics(obj: unknown): obj is ExecutionMetrics {
  return typeof obj === 'object' && 
         obj !== null && 
         'startTime' in obj &&
         typeof (obj as ExecutionMetrics).startTime === 'number';
}

/**
 * Type guard for UnifiedMetrics
 */
export function isUnifiedMetrics(obj: unknown): obj is UnifiedMetrics {
  return typeof obj === 'object' && 
         obj !== null && 
         'performance' in obj && 
         'timestamp' in obj;
}

// ============================================================================
// CONSTANTS
// ============================================================================

/**
 * Metric collection intervals (in milliseconds)
 */
export const METRICS_INTERVALS = {
  PERFORMANCE_UPDATE: 1000,    // 1 second
  AGENT_STATUS_UPDATE: 500,    // 500ms
  EXECUTION_SAMPLE: 100,       // 100ms for high-frequency sampling
  REPORT_GENERATION: 30000,    // 30 seconds
} as const;

/**
 * Metric thresholds for alerting
 */
export const METRICS_THRESHOLDS = {
  ...PERFORMANCE_THRESHOLDS,
  MAX_EXECUTION_TIME: 30000,   // 30 seconds
  MAX_MEMORY_PER_AGENT: 256,   // MB
  MAX_TOKEN_COST: 1.0,         // $1 per operation
  MIN_SUCCESS_RATE: 95,        // 95%
} as const;