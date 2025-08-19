/**
 * Heartbeat Timing Fix Utilities
 * CRITICAL: Fixes heartbeat intervals causing timing conflicts in tests
 * Ensures proper cleanup and prevents infinite loops in tests
 * ≤300 lines, ≤8 lines per function
 */

import { act } from '@testing-library/react';

export interface HeartbeatConfig {
  interval: number;
  maxRetries: number;
  timeout: number;
  enabled: boolean;
}

export interface HeartbeatManager {
  start: () => void;
  stop: () => void;
  isRunning: () => boolean;
  getStats: () => HeartbeatStats;
  cleanup: () => void;
}

export interface HeartbeatStats {
  totalBeats: number;
  lastBeatTime: number;
  isActive: boolean;
  intervalId: number | null;
}

/**
 * Test-safe Heartbeat Manager
 */
export class TestHeartbeatManager implements HeartbeatManager {
  private config: HeartbeatConfig;
  private stats: HeartbeatStats;
  private intervalId: NodeJS.Timeout | null = null;
  private onBeat?: () => void;

  constructor(config: Partial<HeartbeatConfig> = {}, onBeat?: () => void) {
    this.config = {
      interval: config.interval || 1000,
      maxRetries: config.maxRetries || 3,
      timeout: config.timeout || 5000,
      enabled: config.enabled !== false
    };
    
    this.stats = {
      totalBeats: 0,
      lastBeatTime: 0,
      isActive: false,
      intervalId: null
    };
    
    this.onBeat = onBeat;
  }

  start(): void {
    if (!this.config.enabled || this.intervalId) return;

    act(() => {
      this.intervalId = setInterval(() => {
        this.beat();
      }, this.config.interval);
      
      this.stats.isActive = true;
      this.stats.intervalId = this.intervalId as any;
    });
  }

  stop(): void {
    if (!this.intervalId) return;

    act(() => {
      clearInterval(this.intervalId!);
      this.intervalId = null;
      this.stats.isActive = false;
      this.stats.intervalId = null;
    });
  }

  isRunning(): boolean {
    return this.intervalId !== null && this.stats.isActive;
  }

  getStats(): HeartbeatStats {
    return { ...this.stats };
  }

  cleanup(): void {
    this.stop();
    this.stats.totalBeats = 0;
    this.stats.lastBeatTime = 0;
  }

  private beat(): void {
    act(() => {
      this.stats.totalBeats++;
      this.stats.lastBeatTime = Date.now();
      this.onBeat?.();
    });
  }
}

/**
 * Heartbeat Registry to prevent conflicts
 */
export class HeartbeatRegistry {
  private static managers = new Map<string, TestHeartbeatManager>();

  static register(key: string, manager: TestHeartbeatManager): void {
    // Stop any existing manager with same key
    const existing = this.managers.get(key);
    if (existing) {
      existing.cleanup();
    }
    
    this.managers.set(key, manager);
  }

  static unregister(key: string): void {
    const manager = this.managers.get(key);
    if (manager) {
      manager.cleanup();
      this.managers.delete(key);
    }
  }

  static stopAll(): void {
    for (const manager of this.managers.values()) {
      manager.stop();
    }
  }

  static cleanupAll(): void {
    for (const manager of this.managers.values()) {
      manager.cleanup();
    }
    this.managers.clear();
  }

  static getManager(key: string): TestHeartbeatManager | undefined {
    return this.managers.get(key);
  }

  static getAllStats(): Record<string, HeartbeatStats> {
    const stats: Record<string, HeartbeatStats> = {};
    for (const [key, manager] of this.managers.entries()) {
      stats[key] = manager.getStats();
    }
    return stats;
  }
}

/**
 * Heartbeat utilities for tests
 */
