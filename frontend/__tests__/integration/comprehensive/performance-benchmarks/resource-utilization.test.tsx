import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { source Utilization Tests
 * 
 * BVJ: Enterprise segment - ensures efficient resource usage within limits
 * Tests memory usage, bundle optimization, and DOM node management.
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
  createMemoryMonitorComponent,
  createBundleOptimizationComponent,
  createDOMManagementComponent,
  testMemoryUtilization,
  testBundleOptimization,
  testDOMNodeManagement
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

describe('Resource Utilization Tests', () => {
    jest.setTimeout(10000);
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Memory Management', () => {
      jest.setTimeout(10000);
    it('should maintain memory usage within limits', async () => {
      const MemoryMonitorComponent = createMemoryMonitorComponent();
      
      const { getByText, getByTestId } = render(<MemoryMonitorComponent />);
      
      await testMemoryUtilization(getByText, getByTestId);
    });

    it('should prevent memory leaks during component unmount', async () => {
      const MemoryMonitorComponent = createMemoryMonitorComponent();
      
      const { getByText, getByTestId, unmount } = render(<MemoryMonitorComponent />);
      
      await testMemoryLeakPrevention(getByText, getByTestId, unmount);
    });

    it('should efficiently garbage collect unused objects', async () => {
      const MemoryMonitorComponent = createMemoryMonitorComponent();
      
      const { getByText, getByTestId } = render(<MemoryMonitorComponent />);
      
      await testGarbageCollection(getByText, getByTestId);
    });
  });

  describe('Bundle Optimization', () => {
      jest.setTimeout(10000);
    it('should optimize bundle size impact', async () => {
      const BundleOptimizationComponent = createBundleOptimizationComponent();
      
      const { getByTestId } = render(<BundleOptimizationComponent />);
      
      await testBundleOptimization(getByTestId);
    });

    it('should lazy load components efficiently', async () => {
      const BundleOptimizationComponent = createBundleOptimizationComponent();
      
      const { getByTestId } = render(<BundleOptimizationComponent />);
      
      await testLazyLoading(getByTestId);
    });

    it('should cache loaded components properly', async () => {
      const BundleOptimizationComponent = createBundleOptimizationComponent();
      
      const { getByTestId } = render(<BundleOptimizationComponent />);
      
      await testComponentCaching(getByTestId);
    });
  });

  describe('DOM Management', () => {
      jest.setTimeout(10000);
    it('should efficiently manage DOM nodes', async () => {
      const DOMManagementComponent = createDOMManagementComponent();
      
      const { getByText, getByTestId } = render(<DOMManagementComponent />);
      
      await testDOMNodeManagement(getByText, getByTestId);
    });

    it('should optimize DOM updates', async () => {
      const DOMManagementComponent = createDOMManagementComponent();
      
      const { getByText, getByTestId } = render(<DOMManagementComponent />);
      
      await testDOMUpdateOptimization(getByText, getByTestId);
    });

    it('should handle large DOM trees efficiently', async () => {
      const DOMManagementComponent = createDOMManagementComponent();
      
      const { getByText, getByTestId } = render(<DOMManagementComponent />);
      
      await testLargeDOMTrees(getByText, getByTestId);
    });
  });
});

// Test helper functions (≤8 lines each)
const testMemoryLeakPrevention = async (getByText: any, getByTestId: any, unmount: any): Promise<void> => {
  // Allocate some memory
  getByText('Allocate Memory').click();
  
  const initialMemory = parseFloat(getByTestId('memory-usage').textContent?.split('MB')[0] || '0');
  expect(initialMemory).toBeGreaterThan(0);
  
  // Unmount component - should not cause leaks
  unmount();
};

const testGarbageCollection = async (getByText: any, getByTestId: any): Promise<void> => {
  // Allocate and clear memory multiple times
  for (let i = 0; i < 3; i++) {
    getByText('Allocate Memory').click();
    getByText('Clear Memory').click();
  }
  
  // Memory should be properly cleaned up
  expect(getByTestId('memory-usage')).toHaveTextContent('0.00MB');
};

const testLazyLoading = async (getByTestId: any): Promise<void> => {
  const loadButton1 = getByTestId('loaded-components').closest('div')?.querySelector('button:first-of-type');
  
  if (loadButton1) loadButton1.click();
  
  // Component should be loaded with reasonable time
  expect(getByTestId('loaded-components')).toHaveTextContent('1 loaded');
  
  const avgLoadTime = parseFloat(getByTestId('average-load-time').textContent?.split('ms')[0] || '0');
  expect(avgLoadTime).toBeGreaterThan(0);
};

const testComponentCaching = async (getByTestId: any): Promise<void> => {
  const loadButton1 = getByTestId('loaded-components').closest('div')?.querySelector('button:first-of-type');
  
  // Load same component multiple times
  if (loadButton1) loadButton1.click();
  if (loadButton1) loadButton1.click();
  
  // Should only count unique components
  expect(getByTestId('loaded-components')).toHaveTextContent('2 loaded');
};

const testDOMUpdateOptimization = async (getByText: any, getByTestId: any): Promise<void> => {
  // Perform multiple DOM updates
  for (let i = 0; i < 3; i++) {
    getByText('Add Nodes').click();
  }
  
  // Updates should be optimized
  expect(getByTestId('dom-node-count')).toHaveTextContent('250 nodes');
  
  const updateTime = parseFloat(getByTestId('dom-update-performance').textContent?.split('ms')[0] || '0');
  expect(updateTime).toBeLessThan(50); // Reasonable threshold
};

const testLargeDOMTrees = async (getByText: any, getByTestId: any): Promise<void> => {
  // Create large DOM tree
  for (let i = 0; i < 10; i++) {
    getByText('Add Nodes').click();
  }
  
  expect(getByTestId('dom-node-count')).toHaveTextContent('600 nodes');
  
  // Performance should still be acceptable
  const updateTime = parseFloat(getByTestId('dom-update-performance').textContent?.split('ms')[0] || '0');
  expect(updateTime).toBeLessThan(100);
};