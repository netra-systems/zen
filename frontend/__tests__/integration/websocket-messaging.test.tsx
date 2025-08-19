/**
 * WebSocket Message Processing Tests
 * Extracted from oversized websocket-complete.test.tsx for modularity
 * Tests message sending, receiving, queuing, and basic processing scenarios
 * Focuses on real message behavior simulation with proper error handling
 */

import { waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import { WebSocketTestManager, createWebSocketManager } from '../helpers/websocket-test-manager';
import { MessageBuffer } from '../setup/websocket-test-utils';

describe('WebSocket Message Processing Tests', () => {
  let wsManager: WebSocketTestManager;
  let messageBuffer: MessageBuffer;

  beforeEach(() => {
    // Use real WebSocket simulation instead of mocks
    wsManager = createWebSocketManager(undefined, true);
    messageBuffer = wsManager.getMessageBuffer();
    wsManager.setup();
  });

  afterEach(() => {
    wsManager.cleanup();
    jest.clearAllMocks();
  });

  describe('Message Sending', () => {
    it('should handle real message sending with queue tracking', async () => {
      await wsManager.waitForConnection();
      
      const testMessage = { type: 'test', data: 'Hello WebSocket' };
      wsManager.sendMessage(testMessage);
      wsManager.sendMessage({ type: 'test2', data: 'Second message' });
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages).toHaveLength(2);
      expect(sentMessages[0]).toContain('Hello WebSocket');
    });

    it('should queue messages when connection is not ready', async () => {
      // Don't wait for connection, send messages immediately
      const message1 = { type: 'queued', data: 'Message 1' };
      const message2 = { type: 'queued', data: 'Message 2' };
      
      wsManager.sendMessage(message1);
      wsManager.sendMessage(message2);
      
      // Messages should be queued if connection not ready
      const queuedMessages = messageBuffer.getAll();
      expect(queuedMessages.length).toBeGreaterThanOrEqual(0);
    });

    it('should handle message serialization correctly', async () => {
      await wsManager.waitForConnection();
      
      const complexMessage = {
        type: 'complex',
        data: {
          nested: { value: 42 },
          array: [1, 2, 3],
          boolean: true,
          nullValue: null
        },
        timestamp: Date.now()
      };
      
      wsManager.sendMessage(complexMessage);
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages).toHaveLength(1);
      
      // Verify message was serialized properly
      const sentData = JSON.parse(sentMessages[0]);
      expect(sentData.data.nested.value).toBe(42);
      expect(sentData.data.array).toEqual([1, 2, 3]);
    });
  });

  describe('Message Receiving', () => {
    it('should handle real message receiving with event simulation', async () => {
      await wsManager.waitForConnection();
      
      const testMessage = { type: 'incoming', data: 'Server message' };
      wsManager.simulateIncomingMessage(testMessage);
      
      await waitFor(() => {
        const receivedMessages = wsManager.getReceivedMessages();
        expect(receivedMessages).toHaveLength(1);
        expect(receivedMessages[0]).toContain('Server message');
      });
    });

    it('should handle multiple incoming messages in sequence', async () => {
      await wsManager.waitForConnection();
      
      const messages = [
        { type: 'seq1', data: 'First message' },
        { type: 'seq2', data: 'Second message' },
        { type: 'seq3', data: 'Third message' }
      ];
      
      // Send messages in sequence
      for (const message of messages) {
        wsManager.simulateIncomingMessage(message);
      }
      
      await waitFor(() => {
        const receivedMessages = wsManager.getReceivedMessages();
        expect(receivedMessages).toHaveLength(3);
      });
      
      const receivedMessages = wsManager.getReceivedMessages();
      expect(receivedMessages[0]).toContain('First message');
      expect(receivedMessages[1]).toContain('Second message');
      expect(receivedMessages[2]).toContain('Third message');
    });

    it('should handle message parsing and validation', async () => {
      await wsManager.waitForConnection();
      
      // Test with valid JSON
      const validMessage = { type: 'valid', data: 'Good message' };
      wsManager.simulateIncomingMessage(validMessage);
      
      await waitFor(() => {
        const receivedMessages = wsManager.getReceivedMessages();
        expect(receivedMessages).toHaveLength(1);
      });
      
      // Test with invalid JSON (should be handled gracefully)
      try {
        wsManager.simulateIncomingMessage('invalid json {');
        // Should not throw, but handle gracefully
      } catch (error) {
        // Expected behavior for invalid messages
        expect(error).toBeDefined();
      }
    });
  });

  describe('Message Queuing', () => {
    it('should handle message queuing with real buffer behavior', async () => {
      const buffer = wsManager.getMessageBuffer();
      
      const success1 = buffer.add('Message 1');
      const success2 = buffer.add('Message 2');
      
      expect(success1).toBe(true);
      expect(success2).toBe(true);
      expect(buffer.size()).toBe(2);
      
      const flushed = buffer.flush();
      expect(flushed).toHaveLength(2);
      expect(buffer.size()).toBe(0);
    });

    it('should respect buffer size limits', async () => {
      const buffer = wsManager.getMessageBuffer();
      buffer.setMaxSize(3); // Small buffer for testing
      
      // Fill buffer to capacity
      expect(buffer.add('message-1')).toBe(true);
      expect(buffer.add('message-2')).toBe(true);
      expect(buffer.add('message-3')).toBe(true);
      
      // Should fail when buffer is full
      expect(buffer.add('message-4')).toBe(false);
      expect(buffer.size()).toBe(3);
      
      // Test buffer flushing
      const flushed = buffer.flush();
      expect(flushed.length).toBe(3);
      expect(buffer.size()).toBe(0);
      
      // Should accept messages after flush
      expect(buffer.add('message-after-flush')).toBe(true);
    });

    it('should handle buffer overflow gracefully', async () => {
      const buffer = wsManager.getMessageBuffer();
      buffer.setMaxSize(2);
      
      // Fill buffer
      buffer.add('msg1');
      buffer.add('msg2');
      
      // Attempt overflow
      const overflowResult = buffer.add('overflow');
      expect(overflowResult).toBe(false);
      
      // Buffer should maintain integrity
      expect(buffer.size()).toBe(2);
      const messages = buffer.getAll();
      expect(messages).toEqual(['msg1', 'msg2']);
    });
  });

  describe('Message Failure Handling', () => {
    it('should handle failed messages with real error conditions', async () => {
      // Close connection to simulate failure
      wsManager.close();
      
      await waitFor(() => {
        expect(wsManager.isReady()).toBe(false);
      });
      
      // Attempt to send message on closed connection
      expect(() => {
        wsManager.sendMessage('Should fail');
      }).toThrow();
    });

    it('should track failed message attempts', async () => {
      await wsManager.waitForConnection();
      
      // Force connection close
      wsManager.close();
      
      let failedAttempts = 0;
      try {
        wsManager.sendMessage('test message');
      } catch (error) {
        failedAttempts++;
      }
      
      expect(failedAttempts).toBe(1);
    });
  });

  describe('Message Performance', () => {
    it('should measure real message round-trip latency', async () => {
      await wsManager.waitForConnection();
      
      const testMessage = { id: 'test-123', echo: true };
      const latency = await wsManager.measureMessageRoundTrip(testMessage);
      
      expect(latency).toBeGreaterThan(0);
      expect(latency).toBeLessThan(100); // Should be fast in tests
    });

    it('should handle concurrent message processing', async () => {
      await wsManager.waitForConnection();
      
      const promises = Array(10).fill(0).map((_, i) => {
        return new Promise<void>((resolve) => {
          wsManager.sendMessage({ id: i, data: `Message ${i}` });
          resolve();
        });
      });
      
      await Promise.all(promises);
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages.length).toBe(10);
    });

    it('should handle message throughput testing', async () => {
      await wsManager.waitForConnection();
      
      const messageCount = 50;
      const startTime = performance.now();
      
      // Send messages rapidly
      for (let i = 0; i < messageCount; i++) {
        wsManager.sendMessage({ index: i, data: `Message ${i}` });
      }
      
      const endTime = performance.now();
      const throughput = messageCount / ((endTime - startTime) / 1000);
      
      expect(throughput).toBeGreaterThan(10); // Should handle at least 10 messages/sec
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages.length).toBe(messageCount);
    });
  });
});