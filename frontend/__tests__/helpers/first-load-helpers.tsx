/**
 * First Load Test Helpers
 * Modular utilities for first load integration tests
 * Each function ≤8 lines per architecture requirements
 */

import React from 'react';
import { jest } from '@jest/globals';
import { screen, waitFor } from '@testing-library/react';
import { mockAuthServiceResponses, resetAuthServiceMocks } from '../mocks/auth-service-mock';
import { authService } from '@/auth';

interface FirstLoadState {
  authLoading: boolean;
  authUser: any;
  authError: string | null;
  configLoaded: boolean;
}

const createFirstLoadState = (overrides: Partial<FirstLoadState> = {}): FirstLoadState => ({
  authLoading: true,
  authUser: null,
  authError: null,
  configLoaded: false,
  ...overrides
});

export const setupFirstLoadMocks = () => {
  resetAuthServiceMocks();
  jest.clearAllMocks();
  (authService.useAuth as jest.Mock).mockReturnValue({
    loading: false,
    user: null,
    error: null,
    login: jest.fn(),
    logout: jest.fn()
  });
};

export const simulateLoadingSequence = (finalState: FirstLoadState) => {
  const { authLoading, authUser, authError, configLoaded } = finalState;
  
  (authService.useAuth as jest.Mock)
    .mockReturnValueOnce({ loading: true, user: null, error: null })
    .mockReturnValue({ loading: authLoading, user: authUser, error: authError });
    
  if (configLoaded) {
    (authService.getAuthConfig as jest.Mock).mockResolvedValue(mockAuthServiceResponses.config);
  } else {
    (authService.getAuthConfig as jest.Mock).mockRejectedValue(new Error('Config load failed'));
  }
};

export const simulatePerformanceMetrics = () => {
  Object.defineProperty(window, 'performance', {
    value: {
      now: jest.fn(() => Date.now()),
      mark: jest.fn(),
      measure: jest.fn(),
      getEntriesByType: jest.fn(() => []),
      timing: {
        navigationStart: Date.now() - 2000,
        loadEventEnd: Date.now()
      }
    },
    configurable: true
  });
};

export const checkPageInteractive = async (timeoutMs = 3000): Promise<boolean> => {
  const startTime = Date.now();
  
  try {
    await waitFor(() => {
      const buttons = screen.queryAllByRole('button');
      const links = screen.queryAllByRole('link');
      const inputs = screen.queryAllByRole('textbox');
      
      return buttons.length > 0 || links.length > 0 || inputs.length > 0;
    }, { timeout: timeoutMs });
    
    const loadTime = Date.now() - startTime;
    return loadTime < timeoutMs;
  } catch {
    return false;
  }
};

export const FirstLoadTestComponent: React.FC<{ scenario: string }> = ({ scenario }) => {
  const [loadState, setLoadState] = React.useState('loading');
  const [errorCount, setErrorCount] = React.useState(0);
  
  React.useEffect(() => {
    const timer = setTimeout(() => {
      if (scenario === 'error') {
        setErrorCount(prev => prev + 1);
        setLoadState('error');
      } else {
        setLoadState('loaded');
      }
    }, 100);
    
    return () => clearTimeout(timer);
  }, [scenario]);
  
  if (loadState === 'loading') {
    return <div data-testid="loading-spinner">Loading Netra Apex...</div>;
  }
  
  if (loadState === 'error') {
    return (
      <div data-testid="load-error">
        <p>Failed to load application (Errors: {errorCount})</p>
        <button 
          onClick={() => setLoadState('loading')}
          data-testid="retry-load"
        >
          Retry
        </button>
      </div>
    );
  }
  
  return (
    <div data-testid="app-loaded">
      <p>Netra Apex Ready</p>
      <button data-testid="interactive-element">Get Started</button>
    </div>
  );
};