import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { vigation and Search Integration Tests
 * 
 * Tests complex navigation flows, deep linking, state preservation,
 * protected routes, and advanced search functionality with filters.
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
  simulateNetworkDelay,
  TEST_TIMEOUTS,
  WS,
  useAuthStore
} from './test-utils';

// Apply Next.js navigation mock
const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  refresh: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  pathname: '/',
  query: {},
  asPath: '/',
};

jest.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

describe('Navigation and Search Integration Tests', () => {
    jest.setTimeout(10000);
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
    jest.clearAllMocks();
  });

  afterEach(() => {
    cleanupTestEnvironment();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Complex Navigation Flows', () => {
      jest.setTimeout(10000);
    it('should handle deep linking with state preservation', async () => {
      const NavigationComponent = () => {
        const [navigationStack, setNavigationStack] = React.useState<string[]>(['/']);
        const router = require('next/navigation').useRouter();
        
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
            <button onClick={() => navigateTo('/settings')}>Go to Settings</button>
            <button onClick={goBack}>Back</button>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<NavigationComponent />);
      
      expect(getByTestId('current-path')).toHaveTextContent('/');
      expect(getByTestId('stack-depth')).toHaveTextContent('1');
      
      fireEvent.click(getByText('Go to Thread'));
      
      await waitFor(() => {
        expect(getByTestId('current-path')).toHaveTextContent('/chat/thread-1');
        expect(getByTestId('stack-depth')).toHaveTextContent('2');
      });
      
      // Verify state was preserved
      const savedState = JSON.parse(sessionStorage.getItem('nav_state') || '{}');
      expect(savedState.from).toBe('/');
      expect(mockRouter.push).toHaveBeenCalledWith('/chat/thread-1');
      
      // Test navigation to another path
      fireEvent.click(getByText('Go to Settings'));
      
      await waitFor(() => {
        expect(getByTestId('current-path')).toHaveTextContent('/settings');
        expect(getByTestId('stack-depth')).toHaveTextContent('3');
      });
      
      // Test going back
      fireEvent.click(getByText('Back'));
      
      await waitFor(() => {
        expect(getByTestId('current-path')).toHaveTextContent('/chat/thread-1');
        expect(getByTestId('stack-depth')).toHaveTextContent('2');
      });
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
      const { getByText, rerender } = render(<TestComponent />);
      
      expect(getByText('Redirecting to login...')).toBeInTheDocument();
      expect(sessionStorage.getItem('redirect_after_login')).toBe('/');
      expect(mockRouter.push).toHaveBeenCalledWith('/auth/login');
      
      // Authenticate and rerender
      act(() => {
        useAuthStore.setState({ 
          isAuthenticated: true, 
          user: { id: '1', email: 'test@example.com' },
          token: 'mock-token'
        });
      });
      
      rerender(<TestComponent />);
      
      await waitFor(() => {
        expect(screen.getByTestId('protected-content')).toBeInTheDocument();
      });
    });

    it('should handle navigation with query parameters', async () => {
      const QueryNavigationComponent = () => {
        const [params, setParams] = React.useState(new URLSearchParams());
        
        const updateParams = (key: string, value: string) => {
          const newParams = new URLSearchParams(params);
          newParams.set(key, value);
          setParams(newParams);
          
          const router = require('next/navigation').useRouter();
          router.push(`?${newParams.toString()}`);
        };
        
        return (
          <div>
            <div data-testid="current-params">{params.toString()}</div>
            <button onClick={() => updateParams('tab', 'settings')}>
              Set Tab
            </button>
            <button onClick={() => updateParams('filter', 'active')}>
              Set Filter
            </button>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<QueryNavigationComponent />);
      
      fireEvent.click(getByText('Set Tab'));
      
      await waitFor(() => {
        expect(getByTestId('current-params')).toHaveTextContent('tab=settings');
      });
      
      fireEvent.click(getByText('Set Filter'));
      
      await waitFor(() => {
        const params = getByTestId('current-params').textContent;
        expect(params).toContain('tab=settings');
        expect(params).toContain('filter=active');
      });
    });
  });

  describe('Advanced Search Integration', () => {
      jest.setTimeout(10000);
    it('should implement fuzzy search with highlighting', async () => {
      const SearchComponent = () => {
        const [query, setQuery] = React.useState('');
        const [results, setResults] = React.useState<any[]>([]);
        
        const items = [
          { id: 1, title: 'Machine Learning Optimization' },
          { id: 2, title: 'Deep Learning Models' },
          { id: 3, title: 'Neural Network Training' },
          { id: 4, title: 'Data Processing Pipeline' },
          { id: 5, title: 'AI Model Deployment' }
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
              placeholder="Search..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div data-testid="results">
              {results.map(r => (
                <div 
                  key={r.id} 
                  data-testid={`result-${r.id}`}
                  dangerouslySetInnerHTML={{ __html: r.highlighted }} 
                />
              ))}
            </div>
            <div data-testid="result-count">{results.length} results</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<SearchComponent />);
      
      fireEvent.change(getByTestId('search-input'), { target: { value: 'learning' } });
      
      await waitFor(() => {
        const results = getByTestId('results');
        expect(results.innerHTML).toContain('<mark>Learning</mark>');
        expect(getByTestId('result-count')).toHaveTextContent('2 results');
      });
      
      // Test more complex search
      fireEvent.change(getByTestId('search-input'), { target: { value: 'model' } });
      
      await waitFor(() => {
        expect(getByTestId('result-count')).toHaveTextContent('2 results');
        expect(getByTestId('result-2')).toBeInTheDocument();
        expect(getByTestId('result-5')).toBeInTheDocument();
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
        const [loading, setLoading] = React.useState(false);
        
        const performSearch = async () => {
          setLoading(true);
          await simulateNetworkDelay(100); // Simulate API delay
          
          const allResults = [
            { id: 1, title: 'Result 1', category: 'optimization', status: 'active', date: '2024-01-01' },
            { id: 2, title: 'Result 2', category: 'training', status: 'completed', date: '2024-02-01' },
            { id: 3, title: 'Result 3', category: 'optimization', status: 'pending', date: '2024-01-15' },
            { id: 4, title: 'Result 4', category: 'deployment', status: 'active', date: '2024-03-01' }
          ];
          
          const filteredResults = allResults.filter(item => {
            if (filters.category && item.category !== filters.category) return false;
            if (filters.status && item.status !== filters.status) return false;
            return true;
          });
          
          setSearchResults(filteredResults);
          setLoading(false);
        };
        
        React.useEffect(() => {
          performSearch();
        }, [filters]);
        
        return (
          <div>
            <div>
              <label>
                Category:
                <select
                  data-testid="category-filter"
                  value={filters.category}
                  onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                >
                  <option value="">All Categories</option>
                  <option value="optimization">Optimization</option>
                  <option value="training">Training</option>
                  <option value="deployment">Deployment</option>
                </select>
              </label>
            </div>
            <div>
              <label>
                Status:
                <select
                  data-testid="status-filter"
                  value={filters.status}
                  onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                >
                  <option value="">All Status</option>
                  <option value="active">Active</option>
                  <option value="completed">Completed</option>
                  <option value="pending">Pending</option>
                </select>
              </label>
            </div>
            
            {loading && <div data-testid="loading">Loading...</div>}
            <div data-testid="result-count">{searchResults.length} results</div>
            
            <div data-testid="results">
              {searchResults.map(result => (
                <div key={result.id} data-testid={`result-${result.id}`}>
                  {result.title} - {result.category} ({result.status})
                </div>
              ))}
            </div>
          </div>
        );
      };
      
      const { getByTestId } = render(<FilteredSearchComponent />);
      
      // Initially shows all results
      await waitFor(() => {
        expect(getByTestId('result-count')).toHaveTextContent('4 results');
      });
      
      // Apply category filter
      fireEvent.change(getByTestId('category-filter'), { target: { value: 'optimization' } });
      
      await waitFor(() => {
        expect(getByTestId('result-count')).toHaveTextContent('2 results');
        expect(getByTestId('result-1')).toBeInTheDocument();
        expect(getByTestId('result-3')).toBeInTheDocument();
      });
      
      // Apply status filter while keeping category filter
      fireEvent.change(getByTestId('status-filter'), { target: { value: 'active' } });
      
      await waitFor(() => {
        expect(getByTestId('result-count')).toHaveTextContent('1 results');
        expect(getByTestId('result-1')).toBeInTheDocument();
      });
      
      // Clear filters
      fireEvent.change(getByTestId('category-filter'), { target: { value: '' } });
      fireEvent.change(getByTestId('status-filter'), { target: { value: '' } });
      
      await waitFor(() => {
        expect(getByTestId('result-count')).toHaveTextContent('4 results');
      });
    });

    it('should handle search with autocomplete and suggestions', async () => {
      const AutocompleteComponent = () => {
        const [query, setQuery] = React.useState('');
        const [suggestions, setSuggestions] = React.useState<string[]>([]);
        const [showSuggestions, setShowSuggestions] = React.useState(false);
        
        const allSuggestions = [
          'machine learning',
          'deep learning',
          'neural networks',
          'data processing',
          'model optimization',
          'ai deployment'
        ];
        
        const updateSuggestions = (searchQuery: string) => {
          if (!searchQuery) {
            setSuggestions([]);
            setShowSuggestions(false);
            return;
          }
          
          const filtered = allSuggestions.filter(suggestion =>
            suggestion.toLowerCase().includes(searchQuery.toLowerCase())
          );
          
          setSuggestions(filtered);
          setShowSuggestions(filtered.length > 0);
        };
        
        React.useEffect(() => {
          const timer = setTimeout(() => updateSuggestions(query), 150);
          return () => clearTimeout(timer);
        }, [query]);
        
        const selectSuggestion = (suggestion: string) => {
          setQuery(suggestion);
          setShowSuggestions(false);
        };
        
        return (
          <div>
            <input
              data-testid="autocomplete-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => updateSuggestions(query)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 100)}
            />
            {showSuggestions && (
              <div data-testid="suggestions">
                {suggestions.map((suggestion, index) => (
                  <div
                    key={suggestion}
                    data-testid={`suggestion-${index}`}
                    onClick={() => selectSuggestion(suggestion)}
                    style={{ cursor: 'pointer', padding: '5px' }}
                  >
                    {suggestion}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      };
      
      const { getByTestId } = render(<AutocompleteComponent />);
      
      // Type to trigger suggestions
      fireEvent.change(getByTestId('autocomplete-input'), { target: { value: 'learn' } });
      
      await waitFor(() => {
        expect(getByTestId('suggestions')).toBeInTheDocument();
        expect(getByTestId('suggestion-0')).toHaveTextContent('machine learning');
        expect(getByTestId('suggestion-1')).toHaveTextContent('deep learning');
      });
      
      // Select a suggestion
      fireEvent.click(getByTestId('suggestion-0'));
      
      await waitFor(() => {
        expect(getByTestId('autocomplete-input')).toHaveValue('machine learning');
      });
    });
  });
});