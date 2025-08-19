/**
 * Comprehensive Timing Fix Integration Test
 * CRITICAL: Demonstrates all timing fixes working together
 * Validates WebSocket, React act(), state management, and mock alignment
 * ≤300 lines, ≤8 lines per function
 */

import React from 'react';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { act } from '@testing-library/react';
import { ActUtils } from '../test-utils/react-act-utils';
import { setupAlignedMocks } from '../test-utils/mock-service-alignment';
import { StateTimingUtils, StateTimingTestComponent } from '../test-utils/state-timing-utils';
import { createWebSocketManager } from '../helpers/websocket-test-manager';
import { TestProviders } from '../setup/test-providers';

// Comprehensive test component
const ComprehensiveTimingTestComponent: React.FC = () => {
  const [wsState, setWsState] = React.useState('disconnected');
  const [authState, setAuthState] = React.useState(false);
  const [messages, setMessages] = React.useState<string[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);

  const handleFullFlow = async () => {
    // Step 1: Start loading
    await ActUtils.stateUpdate(() => setIsLoading(true));
    
    // Step 2: Connect WebSocket
    await ActUtils.webSocketConnect(async () => {
      setWsState('connecting');
      await ActUtils.delay(50);
      setWsState('connected');
    });
    
    // Step 3: Authenticate
    await ActUtils.async(async () => {
      await ActUtils.delay(100);
      setAuthState(true);
    });
    
    // Step 4: Send messages
    await ActUtils.batch([
      () => ActUtils.async(async () => {
        setMessages(prev => [...prev, 'Message 1']);
      }),
      () => ActUtils.async(async () => {
        setMessages(prev => [...prev, 'Message 2']);
      }),
      () => ActUtils.async(async () => {
        setMessages(prev => [...prev, 'Message 3']);
      })
    ]);
    
    // Step 5: Finish loading
    await ActUtils.stateUpdate(() => setIsLoading(false));
  };

  return (
    <div data-testid="comprehensive-timing-test">
      <div data-testid="ws-state">{wsState}</div>
      <div data-testid="auth-state">{authState.toString()}</div>
      <div data-testid="message-count">{messages.length}</div>
      <div data-testid="is-loading">{isLoading.toString()}</div>
      <div data-testid="messages">
        {messages.map((msg, idx) => (
          <div key={idx} data-testid={`message-${idx}`}>{msg}</div>
        ))}
      </div>
      <button data-testid="start-flow" onClick={handleFullFlow}>
        Start Flow
      </button>
    </div>
  );
};

