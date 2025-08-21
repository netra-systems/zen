/**
 * WebSocket Test Manager - Real WebSocket behavior simulation
 * Replaces jest-websocket-mock with realistic WebSocket testing
 * Provides comprehensive WebSocket lifecycle and state management
 * FIXED: React synchronization and timing issues resolved
 */

import WS from 'jest-websocket-mock';
import { TestWebSocket, ConnectionStateManager, MessageBuffer } from '../setup/websocket-test-utils';

/**
 * Generates unique WebSocket URL for each test
 */
function generateUniqueUrl(): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substr(2, 9);
  return `ws://localhost:8000/ws-${timestamp}-${random}`;
}

/**
 * Safely cleans up WebSocket mock servers
 */
function safeCleanup(): void {
  try {
    // Check if WS exists and has the clean method
    if (typeof WS !== 'undefined' && WS && typeof WS.clean === 'function') {
      WS.clean();
    }
  } catch (error) {
    // Silently ignore all cleanup errors - they're not critical for tests
  }
}

/**
 * Creates WebSocket mock server with unique URL
 */
function createMockServer(url?: string): WS {
  const serverUrl = url || generateUniqueUrl();
  return new WS(serverUrl);
}

/**
 * Enhanced WebSocket Test Manager with real behavior simulation
 */
export class WebSocketTestManager {
  private server?: WS;
  private testWebSocket?: TestWebSocket;
  private stateManager: ConnectionStateManager;
  private messageBuffer: MessageBuffer;
  private readonly url: string;
  private connectionHistory: { event: string; timestamp: number }[] = [];
  private isUsingRealSimulation: boolean = true;

  constructor(customUrl?: string, useRealSimulation: boolean = true) {
    this.url = customUrl || generateUniqueUrl();
    this.isUsingRealSimulation = useRealSimulation;
    this.stateManager = new ConnectionStateManager();
    this.messageBuffer = new MessageBuffer();
  }

  /**
   * Sets up WebSocket with real behavior simulation or mock server
   */
  setup(): WS | TestWebSocket {
    this.cleanup(); // Ensure clean state
    
    if (this.isUsingRealSimulation) {
      this.testWebSocket = new TestWebSocket(this.url);
      this.setupRealSimulation();
      return this.testWebSocket as any;
    } else {
      this.server = createMockServer(this.url);
      return this.server;
    }
  }

  /**
   * Sets up real WebSocket simulation with state tracking and React synchronization
   */
  private setupRealSimulation(): void {
    if (!this.testWebSocket) return;

    this.testWebSocket.addEventListener('open', () => {
      this.synchronizeStateChange(() => {
        this.stateManager.setState('connected');
        this.logEvent('open');
      });
    });

    this.testWebSocket.addEventListener('close', () => {
      this.synchronizeStateChange(() => {
        this.stateManager.setState('disconnected');
        this.logEvent('close');
      });
    });

    this.testWebSocket.addEventListener('error', () => {
      this.synchronizeStateChange(() => {
        this.stateManager.setState('error');
        this.logEvent('error');
      });
    });

    this.testWebSocket.addEventListener('message', (event: Event) => {
      this.synchronizeStateChange(() => {
        const messageEvent = event as MessageEvent;
        this.messageBuffer.add(messageEvent.data);
        this.logEvent('message');
      });
    });
    
    // Now that listeners are set up, trigger the connection
    this.testWebSocket.connect();
  }

  /**
   * Cleans up WebSocket resources
   */
  cleanup(): void {
    if (this.testWebSocket) {
      this.testWebSocket.close();
      this.testWebSocket = undefined;
    }
    if (this.server) {
      this.server = undefined;
    }
    this.stateManager.clearHistory();
    this.messageBuffer.flush();
    this.connectionHistory = [];
    safeCleanup();
  }

  /**
   * Gets current server instance (real or mock)
   */
  getServer(): WS | TestWebSocket | undefined {
    return this.testWebSocket || this.server;
  }

  /**
   * Gets WebSocket URL
   */
  getUrl(): string {
    return this.url;
  }

  /**
   * Gets connection state manager
   */
  getStateManager(): ConnectionStateManager {
    return this.stateManager;
  }

  /**
   * Gets message buffer
   */
  getMessageBuffer(): MessageBuffer {
    return this.messageBuffer;
  }

  /**
   * Waits for WebSocket connection with React-synchronized timing
   */
  async waitForConnection(timeoutMs: number = 1000): Promise<void> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      
      const checkConnection = () => {
        if (this.stateManager.getState() === 'connected') {
          resolve();
        } else if (Date.now() - startTime > timeoutMs) {
          reject(new Error('Connection timeout'));
        } else {
          // Use queueMicrotask for better React synchronization
          queueMicrotask(checkConnection);
        }
      };
      
