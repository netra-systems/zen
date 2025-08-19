/**
 * WebSocket Test Utilities
 * Shared utilities for WebSocket testing to reduce code duplication
 * Agent 10 Implementation - Modular test helpers
 */

export interface WebSocketConnectionLifecycle {
  connecting: boolean;
  connected: boolean;
  disconnected: boolean;
  error: boolean;
  reconnecting: boolean;
}

export interface MessageMetrics {
  sent: number;
  received: number;
  queued: number;
  failed: number;
  largeMessages: number;
}

export interface StreamingMetrics {
  messagesPerSecond: number;
  framesPerSecond: number;
  droppedFrames: number;
  bufferSize: number;
  backpressureEvents: number;
  latencyMs: number;
}

export interface MessageChunk {
  id: string;
  sequence: number;
  data: string;
  timestamp: number;
  size: number;
}

// Create message chunk utility
export const createMessageChunk = (data: string, sequence: number): MessageChunk => ({
  id: Math.random().toString(36).substr(2, 9),
  sequence,
  data,
  timestamp: Date.now(),
  size: data.length
});

// Generate large message for testing
export const generateLargeMessage = (sizeKB: number): string => {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  const size = sizeKB * 1024;
  return Array(size).fill(0).map(() => 
    chars[Math.floor(Math.random() * chars.length)]
  ).join('');
};

// Performance measurement utility
export const measurePerformance = async (operation: () => Promise<void>): Promise<number> => {
  const start = performance.now();
  await operation();
  return performance.now() - start;
};

// Connection state manager
export class ConnectionStateManager {
  private state: string = 'disconnected';
  private callbacks: ((state: string) => void)[] = [];

  setState(newState: string): void {
    this.state = newState;
    this.notifyCallbacks();
  }

  getState(): string { return this.state; }

  addCallback(callback: (state: string) => void): void {
    this.callbacks.push(callback);
  }

  private notifyCallbacks(): void {
    this.callbacks.forEach(callback => callback(this.state));
  }
}

// Message buffer for queue testing
export class MessageBuffer {
  private messages: string[] = [];
  private maxSize: number = 1000;

  add(message: string): boolean {
    if (this.messages.length >= this.maxSize) return false;
    this.messages.push(message);
    return true;
  }

  flush(): string[] {
    const messages = [...this.messages];
    this.messages = [];
    return messages;
  }

  size(): number { return this.messages.length; }
}