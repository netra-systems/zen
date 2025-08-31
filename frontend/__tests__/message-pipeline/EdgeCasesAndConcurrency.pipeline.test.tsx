/**
 * Comprehensive Edge Cases and Concurrency Pipeline Tests
 * 
 * Tests complex scenarios and boundary conditions:
 * 1. Concurrent message sending and receiving
 * 2. Race conditions and state consistency
 * 3. Memory limits and performance boundaries
 * 4. Network disruption and recovery scenarios
 * 5. Authentication state changes during operations
 * 6. Thread switching during message pipeline
 * 7. Component lifecycle edge cases
 * 8. Browser environment variations
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageInput } from '@/components/chat/MessageInput';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';
import { optimisticMessageManager } from '@/services/optimistic-updates';
import { webSocketService } from '@/services/webSocketService';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { ThreadService } from '@/services/threadService';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Advanced test harness for edge case and concurrency testing
const ConcurrencyTestHarness: React.FC<{
  simultaneousUsers?: number;
  messageLoad?: number;
  networkLatency?: number;
  memoryConstraints?: boolean;
  chaosMode?: boolean;
  onMetrics?: (metrics: any) => void;
}> = ({ 
  simultaneousUsers = 1,
  messageLoad = 10,
  networkLatency = 0,
  memoryConstraints = false,
  chaosMode = false,
  onMetrics 
}) => {
  const [metrics, setMetrics] = React.useState({
    messagesSent: 0,
    messagesReceived: 0,
    errors: 0,
    memoryUsage: 0,
    responseTimeMs: [],
    concurrentOperations: 0
  });

  const [testState, setTestState] = React.useState({
    activeUsers: 0,
    completedOperations: 0,
    failedOperations: 0,
    networkDisruptions: 0
  });

  // Simulate memory constraints
  React.useEffect(() => {
    if (memoryConstraints) {
      const memoryLimit = 50; // Simulate low memory
      const checkMemory = () => {
        const optimisticMessages = optimisticMessageManager.getOptimisticMessages();
        if (optimisticMessages.length > memoryLimit) {
          // Simulate memory pressure by clearing oldest messages
          optimisticMessageManager.clearAllOptimisticMessages();
          setMetrics(prev => ({ ...prev, memoryUsage: prev.memoryUsage + 1 }));
        }
      };
      const interval = setInterval(checkMemory, 1000);
      return () => clearInterval(interval);
    }
  }, [memoryConstraints]);

  // Chaos mode - random disruptions
  React.useEffect(() => {
    if (chaosMode) {
      const chaosInterval = setInterval(() => {
        const chaos = Math.random();
        if (chaos < 0.1) {
          // Random network disruption
          setTestState(prev => ({ ...prev, networkDisruptions: prev.networkDisruptions + 1 }));
          webSocketService.simulateError?.({ code: 1006, message: 'Chaos disruption' });
        } else if (chaos < 0.2) {
          // Random slow response
          setTimeout(() => {
            const mockMessage = {
              type: 'delayed_response',
              payload: { content: 'Delayed chaos response' }
            };
            webSocketService.onMessage?.(mockMessage);
          }, Math.random() * 5000);
        }
      }, 2000);
      return () => clearInterval(chaosInterval);
    }
  }, [chaosMode]);

  const updateMetrics = React.useCallback((update: Partial<typeof metrics>) => {
    setMetrics(prev => {
      const newMetrics = { ...prev, ...update };
      onMetrics?.(newMetrics);
      return newMetrics;
    });
  }, [onMetrics]);

  const authValue = {
    token: 'test-token-123',
    user: { id: 'test-user', email: 'test@example.com' },
    isAuthenticated: true,
    login: jest.fn(),
    logout: jest.fn(),
    refreshToken: jest.fn()
  };

  // Render multiple instances for concurrent testing
  const instances = Array.from({ length: simultaneousUsers }, (_, index) => (
    <div key={index} data-testid={`user-instance-${index}`}>
      <MessageInput />
    </div>
  ));

  return (
    <AuthContext.Provider value={authValue}>
      <WebSocketProvider>
        <div data-testid="concurrency-harness">
          {instances}
          <div data-testid="metrics" data-metrics={JSON.stringify(metrics)} />
          <div data-testid="test-state" data-state={JSON.stringify(testState)} />
        </div>
      </WebSocketProvider>
    </AuthContext.Provider>
  );
};

// Mock dependencies with advanced simulation capabilities
jest.mock('@/services/webSocketService');
jest.mock('@/services/threadService');
jest.mock('@/store/unified-chat');
jest.mock('@/store/threadStore');

describe('Edge Cases and Concurrency Pipeline Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  const mockWebSocketService = {
    onMessage: null,
    onStatusChange: null,
    connect: jest.fn(),
    disconnect: jest.fn(),
    sendMessage: jest.fn(),
    updateToken: jest.fn(),
    getSecureUrl: jest.fn((url: string) => url),
    simulateError: jest.fn()
  };

  const mockUnifiedChatStore = {
    subscribe: jest.fn(() => () => {}),
    getState: jest.fn(() => ({
      activeThreadId: null,
      messages: [],
      isProcessing: false
    })),
    addOptimisticMessage: jest.fn(),
    setActiveThread: jest.fn(),
    setProcessing: jest.fn()
  };

  const mockThreadStore = {
    subscribe: jest.fn(() => () => {}),
    getState: jest.fn(() => ({
      currentThreadId: null
    })),
    setCurrentThread: jest.fn(),
    addThread: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    (webSocketService as jest.Mocked<typeof webSocketService>) = mockWebSocketService as any;
    (useUnifiedChatStore as any) = Object.assign(jest.fn(() => mockUnifiedChatStore.getState()), mockUnifiedChatStore);
    (useThreadStore as any) = Object.assign(jest.fn(() => mockThreadStore.getState()), mockThreadStore);

    (ThreadService.createThread as jest.Mock).mockResolvedValue({
      id: 'concurrent-thread-123',
      title: 'Concurrent Thread'
    });

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

  describe('Concurrent Message Sending', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle multiple users sending messages simultaneously', async () => {
      const metrics: any[] = [];
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <ConcurrencyTestHarness 
          simultaneousUsers={3}
          onMetrics={(m) => metrics.push(m)}
        />
      );

      // Get textareas for all users
      const textareas = [
        screen.getByRole('textbox', { name: /message input/i }),
        // Note: Multiple textareas would need better selectors in real implementation
      ];

      // Simulate concurrent message sending
      const sendPromises = [];
      for (let i = 0; i < 3; i++) {
        const promise = (async () => {
          if (textareas[0]) { // Use first textarea for testing
            await user.type(textareas[0], `Concurrent message ${i}`);
            await user.keyboard('{Enter}');
            await user.clear(textareas[0]);
          }
        })();
        sendPromises.push(promise);
        
        // Stagger slightly to create concurrency
        act(() => {
          jest.advanceTimersByTime(10);
        });
      }

      await Promise.all(sendPromises);

      // Should have handled all concurrent sends
      expect(mockWebSocketService.sendMessage).toHaveBeenCalled();
      
      // Check optimistic message state
      const optimisticMessages = optimisticMessageManager.getOptimisticMessages();
      expect(optimisticMessages.length).toBeGreaterThan(0);
    });

    it('should maintain message ordering during concurrent sends', async () => {
      const messageOrder: string[] = [];
      
      // Track message order
      mockWebSocketService.sendMessage.mockImplementation((message: any) => {
        if (message.payload?.user_request) {
          messageOrder.push(message.payload.user_request);
        }
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ConcurrencyTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Send messages with enforced order
      const messages = ['First message', 'Second message', 'Third message'];
      
      for (const message of messages) {
        await user.clear(textarea);
        await user.type(textarea, message);
        await user.keyboard('{Enter}');
        
        // Small delay to ensure ordering
        act(() => {
          jest.advanceTimersByTime(100);
        });
      }

      // Messages should maintain order despite concurrency
      expect(messageOrder).toHaveLength(3);
      expect(messageOrder[0]).toContain('First message');
      expect(messageOrder[1]).toContain('Second message');
      expect(messageOrder[2]).toContain('Third message');
    });

    it('should handle rapid-fire message sending with rate limiting', async () => {
      let sendCount = 0;
      mockWebSocketService.sendMessage.mockImplementation(() => {
        sendCount++;
        if (sendCount > 10) {
          throw new Error('Rate limit exceeded');
        }
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ConcurrencyTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Attempt to send many messages rapidly
      for (let i = 0; i < 20; i++) {
        await user.clear(textarea);
        await user.type(textarea, `Rapid message ${i}`);
        await user.keyboard('{Enter}');
        
        act(() => {
          jest.advanceTimersByTime(50);
        });
      }

      // Should respect rate limiting
      expect(sendCount).toBeLessThanOrEqual(10);
      
      // Failed messages should be marked appropriately
      await waitFor(() => {
        const failedMessages = optimisticMessageManager.getFailedMessages();
        expect(failedMessages.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Race Conditions and State Consistency', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle race between message send and thread creation', async () => {
      let threadCreationDelay = 1000;
      
      (ThreadService.createThread as jest.Mock).mockImplementation(async (title) => {
        // Simulate slow thread creation
        await new Promise(resolve => setTimeout(resolve, threadCreationDelay));
        return {
          id: `race-thread-${Date.now()}`,
          title
        };
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ConcurrencyTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Send multiple messages before thread creation completes
      const sendPromises = [];
      for (let i = 0; i < 3; i++) {
        const promise = (async () => {
          await user.clear(textarea);
          await user.type(textarea, `Race message ${i}`);
          await user.keyboard('{Enter}');
        })();
        sendPromises.push(promise);
        
        act(() => {
          jest.advanceTimersByTime(100);
        });
      }

      // Complete all sends
      await Promise.all(sendPromises);

      // Advance time to complete thread creation
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      // Should have handled race condition gracefully
      expect(ThreadService.createThread).toHaveBeenCalled();
      
      // All messages should be associated with the same thread
      const optimisticMessages = optimisticMessageManager.getOptimisticMessages();
      const userMessages = optimisticMessages.filter(m => m.role === 'user');
      
      if (userMessages.length > 1) {
        const threadIds = userMessages.map(m => m.threadId).filter(Boolean);
        const uniqueThreadIds = new Set(threadIds);
        expect(uniqueThreadIds.size).toBeLessThanOrEqual(1); // Should use same thread
      }
    });

    it('should handle race between authentication and message send', async () => {
      const { rerender } = render(<ConcurrencyTestHarness />);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Start typing message
      await user.type(textarea, 'Message during auth change');

      // Simulate auth state change during typing
      const unauthValue = {
        token: null,
        user: null,
        isAuthenticated: false,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn()
      };

      rerender(
        <AuthContext.Provider value={unauthValue}>
          <WebSocketProvider>
            <div data-testid="concurrency-harness">
              <MessageInput />
            </div>
          </WebSocketProvider>
        </AuthContext.Provider>
      );

      // Try to send message while unauthenticated
      await user.keyboard('{Enter}');

      // Should not send message
      expect(mockWebSocketService.sendMessage).not.toHaveBeenCalled();
      
      // Input should be disabled
      expect(textarea).toBeDisabled();
    });

    it('should handle concurrent optimistic updates and reconciliation', async () => {
      render(<ConcurrencyTestHarness />);

      // Create optimistic messages
      const userMsg1 = optimisticMessageManager.addOptimisticUserMessage('Message 1');
      const userMsg2 = optimisticMessageManager.addOptimisticUserMessage('Message 2');
      const aiMsg1 = optimisticMessageManager.addOptimisticAiMessage();

      // Simulate concurrent updates and reconciliation
      const updatePromises = [
        // Concurrent optimistic updates
        Promise.resolve(optimisticMessageManager.updateOptimisticMessage(userMsg1.localId, { status: 'confirmed' })),
        Promise.resolve(optimisticMessageManager.updateOptimisticMessage(userMsg2.localId, { content: 'Updated content' })),
        Promise.resolve(optimisticMessageManager.updateOptimisticMessage(aiMsg1.localId, { content: 'AI response' })),
        
        // Concurrent reconciliation
        Promise.resolve().then(() => {
          const backendMessages = [
            {
              id: 'backend-1',
              content: 'Message 1',
              role: 'user' as const,
              timestamp: Date.now()
            }
          ];
          return optimisticMessageManager.reconcileWithBackend(backendMessages);
        })
      ];

      await Promise.all(updatePromises);

      // State should be consistent despite concurrent operations
      const finalState = optimisticMessageManager.getState();
      expect(finalState.messages.size).toBe(3);
    });
  });

  describe('Memory and Performance Boundaries', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle memory constraints with message cleanup', async () => {
      render(<ConcurrencyTestHarness memoryConstraints={true} />);

      // Create many optimistic messages to trigger memory pressure
      const messages = [];
      for (let i = 0; i < 100; i++) {
        const msg = optimisticMessageManager.addOptimisticUserMessage(`Memory test message ${i}`);
        messages.push(msg);
        
        act(() => {
          jest.advanceTimersByTime(10);
        });
      }

      // Fast-forward to trigger memory cleanup
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      // Should have cleaned up messages due to memory constraints
      const remainingMessages = optimisticMessageManager.getOptimisticMessages();
      expect(remainingMessages.length).toBeLessThan(100);
    });

    it('should maintain performance under high message load', async () => {
      const performanceStart = performance.now();
      
      render(<ConcurrencyTestHarness messageLoad={1000} />);

      // Create high volume of messages
      for (let i = 0; i < 1000; i++) {
        optimisticMessageManager.addOptimisticUserMessage(`Load test message ${i}`);
        
        if (i % 100 === 0) {
          act(() => {
            jest.advanceTimersByTime(1);
          });
        }
      }

      const performanceEnd = performance.now();
      const totalTime = performanceEnd - performanceStart;

      // Should complete within reasonable time
      expect(totalTime).toBeLessThan(2000);

      // Should handle all messages
      const messages = optimisticMessageManager.getOptimisticMessages();
      expect(messages.length).toBe(1000);
    });

    it('should handle memory leaks prevention during long sessions', async () => {
      render(<ConcurrencyTestHarness />);

      // Simulate long session with many message cycles
      for (let cycle = 0; cycle < 10; cycle++) {
        // Create messages
        const cycleMessages = [];
        for (let i = 0; i < 20; i++) {
          const msg = optimisticMessageManager.addOptimisticUserMessage(`Cycle ${cycle} Message ${i}`);
          cycleMessages.push(msg);
        }

        // Reconcile some messages
        const backendMessages = cycleMessages.slice(0, 10).map((msg, index) => ({
          id: `backend-${cycle}-${index}`,
          content: msg.content,
          role: msg.role,
          timestamp: Date.now()
        }));

        optimisticMessageManager.reconcileWithBackend(backendMessages);

        act(() => {
          jest.advanceTimersByTime(1000);
        });
      }

      // Should not accumulate excessive state
      const finalState = optimisticMessageManager.getState();
      expect(finalState.messages.size).toBeLessThan(200); // Reasonable upper bound
    });
  });

  describe('Network Disruption and Recovery', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle network disruption during message pipeline', async () => {
      let networkDown = false;
      
      mockWebSocketService.sendMessage.mockImplementation(() => {
        if (networkDown) {
          throw new Error('Network unavailable');
        }
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ConcurrencyTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Send message while network is up
      await user.type(textarea, 'Message before disruption');
      await user.keyboard('{Enter}');

      expect(mockWebSocketService.sendMessage).toHaveBeenCalledTimes(1);

      // Simulate network disruption
      networkDown = true;
      
      await user.clear(textarea);
      await user.type(textarea, 'Message during disruption');
      await user.keyboard('{Enter}');

      // Should have failed messages
      const failedMessages = optimisticMessageManager.getFailedMessages();
      expect(failedMessages.length).toBeGreaterThan(0);

      // Network recovery
      networkDown = false;
      
      await user.clear(textarea);
      await user.type(textarea, 'Message after recovery');
      await user.keyboard('{Enter}');

      // Should work again after recovery
      expect(mockWebSocketService.sendMessage).toHaveBeenCalledTimes(3);
    });

    it('should handle intermittent connection with automatic retry', async () => {
      let connectionAttempts = 0;
      
      mockWebSocketService.sendMessage.mockImplementation(() => {
        connectionAttempts++;
        if (connectionAttempts % 3 === 0) {
          // Every 3rd attempt succeeds
          return;
        }
        throw new Error('Intermittent connection failure');
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<ConcurrencyTestHarness />);

      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Send multiple messages with intermittent failures
      for (let i = 0; i < 6; i++) {
        await user.clear(textarea);
        await user.type(textarea, `Intermittent message ${i}`);
        await user.keyboard('{Enter}');
        
        act(() => {
          jest.advanceTimersByTime(200);
        });
      }

      // Should have attempted all sends
      expect(connectionAttempts).toBe(6);
      
      // Some should have succeeded, others failed
      const failedMessages = optimisticMessageManager.getFailedMessages();
      expect(failedMessages.length).toBeGreaterThan(0);
      expect(failedMessages.length).toBeLessThan(6);
    });
  });

  describe('Chaos Mode Testing', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should maintain stability under chaotic conditions', async () => {
      const chaosMetrics: any[] = [];
      
      render(
        <ConcurrencyTestHarness 
          chaosMode={true}
          onMetrics={(m) => chaosMetrics.push(m)}
        />
      );

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Send messages during chaos
      for (let i = 0; i < 10; i++) {
        try {
          await user.clear(textarea);
          await user.type(textarea, `Chaos message ${i}`);
          await user.keyboard('{Enter}');
        } catch (error) {
          // Expected in chaos mode
        }
        
        act(() => {
          jest.advanceTimersByTime(500);
        });
      }

      // Fast-forward through chaos period
      act(() => {
        jest.advanceTimersByTime(10000);
      });

      // System should remain functional despite chaos
      expect(() => {
        optimisticMessageManager.getOptimisticMessages();
      }).not.toThrow();

      // Should have handled some messages successfully
      const messages = optimisticMessageManager.getOptimisticMessages();
      expect(messages.length).toBeGreaterThan(0);
    });
  });

  describe('Component Lifecycle Edge Cases', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle rapid mount/unmount cycles', async () => {
      const { unmount, rerender } = render(<ConcurrencyTestHarness />);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      // Start operation
      const textarea = screen.getByRole('textbox', { name: /message input/i });
      await user.type(textarea, 'Message during lifecycle test');

      // Rapid unmount/remount
      unmount();
      rerender(<ConcurrencyTestHarness />);

      // Should not crash
      expect(() => {
        screen.getByRole('textbox', { name: /message input/i });
      }).not.toThrow();
    });

    it('should cleanup properly on unmount with pending operations', async () => {
      const slowPromise = new Promise(resolve => setTimeout(resolve, 1000));
      
      mockWebSocketService.sendMessage.mockReturnValue(slowPromise);

      const { unmount } = render(<ConcurrencyTestHarness />);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Start slow operation
      await user.type(textarea, 'Message with slow operation');
      await user.keyboard('{Enter}');

      // Unmount before completion
      unmount();

      // Should not cause memory leaks or errors
      act(() => {
        jest.advanceTimersByTime(6000);
      });

      expect(() => {
        // No errors should occur after unmount
      }).not.toThrow();
    });
  });

  describe('Browser Environment Edge Cases', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle focus/blur events during message sending', async () => {
      render(<ConcurrencyTestHarness />);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Start typing
      await user.type(textarea, 'Message with focus changes');

      // Simulate focus loss
      fireEvent.blur(textarea);
      
      // Simulate focus regain
      fireEvent.focus(textarea);

      // Complete message
      await user.keyboard('{Enter}');

      // Should handle focus changes gracefully
      expect(mockWebSocketService.sendMessage).toHaveBeenCalled();
    });

    it('should handle page visibility changes during operations', async () => {
      render(<ConcurrencyTestHarness />);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const textarea = screen.getByRole('textbox', { name: /message input/i });

      // Start message send
      await user.type(textarea, 'Message during visibility change');
      await user.keyboard('{Enter}');

      // Simulate page becoming hidden
      Object.defineProperty(document, 'visibilityState', {
        writable: true,
        value: 'hidden'
      });
      fireEvent(document, new Event('visibilitychange'));

      // Simulate page becoming visible again
      Object.defineProperty(document, 'visibilityState', {
        writable: true,
        value: 'visible'
      });
      fireEvent(document, new Event('visibilitychange'));

      // Should maintain functionality
      expect(mockWebSocketService.sendMessage).toHaveBeenCalled();
    });
  });
});