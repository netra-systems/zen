/**
 * Offline Mode and Navigation Integration Tests
 * Tests for offline functionality and complex navigation flows
 */

import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react';
import { createTestSetup, mockFetch } from './setup';
import { useAuthStore } from '@/store/authStore';

describe('Offline Mode and Navigation Integration', () => {
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
  });

  describe('Offline Mode', () => {
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
      
      mockFetch({});
      
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

  describe('Complex Navigation Flows', () => {
    it('should handle deep linking with state preservation', async () => {
      const router = require('next/navigation').useRouter();
      
      const NavigationComponent = () => {
        const [navigationStack, setNavigationStack] = React.useState<string[]>(['/']);
        
        const navigateTo = (path: string, preserveState = true) => {
          if (preserveState) {
            sessionStorage.setItem('nav_state', JSON.stringify({
              from: navigationStack[navigationStack.length - 1],
              timestamp: Date.now()
            }));
          }
          
          setNavigationStack(prev => [...prev, path]);
          router.push(path);
        };
        
        const goBack = () => {
          if (navigationStack.length > 1) {
            const newStack = [...navigationStack];
            newStack.pop();
            setNavigationStack(newStack);
            router.back();
          }
        };
        
        return (
          <div>
            <div data-testid="current-path">
              {navigationStack[navigationStack.length - 1]}
            </div>
            <div data-testid="stack-depth">{navigationStack.length}</div>
            <button onClick={() => navigateTo('/chat/thread-1')}>Go to Thread</button>
            <button onClick={goBack}>Back</button>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<NavigationComponent />);
      
      expect(getByTestId('current-path')).toHaveTextContent('/');
      
      fireEvent.click(getByText('Go to Thread'));
      
      await waitFor(() => {
        expect(getByTestId('current-path')).toHaveTextContent('/chat/thread-1');
        expect(getByTestId('stack-depth')).toHaveTextContent('2');
      });
      
      // Verify state was preserved
      const savedState = JSON.parse(sessionStorage.getItem('nav_state') || '{}');
      expect(savedState.from).toBe('/');
    });

    it('should handle protected route redirects', async () => {
      const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
        const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
        const router = require('next/navigation').useRouter();
        
        React.useEffect(() => {
          if (!isAuthenticated) {
            // Save intended destination
            sessionStorage.setItem('redirect_after_login', window.location.pathname);
            router.push('/auth/login');
          }
        }, [isAuthenticated, router]);
        
        if (!isAuthenticated) {
          return <div>Redirecting to login...</div>;
        }
        
        return <>{children}</>;
      };
      
      const TestComponent = () => {
        return (
          <ProtectedRoute>
            <div data-testid="protected-content">Protected Content</div>
          </ProtectedRoute>
        );
      };
      
      // Test unauthenticated access
      const { getByText, getByTestId, rerender } = render(<TestComponent />);
      
      expect(getByText('Redirecting to login...')).toBeInTheDocument();
      expect(sessionStorage.getItem('redirect_after_login')).toBe('/');
      
      // Authenticate and rerender
      act(() => {
        useAuthStore.setState({ isAuthenticated: true, user: { id: '1', email: 'test@example.com' } });
      });
      
      rerender(<TestComponent />);
      
      await waitFor(() => {
        expect(getByTestId('protected-content')).toBeInTheDocument();
      });
    });

    it('should handle navigation with query parameters', async () => {
      const QueryNavigationComponent = () => {
        const [searchParams, setSearchParams] = React.useState(new URLSearchParams());
        const [filters, setFilters] = React.useState({
          category: '',
          sort: 'date',
          page: 1
        });
        
        React.useEffect(() => {
          const params = new URLSearchParams();
          Object.entries(filters).forEach(([key, value]) => {
            if (value) params.set(key, value.toString());
          });
          setSearchParams(params);
        }, [filters]);
        
        const updateFilter = (key: string, value: string | number) => {
          setFilters(prev => ({ ...prev, [key]: value }));
        };
        
        return (
          <div>
            <div data-testid="query-string">{searchParams.toString()}</div>
            <select
              data-testid="select"
              value={filters.category}
              onChange={(e) => updateFilter('category', e.target.value)}
            >
              <option value="">All</option>
              <option value="tech">Tech</option>
              <option value="business">Business</option>
            </select>
            <button onClick={() => updateFilter('page', filters.page + 1)}>
              Next Page
            </button>
          </div>
        );
      };
      
      const { getByTestId } = render(<QueryNavigationComponent />);
      
      // Initial state should have default sort
      expect(getByTestId('query-string')).toHaveTextContent('sort=date&page=1');
      
      // Update category
      fireEvent.change(getByTestId('select'), { target: { value: 'tech' } });
      
      await waitFor(() => {
        expect(getByTestId('query-string').textContent).toContain('category=tech');
      });
    });
  });
});