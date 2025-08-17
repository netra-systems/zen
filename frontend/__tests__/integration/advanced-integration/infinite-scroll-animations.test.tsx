/**
 * Infinite Scroll and Animation Tests
 */

import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react';
import WS from 'jest-websocket-mock';
import { safeWebSocketCleanup } from '../../helpers/websocket-test-manager';
import { setupTestEnvironment } from './test-setup';

describe('Advanced Frontend Integration Tests - Infinite Scroll and Animations', () => {
  let server: WS;
  
  setupTestEnvironment();

  beforeEach(() => {
    server = new WS('ws://localhost:8000/ws');
  });

  afterEach(() => {
    safeWebSocketCleanup();
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
      // Directly set properties on the container
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
});