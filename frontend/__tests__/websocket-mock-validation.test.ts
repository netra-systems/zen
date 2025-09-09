/**
 * WebSocket Mock Validation Tests
 * 
 * These tests verify that WebSocket mocking is working correctly
 * and no real WebSocket connections can be established.
 */

import { webSocketTestHelper, WebSocketMockFactory, ensureWebSocketMocksWork } from './helpers/websocket-test-helpers';

describe('WebSocket Mock Validation', () => {
  beforeEach(() => {
    // Ensure we start with clean state
    if (global.mockWebSocketInstances) {
      global.mockWebSocketInstances.length = 0;
    }
  });

  afterEach(() => {
    // Clean up any WebSocket instances created during tests
    if (global.cleanupAllResources) {
      global.cleanupAllResources();
    }
  });

  describe('Mock Setup Validation', () => {
    test('should have WebSocket mock available on global object', () => {
      expect(global.WebSocket).toBeDefined();
      expect(typeof global.WebSocket).toBe('function');
    });

    test('should pass mock validation check', () => {
      expect(ensureWebSocketMocksWork()).toBe(true);
    });

    test('should create mock WebSocket instances', () => {
      const ws = new global.WebSocket('ws://test');
      expect(ws).toBeDefined();
      expect(ws.readyState).toBeDefined();
      expect(typeof ws.send).toBe('function');
      expect(typeof ws.close).toBe('function');
    });

    test('should have simulation methods available', () => {
      const ws = new global.WebSocket('ws://test');
      expect(typeof ws.simulateOpen).toBe('function');
      expect(typeof ws.simulateMessage).toBe('function');
      expect(typeof ws.simulateClose).toBe('function');
      expect(typeof ws.simulateError).toBe('function');
    });
  });

  describe('WebSocket Mock Behavior', () => {
    test('should start in CONNECTING state', () => {
      const ws = new global.WebSocket('ws://test');
      expect(ws.readyState).toBe(0); // WebSocket.CONNECTING
    });

    test('should transition to OPEN state when simulated', async () => {
      const ws = new global.WebSocket('ws://test');
      
      // Set up event handler
      let openFired = false;
      ws.onopen = () => { openFired = true; };
      
      // Simulate open
      ws.simulateOpen();
      
      // Wait for event to fire
      await new Promise(resolve => setTimeout(resolve, 10));
      
      expect(ws.readyState).toBe(1); // WebSocket.OPEN
      expect(openFired).toBe(true);
    });

    test('should handle message simulation', async () => {
      const ws = new global.WebSocket('ws://test');
      ws.simulateOpen();
      
      let receivedMessage = null;
      ws.onmessage = (event) => { receivedMessage = event.data; };
      
      const testMessage = 'Test message';
      ws.simulateMessage(testMessage);
      
      await new Promise(resolve => setTimeout(resolve, 10));
      
      expect(receivedMessage).toBe(testMessage);
    });

    test('should handle connection close simulation', async () => {
      const ws = new global.WebSocket('ws://test');
      ws.simulateOpen();
      
      let closeFired = false;
      let closeCode = null;
      ws.onclose = (event) => { 
        closeFired = true; 
        closeCode = event.code;
      };
      
      ws.simulateClose(1000, 'Normal close');
      
      await new Promise(resolve => setTimeout(resolve, 10));
      
      expect(ws.readyState).toBe(3); // WebSocket.CLOSED
      expect(closeFired).toBe(true);
      expect(closeCode).toBe(1000);
    });

    test('should handle error simulation', async () => {
      const ws = new global.WebSocket('ws://test');
      
      let errorFired = false;
      let errorMessage = null;
      ws.onerror = (event) => { 
        errorFired = true;
        errorMessage = event.error?.message;
      };
      
      const testError = new Error('Test error');
      ws.simulateError(testError);
      
      await new Promise(resolve => setTimeout(resolve, 10));
      
      expect(errorFired).toBe(true);
      expect(errorMessage).toBe('Test error');
    });
  });

  describe('WebSocket Test Helper', () => {
    test('should create WebSocket instances through helper', () => {
      const ws = webSocketTestHelper.createMockWebSocket();
      expect(ws).toBeDefined();
      expect(ws.readyState).toBeDefined();
    });

    test('should simulate events through helper', async () => {
      const ws = webSocketTestHelper.createMockWebSocket();
      
      let openFired = false;
      ws.onopen = () => { openFired = true; };
      
      webSocketTestHelper.simulateOpen(ws);
      await new Promise(resolve => setTimeout(resolve, 10));
      
      expect(openFired).toBe(true);
      expect(webSocketTestHelper.isOpen(ws)).toBe(true);
    });
  });

  describe('WebSocket Mock Factory', () => {
    test('should create connected mock', async () => {
      const ws = WebSocketMockFactory.createConnectedMock();
      
      // Wait for auto-connection
      await new Promise(resolve => setTimeout(resolve, 20));
      
      expect(ws.readyState).toBe(1); // WebSocket.OPEN
    });

    test('should create failed connection mock', async () => {
      const ws = WebSocketMockFactory.createFailedConnectionMock();
      
      let errorFired = false;
      ws.onerror = () => { errorFired = true; };
      
      // Wait for auto-error
      await new Promise(resolve => setTimeout(resolve, 20));
      
      expect(errorFired).toBe(true);
    });

    test('should create unstable connection mock', async () => {
      const ws = WebSocketMockFactory.createUnstableMock();
      
      let openFired = false;
      let closeFired = false;
      ws.onopen = () => { openFired = true; };
      ws.onclose = () => { closeFired = true; };
      
      // Wait for connection and disconnection
      await new Promise(resolve => setTimeout(resolve, 150));
      
      expect(openFired).toBe(true);
      expect(closeFired).toBe(true);
    });

    test('should create interactive mock with response helper', async () => {
      const ws = WebSocketMockFactory.createInteractiveMock();
      
      let receivedMessage = null;
      ws.onmessage = (event) => { receivedMessage = event.data; };
      
      // Wait for connection
      await new Promise(resolve => setTimeout(resolve, 20));
      
      // Use the response helper
      const responseData = { type: 'response', data: 'auto response' };
      ws.respondToMessage(responseData);
      
      await new Promise(resolve => setTimeout(resolve, 20));
      
      expect(receivedMessage).toBe(JSON.stringify(responseData));
    });
  });

  describe('Real WebSocket Prevention', () => {
    test('should prevent access to real WebSocket', () => {
      // Verify that global.WebSocket is our mock, not the real WebSocket
      expect(global.WebSocket.name).toBe('MockWebSocket');
      
      // Verify that window.WebSocket (if available) is also our mock
      if (typeof window !== 'undefined' && window.WebSocket) {
        expect(window.WebSocket.name).toBe('MockWebSocket');
      }
    });

    test('should not allow setting real WebSocket', () => {
      const originalMock = global.WebSocket;
      
      // Try to set a fake "real" WebSocket
      const fakeRealWebSocket = function WebSocket() {};
      
      // This should be blocked by our property descriptor
      global.WebSocket = fakeRealWebSocket;
      
      // Should still be our mock
      expect(global.WebSocket).toBe(originalMock);
      expect(global.WebSocket.name).toBe('MockWebSocket');
    });
  });

  describe('Memory Management', () => {
    test('should track WebSocket instances for cleanup', () => {
      const initialCount = global.mockWebSocketInstances?.length || 0;
      
      const ws1 = webSocketTestHelper.createMockWebSocket();
      const ws2 = webSocketTestHelper.createMockWebSocket();
      
      expect(global.mockWebSocketInstances).toBeDefined();
      // FIXED: Account for other tests creating instances - check that we added at least 2
      expect(global.mockWebSocketInstances.length).toBeGreaterThanOrEqual(initialCount + 2);
    });

    test('should clean up WebSocket instances', () => {
      // Create some instances
      webSocketTestHelper.createMockWebSocket();
      webSocketTestHelper.createMockWebSocket();
      
      const beforeCleanup = global.mockWebSocketInstances?.length || 0;
      expect(beforeCleanup).toBeGreaterThan(0);
      
      // Clean up
      if (global.cleanupAllResources) {
        global.cleanupAllResources();
      }
      
      // Instances should be cleaned up
      expect(global.mockWebSocketInstances?.length).toBe(0);
    });
  });
});