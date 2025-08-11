/**
 * CircularBuffer for efficient WebSocket event storage
 * Maintains a fixed-size buffer that overwrites oldest entries when full
 * Used for debugging and monitoring WebSocket events in the OverflowPanel
 */

export class CircularBuffer<T> {
  private buffer: (T | undefined)[];
  private maxSize: number;
  private pointer: number;
  private count: number;

  constructor(maxSize: number = 1000) {
    if (maxSize <= 0) {
      throw new Error('CircularBuffer maxSize must be greater than 0');
    }
    this.maxSize = maxSize;
    this.buffer = new Array(maxSize);
    this.pointer = 0;
    this.count = 0;
  }

  /**
   * Add an item to the buffer
   * Overwrites the oldest item if buffer is full
   */
  push(item: T): void {
    this.buffer[this.pointer] = item;
    this.pointer = (this.pointer + 1) % this.maxSize;
    if (this.count < this.maxSize) {
      this.count++;
    }
  }

  /**
   * Get all items in chronological order (oldest to newest)
   */
  getAll(): T[] {
    const result: T[] = [];
    
    if (this.count === 0) return result;
    
    if (this.count < this.maxSize) {
      // Buffer not full yet, return items from 0 to pointer
      for (let i = 0; i < this.count; i++) {
        result.push(this.buffer[i] as T);
      }
    } else {
      // Buffer is full, start from pointer (oldest) and wrap around
      for (let i = 0; i < this.maxSize; i++) {
        const index = (this.pointer + i) % this.maxSize;
        result.push(this.buffer[index] as T);
      }
    }
    
    return result;
  }

  /**
   * Get the last N items (most recent)
   */
  getLast(n: number): T[] {
    if (n <= 0) return [];
    
    const all = this.getAll();
    return all.slice(-Math.min(n, all.length));
  }

  /**
   * Get items that match a predicate
   */
  filter(predicate: (item: T) => boolean): T[] {
    return this.getAll().filter(predicate);
  }

  /**
   * Clear all items from the buffer
   */
  clear(): void {
    this.buffer = new Array(this.maxSize);
    this.pointer = 0;
    this.count = 0;
  }

  /**
   * Get the current size of the buffer
   */
  size(): number {
    return this.count;
  }

  /**
   * Check if the buffer is empty
   */
  isEmpty(): boolean {
    return this.count === 0;
  }

  /**
   * Check if the buffer is full
   */
  isFull(): boolean {
    return this.count === this.maxSize;
  }

  /**
   * Get buffer statistics
   */
  getStats(): {
    size: number;
    maxSize: number;
    utilization: number;
    isFull: boolean;
  } {
    return {
      size: this.count,
      maxSize: this.maxSize,
      utilization: (this.count / this.maxSize) * 100,
      isFull: this.isFull()
    };
  }
}

// Export a specialized version for WebSocket events
export interface WSEvent {
  type: string;
  payload: unknown;
  timestamp: number;
  source?: string;
  threadId?: string;
  runId?: string;
  agentName?: string;
}

export class WebSocketEventBuffer extends CircularBuffer<WSEvent> {
  constructor(maxSize: number = 1000) {
    super(maxSize);
  }

  /**
   * Get events by type
   */
  getByType(type: string): WSEvent[] {
    return this.filter(event => event.type === type);
  }

  /**
   * Get events for a specific agent
   */
  getByAgent(agentName: string): WSEvent[] {
    return this.filter(event => event.agentName === agentName);
  }

  /**
   * Get events within a time range
   */
  getByTimeRange(startTime: number, endTime: number): WSEvent[] {
    return this.filter(event => 
      event.timestamp >= startTime && event.timestamp <= endTime
    );
  }

  /**
   * Get event type statistics
   */
  getTypeStats(): Map<string, number> {
    const stats = new Map<string, number>();
    this.getAll().forEach(event => {
      const count = stats.get(event.type) || 0;
      stats.set(event.type, count + 1);
    });
    return stats;
  }

  /**
   * Export events as JSON
   */
  exportAsJSON(): string {
    return JSON.stringify({
      events: this.getAll(),
      stats: this.getStats(),
      typeStats: Array.from(this.getTypeStats().entries()).map(([type, count]) => ({
        type,
        count
      })),
      exportedAt: new Date().toISOString()
    }, null, 2);
  }
}