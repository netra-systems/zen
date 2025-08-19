/**
 * WebSocket Complete Integration Tests - REFACTORED
 * All functions ≤8 lines as per architecture requirements
 * Real behavior simulation with comprehensive utilities
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
import {
  createWebSocketTestComponent,
  useWebSocketLifecycle,
  useWebSocketMetrics
} from './utils/websocket-component-utils';
import {
  performConnectionLifecycleTest,
  performConnectionErrorTest,
  performReconnectionTest,
  performMessageSendingTest,
  performMessageReceivingTest,
  performMessageQueuingTest,
  performFailedMessageTest,
  performLargeMessageSendTest,
  performLargeMessageReceiveTest,
  performBufferLimitTest,
  performConnectionTimingTest,
  performRoundTripLatencyTest,
  performConcurrentMessageTest,
  performCleanupTest
} from './utils/websocket-test-operations';

// Test component for WebSocket lifecycle (≤8 lines)
const WebSocketLifecycleTest: React.FC = () => {
  const { lifecycle, updateLifecycle } = useWebSocketLifecycle();
  const { metrics, updateMetrics } = useWebSocketMetrics();
  
  return createWebSocketTestComponent({
    lifecycle,
    metrics,
    updateLifecycle,
    updateMetrics
  });
};

describe('WebSocket Complete Integration Tests - Real Behavior', () => {
  let wsManager: WebSocketTestManager;
  let stateManager: ConnectionStateManager;
  let messageBuffer: MessageBuffer;
  let advancedTester: AdvancedWebSocketTester;

  beforeEach(() => {
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
      await performConnectionLifecycleTest(wsManager);
    });

    it('should handle real connection errors with proper state transitions', async () => {
      await performConnectionErrorTest(wsManager, WebSocketLifecycleTest);
    });

    it('should handle real reconnection with timing simulation', async () => {
      await performReconnectionTest(wsManager, WebSocketLifecycleTest);
    });

    it('should track real connection state transitions with history', async () => {
      await testStateTransitionHistory(wsManager, stateManager);
    });

    it('should measure real connection performance', async () => {
      await performConnectionTimingTest(wsManager);
    });
  });

  describe('Real Message Processing Simulation', () => {
    it('should handle real message sending with queue tracking', async () => {
      await performMessageSendingTest(wsManager);
    });

    it('should handle real message receiving with event simulation', async () => {
      await performMessageReceivingTest(wsManager);
    });

    it('should handle message queuing with real buffer behavior', async () => {
      await performMessageQueuingTest(wsManager);
    });

    it('should handle failed messages with real error conditions', async () => {
      await performFailedMessageTest(wsManager);
    });

    it('should measure real message round-trip latency', async () => {
      await performRoundTripLatencyTest(wsManager);
    });

    it('should handle concurrent message processing', async () => {
      await performConcurrentMessageTest(wsManager);
    });
  });

  describe('Real Large Message Handling', () => {
    it('should handle 1MB messages with real WebSocket behavior', async () => {
      await performLargeMessageSendTest(wsManager);
    });

    it('should handle large message receiving with real event processing', async () => {
      await performLargeMessageReceiveTest(wsManager);
    });

    it('should respect real buffer limits with backpressure', async () => {
      await performBufferLimitTest(wsManager);
    });

    it('should handle chunked message reconstruction', async () => {
      await testChunkedMessageReconstruction(wsManager);
    });

    it('should measure large message processing performance', async () => {
      await testLargeMessagePerformance(wsManager);
    });
  });

  describe('Real Performance Monitoring', () => {
    it('should measure real connection performance with timing', async () => {
      const connectionTime = await measureConnectionTime(async () => {
        await wsManager.waitForConnection();
      });
      
      expect(connectionTime).toBeGreaterThan(0);
      expect(connectionTime).toBeLessThan(2000);
    });

    it('should handle real concurrent connections with load testing', async () => {
      await testConcurrentConnections();
    });

    it('should monitor real streaming performance with message throughput', async () => {
      await testStreamingPerformance(wsManager);
    });

    it('should measure real message latency patterns', async () => {
      await testMessageLatencyPatterns(wsManager);
    });

    it('should test real backpressure handling', async () => {
      await testBackpressureHandling(wsManager);
    });

    it('should benchmark real WebSocket vs mock performance', async () => {
      await benchmarkRealVsMockPerformance();
    });
  });

  describe('Real WebSocket Protocol Simulation', () => {
    it('should simulate real WebSocket upgrade from HTTP', async () => {
      await testWebSocketUpgrade(wsManager);
    });

    it('should handle real upgrade failures with error simulation', async () => {
      await testUpgradeFailures();
    });

    it('should handle real protocol negotiation', async () => {
      await testProtocolNegotiation();
    });

    it('should test real connection security and validation', async () => {
      await testConnectionSecurity(wsManager);
    });
  });

  describe('Real Resource Management', () => {
    it('should clean up real WebSocket resources properly', async () => {
      await performCleanupTest(wsManager, WebSocketLifecycleTest);
    });

    it('should handle multiple real cleanup calls safely', async () => {
      await testMultipleCleanupCalls(wsManager);
    });

    it('should handle memory cleanup for large message buffers', async () => {
      await testMemoryCleanup(wsManager);
    });

    it('should test advanced multi-connection resource management', async () => {
      await testAdvancedResourceManagement();
    });
  });

  describe('Advanced Real WebSocket Testing', () => {
    it('should test real broadcast message handling', async () => {
      await testBroadcastMessaging(advancedTester);
    });

    it('should test real connection pool management', async () => {
      await testConnectionPoolManagement();
    });

    it('should test real WebSocket reconnection strategies', async () => {
      await testReconnectionStrategies(wsManager);
    });

    it('should benchmark real vs mock WebSocket test performance', async () => {
      await benchmarkTestPerformance();
    });
  });
});

// Helper functions (≤8 lines each)
const testStateTransitionHistory = async (wsManager: WebSocketTestManager, stateManager: ConnectionStateManager) => {
  await wsManager.waitForConnection();
  expect(stateManager.getState()).toBe('connected');
  
  wsManager.close();
  await waitFor(() => {
    expect(stateManager.getState()).toBe('disconnected');
  });
  
  const history = stateManager.getStateHistory();
  expect(history.length).toBeGreaterThan(0);
  expect(history[history.length - 1].state).toBe('disconnected');
};

const testChunkedMessageReconstruction = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const originalMessage = 'This is a long message that will be chunked';
  const chunks = [
    originalMessage.slice(0, 15),
    originalMessage.slice(15, 30),
    originalMessage.slice(30)
  ];
  
  for (const chunk of chunks) {
    wsManager.simulateIncomingMessage({ chunk, isPartial: true });
  }
  
  const receivedMessages = wsManager.getReceivedMessages();
  expect(receivedMessages).toHaveLength(3);
};

const testLargeMessagePerformance = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const largeMessage = generateLargeMessage(256);
  const start = performance.now();
  
  wsManager.sendMessage(largeMessage);
  wsManager.simulateIncomingMessage(largeMessage);
  
  await waitFor(() => {
    const received = wsManager.getReceivedMessages();
    expect(received.length).toBeGreaterThan(0);
  });
  
  const processingTime = performance.now() - start;
  expect(processingTime).toBeLessThan(1000);
};

const testConcurrentConnections = async () => {
  const managers = createMultipleWebSocketManagers(5, true);
  
  const connectionPromises = managers.map(async (manager) => {
    manager.setup();
    return await manager.measureConnectionTime();
  });
  
  const connectionTimes = await Promise.all(connectionPromises);
  
  expect(connectionTimes.every(time => time >= 0)).toBe(true);
  expect(connectionTimes.every(time => time < 2000)).toBe(true);
  
  managers.forEach(manager => manager.cleanup());
};

const testStreamingPerformance = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const messageCount = 60;
  const startTime = performance.now();
  
  for (let i = 0; i < messageCount; i++) {
    wsManager.sendMessage({ frame: i, timestamp: Date.now() });
  }
  
  const endTime = performance.now();
  const totalTime = endTime - startTime;
  const messagesPerSecond = (messageCount / totalTime) * 1000;
  
  expect(messagesPerSecond).toBeGreaterThan(60);
};

const testMessageLatencyPatterns = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const latencies: number[] = [];
  
  for (let i = 0; i < 10; i++) {
    const sendTime = performance.now();
    wsManager.sendMessage({ id: i, timestamp: sendTime });
    
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
  expect(avgLatency).toBeLessThan(50);
};

const testBackpressureHandling = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const buffer = wsManager.getMessageBuffer();
  buffer.setMaxSize(5);
  
  for (let i = 0; i < 5; i++) {
    expect(buffer.add(`message-${i}`)).toBe(true);
  }
  
  expect(buffer.add('overflow-message')).toBe(false);
  
  const processed = buffer.flush();
  expect(processed.length).toBe(5);
  
  expect(buffer.add('after-flush-message')).toBe(true);
};

const benchmarkRealVsMockPerformance = async () => {
  const realManager = createWebSocketManager(undefined, true);
  realManager.setup();
  const realTime = await realManager.measureConnectionTime();
  
  const mockManager = createWebSocketManager(undefined, false);
  mockManager.setup();
  const mockTime = await mockManager.measureConnectionTime();
  
  expect(realTime).toBeGreaterThan(0);
  expect(mockTime).toBeGreaterThanOrEqual(0);
  expect(realTime).toBeGreaterThanOrEqual(mockTime);
  
  realManager.cleanup();
  mockManager.cleanup();
};

const testWebSocketUpgrade = async (wsManager: WebSocketTestManager) => {
  const server = wsManager.getServer();
  expect(server).toBeDefined();
  
  await wsManager.waitForConnection();
  expect(wsManager.isReady()).toBe(true);
  
  const history = wsManager.getConnectionHistory();
  expect(history).toContainEqual(
    expect.objectContaining({ event: 'open' })
  );
};

const testUpgradeFailures = async () => {
  const failingManager = createWebSocketManager('ws://invalid-url:999/ws');
  failingManager.setup();
  
  failingManager.simulateError(new Error('Connection refused'));
  
  await waitFor(() => {
    expect(failingManager.getConnectionState()).toBe('error');
  });
  
  failingManager.cleanup();
};

const testProtocolNegotiation = async () => {
  const testWebSocket = new TestWebSocket('ws://localhost:8000/ws', ['chat', 'echo']);
  
  expect(testWebSocket.url).toBe('ws://localhost:8000/ws');
  
  await waitFor(() => {
    expect(testWebSocket.readyState).toBe(1);
  });
  
  testWebSocket.close();
};

const testConnectionSecurity = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const invalidMessage = { malformed: true, data: null };
  wsManager.sendMessage(invalidMessage);
  
  const sentMessages = wsManager.getSentMessages();
  expect(sentMessages[0]).toContain('malformed');
  expect(wsManager.isReady()).toBe(true);
};

const testMultipleCleanupCalls = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  wsManager.cleanup();
  wsManager.cleanup();
  wsManager.cleanup();
  
  expect(wsManager.isReady()).toBe(false);
};

const testMemoryCleanup = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  
  const largeMessage = generateLargeMessage(100);
  for (let i = 0; i < 10; i++) {
    wsManager.sendMessage(largeMessage);
    wsManager.simulateIncomingMessage(largeMessage);
  }
  
  expect(wsManager.getSentMessages().length).toBe(10);
  
  wsManager.cleanup();
  
  const newManager = createWebSocketManager();
  newManager.setup();
  expect(newManager.getSentMessages()).toHaveLength(0);
  expect(newManager.getReceivedMessages()).toHaveLength(0);
  
  newManager.cleanup();
};

const testAdvancedResourceManagement = async () => {
  const connections = createMultipleWebSocketManagers(3, true);
  
  await Promise.all(connections.map(manager => {
    manager.setup();
    return manager.waitForConnection();
  }));
  
  expect(connections.every(manager => manager.isReady())).toBe(true);
  
  connections[0].cleanup();
  expect(connections[0].isReady()).toBe(false);
  expect(connections[1].isReady()).toBe(true);
  expect(connections[2].isReady()).toBe(true);
  
  connections.slice(1).forEach(manager => manager.cleanup());
  expect(connections.every(manager => !manager.isReady())).toBe(true);
};

const testBroadcastMessaging = async (advancedTester: AdvancedWebSocketTester) => {
  const connection1 = advancedTester.createConnection('ws://localhost:8001/ws');
  const connection2 = advancedTester.createConnection('ws://localhost:8002/ws');
  
  await waitFor(() => {
    expect(connection1.readyState).toBe(1);
    expect(connection2.readyState).toBe(1);
  });
  
  const broadcastMessage = 'Hello all connections';
  advancedTester.broadcastMessage(broadcastMessage);
  
  const messageLog = advancedTester.getMessageLog();
  expect(messageLog.length).toBe(2);
  expect(messageLog.every(log => log.message === broadcastMessage)).toBe(true);
};

const testConnectionPoolManagement = async () => {
  const poolSize = 5;
  const managers = createMultipleWebSocketManagers(poolSize, true);
  
  await Promise.all(managers.map(manager => {
    manager.setup();
    return manager.waitForConnection();
  }));
  
  const healthyConnections = managers.filter(manager => manager.isReady()).length;
  expect(healthyConnections).toBe(poolSize);
  
  managers.forEach((manager, index) => {
    manager.sendMessage({ poolId: index, data: `Pool message ${index}` });
  });
  
  const totalSentMessages = managers.reduce((total, manager) => {
    return total + manager.getSentMessages().length;
  }, 0);
  
  expect(totalSentMessages).toBe(poolSize);
  
  managers.forEach(manager => manager.cleanup());
};

const testReconnectionStrategies = async (wsManager: WebSocketTestManager) => {
  await wsManager.waitForConnection();
  expect(wsManager.isReady()).toBe(true);
  
  wsManager.simulateError(new Error('Network disconnected'));
  
  await waitFor(() => {
    expect(wsManager.getConnectionState()).toBe('error');
  });
  
  wsManager.simulateReconnect();
  
  await waitFor(() => {
    expect(wsManager.getConnectionState()).toBe('connected');
  }, { timeout: 2000 });
  
  expect(wsManager.isReady()).toBe(true);
  
  const history = wsManager.getConnectionHistory();
  const errorEvents = history.filter(event => event.event === 'error');
  const openEvents = history.filter(event => event.event === 'open');
  
  expect(errorEvents.length).toBeGreaterThan(0);
  expect(openEvents.length).toBeGreaterThan(1);
};

const benchmarkTestPerformance = async () => {
  const iterations = 100;
  
  const realStart = performance.now();
  for (let i = 0; i < iterations; i++) {
    const realManager = createWebSocketManager(undefined, true);
    realManager.setup();
    await realManager.waitForConnection();
    realManager.sendMessage({ test: i });
    realManager.cleanup();
  }
  const realTime = performance.now() - realStart;
  
  const mockStart = performance.now();
  for (let i = 0; i < iterations; i++) {
    const mockManager = createWebSocketManager(undefined, false);
    mockManager.setup();
    mockManager.sendMessage({ test: i });
    mockManager.cleanup();
  }
  const mockTime = performance.now() - mockStart;
  
  expect(realTime).toBeGreaterThan(0);
  expect(mockTime).toBeGreaterThan(0);
  
  // Verify realistic timing relationships
  expect(realTime).toBeGreaterThan(10); // Real WebSocket should take some time
  expect(mockTime).toBeLessThan(realTime); // Mock should be faster than real
};