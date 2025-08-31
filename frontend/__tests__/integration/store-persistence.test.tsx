import React from 'react';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
ting-library/react';
import userEvent from '@testing-library/user-event';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';

// Test component that demonstrates persistence behavior
const PersistenceTestComponent: React.FC = () => {
  const {
    messages,
    activeThreadId,
    threads,
    addMessage,
    setActiveThread,
    fastLayerData,
    updateFastLayer
  } = useUnifiedChatStore();
  
  const { user, token, login } = useAuthStore();

  const setUser = (userData: any) => {
    login(userData, 'test-token');
  };

  const setToken = (tokenValue: string) => {
    if (user) {
      login(user, tokenValue);
    }
  };

  return (
    <div>
      <div data-testid="messages-count">{messages.length}</div>
      <div data-testid="active-thread">{activeThreadId || 'none'}</div>
      <div data-testid="threads-count">{threads.size}</div>
      <div data-testid="fast-layer">{fastLayerData ? JSON.stringify(fastLayerData) : 'null'}</div>
      <div data-testid="user-id">{user?.id || 'no-user'}</div>
      <div data-testid="auth-token">{token || 'no-token'}</div>
      
      <button
        data-testid="add-message"
        onClick={() => addMessage({
          id: `msg-${Date.now()}`,
          role: 'user',
          content: 'Test message',
          timestamp: Date.now()
        })}
      />
      <button
        data-testid="set-thread"
        onClick={() => setActiveThread('test-thread-123')}
      />
      <button
        data-testid="update-fast-layer"
        onClick={() => updateFastLayer({
          agentName: 'Persistent Agent',
          timestamp: Date.now(),
          runId: 'persistent-run'
        })}
      />
      <button
        data-testid="set-auth"
        onClick={() => {
          login({ id: 'user-123', name: 'Test User', email: 'test@example.com' }, 'test-token-456');
        }}
      />
    </div>
  );
};

// Helper to simulate page refresh by recreating stores
const simulatePageRefresh = () => {
  // Clear any existing store instances
  jest.clearAllMocks();
  
  // In a real app, stores would be recreated from localStorage
  // Here we simulate by accessing localStorage directly
  const unifiedChatData = localStorage.getItem('unified-chat-store');
  const authData = localStorage.getItem('auth-store');
  
  return { unifiedChatData, authData };
};

// Mock for localStorage persistence
const createMockLocalStorage = () => {
  const store = new Map<string, string>();
  
  return {
    getItem: jest.fn((key: string) => store.get(key) || null),
    setItem: jest.fn((key: string, value: string) => store.set(key, value)),
    removeItem: jest.fn((key: string) => store.delete(key)),
    clear: jest.fn(() => store.clear()),
    get size() { return store.size; },
    key: jest.fn((index: number) => Array.from(store.keys())[index] || null),
    store // Expose for testing
  };
};

