/**
 * Enhanced error handling for WebSocket event processing
 * Provides recovery mechanisms and detailed error tracking
 */

import { logger } from '@/lib/logger';
import { ErrorClassifier } from './error-classifier';
import { CircuitBreaker } from './circuit-breaker';
import { 
  EventError, 
  ErrorHandlerConfig, 
  ErrorHandlerStats,
  DEFAULT_ERROR_CONFIG 
} from './event-error-types';

export class EventErrorHandler {
  private errors: Map<string, EventError> = new Map();
  private config: ErrorHandlerConfig;
  private classifier: ErrorClassifier;
  private circuitBreaker: CircuitBreaker;

  constructor(config: Partial<ErrorHandlerConfig> = {}) {
    this.config = { ...DEFAULT_ERROR_CONFIG, ...config };
    this.classifier = new ErrorClassifier();
    this.circuitBreaker = new CircuitBreaker({
      failureThreshold: this.config.circuitBreakerThreshold,
      timeWindowMs: this.config.errorWindowMs,
      recoveryTimeoutMs: this.config.errorWindowMs / 2
    });
  }

  /**
   * Handle event processing error with recovery
   */
  async handleError(
    eventId: string,
    eventType: string,
    error: Error,
    retryCallback?: () => Promise<void>
  ): Promise<boolean> {
    const timestamp = Date.now();
    const severity = this.classifier.classifyError(error, eventType);
    
    // Record circuit breaker failure
    this.circuitBreaker.recordFailure();
    
    // Check circuit breaker
    if (this.circuitBreaker.isOpen()) {
      this.logCircuitBreakerOpen(error, eventId, eventType);
      return false;
    }

    // Get or create error record
    const errorRecord = this.getOrCreateErrorRecord(eventId, eventType, error, timestamp, severity);
    
    this.logError(errorRecord);

    // Attempt recovery if conditions are met
    if (this.shouldAttemptRecovery(errorRecord, retryCallback)) {
      return this.attemptRecovery(errorRecord, retryCallback!);
    }

    // Mark as permanent failure
    this.markPermanentFailure(errorRecord);
    return false;
  }

  /**
   * Get or create error record
   */
  private getOrCreateErrorRecord(
    eventId: string,
    eventType: string,
    error: Error,
    timestamp: number,
    severity: EventError['severity']
  ): EventError {
    let errorRecord = this.errors.get(eventId);
    
    if (!errorRecord) {
      errorRecord = {
        id: `${eventId}-${timestamp}`,
        eventId,
        eventType,
        error,
        timestamp,
        retryCount: 0,
        recovered: false,
        severity
      };
      this.errors.set(eventId, errorRecord);
    } else {
      errorRecord.retryCount++;
      errorRecord.error = error;
      errorRecord.timestamp = timestamp;
    }
    
    return errorRecord;
  }

  /**
   * Check if recovery should be attempted
   */
  private shouldAttemptRecovery(errorRecord: EventError, retryCallback?: () => Promise<void>): boolean {
    return this.config.enableRecovery && 
           errorRecord.retryCount < this.config.maxRetries &&
           retryCallback !== undefined &&
           !this.circuitBreaker.isOpen();
  }

  /**
   * Attempt to recover from error
   */
  private async attemptRecovery(
    errorRecord: EventError,
    retryCallback: () => Promise<void>
  ): Promise<boolean> {
    try {
      await this.delay(this.calculateRetryDelay(errorRecord.retryCount));
      await retryCallback();
      
      errorRecord.recovered = true;
      this.circuitBreaker.recordSuccess();
      
      this.logRecoverySuccess(errorRecord);
      return true;
      
    } catch (retryError) {
      this.logRecoveryFailure(errorRecord, retryError as Error);
      return false;
    }
  }

  /**
   * Calculate retry delay with exponential backoff
   */
  private calculateRetryDelay(retryCount: number): number {
    return this.config.retryDelay * Math.pow(2, retryCount);
  }

  /**
   * Log circuit breaker open event
   */
  private logCircuitBreakerOpen(error: Error, eventId: string, eventType: string): void {
    logger.error('Circuit breaker open - rejecting event', error, {
      component: 'EventErrorHandler',
      eventId,
      eventType,
      circuitBreakerState: this.circuitBreaker.getState()
    });
  }

  /**
   * Log error event
   */
  private logError(errorRecord: EventError): void {
    logger.error('Event processing error', errorRecord.error, {
      component: 'EventErrorHandler',
      eventId: errorRecord.eventId,
      eventType: errorRecord.eventType,
      retryCount: errorRecord.retryCount,
      severity: errorRecord.severity,
      errorMessage: errorRecord.error.message
    });
  }

  /**
   * Log recovery success
   */
  private logRecoverySuccess(errorRecord: EventError): void {
    logger.info('Event processing recovered successfully', {
      component: 'EventErrorHandler',
      eventId: errorRecord.eventId,
      eventType: errorRecord.eventType,
      retryCount: errorRecord.retryCount
    });
  }

  /**
   * Log recovery failure
   */
  private logRecoveryFailure(errorRecord: EventError, retryError: Error): void {
    logger.warn('Event recovery attempt failed', retryError, {
      component: 'EventErrorHandler',
      eventId: errorRecord.eventId,
      eventType: errorRecord.eventType,
      retryCount: errorRecord.retryCount
    });
  }

  /**
   * Mark error as permanent failure
   */
  private markPermanentFailure(errorRecord: EventError): void {
    logger.error('Event marked as permanent failure', errorRecord.error, {
      component: 'EventErrorHandler',
      eventId: errorRecord.eventId,
      eventType: errorRecord.eventType,
      retryCount: errorRecord.retryCount,
      severity: errorRecord.severity
    });
  }

  /**
   * Get error statistics
   */
  getStats(): ErrorHandlerStats {
    const allErrors = Array.from(this.errors.values());
    const totalErrors = allErrors.length;
    const recoveredErrors = allErrors.filter(e => e.recovered).length;
    const permanentFailures = allErrors.filter(e => 
      !e.recovered && e.retryCount >= this.config.maxRetries
    ).length;
    
    return {
      totalErrors,
      recoveredErrors,
      permanentFailures,
      circuitBreakerOpen: this.circuitBreaker.isOpen(),
      errorRate: this.circuitBreaker.getFailureRate(),
      lastErrorTimestamp: Math.max(...allErrors.map(e => e.timestamp), 0)
    };
  }

  /**
   * Get errors by severity
   */
  getErrorsBySeverity(severity: EventError['severity']): EventError[] {
    return Array.from(this.errors.values()).filter(e => e.severity === severity);
  }

  /**
   * Clear old errors
   */
  clearOldErrors(maxAge: number = 300000): void {
    const cutoff = Date.now() - maxAge;
    for (const [key, error] of this.errors.entries()) {
      if (error.timestamp < cutoff) {
        this.errors.delete(key);
      }
    }
  }

  /**
   * Reset error handler state
   */
  reset(): void {
    this.errors.clear();
    this.circuitBreaker.reset();
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.circuitBreaker.destroy();
    this.errors.clear();
  }

  /**
   * Utility delay function
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}