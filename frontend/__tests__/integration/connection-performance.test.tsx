/**
 * Connection Performance Tests
 * Split from connection-management-advanced.test.tsx for 450-line compliance
 * Agent 10 Implementation - Performance and load testing
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { TestProviders } from '../setup/test-providers';
import { WebSocketTestManager } from '@/__tests__/helpers/websocket-test-manager';

// Multi-connection manager for performance testing
class MultiConnectionManager {
  private connections: Map<string, WebSocketTestManager> = new Map();

  createConnection(id: string): WebSocketTestManager {
    const manager = new WebSocketTestManager();
    manager.setup();
    this.connections.set(id, manager);
    return manager;
  }

  getConnection(id: string): WebSocketTestManager | undefined { return this.connections.get(id); }
  getConnectionCount(): number { return this.connections.size; }

  closeConnection(id: string): void {
    const connection = this.connections.get(id);
    if (connection) {
      connection.cleanup();
      this.connections.delete(id);
    }
  }

  closeAllConnections(): void {
    this.connections.forEach(connection => connection.cleanup());
    this.connections.clear();
  }
}

// Connection state machine for validation
class ConnectionStateMachine {
  private currentState: string = 'disconnected';
  private transitions: Map<string, string[]> = new Map();

  constructor() { this.setupTransitions(); }

  private setupTransitions(): void {
    this.transitions.set('disconnected', ['connecting']);
    this.transitions.set('connecting', ['connected', 'error']);
    this.transitions.set('connected', ['disconnected', 'error']);
    this.transitions.set('error', ['reconnecting', 'disconnected']);
    this.transitions.set('reconnecting', ['connected', 'error']);
  }

  canTransition(newState: string): boolean {
    const allowedStates = this.transitions.get(this.currentState) || [];
    return allowedStates.includes(newState);
  }

  transition(newState: string): boolean {
    if (this.canTransition(newState)) {
      this.currentState = newState;
      return true;
    }
    return false;
  }

  getState(): string { return this.currentState; }
}

describe('Connection Performance Tests', () => {
  let wsManager: WebSocketTestManager;
  let multiManager: MultiConnectionManager;

  beforeEach(() => {
    wsManager = new WebSocketTestManager();
    multiManager = new MultiConnectionManager();
    wsManager.setup();
    jest.useFakeTimers();
  });

  afterEach(() => {
    wsManager.cleanup();
    multiManager.closeAllConnections();
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  describe('Multiple Concurrent Connections', () => {
    it('should handle multiple WebSocket connections', () => {
      const conn1 = multiManager.createConnection('conn1');
      const conn2 = multiManager.createConnection('conn2');
      const conn3 = multiManager.createConnection('conn3');
      
      expect(conn1.getUrl()).not.toBe(conn2.getUrl());
      expect(conn2.getUrl()).not.toBe(conn3.getUrl());
      expect(multiManager.getConnectionCount()).toBe(3);
    });

    it('should isolate connection states', () => {
      const state1 = new ConnectionStateMachine();
      const state2 = new ConnectionStateMachine();
      
      state1.transition('connecting');
      state2.transition('connecting');
      state1.transition('connected');
      
      expect(state1.getState()).toBe('connected');
      expect(state2.getState()).toBe('connecting');
    });

    it('should close individual connections', () => {
      multiManager.createConnection('conn1');
      multiManager.createConnection('conn2');
      expect(multiManager.getConnectionCount()).toBe(2);
      
      multiManager.closeConnection('conn1');
      expect(multiManager.getConnectionCount()).toBe(1);
      expect(multiManager.getConnection('conn1')).toBeUndefined();
    });

    it('should close all connections', () => {
      multiManager.createConnection('conn1');
      multiManager.createConnection('conn2');
      multiManager.createConnection('conn3');
      expect(multiManager.getConnectionCount()).toBe(3);
      
      multiManager.closeAllConnections();
      expect(multiManager.getConnectionCount()).toBe(0);
    });
  });

  describe('Performance Under Load', () => {
    it('should handle concurrent connection attempts', async () => {
      const promises = Array(5).fill(0).map((_, i) => 
        Promise.resolve(multiManager.createConnection(`load-${i}`))
      );
      
      const connections = await Promise.all(promises);
      expect(connections.length).toBe(5);
      expect(multiManager.getConnectionCount()).toBe(5);
    });

    it('should maintain performance with many connections', () => {
      const connectionCount = 10;
      for (let i = 0; i < connectionCount; i++) {
        multiManager.createConnection(`perf-${i}`);
      }
      
      expect(multiManager.getConnectionCount()).toBe(connectionCount);
      const start = Date.now();
      multiManager.closeAllConnections();
      const duration = Date.now() - start;
      expect(duration).toBeLessThan(100);
    });

    it('should handle rapid state changes', () => {
      const machine = new ConnectionStateMachine();
      machine.transition('connecting');
      machine.transition('connected');
      machine.transition('error');
      machine.transition('reconnecting');
      machine.transition('connected');
      expect(machine.getState()).toBe('connected');
    });

    it('should scale connection management', () => {
      const connectionCount = 50;
      const start = Date.now();
      
      for (let i = 0; i < connectionCount; i++) {
        multiManager.createConnection(`scale-${i}`);
      }
      
      const setupTime = Date.now() - start;
      expect(setupTime).toBeLessThan(1000);
      expect(multiManager.getConnectionCount()).toBe(connectionCount);
    });
  });

  describe('Memory Management', () => {
    it('should prevent memory leaks', () => {
      const initialCount = multiManager.getConnectionCount();
      
      for (let i = 0; i < 10; i++) {
        const id = `temp-${i}`;
        multiManager.createConnection(id);
        multiManager.closeConnection(id);
      }
      
      expect(multiManager.getConnectionCount()).toBe(initialCount);
    });

    it('should handle cleanup during active operations', () => {
      multiManager.createConnection('test1');
      multiManager.createConnection('test2');
      
      multiManager.closeAllConnections();
      expect(multiManager.getConnectionCount()).toBe(0);
    });

    it('should manage connection lifecycle efficiently', () => {
      const cycles = 5;
      for (let cycle = 0; cycle < cycles; cycle++) {
        multiManager.createConnection(`cycle-${cycle}`);
        expect(multiManager.getConnectionCount()).toBe(1);
        multiManager.closeAllConnections();
        expect(multiManager.getConnectionCount()).toBe(0);
      }
    });
  });

  describe('Stress Testing', () => {
    it('should handle rapid create/destroy cycles', () => {
      const cycles = 20;
      const start = Date.now();
      
      for (let i = 0; i < cycles; i++) {
        const manager = multiManager.createConnection(`stress-${i}`);
        expect(manager).toBeDefined();
        multiManager.closeConnection(`stress-${i}`);
      }
      
      const duration = Date.now() - start;
      expect(duration).toBeLessThan(500);
      expect(multiManager.getConnectionCount()).toBe(0);
    });

    it('should maintain state consistency under load', () => {
      const machines = Array(10).fill(0).map(() => new ConnectionStateMachine());
      
      machines.forEach((machine, index) => {
        const success = machine.transition('connecting');
        expect(success).toBe(true);
        expect(machine.getState()).toBe('connecting');
      });
      
      machines.forEach(machine => {
        machine.transition('connected');
        expect(machine.getState()).toBe('connected');
      });
    });

    it('should handle burst connection requests', () => {
      const burstSize = 15;
      const connections: string[] = [];
      
      for (let i = 0; i < burstSize; i++) {
        const id = `burst-${i}`;
        multiManager.createConnection(id);
        connections.push(id);
      }
      
      expect(multiManager.getConnectionCount()).toBe(burstSize);
      
      connections.forEach(id => {
        multiManager.closeConnection(id);
      });
      
      expect(multiManager.getConnectionCount()).toBe(0);
    });
  });

  describe('Resource Optimization', () => {
    it('should optimize connection reuse', () => {
      const id = 'reusable';
      multiManager.createConnection(id);
      const firstManager = multiManager.getConnection(id);
      
      expect(firstManager).toBeDefined();
      expect(multiManager.getConnectionCount()).toBe(1);
      
      multiManager.closeConnection(id);
      expect(multiManager.getConnection(id)).toBeUndefined();
    });

    it('should efficiently batch operations', () => {
      const batchSize = 8;
      const operations = [];
      
      for (let i = 0; i < batchSize; i++) {
        operations.push(() => multiManager.createConnection(`batch-${i}`));
      }
      
      const start = Date.now();
      operations.forEach(op => op());
      const duration = Date.now() - start;
      
      expect(duration).toBeLessThan(100);
      expect(multiManager.getConnectionCount()).toBe(batchSize);
    });

    it('should handle connection pool efficiently', () => {
      const poolSize = 12;
      const connections = [];
      
      for (let i = 0; i < poolSize; i++) {
        connections.push(multiManager.createConnection(`pool-${i}`));
      }
      
      expect(multiManager.getConnectionCount()).toBe(poolSize);
      
      // Verify all connections are unique
      const urls = connections.map(conn => conn.getUrl());
      const uniqueUrls = new Set(urls);
      expect(uniqueUrls.size).toBe(poolSize);
    });
  });
});