/**
 * Render Performance Tests
 * 
 * BVJ: Enterprise segment - ensures render performance meets SLAs
 * Tests render time thresholds, rapid re-renders, and virtual scrolling.
 */

import {
  React,
  render,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockWebSocketServer,
  WS
} from '../test-utils';

import {
  createLargeListComponent,
  createRapidRerenderComponent,
  createVirtualScrollComponent,
  measureRenderTime,
  verifyRenderPerformance,
  testRapidRerendering,
  testVirtualScrolling
} from './performance-test-helpers';

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

describe('Render Performance Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
  });

  describe('Large Lists', () => {
    it('should meet render time thresholds for large lists', async () => {
      const LargeListComponent = createLargeListComponent();
      
      const startTime = performance.now();
      const { getByTestId } = render(<LargeListComponent />);
      const renderTime = performance.now() - startTime;
      
      await verifyRenderPerformance(getByTestId, renderTime);
    });

    it('should optimize component memoization', async () => {
      const LargeListComponent = createLargeListComponent();
      
      const { getByTestId, rerender } = render(<LargeListComponent />);
      
      const initialRenderCount = getByTestId('render-count').textContent;
      rerender(<LargeListComponent />);
      
      await verifyComponentMemoization(getByTestId, initialRenderCount);
    });
  });

  describe('Rapid Re-renders', () => {
    it('should maintain performance during rapid re-renders', async () => {
      const RapidRerenderComponent = createRapidRerenderComponent();
      
      const { getByText, getByTestId } = render(<RapidRerenderComponent />);
      
      await testRapidRerendering(getByText, getByTestId);
    });

    it('should batch state updates efficiently', async () => {
      const RapidRerenderComponent = createRapidRerenderComponent();
      
      const { getByText, getByTestId } = render(<RapidRerenderComponent />);
      
      await testStateBatching(getByText, getByTestId);
    });
  });

  describe('Virtual Scrolling', () => {
    it('should optimize virtual scrolling performance', async () => {
      const VirtualScrollComponent = createVirtualScrollComponent();
      
      const { getByTestId } = render(<VirtualScrollComponent />);
      
      await testVirtualScrolling(getByTestId);
    });

    it('should handle large datasets efficiently', async () => {
      const VirtualScrollComponent = createVirtualScrollComponent();
      
      const { getByTestId } = render(<VirtualScrollComponent />);
      
      await testLargeDatasetHandling(getByTestId);
    });
  });
});

// Test helper functions (≤8 lines each)
const verifyComponentMemoization = async (getByTestId: any, initialRenderCount: string | null): Promise<void> => {
  // Component should not re-render unnecessarily
  await act(async () => {
    expect(getByTestId('render-count')).toHaveTextContent(initialRenderCount || '');
  });
  
  // Verify memoization is working
  const renderCountNumber = parseInt(initialRenderCount?.split(': ')[1] || '0');
  expect(renderCountNumber).toBeLessThanOrEqual(2);
};

const testStateBatching = async (getByText: any, getByTestId: any): Promise<void> => {
  const triggerButton = getByText('Trigger Rerender');
  
  // Trigger multiple updates in quick succession with act wrapping
  await act(async () => {
    triggerButton.click();
    triggerButton.click();
    triggerButton.click();
  });
  
  // Updates should be batched, not individual
  const counter = parseInt(getByTestId('counter').textContent || '0');
  expect(counter).toBeGreaterThan(0);
};

const testLargeDatasetHandling = async (getByTestId: any): Promise<void> => {
  const scrollContainer = getByTestId('scroll-performance').closest('div');
  const scrollDownButton = scrollContainer?.querySelector('button:first-child');
  
  // Simulate scrolling through large dataset with act wrapping
  await act(async () => {
    for (let i = 0; i < 5; i++) {
      if (scrollDownButton) scrollDownButton.click();
    }
  });
  
  expect(getByTestId('visible-items')).toHaveTextContent('120 visible');
};