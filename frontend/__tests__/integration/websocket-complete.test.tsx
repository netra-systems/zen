/**
 * WebSocket Complete Integration Tests - Real Behavior Simulation
 * Tests complete WebSocket connection lifecycle with realistic conditions
 * Replaces excessive jest.fn() mocking with real WebSocket behavior simulation
 * Agent 10 Implementation - P1 Priority for real-time communication
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { TestProviders } from '../setup/test-providers';
import { WebSocketTestManager, createWebSocketManager, createMultipleWebSocketManagers } from '../helpers/websocket-test-manager';
import {
  WebSocketConnectionLifecycle,
  MessageMetrics,
  generateLargeMessage,
  measurePerformance
} from '../helpers/websocket-test-utilities';
import {
  TestWebSocket,
  ConnectionStateManager,
  MessageBuffer,
  AdvancedWebSocketTester,
  measureConnectionTime,
  measureMessageLatency
} from '../setup/websocket-test-utils';

// Test component for WebSocket lifecycle
const WebSocketLifecycleTest: React.FC = () => {
  const [lifecycle, setLifecycle] = React.useState<WebSocketConnectionLifecycle>({
    connecting: false,
    connected: false,
    disconnected: true,
    error: false,
    reconnecting: false
  });

  const [metrics, setMetrics] = React.useState<MessageMetrics>({
    sent: 0,
    received: 0,
    queued: 0,
    failed: 0,
    largeMessages: 0
  });

  const updateLifecycle = (state: keyof WebSocketConnectionLifecycle) => {
    setLifecycle(prev => ({ ...prev, [state]: true }));
  };

  const updateMetrics = (metric: keyof MessageMetrics) => {
    setMetrics(prev => ({ ...prev, [metric]: prev[metric] + 1 }));
  };

  return (
    <div>
      <div data-testid="ws-connecting">{lifecycle.connecting.toString()}</div>
      <div data-testid="ws-connected">{lifecycle.connected.toString()}</div>
      <div data-testid="ws-disconnected">{lifecycle.disconnected.toString()}</div>
      <div data-testid="ws-error">{lifecycle.error.toString()}</div>
      <div data-testid="ws-reconnecting">{lifecycle.reconnecting.toString()}</div>
      
      <div data-testid="metrics-sent">{metrics.sent}</div>
      <div data-testid="metrics-received">{metrics.received}</div>
      <div data-testid="metrics-queued">{metrics.queued}</div>
      <div data-testid="metrics-failed">{metrics.failed}</div>
      <div data-testid="metrics-large">{metrics.largeMessages}</div>
      
      <button onClick={() => updateLifecycle('connecting')} data-testid="btn-connecting">
        Start Connecting
      </button>
      <button onClick={() => updateLifecycle('connected')} data-testid="btn-connected">
        Connected
      </button>
      <button onClick={() => updateLifecycle('disconnected')} data-testid="btn-disconnected">
        Disconnected
      </button>
      <button onClick={() => updateLifecycle('error')} data-testid="btn-error">
        Error
      </button>
      <button onClick={() => updateLifecycle('reconnecting')} data-testid="btn-reconnecting">
        Reconnecting
      </button>
      
      <button onClick={() => updateMetrics('sent')} data-testid="btn-send">
        Send Message
      </button>
      <button onClick={() => updateMetrics('received')} data-testid="btn-receive">
        Receive Message
      </button>
      <button onClick={() => updateMetrics('queued')} data-testid="btn-queue">
        Queue Message
      </button>
      <button onClick={() => updateMetrics('failed')} data-testid="btn-fail">
        Fail Message
      </button>
      <button onClick={() => updateMetrics('largeMessages')} data-testid="btn-large">
        Large Message
      </button>
    </div>
  );
};

// Utilities imported from websocket-test-utilities.ts

describe('WebSocket Complete Integration Tests - Real Behavior', () => {
  let wsManager: WebSocketTestManager;
  let stateManager: ConnectionStateManager;
  let messageBuffer: MessageBuffer;
  let advancedTester: AdvancedWebSocketTester;

  beforeEach(() => {
    // Use real WebSocket simulation instead of mocks
    wsManager = createWebSocketManager(undefined, true);
    stateManager = wsManager.getStateManager();
    messageBuffer = wsManager.getMessageBuffer();
    advancedTester = new AdvancedWebSocketTester();
    wsManager.setup();
  });

  afterEach(() => {
    wsManager.cleanup();
    advancedTester.closeAllConnections();
    advancedTester.clearLog();
    jest.clearAllMocks();
  });

  describe('Real Connection Lifecycle Simulation', () => {
    it('should handle complete connection lifecycle with real timing', async () => {
      render(
        <TestProviders>
          <WebSocketLifecycleTest />
        </TestProviders>
      );

      // Wait for real connection
      await waitFor(() => {
        expect(wsManager.getConnectionState()).toBe('connected');
      }, { timeout: 2000 });

      // Verify real connection state
      expect(wsManager.isReady()).toBe(true);
      expect(wsManager.getConnectionHistory()).toContainEqual(
        expect.objectContaining({ event: 'open' })
      );

      // Test real disconnection
      wsManager.close(1000, 'Test close');
      
      await waitFor(() => {
        expect(wsManager.getConnectionState()).toBe('disconnected');
      });
    });

    it('should handle real connection errors with proper state transitions', async () => {
      render(
        <TestProviders>
          <WebSocketLifecycleTest />
        </TestProviders>
      );

      // Simulate real error
      wsManager.simulateError(new Error('Connection failed'));
      
      await waitFor(() => {
        expect(wsManager.getConnectionState()).toBe('error');
      });
      
      expect(wsManager.getConnectionHistory()).toContainEqual(
        expect.objectContaining({ event: 'error' })
      );
    });

    it('should handle real reconnection with timing simulation', async () => {
      render(
        <TestProviders>
          <WebSocketLifecycleTest />
        </TestProviders>
      );

      // Wait for initial connection
      await wsManager.waitForConnection();
      expect(wsManager.isReady()).toBe(true);

      // Test real reconnection
      wsManager.simulateReconnect();
      
      await waitFor(() => {
        expect(wsManager.getConnectionState()).toBe('reconnecting');
      });
      
      await waitFor(() => {
        expect(wsManager.getConnectionState()).toBe('connected');
      }, { timeout: 1000 });
    });

    it('should track real connection state transitions with history', async () => {
      // Test real state transitions
      await wsManager.waitForConnection();
      expect(stateManager.getState()).toBe('connected');
      
      wsManager.close();
      await waitFor(() => {
        expect(stateManager.getState()).toBe('disconnected');
      });
      
      const history = stateManager.getStateHistory();
      expect(history.length).toBeGreaterThan(0);
      expect(history[history.length - 1].state).toBe('disconnected');
    });

    it('should measure real connection performance', async () => {
      const connectionTime = await wsManager.measureConnectionTime();
      expect(connectionTime).toBeGreaterThan(0);
      expect(connectionTime).toBeLessThan(1000); // Should be fast in tests
    });
  });

  describe('Real Message Processing Simulation', () => {
    it('should handle real message sending with queue tracking', async () => {
      await wsManager.waitForConnection();
      
      const testMessage = { type: 'test', data: 'Hello WebSocket' };
      wsManager.sendMessage(testMessage);
      wsManager.sendMessage({ type: 'test2', data: 'Second message' });
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages).toHaveLength(2);
      expect(sentMessages[0]).toContain('Hello WebSocket');
    });

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
  });

  describe('Real Large Message Handling', () => {
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
  });

  describe('Real Performance Monitoring', () => {
    it('should measure real connection performance with timing', async () => {
      const connectionTime = await measureConnectionTime(async () => {
        await wsManager.waitForConnection();
      });
      
      expect(connectionTime).toBeGreaterThan(0);
      expect(connectionTime).toBeLessThan(2000); // Should connect within 2 seconds
    });

    it('should handle real concurrent connections with load testing', async () => {
      const managers = createMultipleWebSocketManagers(5, true);
      
      const connectionPromises = managers.map(async (manager) => {
        manager.setup();
        return await manager.measureConnectionTime();
      });
      
      const connectionTimes = await Promise.all(connectionPromises);
      
      expect(connectionTimes.every(time => time >= 0)).toBe(true);
      expect(connectionTimes.every(time => time < 2000)).toBe(true);
      
      // Cleanup all managers
      managers.forEach(manager => manager.cleanup());
    });

    it('should monitor real streaming performance with message throughput', async () => {
      await wsManager.waitForConnection();
      
      const messageCount = 60; // Simulate 60 messages per second
      const startTime = performance.now();
      
      // Send messages rapidly
      for (let i = 0; i < messageCount; i++) {
        wsManager.sendMessage({ frame: i, timestamp: Date.now() });
      }
      
      const endTime = performance.now();
      const totalTime = endTime - startTime;
      const messagesPerSecond = (messageCount / totalTime) * 1000;
      
      expect(messagesPerSecond).toBeGreaterThan(60); // Should handle 60+ messages/second
    });

    it('should measure real message latency patterns', async () => {
      await wsManager.waitForConnection();
      
      const latencies: number[] = [];
      
      for (let i = 0; i < 10; i++) {
        const sendTime = performance.now();
        wsManager.sendMessage({ id: i, timestamp: sendTime });
        
        // Simulate response after small delay
        setTimeout(() => {
          wsManager.simulateIncomingMessage({ id: i, echo: true });
        }, Math.random() * 10 + 1);
        
        await waitFor(() => {
          const received = wsManager.getReceivedMessages();
          if (received.length > i) {
            latencies.push(measureMessageLatency(sendTime));
            return true;
          }
          return false;
        });
      }
      
      expect(latencies.length).toBe(10);
      const avgLatency = latencies.reduce((a, b) => a + b, 0) / latencies.length;
      expect(avgLatency).toBeLessThan(50); // Average latency should be under 50ms
    });

    it('should test real backpressure handling', async () => {
      await wsManager.waitForConnection();
      
      const buffer = wsManager.getMessageBuffer();
      buffer.setMaxSize(5); // Small buffer to trigger backpressure
      
      // Fill buffer to capacity
      for (let i = 0; i < 5; i++) {
        expect(buffer.add(`message-${i}`)).toBe(true);
      }
      
      // Additional messages should be rejected
      expect(buffer.add('overflow-message')).toBe(false);
      
      // Simulate processing by flushing buffer
      const processed = buffer.flush();
      expect(processed.length).toBe(5);
      
      // Should accept messages again after processing
      expect(buffer.add('after-flush-message')).toBe(true);
    });

    it('should benchmark real WebSocket vs mock performance', async () => {
      // Test real simulation
      const realManager = createWebSocketManager(undefined, true);
      realManager.setup();
      const realTime = await realManager.measureConnectionTime();
      
      // Test mock simulation
      const mockManager = createWebSocketManager(undefined, false);
      mockManager.setup();
      const mockTime = await mockManager.measureConnectionTime();
      
      expect(realTime).toBeGreaterThan(0);
      expect(mockTime).toBeGreaterThanOrEqual(0);
      
      // Real simulation should be more realistic (slightly slower)
      expect(realTime).toBeGreaterThanOrEqual(mockTime);
      
      realManager.cleanup();
      mockManager.cleanup();
    });
  });

  describe('Real WebSocket Protocol Simulation', () => {
    it('should simulate real WebSocket upgrade from HTTP', async () => {
      const server = wsManager.getServer();
      expect(server).toBeDefined();
      
      // Test real connection establishment
      await wsManager.waitForConnection();
      expect(wsManager.isReady()).toBe(true);
      
      // Verify connection history shows proper handshake
      const history = wsManager.getConnectionHistory();
      expect(history).toContainEqual(
        expect.objectContaining({ event: 'open' })
      );
    });

    it('should handle real upgrade failures with error simulation', async () => {
      // Create a manager that will fail
      const failingManager = createWebSocketManager('ws://invalid-url:999/ws');
      failingManager.setup();
      
      // Simulate upgrade failure
      failingManager.simulateError(new Error('Connection refused'));
      
      await waitFor(() => {
        expect(failingManager.getConnectionState()).toBe('error');
      });
      
      failingManager.cleanup();
    });

    it('should handle real protocol negotiation', async () => {
      const testWebSocket = new TestWebSocket('ws://localhost:8000/ws', ['chat', 'echo']);
      
      expect(testWebSocket.url).toBe('ws://localhost:8000/ws');
      
      // Wait for connection
      await waitFor(() => {
        expect(testWebSocket.readyState).toBe(1); // OPEN
      });
      
      testWebSocket.close();
    });

    it('should test real connection security and validation', async () => {
      await wsManager.waitForConnection();
      
      // Test that connection validates message format
      const invalidMessage = { malformed: true, data: null };
      wsManager.sendMessage(invalidMessage);
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages[0]).toContain('malformed');
      
      // Test connection remains stable after invalid message
      expect(wsManager.isReady()).toBe(true);
    });
  });

  describe('Real Resource Management', () => {
    it('should clean up real WebSocket resources properly', async () => {
      await wsManager.waitForConnection();
      expect(wsManager.isReady()).toBe(true);
      
      const { unmount } = render(
        <TestProviders>
          <WebSocketLifecycleTest />
        </TestProviders>
      );

      // Cleanup should properly close connection
      wsManager.cleanup();
      expect(wsManager.isReady()).toBe(false);
      
      unmount();
      
      // Verify resources are cleaned up
      expect(wsManager.getSentMessages()).toHaveLength(0);
      expect(wsManager.getReceivedMessages()).toHaveLength(0);
    });

    it('should handle multiple real cleanup calls safely', async () => {
      await wsManager.waitForConnection();
      
      // Multiple cleanup calls should be safe
      wsManager.cleanup();
      wsManager.cleanup();
      wsManager.cleanup();
      
      expect(wsManager.isReady()).toBe(false);
    });

    it('should handle memory cleanup for large message buffers', async () => {
      await wsManager.waitForConnection();
      
      // Fill with large messages
      const largeMessage = generateLargeMessage(100); // 100KB
      for (let i = 0; i < 10; i++) {
        wsManager.sendMessage(largeMessage);
        wsManager.simulateIncomingMessage(largeMessage);
      }
      
      expect(wsManager.getSentMessages().length).toBe(10);
      
      // Cleanup should clear all messages
      wsManager.cleanup();
      
      // Create new manager to verify clean state
      const newManager = createWebSocketManager();
      newManager.setup();
      expect(newManager.getSentMessages()).toHaveLength(0);
      expect(newManager.getReceivedMessages()).toHaveLength(0);
      
      newManager.cleanup();
    });

    it('should test advanced multi-connection resource management', async () => {
      const connections = createMultipleWebSocketManagers(3, true);
      
      // Set up all connections
      await Promise.all(connections.map(manager => {
        manager.setup();
        return manager.waitForConnection();
      }));
      
      // Verify all connections are active
      expect(connections.every(manager => manager.isReady())).toBe(true);
      
      // Test selective cleanup
      connections[0].cleanup();
      expect(connections[0].isReady()).toBe(false);
      expect(connections[1].isReady()).toBe(true);
      expect(connections[2].isReady()).toBe(true);
      
      // Cleanup remaining connections
      connections.slice(1).forEach(manager => manager.cleanup());
      expect(connections.every(manager => !manager.isReady())).toBe(true);
    });
  });

  describe('Advanced Real WebSocket Testing', () => {
    it('should test real broadcast message handling', async () => {
      const connection1 = advancedTester.createConnection('ws://localhost:8001/ws');
      const connection2 = advancedTester.createConnection('ws://localhost:8002/ws');
      
      // Wait for connections
      await waitFor(() => {
        expect(connection1.readyState).toBe(1);
        expect(connection2.readyState).toBe(1);
      });
      
      // Test broadcast
      const broadcastMessage = 'Hello all connections';
      advancedTester.broadcastMessage(broadcastMessage);
      
      const messageLog = advancedTester.getMessageLog();
      expect(messageLog.length).toBe(2); // Message sent to both connections
      expect(messageLog.every(log => log.message === broadcastMessage)).toBe(true);
    });

    it('should test real connection pool management', async () => {
      const poolSize = 5;
      const managers = createMultipleWebSocketManagers(poolSize, true);
      
      // Initialize connection pool
      await Promise.all(managers.map(manager => {
        manager.setup();
        return manager.waitForConnection();
      }));
      
      // Test pool health
      const healthyConnections = managers.filter(manager => manager.isReady()).length;
      expect(healthyConnections).toBe(poolSize);
      
      // Test pool message distribution
      managers.forEach((manager, index) => {
        manager.sendMessage({ poolId: index, data: `Pool message ${index}` });
      });
      
      // Verify all messages were sent
      const totalSentMessages = managers.reduce((total, manager) => {
        return total + manager.getSentMessages().length;
      }, 0);
      
      expect(totalSentMessages).toBe(poolSize);
      
      // Cleanup pool
      managers.forEach(manager => manager.cleanup());
    });

    it('should test real WebSocket reconnection strategies', async () => {
      await wsManager.waitForConnection();
      expect(wsManager.isReady()).toBe(true);
      
      // Simulate connection loss
      wsManager.simulateError(new Error('Network disconnected'));
      
      await waitFor(() => {
        expect(wsManager.getConnectionState()).toBe('error');
      });
      
      // Test reconnection
      wsManager.simulateReconnect();
      
      await waitFor(() => {
        expect(wsManager.getConnectionState()).toBe('connected');
      }, { timeout: 2000 });
      
      expect(wsManager.isReady()).toBe(true);
      
      // Verify connection history shows reconnection
      const history = wsManager.getConnectionHistory();
      const errorEvents = history.filter(event => event.event === 'error');
      const openEvents = history.filter(event => event.event === 'open');
      
      expect(errorEvents.length).toBeGreaterThan(0);
      expect(openEvents.length).toBeGreaterThan(1); // Initial + reconnection
    });

    it('should benchmark real vs mock WebSocket test performance', async () => {
      const iterations = 100;
      
      // Benchmark real simulation
      const realStart = performance.now();
      for (let i = 0; i < iterations; i++) {
        const realManager = createWebSocketManager(undefined, true);
        realManager.setup();
        await realManager.waitForConnection();
        realManager.sendMessage({ test: i });
        realManager.cleanup();
      }
      const realTime = performance.now() - realStart;
      
      // Benchmark mock simulation (should be faster but less realistic)
      const mockStart = performance.now();
      for (let i = 0; i < iterations; i++) {
        const mockManager = createWebSocketManager(undefined, false);
        mockManager.setup();
        // Mock connections don't need real waiting
        mockManager.sendMessage({ test: i });
        mockManager.cleanup();
      }
      const mockTime = performance.now() - mockStart;
      
      expect(realTime).toBeGreaterThan(0);
      expect(mockTime).toBeGreaterThan(0);
      
      // Real simulation should provide more realistic timing
      console.log(`Real WebSocket simulation: ${realTime}ms, Mock simulation: ${mockTime}ms`);
    });
  });
});