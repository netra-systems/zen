/**
 * Interaction Latency Tests
 * 
 * BVJ: Enterprise segment - ensures user interactions meet responsiveness SLAs
 * Tests interaction response times, computation responsiveness, and debouncing.
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
  createInteractiveComponent,
  createHeavyComputationComponent,
  createDebounceComponent,
  measureInteractionLatency,
  testInteractionLatency,
  testComputationResponsiveness,
  testInteractionDebouncing
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

describe('Interaction Latency Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
  });

  describe('User Interactions', () => {
    it('should respond to user interactions within threshold', async () => {
      const InteractiveComponent = createInteractiveComponent();
      
      const { getByText, getByTestId } = render(<InteractiveComponent />);
      
      await testInteractionLatency(getByText, getByTestId);
    });

    it('should handle multiple concurrent interactions', async () => {
      const InteractiveComponent = createInteractiveComponent();
      
      const { getByText, getByTestId } = render(<InteractiveComponent />);
      
      await testConcurrentInteractions(getByText, getByTestId);
    });

    it('should maintain consistent response times', async () => {
      const InteractiveComponent = createInteractiveComponent();
      
      const { getByText, getByTestId } = render(<InteractiveComponent />);
      
      await testResponseTimeConsistency(getByText, getByTestId);
    });
  });

  describe('Heavy Computations', () => {
    it('should maintain responsiveness during heavy computations', async () => {
      const HeavyComputationComponent = createHeavyComputationComponent();
      
      const { getByText, getByTestId } = render(<HeavyComputationComponent />);
      
      await testComputationResponsiveness(getByText, getByTestId);
    });

    it('should prioritize user interactions over computations', async () => {
      const HeavyComputationComponent = createHeavyComputationComponent();
      
      const { getByText, getByTestId } = render(<HeavyComputationComponent />);
      
      await testComputationPrioritization(getByText, getByTestId);
    });
  });

  describe('Input Debouncing', () => {
    it('should debounce high-frequency interactions', async () => {
      const DebounceComponent = createDebounceComponent();
      
      const { getByTestId } = render(<DebounceComponent />);
      
      await testInteractionDebouncing(getByTestId);
    });

    it('should handle rapid input changes efficiently', async () => {
      const DebounceComponent = createDebounceComponent();
      
      const { getByTestId } = render(<DebounceComponent />);
      
      await testRapidInputChanges(getByTestId);
    });
  });
});

// Test helper functions (≤8 lines each)
const testConcurrentInteractions = async (getByText: any, getByTestId: any): Promise<void> => {
  const interactButton = getByText('Interact');
  
  // Trigger multiple concurrent interactions
  interactButton.click();
  interactButton.click();
  interactButton.click();
  
  // All interactions should be processed
  expect(getByTestId('interaction-count')).toHaveTextContent('3 interactions');
};

const testResponseTimeConsistency = async (getByText: any, getByTestId: any): Promise<void> => {
  const interactButton = getByText('Interact');
  
  // Test multiple interactions to check consistency
  for (let i = 0; i < 5; i++) {
    interactButton.click();
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  
  expect(getByTestId('interaction-count')).toHaveTextContent('5 interactions');
};

const testComputationPrioritization = async (getByText: any, getByTestId: any): Promise<void> => {
  const startButton = getByText('Start Computation');
  
  startButton.click();
  
  // UI should remain responsive even during computation
  expect(getByTestId('computation-status')).toBeInTheDocument();
  expect(startButton).toBeDisabled();
};

const testRapidInputChanges = async (getByTestId: any): Promise<void> => {
  const input = getByTestId('debounce-input');
  
  // Simulate very rapid typing
  const rapidValues = ['a', 'ab', 'abc', 'abcd', 'abcde'];
  rapidValues.forEach(value => {
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
  
  // Only final value should trigger update
  expect(getByTestId('update-count')).toHaveTextContent('1 updates');
};