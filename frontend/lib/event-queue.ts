/**
 * Event Queue for WebSocket message processing
 * Provides atomic processing, deduplication, and proper ordering
 * Prevents race conditions in event handling
 */

import { logger } from '@/lib/logger';
import { EventErrorHandler } from '@/lib/event-error-handler';

export interface ProcessableEvent {
  id: string;
  type: string;
  payload: unknown;
  timestamp: number;
  source?: string;
}

export interface EventQueueStats {
  totalProcessed: number;
  totalDropped: number;
  totalErrors: number;
  queueSize: number;
  duplicatesDropped: number;
  lastProcessedTimestamp: number;
}

export interface EventQueueConfig {
  maxQueueSize: number;
  duplicateWindowMs: number;
  processingTimeoutMs: number;
  enableDeduplication: boolean;
}

export class EventQueue<T extends ProcessableEvent> {
  private queue: T[] = [];
  private processing = false;
  private processedIds = new Set<string>();
  private stats: EventQueueStats = {
    totalProcessed: 0,
    totalDropped: 0,
    totalErrors: 0,
    queueSize: 0,
    duplicatesDropped: 0,
    lastProcessedTimestamp: 0
  };
  
  private config: EventQueueConfig;
  private processor: (event: T) => Promise<void> | void;
  private cleanupTimer?: NodeJS.Timeout;
  private errorHandler: EventErrorHandler;

  constructor(
    processor: (event: T) => Promise<void> | void,
    config: Partial<EventQueueConfig> = {}
  ) {
    this.processor = processor;
    this.config = {
      maxQueueSize: 1000,
      duplicateWindowMs: 5000,
      processingTimeoutMs: 10000,
      enableDeduplication: true,
      ...config
    };
    
    this.errorHandler = new EventErrorHandler({
      maxRetries: 3,
      retryDelay: 1000,
      circuitBreakerThreshold: 10,
      errorWindowMs: 60000,
      enableRecovery: true
    });
    
    this.startCleanupTimer();
  }

  /**
   * Add event to queue with atomic processing
   */
  enqueue(event: T): boolean {
    // Check for duplicates if enabled
    if (this.config.enableDeduplication && this.isDuplicate(event)) {
      this.stats.duplicatesDropped++;
      logger.debug('Event dropped as duplicate', {
        component: 'EventQueue',
        eventId: event.id,
        eventType: event.type
      });
      return false;
    }

    // Check queue size limit
    if (this.queue.length >= this.config.maxQueueSize) {
      this.stats.totalDropped++;
      logger.warn('Event dropped due to queue overflow', {
        component: 'EventQueue',
        queueSize: this.queue.length,
        maxSize: this.config.maxQueueSize
      });
      return false;
    }

    // Add to queue maintaining timestamp order
    this.insertInOrder(event);
    this.stats.queueSize = this.queue.length;
    
    // Mark as seen for deduplication
    if (this.config.enableDeduplication) {
      this.processedIds.add(event.id);
    }

    // Start processing if not already running
    this.processQueue();
    
    return true;
  }

  /**
   * Process all queued events atomically
   */
  private async processQueue(): Promise<void> {
    if (this.processing || this.queue.length === 0) {
      return;
    }

    this.processing = true;
    
    try {
      while (this.queue.length > 0) {
        const event = this.queue.shift()!;
        await this.processEvent(event);
      }
    } catch (error) {
      logger.error('Queue processing failed', error as Error, {
        component: 'EventQueue',
        action: 'process_queue'
      });
    } finally {
      this.processing = false;
      this.stats.queueSize = this.queue.length;
    }
  }

  /**
   * Process single event with timeout and error handling
   */
  private async processEvent(event: T): Promise<void> {
    const startTime = Date.now();
    
    // Create timeout promise
    const createTimeoutPromise = () => new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error('Processing timeout')), 
        this.config.processingTimeoutMs);
    });
    
    try {
      // Process with timeout
      const processingPromise = Promise.resolve(this.processor(event));
      await Promise.race([processingPromise, createTimeoutPromise()]);
      
      this.stats.totalProcessed++;
      this.stats.lastProcessedTimestamp = event.timestamp;
      
      logger.debug('Event processed successfully', {
        component: 'EventQueue',
        eventId: event.id,
        eventType: event.type,
        processingTime: Date.now() - startTime
      });
      
    } catch (error) {
      this.stats.totalErrors++;
      
      // Use enhanced error handler for recovery
      const recovered = await this.errorHandler.handleError(
        event.id,
        event.type,
        error as Error,
        async () => {
          const retryPromise = Promise.resolve(this.processor(event));
          await Promise.race([retryPromise, createTimeoutPromise()]);
        }
      );
      
      if (recovered) {
        this.stats.totalProcessed++;
        this.stats.lastProcessedTimestamp = event.timestamp;
      }
      
      // Don't throw - continue processing other events
    }
  }

  /**
   * Insert event maintaining timestamp order
   */
  private insertInOrder(event: T): void {
    let insertIndex = this.queue.length;
    
    // Find correct position to maintain ordering
    for (let i = this.queue.length - 1; i >= 0; i--) {
      if (this.queue[i].timestamp <= event.timestamp) {
        break;
      }
      insertIndex = i;
    }
    
    this.queue.splice(insertIndex, 0, event);
  }

  /**
   * Check if event is duplicate
   */
  private isDuplicate(event: T): boolean {
    return this.processedIds.has(event.id);
  }

  /**
   * Start cleanup timer for processed IDs
   */
  private startCleanupTimer(): void {
    this.cleanupTimer = setInterval(() => {
      this.cleanupProcessedIds();
    }, this.config.duplicateWindowMs);
  }

  /**
   * Clean up old processed IDs to prevent memory leak
   */
  private cleanupProcessedIds(): void {
    const cutoffTime = Date.now() - this.config.duplicateWindowMs;
    
    // For Set-based tracking, we'll clear periodically
    // In production, consider using a time-aware data structure
    if (this.processedIds.size > 10000) {
      this.processedIds.clear();
      logger.debug('Cleared processed IDs cache', {
        component: 'EventQueue',
        action: 'cleanup_processed_ids'
      });
    }
  }

  /**
   * Get current queue statistics
   */
  getStats(): EventQueueStats & { errorHandler: any } {
    return { 
      ...this.stats, 
      queueSize: this.queue.length,
      errorHandler: this.errorHandler.getStats()
    };
  }

  /**
   * Clear queue and reset state
   */
  clear(): void {
    this.queue = [];
    this.processedIds.clear();
    this.stats = {
      totalProcessed: 0,
      totalDropped: 0,
      totalErrors: 0,
      queueSize: 0,
      duplicatesDropped: 0,
      lastProcessedTimestamp: 0
    };
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = undefined;
    }
    this.errorHandler.reset();
    this.clear();
  }
}

/**
 * Factory function to create WebSocket event queue
 */
export function createWebSocketEventQueue<T extends ProcessableEvent>(
  processor: (event: T) => Promise<void> | void,
  config?: Partial<EventQueueConfig>
): EventQueue<T> {
  return new EventQueue(processor, {
    maxQueueSize: 500,
    duplicateWindowMs: 3000,
    processingTimeoutMs: 5000,
    enableDeduplication: true,
    ...config
  });
}