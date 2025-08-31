import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react';
import { createTestSetup, waitForAnimation, createMockFile } from './setup';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
 fireEvent, waitFor } from '@testing-library/react';
import { createTestSetup, waitForAnimation, createMockFile } from './setup';

describe('Search and UI Interactions Integration', () => {
    jest.setTimeout(10000);
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Advanced Search', () => {
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

  describe('Drag and Drop', () => {
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
      const file = createMockFile('test.txt');
      
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

  describe('Infinite Scroll', () => {
      jest.setTimeout(10000);
    it('should load more content on scroll', async () => {
      const InfiniteScrollComponent = () => {
        const [items, setItems] = React.useState(Array.from({ length: 10 }, (_, i) => `Item ${i + 1}`));
        const [isLoading, setIsLoading] = React.useState(false);
        const [hasMore, setHasMore] = React.useState(true);
        
        const loadMore = async () => {
          if (isLoading || !hasMore) return;
          
          setIsLoading(true);
          
          // Simulate API call
          await waitForAnimation(100);
          
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
      Object.defineProperty(container, 'scrollTop', { value: 150, writable: true });
      Object.defineProperty(container, 'scrollHeight', { value: 200, writable: true });
      Object.defineProperty(container, 'clientHeight', { value: 50, writable: true });
      
      fireEvent.scroll(container);
      
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

  describe('Complex Animations', () => {
      jest.setTimeout(10000);
    it('should chain animations with proper timing', async () => {
      const AnimationComponent = () => {
        const [stage, setStage] = React.useState(0);
        
        const runAnimation = async () => {
          setStage(1);
          await waitForAnimation(100);
          
          setStage(2);
          await waitForAnimation(100);
          
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
        
        const handleSwipe = (direction: string) => {
          const velocityMap: Record<string, { x: number; y: number }> = {
            left: { x: -100, y: 0 },
            right: { x: 100, y: 0 },
            up: { x: 0, y: -100 },
            down: { x: 0, y: 100 }
          };
          
          const velocity = velocityMap[direction] || { x: 0, y: 0 };
          setPosition(prev => ({
            x: prev.x + velocity.x,
            y: prev.y + velocity.y
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
});