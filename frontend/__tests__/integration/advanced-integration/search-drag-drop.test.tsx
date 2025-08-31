import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react';
import WS from 'jest-websocket-mock';
import { safeWebSocketCleanup } from '../../helpers/websocket-test-manager';
import { setupTestEnvironment } from './test-setup';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
port { setupTestEnvironment } from './test-setup';

describe('Advanced Frontend Integration Tests - Search and Drag-Drop', () => {
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

  describe('21. Advanced Search Integration', () => {
      jest.setTimeout(10000);
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
      jest.setTimeout(10000);
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
});