/**
 * WebSocket Test Manager - Centralized WebSocket mock server management
 * Solves URL conflicts and improper cleanup issues
 * Ensures test isolation with unique URLs per test
 */

import WS from 'jest-websocket-mock';

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
    WS.clean();
  } catch (error) {
    // Ignore cleanup errors for non-existent servers
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
 * WebSocket Test Manager for centralized mock server management
 */
export class WebSocketTestManager {
  private server?: WS;
  private readonly url: string;

  constructor(customUrl?: string) {
    this.url = customUrl || generateUniqueUrl();
  }

  /**
   * Sets up WebSocket mock server
   */
  setup(): WS {
    this.cleanup(); // Ensure clean state
    this.server = createMockServer(this.url);
    return this.server;
  }

  /**
   * Cleans up WebSocket mock server
   */
  cleanup(): void {
    if (this.server) {
      this.server = undefined;
    }
    safeCleanup();
  }

  /**
   * Gets current server instance
   */
  getServer(): WS | undefined {
    return this.server;
  }

  /**
   * Gets WebSocket URL
   */
  getUrl(): string {
    return this.url;
  }

  /**
   * Waits for WebSocket connection
   */
  async waitForConnection(): Promise<void> {
    if (this.server) {
      await this.server.connected;
    }
  }

  /**
   * Sends message through WebSocket
   */
  sendMessage(message: any): void {
    if (this.server) {
      this.server.send(JSON.stringify(message));
    }
  }

  /**
   * Closes WebSocket connection
   */
  close(): void {
    if (this.server) {
      this.server.close();
    }
  }
}

/**
 * Creates WebSocket manager for tests
 */
export function createWebSocketManager(customUrl?: string): WebSocketTestManager {
  return new WebSocketTestManager(customUrl);
}

/**
 * Global cleanup utility for afterAll hooks
 */
export function globalWebSocketCleanup(): void {
  safeCleanup();
}

export default WebSocketTestManager;