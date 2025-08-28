/**
 * GTM-specific Circuit Breaker
 * Prevents infinite loops and excessive event tracking
 */

import { CircuitBreaker } from '@/lib/circuit-breaker';
import { logger } from '@/lib/logger';

export interface GTMEventKey {
  event: string;
  category: string;
  action: string;
  context?: string;
}

export class GTMCircuitBreaker {
  private circuitBreaker: CircuitBreaker;
  private recentEvents: Map<string, number> = new Map();
  private eventCounts: Map<string, number> = new Map();
  private readonly dedupeWindowMs = 2000; // 2 seconds deduplication window
  private readonly maxEventsPerType = 100; // Max events per type per minute
  private cleanupTimer?: NodeJS.Timeout;

  constructor() {
    this.circuitBreaker = new CircuitBreaker({
      failureThreshold: 50, // Trip after 50 events in window
      timeWindowMs: 10000, // 10 second window
      recoveryTimeoutMs: 30000 // 30 second recovery
    });

    // Start cleanup timer
    this.startCleanupTimer();
  }

  /**
   * Check if event should be allowed
   */
  canSendEvent(eventKey: GTMEventKey): boolean {
    // Check if circuit is open
    if (this.circuitBreaker.isOpen()) {
      logger.warn('GTM Circuit breaker is open - blocking event', {
        component: 'GTMCircuitBreaker',
        event: eventKey.event,
        category: eventKey.category
      });
      return false;
    }

    const key = this.createEventKey(eventKey);
    const now = Date.now();

    // Check for duplicate events within deduplication window
    const lastEventTime = this.recentEvents.get(key);
    if (lastEventTime && (now - lastEventTime) < this.dedupeWindowMs) {
      logger.debug('GTM event deduplicated', {
        component: 'GTMCircuitBreaker',
        event: eventKey.event,
        timeSinceLastEvent: now - lastEventTime
      });
      return false;
    }

    // Check rate limiting per event type
    const eventTypeKey = `${eventKey.category}:${eventKey.action}`;
    const count = this.eventCounts.get(eventTypeKey) || 0;
    if (count >= this.maxEventsPerType) {
      logger.warn('GTM event rate limit exceeded', {
        component: 'GTMCircuitBreaker',
        event: eventKey.event,
        count: count,
        maxAllowed: this.maxEventsPerType
      });
      this.circuitBreaker.recordFailure();
      return false;
    }

    return true;
  }

  /**
   * Record that an event was sent
   */
  recordEventSent(eventKey: GTMEventKey): void {
    const key = this.createEventKey(eventKey);
    const now = Date.now();

    // Update recent events for deduplication
    this.recentEvents.set(key, now);

    // Update event counts for rate limiting
    const eventTypeKey = `${eventKey.category}:${eventKey.action}`;
    const count = this.eventCounts.get(eventTypeKey) || 0;
    this.eventCounts.set(eventTypeKey, count + 1);

    // Record success with circuit breaker
    this.circuitBreaker.recordSuccess();
  }

  /**
   * Record an event failure
   */
  recordEventFailure(eventKey: GTMEventKey, error?: Error): void {
    this.circuitBreaker.recordFailure();
    
    logger.error('GTM event failed', error || new Error('Unknown GTM error'), {
      component: 'GTMCircuitBreaker',
      event: eventKey.event,
      category: eventKey.category
    });
  }

  /**
   * Create a unique key for an event
   */
  private createEventKey(eventKey: GTMEventKey): string {
    return `${eventKey.event}:${eventKey.category}:${eventKey.action}:${eventKey.context || 'default'}`;
  }

  /**
   * Start cleanup timer for old events
   */
  private startCleanupTimer(): void {
    this.cleanupTimer = setInterval(() => {
      this.cleanup();
    }, 60000); // Clean up every minute
  }

  /**
   * Clean up old event tracking data
   */
  private cleanup(): void {
    const now = Date.now();
    const cutoff = now - 60000; // 1 minute cutoff

    // Clean recent events older than cutoff
    for (const [key, timestamp] of this.recentEvents.entries()) {
      if (timestamp < cutoff) {
        this.recentEvents.delete(key);
      }
    }

    // Reset event counts every minute
    this.eventCounts.clear();

    logger.debug('GTM circuit breaker cleanup completed', {
      component: 'GTMCircuitBreaker',
      recentEventsSize: this.recentEvents.size
    });
  }

  /**
   * Check if circuit is open
   */
  isOpen(): boolean {
    return this.circuitBreaker.isOpen();
  }

  /**
   * Get current stats
   */
  getStats(): {
    isOpen: boolean;
    recentEventsCount: number;
    eventTypeCounts: Record<string, number>;
    circuitBreakerState: any;
  } {
    return {
      isOpen: this.circuitBreaker.isOpen(),
      recentEventsCount: this.recentEvents.size,
      eventTypeCounts: Object.fromEntries(this.eventCounts),
      circuitBreakerState: this.circuitBreaker.getState()
    };
  }

  /**
   * Reset circuit breaker
   */
  reset(): void {
    this.circuitBreaker.reset();
    this.recentEvents.clear();
    this.eventCounts.clear();
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = undefined;
    }
    this.circuitBreaker.destroy();
    this.recentEvents.clear();
    this.eventCounts.clear();
  }
}

// Singleton instance
let gtmCircuitBreakerInstance: GTMCircuitBreaker | null = null;

/**
 * Get singleton GTM circuit breaker instance
 */
export function getGTMCircuitBreaker(): GTMCircuitBreaker {
  if (!gtmCircuitBreakerInstance) {
    gtmCircuitBreakerInstance = new GTMCircuitBreaker();
  }
  return gtmCircuitBreakerInstance;
}