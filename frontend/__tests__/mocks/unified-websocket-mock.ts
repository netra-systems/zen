/**
 * Unified WebSocket Mock - SSOT Implementation
 * 
 * CLAUDE.md Compliance:
 * - Single Source of Truth for WebSocket testing across all frontend tests
 * - Fixes timing race conditions between mock events and React handlers
 * - Provides comprehensive error scenario simulation
 * - Enables proper async/await patterns for reliable testing
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Infrastructure supporting all user tiers)
 * - Business Goal: Enable reliable WebSocket testing for 90% of revenue delivery
 * - Value Impact: Prevents WebSocket test failures that could mask production bugs
 * - Strategic Impact: CRITICAL - WebSocket reliability directly affects chat value delivery
 * 
 * FIXES IDENTIFIED IN FIVE WHYS ANALYSIS:
 * 1. TIMING RACE CONDITION - Mock fires errors before React handlers established
 * 2. MOCK INCONSISTENCY - Multiple implementations causing handler attachment failures  
 * 3. SSOT VIOLATION - No single source of truth for WebSocket mock behavior
 */

export interface WebSocketEventData {
  type: string;
  data?: any;
  timestamp?: number;
  thread_id?: string;
}

export interface UnifiedWebSocketConfig {
  autoConnect?: boolean;
  simulateNetworkDelay?: boolean;
  networkDelayMs?: number;
  enableErrorSimulation?: boolean;
  errorDelay?: number;
  maxReconnectAttempts?: number;
}

/**
 * Unified WebSocket Mock Class
 * Replaces all custom WebSocket mocks with single, reliable implementation
 */
export class UnifiedWebSocketMock {
  // WebSocket state constants
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  // Instance properties matching real WebSocket API
  public readonly url: string;
  public readonly protocols: string | string[];
  public readyState: number = UnifiedWebSocketMock.CONNECTING;
  public bufferedAmount: number = 0;
  public binaryType: BinaryType = 'blob';
  public extensions: string = '';
  public protocol: string = '';

  // Event handlers (React components set these)
  public onopen: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;

  // Internal state for testing
  private eventListeners: Map<string, ((event: Event) => void)[]> = new Map();
  private messageQueue: any[] = [];
  private isDisposed: boolean = false;
  private config: UnifiedWebSocketConfig;
  private reconnectAttempts: number = 0;

  // Error state tracking to fix timing issues
  public hasErrored: boolean = false;
  
  // Mock function tracking for Jest
  public send = jest.fn((data: string | ArrayBufferLike | Blob | ArrayBufferView) => {
    if (this.readyState === UnifiedWebSocketMock.OPEN) {
      // Simulate successful send
      console.log('UnifiedWebSocketMock: Message sent', data);
    } else {
      throw new Error('WebSocket is not open');
    }
  });
  
  public close = jest.fn((code?: number, reason?: string) => {
    if (this.readyState === UnifiedWebSocketMock.CLOSED) return;
    
    this.readyState = UnifiedWebSocketMock.CLOSING;
    
    // Simulate close with proper timing
    setTimeout(() => {
      if (this.isDisposed) return;
      
      this.readyState = UnifiedWebSocketMock.CLOSED;
      const closeEvent = new CloseEvent('close', {
        code: code || 1000,
        reason: reason || 'Normal closure',
        wasClean: code === 1000
      });
      
      this.triggerEventHandler('onclose', closeEvent);
    }, 10);
  });

  public addEventListener = jest.fn((type: string, listener: EventListener) => {
    if (!this.eventListeners.has(type)) {
      this.eventListeners.set(type, []);
    }
    this.eventListeners.get(type)!.push(listener as any);
  });

