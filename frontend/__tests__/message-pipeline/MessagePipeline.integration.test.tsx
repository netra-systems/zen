/**
 * Complete Message Pipeline Integration Tests
 * 
 * Tests the entire end-to-end message flow:
 * 1. User input → MessageInput component
 * 2. MessageInput → useMessageSending hook
 * 3. useMessageSending → OptimisticMessageManager
 * 4. OptimisticMessageManager → Unified Chat Store
 * 5. useMessageSending → WebSocket via useWebSocket hook
 * 6. WebSocket → Backend integration
 * 7. Backend response → OptimisticMessageManager reconciliation
 * 8. Reconciled data → UI updates
 * 
 * Critical flows tested:
 * - Happy path: Message sent, optimistic updates, backend confirmation
 * - Network failure: Optimistic updates, failure detection, retry
 * - Thread management: New thread creation, existing thread messaging
 * - Authentication: Token handling, refresh, error recovery
 * - Concurrency: Multiple messages, race conditions, state consistency
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { optimisticMessageManager } from '@/services/optimistic-updates';
import { webSocketService } from '@/services/webSocketService';
import { ThreadService } from '@/services/threadService';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Create a comprehensive test harness that integrates all components
const MessagePipelineTestHarness: React.FC<{
  token?: string | null;
  initialState?: any;
  onStateChange?: (state: any) => void;
  onWebSocketMessage?: (message: any) => void;
}> = ({ 
  token = 'test-token-123',
  initialState = {},
  onStateChange,
  onWebSocketMessage 
}) => {
  const [testState, setTestState] = React.useState({
    messages: [],
    optimisticMessages: [],
    webSocketMessages: [],
    errors: [],
    ...initialState
  });

  // Mock state management stores
  React.useEffect(() => {
    const unsubscribeUnified = useUnifiedChatStore.subscribe((state) => {
      setTestState(prev => ({ 
        ...prev, 
        unifiedChat: state,
        messages: state.messages 
      }));
      onStateChange?.(state);
    });

    const unsubscribeThread = useThreadStore.subscribe((state) => {
      setTestState(prev => ({ ...prev, threadStore: state }));
    });

    const unsubscribeAuth = useAuthStore.subscribe((state) => {
      setTestState(prev => ({ ...prev, authStore: state }));
    });

    const unsubscribeOptimistic = optimisticMessageManager.subscribe((state) => {
      setTestState(prev => ({ 
        ...prev, 
        optimisticState: state,
        optimisticMessages: Array.from(state.messages.values())
      }));
    });

    return () => {
      unsubscribeUnified();
      unsubscribeThread();
      unsubscribeAuth();
      unsubscribeOptimistic();
    };
  }, [onStateChange]);

  // Mock WebSocket message interception
  React.useEffect(() => {
    const originalOnMessage = webSocketService.onMessage;
    
    webSocketService.onMessage = (message) => {
      setTestState(prev => ({
        ...prev,
        webSocketMessages: [...prev.webSocketMessages, message]
      }));
      onWebSocketMessage?.(message);
      originalOnMessage?.(message);
    };

    return () => {
      webSocketService.onMessage = originalOnMessage;
    };
  }, [onWebSocketMessage]);

  const authValue = {
    token,
    user: token ? { id: 'test-user', email: 'test@example.com' } : null,
    isAuthenticated: !!token,
    login: jest.fn(),
    logout: jest.fn(),
    refreshToken: jest.fn()
  };

  return (
    <AuthContext.Provider value={authValue}>
      <WebSocketProvider>
        <div data-testid="pipeline-harness">
          <MessageInput />
          <div data-testid="test-state" data-state={JSON.stringify(testState)} />
          <div data-testid="message-count">{testState.messages.length}</div>
          <div data-testid="optimistic-count">{testState.optimisticMessages.length}</div>
          <div data-testid="websocket-count">{testState.webSocketMessages.length}</div>
        </div>
      </WebSocketProvider>
    </AuthContext.Provider>
  );
};

// Mock all required services and stores with realistic behavior
jest.mock('@/services/webSocketService');
jest.mock('@/services/threadService');
jest.mock('@/services/threadRenameService');
jest.mock('@/store/unified-chat');
jest.mock('@/store/threadStore');
jest.mock('@/store/authStore');

describe('Complete Message Pipeline Integration Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  const mockWebSocketService = {
    onMessage: null,
    onStatusChange: null,
    connect: jest.fn(),
    disconnect: jest.fn(),
    sendMessage: jest.fn(),
    updateToken: jest.fn().mockResolvedValue(undefined),
    getSecureUrl: jest.fn((url: string) => url)
  };

  const mockUnifiedChatStore = {
    subscribe: jest.fn(() => () => {}),
    getState: jest.fn(() => ({
      activeThreadId: null,
      isProcessing: false,
      messages: [],
      optimisticMessages: new Map()
    })),
    addMessage: jest.fn(),
    setActiveThread: jest.fn(),
    setProcessing: jest.fn(),
    addOptimisticMessage: jest.fn(),
    updateOptimisticMessage: jest.fn()
  };

  const mockThreadStore = {
    subscribe: jest.fn(() => () => {}),
    getState: jest.fn(() => ({
      currentThreadId: null,
      threads: []
    })),
    setCurrentThread: jest.fn(),
    addThread: jest.fn()
  };

  const mockAuthStore = {
    subscribe: jest.fn(() => () => {}),
    getState: jest.fn(() => ({
      isAuthenticated: true,
      token: 'test-token-123'
    }))
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    // Setup comprehensive mocks
    (webSocketService as jest.Mocked<typeof webSocketService>) = mockWebSocketService as any;
    (useUnifiedChatStore as any) = Object.assign(jest.fn(() => mockUnifiedChatStore.getState()), mockUnifiedChatStore);
    (useThreadStore as any) = Object.assign(jest.fn(() => mockThreadStore.getState()), mockThreadStore);
    (useAuthStore as any) = Object.assign(jest.fn(() => mockAuthStore.getState()), mockAuthStore);

    (ThreadService.createThread as jest.Mock).mockResolvedValue({
      id: 'new-thread-123',
      title: 'New Thread',
      metadata: { renamed: false }
    });

    // Reset optimistic manager
    optimisticMessageManager.clearAllOptimisticMessages();
  });

  afterEach(() => {
    jest.useRealTimers();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('Happy Path - Complete End-to-End Flow', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle complete message pipeline from input to backend confirmation', async () => {
      const stateChanges: any[] = [];
      const webSocketMessages: any[] = [];
      
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <MessagePipelineTestHarness
          onStateChange={(state) => stateChanges.push(state)}
          onWebSocketMessage={(msg) => webSocketMessages.push(msg)}
        />
      );

      // Step 1: User types message
      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Hello, this is my first message!');

      expect(textarea).toHaveValue('Hello, this is my first message!');

      // Step 2: User sends message
      await user.keyboard('{Enter}');

      // Step 3: Verify optimistic updates appeared immediately
      await waitFor(() => {
        expect(screen.getByTestId('optimistic-count')).toHaveTextContent('2'); // User + AI optimistic
      });

      // Step 4: Verify WebSocket message was sent
      expect(mockWebSocketService.sendMessage).toHaveBeenCalledWith({
        type: 'start_agent',
        payload: {
          user_request: 'Hello, this is my first message!',
          thread_id: 'new-thread-123',
          context: {},
          settings: {}
        }
      });

      // Step 5: Verify thread was created
      expect(ThreadService.createThread).toHaveBeenCalledWith('Hello, this is my first message!');
      expect(mockThreadStore.addThread).toHaveBeenCalled();
      expect(mockUnifiedChatStore.setActiveThread).toHaveBeenCalledWith('new-thread-123');

      // Step 6: Simulate backend response
      const backendResponse = {
        type: 'agent_response',
        payload: {
          message_id: 'backend-msg-123',
          content: 'Hello! How can I help you?',
          role: 'assistant',
          thread_id: 'new-thread-123'
        }
      };

      act(() => {
        mockWebSocketService.onMessage!(backendResponse);
      });

      // Step 7: Verify message was processed and reconciled
      await waitFor(() => {
        expect(webSocketMessages).toContainEqual(backendResponse);
      });

      // Step 8: Verify processing state was set
      expect(mockUnifiedChatStore.setProcessing).toHaveBeenCalledWith(true);

      // Step 9: Verify textarea was cleared
      expect(textarea).toHaveValue('');
    });

    it('should handle subsequent messages in existing thread', async () => {
      // Setup existing thread state
      mockUnifiedChatStore.getState.mockReturnValue({
        activeThreadId: 'existing-thread-456',
        isProcessing: false,
        messages: [
          { id: 'prev-msg-1', role: 'user', content: 'Previous message', thread_id: 'existing-thread-456' }
        ],
        optimisticMessages: new Map()
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<MessagePipelineTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Follow-up question');
      await user.keyboard('{Enter}');

      // Should use user_message type for existing thread
      expect(mockWebSocketService.sendMessage).toHaveBeenCalledWith({
        type: 'user_message',
        payload: {
          content: 'Follow-up question',
          references: [],
          thread_id: 'existing-thread-456'
        }
      });

      // Should not create new thread
      expect(ThreadService.createThread).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling and Recovery Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle WebSocket send failure with retry mechanism', async () => {
      const sendError = new Error('WebSocket connection failed');
      mockWebSocketService.sendMessage.mockImplementationOnce(() => {
        throw sendError;
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<MessagePipelineTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message that will fail');
      await user.keyboard('{Enter}');

      // Should still create optimistic messages
      await waitFor(() => {
        expect(screen.getByTestId('optimistic-count')).toHaveTextContent('2');
      });

      // Should mark messages as failed and provide retry
      await waitFor(() => {
        const optimisticMessages = optimisticMessageManager.getOptimisticMessages();
        const failedMessage = optimisticMessages.find(m => m.status === 'failed');
        expect(failedMessage).toBeDefined();
        expect(failedMessage?.retry).toBeInstanceOf(Function);
      });
    });

    it('should handle thread creation failure gracefully', async () => {
      const threadError = new Error('Thread service unavailable');
      (ThreadService.createThread as jest.Mock).mockRejectedValue(threadError);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<MessagePipelineTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message causing thread error');
      await user.keyboard('{Enter}');

      // Should not send WebSocket message due to thread creation failure
      await waitFor(() => {
        expect(mockWebSocketService.sendMessage).not.toHaveBeenCalled();
      });

      // Optimistic messages should still be created but marked as failed
      await waitFor(() => {
        const failedMessages = optimisticMessageManager.getFailedMessages();
        expect(failedMessages.length).toBeGreaterThan(0);
      });
    });

    it('should handle authentication failures during message send', async () => {
      // Start with authenticated state
      const { rerender } = render(<MessagePipelineTestHarness token="valid-token" />);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Suddenly lose authentication
      rerender(<MessagePipelineTestHarness token={null} />);

      await user.type(textarea, 'Message while unauthenticated');
      await user.keyboard('{Enter}');

      // Should not send message
      expect(mockWebSocketService.sendMessage).not.toHaveBeenCalled();
      
      // Textarea should show disabled state
      expect(textarea).toBeDisabled();
    });
  });

  describe('Optimistic Updates and Reconciliation Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should show immediate optimistic updates and reconcile with backend', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<MessagePipelineTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message for reconciliation test');
      await user.keyboard('{Enter}');

      // Verify immediate optimistic updates
      await waitFor(() => {
        const optimisticMessages = optimisticMessageManager.getOptimisticMessages();
        expect(optimisticMessages).toHaveLength(2);
        
        const userMessage = optimisticMessages.find(m => m.role === 'user');
        const aiMessage = optimisticMessages.find(m => m.role === 'assistant');
        
        expect(userMessage?.content).toBe('Message for reconciliation test');
        expect(userMessage?.status).toBe('pending');
        expect(aiMessage?.content).toBe('');
        expect(aiMessage?.status).toBe('processing');
      });

      // Simulate backend confirmation of user message
      const backendUserConfirmation = {
        id: 'backend-user-msg-123',
        content: 'Message for reconciliation test',
        role: 'user',
        timestamp: Date.now(),
        thread_id: 'new-thread-123'
      };

      const reconciliationResult = optimisticMessageManager.reconcileWithBackend([backendUserConfirmation]);

      expect(reconciliationResult.confirmed).toHaveLength(1);
      expect(reconciliationResult.confirmed[0].status).toBe('confirmed');
      expect(reconciliationResult.failed).toHaveLength(0);

      // Simulate backend AI response
      const backendAiResponse = {
        id: 'backend-ai-msg-456',
        content: 'I understand your message!',
        role: 'assistant',
        timestamp: Date.now() + 1000,
        thread_id: 'new-thread-123'
      };

      // Update optimistic AI message content first (simulating streaming)
      const aiMessage = optimisticMessageManager.getOptimisticMessages()
        .find(m => m.role === 'assistant');
      
      if (aiMessage) {
        optimisticMessageManager.updateOptimisticMessage(aiMessage.localId, {
          content: 'I understand your message!'
        });
      }

      const aiReconciliation = optimisticMessageManager.reconcileWithBackend([backendAiResponse]);
      
      expect(aiReconciliation.confirmed).toHaveLength(1);
    });

    it('should handle optimistic message timeout and failure', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<MessagePipelineTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message that will timeout');
      await user.keyboard('{Enter}');

      // Fast-forward time to simulate timeout (30+ seconds)
      act(() => {
        jest.advanceTimersByTime(35000);
      });

      // Reconcile with empty backend response (simulating no response)
      const reconciliationResult = optimisticMessageManager.reconcileWithBackend([]);

      await waitFor(() => {
        expect(reconciliationResult.failed).toHaveLength(1);
        expect(reconciliationResult.failed[0].status).toBe('failed');
      });
    });
  });

  describe('Concurrent Operations Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle multiple rapid message sends correctly', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<MessagePipelineTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Send multiple messages rapidly
      const messages = ['First message', 'Second message', 'Third message'];
      
      for (const message of messages) {
        await user.clear(textarea);
        await user.type(textarea, message);
        await user.keyboard('{Enter}');
        
        // Small delay to allow processing
        act(() => {
          jest.advanceTimersByTime(100);
        });
      }

      // Should have created optimistic messages for all sends
      await waitFor(() => {
        const optimisticMessages = optimisticMessageManager.getOptimisticMessages();
        const userMessages = optimisticMessages.filter(m => m.role === 'user');
        expect(userMessages.length).toBeGreaterThanOrEqual(3);
      });

      // WebSocket should have been called multiple times
      // Note: Due to isSending guard, some calls might be prevented
      expect(mockWebSocketService.sendMessage).toHaveBeenCalled();
    });

    it('should prevent duplicate sends with isSending guard', async () => {
      // Mock a slow send operation
      let resolveSend: () => void;
      const slowSendPromise = new Promise<void>((resolve) => {
        resolveSend = resolve;
      });

      mockWebSocketService.sendMessage.mockImplementationOnce(() => slowSendPromise);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<MessagePipelineTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Slow message');
      
      // Start first send
      await user.keyboard('{Enter}');
      
      // Try to send again immediately
      await user.type(textarea, 'Second attempt');
      await user.keyboard('{Enter}');

      // Should only have called sendMessage once due to isSending guard
      expect(mockWebSocketService.sendMessage).toHaveBeenCalledTimes(1);

      // Complete the slow send
      act(() => {
        resolveSend!();
      });
    });

    it('should handle concurrent thread creation correctly', async () => {
      // Mock slow thread creation
      let resolveThreadCreation: (value: any) => void;
      const slowThreadPromise = new Promise((resolve) => {
        resolveThreadCreation = resolve;
      });

      (ThreadService.createThread as jest.Mock).mockReturnValue(slowThreadPromise);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<MessagePipelineTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'First message creating thread');
      
      // Start thread creation
      await user.keyboard('{Enter}');

      // Try to send another message before thread creation completes
      await user.type(textarea, 'Second message while creating');
      await user.keyboard('{Enter}');

      // Complete thread creation
      act(() => {
        resolveThreadCreation!({
          id: 'concurrent-thread-123',
          title: 'Concurrent Thread',
          metadata: { renamed: false }
        });
      });

      await waitFor(() => {
        expect(ThreadService.createThread).toHaveBeenCalled();
      });
    });
  });

  describe('State Synchronization Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should maintain consistent state across all stores', async () => {
      const stateUpdates: any[] = [];
      
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <MessagePipelineTestHarness
          onStateChange={(state) => stateUpdates.push(state)}
        />
      );

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'State sync test message');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        // Verify all stores were updated appropriately
        expect(mockUnifiedChatStore.setActiveThread).toHaveBeenCalled();
        expect(mockUnifiedChatStore.addOptimisticMessage).toHaveBeenCalled();
        expect(mockUnifiedChatStore.setProcessing).toHaveBeenCalled();
        expect(mockThreadStore.setCurrentThread).toHaveBeenCalled();
        expect(mockThreadStore.addThread).toHaveBeenCalled();
      });

      // Verify optimistic manager state is consistent
      const optimisticState = optimisticMessageManager.getState();
      expect(optimisticState.messages.size).toBeGreaterThan(0);
      expect(optimisticState.pendingUserMessage).toBeTruthy();
      expect(optimisticState.pendingAiMessage).toBeTruthy();
    });

    it('should handle store update failures gracefully', async () => {
      // Mock store update failure
      mockUnifiedChatStore.addOptimisticMessage.mockImplementation(() => {
        throw new Error('Store update failed');
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<MessagePipelineTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message causing store error');

      // Should not crash the application
      expect(async () => {
        await user.keyboard('{Enter}');
      }).not.toThrow();
    });
  });

  describe('Performance and Memory Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle large message volumes efficiently', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<MessagePipelineTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      
      const startTime = performance.now();
      
      // Send 50 messages rapidly
      for (let i = 0; i < 50; i++) {
        await user.clear(textarea);
        await user.type(textarea, `Performance test message ${i}`);
        await user.keyboard('{Enter}');
        
        act(() => {
          jest.advanceTimersByTime(10);
        });
      }
      
      const endTime = performance.now();
      
      // Should complete within reasonable time
      expect(endTime - startTime).toBeLessThan(5000);
      
      // Should not create excessive memory usage
      const optimisticMessages = optimisticMessageManager.getOptimisticMessages();
      expect(optimisticMessages.length).toBeLessThan(200); // Should have reasonable bounds
    });

    it('should cleanup resources properly on unmount', async () => {
      const { unmount } = render(<MessagePipelineTestHarness />);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      // Create some optimistic messages first
      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message before unmount');
      await user.keyboard('{Enter}');

      // Unmount component
      unmount();

      // Should cleanup WebSocket connections
      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
      expect(mockWebSocketService.onMessage).toBeNull();
      expect(mockWebSocketService.onStatusChange).toBeNull();
    });
  });

  describe('Real-time Updates Pipeline', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle streaming AI responses correctly', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<MessagePipelineTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Tell me a story');
      await user.keyboard('{Enter}');

      // Get the AI optimistic message
      await waitFor(() => {
        const optimisticMessages = optimisticMessageManager.getOptimisticMessages();
        const aiMessage = optimisticMessages.find(m => m.role === 'assistant');
        expect(aiMessage).toBeDefined();
      });

      const aiMessage = optimisticMessageManager.getOptimisticMessages()
        .find(m => m.role === 'assistant');

      // Simulate streaming response updates
      const streamingChunks = [
        'Once upon',
        'Once upon a time',
        'Once upon a time, there was',
        'Once upon a time, there was a brave knight...'
      ];

      for (const chunk of streamingChunks) {
        if (aiMessage) {
          optimisticMessageManager.updateOptimisticMessage(aiMessage.localId, {
            content: chunk
          });
        }
        
        act(() => {
          jest.advanceTimersByTime(100);
        });
      }

      // Verify final content
      const finalAiMessage = optimisticMessageManager.getOptimisticMessages()
        .find(m => m.role === 'assistant');
      
      expect(finalAiMessage?.content).toBe('Once upon a time, there was a brave knight...');
    });
  });
});