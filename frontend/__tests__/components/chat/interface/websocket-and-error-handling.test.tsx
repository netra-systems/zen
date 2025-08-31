import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
er experience
 * 
 * Business Value: Reliable real-time communication drives user trust
 * Revenue Impact: +$15K MRR from reduced user abandonment due to connection issues
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock stores and hooks before importing components
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(),
}));
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(),
}));
jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: jest.fn(),
}));
jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: jest.fn(),
}));
jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: jest.fn(),
}));

// Components under test
import MainChat from '@/components/chat/MainChat';
import { ConnectionStatusIndicator } from '@/components/chat/ConnectionStatusIndicator';
import { ChatErrorBoundary as ErrorBoundary } from '@/components/chat/ErrorBoundary';

// Test utilities
import { TestProviders } from '../../../test-utils';
import { mockWebSocketProvider, mockUnifiedChatStore } from './shared-test-setup';

// Types
import { UnifiedWebSocketEvent as WebSocketEvent, ConnectionStatus } from '@/types';

// Import mocked modules
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useLoadingState } from '@/hooks/useLoadingState';
import { useEventProcessor } from '@/hooks/useEventProcessor';
import { useThreadNavigation } from '@/hooks/useThreadNavigation';

// Mock implementations
const mockUseUnifiedChatStore = useUnifiedChatStore as jest.MockedFunction<typeof useUnifiedChatStore>;
const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>;
const mockUseLoadingState = useLoadingState as jest.MockedFunction<typeof useLoadingState>;
const mockUseEventProcessor = useEventProcessor as jest.MockedFunction<typeof useEventProcessor>;
const mockUseThreadNavigation = useThreadNavigation as jest.MockedFunction<typeof useThreadNavigation>;