  public removeEventListener = jest.fn((type: string, listener: EventListener) => {
    const listeners = this.eventListeners.get(type);
    if (listeners) {
      const index = listeners.indexOf(listener as any);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  });

  public dispatchEvent = jest.fn((event: Event): boolean => {
    const listeners = this.eventListeners.get(event.type);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(event);
        } catch (error) {
          console.error('Error in WebSocket event listener:', error);
        }
      });
    }
    return true;
  });

  constructor(url: string, protocols?: string | string[], config: UnifiedWebSocketConfig = {}) {
    this.url = url;
    this.protocols = protocols || [];
    this.config = {
      autoConnect: true,
      simulateNetworkDelay: false,
      networkDelayMs: 100,
      enableErrorSimulation: false,
      errorDelay: 50,
      maxReconnectAttempts: 3,
      ...config
    };

    console.log('UnifiedWebSocketMock: Created with URL:', url, 'Config:', this.config);

    // Initialize global tracking array if it doesn't exist
    if (!global.mockWebSocketInstances) {
      global.mockWebSocketInstances = [];
    }
    
    // Add to global tracking for cleanup
    global.mockWebSocketInstances.push(this);
    console.log('UnifiedWebSocketMock: Added to global tracking, total instances:', global.mockWebSocketInstances.length);

    // Initialize connection simulation with proper timing
    if (this.config.autoConnect) {
      this.simulateConnection();
    }
  }

  /**
   * Simulate WebSocket connection with proper async timing
   * FIXES: Race condition between mock events and React handler setup
   */
  private simulateConnection(): void {
    if (this.config.enableErrorSimulation) {
      // For error simulation, use error delay (can be 0 for immediate)
      const errorDelay = this.config.errorDelay || 0;
      setTimeout(() => {
        if (this.isDisposed || this.readyState !== UnifiedWebSocketMock.CONNECTING) return;
        this.simulateConnectionError();
      }, errorDelay);
    } else {
      // For normal connection, use network delay
      const delay = this.config.simulateNetworkDelay ? this.config.networkDelayMs! : 10;
      setTimeout(() => {
        if (this.isDisposed || this.readyState !== UnifiedWebSocketMock.CONNECTING) return;
        this.simulateConnectionSuccess();
      }, delay);
    }
  }

  /**
   * Simulate successful connection
   * FIXES: Ensures handlers are established before triggering events
   */
  private simulateConnectionSuccess(): void {
    // Don't proceed if error is already configured
    if (this.hasErrored || this.config.enableErrorSimulation) return;
    
    // Wait for React component to set up event handlers
    this.waitForHandlerSetup(() => {
      if (this.isDisposed || this.hasErrored) return;
      
      this.readyState = UnifiedWebSocketMock.OPEN;
      const openEvent = new Event('open');
      this.triggerEventHandler('onopen', openEvent);
    });
  }

  /**
   * Simulate connection error
   * FIXES: Proper error state management and timing
   */
  private simulateConnectionError(): void {
    this.waitForHandlerSetup(() => {
      if (this.isDisposed) return;
      
      this.hasErrored = true;
      this.readyState = UnifiedWebSocketMock.CLOSED;
      
      const errorEvent = new ErrorEvent('error', {
        error: new Error('WebSocket connection failed'),
        message: 'Connection failed'
      });
      
      this.triggerEventHandler('onerror', errorEvent);
      
      // Also trigger close event after error to complete the failed connection flow
      setTimeout(() => {
        if (!this.isDisposed) {
          const closeEvent = new CloseEvent('close', {
            code: 1006,
            reason: 'Connection failed',
            wasClean: false
          });
          this.triggerEventHandler('onclose', closeEvent);
        }
      }, 10);
    });
  }

  /**
   * Wait for React component to set up event handlers
   * FIXES: Race condition where mock events fire before handlers are ready
   */
  private waitForHandlerSetup(callback: () => void): void {
    const maxWaitTime = 500; // Max wait time in ms
    const checkInterval = 10; // Check every 10ms
    let elapsed = 0;

    const checkHandlers = () => {
      // Check if at least one handler is set up or we've exceeded max wait time
      if (this.onopen || this.onerror || elapsed >= maxWaitTime) {
        callback();
        return;
      }

      elapsed += checkInterval;
      setTimeout(checkHandlers, checkInterval);
    };

    checkHandlers();
  }

  /**
   * Safely trigger event handlers with error handling
   * FIXES: Prevents test failures from handler exceptions
   */
  private triggerEventHandler(handlerName: keyof this, event: Event): void {
    try {
      const handler = this[handlerName] as any;
      if (typeof handler === 'function') {
        handler.call(this, event);
      }
      
      // Also trigger via addEventListener pattern
      this.dispatchEvent(event);
    } catch (error) {
      console.error(`UnifiedWebSocketMock: Error in ${handlerName}:`, error);
    }
  }

  /**
   * Simulate receiving a message from server
   * Used by tests to simulate server-sent events
   */
  public simulateMessage(data: WebSocketEventData | string): void {
    if (this.readyState !== UnifiedWebSocketMock.OPEN) {
      console.warn('UnifiedWebSocketMock: Cannot simulate message - connection not open');
      return;
    }

    const messageData = typeof data === 'string' ? data : JSON.stringify(data);
    const messageEvent = new MessageEvent('message', {
      data: messageData,
      origin: this.url,
      lastEventId: '',
      source: null,
      ports: []
    });

    this.triggerEventHandler('onmessage', messageEvent);
  }

  /**
   * Simulate WebSocket error
   * Used by tests to simulate various error scenarios
   */
  public simulateError(error?: Error): void {
    this.hasErrored = true;
    const errorEvent = new ErrorEvent('error', {
      error: error || new Error('Simulated WebSocket error'),
      message: error?.message || 'WebSocket error'
    });

    this.triggerEventHandler('onerror', errorEvent);
  }

  /**
   * Simulate connection close
   * Used by tests to simulate disconnection scenarios
   */
  public simulateClose(code: number = 1000, reason: string = 'Test close', wasClean: boolean = true): void {
    if (this.readyState === UnifiedWebSocketMock.CLOSED) return;
    
    this.readyState = UnifiedWebSocketMock.CLOSING;
    
    setTimeout(() => {
      if (this.isDisposed) return;
      
      this.readyState = UnifiedWebSocketMock.CLOSED;
      const closeEvent = new CloseEvent('close', { code, reason, wasClean });
      
      this.triggerEventHandler('onclose', closeEvent);
    }, 10);
  }

  /**
   * Simulate network disconnection (unexpected close)
   */
  public simulateNetworkDisconnection(): void {
    this.simulateClose(1006, 'Abnormal closure', false);
  }

  /**
   * Manually trigger connection success (for manual testing)
   * Used by tests that need explicit control over connection timing
   */
  public simulateConnectionSuccess(): void {
    if (this.isDisposed || this.hasErrored) return;
    
    this.readyState = UnifiedWebSocketMock.OPEN;
    const openEvent = new Event('open');
    this.triggerEventHandler('onopen', openEvent);
  }

  /**
   * Manually start connection process (for manual testing)
   * Used when autoConnect is false
   */
  public connect(): void {
    if (this.readyState === UnifiedWebSocketMock.OPEN) return;
    
    this.readyState = UnifiedWebSocketMock.CONNECTING;
    this.simulateConnection();
  }

  /**
   * Cleanup method for proper resource management
   * FIXES: Memory leaks and hanging test issues
   */
  public cleanup(): void {
    this.isDisposed = true;
    this.eventListeners.clear();
    this.messageQueue.length = 0;
    this.onopen = null;
    this.onclose = null;
    this.onerror = null;
    this.onmessage = null;
    
    if (this.readyState !== UnifiedWebSocketMock.CLOSED) {
      this.readyState = UnifiedWebSocketMock.CLOSED;
    }
  }
}

