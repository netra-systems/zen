import { act, renderHook } from '@testing-library/react';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chat';
import { useAppStore } from '@/store/app';
import { AuthStoreTestUtils, ChatStoreTestUtils, GlobalTestUtils } from './store-test-utils';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
on correct state management
 * - Revenue Impact: State corruption loses user data and revenue
 * 
 * Tests: Action dispatching, reducer logic, state transitions
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { act, renderHook } from '@testing-library/react';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chat';
import { useAppStore } from '@/store/app';
import { AuthStoreTestUtils, ChatStoreTestUtils, GlobalTestUtils } from './store-test-utils';

describe('Store Actions and Reducers - State Transition Tests', () => {
    jest.setTimeout(10000);
  beforeEach(() => {
    GlobalTestUtils.setupStoreTestEnvironment();
  });

  afterEach(() => {
    GlobalTestUtils.cleanupStoreTestEnvironment();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Auth Store State Transitions', () => {
      jest.setTimeout(10000);
    it('should handle login action with complete state transition', () => {
      const result = AuthStoreTestUtils.initializeStore();
      const user = AuthStoreTestUtils.createMockUser('standard_user', ['read']);
      const token = AuthStoreTestUtils.createTestToken('login');

      AuthStoreTestUtils.performLogin(result, user, token);

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(user);
      expect(result.current.token).toBe(token);
      expect(result.current.error).toBeNull();
    });

    it('should handle logout action with complete state reset', () => {
      const result = AuthStoreTestUtils.initializeStore();
      const user = AuthStoreTestUtils.createMockUser('admin', ['admin']);
      const token = AuthStoreTestUtils.createTestToken('logout');

      // Login first
      AuthStoreTestUtils.performLogin(result, user, token);
      expect(result.current.isAuthenticated).toBe(true);

      // Then logout
      act(() => {
        result.current.logout();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
      expect(result.current.error).toBeNull();
    });

    it('should handle user update action preserving other state', () => {
      const result = AuthStoreTestUtils.initializeStore();
      const user = AuthStoreTestUtils.createMockUser('developer', ['dev']);
      const token = AuthStoreTestUtils.createTestToken('update');

      AuthStoreTestUtils.performLogin(result, user, token);

      const updateData = { full_name: 'Updated Developer' };
      act(() => {
        result.current.updateUser(updateData);
      });

      expect(result.current.user?.full_name).toBe('Updated Developer');
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.token).toBe(token);
    });

    it('should handle error state management', () => {
      const result = AuthStoreTestUtils.initializeStore();
      const errorMessage = 'Authentication failed';

      act(() => {
        result.current.setError(errorMessage);
      });

      expect(result.current.error).toBe(errorMessage);

      act(() => {
        result.current.setError(null);
      });

      expect(result.current.error).toBeNull();
    });

    it('should handle loading state management', () => {
      const result = AuthStoreTestUtils.initializeStore();

      act(() => {
        result.current.setLoading(true);
      });

      expect(result.current.loading).toBe(true);

      act(() => {
        result.current.setLoading(false);
      });

      expect(result.current.loading).toBe(false);
    });
  });

  describe('Chat Store State Transitions', () => {
      jest.setTimeout(10000);
    it('should handle message addition with ID generation', () => {
      const result = ChatStoreTestUtils.initializeStore();
      const message = ChatStoreTestUtils.createMockMessage('', 'user', 'Test');

      ChatStoreTestUtils.addMessageAndVerify(result, message);

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].id).toBeTruthy();
      expect(result.current.messages[0].content).toBe('Test');
    });

    it('should handle message updates correctly', () => {
      const result = ChatStoreTestUtils.initializeStore();
      const message = ChatStoreTestUtils.createMockMessage('msg-1');

      ChatStoreTestUtils.addMessageAndVerify(result, message);

      act(() => {
        result.current.updateMessage('msg-1', { content: 'Updated content' });
      });

      expect(result.current.messages[0].content).toBe('Updated content');
      expect(result.current.messages[0].id).toBe('msg-1');
    });

    it('should handle processing state transitions', () => {
      const result = ChatStoreTestUtils.initializeStore();

      ChatStoreTestUtils.setProcessingAndVerify(result, true);
      expect(result.current.isProcessing).toBe(true);

      ChatStoreTestUtils.setProcessingAndVerify(result, false);
      expect(result.current.isProcessing).toBe(false);
    });

    it('should handle sub-agent state updates', () => {
      const result = ChatStoreTestUtils.initializeStore();

      act(() => {
        result.current.setSubAgent('DataSubAgent', 'processing');
      });

      expect(result.current.subAgentName).toBe('DataSubAgent');
      expect(result.current.currentSubAgent).toBe('DataSubAgent');
      expect(result.current.subAgentStatus).toBe('processing');
    });

    it('should handle thread switching with message clearing', () => {
      const result = ChatStoreTestUtils.initializeStore();
      const message = ChatStoreTestUtils.createMockMessage('msg-1');

      ChatStoreTestUtils.addMessageAndVerify(result, message);
      expect(result.current.messages).toHaveLength(1);

      act(() => {
        result.current.setActiveThread('thread-2');
      });

      expect(result.current.activeThreadId).toBe('thread-2');
      expect(result.current.messages).toHaveLength(0);
    });

    it('should handle error message addition', () => {
      const result = ChatStoreTestUtils.initializeStore();
      const errorMessage = 'Connection failed';

      act(() => {
        result.current.addError(errorMessage);
      });

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].type).toBe('error');
      expect(result.current.messages[0].content).toBe(errorMessage);
    });
  });

  describe('App Store State Transitions', () => {
      jest.setTimeout(10000);
    it('should handle sidebar toggle action', () => {
      const { result } = renderHook(() => useAppStore());

      expect(result.current.isSidebarCollapsed).toBe(false);

      act(() => {
        result.current.toggleSidebar();
      });

      expect(result.current.isSidebarCollapsed).toBe(true);

      act(() => {
        result.current.toggleSidebar();
      });

      expect(result.current.isSidebarCollapsed).toBe(false);
    });
  });

  describe('Complex State Transitions', () => {
      jest.setTimeout(10000);
    it('should handle sequential auth and chat actions', () => {
      const authResult = AuthStoreTestUtils.initializeStore();
      const chatResult = ChatStoreTestUtils.initializeStore();

      // Login sequence
      const user = AuthStoreTestUtils.createMockUser('power_user');
      const token = AuthStoreTestUtils.createTestToken('sequence');
      AuthStoreTestUtils.performLogin(authResult, user, token);

      // Chat sequence
      const message = ChatStoreTestUtils.createMockMessage('msg-1');
      ChatStoreTestUtils.addMessageAndVerify(chatResult, message);

      expect(authResult.current.isAuthenticated).toBe(true);
      expect(chatResult.current.messages).toHaveLength(1);
    });

    it('should handle error scenarios across stores', () => {
      const authResult = AuthStoreTestUtils.initializeStore();
      const chatResult = ChatStoreTestUtils.initializeStore();

      // Set errors in both stores
      act(() => {
        authResult.current.setError('Auth error');
        chatResult.current.addError('Chat error');
      });

      expect(authResult.current.error).toBe('Auth error');
      expect(chatResult.current.messages[0].type).toBe('error');
    });

    it('should handle rapid state updates without conflicts', () => {
      const result = ChatStoreTestUtils.initializeStore();

      act(() => {
        result.current.addMessage({
          id: 'msg-1',
          type: 'user',
          content: 'Message 1',
          created_at: new Date().toISOString(),
          displayed_to_user: true
        });
        result.current.setProcessing(true);
        result.current.addMessage({
          id: 'msg-2', 
          type: 'ai',
          content: 'Message 2',
          created_at: new Date().toISOString(),
          displayed_to_user: true
        });
        result.current.setProcessing(false);
      });

      expect(result.current.messages).toHaveLength(2);
      expect(result.current.isProcessing).toBe(false);
    });

    it('should handle reset actions completely', () => {
      const authResult = AuthStoreTestUtils.initializeStore();
      const chatResult = ChatStoreTestUtils.initializeStore();

      // Set up some state
      const user = AuthStoreTestUtils.createMockUser('admin');
      const token = AuthStoreTestUtils.createTestToken('reset');
      AuthStoreTestUtils.performLogin(authResult, user, token);

      const message = ChatStoreTestUtils.createMockMessage('msg-1');
      ChatStoreTestUtils.addMessageAndVerify(chatResult, message);

      // Reset both stores
      act(() => {
        authResult.current.reset();
        chatResult.current.reset();
      });

      expect(authResult.current.isAuthenticated).toBe(false);
      expect(authResult.current.user).toBeNull();
      expect(chatResult.current.messages).toHaveLength(0);
      expect(chatResult.current.isProcessing).toBe(false);
    });
  });

  describe('Action Immutability', () => {
      jest.setTimeout(10000);
    it('should not mutate original state objects', () => {
      const result = ChatStoreTestUtils.initializeStore();
      const originalMessage = {
        id: 'msg-1',
        type: 'user' as const,
        content: 'Original',
        created_at: new Date().toISOString(),
        displayed_to_user: true
      };

      act(() => {
        result.current.addMessage(originalMessage);
      });

      // Original object should remain unchanged
      expect(originalMessage.content).toBe('Original');

      act(() => {
        result.current.updateMessage('msg-1', { content: 'Updated' });
      });

      expect(originalMessage.content).toBe('Original');
      expect(result.current.messages[0].content).toBe('Updated');
    });

    it('should maintain array immutability', () => {
      const result = ChatStoreTestUtils.initializeStore();
      const originalMessages = result.current.messages;

      const message = ChatStoreTestUtils.createMockMessage('msg-1');
      act(() => {
        result.current.addMessage(message);
      });

      // Should get new array reference
      expect(result.current.messages).not.toBe(originalMessages);
      expect(result.current.messages).toHaveLength(1);
    });
  });
});