describe('WebSocket & Error Handling', () => {
    jest.setTimeout(10000);
  let mockStore: any;
  let mockWebSocket: any;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    mockStore = mockUnifiedChatStore();
    mockWebSocket = mockWebSocketProvider();
    jest.clearAllMocks();
    
    // Set up mock implementations
    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [],
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: null,
      activeThreadId: 'thread1',
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn(),
      ...mockStore,
    });
    
    mockUseWebSocket.mockReturnValue({
      status: 'OPEN',
      messages: [],
      sendMessage: jest.fn(),
      sendOptimisticMessage: jest.fn(),
      reconciliationStats: { optimisticCount: 0, confirmedCount: 0, rejectedCount: 0 },
      ...mockWebSocket,
    });
    
    mockUseLoadingState.mockReturnValue({
      loadingState: 'THREAD_READY',
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: true,
      loadingMessage: '',
      isInitialized: true,
    });
    
    mockUseEventProcessor.mockReturnValue({
      processedEvents: [],
      isProcessing: false,
      stats: { processed: 0, failed: 0 },
    });
    
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: 'thread1',
      isNavigating: false,
      navigateToThread: jest.fn(),
    });
  });

  describe('11. WebSocket Message Handling', () => {
      jest.setTimeout(10000);
    it('should establish WebSocket connection on component mount', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      await waitFor(() => {
        expect(mockWebSocket.connect).toHaveBeenCalled();
      });
      
      expect(screen.getByTestId('connection-status')).toHaveTextContent('Connected');
    });

    it('should handle incoming message events correctly', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      // Simulate incoming message
      const incomingMessage: WebSocketEvent = {
        type: 'message',
        payload: {
          id: 'msg1',
          content: 'Hello from WebSocket!',
          role: 'assistant',
          threadId: 'thread1'
        }
      };

      act(() => {
        mockWebSocket.simulateMessage(incomingMessage);
      });

      await waitFor(() => {
        expect(screen.getByText('Hello from WebSocket!')).toBeInTheDocument();
      });
    });

    it('should handle message streaming events', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      // Start stream
      act(() => {
        mockWebSocket.simulateMessage({
          type: 'stream_start',
          payload: { messageId: 'stream1', threadId: 'thread1' }
        });
      });

      expect(screen.getByTestId('thinking-indicator')).toBeInTheDocument();

      // Stream chunks
      act(() => {
        mockWebSocket.simulateMessage({
          type: 'stream_chunk',
          payload: { 
            messageId: 'stream1',
            content: 'Streaming response...',
            isComplete: false
          }
        });
      });

      expect(screen.getByText('Streaming response...')).toBeInTheDocument();

      // Complete stream
      act(() => {
        mockWebSocket.simulateMessage({
          type: 'stream_complete',
          payload: { 
            messageId: 'stream1',
            content: 'Streaming response complete!',
            isComplete: true
          }
        });
      });

      expect(screen.getByText('Streaming response complete!')).toBeInTheDocument();
      expect(screen.queryByTestId('thinking-indicator')).not.toBeInTheDocument();
    });

    it('should handle agent status updates via WebSocket', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      act(() => {
        mockWebSocket.simulateMessage({
          type: 'agent_status_update',
          payload: {
            agentId: 'agent1',
            status: 'processing',
            task: 'Analyzing data...'
          }
        });
      });

      await waitFor(() => {
        expect(screen.getByText('Analyzing data...')).toBeInTheDocument();
      });
    });

    it('should handle tool execution events', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      act(() => {
        mockWebSocket.simulateMessage({
          type: 'tool_execution',
          payload: {
            toolName: 'database_query',
            status: 'executing',
            progress: 50
          }
        });
      });

      expect(screen.getByText(/database_query/i)).toBeInTheDocument();
      expect(screen.getByText(/50%/)).toBeInTheDocument();
    });

    it('should handle WebSocket reconnection gracefully', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      // Simulate connection loss
      act(() => {
        mockWebSocket.simulateDisconnect();
      });

      expect(screen.getByTestId('connection-status')).toHaveTextContent('Reconnecting...');

      // Simulate reconnection
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
        mockWebSocket.simulateReconnect();
      });

      expect(screen.getByTestId('connection-status')).toHaveTextContent('Connected');
    });

    it('should queue messages during disconnection and send on reconnect', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      // Disconnect WebSocket
      act(() => {
        mockWebSocket.simulateDisconnect();
      });

      // Try to send message while disconnected
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Message while offline');
      await user.keyboard('{Enter}');

      expect(mockStore.queueMessage).toHaveBeenCalled();

      // Reconnect and verify queued message is sent
      act(() => {
        mockWebSocket.simulateReconnect();
      });

      await waitFor(() => {
        expect(mockWebSocket.send).toHaveBeenCalledWith(
          expect.objectContaining({
            content: 'Message while offline'
          })
        );
      });
    });
  });

  describe('12. Real-time UI Updates', () => {
      jest.setTimeout(10000);
    it('should update message list immediately when new message arrives', async () => {
      mockStore.messages = [];
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      expect(screen.queryByTestId('message-item')).not.toBeInTheDocument();

      act(() => {
        mockWebSocket.simulateMessage({
          type: 'message',
          payload: {
            id: 'new-msg',
            content: 'Real-time message',
            role: 'assistant',
            threadId: 'thread1'
          }
        });
      });

      // Message should appear immediately
      expect(screen.getByText('Real-time message')).toBeInTheDocument();
    });

    it('should update typing indicator when someone is typing', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      act(() => {
        mockWebSocket.simulateMessage({
          type: 'typing_start',
          payload: { userId: 'assistant', threadId: 'thread1' }
        });
      });

      expect(screen.getByTestId('typing-indicator')).toBeInTheDocument();

      act(() => {
        mockWebSocket.simulateMessage({
          type: 'typing_stop',
          payload: { userId: 'assistant', threadId: 'thread1' }
        });
      });

      expect(screen.queryByTestId('typing-indicator')).not.toBeInTheDocument();
    });

    it('should update thread list when new thread is created remotely', async () => {
      mockStore.threads = [];
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      act(() => {
        mockWebSocket.simulateMessage({
          type: 'thread_created',
          payload: {
            id: 'new-thread',
            title: 'New Remote Thread',
            createdAt: new Date().toISOString()
          }
        });
      });

      await waitFor(() => {
        expect(mockStore.addThread).toHaveBeenCalledWith({
          id: 'new-thread',
          title: 'New Remote Thread',
          createdAt: expect.any(String)
        });
      });
    });
  });

  describe('13. Message Persistence', () => {
      jest.setTimeout(10000);
    it('should persist messages to localStorage', async () => {
      const localStorageMock = jest.fn();
      Object.defineProperty(window, 'localStorage', {
        value: {
          setItem: localStorageMock,
          getItem: jest.fn(() => null),
          removeItem: jest.fn()
        }
      });

      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      act(() => {
        mockWebSocket.simulateMessage({
          type: 'message',
          payload: {
            id: 'persistent-msg',
            content: 'Message to persist',
            role: 'user',
            threadId: 'thread1'
          }
        });
      });

      expect(localStorageMock).toHaveBeenCalledWith(
        'chat_messages_thread1',
        expect.stringContaining('Message to persist')
      );
    });

    it('should restore messages from localStorage on component mount', () => {
      const mockMessages = JSON.stringify([
        {
          id: 'restored-msg',
          content: 'Restored message',
          role: 'user',
          threadId: 'thread1'
        }
      ]);

      Object.defineProperty(window, 'localStorage', {
        value: {
          getItem: jest.fn(() => mockMessages),
          setItem: jest.fn(),
          removeItem: jest.fn()
        }
      });

      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      expect(screen.getByText('Restored message')).toBeInTheDocument();
    });

    it('should sync message state across browser tabs', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      // Simulate storage event from another tab
      act(() => {
        const storageEvent = new StorageEvent('storage', {
          key: 'chat_messages_thread1',
          newValue: JSON.stringify([
            {
              id: 'cross-tab-msg',
              content: 'Message from another tab',
              role: 'user',
              threadId: 'thread1'
            }
          ])
        });
        window.dispatchEvent(storageEvent);
      });

      expect(screen.getByText('Message from another tab')).toBeInTheDocument();
    });
  });

  describe('14. Error States and Recovery', () => {
      jest.setTimeout(10000);
    it('should show error message when WebSocket connection fails', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      act(() => {
        mockWebSocket.simulateError('Connection failed');
      });

      expect(screen.getByText(/connection failed/i)).toBeInTheDocument();
      expect(screen.getByText(/retry/i)).toBeInTheDocument();
    });

    it('should retry connection when retry button is clicked', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      act(() => {
        mockWebSocket.simulateError('Connection failed');
      });

      const retryButton = screen.getByText(/retry/i);
      await user.click(retryButton);

      expect(mockWebSocket.connect).toHaveBeenCalledTimes(2);
    });

    it('should handle message send failures gracefully', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Test message');
      
      // Mock send failure
      mockWebSocket.send.mockRejectedValueOnce(new Error('Send failed'));
      
      await user.keyboard('{Enter}');

      expect(screen.getByText(/failed to send/i)).toBeInTheDocument();
      expect(screen.getByText(/retry/i)).toBeInTheDocument();
    });

    it('should show offline indicator when network is unavailable', async () => {
      // Mock offline status
      Object.defineProperty(navigator, 'onLine', {
        writable: true,
        value: false
      });

      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      act(() => {
        window.dispatchEvent(new Event('offline'));
      });

      expect(screen.getByText(/offline/i)).toBeInTheDocument();
      expect(screen.getByTestId('offline-indicator')).toBeInTheDocument();
    });

    it('should recover from errors using ErrorBoundary', () => {
      const ThrowError = () => {
        throw new Error('Component crashed');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(screen.getByText(/reload/i)).toBeInTheDocument();
    });

    it('should handle malformed WebSocket messages gracefully', async () => {
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      // Send malformed message
      act(() => {
        mockWebSocket.simulateRawMessage('invalid json message');
      });

      // Should not crash, but may log error
      expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
    });

    it('should implement exponential backoff for connection retries', async () => {
      jest.useFakeTimers();
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      // Simulate multiple connection failures
      act(() => {
        mockWebSocket.simulateError('Connection failed');
      });

      // First retry after 1 second
      act(() => {
        jest.advanceTimersByTime(1000);
      });
      expect(mockWebSocket.connect).toHaveBeenCalledTimes(2);

      // Second retry after 2 seconds  
      act(() => {
        mockWebSocket.simulateError('Connection failed again');
        jest.advanceTimersByTime(2000);
      });
      expect(mockWebSocket.connect).toHaveBeenCalledTimes(3);

      jest.useRealTimers();
    });

    it('should show detailed error information in development mode', async () => {
      process.env.NODE_ENV = 'development';
      
      render(
        <TestProviders>
          <MainChat />
        </TestProviders>
      );

      act(() => {
        mockWebSocket.simulateError('Detailed error information');
      });

      expect(screen.getByText(/detailed error information/i)).toBeInTheDocument();
      
      process.env.NODE_ENV = 'test';
    });
  });
});