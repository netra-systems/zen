/**
 * Loading State Timeout Fix Verification Test
 * Tests that the useLoadingState hook properly handles timeouts
 * and doesn't get stuck in infinite loading states.
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { useLoadingState } from '@/hooks/useLoadingState';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock store - keep this consistent for all tests
const mockStoreState = {
  activeThreadId: null,
  isThreadLoading: false,
  messages: [],
  isProcessing: false,
  currentRunId: null,
  fastLayerData: null
};

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn((selector) => {
    if (selector) {
      return selector(mockStoreState);
    }
    return mockStoreState;
  })
}));

// Mock WebSocket - will be dynamically configured per test  
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn()
}));

// Test component that uses the loading state hook
const TestComponent: React.FC = () => {
  const {
    shouldShowLoading,
    shouldShowExamplePrompts,
    loadingMessage,
    isInitialized
  } = useLoadingState();

  if (shouldShowLoading) {
    return (
      <div data-testid="loading-state">
        <div data-testid="loading-message">{loadingMessage}</div>
        <div data-testid="initialized">{isInitialized ? 'true' : 'false'}</div>
      </div>
    );
  }

  if (shouldShowExamplePrompts) {
    return <div data-testid="example-prompts">Ready for prompts</div>;
  }

  return <div data-testid="ready-state">Ready</div>;
};

describe('Loading State Timeout Fix', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
    // Ensure we're in test environment
    process.env.NODE_ENV = 'test';
  });

  it('should timeout and initialize in test environment within 1 second', async () => {
    // Get the mock and set it to CONNECTING to simulate timeout scenario
    const { useWebSocket } = require('@/hooks/useWebSocket');
    useWebSocket.mockReturnValue({
      status: 'CONNECTING',
      messages: []
    });
    
    const startTime = Date.now();
    
    render(<TestComponent />);
    
    // Should start in loading state
    expect(screen.getByTestId('loading-state')).toBeInTheDocument();
    expect(screen.getByTestId('initialized')).toHaveTextContent('false');
    
    // Should timeout and initialize within reasonable time (much less than 5 seconds)
    await waitFor(() => {
      expect(screen.getByTestId('initialized')).toHaveTextContent('true');
    }, { timeout: 2000 }); // Allow 2 seconds max for timeout
    
    const elapsedTime = Date.now() - startTime;
    console.log(`Loading state initialized in ${elapsedTime}ms`);
    
    // Should be much faster than the old 5 second timeout
    expect(elapsedTime).toBeLessThan(1000); // Should be under 1 second in test env
  }, 10000);

  it('should eventually transition to ready state after initialization', async () => {
    // Get the mock and set WebSocket as OPEN from the start to allow proper state transition
    const { useWebSocket } = require('@/hooks/useWebSocket');
    useWebSocket.mockReturnValue({
      status: 'OPEN',
      messages: []
    });
    
    render(<TestComponent />);
    
    // Should start in loading state
    expect(screen.getByTestId('loading-state')).toBeInTheDocument();
    expect(screen.getByTestId('initialized')).toHaveTextContent('false');
    
    // Wait for initialization to complete (should be fast in test env)
    await waitFor(() => {
      const initializedElement = screen.getByTestId('initialized');
      expect(initializedElement).toHaveTextContent('true');
    }, { timeout: 1000 }); // Reduced timeout since it should be fast
    
    // After initialization, should eventually show ready state or example prompts
    // The component might still be in loading momentarily while state transitions
    await waitFor(() => {
      const hasReadyState = screen.queryByTestId('ready-state') || screen.queryByTestId('example-prompts');
      expect(hasReadyState).toBeInTheDocument();
    }, { timeout: 2000 }); // Give some time for state transition
  }, 10000);

  it('should detect test environment correctly', () => {
    // Verify that we're properly detecting test environment
    const isTestEnv = process.env.NODE_ENV === 'test' || process.env.JEST_WORKER_ID !== undefined;
    expect(isTestEnv).toBe(true);
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});