/**
 * Comprehensive Optimistic UI Updates and Reconciliation Tests
 * 
 * Tests the complete optimistic update system including:
 * 1. Immediate UI updates on user actions
 * 2. Optimistic message lifecycle management
 * 3. Backend response reconciliation
 * 4. Streaming response handling
 * 5. Message status transitions
 * 6. UI state synchronization
 * 7. Performance and memory optimization
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { MessageList } from '@/components/chat/MessageList';
import { optimisticMessageManager } from '@/services/optimistic-updates';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { reconciliationService } from '@/services/reconciliation';
import type { ChatMessage } from '@/types/unified';

// Test component that visualizes optimistic updates
const OptimisticUpdateVisualizer: React.FC<{
  onOptimisticChange?: (messages: any[]) => void;
  onReconciliationChange?: (stats: any) => void;
}> = ({ onOptimisticChange, onReconciliationChange }) => {
  const [optimisticMessages, setOptimisticMessages] = React.useState<any[]>([]);
  const [reconciliationStats, setReconciliationStats] = React.useState<any>({});
  const [uiState, setUiState] = React.useState({
    isThinking: false,
    isPending: false,
    lastUpdate: null
  });

  // Subscribe to optimistic message manager
  React.useEffect(() => {
    const unsubscribe = optimisticMessageManager.subscribe((state) => {
      const messages = Array.from(state.messages.values());
      setOptimisticMessages(messages);
      onOptimisticChange?.(messages);

      // Update UI state based on optimistic messages
      setUiState({
        isThinking: !!state.pendingAiMessage && state.pendingAiMessage.status === 'processing',
        isPending: messages.some(m => m.status === 'pending'),
        lastUpdate: Date.now()
      });
    });

    return unsubscribe;
  }, [onOptimisticChange]);

  // Mock reconciliation service subscription
  React.useEffect(() => {
    const stats = {
      totalOptimistic: optimisticMessages.length,
      pendingCount: optimisticMessages.filter(m => m.status === 'pending').length,
      processingCount: optimisticMessages.filter(m => m.status === 'processing').length,
      confirmedCount: optimisticMessages.filter(m => m.status === 'confirmed').length,
      failedCount: optimisticMessages.filter(m => m.status === 'failed').length
    };
    setReconciliationStats(stats);
    onReconciliationChange?.(stats);
  }, [optimisticMessages, onReconciliationChange]);

  return (
    <div data-testid="optimistic-visualizer">
      <div data-testid="ui-state" data-state={JSON.stringify(uiState)} />
      <div data-testid="total-optimistic">{optimisticMessages.length}</div>
      <div data-testid="pending-count">{reconciliationStats.pendingCount || 0}</div>
      <div data-testid="processing-count">{reconciliationStats.processingCount || 0}</div>
      <div data-testid="confirmed-count">{reconciliationStats.confirmedCount || 0}</div>
      <div data-testid="failed-count">{reconciliationStats.failedCount || 0}</div>
      
      {/* Message status indicators */}
      {optimisticMessages.map((msg, index) => (
        <div 
          key={msg.localId} 
          data-testid={`message-${index}`}
          data-status={msg.status}
          data-role={msg.role}
          data-content={msg.content.substring(0, 50)}
        >
          [{msg.status}] {msg.role}: {msg.content}
        </div>
      ))}
      
      {/* Thinking indicator */}
      {uiState.isThinking && (
        <div data-testid="thinking-indicator">AI is thinking...</div>
      )}
    </div>
  );
};