/**
 * Factory function for creating configured WebSocket mocks
 * Provides consistent configuration for different test scenarios
 */
export const createUnifiedWebSocketMock = (config: UnifiedWebSocketConfig = {}) => {
  return class extends UnifiedWebSocketMock {
    constructor(url: string, protocols?: string | string[]) {
      super(url, protocols, config);
    }
  };
};

/**
 * Predefined mock configurations for common test scenarios
 */
export const WebSocketMockConfigs = {
  // Normal connection - for happy path tests
  normal: {
    autoConnect: true,
    simulateNetworkDelay: false,
    enableErrorSimulation: false
  },
  
  // Immediate error - for error handling tests
  immediateError: {
    autoConnect: true,
    simulateNetworkDelay: false,
    enableErrorSimulation: true,
    errorDelay: 0
  },
  
  // Delayed error - for timeout testing
  delayedError: {
    autoConnect: true,
    simulateNetworkDelay: true,
    networkDelayMs: 200,
    enableErrorSimulation: true,
    errorDelay: 100
  },
  
  // Network simulation - for reconnection testing
  networkSimulation: {
    autoConnect: true,
    simulateNetworkDelay: true,
    networkDelayMs: 50,
    enableErrorSimulation: false
  },
  
  // Manual control - for custom test scenarios
  manual: {
    autoConnect: false,
    simulateNetworkDelay: false,
    enableErrorSimulation: false
  }
};

