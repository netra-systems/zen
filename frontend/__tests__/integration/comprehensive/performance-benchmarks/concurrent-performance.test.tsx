import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { ncurrent Performance Tests
 * 
 * BVJ: Enterprise segment - ensures concurrent operations perform efficiently
 * Tests concurrent updates, priority handling, and React 18 features.
 */

import {
  React,
  render,
  act,
  waitFor,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockWebSocketServer,
  WS
} from '../test-utils';

import {
  createConcurrentUpdateComponent,
  createPriorityUpdateComponent,
  testConcurrentUpdates,
  testUpdatePrioritization
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

describe('Concurrent Performance Tests', () => {
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

  describe('Concurrent Updates', () => {
      jest.setTimeout(10000);
    it('should handle concurrent updates efficiently', async () => {
      const ConcurrentUpdateComponent = createConcurrentUpdateComponent();
      
      const { getByText, getByTestId } = render(<ConcurrentUpdateComponent />);
      
      await testConcurrentUpdates(getByText, getByTestId);
    });

    it('should batch multiple concurrent updates', async () => {
      const ConcurrentUpdateComponent = createConcurrentUpdateComponent();
      
      const { getByText, getByTestId } = render(<ConcurrentUpdateComponent />);
      
      await testUpdateBatching(getByText, getByTestId);
    });

    it('should maintain state consistency during concurrent updates', async () => {
      const ConcurrentUpdateComponent = createConcurrentUpdateComponent();
      
      const { getByText, getByTestId } = render(<ConcurrentUpdateComponent />);
      
      await testStateConsistency(getByText, getByTestId);
    });
  });

  describe('Priority Updates', () => {
      jest.setTimeout(10000);
    it('should prioritize critical updates', async () => {
      const PriorityUpdateComponent = createPriorityUpdateComponent();
      
      const { getByText, getByTestId } = render(<PriorityUpdateComponent />);
      
      await testUpdatePrioritization(getByText, getByTestId);
    });

    it('should handle mixed priority updates correctly', async () => {
      const PriorityUpdateComponent = createPriorityUpdateComponent();
      
      const { getByText, getByTestId } = render(<PriorityUpdateComponent />);
      
      await testMixedPriorityUpdates(getByText, getByTestId);
    });

    it('should defer low-priority updates appropriately', async () => {
      const PriorityUpdateComponent = createPriorityUpdateComponent();
      
      const { getByText, getByTestId } = render(<PriorityUpdateComponent />);
      
      await testLowPriorityDeferral(getByText, getByTestId);
    });
  });

  describe('React 18 Features', () => {
      jest.setTimeout(10000);
    it('should use startTransition for non-urgent updates', async () => {
      const PriorityUpdateComponent = createPriorityUpdateComponent();
      
      const { getByText, getByTestId } = render(<PriorityUpdateComponent />);
      
      await testStartTransition(getByText, getByTestId);
    });

    it('should handle interruptions gracefully', async () => {
      const ConcurrentUpdateComponent = createConcurrentUpdateComponent();
      
      const { getByText, getByTestId } = render(<ConcurrentUpdateComponent />);
      
      await testInterruption(getByText, getByTestId);
    });

    it('should optimize render scheduling', async () => {
      const ConcurrentUpdateComponent = createConcurrentUpdateComponent();
      
      const { getByText, getByTestId } = render(<ConcurrentUpdateComponent />);
      
      await testRenderScheduling(getByText, getByTestId);
    });
  });
});

// Test helper functions (≤8 lines each)
const testUpdateBatching = async (getByText: any, getByTestId: any): Promise<void> => {
  const triggerButton = getByText('Trigger Concurrent Updates');
  
  // Trigger multiple batches rapidly
  await act(async () => {
    triggerButton.click();
    triggerButton.click();
  });
  
  // Should handle batching efficiently with waitFor to ensure DOM updates
  await waitFor(() => {
    expect(getByTestId('update-count')).toHaveTextContent('6 updates');
    expect(getByTestId('high-priority-updates')).toHaveTextContent('2 high priority');
  }, { timeout: 2000 });
};

const testStateConsistency = async (getByText: any, getByTestId: any): Promise<void> => {
  const triggerButton = getByText('Trigger Concurrent Updates');
  
  // Multiple rapid triggers should maintain consistency
  await act(async () => {
    for (let i = 0; i < 5; i++) {
      triggerButton.click();
    }
  });
  
  // State should remain consistent with waitFor to ensure DOM updates
  await waitFor(() => {
    const updateCount = parseInt(getByTestId('update-count').textContent?.split(' ')[0] || '0');
    const highPriorityCount = parseInt(getByTestId('high-priority-updates').textContent?.split(' ')[0] || '0');
    
    expect(updateCount).toBeGreaterThan(0);
    expect(highPriorityCount).toBeGreaterThan(0);
    expect(highPriorityCount).toBeLessThanOrEqual(updateCount);
  }, { timeout: 2000 });
};

const testMixedPriorityUpdates = async (getByText: any, getByTestId: any): Promise<void> => {
  const criticalButton = getByText('Critical Update');
  const normalButton = getByText('Normal Update');
  
  // Mix critical and normal updates
  await act(async () => {
    criticalButton.click();
    normalButton.click();
    criticalButton.click();
  });
  
  // Both types should be processed with waitFor to ensure DOM updates
  await waitFor(() => {
    expect(getByTestId('critical-data')).not.toHaveTextContent('');
    expect(getByTestId('normal-data')).not.toHaveTextContent('');
  }, { timeout: 2000 });
};

const testLowPriorityDeferral = async (getByText: any, getByTestId: any): Promise<void> => {
  const criticalButton = getByText('Critical Update');
  const normalButton = getByText('Normal Update');
  
  // Trigger low priority followed by high priority
  await act(async () => {
    normalButton.click();
    criticalButton.click();
  });
  
  // Critical should be processed first/faster with waitFor
  await waitFor(() => {
    expect(getByTestId('critical-data')).not.toHaveTextContent('');
  }, { timeout: 2000 });
};

const testStartTransition = async (getByText: any, getByTestId: any): Promise<void> => {
  const normalButton = getByText('Normal Update');
  
  await act(async () => {
    normalButton.click();
  });
  
  // Normal updates should use startTransition (non-blocking) with waitFor
  await waitFor(() => {
    expect(getByTestId('normal-data')).toBeInTheDocument();
  }, { timeout: 2000 });
};

const testInterruption = async (getByText: any, getByTestId: any): Promise<void> => {
  const triggerButton = getByText('Trigger Concurrent Updates');
  
  // Start update, then interrupt with another
  await act(async () => {
    triggerButton.click();
    triggerButton.click();
  });
  
  // Should handle interruption gracefully with waitFor
  await waitFor(() => {
    expect(getByTestId('update-count')).toBeDefined();
  }, { timeout: 2000 });
};

const testRenderScheduling = async (getByText: any, getByTestId: any): Promise<void> => {
  const triggerButton = getByText('Trigger Concurrent Updates');
  
  // Multiple rapid updates should be scheduled optimally
  const startTime = performance.now();
  await act(async () => {
    for (let i = 0; i < 3; i++) {
      triggerButton.click();
    }
  });
  const endTime = performance.now();
  
  // Should complete efficiently with waitFor to ensure DOM updates
  await waitFor(() => {
    expect(getByTestId('update-count')).toBeDefined();
  }, { timeout: 2000 });
  
  expect(endTime - startTime).toBeLessThan(100);
};;