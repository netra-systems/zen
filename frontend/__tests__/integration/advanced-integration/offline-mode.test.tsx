import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import WS from 'jest-websocket-mock';
import { safeWebSocketCleanup } from '../../helpers/websocket-test-manager';
import { setupTestEnvironment } from './test-setup';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
etupTestEnvironment } from './test-setup';

describe('Advanced Frontend Integration Tests - Offline Mode', () => {
    jest.setTimeout(10000);
  let server: WS;
  
  setupTestEnvironment();

  beforeEach(() => {
    server = new WS('ws://localhost:8000/ws');
  });

  afterEach(() => {
    safeWebSocketCleanup();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('19. Offline Mode Integration', () => {
      jest.setTimeout(10000);
    it('should queue actions when offline and sync when online', async () => {
      const actionQueue: any[] = [];
      
      const OfflineSyncComponent = () => {
        const [isOnline, setIsOnline] = React.useState(navigator.onLine);
        const [queuedActions, setQueuedActions] = React.useState<any[]>([]);
        
        React.useEffect(() => {
          const handleOnline = () => {
            setIsOnline(true);
            // Sync queued actions
            queuedActions.forEach(action => {
              fetch('/api/sync', {
                method: 'POST',
                body: JSON.stringify(action)
              });
            });
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
            <button onClick={() => performAction({ type: 'test' })}>
              Perform Action
            </button>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<OfflineSyncComponent />);
      
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
      
      // Perform action while offline
      fireEvent.click(getByText('Perform Action'));
      
      await waitFor(() => {
        expect(getByTestId('queue-size')).toHaveTextContent('1 queued');
      });
      
      // Go back online
      Object.defineProperty(navigator, 'onLine', { value: true });
      act(() => {
        window.dispatchEvent(new Event('online'));
      });
      
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({})
      });
      
      await waitFor(() => {
        expect(getByTestId('status')).toHaveTextContent('Online');
        expect(getByTestId('queue-size')).toHaveTextContent('0 queued');
      });
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
        
        return (
          <div>
            <button onClick={() => saveOffline({ id: Date.now(), text: 'Test' })}>
              Save Offline
            </button>
            <div data-testid="item-count">{data.length} items</div>
          </div>
        );
      };
      
      const { getByText, getByTestId, unmount } = render(<OfflineStorageComponent />);
      
      fireEvent.click(getByText('Save Offline'));
      
      await waitFor(() => {
        expect(getByTestId('item-count')).toHaveTextContent('1 items');
      });
      
      // Unmount and remount to simulate page refresh
      unmount();
      const { getByTestId: getByTestIdNew } = render(<OfflineStorageComponent />);
      
      // Should restore from local storage
      expect(getByTestIdNew('item-count')).toHaveTextContent('1 items');
    });
  });
});