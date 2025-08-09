import { renderHook, act } from '@testing-library/react-hooks';
import { create } from 'zustand';
import { useChatStore } from '../../store/chatStore';
import { useAuthStore } from '../../store/authStore';
import { useThreadStore } from '../../store/threadStore';
import { immer } from 'zustand/middleware/immer';

describe('State Management and Data Flow Tests', () => {
  beforeEach(() => {
    // Reset all stores before each test
    useChatStore.getState().reset();
    useAuthStore.getState().reset();
    useThreadStore.getState().reset();
  });

  describe('Chat Store Management', () => {
    it('should handle message state updates correctly', () => {
      const { result } = renderHook(() => useChatStore());

      const testMessage = {
        id: 'msg_1',
        content: 'Test message',
        role: 'user' as const,
        timestamp: Date.now(),
        runId: 'run_123',
      };

      act(() => {
        result.current.addMessage(testMessage);
      });

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0]).toEqual(testMessage);
      expect(result.current.currentRunId).toBe('run_123');
    });

    it('should handle agent status updates and workflow progression', () => {
      const { result } = renderHook(() => useChatStore());

      const statusUpdates = [
        { status: 'IDLE' as const, progress: 0 },
        { status: 'RUNNING' as const, progress: 25 },
        { status: 'RUNNING' as const, progress: 75 },
        { status: 'COMPLETED' as const, progress: 100 },
      ];

      statusUpdates.forEach(update => {
        act(() => {
          result.current.updateAgentStatus(update.status, update.progress);
        });
        
        expect(result.current.agentStatus).toBe(update.status);
        expect(result.current.workflowProgress).toBe(update.progress);
      });
    });

    it('should manage streaming message state correctly', () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setStreamingMessage('Starting analysis');
        result.current.setIsStreaming(true);
      });

      expect(result.current.streamingMessage).toBe('Starting analysis');
      expect(result.current.isStreaming).toBe(true);

      act(() => {
        result.current.appendToStreamingMessage('...');
      });

      expect(result.current.streamingMessage).toBe('Starting analysis...');

      act(() => {
        result.current.completeStreaming();
      });

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.messages).toContainEqual(
        expect.objectContaining({
          content: 'Starting analysis...',
          role: 'assistant',
        })
      );
    });

    it('should handle sub-agent state management', () => {
      const { result } = renderHook(() => useChatStore());

      const subAgentUpdate = {
        name: 'TriageSubAgent',
        status: 'RUNNING' as const,
        progress: 50,
        messages: ['Analyzing request type...'],
      };

      act(() => {
        result.current.updateSubAgent(subAgentUpdate.name, subAgentUpdate);
      });

      expect(result.current.subAgents[subAgentUpdate.name]).toEqual(subAgentUpdate);

      act(() => {
        result.current.updateSubAgent(subAgentUpdate.name, {
          ...subAgentUpdate,
          status: 'COMPLETED',
          progress: 100,
          messages: [...subAgentUpdate.messages, 'Request classified successfully'],
        });
      });

      expect(result.current.subAgents[subAgentUpdate.name].status).toBe('COMPLETED');
      expect(result.current.subAgents[subAgentUpdate.name].messages).toHaveLength(2);
    });
  });

  describe('Authentication State Management', () => {
    it('should handle login state transitions', () => {
      const { result } = renderHook(() => useAuthStore());

      const user = {
        id: 'user_123',
        email: 'test@netra.ai',
        name: 'Test User',
        roles: ['user'],
      };

      const token = 'jwt_token_123';

      act(() => {
        result.current.login(user, token);
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(user);
      expect(result.current.token).toBe(token);
      expect(result.current.loginTimestamp).toBeDefined();
    });

    it('should handle logout and state cleanup', () => {
      const { result } = renderHook(() => useAuthStore());

      // Setup authenticated state
      act(() => {
        result.current.login(
          { id: 'user_123', email: 'test@netra.ai', name: 'Test User', roles: ['user'] },
          'jwt_token_123'
        );
      });

      expect(result.current.isAuthenticated).toBe(true);

      act(() => {
        result.current.logout();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
      expect(result.current.loginTimestamp).toBeNull();
    });

    it('should handle token refresh and expiration', () => {
      const { result } = renderHook(() => useAuthStore());

      const initialToken = 'initial_token';
      const refreshedToken = 'refreshed_token';

      act(() => {
        result.current.login(
          { id: 'user_123', email: 'test@netra.ai', name: 'Test User', roles: ['user'] },
          initialToken
        );
      });

      expect(result.current.token).toBe(initialToken);

      act(() => {
        result.current.refreshToken(refreshedToken);
      });

      expect(result.current.token).toBe(refreshedToken);
      expect(result.current.tokenRefreshCount).toBe(1);

      // Test token expiration
      act(() => {
        result.current.handleTokenExpiration();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.tokenExpired).toBe(true);
    });
  });

  describe('Thread Store Management', () => {
    it('should manage thread creation and selection', () => {
      const { result } = renderHook(() => useThreadStore());

      const newThread = {
        id: 'thread_1',
        title: 'AI Optimization Discussion',
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messageCount: 0,
      };

      act(() => {
        result.current.createThread(newThread);
      });

      expect(result.current.threads).toHaveLength(1);
      expect(result.current.threads[0]).toEqual(newThread);

      act(() => {
        result.current.selectThread('thread_1');
      });

      expect(result.current.activeThreadId).toBe('thread_1');
      expect(result.current.activeThread).toEqual(newThread);
    });

    it('should handle thread updates and message counting', () => {
      const { result } = renderHook(() => useThreadStore());

      const thread = {
        id: 'thread_1',
        title: 'Test Thread',
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messageCount: 0,
      };

      act(() => {
        result.current.createThread(thread);
        result.current.selectThread('thread_1');
      });

      act(() => {
        result.current.incrementMessageCount('thread_1');
      });

      expect(result.current.activeThread?.messageCount).toBe(1);

      act(() => {
        result.current.updateThreadTitle('thread_1', 'Updated Thread Title');
      });

      expect(result.current.activeThread?.title).toBe('Updated Thread Title');
    });

    it('should handle thread deletion and cleanup', () => {
      const { result } = renderHook(() => useThreadStore());

      const threads = [
        { id: 'thread_1', title: 'Thread 1', createdAt: Date.now(), updatedAt: Date.now(), messageCount: 0 },
        { id: 'thread_2', title: 'Thread 2', createdAt: Date.now(), updatedAt: Date.now(), messageCount: 0 },
      ];

      threads.forEach(thread => {
        act(() => {
          result.current.createThread(thread);
        });
      });

      act(() => {
        result.current.selectThread('thread_1');
      });

      expect(result.current.threads).toHaveLength(2);
      expect(result.current.activeThreadId).toBe('thread_1');

      act(() => {
        result.current.deleteThread('thread_1');
      });

      expect(result.current.threads).toHaveLength(1);
      expect(result.current.activeThreadId).toBeNull();
      expect(result.current.threads[0].id).toBe('thread_2');
    });
  });

  describe('Cross-Store State Synchronization', () => {
    it('should synchronize authentication state with chat store', () => {
      const { result: authResult } = renderHook(() => useAuthStore());
      const { result: chatResult } = renderHook(() => useChatStore());

      // Login should affect chat store
      act(() => {
        authResult.current.login(
          { id: 'user_123', email: 'test@netra.ai', name: 'Test User', roles: ['user'] },
          'jwt_token_123'
        );
      });

      expect(chatResult.current.currentUserId).toBe('user_123');

      // Logout should clear chat data
      act(() => {
        authResult.current.logout();
      });

      expect(chatResult.current.currentUserId).toBeNull();
      expect(chatResult.current.messages).toHaveLength(0);
    });

    it('should handle concurrent state updates from multiple sources', async () => {
      const { result: chatResult } = renderHook(() => useChatStore());
      const { result: threadResult } = renderHook(() => useThreadStore());

      const concurrentUpdates = [
        () => chatResult.current.addMessage({
          id: 'msg_1',
          content: 'Message 1',
          role: 'user',
          timestamp: Date.now(),
          runId: 'run_1',
        }),
        () => threadResult.current.createThread({
          id: 'thread_1',
          title: 'Thread 1',
          createdAt: Date.now(),
          updatedAt: Date.now(),
          messageCount: 0,
        }),
        () => chatResult.current.updateAgentStatus('RUNNING', 50),
      ];

      // Execute all updates concurrently
      await act(async () => {
        await Promise.all(concurrentUpdates.map(update => 
          new Promise(resolve => {
            update();
            resolve(undefined);
          })
        ));
      });

      expect(chatResult.current.messages).toHaveLength(1);
      expect(threadResult.current.threads).toHaveLength(1);
      expect(chatResult.current.agentStatus).toBe('RUNNING');
    });
  });

  describe('State Persistence and Hydration', () => {
    it('should persist critical state to localStorage', () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        result.current.login(
          { id: 'user_123', email: 'test@netra.ai', name: 'Test User', roles: ['user'] },
          'jwt_token_123'
        );
      });

      expect(localStorage.getItem('auth_token')).toBe('jwt_token_123');
      expect(JSON.parse(localStorage.getItem('auth_user') || '{}')).toEqual({
        id: 'user_123',
        email: 'test@netra.ai',
        name: 'Test User',
        roles: ['user'],
      });
    });

    it('should hydrate state from localStorage on initialization', () => {
      localStorage.setItem('auth_token', 'stored_token');
      localStorage.setItem('auth_user', JSON.stringify({
        id: 'stored_user',
        email: 'stored@netra.ai',
        name: 'Stored User',
        roles: ['user'],
      }));

      const { result } = renderHook(() => useAuthStore());

      expect(result.current.token).toBe('stored_token');
      expect(result.current.user?.id).toBe('stored_user');
      expect(result.current.isAuthenticated).toBe(true);
    });

    it('should handle corrupted localStorage gracefully', () => {
      localStorage.setItem('auth_user', 'invalid_json');
      localStorage.setItem('threads', 'also_invalid');

      const { result: authResult } = renderHook(() => useAuthStore());
      const { result: threadResult } = renderHook(() => useThreadStore());

      expect(authResult.current.user).toBeNull();
      expect(authResult.current.isAuthenticated).toBe(false);
      expect(threadResult.current.threads).toHaveLength(0);
    });
  });

  describe('State Immutability and Time Travel', () => {
    it('should maintain immutable state updates', () => {
      const { result } = renderHook(() => useChatStore());

      const initialState = result.current;

      act(() => {
        result.current.addMessage({
          id: 'msg_1',
          content: 'Test message',
          role: 'user',
          timestamp: Date.now(),
          runId: 'run_1',
        });
      });

      expect(initialState.messages).toHaveLength(0);
      expect(result.current.messages).toHaveLength(1);
      expect(initialState).not.toBe(result.current);
    });

    it('should support state history for debugging', () => {
      const stateHistory: any[] = [];
      
      const { result } = renderHook(() => {
        const store = useChatStore();
        stateHistory.push(JSON.parse(JSON.stringify(store)));
        return store;
      });

      act(() => {
        result.current.updateAgentStatus('RUNNING', 25);
      });

      act(() => {
        result.current.updateAgentStatus('RUNNING', 75);
      });

      act(() => {
        result.current.updateAgentStatus('COMPLETED', 100);
      });

      expect(stateHistory).toHaveLength(4); // Initial + 3 updates
      expect(stateHistory[0].agentStatus).toBe('IDLE');
      expect(stateHistory[1].agentStatus).toBe('RUNNING');
      expect(stateHistory[3].agentStatus).toBe('COMPLETED');
    });
  });

  describe('Performance and Memory Management', () => {
    it('should handle large state objects efficiently', () => {
      const { result } = renderHook(() => useChatStore());

      const largeMessageBatch = Array.from({ length: 1000 }, (_, i) => ({
        id: `msg_${i}`,
        content: `Message ${i}`,
        role: 'user' as const,
        timestamp: Date.now() + i,
        runId: `run_${i}`,
      }));

      const startTime = performance.now();

      act(() => {
        largeMessageBatch.forEach(message => {
          result.current.addMessage(message);
        });
      });

      const endTime = performance.now();
      const executionTime = endTime - startTime;

      expect(result.current.messages).toHaveLength(1000);
      expect(executionTime).toBeLessThan(1000); // Should complete within 1 second
    });

    it('should clean up expired state data', () => {
      const { result } = renderHook(() => useChatStore());

      // Add messages with old timestamps
      const expiredMessages = Array.from({ length: 10 }, (_, i) => ({
        id: `expired_msg_${i}`,
        content: `Expired message ${i}`,
        role: 'user' as const,
        timestamp: Date.now() - (24 * 60 * 60 * 1000), // 24 hours ago
        runId: `expired_run_${i}`,
      }));

      expiredMessages.forEach(message => {
        act(() => {
          result.current.addMessage(message);
        });
      });

      expect(result.current.messages).toHaveLength(10);

      act(() => {
        result.current.cleanupExpiredData();
      });

      expect(result.current.messages.length).toBeLessThan(10);
    });
  });
});