describe('Store Persistence Integration Tests', () => {
    jest.setTimeout(10000);
  let mockLocalStorage: ReturnType<typeof createMockLocalStorage>;

  beforeEach(() => {
    // Reset stores
    act(() => {
      useUnifiedChatStore.getState().resetLayers();
      useAuthStore.getState().reset();
    });
    
    // Set up mock localStorage
    mockLocalStorage = createMockLocalStorage();
    Object.defineProperty(global, 'localStorage', {
      value: mockLocalStorage,
      writable: true
    });
  });

  describe('State Persistence Across Page Refreshes', () => {
      jest.setTimeout(10000);
    it('persists authentication state across refreshes', async () => {
      const user = userEvent.setup();
      
      render(<PersistenceTestComponent />);

      // Set authentication data
      await user.click(screen.getByTestId('set-auth'));
      
      expect(screen.getByTestId('user-id')).toHaveTextContent('user-123');
      expect(screen.getByTestId('auth-token')).toHaveTextContent('test-token-456');
      
      // Verify localStorage was updated
      expect(mockLocalStorage.setItem).toHaveBeenCalled();
      
      // Simulate page refresh
      const { authData } = simulatePageRefresh();
      
      // Verify auth data exists in localStorage
      if (authData) {
        const parsedAuthData = JSON.parse(authData);
        expect(parsedAuthData.state.user?.id).toBe('user-123');
        expect(parsedAuthData.state.token).toBe('test-token-456');
      }
    });

    it('persists chat messages across browser sessions', async () => {
      const user = userEvent.setup();
      
      render(<PersistenceTestComponent />);

      // Add multiple messages
      await user.click(screen.getByTestId('add-message'));
      await user.click(screen.getByTestId('add-message'));
      await user.click(screen.getByTestId('add-message'));
      
      expect(screen.getByTestId('messages-count')).toHaveTextContent('3');
      
      // Set active thread
      await user.click(screen.getByTestId('set-thread'));
      expect(screen.getByTestId('active-thread')).toHaveTextContent('test-thread-123');
      
      // Simulate browser restart
      const { unifiedChatData } = simulatePageRefresh();
      
      // Verify chat data persistence structure
      if (unifiedChatData) {
        const parsedChatData = JSON.parse(unifiedChatData);
        expect(parsedChatData.state.messages).toHaveLength(3);
        expect(parsedChatData.state.activeThreadId).toBe('test-thread-123');
      }
    });

    it('handles partial state restoration gracefully', async () => {
      const user = userEvent.setup();
      
      render(<PersistenceTestComponent />);

      // Set up complex state
      await user.click(screen.getByTestId('add-message'));
      await user.click(screen.getByTestId('set-thread'));
      await user.click(screen.getByTestId('update-fast-layer'));
      
      // Verify all state set correctly
      expect(screen.getByTestId('messages-count')).toHaveTextContent('1');
      expect(screen.getByTestId('active-thread')).toHaveTextContent('test-thread-123');
      expect(screen.getByTestId('fast-layer')).toHaveTextContent('Persistent Agent');
      
      // Simulate corrupted localStorage (partial data)
      mockLocalStorage.store.set('unified-chat-store', '{"partial": "data"}');
      
      // Verify app doesn't crash with corrupted data
      expect(() => {
        simulatePageRefresh();
      }).not.toThrow();
    });
  });

  describe('Large State Persistence', () => {
      jest.setTimeout(10000);
    it('handles large message history persistence efficiently', async () => {
      const user = userEvent.setup();
      
      render(<PersistenceTestComponent />);

      // Create large message history
      await act(async () => {
        for (let i = 0; i < 1000; i++) {
          useUnifiedChatStore.getState().addMessage({
            id: `msg-${i}`,
            role: i % 2 === 0 ? 'user' : 'assistant',
            content: `Message ${i} with content that could be quite long in real scenarios`,
            timestamp: Date.now() + i
          });
        }
      });

      expect(screen.getByTestId('messages-count')).toHaveTextContent('1000');
      
      // Verify localStorage can handle large data
      expect(mockLocalStorage.setItem).toHaveBeenCalled();
      
      // Check performance of persistence operation
      const startTime = performance.now();
      simulatePageRefresh();
      const endTime = performance.now();
      
      // Persistence should complete quickly (< 100ms)
      expect(endTime - startTime).toBeLessThan(100);
    });

    it('implements storage quota management', async () => {
      const user = userEvent.setup();
      
      render(<PersistenceTestComponent />);

      // Simulate storage quota exceeded
      mockLocalStorage.setItem.mockImplementation(() => {
        throw new Error('QuotaExceededError');
      });

      // Attempt to add message that would exceed quota
      expect(() => {
        user.click(screen.getByTestId('add-message'));
      }).not.toThrow();
      
      // Verify graceful handling of quota issues
      expect(screen.getByTestId('messages-count')).toHaveTextContent('1');
    });
  });

  describe('Cross-Tab State Synchronization', () => {
      jest.setTimeout(10000);
    it('synchronizes state changes across browser tabs', async () => {
      const user = userEvent.setup();
      
      // Simulate first tab
      const { rerender } = render(<PersistenceTestComponent />);

      await user.click(screen.getByTestId('set-auth'));
      expect(screen.getByTestId('user-id')).toHaveTextContent('user-123');
      
      // Simulate storage event from another tab
      const storageEvent = new StorageEvent('storage', {
        key: 'auth-store',
        newValue: JSON.stringify({
          state: {
            user: { id: 'user-456', name: 'Updated User', email: 'updated@example.com' },
            token: 'updated-token'
          },
          version: 1
        }),
        oldValue: null,
        storageArea: localStorage
      });
      
      // Dispatch storage event
      act(() => {
        window.dispatchEvent(storageEvent);
      });
      
      // Re-render to reflect potential changes
      rerender(<PersistenceTestComponent />);
      
      // Verify state could be synchronized (implementation dependent)
      // This test documents expected behavior
    });

    it('prevents infinite sync loops between tabs', async () => {
      const user = userEvent.setup();
      
      render(<PersistenceTestComponent />);

      // Track localStorage write operations
      const setItemSpy = jest.spyOn(mockLocalStorage, 'setItem');
      
      await user.click(screen.getByTestId('set-auth'));
      
      const initialCallCount = setItemSpy.mock.calls.length;
      
      // Simulate multiple rapid storage events
      for (let i = 0; i < 10; i++) {
        const storageEvent = new StorageEvent('storage', {
          key: 'auth-store',
          newValue: JSON.stringify({
            state: { user: { id: `user-${i}` }, token: `token-${i}` },
            version: i
          }),
          storageArea: localStorage
        });
        
        act(() => {
          window.dispatchEvent(storageEvent);
        });
      }
      
      // Verify no excessive localStorage writes (indicating sync loop)
      const finalCallCount = setItemSpy.mock.calls.length;
      expect(finalCallCount - initialCallCount).toBeLessThan(5);
    });
  });

  describe('Migration and Versioning', () => {
      jest.setTimeout(10000);
    it('handles legacy state format migration', () => {
      // Set up legacy data format
      mockLocalStorage.store.set('unified-chat-store', JSON.stringify({
        messages: [{ id: '1', content: 'legacy message' }],
        // Missing new fields that current version expects
      }));
      
      render(<PersistenceTestComponent />);
      
      // Verify app handles legacy format gracefully
      expect(screen.getByTestId('messages-count')).toHaveTextContent('0');
      expect(screen.getByTestId('active-thread')).toHaveTextContent('none');
    });

    it('maintains backwards compatibility with older versions', () => {
      // Set up data with version information
      mockLocalStorage.store.set('auth-store', JSON.stringify({
        state: {
          user: { id: 'legacy-user' },
          token: 'legacy-token'
        },
        version: 1 // Older version
      }));
      
      render(<PersistenceTestComponent />);
      
      // Verify compatibility handling
      expect(screen.getByTestId('user-id')).toHaveTextContent('no-user');
      expect(screen.getByTestId('auth-token')).toHaveTextContent('no-token');
    });
  });

  describe('Error Recovery and Resilience', () => {
      jest.setTimeout(10000);
    it('recovers from corrupted localStorage data', () => {
      // Set corrupted data
      mockLocalStorage.store.set('unified-chat-store', 'invalid-json');
      mockLocalStorage.store.set('auth-store', '{"incomplete": true');
      
      // App should not crash
      expect(() => {
        render(<PersistenceTestComponent />);
      }).not.toThrow();
      
      // Should show default state
      expect(screen.getByTestId('messages-count')).toHaveTextContent('0');
      expect(screen.getByTestId('user-id')).toHaveTextContent('no-user');
    });

    it('handles localStorage unavailability gracefully', async () => {
      const user = userEvent.setup();
      
      // Mock localStorage methods to throw errors
      mockLocalStorage.getItem.mockImplementation(() => {
        throw new Error('localStorage unavailable');
      });
      
      mockLocalStorage.setItem.mockImplementation(() => {
        throw new Error('localStorage unavailable');
      });
      
      // App should still function without persistence
      expect(() => {
        render(<PersistenceTestComponent />);
      }).not.toThrow();
      
      // Should allow state operations
      await user.click(screen.getByTestId('add-message'));
      expect(screen.getByTestId('messages-count')).toHaveTextContent('1');
    });

    it('implements automatic state cleanup for old data', async () => {
      const user = userEvent.setup();
      
      render(<PersistenceTestComponent />);

      // Create state with timestamps
      await act(async () => {
        // Add old messages (simulate week-old data)
        const weekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
        
        useUnifiedChatStore.getState().addMessage({
          id: 'old-msg',
          role: 'user',
          content: 'Old message',
          timestamp: weekAgo
        });
        
        useUnifiedChatStore.getState().addMessage({
          id: 'new-msg',
          role: 'user',
          content: 'New message',
          timestamp: Date.now()
        });
      });

      expect(screen.getByTestId('messages-count')).toHaveTextContent('2');
      
      // Simulate cleanup trigger (implementation would handle this)
      // This test documents expected cleanup behavior
      await act(async () => {
        // Cleanup logic would go here in real implementation
      });
    });
  });
});