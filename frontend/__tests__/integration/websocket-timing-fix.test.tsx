/**
 * WebSocket Timing Fix Integration Test
 * CRITICAL: Demonstrates proper React act() and timing handling
 * Fixes the most common WebSocket test failure patterns
 * ≤300 lines, ≤8 lines per function
 */

import React from 'react';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { act } from '@testing-library/react';
import { ActUtils } from '../test-utils/react-act-utils';
import { createWebSocketManager } from '../helpers/websocket-test-manager';
import { TestProviders } from '../setup/test-providers';

// Simple test component that uses WebSocket
const WebSocketTimingTestComponent: React.FC = () => {
  const [connectionState, setConnectionState] = React.useState('disconnected');
  const [messageCount, setMessageCount] = React.useState(0);
  const [lastMessage, setLastMessage] = React.useState('');

  const handleConnect = async () => {
    await ActUtils.stateUpdate(() => {
      setConnectionState('connecting');
    });
    
    // Simulate connection
    await ActUtils.delay(50);
    
    await ActUtils.stateUpdate(() => {
      setConnectionState('connected');
    });
  };

  const handleSendMessage = async () => {
    await ActUtils.stateUpdate(() => {
      setMessageCount(prev => prev + 1);
      setLastMessage(`Message ${messageCount + 1}`);
    });
  };

  const handleDisconnect = async () => {
    await ActUtils.stateUpdate(() => {
      setConnectionState('disconnected');
    });
  };

  return (
    <div data-testid="websocket-timing-test">
      <div data-testid="connection-state">{connectionState}</div>
      <div data-testid="message-count">{messageCount}</div>
      <div data-testid="last-message">{lastMessage}</div>
      <button data-testid="connect-btn" onClick={handleConnect}>
        Connect
      </button>
      <button data-testid="send-btn" onClick={handleSendMessage}>
        Send Message
      </button>
      <button data-testid="disconnect-btn" onClick={handleDisconnect}>
        Disconnect
      </button>
    </div>
  );
};

