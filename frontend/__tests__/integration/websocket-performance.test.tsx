import { waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import { 
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
t.tsx for modularity  
 * Tests performance monitoring, connection pools, broadcasting, and benchmarking
 * Focuses on advanced WebSocket scenarios and performance measurement
 */

import { waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import { 
  WebSocketTestManager, 
  createWebSocketManager,
  createMultipleWebSocketManagers 
} from '../helpers/websocket-test-manager';
import { measureConnectionTime } from '../setup/websocket-test-utils';
import { AdvancedWebSocketTester } from '../setup/websocket-test-utils';

describe('WebSocket Performance and Advanced Tests', () => {
    jest.setTimeout(10000);
  let wsManager: WebSocketTestManager;
  let advancedTester: AdvancedWebSocketTester;

  beforeEach(() => {
    // Use real WebSocket simulation instead of mocks
    wsManager = createWebSocketManager(undefined, true);
    advancedTester = new AdvancedWebSocketTester();
    wsManager.setup();
  });

  afterEach(() => {
    wsManager.cleanup();
    advancedTester.closeAllConnections();
    advancedTester.clearLog();
    jest.clearAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Performance Monitoring', () => {
      jest.setTimeout(10000);
    it('should measure real connection performance with timing', async () => {
      const connectionTime = await measureConnectionTime(async () => {
        await wsManager.waitForConnection();
      });
      
      expect(connectionTime).toBeGreaterThan(0);
      expect(connectionTime).toBeLessThan(2000); // Should connect within 2 seconds
    });

    it('should track connection stability over time', async () => {
      await wsManager.waitForConnection();
      
      const testDuration = 500; // 500ms test
      const startTime = Date.now();
      let connectionChecks = 0;
      
      // Monitor connection stability
      const interval = setInterval(() => {
        if (wsManager.isReady()) {
          connectionChecks++;
        }
      }, 50);
      
      await new Promise(resolve => setTimeout(resolve, testDuration));
      clearInterval(interval);
      
      const endTime = Date.now();
      const actualDuration = endTime - startTime;
      
      expect(actualDuration).toBeGreaterThan(400);
      expect(connectionChecks).toBeGreaterThan(5); // Should be stable
    });

    it('should measure message throughput performance', async () => {
      await wsManager.waitForConnection();
      
      const messageCount = 100;
      const startTime = performance.now();
      
      // Send messages rapidly
      for (let i = 0; i < messageCount; i++) {
        wsManager.sendMessage({ index: i, data: `Perf test ${i}` });
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      const throughput = messageCount / (duration / 1000);
      
      expect(throughput).toBeGreaterThan(50); // Should handle 50+ msg/sec
      expect(duration).toBeLessThan(2000); // Should complete within 2 seconds
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages.length).toBe(messageCount);
    });
  });

  describe('Connection Pooling', () => {
      jest.setTimeout(10000);
    it('should handle real concurrent connections with load testing', async () => {
      const connectionCount = 3;
      const connections = [];
      
      // Create multiple connections
      for (let i = 0; i < connectionCount; i++) {
        const connection = advancedTester.createConnection(`ws://localhost:800${i}/ws`);
        connections.push(connection);
      }
      
      // Wait for all connections
      await waitFor(() => {
        const readyConnections = connections.filter(conn => conn.readyState === 1);
        expect(readyConnections.length).toBe(connectionCount);
      });
      
      // Test load across connections
      connections.forEach((connection, index) => {
        advancedTester.sendMessage(connection, `Load test message ${index}`);
      });
      
      const messageLog = advancedTester.getMessageLog();
      expect(messageLog.length).toBe(connectionCount);
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

    it('should handle pool failover scenarios', async () => {
      const poolSize = 3;
      const managers = createMultipleWebSocketManagers(poolSize, true);
      
      // Initialize pool
      await Promise.all(managers.map(manager => {
        manager.setup();
        return manager.waitForConnection();
      }));
      
      // Simulate one connection failing
      managers[0].simulateError(new Error('Connection failed'));
      
      await waitFor(() => {
        expect(managers[0].getConnectionState()).toBe('error');
      });
      
      // Verify other connections still work
      const workingManagers = managers.slice(1);
      workingManagers.forEach((manager, index) => {
        expect(manager.isReady()).toBe(true);
        manager.sendMessage({ failover: true, index });
      });
      
      const totalMessages = workingManagers.reduce((total, manager) => {
        return total + manager.getSentMessages().length;
      }, 0);
      
      expect(totalMessages).toBe(poolSize - 1);
      
      // Cleanup
      managers.forEach(manager => manager.cleanup());
    });
  });

  describe('Broadcasting', () => {
      jest.setTimeout(10000);
    it('should test real multi-connection broadcasting', async () => {
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

    it('should handle selective broadcasting', async () => {
      const connections = [];
      for (let i = 0; i < 4; i++) {
        const connection = advancedTester.createConnection(`ws://localhost:800${i}/ws`);
        connections.push(connection);
      }
      
      // Wait for all connections
      await waitFor(() => {
        const readyCount = connections.filter(conn => conn.readyState === 1).length;
        expect(readyCount).toBe(4);
      });
      
      // Selective broadcast to first 2 connections
      const selectedConnections = connections.slice(0, 2);
      selectedConnections.forEach(connection => {
        advancedTester.sendMessage(connection, 'Selective message');
      });
      
      const messageLog = advancedTester.getMessageLog();
      expect(messageLog.length).toBe(2);
      expect(messageLog.every(log => log.message === 'Selective message')).toBe(true);
    });
  });

  describe('Benchmarking', () => {
      jest.setTimeout(10000);
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
      
      // Verify realistic timing relationships
      expect(realTime).toBeGreaterThan(10); // Real WebSocket should take some time
      expect(mockTime).toBeLessThan(realTime); // Mock should be faster than real
    });

    it('should benchmark connection establishment times', async () => {
      const connectionCount = 10;
      const connectionTimes: number[] = [];
      
      for (let i = 0; i < connectionCount; i++) {
        const manager = createWebSocketManager(undefined, true);
        
        const startTime = performance.now();
        manager.setup();
        await manager.waitForConnection();
        const connectionTime = performance.now() - startTime;
        
        connectionTimes.push(connectionTime);
        manager.cleanup();
      }
      
      // Calculate statistics
      const avgTime = connectionTimes.reduce((a, b) => a + b, 0) / connectionCount;
      const maxTime = Math.max(...connectionTimes);
      const minTime = Math.min(...connectionTimes);
      
      expect(avgTime).toBeLessThan(500); // Average should be reasonable
      expect(maxTime).toBeLessThan(1000); // Max time shouldn't be excessive
      expect(minTime).toBeGreaterThan(0); // Should take some time
      expect(connectionTimes.length).toBe(connectionCount);
    });

    it('should benchmark message processing latency', async () => {
      await wsManager.waitForConnection();
      
      const messageCount = 50;
      const latencies: number[] = [];
      
      for (let i = 0; i < messageCount; i++) {
        const testMessage = { id: `latency-test-${i}`, echo: true };
        const latency = await wsManager.measureMessageRoundTrip(testMessage);
        latencies.push(latency);
      }
      
      // Calculate latency statistics
      const avgLatency = latencies.reduce((a, b) => a + b, 0) / messageCount;
      const maxLatency = Math.max(...latencies);
      const minLatency = Math.min(...latencies);
      
      expect(avgLatency).toBeLessThan(50); // Should be fast
      expect(maxLatency).toBeLessThan(200); // No message should be too slow
      expect(minLatency).toBeGreaterThan(0); // Should take some time
      expect(latencies.length).toBe(messageCount);
    });
  });

});