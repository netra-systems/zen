/**
 * Enhanced Offline Mode Integration Tests
 * Tests comprehensive offline/online transitions with data persistence
 * Ensures no data loss and graceful feature degradation
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import WS from 'jest-websocket-mock';
import { TestProviders } from '../setup/test-providers';
import * from '@/__tests__/helpers/websocket-test-manager';

// Mock dependencies
jest.mock('@/services/webSocketService');
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:3000/api',
    offlineStorageKey: 'netra_offline_data'
  }
}));

interface OfflineAction {
  id: string;
  type: string;
  data: any;
  timestamp: number;
  retries: number;
}

interface OfflineState {
  isOnline: boolean;
  queuedActions: OfflineAction[];
  syncStatus: 'idle' | 'syncing' | 'error';
  lastSyncTime: number | null;
}

interface CachedData {
  conversations: Array<{ id: string; title: string; messages: any[] }>;
  userPreferences: Record<string, any>;
  draftMessages: Record<string, string>;
  timestamp: number;
}

const createOfflineAction = (type: string, data: any): OfflineAction => ({
  id: Math.random().toString(36).substr(2, 9),
  type,
  data,
  timestamp: Date.now(),
  retries: 0
});

const getStoredData = (): CachedData | null => {
  try {
    const stored = localStorage.getItem('netra_offline_data');
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
};

const storeData = (data: CachedData): void => {
  try {
    localStorage.setItem('netra_offline_data', JSON.stringify(data));
  } catch (error) {
    console.warn('Failed to store offline data:', error);
  }
};

const OfflineModeComponent: React.FC = () => {
  const [state, setState] = React.useState<OfflineState>({
    isOnline: navigator.onLine,
    queuedActions: [],
    syncStatus: 'idle',
    lastSyncTime: null
  });
  
  const [cachedConversations, setCachedConversations] = React.useState<Array<{id: string, title: string}>>([]);
  const [currentDraft, setCurrentDraft] = React.useState('');
  const [notificationQueue, setNotificationQueue] = React.useState<string[]>([]);

  // Network status monitoring
  React.useEffect(() => {
    const handleOnline = () => {
      setState(prev => ({ ...prev, isOnline: true }));
      // Trigger sync after state update
      setTimeout(() => syncQueuedActions(), 0);
    };
    
    const handleOffline = () => {
      setState(prev => ({ ...prev, isOnline: false }));
      showOfflineNotification();
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Load cached data on mount
  React.useEffect(() => {
    const cached = getStoredData();
    if (cached) {
      setCachedConversations(cached.conversations.map(c => ({ id: c.id, title: c.title })));
    }
  }, []);

  const showOfflineNotification = () => {
    setNotificationQueue(prev => [...prev, 'You are now offline. Changes will be saved locally.']);
  };

  const queueAction = (type: string, data: any) => {
    const action = createOfflineAction(type, data);
    setState(prev => ({
      ...prev,
      queuedActions: [...prev.queuedActions, action]
    }));
    
    // Store in localStorage for persistence
    const currentQueue = JSON.parse(localStorage.getItem('offline_queue') || '[]');
    localStorage.setItem('offline_queue', JSON.stringify([...currentQueue, action]));
  };

  const syncQueuedActions = async () => {
    if (state.queuedActions.length === 0) return;
    
    setState(prev => ({ ...prev, syncStatus: 'syncing' }));
    
    try {
      // Simulate sync delay
      await new Promise(resolve => setTimeout(resolve, 100));
      
      setState(prev => ({
        ...prev,
        queuedActions: [],
        syncStatus: 'idle',
        lastSyncTime: Date.now()
      }));
      
      localStorage.removeItem('offline_queue');
      setNotificationQueue(prev => [...prev, 'All changes synced successfully']);
    } catch (error) {
      setState(prev => ({ ...prev, syncStatus: 'error' }));
      setNotificationQueue(prev => [...prev, 'Sync failed. Will retry automatically.']);
    }
  };

  const createConversation = (title: string) => {
    const conversation = {
      id: Math.random().toString(36).substr(2, 9),
      title,
      timestamp: Date.now()
    };
    
    if (state.isOnline) {
      // Online: simulate API call
      setCachedConversations(prev => [...prev, conversation]);
    } else {
      // Offline: cache locally and queue for sync
      setCachedConversations(prev => [...prev, conversation]);
      queueAction('create_conversation', conversation);
      
      // Update cached data
      const cached = getStoredData() || { conversations: [], userPreferences: {}, draftMessages: {}, timestamp: Date.now() };
      cached.conversations.push({ ...conversation, messages: [] });
      storeData(cached);
    }
  };

  const sendMessage = (content: string) => {
    const message = {
      id: Math.random().toString(36).substr(2, 9),
      content,
      timestamp: Date.now()
    };
    
    if (state.isOnline) {
      // Online: simulate immediate send
      // No additional action needed for test
    } else {
      // Offline: queue for later
      queueAction('send_message', message);
    }
    
    setCurrentDraft('');
  };

  const saveDraft = (content: string) => {
    setCurrentDraft(content);
    
    // Always save drafts locally
    const cached = getStoredData() || { conversations: [], userPreferences: {}, draftMessages: {}, timestamp: Date.now() };
    cached.draftMessages['current'] = content;
    storeData(cached);
  };

  const clearNotification = (index: number) => {
    setNotificationQueue(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div>
      {/* Connection Status */}
      <div data-testid="connection-status">
        Status: {state.isOnline ? 'Online' : 'Offline'}
      </div>
      
      {/* Sync Status */}
      <div data-testid="sync-status">
        Sync: {state.syncStatus}
      </div>
      
      {/* Queue Status */}
      <div data-testid="queue-status">
        Queued: {state.queuedActions.length} actions
      </div>
      
      {/* Last Sync Time */}
      {state.lastSyncTime && (
        <div data-testid="last-sync">
          Last sync: {new Date(state.lastSyncTime).toLocaleTimeString()}
        </div>
      )}
      
      {/* Notifications */}
      <div data-testid="notifications">
        {notificationQueue.map((notification, index) => (
          <div key={index} data-testid={`notification-${index}`}>
            {notification}
            <button onClick={() => clearNotification(index)}>×</button>
          </div>
        ))}
      </div>
      
      {/* Actions */}
      <div>
        <input
          type="text"
          placeholder="Conversation title"
          data-testid="title-input"
        />
        <button 
          onClick={() => {
            const input = screen.getByTestId('title-input') as HTMLInputElement;
            createConversation(input.value);
            input.value = '';
          }}
          data-testid="create-conversation-btn"
        >
          Create Conversation
        </button>
      </div>
      
      <div>
        <textarea
          value={currentDraft}
          onChange={(e) => saveDraft(e.target.value)}
          placeholder="Type your message..."
          data-testid="message-input"
        />
        <button 
          onClick={() => sendMessage(currentDraft)}
          disabled={!currentDraft.trim()}
          data-testid="send-message-btn"
        >
          Send Message
        </button>
      </div>
      
      {/* Manual Sync */}
      <button 
        onClick={syncQueuedActions}
        disabled={state.syncStatus === 'syncing' || state.queuedActions.length === 0}
        data-testid="manual-sync-btn"
      >
        Manual Sync
      </button>
      
      {/* Cached Conversations */}
      <div data-testid="conversation-list">
        <h3>Conversations ({cachedConversations.length})</h3>
        {cachedConversations.map((conv, index) => (
          <div key={conv.id} data-testid={`conversation-${index}`}>
            {conv.title}
          </div>
        ))}
      </div>
    </div>
  );
};

