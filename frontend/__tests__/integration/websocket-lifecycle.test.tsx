/**
 * WebSocket Connection Lifecycle Tests
 * Extracted from oversized websocket-complete.test.tsx for modularity
 * Tests complete WebSocket connection lifecycle with realistic conditions
 * Focuses on connection, disconnection, errors, and reconnection scenarios
 */

import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import { TestProviders } from '@/__tests__/setup/test-providers';
import { WebSocketTestManager, createWebSocketManager } from '@/__tests__/helpers/websocket-test-manager';
import {
  WebSocketConnectionLifecycle,
  measurePerformance
} from '@/__tests__/helpers/websocket-test-utilities';
import {
  ConnectionStateManager,
  measureConnectionTime
} from '@/__tests__/setup/websocket-test-utils';
import { WebSocketLifecycleTest } from './utils/websocket-test-components';

describe('WebSocket Connection Lifecycle Tests', () => {
  let wsManager: WebSocketTestManager;
  let stateManager: ConnectionStateManager;

  beforeEach(() => {
    // Use real WebSocket simulation instead of mocks
    wsManager = createWebSocketManager(undefined, true);
    stateManager = wsManager.getStateManager();
    wsManager.setup();
  });

  afterEach(() => {
    wsManager.cleanup();
    jest.clearAllMocks();
  });

  describe('Connection Establishment', () => {
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

    it('should track real connection state transitions with history', async () => {
      // Test real state transitions
      await wsManager.waitForConnection(3000);
      expect(stateManager.getState()).toBe('connected');
      
      wsManager.close();
      await waitFor(() => {
        expect(stateManager.getState()).toBe('disconnected');
      }, { timeout: 2000 });
      
      const history = stateManager.getStateHistory();
      expect(history.length).toBeGreaterThan(0);
      expect(history[history.length - 1].state).toBe('disconnected');
    });

    it('should measure real connection performance', async () => {
      const connectionTime = await wsManager.measureConnectionTime();
      expect(connectionTime).toBeGreaterThan(0);
      expect(connectionTime).toBeLessThan(3000); // Should be fast in tests
    });
  });

  describe('Error Handling', () => {
    it('should handle real connection errors with proper state transitions', async () => {
      render(
        <TestProviders>
          <WebSocketLifecycleTest />
        </TestProviders>
      );

      // Wait for initial connection first
      await wsManager.waitForConnection(3000);
      expect(wsManager.getConnectionState()).toBe('connected');

      // Simulate real error
      wsManager.simulateError(new Error('Connection failed'));
      
      await waitFor(() => {
        expect(wsManager.getConnectionState()).toBe('error');
      }, { timeout: 2000 });
      
      expect(wsManager.getConnectionHistory()).toContainEqual(
        expect.objectContaining({ event: 'error' })
      );
    });

    it('should handle network disconnections gracefully', async () => {
      await wsManager.waitForConnection();
      expect(wsManager.isReady()).toBe(true);
      
      // Simulate network failure
      wsManager.simulateError(new Error('Network disconnected'));
      
      await waitFor(() => {
        expect(wsManager.getConnectionState()).toBe('error');
      });
      
      // Verify error is logged properly
      const history = wsManager.getConnectionHistory();
      const errorEvents = history.filter(event => event.event === 'error');
      expect(errorEvents.length).toBeGreaterThan(0);
    });
  });

  describe('Reconnection Scenarios', () => {
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

    it('should handle multiple reconnection attempts', async () => {
      await wsManager.waitForConnection();
      
      // Force multiple reconnection attempts
      for (let i = 0; i < 3; i++) {
        wsManager.simulateError(new Error(`Disconnect ${i}`));
        await waitFor(() => {
          expect(wsManager.getConnectionState()).toBe('error');
        });
        
        wsManager.simulateReconnect();
        await waitFor(() => {
          expect(wsManager.getConnectionState()).toBe('connected');
        }, { timeout: 1000 });
      }
      
      // Verify final state
      expect(wsManager.isReady()).toBe(true);
      
      // Check reconnection history
      const history = wsManager.getConnectionHistory();
      const openEvents = history.filter(event => event.event === 'open');
      expect(openEvents.length).toBe(4); // Initial + 3 reconnections
    });
  });

  describe('Performance Measurement', () => {
    it('should measure real connection performance with timing', async () => {
      const connectionTime = await measureConnectionTime(async () => {
        await wsManager.waitForConnection();
      });
      
      expect(connectionTime).toBeGreaterThan(0);
      expect(connectionTime).toBeLessThan(2000); // Should connect within 2 seconds
    });

    it('should track connection stability metrics', async () => {
      const startTime = Date.now();
      await wsManager.waitForConnection();
      
      // Keep connection alive for testing
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const uptime = Date.now() - startTime;
      expect(uptime).toBeGreaterThan(50);
      expect(wsManager.isReady()).toBe(true);
    });
  });
});