describe('WebSocket Timing Fix Tests', () => {
  let wsManager: ReturnType<typeof createWebSocketManager>;

  beforeEach(async () => {
    await ActUtils.cleanup(() => {
      wsManager = createWebSocketManager(undefined, true);
      wsManager.setup();
    });
  });

  afterEach(async () => {
    await ActUtils.cleanup(() => {
      wsManager?.cleanup();
      cleanup();
    });
  });

  describe('Connection Lifecycle with Proper Timing', () => {
    it('should handle connection with proper act() wrapping', async () => {
      const { unmount } = render(
        <TestProviders>
          <WebSocketTimingTestComponent />
        </TestProviders>
      );

      // Wait for initial render
      await ActUtils.waitFor(() => {
        expect(screen.getByTestId('connection-state')).toBeInTheDocument();
      });

      // Test connection with proper timing
      const connectBtn = screen.getByTestId('connect-btn');
      
      await ActUtils.userInteraction(async () => {
        await userEvent.click(connectBtn);
      });

      // Wait for connection state update
      await ActUtils.waitFor(() => {
        expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
      });

      unmount();
    });

    it('should handle message sending with act() synchronization', async () => {
      const { unmount } = render(
        <TestProviders>
          <WebSocketTimingTestComponent />
        </TestProviders>
      );

      // Connect first
      const connectBtn = screen.getByTestId('connect-btn');
      await ActUtils.userInteraction(async () => {
        await userEvent.click(connectBtn);
      });

      await ActUtils.waitFor(() => {
        expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
      });

      // Send message
      const sendBtn = screen.getByTestId('send-btn');
      await ActUtils.userInteraction(async () => {
        await userEvent.click(sendBtn);
      });

      // Verify message count update
      await ActUtils.waitFor(() => {
        expect(screen.getByTestId('message-count')).toHaveTextContent('1');
        expect(screen.getByTestId('last-message')).toHaveTextContent('Message 1');
      });

      unmount();
    });

    it('should handle disconnection with proper cleanup', async () => {
      const { unmount } = render(
        <TestProviders>
          <WebSocketTimingTestComponent />
        </TestProviders>
      );

      // Connect and then disconnect
      const connectBtn = screen.getByTestId('connect-btn');
      const disconnectBtn = screen.getByTestId('disconnect-btn');

      await ActUtils.userInteraction(async () => {
        await userEvent.click(connectBtn);
      });

      await ActUtils.waitFor(() => {
        expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
      });

      await ActUtils.userInteraction(async () => {
        await userEvent.click(disconnectBtn);
      });

      await ActUtils.waitFor(() => {
        expect(screen.getByTestId('connection-state')).toHaveTextContent('disconnected');
      });

      unmount();
    });
  });

  describe('Real WebSocket Manager Integration', () => {
    it('should properly wait for WebSocket connection', async () => {
      // Use real WebSocket timing
      await ActUtils.webSocketConnect(async () => {
        await wsManager.waitForConnection(1000);
      });

      expect(wsManager.isReady()).toBe(true);
      expect(wsManager.getConnectionState()).toBe('connected');
    });

    it('should handle message sending with proper timing', async () => {
      await ActUtils.webSocketConnect(async () => {
        await wsManager.waitForConnection();
      });

      const testMessage = { type: 'test', data: 'Hello WebSocket' };
      
      await ActUtils.webSocketSend(() => {
        wsManager.sendMessage(testMessage);
      });

      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages).toHaveLength(1);
      expect(sentMessages[0]).toContain('Hello WebSocket');
    });

    it('should handle incoming messages with act() wrapping', async () => {
      await ActUtils.webSocketConnect(async () => {
        await wsManager.waitForConnection();
      });

      const testMessage = { type: 'incoming', data: 'Server message' };
      
      await ActUtils.async(async () => {
        wsManager.simulateIncomingMessage(testMessage);
      });

      await ActUtils.waitFor(() => {
        const receivedMessages = wsManager.getReceivedMessages();
        expect(receivedMessages.length).toBeGreaterThan(0);
      });
    });

    it('should handle connection errors gracefully', async () => {
      const error = new Error('Connection failed');
      
      await ActUtils.errorHandler(
        async () => {
          wsManager.simulateError(error);
        },
        (err) => {
          expect(err.message).toBe('Connection failed');
        }
      );

      await ActUtils.waitFor(() => {
        expect(wsManager.getConnectionState()).toBe('error');
      });
    });

    it('should handle reconnection with proper timing', async () => {
      // Initial connection
      await ActUtils.webSocketConnect(async () => {
        await wsManager.waitForConnection();
      });

      expect(wsManager.isReady()).toBe(true);

      // Simulate disconnect
      await ActUtils.webSocketDisconnect(() => {
        wsManager.simulateError(new Error('Network disconnected'));
      });

      await ActUtils.waitFor(() => {
        expect(wsManager.getConnectionState()).toBe('error');
      });

      // Reconnect
      await ActUtils.webSocketConnect(async () => {
        wsManager.simulateReconnect();
        await wsManager.waitForConnection(2000);
      });

      expect(wsManager.isReady()).toBe(true);
      expect(wsManager.getConnectionState()).toBe('connected');
    });
  });

  describe('Performance and Heartbeat Tests', () => {
    it('should handle heartbeat without causing timing conflicts', async () => {
      const timer = ActUtils.createActTimer();
      let heartbeatCount = 0;

      await ActUtils.webSocketConnect(async () => {
        await wsManager.waitForConnection();
      });

      // Simulate heartbeat every 100ms
      timer.setInterval(() => {
        heartbeatCount++;
        wsManager.sendMessage({ type: 'ping', timestamp: Date.now() });
      }, 100);

      // Wait for multiple heartbeats
      await ActUtils.delay(350);

      expect(heartbeatCount).toBeGreaterThan(2);
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages.filter(msg => msg.includes('ping')).length).toBeGreaterThan(2);

      timer.clearAll();
    });

    it('should measure performance without act() warnings', async () => {
      const performanceTime = await ActUtils.retry(async () => {
        return wsManager.measureConnectionTime();
      }, 3, 100);

      expect(performanceTime).toBeGreaterThan(0);
      expect(performanceTime).toBeLessThan(1000); // Should be fast in tests
    });

    it('should handle concurrent operations without race conditions', async () => {
      await ActUtils.webSocketConnect(async () => {
        await wsManager.waitForConnection();
      });

      const operations = Array(5).fill(0).map((_, i) => 
        () => ActUtils.webSocketSend(() => {
          wsManager.sendMessage({ id: i, data: `Message ${i}` });
        })
      );

      await ActUtils.batch(operations);

      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages.length).toBe(5);
    });
  });

  describe('Cleanup and Resource Management', () => {
    it('should cleanup resources without warnings', async () => {
      await ActUtils.webSocketConnect(async () => {
        await wsManager.waitForConnection();
      });

      expect(wsManager.isReady()).toBe(true);

      await ActUtils.cleanup(() => {
        wsManager.cleanup();
      });

      expect(wsManager.isReady()).toBe(false);
      expect(wsManager.getSentMessages()).toHaveLength(0);
    });

    it('should handle multiple cleanup calls safely', async () => {
      await ActUtils.webSocketConnect(async () => {
        await wsManager.waitForConnection();
      });

      // Multiple cleanup calls should be safe
      await ActUtils.cleanup(() => {
        wsManager.cleanup();
        wsManager.cleanup();
        wsManager.cleanup();
      });

      expect(wsManager.isReady()).toBe(false);
    });
  });
});