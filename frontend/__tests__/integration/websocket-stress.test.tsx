/**
 * WebSocket Stress Testing
 * Extracted from websocket-performance.test.tsx to maintain 450-line limit
 * Tests stress scenarios, memory management, and rapid operations
 * Focuses on edge cases and resource management
 */

import { waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import { WebSocketTestManager, createWebSocketManager } from '@/__tests__/helpers/websocket-test-manager';

describe('WebSocket Stress Testing', () => {
  let wsManager: WebSocketTestManager;

  beforeEach(() => {
    // Use real WebSocket simulation instead of mocks
    wsManager = createWebSocketManager(undefined, true);
    wsManager.setup();
  });

  afterEach(() => {
    wsManager.cleanup();
    jest.clearAllMocks();
  });

  describe('Connection Stress', () => {
    it('should handle rapid connect/disconnect cycles', async () => {
      const cycles = 5;
      
      for (let i = 0; i < cycles; i++) {
        // Connect
        const manager = createWebSocketManager(undefined, true);
        manager.setup();
        await manager.waitForConnection();
        expect(manager.isReady()).toBe(true);
        
        // Send a message
        manager.sendMessage({ cycle: i, data: 'Stress test' });
        
        // Disconnect
        manager.close();
        await waitFor(() => {
          expect(manager.isReady()).toBe(false);
        });
        
        manager.cleanup();
      }
      
      // Should complete without errors
      expect(true).toBe(true);
    });

    it('should handle multiple simultaneous connection attempts', async () => {
      const connectionCount = 5;
      const managers = [];
      
      // Create multiple managers simultaneously
      for (let i = 0; i < connectionCount; i++) {
        const manager = createWebSocketManager(undefined, true);
        managers.push(manager);
        manager.setup();
      }
      
      // Wait for all to connect
      await Promise.all(managers.map(manager => manager.waitForConnection()));
      
      // Verify all connected
      const connectedCount = managers.filter(manager => manager.isReady()).length;
      expect(connectedCount).toBe(connectionCount);
      
      // Cleanup all
      managers.forEach(manager => manager.cleanup());
    });
  });

  describe('Memory Management', () => {
    it('should handle memory cleanup during stress testing', async () => {
      const initialMemory = process.memoryUsage?.()?.heapUsed || 0;
      
      // Create and destroy multiple managers
      for (let i = 0; i < 10; i++) {
        const manager = createWebSocketManager(undefined, true);
        manager.setup();
        await manager.waitForConnection();
        
        // Send some messages
        for (let j = 0; j < 10; j++) {
          manager.sendMessage({ stress: i, message: j });
        }
        
        manager.cleanup();
      }
      
      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }
      
      const finalMemory = process.memoryUsage?.()?.heapUsed || 0;
      const memoryIncrease = finalMemory - initialMemory;
      
      // Memory increase should be reasonable (not a major leak)
      expect(memoryIncrease).toBeLessThan(5000000); // Less than 5MB increase
    });

    it('should handle repeated message sending without memory leaks', async () => {
      await wsManager.waitForConnection();
      
      const initialMemory = process.memoryUsage?.()?.heapUsed || 0;
      const messageCount = 1000;
      
      // Send many messages
      for (let i = 0; i < messageCount; i++) {
        wsManager.sendMessage({ index: i, data: `Stress message ${i}` });
      }
      
      // Force cleanup
      if (global.gc) {
        global.gc();
      }
      
      const finalMemory = process.memoryUsage?.()?.heapUsed || 0;
      const memoryIncrease = finalMemory - initialMemory;
      
      // Verify messages were sent
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages.length).toBe(messageCount);
      
      // Memory should not increase excessively
      expect(memoryIncrease).toBeLessThan(2000000); // Less than 2MB increase
    });
  });

  describe('Load Testing', () => {
    it('should handle high message volume', async () => {
      await wsManager.waitForConnection();
      
      const messageCount = 500;
      const startTime = performance.now();
      
      // Send messages rapidly
      for (let i = 0; i < messageCount; i++) {
        wsManager.sendMessage({ load: i, timestamp: Date.now() });
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      expect(duration).toBeLessThan(5000); // Should complete within 5 seconds
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages.length).toBe(messageCount);
    });

    it('should handle concurrent message bursts', async () => {
      await wsManager.waitForConnection();
      
      const burstCount = 5;
      const messagesPerBurst = 20;
      
      // Create concurrent bursts
      const bursts = Array(burstCount).fill(0).map(async (_, burstIndex) => {
        for (let i = 0; i < messagesPerBurst; i++) {
          wsManager.sendMessage({ 
            burst: burstIndex, 
            message: i, 
            data: `Burst ${burstIndex} Message ${i}` 
          });
        }
      });
      
      await Promise.all(bursts);
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages.length).toBe(burstCount * messagesPerBurst);
    });
  });

  describe('Error Recovery Stress', () => {
    it('should handle repeated error/recovery cycles', async () => {
      const cycles = 3;
      
      for (let i = 0; i < cycles; i++) {
        await wsManager.waitForConnection();
        expect(wsManager.isReady()).toBe(true);
        
        // Force error
        wsManager.simulateError(new Error(`Stress error ${i}`));
        
        await waitFor(() => {
          expect(wsManager.getConnectionState()).toBe('error');
        });
        
        // Recover
        wsManager.simulateReconnect();
        
        await waitFor(() => {
          expect(wsManager.getConnectionState()).toBe('connected');
        }, { timeout: 1000 });
      }
      
      // Should end in connected state
      expect(wsManager.isReady()).toBe(true);
    });

    it('should maintain message queue integrity during stress', async () => {
      const buffer = wsManager.getMessageBuffer();
      const messageCount = 100;
      
      // Fill buffer with many messages
      for (let i = 0; i < messageCount; i++) {
        const success = buffer.add(`Stress queue message ${i}`);
        if (!success) {
          // Buffer full, flush and continue
          buffer.flush();
          buffer.add(`Stress queue message ${i}`);
        }
      }
      
      // Verify buffer integrity
      expect(buffer.size()).toBeGreaterThan(0);
      
      const messages = buffer.getAll();
      expect(messages.length).toBeGreaterThan(0);
      expect(messages.every(msg => typeof msg === 'string')).toBe(true);
    });
  });
});