      checkConnection();
    });
  }

  /**
   * Sends message through WebSocket with real behavior
   */
  sendMessage(message: any): void {
    const messageData = typeof message === 'string' ? message : JSON.stringify(message);
    
    if (this.testWebSocket) {
      try {
        this.testWebSocket.send(messageData);
        this.logEvent('send');
      } catch (error) {
        this.logEvent('send_error');
        throw error;
      }
    } else if (this.server) {
      this.server.send(messageData);
    }
  }

  /**
   * Closes WebSocket connection with real behavior
   */
  close(code?: number, reason?: string): void {
    if (this.testWebSocket) {
      this.testWebSocket.close(code, reason);
    } else if (this.server) {
      this.server.close();
    }
  }

  /**
   * Simulates incoming message
   */
  simulateIncomingMessage(data: any): void {
    if (this.testWebSocket) {
      this.testWebSocket.simulateMessage(data);
    }
  }

  /**
   * Simulates connection error
   */
  simulateError(error?: any): void {
    if (this.testWebSocket) {
      this.testWebSocket.simulateError(error);
    }
  }

  /**
   * Simulates reconnection with proper state synchronization
   */
  simulateReconnect(): void {
    if (this.testWebSocket) {
      this.synchronizeStateChange(() => {
        this.stateManager.setState('reconnecting');
        this.testWebSocket?.simulateReconnect();
      });
    }
  }

  /**
   * Gets connection event history
   */
  getConnectionHistory(): { event: string; timestamp: number }[] {
    return [...this.connectionHistory];
  }

  /**
   * Gets current connection state
   */
  getConnectionState(): string {
    return this.stateManager.getState();
  }

  /**
   * Checks if WebSocket is ready for communication
   */
  isReady(): boolean {
    if (this.testWebSocket) {
      return this.testWebSocket.readyState === 1; // OPEN
    }
    return false;
  }

  /**
   * Gets sent messages queue
   */
  getSentMessages(): string[] {
    if (this.testWebSocket) {
      return this.testWebSocket.getSentMessages();
    }
    return [];
  }

  /**
   * Gets received messages buffer
   */
  getReceivedMessages(): string[] {
    return this.messageBuffer.flush();
  }

  /**
   * Logs connection events for testing
   */
  private logEvent(event: string): void {
    this.connectionHistory.push({
      event,
      timestamp: Date.now()
    });
  }

  /**
   * Enables/disables real simulation mode
   */
  setRealSimulationMode(enabled: boolean): void {
    this.isUsingRealSimulation = enabled;
  }
  
  /**
   * Synchronizes state changes with React updates to prevent race conditions
   */
  private synchronizeStateChange(stateChangeFn: () => void): void {
    if (this.isUsingRealSimulation) {
      // Use queueMicrotask for better React synchronization
      queueMicrotask(stateChangeFn);
    } else {
      // For mock mode, execute immediately
      stateChangeFn();
    }
  }

  /**
   * Tests WebSocket performance
   */
  async measureConnectionTime(): Promise<number> {
    const start = performance.now();
    await this.waitForConnection();
    return performance.now() - start;
  }

  /**
   * Tests message round-trip time with React synchronization
   */
  async measureMessageRoundTrip(message: any): Promise<number> {
    const start = performance.now();
    this.sendMessage(message);
    // Simulate echo response with proper timing
    queueMicrotask(() => {
      this.simulateIncomingMessage(message);
    });
    
    return new Promise((resolve) => {
      const checkMessage = () => {
        const received = this.getReceivedMessages();
        if (received.length > 0) {
          resolve(performance.now() - start);
        } else {
          queueMicrotask(checkMessage);
        }
      };
      checkMessage();
    });
  }
}

/**
 * Creates WebSocket manager for tests with realistic behavior
 */
export function createWebSocketManager(customUrl?: string, useRealSimulation: boolean = true): WebSocketTestManager {
  return new WebSocketTestManager(customUrl, useRealSimulation);
}

/**
 * Creates WebSocket manager specifically for legacy mock testing
 */
export function createLegacyWebSocketManager(customUrl?: string): WebSocketTestManager {
  return new WebSocketTestManager(customUrl, false);
}

/**
 * Creates multiple WebSocket managers for concurrent testing
 */
export function createMultipleWebSocketManagers(count: number, useRealSimulation: boolean = true): WebSocketTestManager[] {
  return Array(count).fill(0).map(() => 
    new WebSocketTestManager(generateUniqueUrl(), useRealSimulation)
  );
}

/**
 * Enhanced safe WebSocket cleanup utility - handles all edge cases
 * Use this in afterEach/afterAll hooks instead of WS.clean() directly
 */
export function safeWebSocketCleanup(): void {
  try {
    // Check if WS exists and has the clean method
    if (typeof WS !== 'undefined' && WS && typeof WS.clean === 'function') {
      WS.clean();
    }
  } catch (error) {
    // Silently ignore all cleanup errors - they're not critical for tests
    // Common errors: "Cannot read properties of undefined", connection issues
  }
}

/**
 * Global cleanup utility for afterAll hooks
 * @deprecated Use safeWebSocketCleanup() instead
 */
export function globalWebSocketCleanup(): void {
  safeWebSocketCleanup();
}

export default WebSocketTestManager;