// Test harness for comprehensive optimistic update testing
const OptimisticTestHarness: React.FC<{
  onStateChange?: (state: any) => void;
  simulateSlowBackend?: boolean;
  simulateStreamingResponse?: boolean;
}> = ({ onStateChange, simulateSlowBackend, simulateStreamingResponse }) => {
  const [backendMessages, setBackendMessages] = React.useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = React.useState('');

  // Mock backend response simulation
  const simulateBackendResponse = async (userMessage: string) => {
    if (simulateSlowBackend) {
      await new Promise(resolve => setTimeout(resolve, 2000));
    }

    const userBackendMsg: ChatMessage = {
      id: `backend-user-${Date.now()}`,
      content: userMessage,
      role: 'user',
      timestamp: Date.now()
    };

    const aiBackendMsg: ChatMessage = {
      id: `backend-ai-${Date.now()}`,
      content: simulateStreamingResponse ? '' : `I received: "${userMessage}"`,
      role: 'assistant',
      timestamp: Date.now() + 100
    };

    setBackendMessages(prev => [...prev, userBackendMsg, aiBackendMsg]);

    // Simulate streaming for AI response
    if (simulateStreamingResponse) {
      const fullResponse = `I received: "${userMessage}" and here's my detailed response.`;
      const words = fullResponse.split(' ');
      
      for (let i = 0; i < words.length; i++) {
        const partialContent = words.slice(0, i + 1).join(' ');
        setStreamingContent(partialContent);
        
        // Update the AI message content
        setBackendMessages(prev => 
          prev.map(msg => 
            msg.id === aiBackendMsg.id 
              ? { ...msg, content: partialContent }
              : msg
          )
        );
        
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
  };

  // Auto-reconcile with backend messages
  React.useEffect(() => {
    if (backendMessages.length > 0) {
      const result = optimisticMessageManager.reconcileWithBackend(backendMessages);
      onStateChange?.({ 
        reconciliationResult: result,
        backendMessages,
        totalMessages: backendMessages.length
      });
    }
  }, [backendMessages, onStateChange]);

  // Mock message sending that triggers backend simulation
  const handleMessageSent = React.useCallback((message: string) => {
    simulateBackendResponse(message);
  }, [simulateSlowBackend, simulateStreamingResponse]);

  return (
    <div data-testid="optimistic-test-harness">
      <OptimisticUpdateVisualizer />
      <div data-testid="backend-message-count">{backendMessages.length}</div>
      <div data-testid="streaming-content">{streamingContent}</div>
      {/* Hidden component to trigger message sending */}
      <div 
        data-testid="message-trigger"
        onClick={() => handleMessageSent('Test message')}
        style={{ display: 'none' }}
      />
    </div>
  );
};

// Mock dependencies
jest.mock('@/services/reconciliation');
jest.mock('@/store/unified-chat');

describe('Optimistic UI Updates and Reconciliation Pipeline Tests', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  const mockReconciliationService = {
    processConfirmation: jest.fn((msg) => msg),
    addOptimisticMessage: jest.fn((msg) => ({ ...msg, tempId: 'temp-123' })),
    getStats: jest.fn(() => ({ confirmed: 0, failed: 0, pending: 0 }))
  };

  const mockUnifiedChatStore = {
    subscribe: jest.fn(() => () => {}),
    getState: jest.fn(() => ({
      messages: [],
      optimisticMessages: new Map(),
      isProcessing: false
    })),
    addOptimisticMessage: jest.fn(),
    updateOptimisticMessage: jest.fn(),
    removeOptimisticMessage: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    
    (reconciliationService as jest.Mocked<typeof reconciliationService>) = mockReconciliationService as any;
    (useUnifiedChatStore as any) = Object.assign(jest.fn(() => mockUnifiedChatStore.getState()), mockUnifiedChatStore);
    
    // Clear optimistic manager state
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

  describe('Immediate Optimistic Updates', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should show user message immediately on send', async () => {
      render(<OptimisticTestHarness />);

      // Create optimistic user message
      const userMessage = optimisticMessageManager.addOptimisticUserMessage(
        'Hello, this should appear immediately!'
      );

      await waitFor(() => {
        expect(screen.getByTestId('total-optimistic')).toHaveTextContent('1');
        expect(screen.getByTestId('pending-count')).toHaveTextContent('1');
      });

      const messageElement = screen.getByTestId('message-0');
      expect(messageElement).toHaveAttribute('data-status', 'pending');
      expect(messageElement).toHaveAttribute('data-role', 'user');
      expect(messageElement).toHaveAttribute('data-content', 'Hello, this should appear immediately!');
    });

    it('should show AI thinking indicator immediately', async () => {
      render(<OptimisticTestHarness />);

      // Create optimistic AI message in processing state
      const aiMessage = optimisticMessageManager.addOptimisticAiMessage();

      await waitFor(() => {
        expect(screen.getByTestId('thinking-indicator')).toBeInTheDocument();
        expect(screen.getByTestId('processing-count')).toHaveTextContent('1');
      });

      const messageElement = screen.getByTestId('message-0');
      expect(messageElement).toHaveAttribute('data-status', 'processing');
      expect(messageElement).toHaveAttribute('data-role', 'assistant');
    });

    it('should update optimistic message content in real-time', async () => {
      render(<OptimisticTestHarness />);

      const aiMessage = optimisticMessageManager.addOptimisticAiMessage();

      // Simulate streaming content updates
      const contentUpdates = [
        'Hello',
        'Hello there',
        'Hello there! How',
        'Hello there! How can I help?'
      ];

      for (const content of contentUpdates) {
        optimisticMessageManager.updateOptimisticMessage(aiMessage.localId, { content });
        
        act(() => {
          jest.advanceTimersByTime(100);
        });

        await waitFor(() => {
          const messageElement = screen.getByTestId('message-0');
          expect(messageElement.textContent).toContain(content);
        });
      }
    });

    it('should handle rapid optimistic updates without flickering', async () => {
      render(<OptimisticTestHarness />);

      const messages = [];
      
      // Create multiple optimistic messages rapidly
      for (let i = 0; i < 10; i++) {
        const message = optimisticMessageManager.addOptimisticUserMessage(`Message ${i}`);
        messages.push(message);
        
        act(() => {
          jest.advanceTimersByTime(10);
        });
      }

      await waitFor(() => {
        expect(screen.getByTestId('total-optimistic')).toHaveTextContent('10');
      });

      // All messages should be visible
      for (let i = 0; i < 10; i++) {
        const messageElement = screen.getByTestId(`message-${i}`);
        expect(messageElement).toBeInTheDocument();
        expect(messageElement).toHaveAttribute('data-content', `Message ${i}`);
      }
    });
  });

  describe('Message Status Transitions', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should transition from pending to confirmed on backend success', async () => {
      const stateChanges: any[] = [];
      
      render(
        <OptimisticTestHarness 
          onStateChange={(state) => stateChanges.push(state)}
        />
      );

      const userMessage = optimisticMessageManager.addOptimisticUserMessage('Test message');

      // Initially pending
      await waitFor(() => {
        expect(screen.getByTestId('pending-count')).toHaveTextContent('1');
      });

      // Simulate backend confirmation
      const backendMessage: ChatMessage = {
        id: 'backend-123',
        content: 'Test message',
        role: 'user',
        timestamp: Date.now()
      };

      const reconciliationResult = optimisticMessageManager.reconcileWithBackend([backendMessage]);

      await waitFor(() => {
        expect(reconciliationResult.confirmed).toHaveLength(1);
        expect(screen.getByTestId('confirmed-count')).toHaveTextContent('1');
        expect(screen.getByTestId('pending-count')).toHaveTextContent('0');
      });

      const messageElement = screen.getByTestId('message-0');
      expect(messageElement).toHaveAttribute('data-status', 'confirmed');
    });

    it('should transition from pending to failed on timeout', async () => {
      render(<OptimisticTestHarness />);

      const userMessage = optimisticMessageManager.addOptimisticUserMessage('Timeout message');

      // Initially pending
      await waitFor(() => {
        expect(screen.getByTestId('pending-count')).toHaveTextContent('1');
      });

      // Fast-forward past timeout threshold
      act(() => {
        jest.advanceTimersByTime(35000);
      });

      // Reconcile with no backend response (timeout scenario)
      const reconciliationResult = optimisticMessageManager.reconcileWithBackend([]);

      await waitFor(() => {
        expect(reconciliationResult.failed).toHaveLength(1);
        expect(screen.getByTestId('failed-count')).toHaveTextContent('1');
        expect(screen.getByTestId('pending-count')).toHaveTextContent('0');
      });

      const messageElement = screen.getByTestId('message-0');
      expect(messageElement).toHaveAttribute('data-status', 'failed');
    });

    it('should transition from processing to confirmed for AI responses', async () => {
      render(<OptimisticTestHarness />);

      const aiMessage = optimisticMessageManager.addOptimisticAiMessage();

      // Initially processing
      await waitFor(() => {
        expect(screen.getByTestId('processing-count')).toHaveTextContent('1');
        expect(screen.getByTestId('thinking-indicator')).toBeInTheDocument();
      });

      // Update with content (simulating streaming)
      optimisticMessageManager.updateOptimisticMessage(aiMessage.localId, {
        content: 'AI response content'
      });

      // Simulate backend confirmation
      const backendAiMessage: ChatMessage = {
        id: 'backend-ai-456',
        content: 'AI response content',
        role: 'assistant',
        timestamp: Date.now()
      };

      optimisticMessageManager.reconcileWithBackend([backendAiMessage]);

      await waitFor(() => {
        expect(screen.getByTestId('confirmed-count')).toHaveTextContent('1');
        expect(screen.getByTestId('processing-count')).toHaveTextContent('0');
        expect(screen.queryByTestId('thinking-indicator')).not.toBeInTheDocument();
      });
    });

    it('should handle retrying status transitions', async () => {
      render(<OptimisticTestHarness />);

      const userMessage = optimisticMessageManager.addOptimisticUserMessage('Retry message');
      
      // Mark as failed
      optimisticMessageManager.updateOptimisticMessage(userMessage.localId, { 
        status: 'failed',
        retry: jest.fn().mockResolvedValue(undefined)
      });

      await waitFor(() => {
        expect(screen.getByTestId('failed-count')).toHaveTextContent('1');
      });

      // Mark as retrying
      optimisticMessageManager.updateOptimisticMessage(userMessage.localId, { 
        status: 'retrying' 
      });

      await waitFor(() => {
        const messageElement = screen.getByTestId('message-0');
        expect(messageElement).toHaveAttribute('data-status', 'retrying');
      });

      // Back to pending after retry
      optimisticMessageManager.updateOptimisticMessage(userMessage.localId, { 
        status: 'pending' 
      });

      await waitFor(() => {
        expect(screen.getByTestId('pending-count')).toHaveTextContent('1');
        expect(screen.getByTestId('failed-count')).toHaveTextContent('0');
      });
    });
  });

  describe('Backend Reconciliation', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should reconcile multiple messages correctly', async () => {
      const stateChanges: any[] = [];
      
      render(
        <OptimisticTestHarness 
          onStateChange={(state) => stateChanges.push(state)}
        />
      );

      // Create multiple optimistic messages
      const userMsg1 = optimisticMessageManager.addOptimisticUserMessage('First message');
      const aiMsg1 = optimisticMessageManager.addOptimisticAiMessage();
      const userMsg2 = optimisticMessageManager.addOptimisticUserMessage('Second message');
      const aiMsg2 = optimisticMessageManager.addOptimisticAiMessage();

      await waitFor(() => {
        expect(screen.getByTestId('total-optimistic')).toHaveTextContent('4');
      });

      // Simulate backend responses
      const backendMessages: ChatMessage[] = [
        {
          id: 'backend-user-1',
          content: 'First message',
          role: 'user',
          timestamp: Date.now()
        },
        {
          id: 'backend-ai-1',
          content: 'Response to first message',
          role: 'assistant',
          timestamp: Date.now() + 100
        },
        {
          id: 'backend-user-2',
          content: 'Second message',
          role: 'user',
          timestamp: Date.now() + 200
        },
        {
          id: 'backend-ai-2',
          content: 'Response to second message',
          role: 'assistant',
          timestamp: Date.now() + 300
        }
      ];

      // Update optimistic AI messages with content first
      optimisticMessageManager.updateOptimisticMessage(aiMsg1.localId, {
        content: 'Response to first message'
      });
      optimisticMessageManager.updateOptimisticMessage(aiMsg2.localId, {
        content: 'Response to second message'
      });

      const reconciliationResult = optimisticMessageManager.reconcileWithBackend(backendMessages);

      await waitFor(() => {
        expect(reconciliationResult.confirmed).toHaveLength(4);
        expect(reconciliationResult.failed).toHaveLength(0);
        expect(screen.getByTestId('confirmed-count')).toHaveTextContent('4');
      });
    });

    it('should handle partial reconciliation correctly', async () => {
      render(<OptimisticTestHarness />);

      const userMsg1 = optimisticMessageManager.addOptimisticUserMessage('Confirmed message');
      const userMsg2 = optimisticMessageManager.addOptimisticUserMessage('Missing message');

      // Backend only confirms first message
      const backendMessages: ChatMessage[] = [
        {
          id: 'backend-user-1',
          content: 'Confirmed message',
          role: 'user',
          timestamp: Date.now()
        }
      ];

      const reconciliationResult = optimisticMessageManager.reconcileWithBackend(backendMessages);

      expect(reconciliationResult.confirmed).toHaveLength(1);
      expect(reconciliationResult.failed).toHaveLength(0); // Second message not old enough to fail

      await waitFor(() => {
        expect(screen.getByTestId('confirmed-count')).toHaveTextContent('1');
        expect(screen.getByTestId('pending-count')).toHaveTextContent('1'); // Second still pending
      });
    });

    it('should handle conflicting reconciliation data', async () => {
      render(<OptimisticTestHarness />);

      const userMessage = optimisticMessageManager.addOptimisticUserMessage('Original content');

      // Backend returns modified content
      const backendMessages: ChatMessage[] = [
        {
          id: 'backend-modified',
          content: 'Modified content by backend',
          role: 'user',
          timestamp: Date.now()
        }
      ];

      const reconciliationResult = optimisticMessageManager.reconcileWithBackend(backendMessages);

      // Should reconcile but use backend content
      expect(reconciliationResult.confirmed).toHaveLength(1);
      expect(reconciliationResult.confirmed[0].content).toBe('Modified content by backend');

      await waitFor(() => {
        const messageElement = screen.getByTestId('message-0');
        expect(messageElement.textContent).toContain('Modified content by backend');
      });
    });
  });

  describe('Streaming Response Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle streaming AI responses with real-time updates', async () => {
      render(<OptimisticTestHarness simulateStreamingResponse={true} />);

      const aiMessage = optimisticMessageManager.addOptimisticAiMessage();

      // Simulate streaming response
      const streamChunks = [
        'I',
        'I am',
        'I am thinking',
        'I am thinking about',
        'I am thinking about your',
        'I am thinking about your question...'
      ];

      for (let i = 0; i < streamChunks.length; i++) {
        optimisticMessageManager.updateOptimisticMessage(aiMessage.localId, {
          content: streamChunks[i]
        });

        act(() => {
          jest.advanceTimersByTime(100);
        });

        await waitFor(() => {
          const messageElement = screen.getByTestId('message-0');
          expect(messageElement.textContent).toContain(streamChunks[i]);
        });
      }

      // Final reconciliation with complete response
      const finalBackendMessage: ChatMessage = {
        id: 'backend-ai-final',
        content: 'I am thinking about your question...',
        role: 'assistant',
        timestamp: Date.now()
      };

      optimisticMessageManager.reconcileWithBackend([finalBackendMessage]);

      await waitFor(() => {
        expect(screen.getByTestId('confirmed-count')).toHaveTextContent('1');
      });
    });

    it('should handle streaming interruption and recovery', async () => {
      render(<OptimisticTestHarness />);

      const aiMessage = optimisticMessageManager.addOptimisticAiMessage();

      // Start streaming
      optimisticMessageManager.updateOptimisticMessage(aiMessage.localId, {
        content: 'Starting to stream...'
      });

      // Simulate interruption (connection lost)
      optimisticMessageManager.updateOptimisticMessage(aiMessage.localId, {
        status: 'failed'
      });

      await waitFor(() => {
        expect(screen.getByTestId('failed-count')).toHaveTextContent('1');
      });

      // Recovery - retry and continue streaming
      optimisticMessageManager.updateOptimisticMessage(aiMessage.localId, {
        status: 'processing',
        content: 'Resuming stream after interruption...'
      });

      await waitFor(() => {
        expect(screen.getByTestId('processing-count')).toHaveTextContent('1');
        expect(screen.getByTestId('failed-count')).toHaveTextContent('0');
      });
    });

    it('should handle multiple concurrent streaming responses', async () => {
      render(<OptimisticTestHarness />);

      // Create multiple AI messages for concurrent streaming
      const aiMsg1 = optimisticMessageManager.addOptimisticAiMessage();
      const aiMsg2 = optimisticMessageManager.addOptimisticAiMessage();

      // Stream both responses simultaneously
      const stream1Content = ['Hello', 'Hello there', 'Hello there! First AI here.'];
      const stream2Content = ['Hi', 'Hi back', 'Hi back! Second AI responding.'];

      for (let i = 0; i < Math.max(stream1Content.length, stream2Content.length); i++) {
        if (i < stream1Content.length) {
          optimisticMessageManager.updateOptimisticMessage(aiMsg1.localId, {
            content: stream1Content[i]
          });
        }
        
        if (i < stream2Content.length) {
          optimisticMessageManager.updateOptimisticMessage(aiMsg2.localId, {
            content: stream2Content[i]
          });
        }

        act(() => {
          jest.advanceTimersByTime(50);
        });
      }

      await waitFor(() => {
        const msg1Element = screen.getByTestId('message-0');
        const msg2Element = screen.getByTestId('message-1');
        
        expect(msg1Element.textContent).toContain('Hello there! First AI here.');
        expect(msg2Element.textContent).toContain('Hi back! Second AI responding.');
      });
    });
  });

  describe('Performance and Memory Optimization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle large numbers of optimistic updates efficiently', async () => {
      render(<OptimisticTestHarness />);

      const startTime = performance.now();
      const messageCount = 1000;

      // Create many optimistic messages
      for (let i = 0; i < messageCount; i++) {
        optimisticMessageManager.addOptimisticUserMessage(`Message ${i}`);
        
        if (i % 100 === 0) {
          act(() => {
            jest.advanceTimersByTime(1);
          });
        }
      }

      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(1000); // Should complete quickly

      await waitFor(() => {
        expect(screen.getByTestId('total-optimistic')).toHaveTextContent(messageCount.toString());
      });
    });

    it('should cleanup confirmed messages to prevent memory leaks', async () => {
      render(<OptimisticTestHarness />);

      // Create many messages
      const messages = [];
      for (let i = 0; i < 100; i++) {
        const msg = optimisticMessageManager.addOptimisticUserMessage(`Message ${i}`);
        messages.push(msg);
      }

      await waitFor(() => {
        expect(screen.getByTestId('total-optimistic')).toHaveTextContent('100');
      });

      // Reconcile all messages as confirmed
      const backendMessages: ChatMessage[] = messages.map((msg, i) => ({
        id: `backend-${i}`,
        content: msg.content,
        role: msg.role,
        timestamp: Date.now() + i
      }));

      const reconciliationResult = optimisticMessageManager.reconcileWithBackend(backendMessages);
      
      expect(reconciliationResult.confirmed).toHaveLength(100);

      // Verify memory usage is reasonable
      const optimisticState = optimisticMessageManager.getState();
      expect(optimisticState.pendingUserMessage).toBeNull();
      expect(optimisticState.pendingAiMessage).toBeNull();
    });

    it('should throttle rapid UI updates to maintain performance', async () => {
      render(<OptimisticTestHarness />);

      const aiMessage = optimisticMessageManager.addOptimisticAiMessage();
      let updateCount = 0;

      // Rapidly update message content
      const rapidUpdates = setInterval(() => {
        updateCount++;
        optimisticMessageManager.updateOptimisticMessage(aiMessage.localId, {
          content: `Update ${updateCount}`
        });
        
        if (updateCount >= 100) {
          clearInterval(rapidUpdates);
        }
      }, 10);

      // Fast-forward through rapid updates
      act(() => {
        jest.advanceTimersByTime(1000);
        clearInterval(rapidUpdates);
      });

      // Should handle updates without performance degradation
      await waitFor(() => {
        const messageElement = screen.getByTestId('message-0');
        expect(messageElement.textContent).toContain('Update');
      });

      expect(updateCount).toBe(100);
    });
  });

  describe('UI State Synchronization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should synchronize UI state across components', async () => {
      const stateChanges: any[] = [];
      
      render(
        <OptimisticTestHarness 
          onStateChange={(state) => stateChanges.push(state)}
        />
      );

      // Create messages that affect UI state
      const userMessage = optimisticMessageManager.addOptimisticUserMessage('Test message');
      const aiMessage = optimisticMessageManager.addOptimisticAiMessage();

      // Check initial state
      await waitFor(() => {
        const uiStateElement = screen.getByTestId('ui-state');
        const uiState = JSON.parse(uiStateElement.getAttribute('data-state') || '{}');
        
        expect(uiState.isThinking).toBe(true); // AI message in processing state
        expect(uiState.isPending).toBe(true); // User message pending
      });

      // Update AI message to confirmed
      optimisticMessageManager.updateOptimisticMessage(aiMessage.localId, {
        content: 'AI response',
        status: 'confirmed'
      });

      // Reconcile user message
      const backendUserMessage: ChatMessage = {
        id: 'backend-user',
        content: 'Test message',
        role: 'user',
        timestamp: Date.now()
      };

      optimisticMessageManager.reconcileWithBackend([backendUserMessage]);

      // Check final state
      await waitFor(() => {
        const uiStateElement = screen.getByTestId('ui-state');
        const uiState = JSON.parse(uiStateElement.getAttribute('data-state') || '{}');
        
        expect(uiState.isThinking).toBe(false); // No more processing messages
        expect(uiState.isPending).toBe(false); // No more pending messages
      });
    });

    it('should maintain consistent state during rapid changes', async () => {
      render(<OptimisticTestHarness />);

      const messages = [];
      
      // Create and update messages rapidly
      for (let i = 0; i < 10; i++) {
        const userMsg = optimisticMessageManager.addOptimisticUserMessage(`Message ${i}`);
        const aiMsg = optimisticMessageManager.addOptimisticAiMessage();
        
        messages.push({ user: userMsg, ai: aiMsg });
        
        // Randomly update some messages
        if (i % 3 === 0) {
          optimisticMessageManager.updateOptimisticMessage(aiMsg.localId, {
            content: `AI response ${i}`
          });
        }
        
        act(() => {
          jest.advanceTimersByTime(50);
        });
      }

      // Verify final consistent state
      await waitFor(() => {
        expect(screen.getByTestId('total-optimistic')).toHaveTextContent('20');
        expect(screen.getByTestId('pending-count')).toHaveTextContent('10'); // User messages
        expect(screen.getByTestId('processing-count')).toHaveTextContent('10'); // AI messages
      });

      // State should be consistent across all components
      const optimisticState = optimisticMessageManager.getState();
      expect(optimisticState.messages.size).toBe(20);
    });
  });
});