const OfflineStorageComponent: React.FC = () => {
  const [storedData, setStoredData] = React.useState<any>(null);
  const [storageQuota, setStorageQuota] = React.useState<{used: number, available: number} | null>(null);

  React.useEffect(() => {
    // Load existing data
    const data = getStoredData();
    setStoredData(data);
    
    // Check storage quota (if available)
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      navigator.storage.estimate().then(estimate => {
        setStorageQuota({
          used: estimate.usage || 0,
          available: estimate.quota || 0
        });
      });
    }
  }, []);

  const addTestData = () => {
    const testData: CachedData = {
      conversations: [
        {
          id: '1',
          title: 'Test Conversation',
          messages: [{ id: 'm1', content: 'Hello', timestamp: Date.now() }]
        }
      ],
      userPreferences: { theme: 'dark', language: 'en' },
      draftMessages: { draft1: 'Draft message' },
      timestamp: Date.now()
    };
    
    storeData(testData);
    setStoredData(testData);
  };

  const clearStorage = () => {
    localStorage.removeItem('netra_offline_data');
    setStoredData(null);
  };

  const exportData = () => {
    const data = getStoredData();
    if (data) {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'offline-data.json';
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div>
      <div data-testid="storage-status">
        Data stored: {storedData ? 'Yes' : 'No'}
      </div>
      
      {storageQuota && (
        <div data-testid="storage-quota">
          Storage: {Math.round(storageQuota.used / 1024)}KB / {Math.round(storageQuota.available / 1024 / 1024)}MB
        </div>
      )}
      
      {storedData && (
        <div data-testid="stored-data">
          <div>Conversations: {storedData.conversations?.length || 0}</div>
          <div>Preferences: {Object.keys(storedData.userPreferences || {}).length} items</div>
          <div>Drafts: {Object.keys(storedData.draftMessages || {}).length} items</div>
        </div>
      )}
      
      <button onClick={addTestData} data-testid="add-test-data-btn">
        Add Test Data
      </button>
      
      <button onClick={clearStorage} data-testid="clear-storage-btn">
        Clear Storage
      </button>
      
      <button onClick={exportData} data-testid="export-data-btn">
        Export Data
      </button>
    </div>
  );
};

