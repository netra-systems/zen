/**
 * Initial State Test Helpers
 * Modular utilities for initial state integration tests
 * Each function ≤8 lines per architecture requirements
 */

import React from 'react';
import { jest } from '@jest/globals';
// Auth service mocks handled by test setup
import { useAppStore } from '@/store/app';
import { wrapStateSetterWithAct } from '../test-utils/react-act-utils';

interface MockStorageItem {
  key: string;
  value: string;
}

interface MockCookie {
  name: string;
  value: string;
  expires?: Date;
}

export const createMockStorage = (items: MockStorageItem[] = []) => {
  const storage: Record<string, string> = {};
  items.forEach(({ key, value }) => {
    storage[key] = value;
  });
  
  return {
    getItem: jest.fn((key: string) => storage[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      storage[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete storage[key];
    }),
    clear: jest.fn(() => {
      Object.keys(storage).forEach(key => delete storage[key]);
    }),
    length: Object.keys(storage).length,
    key: jest.fn((index: number) => Object.keys(storage)[index] || null)
  };
};

export const setupMockCookies = (cookies: MockCookie[] = []) => {
  const cookieString = cookies
    .map(cookie => `${cookie.name}=${cookie.value}`)
    .join('; ');
    
  Object.defineProperty(document, 'cookie', {
    writable: true,
    value: cookieString
  });
};

export const setupInitialStateMocks = () => {
  jest.clearAllMocks();
  
  jest.mocked(useAppStore).mockReturnValue({
    isSidebarCollapsed: false,
    toggleSidebar: jest.fn()
  });
  
  Object.defineProperty(window, 'localStorage', {
    value: createMockStorage(),
    configurable: true
  });
  
  Object.defineProperty(window, 'sessionStorage', {
    value: createMockStorage(),
    configurable: true
  });
  
  setupMockCookies();
};

export const validateStorageAccess = () => {
  expect(() => localStorage.getItem('test')).not.toThrow();
  expect(() => sessionStorage.getItem('test')).not.toThrow();
};

export const validateCookieAccess = () => {
  expect(() => document.cookie).not.toThrow();
  expect(typeof document.cookie).toBe('string');
};

export const InitialStateTestComponent: React.FC<{ testType: string }> = ({ testType }) => {
  const [stateLoaded, setStateLoaded] = React.useState(false);
  const [errors, setErrors] = React.useState<string[]>([]);
  
  React.useEffect(() => {
    const checkInitialState = async () => {
      try {
        if (testType === 'localStorage') {
          const saved = localStorage.getItem('app-storage');
          if (saved) {
            JSON.parse(saved);
          }
        }
        
        if (testType === 'sessionStorage') {
          const session = sessionStorage.getItem('user-session');
          if (session) {
            JSON.parse(session);
          }
        }
        
        if (testType === 'cookies') {
          const authCookie = document.cookie
            .split(';')
            .find(c => c.trim().startsWith('auth_token='));
          
          if (authCookie) {
            const token = authCookie.split('=')[1];
            if (!token) throw new Error('Invalid auth cookie');
          }
        }
        
        setStateLoaded(true);
      } catch (error) {
        setErrors(prev => [...prev, (error as Error).message]);
      }
    };
    
    checkInitialState();
  }, [testType]);
  
  return (
    <div data-testid="initial-state-component">
      {stateLoaded ? (
        <div data-testid="state-loaded">
          <p>Initial state loaded successfully</p>
          <p data-testid="test-type">Type: {testType}</p>
        </div>
      ) : (
        <div data-testid="state-loading">Loading initial state...</div>
      )}
      
      {errors.length > 0 && (
        <div data-testid="state-errors">
          {errors.map((error, idx) => (
            <p key={idx} data-testid={`error-${idx}`}>
              Error: {error}
            </p>
          ))}
        </div>
      )}
    </div>
  );
};

export const WebSocketConnectionComponent: React.FC = () => {
  const [connectionState, setConnectionState] = React.useState('connecting');
  const [attempts, setAttempts] = React.useState(0);
  
  // Wrap state setters with act() to prevent warnings  
  const safeSetConnectionState = wrapStateSetterWithAct(setConnectionState);
  const safeSetAttempts = wrapStateSetterWithAct(setAttempts);
  
  React.useEffect(() => {
    const connectWebSocket = async () => {
      safeSetAttempts(prev => prev + 1);
      
      try {
        await new Promise(resolve => setTimeout(resolve, 100));
        
        const mockWebSocketService = require('@/services/webSocketService').webSocketService;
        if (mockWebSocketService.isConnected()) {
          safeSetConnectionState('connected');
        } else {
          safeSetConnectionState('failed');
        }
      } catch (error) {
        safeSetConnectionState('error');
      }
    };
    
    connectWebSocket();
  }, []);
  
  return (
    <div data-testid="websocket-component">
      <div data-testid="connection-state">
        Connection: {connectionState}
      </div>
      <div data-testid="connection-attempts">
        Attempts: {attempts}
      </div>
      
      {connectionState === 'failed' && (
        <button 
          onClick={() => safeSetConnectionState('connecting')}
          data-testid="retry-connection"
        >
          Retry Connection
        </button>
      )}
    </div>
  );
};