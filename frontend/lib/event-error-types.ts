/**
 * Type definitions for event error handling
 * Separated for modularity and compliance with 450-line limit
 */

export interface EventError {
  id: string;
  eventId: string;
  eventType: string;
  error: Error;
  timestamp: number;
  retryCount: number;
  recovered: boolean;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export interface ErrorHandlerConfig {
  maxRetries: number;
  retryDelay: number;
  circuitBreakerThreshold: number;
  errorWindowMs: number;
  enableRecovery: boolean;
}

export interface ErrorHandlerStats {
  totalErrors: number;
  recoveredErrors: number;
  permanentFailures: number;
  circuitBreakerOpen: boolean;
  errorRate: number;
  lastErrorTimestamp: number;
}

export interface ErrorClassification {
  pattern: string;
  severity: EventError['severity'];
  recoverable: boolean;
}

export interface RetryStrategy {
  maxAttempts: number;
  baseDelay: number;
  backoffMultiplier: number;
  jitter: boolean;
}

/**
 * Default error classifications
 */
export const DEFAULT_ERROR_CLASSIFICATIONS: ErrorClassification[] = [
  {
    pattern: 'network|connection|timeout',
    severity: 'critical',
    recoverable: true
  },
  {
    pattern: 'parse|validation|type',
    severity: 'high',
    recoverable: false
  },
  {
    pattern: 'agent',
    severity: 'medium',
    recoverable: true
  }
];

/**
 * Default error handler configuration
 */
export const DEFAULT_ERROR_CONFIG: ErrorHandlerConfig = {
  maxRetries: 3,
  retryDelay: 1000,
  circuitBreakerThreshold: 10,
  errorWindowMs: 60000,
  enableRecovery: true
};

/**
 * Default retry strategy
 */
export const DEFAULT_RETRY_STRATEGY: RetryStrategy = {
  maxAttempts: 3,
  baseDelay: 1000,
  backoffMultiplier: 2,
  jitter: true
};