import {
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
teractive Features Advanced Scroll Integration Tests
 * ULTRA DEEP THINK: Module-based architecture - Advanced scroll tests extracted for 450-line compliance
 */

import {
  React, render, waitFor, TEST_TIMEOUTS,
  setupInteractiveTest, teardownInteractiveTest,
  simulateNetworkDelay, simulateScroll, createScrollContainer,
  generateScrollItems, saveScrollPosition, restoreScrollPosition
} from './interactive-features-utils';

describe('Advanced Scroll Integration Tests', () => {
    jest.setTimeout(10000);
  let server: any;
  
  beforeEach(() => {
    server = setupInteractiveTest();
  });

  afterEach(() => {
    teardownInteractiveTest();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  it('should handle scroll position restoration', async () => {
    const ScrollRestoreComponent = () => {
      const [items] = React.useState(generateScrollItems(50));
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
        saveScrollPosition(newScrollPosition);
      };
      
      const restoreFromStorage = () => {
        const savedPosition = restoreScrollPosition();
        setScrollPosition(savedPosition);
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
    const scrollProperties = createScrollContainer(300, 2000, 200);
    simulateScroll(container, scrollProperties);
    
    await waitFor(() => {
      expect(getByTestId('current-scroll')).toHaveTextContent('300px');
    });
    
    // Verify scroll position is saved
    expect(localStorage.getItem('scroll_position')).toBe('300');
  });

  it('should handle bidirectional infinite scroll', async () => {
    const BidirectionalScrollComponent = () => {
      const [items, setItems] = React.useState(
        Array.from({ length: 20 }, (_, i) => `Item ${i + 1}`)
      );
      const [isLoadingTop, setIsLoadingTop] = React.useState(false);
      const [isLoadingBottom, setIsLoadingBottom] = React.useState(false);
      
      const loadMoreTop = async () => {
        if (isLoadingTop) return;
        setIsLoadingTop(true);
        await simulateNetworkDelay(100);
        const newItems = Array.from({ length: 10 }, (_, i) => `Top Item ${i + 1}`);
        setItems(prev => [...newItems, ...prev]);
        setIsLoadingTop(false);
      };
      
      const loadMoreBottom = async () => {
        if (isLoadingBottom) return;
        setIsLoadingBottom(true);
        await simulateNetworkDelay(100);
        const currentLength = items.length;
        const newItems = Array.from({ length: 10 }, (_, i) => `Bottom Item ${currentLength + i + 1}`);
        setItems(prev => [...prev, ...newItems]);
        setIsLoadingBottom(false);
      };
      
      const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
        
        // Load more at top
        if (scrollTop < 50 && !isLoadingTop) {
          loadMoreTop();
        }
        
        // Load more at bottom
        if (scrollHeight - scrollTop <= clientHeight + 50 && !isLoadingBottom) {
          loadMoreBottom();
        }
      };
      
      return (
        <div>
          <div
            data-testid="bidirectional-scroll"
            onScroll={handleScroll}
            style={{ height: '300px', overflow: 'auto' }}
          >
            {isLoadingTop && <div data-testid="loading-top">Loading top...</div>}
            {items.map((item, index) => (
              <div key={`${item}-${index}`} style={{ height: '40px', padding: '10px' }}>
                {item}
              </div>
            ))}
            {isLoadingBottom && <div data-testid="loading-bottom">Loading bottom...</div>}
          </div>
          <div data-testid="total-items">{items.length} total items</div>
        </div>
      );
    };
    
    const { getByTestId } = render(<BidirectionalScrollComponent />);
    
    expect(getByTestId('total-items')).toHaveTextContent('20 total items');
    
    const container = getByTestId('bidirectional-scroll');
    
    // Scroll near bottom to trigger bottom load
    const bottomScrollProperties = createScrollContainer(800, 1000, 300);
    simulateScroll(container, bottomScrollProperties);
    
    await waitFor(() => {
      const itemCount = parseInt(getByTestId('total-items').textContent?.match(/\d+/)?.[0] || '0');
      expect(itemCount).toBeGreaterThan(20);
    }, { timeout: TEST_TIMEOUTS.MEDIUM });
  });
});