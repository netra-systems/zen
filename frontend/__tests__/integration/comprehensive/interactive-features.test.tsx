/**
 * Interactive Features Integration Tests
 * 
 * Tests drag and drop functionality, infinite scroll, virtual scrolling,
 * complex animation sequences, and gesture-based interactions.
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
  waitForUserInteraction,
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

describe('Interactive Features Integration Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
  });

  describe('Drag and Drop Integration', () => {
    it('should handle file drag and drop with preview', async () => {
      const DragDropComponent = () => {
        const [isDragging, setIsDragging] = React.useState(false);
        const [files, setFiles] = React.useState<File[]>([]);
        const [previews, setPreviews] = React.useState<string[]>([]);
        
        const handleDragOver = (e: React.DragEvent) => {
          e.preventDefault();
          setIsDragging(true);
        };
        
        const handleDragLeave = () => {
          setIsDragging(false);
        };
        
        const handleDrop = async (e: React.DragEvent) => {
          e.preventDefault();
          setIsDragging(false);
          
          const droppedFiles = Array.from(e.dataTransfer.files);
          setFiles(prev => [...prev, ...droppedFiles]);
          
          // Generate previews for image files
          const newPreviews = await Promise.all(
            droppedFiles.map(file => {
              if (file.type.startsWith('image/')) {
                return new Promise<string>((resolve) => {
                  const reader = new FileReader();
                  reader.onload = (e) => resolve(e.target?.result as string);
                  reader.readAsDataURL(file);
                });
              }
              return Promise.resolve('');
            })
          );
          
          setPreviews(prev => [...prev, ...newPreviews]);
        };
        
        return (
          <div>
            <div
              data-testid="drop-zone"
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              style={{ 
                border: isDragging ? '2px solid blue' : '2px solid gray',
                padding: '20px',
                minHeight: '100px'
              }}
            >
              {isDragging ? 'Drop files here' : 'Drag files here'}
            </div>
            <div data-testid="file-count">{files.length} files</div>
            <div data-testid="preview-count">{previews.filter(p => p).length} previews</div>
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
      
      fireEvent.dragOver(dropZone, { dataTransfer });
      expect(dropZone).toHaveTextContent('Drop files here');
      
      fireEvent.drop(dropZone, { dataTransfer });
      
      await waitFor(() => {
        expect(getByTestId('file-count')).toHaveTextContent('1 files');
      });
    });

    it('should reorder items with drag and drop', async () => {
      const ReorderableList = () => {
        const [items, setItems] = React.useState([
          { id: '1', text: 'Item 1', order: 1 },
          { id: '2', text: 'Item 2', order: 2 },
          { id: '3', text: 'Item 3', order: 3 },
          { id: '4', text: 'Item 4', order: 4 }
        ]);
        const [draggedItem, setDraggedItem] = React.useState<string | null>(null);
        const [dragOverItem, setDragOverItem] = React.useState<string | null>(null);
        
        const handleDragStart = (id: string) => {
          setDraggedItem(id);
        };
        
        const handleDragOver = (e: React.DragEvent, targetId: string) => {
          e.preventDefault();
          setDragOverItem(targetId);
        };
        
        const handleDragLeave = () => {
          setDragOverItem(null);
        };
        
        const handleDrop = (targetId: string) => {
          if (!draggedItem || draggedItem === targetId) {
            setDraggedItem(null);
            setDragOverItem(null);
            return;
          }
          
          const draggedIndex = items.findIndex(item => item.id === draggedItem);
          const targetIndex = items.findIndex(item => item.id === targetId);
          
          const newItems = [...items];
          const [removed] = newItems.splice(draggedIndex, 1);
          newItems.splice(targetIndex, 0, removed);
          
          setItems(newItems);
          setDraggedItem(null);
          setDragOverItem(null);
        };
        
        return (
          <div data-testid="reorderable-list">
            {items.map((item, index) => (
              <div
                key={item.id}
                data-testid={`item-${index}`}
                draggable
                onDragStart={() => handleDragStart(item.id)}
                onDragOver={(e) => handleDragOver(e, item.id)}
                onDragLeave={handleDragLeave}
                onDrop={() => handleDrop(item.id)}
                style={{
                  padding: '10px',
                  margin: '5px',
                  backgroundColor: dragOverItem === item.id ? '#e0e0e0' : '#f5f5f5',
                  border: draggedItem === item.id ? '2px dashed #999' : '1px solid #ddd',
                  cursor: 'move'
                }}
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
      expect(getByTestId('item-2')).toHaveTextContent('Item 3');
      
      // Simulate drag Item 1 to position of Item 3
      const item1 = getByTestId('item-0');
      const item3 = getByTestId('item-2');
      
      fireEvent.dragStart(item1);
      fireEvent.dragOver(item3);
      fireEvent.drop(item3);
      
      await waitFor(() => {
        expect(getByTestId('item-0')).toHaveTextContent('Item 2');
        expect(getByTestId('item-1')).toHaveTextContent('Item 3');
        expect(getByTestId('item-2')).toHaveTextContent('Item 1');
      });
    });

    it('should handle drag and drop with validation', async () => {
      const ValidatedDragDrop = () => {
        const [validItems] = React.useState(['valid1', 'valid2']);
        const [invalidItems] = React.useState(['invalid1']);
        const [dropZones, setDropZones] = React.useState({
          valid: [] as string[],
          invalid: [] as string[]
        });
        const [error, setError] = React.useState('');
        
        const handleDrop = (zone: 'valid' | 'invalid', item: string) => {
          // Validation: only valid items can be dropped in valid zone
          if (zone === 'valid' && invalidItems.includes(item)) {
            setError('Invalid item cannot be placed in valid zone');
            return;
          }
          
          setError('');
          setDropZones(prev => ({
            ...prev,
            [zone]: [...prev[zone], item]
          }));
        };
        
        return (
          <div>
            <div data-testid="valid-zone">
              Valid Zone: {dropZones.valid.join(', ')}
            </div>
            <div data-testid="invalid-zone">
              Invalid Zone: {dropZones.invalid.join(', ')}
            </div>
            {error && <div data-testid="error">{error}</div>}
            <button
              onClick={() => handleDrop('valid', 'valid1')}
              data-testid="drop-valid-item"
            >
              Drop Valid Item
            </button>
            <button
              onClick={() => handleDrop('valid', 'invalid1')}
              data-testid="drop-invalid-item"
            >
              Drop Invalid Item
            </button>
          </div>
        );
      };
      
      const { getByTestId, getByText } = render(<ValidatedDragDrop />);
      
      // Drop valid item - should succeed
      fireEvent.click(getByTestId('drop-valid-item'));
      
      await waitFor(() => {
        expect(getByTestId('valid-zone')).toHaveTextContent('Valid Zone: valid1');
      });
      
      // Drop invalid item - should fail
      fireEvent.click(getByTestId('drop-invalid-item'));
      
      await waitFor(() => {
        expect(getByTestId('error')).toHaveTextContent('Invalid item cannot be placed in valid zone');
        expect(getByTestId('valid-zone')).not.toHaveTextContent('invalid1');
      });
    });
  });

  describe('Infinite Scroll Integration', () => {
    it('should load more content on scroll', async () => {
      const InfiniteScrollComponent = () => {
        const [items, setItems] = React.useState(
          Array.from({ length: 10 }, (_, i) => `Item ${i + 1}`)
        );
        const [isLoading, setIsLoading] = React.useState(false);
        const [hasMore, setHasMore] = React.useState(true);
        const [loadCount, setLoadCount] = React.useState(1);
        
        const loadMore = async () => {
          if (isLoading || !hasMore) return;
          
          setIsLoading(true);
          
          // Simulate API call
          await simulateNetworkDelay(100);
          
          const newItems = Array.from(
            { length: 10 }, 
            (_, i) => `Item ${items.length + i + 1}`
          );
          
          setItems(prev => [...prev, ...newItems]);
          setLoadCount(prev => prev + 1);
          
          if (loadCount >= 3) {
            setHasMore(false);
          }
          
          setIsLoading(false);
        };
        
        const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
          const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
          if (scrollHeight - scrollTop <= clientHeight * 1.5 && hasMore && !isLoading) {
            loadMore();
          }
        };
        
        return (
          <div>
            <div
              data-testid="scroll-container"
              onScroll={handleScroll}
              style={{ height: '200px', overflow: 'auto' }}
            >
              {items.map((item, index) => (
                <div key={index} style={{ height: '30px', padding: '5px' }}>
                  {item}
                </div>
              ))}
              {isLoading && <div data-testid="loading">Loading more...</div>}
              {!hasMore && <div data-testid="end">No more items</div>}
            </div>
            <div data-testid="item-count">{items.length} items</div>
            <div data-testid="load-count">Loaded {loadCount} times</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<InfiniteScrollComponent />);
      
      expect(getByTestId('item-count')).toHaveTextContent('10 items');
      expect(getByTestId('load-count')).toHaveTextContent('Loaded 1 times');
      
      // Simulate scroll near bottom
      const container = getByTestId('scroll-container');
      Object.defineProperty(container, 'scrollTop', { value: 150, writable: true });
      Object.defineProperty(container, 'scrollHeight', { value: 300, writable: true });
      Object.defineProperty(container, 'clientHeight', { value: 200, writable: true });
      
      fireEvent.scroll(container);
      
      await waitFor(() => {
        expect(getByTestId('item-count')).toHaveTextContent('20 items');
        expect(getByTestId('load-count')).toHaveTextContent('Loaded 2 times');
      }, { timeout: TEST_TIMEOUTS.MEDIUM });
    });

    it('should implement virtual scrolling for large lists', async () => {
      const VirtualScrollComponent = () => {
        const [visibleRange, setVisibleRange] = React.useState({ start: 0, end: 10 });
        const totalItems = 1000;
        const items = React.useMemo(
          () => Array.from({ length: totalItems }, (_, i) => `Virtual Item ${i + 1}`),
          []
        );
        const itemHeight = 30;
        const containerHeight = 200;
        
        const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
          const scrollTop = e.currentTarget.scrollTop;
          const start = Math.floor(scrollTop / itemHeight);
          const visibleCount = Math.ceil(containerHeight / itemHeight);
          const end = Math.min(start + visibleCount + 5, totalItems); // Buffer of 5 items
          
          setVisibleRange({ start, end });
        };
        
        const visibleItems = React.useMemo(
          () => items.slice(visibleRange.start, visibleRange.end),
          [items, visibleRange]
        );
        
        return (
          <div>
            <div
              data-testid="virtual-scroll"
              onScroll={handleScroll}
              style={{ height: `${containerHeight}px`, overflow: 'auto' }}
            >
              <div style={{ height: `${totalItems * itemHeight}px`, position: 'relative' }}>
                {visibleItems.map((item, index) => (
                  <div
                    key={visibleRange.start + index}
                    data-testid={`virtual-item-${visibleRange.start + index}`}
                    style={{
                      position: 'absolute',
                      top: `${(visibleRange.start + index) * itemHeight}px`,
                      height: `${itemHeight}px`,
                      width: '100%',
                      padding: '5px',
                      borderBottom: '1px solid #eee'
                    }}
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>
            <div data-testid="visible-count">{visibleItems.length} visible items</div>
            <div data-testid="range">Range: {visibleRange.start} - {visibleRange.end}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<VirtualScrollComponent />);
      
      // Only renders visible items (much less than 1000)
      const visibleCount = parseInt(
        getByTestId('visible-count').textContent?.match(/\d+/)?.[0] || '0'
      );
      expect(visibleCount).toBeLessThan(50); // Should be much less than total items
      expect(visibleCount).toBeGreaterThan(5); // But still render some items
      
      // Test that virtual item exists
      expect(getByTestId('virtual-item-0')).toHaveTextContent('Virtual Item 1');
    });

    it('should handle scroll position restoration', async () => {
      const ScrollRestoreComponent = () => {
        const [items] = React.useState(
          Array.from({ length: 50 }, (_, i) => `Scroll Item ${i + 1}`)
        );
        const [scrollPosition, setScrollPosition] = React.useState(0);
        const containerRef = React.useRef<HTMLDivElement>(null);
        
        React.useEffect(() => {
          // Restore scroll position
          if (containerRef.current && scrollPosition > 0) {
            containerRef.current.scrollTop = scrollPosition;
          }
        }, [scrollPosition]);
        
        const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
          const newScrollPosition = e.currentTarget.scrollTop;
          setScrollPosition(newScrollPosition);
          localStorage.setItem('scroll_position', newScrollPosition.toString());
        };
        
        const restoreFromStorage = () => {
          const savedPosition = localStorage.getItem('scroll_position');
          if (savedPosition) {
            setScrollPosition(parseInt(savedPosition));
          }
        };
        
        return (
          <div>
            <button onClick={restoreFromStorage} data-testid="restore-scroll">
              Restore Scroll
            </button>
            <div
              ref={containerRef}
              data-testid="scroll-restore-container"
              onScroll={handleScroll}
              style={{ height: '200px', overflow: 'auto' }}
            >
              {items.map((item, index) => (
                <div key={index} style={{ height: '40px', padding: '10px' }}>
                  {item}
                </div>
              ))}
            </div>
            <div data-testid="current-scroll">{scrollPosition}px</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<ScrollRestoreComponent />);
      
      const container = getByTestId('scroll-restore-container');
      
      // Simulate scrolling
      Object.defineProperty(container, 'scrollTop', { value: 300, writable: true });
      fireEvent.scroll(container);
      
      await waitFor(() => {
        expect(getByTestId('current-scroll')).toHaveTextContent('300px');
      });
      
      // Verify scroll position is saved
      expect(localStorage.getItem('scroll_position')).toBe('300');
    });
  });

  describe('Complex Animation Sequences', () => {
    it('should chain animations with proper timing', async () => {
      const AnimationComponent = () => {
        const [stage, setStage] = React.useState(0);
        const [isAnimating, setIsAnimating] = React.useState(false);
        
        const runAnimation = async () => {
          setIsAnimating(true);
          
          setStage(1);
          await waitForUserInteraction(100);
          
          setStage(2);
          await waitForUserInteraction(100);
          
          setStage(3);
          await waitForUserInteraction(100);
          
          setIsAnimating(false);
        };
        
        const resetAnimation = () => {
          setStage(0);
          setIsAnimating(false);
        };
        
        return (
          <div>
            <button onClick={runAnimation} disabled={isAnimating}>
              Start Animation
            </button>
            <button onClick={resetAnimation}>Reset</button>
            <div
              data-testid="animated-element"
              style={{
                transform: `translateX(${stage * 50}px) scale(${1 + stage * 0.1})`,
                transition: 'all 0.1s ease-in-out',
                opacity: stage > 0 ? 1 : 0.5
              }}
            >
              Stage {stage}
            </div>
            <div data-testid="animation-status">
              {isAnimating ? 'Animating' : 'Idle'}
            </div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<AnimationComponent />);
      
      expect(getByTestId('animated-element')).toHaveTextContent('Stage 0');
      expect(getByTestId('animation-status')).toHaveTextContent('Idle');
      
      fireEvent.click(getByText('Start Animation'));
      
      await waitFor(() => {
        expect(getByTestId('animation-status')).toHaveTextContent('Animating');
        expect(getByTestId('animated-element')).toHaveTextContent('Stage 1');
      });
      
      await waitFor(() => {
        expect(getByTestId('animated-element')).toHaveTextContent('Stage 2');
      }, { timeout: 200 });
      
      await waitFor(() => {
        expect(getByTestId('animated-element')).toHaveTextContent('Stage 3');
      }, { timeout: 300 });
      
      await waitFor(() => {
        expect(getByTestId('animation-status')).toHaveTextContent('Idle');
      }, { timeout: 400 });
    });

    it('should handle gesture-based animations', async () => {
      const GestureComponent = () => {
        const [position, setPosition] = React.useState({ x: 0, y: 0 });
        const [isMoving, setIsMoving] = React.useState(false);
        const [history, setHistory] = React.useState<Array<{ x: number, y: number }>>([]);
        
        const handleSwipe = async (direction: string, distance: number = 100) => {
          setIsMoving(true);
          
          const movements = {
            left: { x: -distance, y: 0 },
            right: { x: distance, y: 0 },
            up: { x: 0, y: -distance },
            down: { x: 0, y: distance }
          };
          
          const movement = movements[direction] || { x: 0, y: 0 };
          const newPosition = {
            x: position.x + movement.x,
            y: position.y + movement.y
          };
          
          setPosition(newPosition);
          setHistory(prev => [...prev, newPosition]);
          
          // Simulate animation duration
          await waitForUserInteraction(200);
          setIsMoving(false);
        };
        
        const resetPosition = () => {
          setPosition({ x: 0, y: 0 });
          setHistory([]);
        };
        
        return (
          <div>
            <div style={{ margin: '10px 0' }}>
              <button onClick={() => handleSwipe('right')}>Swipe Right</button>
              <button onClick={() => handleSwipe('left')}>Swipe Left</button>
              <button onClick={() => handleSwipe('up')}>Swipe Up</button>
              <button onClick={() => handleSwipe('down')}>Swipe Down</button>
              <button onClick={resetPosition}>Reset</button>
            </div>
            <div
              data-testid="gesture-element"
              style={{
                transform: `translate(${position.x}px, ${position.y}px)`,
                transition: 'transform 0.2s ease-out',
                display: 'inline-block',
                padding: '10px',
                border: '2px solid',
                borderColor: isMoving ? 'red' : 'blue'
              }}
            >
              Position: {position.x}, {position.y}
            </div>
            <div data-testid="move-count">{history.length} moves</div>
            <div data-testid="moving-status">
              {isMoving ? 'Moving' : 'Stopped'}
            </div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<GestureComponent />);
      
      expect(getByTestId('gesture-element')).toHaveTextContent('Position: 0, 0');
      expect(getByTestId('move-count')).toHaveTextContent('0 moves');
      
      fireEvent.click(getByText('Swipe Right'));
      
      await waitFor(() => {
        expect(getByTestId('moving-status')).toHaveTextContent('Moving');
      });
      
      await waitFor(() => {
        expect(getByTestId('gesture-element')).toHaveTextContent('Position: 100, 0');
        expect(getByTestId('move-count')).toHaveTextContent('1 moves');
        expect(getByTestId('moving-status')).toHaveTextContent('Stopped');
      }, { timeout: TEST_TIMEOUTS.SHORT });
      
      fireEvent.click(getByText('Swipe Left'));
      
      await waitFor(() => {
        expect(getByTestId('gesture-element')).toHaveTextContent('Position: 0, 0');
        expect(getByTestId('move-count')).toHaveTextContent('2 moves');
      }, { timeout: TEST_TIMEOUTS.SHORT });
    });
  });
});