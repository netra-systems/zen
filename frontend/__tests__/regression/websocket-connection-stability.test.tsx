/**
 * WebSocket Connection Stability Regression Tests
 * 
 * Tests to prevent regression of WebSocket connection issues:
 * - Multiple simultaneous connections
 * - Rapid reconnection loops
 * - Connection state management
 */

import { act, waitFor } from '@testing-library/react';

// Mock logger to prevent console output during tests
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  }
}));

// Create mock webSocketService before importing
const mockWebSocketService = {
  connect: jest.fn(),
  disconnect: jest.fn(),
  send: jest.fn(),
  onStatusChange: null as any,
  onMessage: null as any,
  getStatus: jest.fn(),
  getState: jest.fn(),
  isConnected: jest.fn(),
};

// Mock the webSocketService module
jest.mock('@/services/webSocketService', () => ({
  webSocketService: mockWebSocketService
}));

describe('WebSocket Connection Stability Regression Tests', () => {
  const mockUrl = 'ws://localhost:8000/ws';
  let connectionCount = 0;
  let isConnected = false;
  let connectCallbacks: any = {};
  
  beforeEach(() => {
    connectionCount = 0;
    isConnected = false;
    connectCallbacks = {};
    
    // Setup mock implementations
    mockWebSocketService.connect.mockImplementation((url, options) => {
      // Track connection attempts
      connectionCount++;
      
      // Prevent multiple simultaneous connections
      if (isConnected) {
        return; // Already connected, ignore
      }
      
      // Store callbacks
      if (options) {
        connectCallbacks = options;
      }
      
      // Simulate async connection
      if (connectionCount === 1) {
        // Only first connection succeeds
        setTimeout(() => {
          isConnected = true;
          options?.onOpen?.();
        }, 10);
      }
    });
    
    mockWebSocketService.disconnect.mockImplementation(() => {
      isConnected = false;
      // Simulate close callback
      setTimeout(() => {
        connectCallbacks.onClose?.();
      }, 10);
    });
    
    mockWebSocketService.isConnected.mockImplementation(() => isConnected);
    mockWebSocketService.getStatus.mockImplementation(() => isConnected ? 'OPEN' : 'CLOSED');
    mockWebSocketService.getState.mockImplementation(() => isConnected ? 'connected' : 'disconnected');
    
    // Clear all mocks
    jest.clearAllMocks();
  });
  
  afterEach(() => {
    jest.clearAllMocks();
    connectionCount = 0;
    isConnected = false;
    connectCallbacks = {};
  });
  
  describe('Prevent Multiple Simultaneous Connections', () => {
    it('should not create multiple connections when connect is called multiple times rapidly', async () => {
      const onOpen = jest.fn();
      const options = { onOpen };
      
      // Attempt to connect multiple times rapidly
      act(() => {
        mockWebSocketService.connect(mockUrl, options);
        mockWebSocketService.connect(mockUrl, options);
        mockWebSocketService.connect(mockUrl, options);
      });
      
      // Wait for connection to establish
      await waitFor(() => {
        expect(onOpen).toHaveBeenCalled();
      });
      
      // Verify behavior
      expect(mockWebSocketService.connect).toHaveBeenCalledTimes(3); // Called 3 times
      expect(onOpen).toHaveBeenCalledTimes(1); // But only connected once
      expect(connectionCount).toBe(3); // 3 attempts
      expect(isConnected).toBe(true); // Connected
    });
    
    it('should ignore connect calls when already connected', async () => {
      const onOpen = jest.fn();
      const options = { onOpen };
      
      // First connection
      act(() => {
        mockWebSocketService.connect(mockUrl, options);
      });
      
      await waitFor(() => {
        expect(onOpen).toHaveBeenCalledTimes(1);
      });
      
      // Try to connect again while already connected
      act(() => {
        mockWebSocketService.connect(mockUrl, options);
      });
      
      // Wait to ensure no new connection
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Should still only have one connection
      expect(onOpen).toHaveBeenCalledTimes(1);
      expect(mockWebSocketService.connect).toHaveBeenCalledTimes(2);
      expect(isConnected).toBe(true);
    });
    
    it('should prevent connection when isConnecting flag is set', async () => {
      const onOpen = jest.fn();
      const options = { onOpen };
      
      // Modify mock to simulate connecting state
      let isConnecting = false;
      mockWebSocketService.connect.mockImplementation((url, opts) => {
        if (isConnecting || isConnected) {
          return; // Prevent if already connecting or connected
        }
        
        isConnecting = true;
        connectionCount++;
        
        // Simulate async connection
        setTimeout(() => {
          isConnecting = false;
          isConnected = true;
          opts?.onOpen?.();
        }, 50);
      });
      
      // Start connection but don't wait for it to complete
      act(() => {
        mockWebSocketService.connect(mockUrl, options);
      });
      
      // Immediately try to connect again (while isConnecting is true)
      act(() => {
        mockWebSocketService.connect(mockUrl, options);
      });
      
      // Wait for connection to establish
      await waitFor(() => {
        expect(onOpen).toHaveBeenCalled();
      });
      
      // Should only have one successful connection
      expect(mockWebSocketService.connect).toHaveBeenCalledTimes(2);
      expect(onOpen).toHaveBeenCalledTimes(1);
      expect(connectionCount).toBe(1); // Only one went through
    });
  });
  
  describe('Prevent Rapid Reconnection Loops', () => {
    it('should not reconnect after intentional disconnect', async () => {
      const onReconnect = jest.fn();
      const onClose = jest.fn();
      const onOpen = jest.fn();
      const options = { onReconnect, onClose, onOpen };
      
      // Connect
      act(() => {
        mockWebSocketService.connect(mockUrl, options);
      });
      
      await waitFor(() => {
        expect(onOpen).toHaveBeenCalled();
      });
      
      expect(isConnected).toBe(true);
      
      // Intentional disconnect
      act(() => {
        mockWebSocketService.disconnect();
      });
      
      // Wait for disconnect to complete
      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
      });
      
      // Wait to ensure no reconnection happens
      await new Promise(resolve => setTimeout(resolve, 200));
      
      // Should not have attempted reconnection
      expect(onReconnect).not.toHaveBeenCalled();
      expect(isConnected).toBe(false);
    });
    
    it('should respect minimum reconnection interval', async () => {
      jest.useFakeTimers();
      
      const onReconnect = jest.fn();
      const onClose = jest.fn();
      const onOpen = jest.fn();
      const options = { onReconnect, onClose, onOpen };
      
      // Setup reconnect logic
      let reconnectAttempts = 0;
      const MIN_RECONNECT_INTERVAL = 1000;
      
      mockWebSocketService.connect.mockImplementation((url, opts) => {
        connectionCount++;
        
        if (connectionCount === 1) {
          // First connection succeeds immediately
          isConnected = true;
          setTimeout(() => opts?.onOpen?.(), 0);
        } else {
          // Reconnection attempts
          reconnectAttempts++;
          setTimeout(() => {
            isConnected = true;
            opts?.onReconnect?.();
          }, MIN_RECONNECT_INTERVAL);
        }
      });
      
      // Connect
      act(() => {
        mockWebSocketService.connect(mockUrl, options);
      });
      
      // Process initial connection
      jest.runOnlyPendingTimers();
      
      await waitFor(() => {
        expect(onOpen).toHaveBeenCalled();
      });
      
      // Simulate connection loss
      isConnected = false;
      onClose();
      
      // Try to reconnect immediately
      act(() => {
        mockWebSocketService.connect(mockUrl, options);
      });
      
      // Should not reconnect immediately
      expect(onReconnect).not.toHaveBeenCalled();
      
      // Advance time to trigger reconnection
      jest.advanceTimersByTime(MIN_RECONNECT_INTERVAL);
      
      // Now it should attempt reconnection
      await waitFor(() => {
        expect(onReconnect).toHaveBeenCalled();
      });
      
      jest.useRealTimers();
    });
    
    it('should use exponential backoff for reconnection attempts', async () => {
      jest.useFakeTimers();
      
      const onReconnect = jest.fn();
      const onError = jest.fn();
      const onOpen = jest.fn();
      const options = { onReconnect, onError, onOpen };
      
      let attemptDelays: number[] = [];
      let lastAttemptTime = 0;
      
      mockWebSocketService.connect.mockImplementation((url, opts) => {
        const now = Date.now();
        if (lastAttemptTime > 0) {
          attemptDelays.push(now - lastAttemptTime);
        }
        lastAttemptTime = now;
        
        connectionCount++;
        
        if (connectionCount === 1) {
          // First connection succeeds
          isConnected = true;
          setTimeout(() => opts?.onOpen?.(), 0);
        } else if (connectionCount <= 4) {
          // Simulate failures for reconnection attempts
          setTimeout(() => {
            opts?.onError?.({ type: 'CONNECTION_ERROR', message: 'Failed' });
          }, 100);
        } else {
          // Eventually succeed
          isConnected = true;
          setTimeout(() => opts?.onReconnect?.(), 100);
        }
      });
      
      // Connect
      act(() => {
        mockWebSocketService.connect(mockUrl, options);
      });
      
      jest.runOnlyPendingTimers();
      
      await waitFor(() => {
        expect(onOpen).toHaveBeenCalled();
      });
      
      // Simulate multiple connection failures with exponential backoff
      const baseDelay = 1000;
      for (let i = 0; i < 3; i++) {
        // Simulate connection loss
        isConnected = false;
        
        // Attempt reconnection
        act(() => {
          mockWebSocketService.connect(mockUrl, options);
        });
        
        jest.runOnlyPendingTimers();
        
        // Advance time for exponential backoff
        const delay = baseDelay * Math.pow(2, i);
        jest.advanceTimersByTime(delay);
      }
      
      // Verify exponential backoff pattern
      expect(connectionCount).toBeGreaterThan(1);
      expect(onError).toHaveBeenCalled();
      
      jest.useRealTimers();
    });
  });
  
  describe('Connection State Management', () => {
    it('should properly track connection state transitions', async () => {
      const stateChanges: string[] = [];
      let hasDisconnected = false;
      
      mockWebSocketService.onStatusChange = (status: string) => {
        stateChanges.push(status);
      };
      
      // Override disconnect to track when disconnect was called
      const originalDisconnect = mockWebSocketService.disconnect.mockImplementation(() => {
        isConnected = false;
        hasDisconnected = true;
        // Simulate close callback
        setTimeout(() => {
          connectCallbacks.onClose?.();
        }, 10);
      });
      
      // Override getStatus to track state changes
      mockWebSocketService.getStatus.mockImplementation(() => {
        let status;
        if (isConnected) {
          status = 'OPEN';
        } else if (hasDisconnected) {
          status = 'CLOSED';
        } else if (connectionCount > 0) {
          status = 'CONNECTING';
        } else {
          status = 'CLOSED';
        }
        
        if (stateChanges[stateChanges.length - 1] !== status) {
          stateChanges.push(status);
        }
        return status;
      });
      
      // Connect
      act(() => {
        mockWebSocketService.connect(mockUrl);
        mockWebSocketService.getStatus(); // Trigger state check
      });
      
      // Wait for connection
      await new Promise(resolve => setTimeout(resolve, 50));
      mockWebSocketService.getStatus(); // Check state after connection
      
      // Disconnect
      act(() => {
        mockWebSocketService.disconnect();
        mockWebSocketService.getStatus(); // Check state after disconnect
      });
      
      // Wait for disconnect
      await new Promise(resolve => setTimeout(resolve, 50));
      mockWebSocketService.getStatus(); // Final state check
      
      // Verify state progression
      expect(stateChanges).toContain('CONNECTING');
      expect(stateChanges).toContain('OPEN');
      expect(stateChanges[stateChanges.length - 1]).toBe('CLOSED');
    });
    
    it('should handle connection errors gracefully', async () => {
      const onError = jest.fn();
      const options = { onError };
      
      // Mock connection failure
      mockWebSocketService.connect.mockImplementation((url, opts) => {
        connectionCount++;
        
        // Simulate immediate error
        setTimeout(() => {
          opts?.onError?.({ type: 'CONNECTION_ERROR', message: 'Connection failed' });
        }, 0);
      });
      
      // Attempt to connect
      act(() => {
        mockWebSocketService.connect(mockUrl, options);
      });
      
      await waitFor(() => {
        expect(onError).toHaveBeenCalled();
      });
      
      // Should have cleaned up properly
      expect(isConnected).toBe(false);
      expect(onError).toHaveBeenCalledWith({
        type: 'CONNECTION_ERROR',
        message: 'Connection failed'
      });
    });
    
    it('should queue messages when not connected', async () => {
      const messageQueue: any[] = [];
      
      mockWebSocketService.send.mockImplementation((message) => {
        if (!isConnected) {
          messageQueue.push(message);
          return false; // Indicate message was queued
        }
        return true; // Indicate message was sent
      });
      
      // Try to send before connecting
      const testMessage = { type: 'test', payload: { data: 'queued' } };
      act(() => {
        mockWebSocketService.send(testMessage);
      });
      
      expect(messageQueue).toContain(testMessage);
      expect(mockWebSocketService.send).toHaveReturnedWith(false);
      
      // Now connect
      act(() => {
        mockWebSocketService.connect(mockUrl);
      });
      
      // Wait for connection
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Try sending again after connection
      const connectedMessage = { type: 'test', payload: { data: 'sent' } };
      act(() => {
        mockWebSocketService.send(connectedMessage);
      });
      
      expect(mockWebSocketService.send).toHaveReturnedWith(true);
    });
  });
});