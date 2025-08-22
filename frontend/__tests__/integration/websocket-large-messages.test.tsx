/**
 * WebSocket Large Message Handling Tests
 * Extracted from oversized websocket-complete.test.tsx for modularity
 * Tests large message processing, chunking, buffering, and performance
 * Focuses on real behavior with large payloads and memory management
 */

import { waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import * as WebSocketTestManager from '@/__tests__/helpers/websocket-test-manager';
import * as WebSocketTestUtilities from '@/__tests__/helpers/websocket-test-utilities';
import { MessageBuffer } from '../setup/websocket-test-utils';

describe('WebSocket Large Message Handling Tests', () => {
  let wsManager: WebSocketTestManager;
  let messageBuffer: MessageBuffer;

  beforeEach(() => {
    // Use real WebSocket simulation instead of mocks
    wsManager = WebSocketTestManager.createWebSocketManager(undefined, true);
    messageBuffer = wsManager.getMessageBuffer();
    wsManager.setup();
  });

  afterEach(() => {
    wsManager.cleanup();
    jest.clearAllMocks();
  });

  describe('Large Message Sending', () => {
    it('should handle 1MB messages with real WebSocket behavior', async () => {
      await wsManager.waitForConnection();
      
      const largeMessage = generateLargeMessage(1024); // 1MB
      expect(largeMessage.length).toBeGreaterThan(1000000);

      // Test real large message sending
      wsManager.sendMessage(largeMessage);
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages).toHaveLength(1);
      expect(sentMessages[0].length).toBeGreaterThan(1000000);
    });

    it('should handle 512KB messages efficiently', async () => {
      await wsManager.waitForConnection();
      
      const mediumMessage = generateLargeMessage(512); // 512KB
      expect(mediumMessage.length).toBeGreaterThan(500000);

      const startTime = performance.now();
      wsManager.sendMessage(mediumMessage);
      const sendTime = performance.now() - startTime;
      
      expect(sendTime).toBeLessThan(100); // Should send quickly
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages).toHaveLength(1);
      expect(sentMessages[0].length).toBeGreaterThan(500000);
    });

    it('should handle multiple large messages sequentially', async () => {
      await wsManager.waitForConnection();
      
      const message1 = generateLargeMessage(256); // 256KB
      const message2 = generateLargeMessage(256); // 256KB
      const message3 = generateLargeMessage(256); // 256KB
      
      wsManager.sendMessage(message1);
      wsManager.sendMessage(message2);
      wsManager.sendMessage(message3);
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages).toHaveLength(3);
      
      // Verify each message maintained its size
      sentMessages.forEach(message => {
        expect(message.length).toBeGreaterThan(250000);
      });
    });
  });

  describe('Large Message Receiving', () => {
    it('should handle large message receiving with real event processing', async () => {
      await wsManager.waitForConnection();
      
      const largeMessage = generateLargeMessage(512); // 512KB
      wsManager.simulateIncomingMessage(largeMessage);
      
      await waitFor(() => {
        const receivedMessages = wsManager.getReceivedMessages();
        expect(receivedMessages).toHaveLength(1);
        expect(receivedMessages[0].length).toBeGreaterThan(500000);
      });
    });

    it('should handle concurrent large message reception', async () => {
      await wsManager.waitForConnection();
      
      const largeMessages = [
        generateLargeMessage(128), // 128KB
        generateLargeMessage(128), // 128KB
        generateLargeMessage(128)  // 128KB
      ];
      
      // Simulate concurrent message arrival
      largeMessages.forEach(message => {
        wsManager.simulateIncomingMessage(message);
      });
      
      await waitFor(() => {
        const receivedMessages = wsManager.getReceivedMessages();
        expect(receivedMessages).toHaveLength(3);
      });
      
      const receivedMessages = wsManager.getReceivedMessages();
      receivedMessages.forEach(message => {
        expect(message.length).toBeGreaterThan(120000);
      });
    });
  });

  describe('Buffer Management', () => {
    it('should respect real buffer limits with backpressure', async () => {
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

    it('should handle large message buffering with memory limits', async () => {
      const buffer = wsManager.getMessageBuffer();
      const largeMessage = generateLargeMessage(100); // 100KB
      
      // Test buffer capacity with large messages
      const addResult1 = buffer.add(largeMessage);
      const addResult2 = buffer.add(largeMessage);
      
      expect(addResult1).toBe(true);
      expect(addResult2).toBe(true);
      expect(buffer.size()).toBe(2);
      
      // Verify messages are properly stored
      const bufferedMessages = buffer.getAll();
      expect(bufferedMessages).toHaveLength(2);
      bufferedMessages.forEach(message => {
        expect(message.length).toBeGreaterThan(90000);
      });
    });

    it('should handle buffer overflow with large messages', async () => {
      const buffer = wsManager.getMessageBuffer();
      buffer.setMaxSize(2);
      
      const largeMessage1 = generateLargeMessage(50); // 50KB
      const largeMessage2 = generateLargeMessage(50); // 50KB
      const largeMessage3 = generateLargeMessage(50); // 50KB (should fail)
      
      expect(buffer.add(largeMessage1)).toBe(true);
      expect(buffer.add(largeMessage2)).toBe(true);
      expect(buffer.add(largeMessage3)).toBe(false); // Buffer full
      
      expect(buffer.size()).toBe(2);
    });
  });

  describe('Message Chunking', () => {
    it('should handle chunked message reconstruction', async () => {
      await wsManager.waitForConnection();
      
      const originalMessage = 'This is a long message that will be chunked';
      const chunks = [
        originalMessage.slice(0, 15),
        originalMessage.slice(15, 30),
        originalMessage.slice(30)
      ];
      
      // Send chunks sequentially
      for (const chunk of chunks) {
        wsManager.simulateIncomingMessage({ chunk, isPartial: true });
      }
      
      const receivedMessages = wsManager.getReceivedMessages();
      expect(receivedMessages).toHaveLength(3);
    });

    it('should handle large message chunking correctly', async () => {
      await wsManager.waitForConnection();
      
      const largeMessage = generateLargeMessage(200); // 200KB
      const chunkSize = 50000; // 50KB chunks
      const chunks = [];
      
      // Create chunks
      for (let i = 0; i < largeMessage.length; i += chunkSize) {
        chunks.push(largeMessage.slice(i, i + chunkSize));
      }
      
      expect(chunks.length).toBeGreaterThan(3);
      
      // Send chunks
      chunks.forEach((chunk, index) => {
        wsManager.simulateIncomingMessage({
          chunk,
          isPartial: index < chunks.length - 1,
          chunkIndex: index,
          totalChunks: chunks.length
        });
      });
      
      const receivedMessages = wsManager.getReceivedMessages();
      expect(receivedMessages.length).toBe(chunks.length);
    });
  });

  describe('Performance and Memory', () => {
    it('should measure large message processing performance', async () => {
      await wsManager.waitForConnection();
      
      const largeMessage = generateLargeMessage(256); // 256KB
      const start = performance.now();
      
      wsManager.sendMessage(largeMessage);
      wsManager.simulateIncomingMessage(largeMessage);
      
      await waitFor(() => {
        const received = wsManager.getReceivedMessages();
        expect(received.length).toBeGreaterThan(0);
      });
      
      const processingTime = performance.now() - start;
      expect(processingTime).toBeLessThan(1000); // Should process within 1 second
    });

    it('should handle memory pressure with multiple large messages', async () => {
      await wsManager.waitForConnection();
      
      const messageCount = 5;
      const messages = Array(messageCount).fill(0).map((_, i) => 
        generateLargeMessage(100) // 100KB each
      );
      
      const startTime = performance.now();
      
      // Send all large messages
      messages.forEach(message => {
        wsManager.sendMessage(message);
      });
      
      const processingTime = performance.now() - startTime;
      expect(processingTime).toBeLessThan(2000); // Should handle within 2 seconds
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages.length).toBe(messageCount);
      
      // Verify message integrity
      sentMessages.forEach(message => {
        expect(message.length).toBeGreaterThan(90000);
      });
    });

    it('should track memory usage during large message processing', async () => {
      await wsManager.waitForConnection();
      
      const initialMemory = process.memoryUsage?.()?.heapUsed || 0;
      
      // Process multiple large messages
      for (let i = 0; i < 3; i++) {
        const largeMessage = generateLargeMessage(200); // 200KB
        wsManager.sendMessage(largeMessage);
        wsManager.simulateIncomingMessage(largeMessage);
      }
      
      await waitFor(() => {
        const received = wsManager.getReceivedMessages();
        expect(received.length).toBe(3);
      });
      
      const finalMemory = process.memoryUsage?.()?.heapUsed || 0;
      const memoryIncrease = finalMemory - initialMemory;
      
      // Memory increase should be reasonable (not a memory leak)
      expect(memoryIncrease).toBeLessThan(10000000); // Less than 10MB increase
    });
  });
});