const NetworkDetectionComponent: React.FC = () => {
  const [networkState, setNetworkState] = React.useState({
    isOnline: navigator.onLine,
    connectionType: 'unknown',
    downlink: 0,
    rtt: 0
  });

  React.useEffect(() => {
    const updateNetworkStatus = () => {
      const connection = (navigator as any).connection || (navigator as any).mozConnection || (navigator as any).webkitConnection;
      
      setNetworkState({
        isOnline: navigator.onLine,
        connectionType: connection?.effectiveType || 'unknown',
        downlink: connection?.downlink || 0,
        rtt: connection?.rtt || 0
      });
    };

    updateNetworkStatus();
    
    window.addEventListener('online', updateNetworkStatus);
    window.addEventListener('offline', updateNetworkStatus);
    
    const connection = (navigator as any).connection;
    if (connection) {
      connection.addEventListener('change', updateNetworkStatus);
    }
    
    return () => {
      window.removeEventListener('online', updateNetworkStatus);
      window.removeEventListener('offline', updateNetworkStatus);
      if (connection) {
        connection.removeEventListener('change', updateNetworkStatus);
      }
    };
  }, []);

  return (
    <div>
      <div data-testid="network-online">
        Online: {networkState.isOnline ? 'Yes' : 'No'}
      </div>
      
      <div data-testid="connection-type">
        Connection: {networkState.connectionType}
      </div>
      
      {networkState.downlink > 0 && (
        <div data-testid="network-speed">
          Speed: {networkState.downlink} Mbps
        </div>
      )}
      
      {networkState.rtt > 0 && (
        <div data-testid="network-latency">
          Latency: {networkState.rtt}ms
        </div>
      )}
    </div>
  );
};

