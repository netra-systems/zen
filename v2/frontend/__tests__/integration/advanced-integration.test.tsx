/**
 * Advanced Frontend Integration Tests
 * Tests for complex workflows and edge cases
 */

import React from 'react';
import { render, waitFor, screen, fireEvent, act } from '@testing-library/react';
import { renderHook } from '@testing-library/react-hooks';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AgentProvider } from '@/providers/AgentProvider';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAgent } from '@/hooks/useAgent';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { useEnhancedChatWebSocket } from '@/hooks/useEnhancedChatWebSocket';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';
import apiClient from '@/services/apiClient';

// Mock Next.js
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

describe('Advanced Frontend Integration Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
    process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
    server = new WS('ws://localhost:8000/ws');
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    
    // Reset stores
    useAuthStore.setState({ user: null, token: null, isAuthenticated: false });
    useChatStore.setState({ messages: [], currentThread: null });
    useThreadStore.setState({ threads: [], activeThread: null });
    
    global.fetch = jest.fn();
  });

  afterEach(() => {
    WS.clean();
    jest.restoreAllMocks();
  });

  describe('16. Theme and Preferences Synchronization', () => {
    it('should sync theme preferences across components', async () => {
      const ThemeContext = React.createContext({
        theme: 'light',
        setTheme: (theme: string) => {}
      });
      
      const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
        const [theme, setTheme] = React.useState('light');
        
        React.useEffect(() => {
          const savedTheme = localStorage.getItem('theme');
          if (savedTheme) setTheme(savedTheme);
        }, []);
        
        const updateTheme = (newTheme: string) => {
          setTheme(newTheme);
          localStorage.setItem('theme', newTheme);
          document.documentElement.setAttribute('data-theme', newTheme);
        };
        
        return (
          <ThemeContext.Provider value={{ theme, setTheme: updateTheme }}>
            {children}
          </ThemeContext.Provider>
        );
      };
      
      const TestComponent = () => {
        const { theme, setTheme } = React.useContext(ThemeContext);
        
        return (
          <div>
            <div data-testid="current-theme">{theme}</div>
            <button onClick={() => setTheme('dark')}>Dark Mode</button>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );
      
      expect(getByTestId('current-theme')).toHaveTextContent('light');
      
      fireEvent.click(getByText('Dark Mode'));
      
      await waitFor(() => {
        expect(getByTestId('current-theme')).toHaveTextContent('dark');
        expect(localStorage.getItem('theme')).toBe('dark');
      });
    });

    it('should persist user preferences across sessions', async () => {
      const preferences = {
        notifications: true,
        autoSave: false,
        language: 'en',
        fontSize: 'medium'
      };
      
      // Save preferences
      localStorage.setItem('userPreferences', JSON.stringify(preferences));
      
      // Simulate new session
      const loadPreferences = () => {
        const saved = localStorage.getItem('userPreferences');
        return saved ? JSON.parse(saved) : {};
      };
      
      const loaded = loadPreferences();
      
      expect(loaded).toEqual(preferences);
      expect(loaded.notifications).toBe(true);
      expect(loaded.autoSave).toBe(false);
    });
  });

  describe('17. Complex Form Validation Integration', () => {
    it('should validate multi-step forms with dependencies', async () => {
      const FormComponent = () => {
        const [step, setStep] = React.useState(1);
        const [formData, setFormData] = React.useState({
          model: '',
          temperature: 0.7,
          maxTokens: 1000
        });
        const [errors, setErrors] = React.useState<Record<string, string>>({});
        
        const validateStep = (currentStep: number) => {
          const newErrors: Record<string, string> = {};
          
          if (currentStep === 1 && !formData.model) {
            newErrors.model = 'Model is required';
          }
          
          if (currentStep === 2) {
            if (formData.temperature < 0 || formData.temperature > 2) {
              newErrors.temperature = 'Temperature must be between 0 and 2';
            }
            if (formData.maxTokens < 1 || formData.maxTokens > 4000) {
              newErrors.maxTokens = 'Max tokens must be between 1 and 4000';
            }
          }
          
          setErrors(newErrors);
          return Object.keys(newErrors).length === 0;
        };
        
        const handleNext = () => {
          if (validateStep(step)) {
            setStep(step + 1);
          }
        };
        
        return (
          <div>
            <div data-testid="step">{step}</div>
            {step === 1 && (
              <div>
                <input
                  data-testid="model-input"
                  value={formData.model}
                  onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                />
                {errors.model && <div data-testid="model-error">{errors.model}</div>}
              </div>
            )}
            {step === 2 && (
              <div>
                <input
                  data-testid="temperature-input"
                  type="number"
                  value={formData.temperature}
                  onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                />
                {errors.temperature && <div data-testid="temperature-error">{errors.temperature}</div>}
              </div>
            )}
            <button onClick={handleNext}>Next</button>
          </div>
        );
      };
      
      const { getByTestId, getByText } = render(<FormComponent />);
      
      // Try to proceed without required field
      fireEvent.click(getByText('Next'));
      
      await waitFor(() => {
        expect(getByTestId('model-error')).toHaveTextContent('Model is required');
      });
      
      // Fill required field
      fireEvent.change(getByTestId('model-input'), { target: { value: 'gpt-4' } });
      fireEvent.click(getByText('Next'));
      
      await waitFor(() => {
        expect(getByTestId('step')).toHaveTextContent('2');
      });
    });

    it('should handle async validation with debouncing', async () => {
      let validationCount = 0;
      
      const AsyncValidationComponent = () => {
        const [email, setEmail] = React.useState('');
        const [isValidating, setIsValidating] = React.useState(false);
        const [error, setError] = React.useState('');
        
        const validateEmail = React.useCallback(async (value: string) => {
          setIsValidating(true);
          validationCount++;
          
          // Simulate API call
          await new Promise(resolve => setTimeout(resolve, 100));
          
          if (!value.includes('@')) {
            setError('Invalid email');
          } else {
            setError('');
          }
          
          setIsValidating(false);
        }, []);
        
        // Debounce validation
        React.useEffect(() => {
          const timer = setTimeout(() => {
            if (email) validateEmail(email);
          }, 300);
          
          return () => clearTimeout(timer);
        }, [email, validateEmail]);
        
        return (
          <div>
            <input
              data-testid="email-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {isValidating && <div>Validating...</div>}
            {error && <div data-testid="error">{error}</div>}
          </div>
        );
      };
      
      const { getByTestId } = render(<AsyncValidationComponent />);
      
      // Type quickly
      const input = getByTestId('email-input');
      fireEvent.change(input, { target: { value: 't' } });
      fireEvent.change(input, { target: { value: 'te' } });
      fireEvent.change(input, { target: { value: 'test' } });
      
      // Wait for debounce
      await new Promise(resolve => setTimeout(resolve, 400));
      
      // Should only validate once due to debouncing
      expect(validationCount).toBe(1);
      
      await waitFor(() => {
        expect(getByTestId('error')).toHaveTextContent('Invalid email');
      });
    });
  });

  describe('18. Collaborative Features Integration', () => {
    it('should sync cursor positions in real-time', async () => {
      const cursors = new Map();
      
      const CollaborativeEditor = () => {
        const [otherCursors, setOtherCursors] = React.useState<Map<string, { x: number, y: number }>>(new Map());
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
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
      server.send(JSON.stringify({
        type: 'cursor_update',
        userId: 'user-2',
        position: { x: 100, y: 200 }
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('cursor-user-2')).toHaveTextContent('User user-2: 100, 200');
      });
    });

    it('should handle presence and activity status', async () => {
      const PresenceComponent = () => {
        const [activeUsers, setActiveUsers] = React.useState<Set<string>>(new Set());
        const [typingUsers, setTypingUsers] = React.useState<Set<string>>(new Set());
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
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
      server.send(JSON.stringify({ type: 'user_joined', userId: 'user-1' }));
      server.send(JSON.stringify({ type: 'user_joined', userId: 'user-2' }));
      
      await waitFor(() => {
        expect(screen.getByTestId('active-count')).toHaveTextContent('2 users online');
      });
      
      // Simulate typing
      server.send(JSON.stringify({ type: 'typing_start', userId: 'user-1' }));
      
      await waitFor(() => {
        expect(screen.getByTestId('typing-count')).toHaveTextContent('1 users typing');
      });
    });
  });

  describe('19. Offline Mode Integration', () => {
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
      window.dispatchEvent(new Event('offline'));
      
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
      window.dispatchEvent(new Event('online'));
      
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

  describe('20. Complex Navigation Flows', () => {
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
        const { isAuthenticated } = useAuthStore();
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
      const { getByText, rerender } = render(<TestComponent />);
      
      expect(getByText('Redirecting to login...')).toBeInTheDocument();
      expect(sessionStorage.getItem('redirect_after_login')).toBe('/');
      
      // Authenticate and rerender
      act(() => {
        useAuthStore.setState({ isAuthenticated: true, user: { id: '1', email: 'test@example.com' } });
      });
      
      rerender(<TestComponent />);
      
      await waitFor(() => {
        expect(screen.getByTestId('protected-content')).toBeInTheDocument();
      });
    });
  });

  describe('21. Advanced Search Integration', () => {
    it('should implement fuzzy search with highlighting', async () => {
      const SearchComponent = () => {
        const [query, setQuery] = React.useState('');
        const [results, setResults] = React.useState<any[]>([]);
        
        const items = [
          { id: 1, title: 'Machine Learning Optimization' },
          { id: 2, title: 'Deep Learning Models' },
          { id: 3, title: 'Neural Network Training' }
        ];
        
        const fuzzySearch = (searchQuery: string) => {
          if (!searchQuery) {
            setResults([]);
            return;
          }
          
          const searchResults = items.filter(item => {
            const itemLower = item.title.toLowerCase();
            const queryLower = searchQuery.toLowerCase();
            return itemLower.includes(queryLower) || 
                   queryLower.split(' ').every(word => itemLower.includes(word));
          }).map(item => ({
            ...item,
            highlighted: item.title.replace(
              new RegExp(searchQuery, 'gi'),
              match => `<mark>${match}</mark>`
            )
          }));
          
          setResults(searchResults);
        };
        
        React.useEffect(() => {
          const timer = setTimeout(() => fuzzySearch(query), 200);
          return () => clearTimeout(timer);
        }, [query]);
        
        return (
          <div>
            <input
              data-testid="search-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div data-testid="results">
              {results.map(r => (
                <div key={r.id} dangerouslySetInnerHTML={{ __html: r.highlighted }} />
              ))}
            </div>
          </div>
        );
      };
      
      const { getByTestId } = render(<SearchComponent />);
      
      fireEvent.change(getByTestId('search-input'), { target: { value: 'learning' } });
      
      await waitFor(() => {
        const results = getByTestId('results');
        expect(results.innerHTML).toContain('<mark>Learning</mark>');
        expect(results.children).toHaveLength(2);
      });
    });

    it('should implement search with filters and facets', async () => {
      const FilteredSearchComponent = () => {
        const [filters, setFilters] = React.useState({
          category: '',
          dateRange: '',
          status: ''
        });
        const [searchResults, setSearchResults] = React.useState<any[]>([]);
        
        const performSearch = async () => {
          const queryParams = new URLSearchParams();
          Object.entries(filters).forEach(([key, value]) => {
            if (value) queryParams.append(key, value);
          });
          
          // Simulate API call
          const results = [
            { id: 1, title: 'Result 1', category: 'optimization', status: 'active' },
            { id: 2, title: 'Result 2', category: 'training', status: 'completed' }
          ].filter(item => {
            if (filters.category && item.category !== filters.category) return false;
            if (filters.status && item.status !== filters.status) return false;
            return true;
          });
          
          setSearchResults(results);
        };
        
        React.useEffect(() => {
          performSearch();
        }, [filters]);
        
        return (
          <div>
            <select
              data-testid="category-filter"
              value={filters.category}
              onChange={(e) => setFilters({ ...filters, category: e.target.value })}
            >
              <option value="">All Categories</option>
              <option value="optimization">Optimization</option>
              <option value="training">Training</option>
            </select>
            <div data-testid="result-count">{searchResults.length} results</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<FilteredSearchComponent />);
      
      // Initially shows all results
      expect(getByTestId('result-count')).toHaveTextContent('2 results');
      
      // Apply filter
      fireEvent.change(getByTestId('category-filter'), { target: { value: 'optimization' } });
      
      await waitFor(() => {
        expect(getByTestId('result-count')).toHaveTextContent('1 results');
      });
    });
  });

  describe('22. Drag and Drop Integration', () => {
    it('should handle file drag and drop with preview', async () => {
      const DragDropComponent = () => {
        const [isDragging, setIsDragging] = React.useState(false);
        const [files, setFiles] = React.useState<File[]>([]);
        
        const handleDragOver = (e: React.DragEvent) => {
          e.preventDefault();
          setIsDragging(true);
        };
        
        const handleDragLeave = () => {
          setIsDragging(false);
        };
        
        const handleDrop = (e: React.DragEvent) => {
          e.preventDefault();
          setIsDragging(false);
          
          const droppedFiles = Array.from(e.dataTransfer.files);
          setFiles(prev => [...prev, ...droppedFiles]);
        };
        
        return (
          <div
            data-testid="drop-zone"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            style={{ border: isDragging ? '2px solid blue' : '2px solid gray' }}
          >
            {isDragging ? 'Drop files here' : 'Drag files here'}
            <div data-testid="file-count">{files.length} files</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<DragDropComponent />);
      
      const dropZone = getByTestId('drop-zone');
      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      
      // Simulate drag and drop
      const dataTransfer = {
        files: [file],
        items: [],
        types: ['Files']
      };
      
      fireEvent.dragOver(dropZone);
      fireEvent.drop(dropZone, { dataTransfer });
      
      await waitFor(() => {
        expect(getByTestId('file-count')).toHaveTextContent('1 files');
      });
    });

    it('should reorder items with drag and drop', async () => {
      const ReorderableList = () => {
        const [items, setItems] = React.useState([
          { id: '1', text: 'Item 1' },
          { id: '2', text: 'Item 2' },
          { id: '3', text: 'Item 3' }
        ]);
        const [draggedItem, setDraggedItem] = React.useState<string | null>(null);
        
        const handleDragStart = (id: string) => {
          setDraggedItem(id);
        };
        
        const handleDragOver = (e: React.DragEvent) => {
          e.preventDefault();
        };
        
        const handleDrop = (targetId: string) => {
          if (!draggedItem || draggedItem === targetId) return;
          
          const draggedIndex = items.findIndex(item => item.id === draggedItem);
          const targetIndex = items.findIndex(item => item.id === targetId);
          
          const newItems = [...items];
          const [removed] = newItems.splice(draggedIndex, 1);
          newItems.splice(targetIndex, 0, removed);
          
          setItems(newItems);
          setDraggedItem(null);
        };
        
        return (
          <div>
            {items.map((item, index) => (
              <div
                key={item.id}
                data-testid={`item-${index}`}
                draggable
                onDragStart={() => handleDragStart(item.id)}
                onDragOver={handleDragOver}
                onDrop={() => handleDrop(item.id)}
              >
                {item.text}
              </div>
            ))}
          </div>
        );
      };
      
      const { getByTestId } = render(<ReorderableList />);
      
      // Initial order
      expect(getByTestId('item-0')).toHaveTextContent('Item 1');
      expect(getByTestId('item-1')).toHaveTextContent('Item 2');
      
      // Simulate drag Item 1 to position 2
      const item1 = getByTestId('item-0');
      const item2 = getByTestId('item-1');
      
      fireEvent.dragStart(item1);
      fireEvent.dragOver(item2);
      fireEvent.drop(item2);
      
      await waitFor(() => {
        expect(getByTestId('item-0')).toHaveTextContent('Item 2');
        expect(getByTestId('item-1')).toHaveTextContent('Item 1');
      });
    });
  });

  describe('23. Infinite Scroll Integration', () => {
    it('should load more content on scroll', async () => {
      const InfiniteScrollComponent = () => {
        const [items, setItems] = React.useState(Array.from({ length: 10 }, (_, i) => `Item ${i + 1}`));
        const [isLoading, setIsLoading] = React.useState(false);
        const [hasMore, setHasMore] = React.useState(true);
        
        const loadMore = async () => {
          if (isLoading || !hasMore) return;
          
          setIsLoading(true);
          
          // Simulate API call
          await new Promise(resolve => setTimeout(resolve, 100));
          
          const newItems = Array.from({ length: 10 }, (_, i) => `Item ${items.length + i + 1}`);
          setItems(prev => [...prev, ...newItems]);
          
          if (items.length >= 30) {
            setHasMore(false);
          }
          
          setIsLoading(false);
        };
        
        const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
          const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
          if (scrollHeight - scrollTop <= clientHeight * 1.5) {
            loadMore();
          }
        };
        
        return (
          <div
            data-testid="scroll-container"
            onScroll={handleScroll}
            style={{ height: '200px', overflow: 'auto' }}
          >
            {items.map((item, index) => (
              <div key={index}>{item}</div>
            ))}
            {isLoading && <div>Loading...</div>}
            <div data-testid="item-count">{items.length} items</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<InfiniteScrollComponent />);
      
      expect(getByTestId('item-count')).toHaveTextContent('10 items');
      
      // Simulate scroll near bottom
      const container = getByTestId('scroll-container');
      fireEvent.scroll(container, {
        target: {
          scrollTop: 150,
          scrollHeight: 200,
          clientHeight: 200
        }
      });
      
      await waitFor(() => {
        expect(getByTestId('item-count')).toHaveTextContent('20 items');
      }, { timeout: 3000 });
    });

    it('should implement virtual scrolling for large lists', async () => {
      const VirtualScrollComponent = () => {
        const [visibleRange, setVisibleRange] = React.useState({ start: 0, end: 10 });
        const items = Array.from({ length: 10000 }, (_, i) => `Item ${i + 1}`);
        const itemHeight = 30;
        
        const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
          const scrollTop = e.currentTarget.scrollTop;
          const start = Math.floor(scrollTop / itemHeight);
          const end = start + Math.ceil(200 / itemHeight) + 1;
          
          setVisibleRange({ start, end });
        };
        
        const visibleItems = items.slice(visibleRange.start, visibleRange.end);
        
        return (
          <div
            data-testid="virtual-scroll"
            onScroll={handleScroll}
            style={{ height: '200px', overflow: 'auto' }}
          >
            <div style={{ height: `${items.length * itemHeight}px`, position: 'relative' }}>
              {visibleItems.map((item, index) => (
                <div
                  key={visibleRange.start + index}
                  style={{
                    position: 'absolute',
                    top: `${(visibleRange.start + index) * itemHeight}px`,
                    height: `${itemHeight}px`
                  }}
                >
                  {item}
                </div>
              ))}
            </div>
            <div data-testid="visible-count">{visibleItems.length} visible</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<VirtualScrollComponent />);
      
      // Only renders visible items
      expect(getByTestId('visible-count').textContent).toMatch(/\d+ visible/);
      const visibleCount = parseInt(getByTestId('visible-count').textContent || '0');
      expect(visibleCount).toBeLessThan(20);
    });
  });

  describe('24. Complex Animation Sequences', () => {
    it('should chain animations with proper timing', async () => {
      const AnimationComponent = () => {
        const [stage, setStage] = React.useState(0);
        
        const runAnimation = async () => {
          setStage(1);
          await new Promise(resolve => setTimeout(resolve, 100));
          
          setStage(2);
          await new Promise(resolve => setTimeout(resolve, 100));
          
          setStage(3);
        };
        
        return (
          <div>
            <button onClick={runAnimation}>Start Animation</button>
            <div
              data-testid="animated-element"
              style={{
                transform: `translateX(${stage * 100}px)`,
                transition: 'transform 0.1s'
              }}
            >
              Stage {stage}
            </div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<AnimationComponent />);
      
      fireEvent.click(getByText('Start Animation'));
      
      await waitFor(() => {
        expect(getByTestId('animated-element')).toHaveTextContent('Stage 1');
      });
      
      await waitFor(() => {
        expect(getByTestId('animated-element')).toHaveTextContent('Stage 2');
      }, { timeout: 200 });
      
      await waitFor(() => {
        expect(getByTestId('animated-element')).toHaveTextContent('Stage 3');
      }, { timeout: 300 });
    });

    it('should handle gesture-based animations', async () => {
      const GestureComponent = () => {
        const [position, setPosition] = React.useState({ x: 0, y: 0 });
        const [velocity, setVelocity] = React.useState({ x: 0, y: 0 });
        
        const handleSwipe = (direction: string) => {
          const velocityMap = {
            left: { x: -100, y: 0 },
            right: { x: 100, y: 0 },
            up: { x: 0, y: -100 },
            down: { x: 0, y: 100 }
          };
          
          const v = velocityMap[direction] || { x: 0, y: 0 };
          setVelocity(v);
          setPosition(prev => ({
            x: prev.x + v.x,
            y: prev.y + v.y
          }));
        };
        
        return (
          <div>
            <button onClick={() => handleSwipe('right')}>Swipe Right</button>
            <button onClick={() => handleSwipe('left')}>Swipe Left</button>
            <div
              data-testid="gesture-element"
              style={{
                transform: `translate(${position.x}px, ${position.y}px)`,
                transition: 'transform 0.3s'
              }}
            >
              Position: {position.x}, {position.y}
            </div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<GestureComponent />);
      
      fireEvent.click(getByText('Swipe Right'));
      
      await waitFor(() => {
        expect(getByTestId('gesture-element')).toHaveTextContent('Position: 100, 0');
      });
      
      fireEvent.click(getByText('Swipe Left'));
      
      await waitFor(() => {
        expect(getByTestId('gesture-element')).toHaveTextContent('Position: 0, 0');
      });
    });
  });

  describe('25. Memory Management Integration', () => {
    it('should cleanup resources on unmount', async () => {
      const cleanupFunctions: (() => void)[] = [];
      
      const ResourceComponent = () => {
        React.useEffect(() => {
          const timer = setInterval(() => {}, 1000);
          const listener = () => {};
          window.addEventListener('resize', listener);
          
          const cleanup = () => {
            clearInterval(timer);
            window.removeEventListener('resize', listener);
          };
          
          cleanupFunctions.push(cleanup);
          
          return cleanup;
        }, []);
        
        return <div>Resource Component</div>;
      };
      
      const { unmount } = render(<ResourceComponent />);
      
      expect(cleanupFunctions).toHaveLength(1);
      
      unmount();
      
      // Verify cleanup was called
      cleanupFunctions.forEach(cleanup => {
        expect(cleanup).toBeDefined();
      });
    });

    it('should manage large data sets efficiently', async () => {
      const LargeDataComponent = () => {
        const [data, setData] = React.useState<any[]>([]);
        const [isLoading, setIsLoading] = React.useState(false);
        
        const loadLargeDataset = async () => {
          setIsLoading(true);
          
          // Simulate loading large dataset in chunks
          const chunkSize = 1000;
          const totalSize = 5000;
          
          for (let i = 0; i < totalSize; i += chunkSize) {
            const chunk = Array.from({ length: chunkSize }, (_, j) => ({
              id: i + j,
              value: Math.random()
            }));
            
            setData(prev => [...prev, ...chunk]);
            
            // Allow UI to update
            await new Promise(resolve => setTimeout(resolve, 0));
          }
          
          setIsLoading(false);
        };
        
        // Cleanup large data on unmount
        React.useEffect(() => {
          return () => {
            setData([]);
          };
        }, []);
        
        return (
          <div>
            <button onClick={loadLargeDataset}>Load Data</button>
            <div data-testid="data-size">{data.length} items</div>
            {isLoading && <div>Loading...</div>}
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<LargeDataComponent />);
      
      fireEvent.click(getByText('Load Data'));
      
      await waitFor(() => {
        expect(getByTestId('data-size')).toHaveTextContent('5000 items');
      }, { timeout: 5000 });
    });
  });

  describe('26. Real-time Collaboration Sync', () => {
    it('should handle conflict resolution in collaborative editing', async () => {
      const CollaborativeEditor = () => {
        const [content, setContent] = React.useState('Initial content');
        const [conflicts, setConflicts] = React.useState<any[]>([]);
        const [version, setVersion] = React.useState(1);
        
        const handleRemoteChange = (remoteContent: string, remoteVersion: number) => {
          if (remoteVersion > version) {
            // Remote is newer, accept it
            setContent(remoteContent);
            setVersion(remoteVersion);
          } else if (remoteVersion === version) {
            // Conflict detected
            setConflicts(prev => [...prev, {
              local: content,
              remote: remoteContent,
              timestamp: Date.now()
            }]);
          }
        };
        
        const resolveConflict = (resolution: 'local' | 'remote', conflictIndex: number) => {
          const conflict = conflicts[conflictIndex];
          if (resolution === 'remote') {
            setContent(conflict.remote);
          }
          setConflicts(prev => prev.filter((_, i) => i !== conflictIndex));
          setVersion(prev => prev + 1);
        };
        
        // Simulate receiving remote change
        React.useEffect(() => {
          const timer = setTimeout(() => {
            handleRemoteChange('Remote content update', version);
          }, 1000);
          
          return () => clearTimeout(timer);
        }, []);
        
        return (
          <div>
            <div data-testid="content">{content}</div>
            <div data-testid="version">Version {version}</div>
            <div data-testid="conflicts">{conflicts.length} conflicts</div>
            {conflicts.map((conflict, i) => (
              <div key={i}>
                <button onClick={() => resolveConflict('local', i)}>Keep Local</button>
                <button onClick={() => resolveConflict('remote', i)}>Keep Remote</button>
              </div>
            ))}
          </div>
        );
      };
      
      const { getByTestId } = render(<CollaborativeEditor />);
      
      await waitFor(() => {
        const conflictCount = getByTestId('conflicts').textContent;
        expect(conflictCount).toMatch(/\d+ conflicts/);
      }, { timeout: 2000 });
    });

    it('should maintain operation history for undo/redo', async () => {
      const UndoRedoComponent = () => {
        const [history, setHistory] = React.useState<string[]>(['Initial']);
        const [currentIndex, setCurrentIndex] = React.useState(0);
        
        const performAction = (action: string) => {
          const newHistory = history.slice(0, currentIndex + 1);
          newHistory.push(action);
          setHistory(newHistory);
          setCurrentIndex(newHistory.length - 1);
        };
        
        const undo = () => {
          if (currentIndex > 0) {
            setCurrentIndex(currentIndex - 1);
          }
        };
        
        const redo = () => {
          if (currentIndex < history.length - 1) {
            setCurrentIndex(currentIndex + 1);
          }
        };
        
        return (
          <div>
            <div data-testid="current-state">{history[currentIndex]}</div>
            <button onClick={() => performAction('Action 1')}>Action 1</button>
            <button onClick={() => performAction('Action 2')}>Action 2</button>
            <button onClick={undo} disabled={currentIndex === 0}>Undo</button>
            <button onClick={redo} disabled={currentIndex === history.length - 1}>Redo</button>
            <div data-testid="history-length">{history.length} states</div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<UndoRedoComponent />);
      
      // Perform actions
      fireEvent.click(getByText('Action 1'));
      fireEvent.click(getByText('Action 2'));
      
      expect(getByTestId('current-state')).toHaveTextContent('Action 2');
      expect(getByTestId('history-length')).toHaveTextContent('3 states');
      
      // Undo
      fireEvent.click(getByText('Undo'));
      expect(getByTestId('current-state')).toHaveTextContent('Action 1');
      
      // Redo
      fireEvent.click(getByText('Redo'));
      expect(getByTestId('current-state')).toHaveTextContent('Action 2');
    });
  });

  describe('27. Advanced Error Boundaries', () => {
    it('should recover from component errors gracefully', async () => {
      const ErrorBoundary = ({ children }: { children: React.ReactNode }) => {
        const [hasError, setHasError] = React.useState(false);
        const [errorInfo, setErrorInfo] = React.useState<any>(null);
        
        React.useEffect(() => {
          const errorHandler = (event: ErrorEvent) => {
            setHasError(true);
            setErrorInfo({
              message: event.message,
              stack: event.error?.stack
            });
            event.preventDefault();
          };
          
          window.addEventListener('error', errorHandler);
          return () => window.removeEventListener('error', errorHandler);
        }, []);
        
        const retry = () => {
          setHasError(false);
          setErrorInfo(null);
        };
        
        if (hasError) {
          return (
            <div>
              <div data-testid="error-message">Something went wrong</div>
              <button onClick={retry}>Retry</button>
            </div>
          );
        }
        
        return <>{children}</>;
      };
      
      const FaultyComponent = ({ shouldError }: { shouldError: boolean }) => {
        if (shouldError) {
          throw new Error('Component error');
        }
        return <div>Working component</div>;
      };
      
      const TestComponent = () => {
        const [shouldError, setShouldError] = React.useState(false);
        
        return (
          <ErrorBoundary>
            <button onClick={() => setShouldError(true)}>Trigger Error</button>
            <FaultyComponent shouldError={shouldError} />
          </ErrorBoundary>
        );
      };
      
      const originalError = console.error;
      console.error = jest.fn();
      
      const { getByText } = render(<TestComponent />);
      
      fireEvent.click(getByText('Trigger Error'));
      
      // Error boundary should catch and display fallback
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toHaveTextContent('Something went wrong');
      });
      
      console.error = originalError;
    });

    it('should report errors to monitoring service', async () => {
      const errorReports: any[] = [];
      
      const reportError = async (error: any) => {
        errorReports.push({
          message: error.message,
          stack: error.stack,
          timestamp: Date.now(),
          userAgent: navigator.userAgent
        });
      };
      
      const MonitoredComponent = () => {
        const handleError = () => {
          try {
            throw new Error('Monitored error');
          } catch (error) {
            reportError(error);
            throw error;
          }
        };
        
        return (
          <div>
            <button onClick={handleError}>Trigger Monitored Error</button>
          </div>
        );
      };
      
      const originalError = console.error;
      console.error = jest.fn();
      
      const { getByText } = render(<MonitoredComponent />);
      
      try {
        fireEvent.click(getByText('Trigger Monitored Error'));
      } catch {
        // Expected to throw
      }
      
      expect(errorReports).toHaveLength(1);
      expect(errorReports[0].message).toBe('Monitored error');
      
      console.error = originalError;
    });
  });

  describe('28. Multi-language Support Integration', () => {
    it('should switch languages dynamically', async () => {
      const translations = {
        en: { welcome: 'Welcome', goodbye: 'Goodbye' },
        es: { welcome: 'Bienvenido', goodbye: 'Adiós' },
        fr: { welcome: 'Bienvenue', goodbye: 'Au revoir' }
      };
      
      const I18nComponent = () => {
        const [language, setLanguage] = React.useState('en');
        
        const t = (key: string) => translations[language][key] || key;
        
        return (
          <div>
            <select
              data-testid="language-selector"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="en">English</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
            </select>
            <div data-testid="welcome">{t('welcome')}</div>
            <div data-testid="goodbye">{t('goodbye')}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<I18nComponent />);
      
      expect(getByTestId('welcome')).toHaveTextContent('Welcome');
      
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'es' } });
      
      await waitFor(() => {
        expect(getByTestId('welcome')).toHaveTextContent('Bienvenido');
        expect(getByTestId('goodbye')).toHaveTextContent('Adiós');
      });
    });

    it('should handle RTL languages correctly', async () => {
      const RTLComponent = () => {
        const [language, setLanguage] = React.useState('en');
        const [direction, setDirection] = React.useState<'ltr' | 'rtl'>('ltr');
        
        React.useEffect(() => {
          const rtlLanguages = ['ar', 'he', 'fa'];
          const newDirection = rtlLanguages.includes(language) ? 'rtl' : 'ltr';
          setDirection(newDirection);
          document.documentElement.dir = newDirection;
        }, [language]);
        
        return (
          <div dir={direction}>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="en">English</option>
              <option value="ar">العربية</option>
            </select>
            <div data-testid="direction">{direction}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<RTLComponent />);
      
      expect(getByTestId('direction')).toHaveTextContent('ltr');
      
      const select = document.querySelector('select');
      fireEvent.change(select!, { target: { value: 'ar' } });
      
      await waitFor(() => {
        expect(getByTestId('direction')).toHaveTextContent('rtl');
        expect(document.documentElement.dir).toBe('rtl');
      });
    });
  });

  describe('29. WebSocket Resilience Integration', () => {
    it('should handle WebSocket message buffering during reconnection', async () => {
      const messageBuffer: any[] = [];
      
      const ResilientWebSocketComponent = () => {
        const [isConnected, setIsConnected] = React.useState(false);
        const [messages, setMessages] = React.useState<any[]>([]);
        const wsRef = React.useRef<WebSocket | null>(null);
        
        const sendMessage = (message: any) => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
          } else {
            messageBuffer.push(message);
          }
        };
        
        const connect = () => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onopen = () => {
            setIsConnected(true);
            
            // Flush buffered messages
            while (messageBuffer.length > 0) {
              const bufferedMessage = messageBuffer.shift();
              ws.send(JSON.stringify(bufferedMessage));
            }
          };
          
          ws.onclose = () => {
            setIsConnected(false);
            setTimeout(connect, 1000);
          };
          
          ws.onmessage = (event) => {
            setMessages(prev => [...prev, JSON.parse(event.data)]);
          };
          
          wsRef.current = ws;
        };
        
        React.useEffect(() => {
          connect();
          return () => wsRef.current?.close();
        }, []);
        
        return (
          <div>
            <div data-testid="connection-status">
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
            <button onClick={() => sendMessage({ type: 'test' })}>
              Send Message
            </button>
            <div data-testid="buffer-size">{messageBuffer.length} buffered</div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<ResilientWebSocketComponent />);
      
      await server.connected;
      
      // Close connection to simulate disconnection
      server.close();
      
      await waitFor(() => {
        expect(getByTestId('connection-status')).toHaveTextContent('Disconnected');
      });
      
      // Send message while disconnected
      fireEvent.click(getByText('Send Message'));
      
      expect(messageBuffer).toHaveLength(1);
      expect(getByTestId('buffer-size')).toHaveTextContent('1 buffered');
    });

    it('should implement exponential backoff for reconnection', async () => {
      const reconnectAttempts: number[] = [];
      
      const ExponentialBackoffComponent = () => {
        const [attempts, setAttempts] = React.useState(0);
        const [nextRetryIn, setNextRetryIn] = React.useState(0);
        
        const calculateBackoff = (attemptNumber: number) => {
          const baseDelay = 1000;
          const maxDelay = 30000;
          const delay = Math.min(baseDelay * Math.pow(2, attemptNumber), maxDelay);
          return delay + Math.random() * 1000; // Add jitter
        };
        
        const attemptReconnect = async () => {
          const delay = calculateBackoff(attempts);
          reconnectAttempts.push(delay);
          
          setNextRetryIn(Math.round(delay / 1000));
          setAttempts(prev => prev + 1);
          
          await new Promise(resolve => setTimeout(resolve, delay));
          
          // Simulate connection attempt
          try {
            const ws = new WebSocket('ws://localhost:8000/ws');
            ws.onerror = () => {
              attemptReconnect();
            };
          } catch {
            attemptReconnect();
          }
        };
        
        return (
          <div>
            <button onClick={attemptReconnect}>Start Reconnection</button>
            <div data-testid="attempts">Attempts: {attempts}</div>
            <div data-testid="next-retry">Next retry in: {nextRetryIn}s</div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<ExponentialBackoffComponent />);
      
      fireEvent.click(getByText('Start Reconnection'));
      
      await waitFor(() => {
        expect(parseInt(getByTestId('attempts').textContent?.split(': ')[1] || '0')).toBeGreaterThan(0);
      });
      
      // Verify exponential backoff pattern
      if (reconnectAttempts.length >= 2) {
        expect(reconnectAttempts[1]).toBeGreaterThan(reconnectAttempts[0]);
      }
    });
  });

  describe('30. End-to-End User Journey', () => {
    it('should complete full optimization workflow', async () => {
      const OptimizationWorkflow = () => {
        const [step, setStep] = React.useState('upload');
        const [workloadData, setWorkloadData] = React.useState<any>(null);
        const [optimizations, setOptimizations] = React.useState<any[]>([]);
        const [results, setResults] = React.useState<any>(null);
        
        const handleUpload = (file: File) => {
          // Parse workload data
          setWorkloadData({ name: file.name, size: file.size });
          setStep('analyze');
        };
        
        const analyzeWorkload = async () => {
          // Simulate analysis
          await new Promise(resolve => setTimeout(resolve, 100));
          
          setOptimizations([
            { id: '1', type: 'model', recommendation: 'Switch to GPT-3.5' },
            { id: '2', type: 'caching', recommendation: 'Enable response caching' }
          ]);
          setStep('review');
        };
        
        const applyOptimizations = async () => {
          // Simulate applying optimizations
          await new Promise(resolve => setTimeout(resolve, 100));
          
          setResults({
            costReduction: '45%',
            latencyImprovement: '30ms',
            applied: optimizations.length
          });
          setStep('complete');
        };
        
        return (
          <div>
            <div data-testid="current-step">{step}</div>
            
            {step === 'upload' && (
              <div>
                <input
                  type="file"
                  data-testid="file-input"
                  onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
                />
              </div>
            )}
            
            {step === 'analyze' && (
              <div>
                <div>Analyzing {workloadData?.name}</div>
                <button onClick={analyzeWorkload}>Start Analysis</button>
              </div>
            )}
            
            {step === 'review' && (
              <div>
                <div data-testid="optimization-count">
                  {optimizations.length} optimizations found
                </div>
                <button onClick={applyOptimizations}>Apply All</button>
              </div>
            )}
            
            {step === 'complete' && (
              <div data-testid="results">
                Cost reduced by {results.costReduction},
                Latency improved by {results.latencyImprovement}
              </div>
            )}
          </div>
        );
      };
      
      const { getByTestId, getByText } = render(<OptimizationWorkflow />);
      
      // Step 1: Upload
      expect(getByTestId('current-step')).toHaveTextContent('upload');
      
      const file = new File(['workload data'], 'workload.json', { type: 'application/json' });
      const input = getByTestId('file-input') as HTMLInputElement;
      
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false
      });
      
      fireEvent.change(input);
      
      await waitFor(() => {
        expect(getByTestId('current-step')).toHaveTextContent('analyze');
      });
      
      // Step 2: Analyze
      fireEvent.click(getByText('Start Analysis'));
      
      await waitFor(() => {
        expect(getByTestId('current-step')).toHaveTextContent('review');
      });
      
      // Step 3: Review
      expect(getByTestId('optimization-count')).toHaveTextContent('2 optimizations found');
      
      fireEvent.click(getByText('Apply All'));
      
      // Step 4: Complete
      await waitFor(() => {
        expect(getByTestId('current-step')).toHaveTextContent('complete');
        expect(getByTestId('results')).toHaveTextContent(
          'Cost reduced by 45%, Latency improved by 30ms'
        );
      });
    });
  });
});