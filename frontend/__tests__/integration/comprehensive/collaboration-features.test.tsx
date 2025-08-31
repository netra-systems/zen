import {
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
llaboration Features Integration Tests
 * 
 * Tests real-time cursor synchronization, presence awareness,
 * offline mode functionality, and collaborative editing features.
 */

import {
  React,
  render,
  waitFor,
  screen,
  fireEvent,
  act,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockWebSocketServer,
  createWebSocketMessage,
  simulateNetworkDelay,
  TEST_TIMEOUTS,
  WS
} from './test-utils';

// Apply Next.js navigation mock
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

describe('Collaboration Features Integration Tests', () => {
    jest.setTimeout(10000);
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Real-time Cursor Synchronization', () => {
      jest.setTimeout(10000);
    it('should sync cursor positions in real-time', async () => {
      const CollaborativeEditor = () => {
        const [otherCursors, setOtherCursors] = React.useState<Map<string, { x: number, y: number }>>(new Map());
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:3001/test'));
          
          ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'cursor_update') {
              setOtherCursors(prev => {
                const updated = new Map(prev);
                updated.set(message.userId, message.position);
                return updated;
              });
            }
          };
          
          const handleMouseMove = (e: MouseEvent) => {
            ws.send(JSON.stringify({
              type: 'cursor_move',
              position: { x: e.clientX, y: e.clientY }
            }));
          };
          
          document.addEventListener('mousemove', handleMouseMove);
          
          return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            ws.close();
          };
        }, []);
        
        return (
          <div>
            {Array.from(otherCursors.entries()).map(([userId, pos]) => (
              <div key={userId} data-testid={`cursor-${userId}`}>
                User {userId}: {pos.x}, {pos.y}
              </div>
            ))}
          </div>
        );
      };
      
      render(<CollaborativeEditor />);
      
      await server.connected;
      
      // Simulate another user's cursor
      server.send(createWebSocketMessage('cursor_update', {
        userId: 'user-2',
        position: { x: 100, y: 200 }
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('cursor-user-2')).toHaveTextContent('User user-2: 100, 200');
      });
    });

    it('should handle multiple cursor updates efficiently', async () => {
      const MultiCursorComponent = () => {
        const [cursors, setCursors] = React.useState<Map<string, any>>(new Map());
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:3001/test'));
          
          ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'multi_cursor_update') {
              setCursors(new Map(Object.entries(message.cursors)));
            }
          };
          
          return () => ws.close();
        }, []);
        
        return (
          <div data-testid="cursor-container">
            {Array.from(cursors.entries()).map(([userId, cursor]) => (
              <div key={userId} data-testid={`cursor-${userId}`}>
                {cursor.name}: {cursor.x},{cursor.y}
              </div>
            ))}
          </div>
        );
      };
      
      render(<MultiCursorComponent />);
      
      await server.connected;
      
      // Send multiple cursor updates
      server.send(createWebSocketMessage('multi_cursor_update', {
        cursors: {
          'user-1': { name: 'Alice', x: 50, y: 75 },
          'user-2': { name: 'Bob', x: 150, y: 200 },
          'user-3': { name: 'Charlie', x: 300, y: 400 }
        }
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('cursor-user-1')).toHaveTextContent('Alice: 50,75');
        expect(screen.getByTestId('cursor-user-2')).toHaveTextContent('Bob: 150,200');
        expect(screen.getByTestId('cursor-user-3')).toHaveTextContent('Charlie: 300,400');
      });
    });
  });

  describe('Presence and Activity Status', () => {
      jest.setTimeout(10000);
    it('should handle presence and activity status', async () => {
      const PresenceComponent = () => {
        const [activeUsers, setActiveUsers] = React.useState<Set<string>>(new Set());
        const [typingUsers, setTypingUsers] = React.useState<Set<string>>(new Set());
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:3001/test'));
          
          ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'user_joined') {
              setActiveUsers(prev => new Set(prev).add(message.userId));
            } else if (message.type === 'user_left') {
              setActiveUsers(prev => {
                const updated = new Set(prev);
                updated.delete(message.userId);
                return updated;
              });
            } else if (message.type === 'typing_start') {
              setTypingUsers(prev => new Set(prev).add(message.userId));
            } else if (message.type === 'typing_stop') {
              setTypingUsers(prev => {
                const updated = new Set(prev);
                updated.delete(message.userId);
                return updated;
              });
            }
          };
          
          return () => ws.close();
        }, []);
        
        return (
          <div>
            <div data-testid="active-count">{activeUsers.size} users online</div>
            <div data-testid="typing-count">{typingUsers.size} users typing</div>
          </div>
        );
      };
      
      render(<PresenceComponent />);
      
      await server.connected;
      
      // Simulate users joining
      server.send(createWebSocketMessage('user_joined', { userId: 'user-1' }));
      server.send(createWebSocketMessage('user_joined', { userId: 'user-2' }));
      
      await waitFor(() => {
        expect(screen.getByTestId('active-count')).toHaveTextContent('2 users online');
      });
      
      // Simulate typing
      server.send(createWebSocketMessage('typing_start', { userId: 'user-1' }));
      
      await waitFor(() => {
        expect(screen.getByTestId('typing-count')).toHaveTextContent('1 users typing');
      });

      // Stop typing
      server.send(createWebSocketMessage('typing_stop', { userId: 'user-1' }));
      
      await waitFor(() => {
        expect(screen.getByTestId('typing-count')).toHaveTextContent('0 users typing');
      });
      
      // User leaves
      server.send(createWebSocketMessage('user_left', { userId: 'user-2' }));
      
      await waitFor(() => {
        expect(screen.getByTestId('active-count')).toHaveTextContent('1 users online');
      });
    });

    it('should handle user status with detailed information', async () => {
      const DetailedPresenceComponent = () => {
        const [users, setUsers] = React.useState<Map<string, any>>(new Map());
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:3001/test'));
          
          ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'user_status_update') {
              setUsers(prev => {
                const updated = new Map(prev);
                updated.set(message.userId, message.status);
                return updated;
              });
            }
          };
          
          return () => ws.close();
        }, []);
        
        return (
          <div>
            {Array.from(users.entries()).map(([userId, status]) => (
              <div key={userId} data-testid={`user-${userId}`}>
                {status.name} - {status.activity} ({status.lastSeen})
              </div>
            ))}
          </div>
        );
      };
      
      render(<DetailedPresenceComponent />);
      
      await server.connected;
      
      server.send(createWebSocketMessage('user_status_update', {
        userId: 'user-1',
        status: {
          name: 'Alice',
          activity: 'editing',
          lastSeen: '2 minutes ago'
        }
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('user-user-1')).toHaveTextContent('Alice - editing (2 minutes ago)');
      });
    });
  });

  describe('Offline Mode Integration', () => {
      jest.setTimeout(10000);
    it('should queue actions when offline and sync when online', async () => {
      const OfflineSyncComponent = () => {
        const [isOnline, setIsOnline] = React.useState(navigator.onLine);
        const [queuedActions, setQueuedActions] = React.useState<any[]>([]);
        
        React.useEffect(() => {
          const handleOnline = async () => {
            setIsOnline(true);
            // Sync queued actions
            for (const action of queuedActions) {
              await fetch('/api/sync', {
                method: 'POST',
                body: JSON.stringify(action)
              });
            }
            setQueuedActions([]);
          };
          
          const handleOffline = () => setIsOnline(false);
          
          window.addEventListener('online', handleOnline);
          window.addEventListener('offline', handleOffline);
          
          return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
          };
        }, [queuedActions]);
        
        const performAction = (action: any) => {
          if (isOnline) {
            fetch('/api/action', {
              method: 'POST',
              body: JSON.stringify(action)
            });
          } else {
            setQueuedActions(prev => [...prev, action]);
          }
        };
        
        return (
          <div>
            <div data-testid="status">{isOnline ? 'Online' : 'Offline'}</div>
            <div data-testid="queue-size">{queuedActions.length} queued</div>
            <button onClick={() => performAction({ type: 'test', id: Date.now() })}>
              Perform Action
            </button>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<OfflineSyncComponent />);
      
      // Mock fetch
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({})
      });
      
      // Simulate going offline
      Object.defineProperty(navigator, 'onLine', {
        writable: true,
        value: false
      });
      act(() => {
        window.dispatchEvent(new Event('offline'));
      });
      
      await waitFor(() => {
        expect(getByTestId('status')).toHaveTextContent('Offline');
      });
      
      // Perform actions while offline
      fireEvent.click(getByText('Perform Action'));
      fireEvent.click(getByText('Perform Action'));
      
      await waitFor(() => {
        expect(getByTestId('queue-size')).toHaveTextContent('2 queued');
      });
      
      // Go back online
      Object.defineProperty(navigator, 'onLine', { value: true });
      act(() => {
        window.dispatchEvent(new Event('online'));
      });
      
      await waitFor(() => {
        expect(getByTestId('status')).toHaveTextContent('Online');
        expect(getByTestId('queue-size')).toHaveTextContent('0 queued');
      }, { timeout: TEST_TIMEOUTS.MEDIUM });
    });

    it('should use local storage for offline persistence', async () => {
      const OfflineStorageComponent = () => {
        const [data, setData] = React.useState<any[]>([]);
        
        React.useEffect(() => {
          // Load from local storage on mount
          const saved = localStorage.getItem('offline_data');
          if (saved) {
            setData(JSON.parse(saved));
          }
        }, []);
        
        const saveOffline = (item: any) => {
          const updated = [...data, item];
          setData(updated);
          localStorage.setItem('offline_data', JSON.stringify(updated));
        };
        
        const clearOfflineData = () => {
          setData([]);
          localStorage.removeItem('offline_data');
        };
        
        return (
          <div>
            <button onClick={() => saveOffline({ id: Date.now(), text: 'Test Item' })}>
              Save Offline
            </button>
            <button onClick={clearOfflineData}>Clear Data</button>
            <div data-testid="item-count">{data.length} items</div>
            {data.map(item => (
              <div key={item.id} data-testid={`item-${item.id}`}>
                {item.text}
              </div>
            ))}
          </div>
        );
      };
      
      const { getByText, getByTestId, unmount } = render(<OfflineStorageComponent />);
      
      fireEvent.click(getByText('Save Offline'));
      
      await waitFor(() => {
        expect(getByTestId('item-count')).toHaveTextContent('1 items');
      });
      
      // Verify data persists in localStorage
      const storedData = localStorage.getItem('offline_data');
      expect(storedData).toBeTruthy();
      
      // Unmount and remount to simulate page refresh
      unmount();
      const { getByTestId: getByTestIdNew } = render(<OfflineStorageComponent />);
      
      // Should restore from local storage
      expect(getByTestIdNew('item-count')).toHaveTextContent('1 items');
    });

    it('should handle offline/online transitions gracefully', async () => {
      const NetworkStateComponent = () => {
        const [networkHistory, setNetworkHistory] = React.useState<string[]>([]);
        
        React.useEffect(() => {
          const logNetworkChange = (status: string) => {
            setNetworkHistory(prev => [...prev, `${status} at ${new Date().toISOString()}`]);
          };
          
          const handleOnline = () => logNetworkChange('Online');
          const handleOffline = () => logNetworkChange('Offline');
          
          window.addEventListener('online', handleOnline);
          window.addEventListener('offline', handleOffline);
          
          return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
          };
        }, []);
        
        return (
          <div>
            <div data-testid="history-count">{networkHistory.length} network events</div>
            {networkHistory.map((event, index) => (
              <div key={index} data-testid={`event-${index}`}>
                {event}
              </div>
            ))}
          </div>
        );
      };
      
      const { getByTestId } = render(<NetworkStateComponent />);
      
      // Simulate network state changes
      Object.defineProperty(navigator, 'onLine', { value: false });
      act(() => window.dispatchEvent(new Event('offline')));
      
      await waitFor(() => {
        expect(getByTestId('history-count')).toHaveTextContent('1 network events');
      });
      
      Object.defineProperty(navigator, 'onLine', { value: true });
      act(() => window.dispatchEvent(new Event('online')));
      
      await waitFor(() => {
        expect(getByTestId('history-count')).toHaveTextContent('2 network events');
      });
      
      // Verify events are recorded
      expect(getByTestId('event-0')).toHaveTextContent('Offline');
      expect(getByTestId('event-1')).toHaveTextContent('Online');
    });
  });
});