describe('Enhanced Offline Mode Tests', () => {
  let wsManager: WebSocketTestManager;
  let mockFetch: jest.MockedFunction<typeof fetch>;

  beforeEach(() => {
    wsManager = new WebSocketTestManager();
    wsManager.setup();
    
    // Mock fetch
    mockFetch = jest.fn() as jest.MockedFunction<typeof fetch>;
    global.fetch = mockFetch;
    
    // Clear localStorage
    localStorage.clear();
    
    // Mock navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true
    });
    
    jest.useFakeTimers();
  });

  afterEach(() => {
    wsManager.cleanup();
    jest.clearAllMocks();
    jest.useRealTimers();
    localStorage.clear();
  });

  describe('Offline/Online Transitions', () => {
    it('should detect offline/online status changes', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <OfflineModeComponent />
        </TestProviders>
      );

      // Initially online
      expect(screen.getByTestId('connection-status')).toHaveTextContent('Online');

      // Go offline
      Object.defineProperty(navigator, 'onLine', { value: false });
      act(() => {
        window.dispatchEvent(new Event('offline'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('Offline');
        expect(screen.getByTestId('notification-0')).toHaveTextContent('You are now offline');
      });

      // Go back online
      Object.defineProperty(navigator, 'onLine', { value: true });
      act(() => {
        window.dispatchEvent(new Event('online'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('Online');
      });
    });

    it('should queue actions when offline and sync when online', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true })
      } as Response);
      
      render(
        <TestProviders>
          <OfflineModeComponent />
        </TestProviders>
      );

      // Go offline
      Object.defineProperty(navigator, 'onLine', { value: false });
      act(() => {
        window.dispatchEvent(new Event('offline'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('Offline');
      });

      // Create conversation while offline
      await user.type(screen.getByTestId('title-input'), 'Offline Conversation');
      await user.click(screen.getByTestId('create-conversation-btn'));

      await waitFor(() => {
        expect(screen.getByTestId('queue-status')).toHaveTextContent('1 actions');
        expect(screen.getByTestId('conversation-0')).toHaveTextContent('Offline Conversation');
      });

      // Go back online
      Object.defineProperty(navigator, 'onLine', { value: true });
      act(() => {
        window.dispatchEvent(new Event('online'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('sync-status')).toHaveTextContent('syncing');
      });

      // Wait for sync to complete
      await waitFor(() => {
        expect(screen.getByTestId('sync-status')).toHaveTextContent('idle');
        expect(screen.getByTestId('queue-status')).toHaveTextContent('0 actions');
      });
    });
  });

  describe('Data Persistence', () => {
    it('should persist offline data in localStorage', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <OfflineStorageComponent />
        </TestProviders>
      );

      // Initially no data
      expect(screen.getByTestId('storage-status')).toHaveTextContent('No');

      // Add test data
      await user.click(screen.getByTestId('add-test-data-btn'));

      await waitFor(() => {
        expect(screen.getByTestId('storage-status')).toHaveTextContent('Yes');
        expect(screen.getByTestId('stored-data')).toBeInTheDocument();
      });

      // Verify data structure
      expect(screen.getByText('Conversations: 1')).toBeInTheDocument();
      expect(screen.getByText('Preferences: 2 items')).toBeInTheDocument();
      expect(screen.getByText('Drafts: 1 items')).toBeInTheDocument();
    });

    it('should restore data after page refresh', async () => {
      // Add data first
      const testData: CachedData = {
        conversations: [{ id: '1', title: 'Persisted Conversation', messages: [] }],
        userPreferences: { theme: 'dark' },
        draftMessages: { draft1: 'Persisted draft' },
        timestamp: Date.now()
      };
      
      storeData(testData);

      // Render component (simulating page refresh)
      render(
        <TestProviders>
          <OfflineModeComponent />
        </TestProviders>
      );

      // Should restore cached conversations
      await waitFor(() => {
        expect(screen.getByText('Conversations (1)')).toBeInTheDocument();
        expect(screen.getByTestId('conversation-0')).toHaveTextContent('Persisted Conversation');
      });
    });
  });

  describe('Draft Message Persistence', () => {
    it('should save and restore draft messages', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <OfflineModeComponent />
        </TestProviders>
      );

      // Type a draft message
      await user.type(screen.getByTestId('message-input'), 'This is a draft');

      // Verify draft is saved
      const cached = getStoredData();
      expect(cached?.draftMessages.current).toBe('This is a draft');

      // Send button should be enabled
      expect(screen.getByTestId('send-message-btn')).toBeEnabled();
    });

    it('should clear draft after sending message', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true })
      } as Response);
      
      render(
        <TestProviders>
          <OfflineModeComponent />
        </TestProviders>
      );

      // Type and send message
      await user.type(screen.getByTestId('message-input'), 'Hello World');
      await user.click(screen.getByTestId('send-message-btn'));

      // Draft should be cleared
      await waitFor(() => {
        expect(screen.getByTestId('message-input')).toHaveValue('');
      });
    });
  });

  describe('Network Quality Detection', () => {
    it('should detect network connection type and quality', async () => {
      // Mock connection API
      Object.defineProperty(navigator, 'connection', {
        value: {
          effectiveType: '4g',
          downlink: 10,
          rtt: 100,
          addEventListener: jest.fn(),
          removeEventListener: jest.fn()
        },
        writable: true
      });
      
      render(
        <TestProviders>
          <NetworkDetectionComponent />
        </TestProviders>
      );

      expect(screen.getByTestId('network-online')).toHaveTextContent('Yes');
      expect(screen.getByTestId('connection-type')).toHaveTextContent('4g');
      expect(screen.getByTestId('network-speed')).toHaveTextContent('10 Mbps');
      expect(screen.getByTestId('network-latency')).toHaveTextContent('100ms');
    });
  });

  describe('Storage Management', () => {
    it('should handle storage quota limits gracefully', async () => {
      // Mock storage API
      Object.defineProperty(navigator, 'storage', {
        value: {
          estimate: jest.fn().mockResolvedValue({
            usage: 50000, // 50KB
            quota: 5000000 // 5MB
          })
        },
        writable: true
      });
      
      render(
        <TestProviders>
          <OfflineStorageComponent />
        </TestProviders>
      );

      await waitFor(() => {
        expect(screen.getByTestId('storage-quota')).toHaveTextContent('49KB / 5MB');
      });
    });

    it('should export offline data for backup', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      // Mock URL.createObjectURL
      const mockCreateObjectURL = jest.fn().mockReturnValue('blob:mock-url');
      const mockRevokeObjectURL = jest.fn();
      Object.defineProperty(URL, 'createObjectURL', { value: mockCreateObjectURL });
      Object.defineProperty(URL, 'revokeObjectURL', { value: mockRevokeObjectURL });
      
      render(
        <TestProviders>
          <OfflineStorageComponent />
        </TestProviders>
      );

      // Add test data
      await user.click(screen.getByTestId('add-test-data-btn'));
      
      // Export data
      await user.click(screen.getByTestId('export-data-btn'));
      
      expect(mockCreateObjectURL).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should handle localStorage failures gracefully', async () => {
      // Mock localStorage to throw error
      const originalSetItem = localStorage.setItem;
      localStorage.setItem = jest.fn().mockImplementation(() => {
        throw new Error('Storage quota exceeded');
      });
      
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <TestProviders>
          <OfflineModeComponent />
        </TestProviders>
      );

      // Go offline and try to create conversation
      Object.defineProperty(navigator, 'onLine', { value: false });
      act(() => {
        window.dispatchEvent(new Event('offline'));
      });

      await user.type(screen.getByTestId('title-input'), 'Test Conversation');
      await user.click(screen.getByTestId('create-conversation-btn'));

      // Should still queue action even if storage fails
      await waitFor(() => {
        expect(screen.getByTestId('queue-status')).toHaveTextContent('1 actions');
      });
      
      // Restore localStorage
      localStorage.setItem = originalSetItem;
    });

    it('should handle sync failures with retry', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      // Mock fetch to fail
      mockFetch.mockRejectedValue(new Error('Network error'));
      
      render(
        <TestProviders>
          <OfflineModeComponent />
        </TestProviders>
      );

      // Go offline, create action, then go online
      Object.defineProperty(navigator, 'onLine', { value: false });
      act(() => {
        window.dispatchEvent(new Event('offline'));
      });

      await user.type(screen.getByTestId('title-input'), 'Test');
      await user.click(screen.getByTestId('create-conversation-btn'));

      Object.defineProperty(navigator, 'onLine', { value: true });
      act(() => {
        window.dispatchEvent(new Event('online'));
      });

      // Should show sync error
      await waitFor(() => {
        expect(screen.getByTestId('sync-status')).toHaveTextContent('error');
        expect(screen.getByText(/Sync failed/)).toBeInTheDocument();
      });

      // Actions should remain queued
      expect(screen.getByTestId('queue-status')).toHaveTextContent('1 actions');
    });
  });

  describe('Manual Sync Operations', () => {
    it('should allow manual sync when online', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true })
      } as Response);
      
      render(
        <TestProviders>
          <OfflineModeComponent />
        </TestProviders>
      );

      // Create some queued actions while offline
      Object.defineProperty(navigator, 'onLine', { value: false });
      act(() => {
        window.dispatchEvent(new Event('offline'));
      });

      await user.type(screen.getByTestId('title-input'), 'Manual Sync Test');
      await user.click(screen.getByTestId('create-conversation-btn'));

      // Go back online
      Object.defineProperty(navigator, 'onLine', { value: true });
      act(() => {
        window.dispatchEvent(new Event('online'));
      });

      // Wait for auto-sync to complete
      await waitFor(() => {
        expect(screen.getByTestId('sync-status')).toHaveTextContent('idle');
      });

      // Manual sync button should be disabled (no actions to sync)
      expect(screen.getByTestId('manual-sync-btn')).toBeDisabled();
    });
  });
});