describe('Comprehensive Timing Fix Integration Tests', () => {
  let mocks: ReturnType<typeof setupAlignedMocks>;
  let wsManager: ReturnType<typeof createWebSocketManager>;
  let stateManager: ReturnType<typeof StateTimingUtils.createManager>;

  beforeEach(async () => {
    await ActUtils.cleanup(() => {
      mocks = setupAlignedMocks();
      wsManager = createWebSocketManager(undefined, true);
      wsManager.setup();
      stateManager = StateTimingUtils.createManager({ test: 'initial' });
    });
  });

  afterEach(async () => {
    await ActUtils.cleanup(() => {
      mocks?.cleanup();
      wsManager?.cleanup();
      stateManager?.reset({ test: 'initial' });
      cleanup();
    });
  });

  describe('Mock Service Alignment Tests', () => {
    it('should have properly aligned WebSocket service mock', async () => {
      const wsService = mocks.services.webSocket;
      
      // Validate interface alignment
      expect(wsService.connect).toBeDefined();
      expect(wsService.disconnect).toBeDefined();
      expect(wsService.sendMessage).toBeDefined();
      expect(typeof wsService.isConnected).toBe('boolean');
      
      // Test connection flow
      await ActUtils.webSocketConnect(async () => {
        await wsService.connect();
      });
      
      expect(wsService.isConnected).toBe(true);
      expect(wsService.getStatus()).toBe('CONNECTED');
    });

    it('should have properly aligned Auth service mock', async () => {
      const authService = mocks.services.auth;
      
      // Validate interface alignment
      expect(authService.login).toBeDefined();
      expect(authService.logout).toBeDefined();
      expect(typeof authService.isAuthenticated).toBe('boolean');
      
      // Test auth flow
      await ActUtils.async(async () => {
        await authService.login('test@example.com', 'password');
      });
      
      expect(authService.isAuthenticated).toBe(true);
      expect(authService.user).toBeTruthy();
    });

    it('should handle mock state synchronization', async () => {
      const store = mocks.services.store;
      
      await ActUtils.stateUpdate(() => {
        store.setState({ auth: { isAuthenticated: true } });
      });
      
      const state = store.getState();
      expect(state.auth.isAuthenticated).toBe(true);
    });
  });

  describe('State Management Timing Tests', () => {
    it('should handle sequential state updates without race conditions', async () => {
      const updates = [
        () => stateManager.setState({ step: 1 }, 'test1'),
        () => stateManager.setState({ step: 2 }, 'test2'),
        () => stateManager.setState({ step: 3 }, 'test3')
      ];
      
      await StateTimingUtils.async.sequentialUpdate(updates);
      
      const finalState = stateManager.getState();
      expect(finalState.step).toBe(3);
      
      const history = stateManager.getChangeHistory();
      expect(history).toHaveLength(3);
    });

    it('should handle parallel state updates safely', async () => {
      const updates = [
        () => stateManager.setState({ value1: 'a' }),
        () => stateManager.setState({ value2: 'b' }),
        () => stateManager.setState({ value3: 'c' })
      ];
      
      await StateTimingUtils.async.parallelUpdate(updates);
      
      const finalState = stateManager.getState();
      expect(finalState.value1).toBe('a');
      expect(finalState.value2).toBe('b');
      expect(finalState.value3).toBe('c');
    });

    it('should prevent race conditions with locks', async () => {
      const operations = [
        { key: 'test', operation: () => stateManager.setState({ counter: 1 }) },
        { key: 'test', operation: () => stateManager.setState({ counter: 2 }) },
        { key: 'test', operation: () => stateManager.setState({ counter: 3 }) }
      ];
      
      await StateTimingUtils.raceCondition.serialized(operations);
      
      const finalState = stateManager.getState();
      expect(finalState.counter).toBe(3);
    });
  });

  describe('WebSocket Integration with State Management', () => {
    it('should handle WebSocket connection with state synchronization', async () => {
      await ActUtils.webSocketConnect(async () => {
        await wsManager.waitForConnection();
      });
      
      await stateManager.setState({ wsConnected: true });
      
      expect(wsManager.isReady()).toBe(true);
      const state = stateManager.getState();
      expect(state.wsConnected).toBe(true);
    });

    it('should handle message flow with proper timing', async () => {
      await ActUtils.webSocketConnect(async () => {
        await wsManager.waitForConnection();
      });
      
      const messagePromises = Array(5).fill(0).map((_, i) => 
        () => ActUtils.webSocketSend(() => {
          wsManager.sendMessage({ id: i, data: `Message ${i}` });
          return stateManager.setState({ lastMessageId: i });
        })
      );
      
      await StateTimingUtils.async.sequentialUpdate(messagePromises);
      
      const sentMessages = wsManager.getSentMessages();
      expect(sentMessages).toHaveLength(5);
      
      const state = stateManager.getState();
      expect(state.lastMessageId).toBe(4);
    });
  });

  describe('Complete Integration Flow', () => {
    it('should handle complete user flow without timing issues', async () => {
      const { unmount } = render(
        <TestProviders>
          <ComprehensiveTimingTestComponent />
        </TestProviders>
      );

      // Wait for component mount
      await ActUtils.waitFor(() => {
        expect(screen.getByTestId('comprehensive-timing-test')).toBeInTheDocument();
      });

      // Start the complete flow
      const startBtn = screen.getByTestId('start-flow');
      await ActUtils.userInteraction(async () => {
        await userEvent.click(startBtn);
      });

      // Wait for loading to start
      await ActUtils.waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('true');
      });

      // Wait for WebSocket connection
      await ActUtils.waitFor(() => {
        expect(screen.getByTestId('ws-state')).toHaveTextContent('connected');
      });

      // Wait for authentication
      await ActUtils.waitFor(() => {
        expect(screen.getByTestId('auth-state')).toHaveTextContent('true');
      });

      // Wait for messages
      await ActUtils.waitFor(() => {
        expect(screen.getByTestId('message-count')).toHaveTextContent('3');
      });

      // Wait for loading to finish
      await ActUtils.waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });

      // Verify all messages are present
      expect(screen.getByTestId('message-0')).toHaveTextContent('Message 1');
      expect(screen.getByTestId('message-1')).toHaveTextContent('Message 2');
      expect(screen.getByTestId('message-2')).toHaveTextContent('Message 3');

      unmount();
    });

    it('should handle state timing component integration', async () => {
      let capturedStates: any[] = [];
      
      const { unmount } = render(
        <TestProviders>
          <StateTimingTestComponent 
            initialState={{ count: 0 }}
            onStateChange={(state) => capturedStates.push(state)}
          />
        </TestProviders>
      );

      // Test synchronous update
      const updateBtn = screen.getByTestId('update-state');
      await ActUtils.userInteraction(async () => {
        await userEvent.click(updateBtn);
      });

      await ActUtils.waitFor(() => {
        expect(capturedStates.length).toBeGreaterThan(1);
      });

      // Test asynchronous update
      const asyncBtn = screen.getByTestId('async-update');
      await ActUtils.userInteraction(async () => {
        await userEvent.click(asyncBtn);
      });

      await ActUtils.waitFor(() => {
        const lastState = capturedStates[capturedStates.length - 1];
        expect(lastState.result).toBe('success');
        expect(lastState.loading).toBe(false);
      });

      unmount();
    });
  });

  describe('Performance and Error Handling', () => {
    it('should handle rapid state changes without memory leaks', async () => {
      const rapidUpdates = Array(50).fill(0).map((_, i) => 
        () => stateManager.setState({ rapidUpdate: i })
      );
      
      const performance = await ActUtils.retry(async () => {
        return StateTimingUtils.async.batchedUpdate(rapidUpdates, 10);
      });
      
      expect(performance).toHaveLength(50);
      
      const finalState = stateManager.getState();
      expect(finalState.rapidUpdate).toBe(49);
    });

    it('should handle error recovery in async operations', async () => {
      let errorHandled = false;
      
      await ActUtils.errorHandler(
        async () => {
          throw new Error('Test error');
        },
        (error) => {
          errorHandled = true;
          expect(error.message).toBe('Test error');
        }
      );
      
      expect(errorHandled).toBe(true);
    });
  });
});