export const HeartbeatUtils = {
  create: (config?: Partial<HeartbeatConfig>, onBeat?: () => void) => 
    new TestHeartbeatManager(config, onBeat),

  createAndRegister: (key: string, config?: Partial<HeartbeatConfig>, onBeat?: () => void) => {
    const manager = new TestHeartbeatManager(config, onBeat);
    HeartbeatRegistry.register(key, manager);
    return manager;
  },

  async waitForBeats(manager: TestHeartbeatManager, count: number, timeout = 5000): Promise<void> {
    const startTime = Date.now();
    const initialCount = manager.getStats().totalBeats;
    
    return new Promise((resolve, reject) => {
      const check = () => {
        const currentCount = manager.getStats().totalBeats;
        const beatsSinceStart = currentCount - initialCount;
        
        if (beatsSinceStart >= count) {
          resolve();
        } else if (Date.now() - startTime > timeout) {
          reject(new Error(`Timeout waiting for ${count} beats`));
        } else {
          setTimeout(check, 50);
        }
      };
      check();
    });
  },

  async withHeartbeat<T>(
    key: string,
    config: Partial<HeartbeatConfig>,
    operation: (manager: TestHeartbeatManager) => Promise<T>
  ): Promise<T> {
    const manager = HeartbeatUtils.createAndRegister(key, config);
    
    try {
      manager.start();
      return await operation(manager);
    } finally {
      HeartbeatRegistry.unregister(key);
    }
  },

  setupTestHeartbeat: (interval = 100) => {
    const config = { interval, enabled: true };
    return HeartbeatUtils.create(config);
  },

  async flushHeartbeats(): Promise<void> {
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
  }
};

/**
 * Mock WebSocket with heartbeat management
 */
export class MockWebSocketWithHeartbeat {
  private heartbeat: TestHeartbeatManager;
  private isConnected = false;
  private messages: string[] = [];

  constructor(heartbeatConfig?: Partial<HeartbeatConfig>) {
    this.heartbeat = new TestHeartbeatManager(
      { interval: 30000, ...heartbeatConfig },
      () => this.sendHeartbeat()
    );
  }

  connect(): void {
    act(() => {
      this.isConnected = true;
      this.heartbeat.start();
    });
  }

  disconnect(): void {
    act(() => {
      this.isConnected = false;
      this.heartbeat.stop();
    });
  }

  send(message: string): void {
    if (!this.isConnected) {
      throw new Error('Not connected');
    }
    this.messages.push(message);
  }

  getMessages(): string[] {
    return [...this.messages];
  }

  cleanup(): void {
    this.disconnect();
    this.heartbeat.cleanup();
    this.messages = [];
  }

  private sendHeartbeat(): void {
    if (this.isConnected) {
      this.messages.push('ping');
    }
  }

  getHeartbeatStats(): HeartbeatStats {
    return this.heartbeat.getStats();
  }
}

/**
 * Test environment setup for heartbeat management
 */
export const setupHeartbeatTestEnvironment = () => {
  let originalSetInterval: typeof global.setInterval;
  let originalClearInterval: typeof global.clearInterval;
  let activeIntervals: Set<NodeJS.Timeout> = new Set();

  const setup = () => {
    originalSetInterval = global.setInterval;
    originalClearInterval = global.clearInterval;

    global.setInterval = ((callback: Function, ms: number) => {
      const intervalId = originalSetInterval(() => {
        act(() => {
          callback();
        });
      }, ms);
      activeIntervals.add(intervalId);
      return intervalId;
    }) as any;

    global.clearInterval = (intervalId: NodeJS.Timeout) => {
      activeIntervals.delete(intervalId);
      return originalClearInterval(intervalId);
    };
  };

  const cleanup = () => {
    // Clear all active intervals
    for (const intervalId of activeIntervals) {
      originalClearInterval(intervalId);
    }
    activeIntervals.clear();

    // Restore original functions
    global.setInterval = originalSetInterval;
    global.clearInterval = originalClearInterval;

    // Cleanup all registered heartbeats
    HeartbeatRegistry.cleanupAll();
  };

  const getActiveIntervalCount = () => activeIntervals.size;

  return { setup, cleanup, getActiveIntervalCount };
};

/**
 * Heartbeat test wrapper
 */
export const withHeartbeatTestEnvironment = async <T>(
  testFn: () => Promise<T>
): Promise<T> => {
  const env = setupHeartbeatTestEnvironment();
  
  try {
    env.setup();
    return await testFn();
  } finally {
    env.cleanup();
  }
};

/**
 * Export utilities for common use
 */
export default {
  HeartbeatManager: TestHeartbeatManager,
  Registry: HeartbeatRegistry,
  Utils: HeartbeatUtils,
  MockWebSocketWithHeartbeat,
  setupTestEnvironment: setupHeartbeatTestEnvironment,
  withTestEnvironment: withHeartbeatTestEnvironment
};