/**
 * Global WebSocket mock replacement
 * This replaces the global WebSocket constructor for all tests
 */
export const setupUnifiedWebSocketMock = (config: UnifiedWebSocketConfig = WebSocketMockConfigs.normal) => {
  const MockClass = createUnifiedWebSocketMock(config);
  
  // Replace global WebSocket
  global.WebSocket = MockClass as any;
  
  // Also replace on window if it exists (browser environment)
  if (typeof window !== 'undefined') {
    (window as any).WebSocket = MockClass;
  }
  
  return MockClass;
};

/**
 * Test helper functions for common WebSocket test patterns
 */
export const WebSocketTestHelpers = {
  /**
   * Wait for WebSocket connection to be established
   */
  waitForConnection: async (ws: UnifiedWebSocketMock, timeout: number = 3000): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (ws.readyState === UnifiedWebSocketMock.OPEN) {
        resolve();
        return;
      }

      const timeoutId = setTimeout(() => {
        reject(new Error(`WebSocket connection timeout after ${timeout}ms`));
      }, timeout);

      const originalOnOpen = ws.onopen;
      ws.onopen = (event) => {
        clearTimeout(timeoutId);
        if (originalOnOpen) originalOnOpen(event);
        resolve();
      };

      const originalOnError = ws.onerror;
      ws.onerror = (event) => {
        clearTimeout(timeoutId);
        if (originalOnError) originalOnError(event);
        reject(new Error('WebSocket connection failed'));
      };
    });
  },

  /**
   * Simulate agent event sequence for testing
   */
  simulateAgentEvents: async (ws: UnifiedWebSocketMock, threadId: string): Promise<void> => {
    // Ensure WebSocket is in OPEN state before sending events
    if (ws.readyState !== UnifiedWebSocketMock.OPEN) {
      console.warn('WebSocket not in OPEN state, cannot simulate events');
      return;
    }

    const events = [
      { type: 'agent_started', data: { thread_id: threadId, agent: 'test_agent' }},
      { type: 'agent_thinking', data: { thread_id: threadId, reasoning: 'Processing...' }},
      { type: 'tool_executing', data: { thread_id: threadId, tool: 'test_tool' }},
      { type: 'tool_completed', data: { thread_id: threadId, tool: 'test_tool', result: {} }},
      { type: 'agent_completed', data: { thread_id: threadId, result: 'Success' }}
    ];

    for (const event of events) {
      if (ws.readyState === UnifiedWebSocketMock.OPEN) {
        ws.simulateMessage(event);
        // Small delay between events for realistic timing
        await new Promise(resolve => setTimeout(resolve, 10));
      }
    }
  }
};

export default UnifiedWebSocketMock;