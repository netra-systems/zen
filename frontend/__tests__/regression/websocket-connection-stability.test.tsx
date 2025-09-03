/**
 * WebSocket Connection Stability Regression Tests
 * 
 * Tests to prevent regression of WebSocket connection issues:
 * - Multiple simultaneous connections
 * - Rapid reconnection loops
 * - Connection state management
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import WS from 'jest-websocket-mock';
import { webSocketService } from '@/services/webSocketService';

// Mock logger to prevent console output during tests
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  }
}));

describe('WebSocket Connection Stability Regression Tests', () => {
  let server: WS;
  const mockUrl = 'ws://localhost:8000/ws';
  
  beforeEach(() => {
    server = new WS(mockUrl);
    jest.clearAllMocks();
  });
  
  afterEach(() => {
    WS.clean();
    webSocketService.disconnect();
  });
  
  describe('Prevent Multiple Simultaneous Connections', () => {
    it('should not create multiple connections when connect is called multiple times rapidly', async () => {
      const onOpen = jest.fn();
      const options = { onOpen };
      
      // Attempt to connect multiple times rapidly
      act(() => {
        webSocketService.connect(mockUrl, options);
        webSocketService.connect(mockUrl, options);
        webSocketService.connect(mockUrl, options);
      });
      
      // Wait for connection
      await waitFor(() => {
        expect(server).toHaveReceivedMessages([]);
      });
      
      // Should only have one connection
      expect(onOpen).toHaveBeenCalledTimes(1);
      expect(server.server.clients()).toHaveLength(1);
    });
    
    it('should ignore connect calls when already connected', async () => {
      const onOpen = jest.fn();
      const options = { onOpen };
      
      // First connection
      act(() => {
        webSocketService.connect(mockUrl, options);
      });
      
      await waitFor(() => {
        expect(onOpen).toHaveBeenCalledTimes(1);
      });
      
      // Try to connect again while already connected
      act(() => {
        webSocketService.connect(mockUrl, options);
      });
      
      // Should still only have one connection
      expect(onOpen).toHaveBeenCalledTimes(1);
      expect(server.server.clients()).toHaveLength(1);
    });
    
    it('should prevent connection when isConnecting flag is set', async () => {
      const onOpen = jest.fn();
      const options = { onOpen };
      
      // Start connection but don't wait for it to complete
      act(() => {
        webSocketService.connect(mockUrl, options);
      });
      
      // Immediately try to connect again (while isConnecting is true)
      act(() => {
        webSocketService.connect(mockUrl, options);
      });
      
      await waitFor(() => {
        expect(server).toHaveReceivedMessages([]);
      });
      
      // Should only have one connection attempt
      expect(server.server.clients()).toHaveLength(1);
    });
  });
  
  describe('Prevent Rapid Reconnection Loops', () => {
    it('should not reconnect after intentional disconnect', async () => {
      const onReconnect = jest.fn();
      const onClose = jest.fn();
      const options = { onReconnect, onClose };
      
      // Connect
      act(() => {
        webSocketService.connect(mockUrl, options);
      });
      
      await waitFor(() => {
        expect(server).toHaveReceivedMessages([]);
      });
      
      // Intentional disconnect
      act(() => {
        webSocketService.disconnect();
      });
      
      // Simulate server closing connection
      act(() => {
        server.close();
      });
      
      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
      });
      
      // Wait to ensure no reconnection happens
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Should not have attempted reconnection
      expect(onReconnect).not.toHaveBeenCalled();
    });
    
    it('should respect minimum reconnection interval', async () => {
      jest.useFakeTimers();
      
      const onReconnect = jest.fn();
      const onClose = jest.fn();
      const options = { onReconnect, onClose };
      
      // Connect
      act(() => {
        webSocketService.connect(mockUrl, options);
      });
      
      await waitFor(() => {
        expect(server).toHaveReceivedMessages([]);
      });
      
      // Simulate unexpected disconnection
      act(() => {
        server.close();
      });
      
      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
      });
      
      // Fast forward time but less than minimum reconnect delay
      act(() => {
        jest.advanceTimersByTime(500);
      });
      
      // Should not have reconnected yet
      expect(onReconnect).not.toHaveBeenCalled();
      
      // Fast forward past minimum reconnect delay (2000ms base delay)
      act(() => {
        jest.advanceTimersByTime(2000);
      });
      
      // Now should attempt reconnection
      expect(onReconnect).toHaveBeenCalled();
      
      jest.useRealTimers();
    });
    
    it('should stop reconnection attempts after max attempts', async () => {
      jest.useFakeTimers();
      
      const onReconnect = jest.fn();
      const onError = jest.fn();
      const options = { onReconnect, onError };
      
      // Connect and immediately fail multiple times
      for (let i = 0; i < 6; i++) {  // More than max attempts (5)
        act(() => {
          webSocketService.connect(mockUrl, options);
        });
        
        // Simulate immediate connection failure
        act(() => {
          server.error();
          server.close();
        });
        
        // Advance timers for reconnection delay
        act(() => {
          jest.advanceTimersByTime(30000);  // Max delay
        });
      }
      
      // Should stop after max attempts (5)
      expect(onReconnect.mock.calls.length).toBeLessThanOrEqual(5);
      
      jest.useRealTimers();
    });
  });
  
  describe('Connection State Management', () => {
    it('should properly track connection state transitions', async () => {
      const stateChanges: string[] = [];
      const onStatusChange = (status: string) => {
        stateChanges.push(status);
      };
      
      webSocketService.onStatusChange = onStatusChange;
      
      // Connect
      act(() => {
        webSocketService.connect(mockUrl, {});
      });
      
      await waitFor(() => {
        expect(stateChanges).toContain('CONNECTING');
      });
      
      // Wait for connection to be established
      await waitFor(() => {
        expect(stateChanges).toContain('OPEN');
      });
      
      // Disconnect
      act(() => {
        webSocketService.disconnect();
      });
      
      await waitFor(() => {
        expect(stateChanges).toContain('CLOSED');
      });
      
      // Verify proper state sequence
      expect(stateChanges).toEqual(['CONNECTING', 'OPEN', 'CLOSED']);
    });
    
    it('should clean up existing connection before new connection', async () => {
      const onClose1 = jest.fn();
      const onOpen2 = jest.fn();
      
      // First connection
      act(() => {
        webSocketService.connect(mockUrl, { onClose: onClose1 });
      });
      
      await waitFor(() => {
        expect(server).toHaveReceivedMessages([]);
      });
      
      // Disconnect and immediately reconnect with new options
      act(() => {
        webSocketService.disconnect();
        webSocketService.connect(mockUrl, { onOpen: onOpen2 });
      });
      
      await waitFor(() => {
        expect(onClose1).toHaveBeenCalled();
      });
      
      await waitFor(() => {
        expect(onOpen2).toHaveBeenCalled();
      });
      
      // Should have properly transitioned between connections
      expect(server.server.clients()).toHaveLength(1);
    });
  });
  
  describe('Thread-Specific Connection Management', () => {
    it('should maintain single connection across thread switches', async () => {
      const onMessage = jest.fn();
      const options = { onMessage };
      
      // Connect
      act(() => {
        webSocketService.connect(mockUrl, options);
      });
      
      await waitFor(() => {
        expect(server).toHaveReceivedMessages([]);
      });
      
      // Simulate thread switch messages
      act(() => {
        server.send(JSON.stringify({ type: 'thread_loaded', payload: { threadId: 'thread-1' } }));
      });
      
      await waitFor(() => {
        expect(onMessage).toHaveBeenCalledWith(
          expect.objectContaining({ type: 'thread_loaded' })
        );
      });
      
      // Switch to another thread
      act(() => {
        server.send(JSON.stringify({ type: 'thread_loaded', payload: { threadId: 'thread-2' } }));
      });
      
      await waitFor(() => {
        expect(onMessage).toHaveBeenCalledWith(
          expect.objectContaining({ 
            type: 'thread_loaded',
            payload: { threadId: 'thread-2' }
          })
        );
      });
      
      // Should still have only one connection
      expect(server.server.clients()).toHaveLength(1);
    });
  });
});