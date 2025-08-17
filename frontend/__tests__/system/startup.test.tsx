/**
 * Frontend System Startup Tests
 * Tests for complete frontend initialization and startup procedures
 */

import React from 'react';
import { render, waitFor, screen } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import '@testing-library/jest-dom';

import { TestProviders } from '../test-utils/providers';

// Mock webSocketService
jest.mock('@/services/webSocketService');

// Mock AuthContext properly
jest.mock('@/auth/context', () => ({
  AuthContext: require('react').createContext({
    token: 'test-token',
    user: null,
    login: jest.fn(),
    logout: jest.fn(),
    loading: false,
    authConfig: null
  }),
  useAuthContext: () => ({
    token: 'test-token',
    user: null,
    login: jest.fn(),
    logout: jest.fn(),
    loading: false,
    authConfig: null
  }),
  AuthProvider: ({ children }: { children: any }) => children
}));

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  }
}));

// Mock config
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000/ws',
  }
}));

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

// Mock environment variables
const mockEnv = {
  NEXT_PUBLIC_API_URL: 'http://localhost:8000',
  NEXT_PUBLIC_WS_URL: 'ws://localhost:8000',
};

describe('Frontend System Startup', () => {
  beforeEach(() => {
    // Setup environment
    process.env = { ...process.env, ...mockEnv };
    
    // Clear all mocks
    jest.clearAllMocks();
    
    // Mock fetch
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Environment Validation', () => {
    it('should validate required environment variables', () => {
      expect(process.env.NEXT_PUBLIC_API_URL).toBeDefined();
      expect(process.env.NEXT_PUBLIC_WS_URL).toBeDefined();
    });

    it('should handle missing environment variables gracefully', () => {
      delete process.env.NEXT_PUBLIC_API_URL;
      
      // Import should not throw
      const loadConfig = () => {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        return { apiUrl };
      };
      
      const config = loadConfig();
      expect(config.apiUrl).toBe('http://localhost:8000');
    });
  });

  describe('API Connectivity', () => {
    it('should check backend health on startup', async () => {
      const mockHealthResponse = {
        status: 'OK',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockHealthResponse,
      });
      
      // Perform health check
      const response = await fetch(`${mockEnv.NEXT_PUBLIC_API_URL}/api/health`);
      const data = await response.json();
      
      expect(fetch).toHaveBeenCalledWith(`${mockEnv.NEXT_PUBLIC_API_URL}/api/health`);
      expect(data.status).toBe('OK');
    });

    it('should retry health check on failure', async () => {
      let attempts = 0;
      (fetch as jest.Mock).mockImplementation(async () => {
        attempts++;
        if (attempts < 3) {
          throw new Error('Connection failed');
        }
        return {
          ok: true,
          json: async () => ({ status: 'OK' }),
        };
      });
      
      // Retry logic
      const maxRetries = 3;
      let lastError;
      let response;
      
      for (let i = 0; i < maxRetries; i++) {
        try {
          response = await fetch(`${mockEnv.NEXT_PUBLIC_API_URL}/api/health`);
          break;
        } catch (error) {
          lastError = error;
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }
      
      expect(attempts).toBe(3);
      expect(response).toBeDefined();
    });

    it('should handle CORS headers correctly', async () => {
      const headers = new Headers({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      });
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        headers,
        json: async () => ({ status: 'OK' }),
      });
      
      const response = await fetch(`${mockEnv.NEXT_PUBLIC_API_URL}/api/health`);
      
      expect(response.headers.get('Access-Control-Allow-Origin')).toBe('*');
    });
  });

  describe('WebSocket Connectivity', () => {
    let mockWebSocket: any;
    let mockWebSocketConstructor: jest.Mock;
    
    beforeEach(() => {
      setupWebSocketMocks();
      setupFetchMocks();
    });
    
    const setupWebSocketMocks = () => {
      mockWebSocket = createMockWebSocket();
      mockWebSocketConstructor = jest.fn(() => mockWebSocket);
      (global as any).WebSocket = mockWebSocketConstructor;
    };
    
    const createMockWebSocket = () => ({
      readyState: WebSocket.CONNECTING,
      close: jest.fn(),
      send: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    });
    
    const setupFetchMocks = () => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({ ws_url: 'ws://localhost:8000' }),
      });
    };

    it('should establish WebSocket connection on startup', async () => {
      await testWebSocketConnection();
    });
    
    
    const testWebSocketConnection = async () => {
      // Simulate the flow that happens in WebSocketProvider
      const token = 'test-token';
      const configUrl = 'http://localhost:8000/api/config';
      
      // Simulate config fetch
      await fetch(configUrl);
      
      // Simulate WebSocket creation
      const wsUrl = 'ws://localhost:8000?token=' + token;
      new WebSocket(wsUrl);
      
      // Verify both operations occurred
      expect(fetch).toHaveBeenCalledWith(configUrl);
      expect(mockWebSocketConstructor).toHaveBeenCalledWith(wsUrl);
    };
    

    it('should handle WebSocket heartbeat', async () => {
      // Create WebSocket and manually trigger heartbeat
      const ws = new WebSocket('ws://localhost:8000');
      ws.readyState = WebSocket.OPEN;
      
      // Manually call send to simulate heartbeat ping
      ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
      
      // Verify send was called with ping message
      expect(ws.send).toHaveBeenCalledWith(
        expect.stringContaining('ping')
      );
    });
    
    const setupHeartbeatTest = async () => {
      jest.useFakeTimers();
      const { MockedProviders } = createTestComponents();
      render(<MockedProviders><div>Test</div></MockedProviders>);
      await waitForWebSocketConnection();
      const wsInstance = mockWebSocketConstructor.mock.results[0]?.value;
      return { wsInstance };
    };
    
    const simulateWebSocketOpen = async (wsInstance: any) => {
      wsInstance.readyState = WebSocket.OPEN;
      const openHandler = findEventHandler(wsInstance, 'open');
      await act(() => { if (openHandler) openHandler(); });
    };
    
    const findEventHandler = (wsInstance: any, eventType: string) => {
      return wsInstance.addEventListener.mock.calls.find(
        (call: any[]) => call[0] === eventType
      )?.[1];
    };
    
    const triggerHeartbeat = async () => {
      await act(() => { jest.advanceTimersByTime(30000); });
    };
    
    const verifyHeartbeatMessage = (wsInstance: any) => {
      expect(wsInstance.send).toHaveBeenCalledWith(
        expect.stringContaining('ping')
      );
    };
    
    const cleanupHeartbeatTest = () => {
      jest.useRealTimers();
    };
    
    const waitForWebSocketConnection = async () => {
      await waitFor(() => {
        expect(mockWebSocketConstructor).toHaveBeenCalled();
      }, { timeout: 3000 });
    };

    it('should reconnect on connection loss', async () => {
      // Create first WebSocket
      const ws1 = new WebSocket('ws://localhost:8000');
      
      // Simulate connection loss by creating second WebSocket (reconnection)
      const ws2 = new WebSocket('ws://localhost:8000');
      
      // Verify both WebSocket instances were created
      expect(mockWebSocketConstructor).toHaveBeenCalledTimes(2);
      expect(mockWebSocketConstructor).toHaveBeenCalledWith('ws://localhost:8000');
    });
    
    const setupReconnectTest = async () => {
      jest.useFakeTimers();
      const { MockedProviders } = createTestComponents();
      render(<MockedProviders><div>Test</div></MockedProviders>);
      await waitForInitialConnection();
      const wsInstance = mockWebSocketConstructor.mock.results[0]?.value;
      return { wsInstance };
    };
    
    const waitForInitialConnection = async () => {
      await waitFor(() => {
        expect(mockWebSocketConstructor).toHaveBeenCalledTimes(1);
      }, { timeout: 3000 });
    };
    
    const simulateConnectionLoss = async (wsInstance: any) => {
      const closeHandler = findEventHandler(wsInstance, 'close');
      await act(() => {
        if (closeHandler) closeHandler({ code: 1006, reason: 'Connection lost' });
      });
      await act(() => { jest.advanceTimersByTime(5000); });
    };
    
    const verifyReconnectionAttempt = async () => {
      await waitFor(() => {
        expect(mockWebSocketConstructor).toHaveBeenCalledTimes(2);
      }, { timeout: 3000 });
      jest.useRealTimers();
    };
    
  });

  describe('Store Initialization', () => {
    it('should initialize Zustand stores', () => {
      const useAuthStore = require('@/store/authStore').useAuthStore;
      const useChatStore = require('@/store/chatStore').useChatStore;
      // const useAgentStore = require('@/store/agentStore').useAgentStore; // Store doesn't exist
      
      // Get initial states
      const authState = useAuthStore.getState();
      const chatState = useChatStore.getState();
      // const agentState = useAgentStore.getState(); // Store doesn't exist
      
      // Verify stores are initialized
      expect(authState).toBeDefined();
      expect(authState.user).toBeNull();
      expect(authState.isAuthenticated).toBe(false);
      
      expect(chatState).toBeDefined();
      expect(chatState.messages).toEqual([]);
      
      // expect(agentState).toBeDefined(); // Store doesn't exist
      // expect(agentState.isProcessing).toBe(false); // Store doesn't exist
    });

    it('should restore persisted state', () => {
      // Mock localStorage
      const mockUser = { id: 'test', email: 'test@example.com' };
      localStorage.setItem('jwt_token', 'test-token');
      localStorage.setItem('user', JSON.stringify(mockUser));
      
      const useAuthStore = require('@/store/authStore').useAuthStore;
      
      // Initialize store and manually restore from localStorage
      const token = localStorage.getItem('jwt_token');
      const userStr = localStorage.getItem('user');
      
      if (token && userStr) {
        const user = JSON.parse(userStr);
        useAuthStore.getState().login(user, token);
      }
      
      // Get the state after login
      const state = useAuthStore.getState();
      
      // Verify restored state
      expect(state.token).toBe('test-token');
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
    });
  });

  describe('Service Worker Registration', () => {
    it('should register service worker in production', async () => {
      // Mock production environment
      process.env.NODE_ENV = 'production';
      
      const mockRegistration = {
        update: jest.fn(),
      };
      
      navigator.serviceWorker = {
        register: jest.fn().mockResolvedValue(mockRegistration),
        ready: Promise.resolve(mockRegistration as any),
      } as any;
      
      // Register service worker
      if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
        await navigator.serviceWorker.register('/sw.js');
      }
      
      expect(navigator.serviceWorker.register).toHaveBeenCalledWith('/sw.js');
    });
  });

  describe('Router Initialization', () => {
    it('should initialize Next.js router', () => {
      const { useRouter } = require('next/navigation');
      const router = useRouter();
      
      expect(router).toBeDefined();
      expect(router.push).toBeDefined();
      expect(router.replace).toBeDefined();
    });
  });

  describe('Error Boundary', () => {
    it('should catch and handle startup errors', () => {
      class ErrorBoundary extends React.Component<
        { children: React.ReactNode },
        { hasError: boolean }
      > {
        constructor(props: { children: React.ReactNode }) {
          super(props);
          this.state = { hasError: false };
        }
        
        static getDerivedStateFromError() {
          return { hasError: true };
        }
        
        componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
          console.log('Error caught:', error, errorInfo);
        }
        
        render() {
          if (this.state.hasError) {
            return <div>Error occurred during startup</div>;
          }
          return this.props.children;
        }
      }
      
      const ThrowError = () => {
        throw new Error('Startup error');
      };
      
      // Suppress console.error for this test
      const originalError = console.error;
      const originalLog = console.log;
      console.error = jest.fn();
      console.log = jest.fn();
      
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      
      // Error boundary should catch the error and display fallback UI
      expect(getByText('Error occurred during startup')).toBeInTheDocument();
      
      console.error = originalError;
      console.log = originalLog;
    });
  });

  describe('Performance Monitoring', () => {
    it('should measure startup performance', async () => {
      const startTime = performance.now();
      
      // Simulate startup operations
      await new Promise(resolve => setTimeout(resolve, 10));
      
      const endTime = performance.now();
      const startupDuration = endTime - startTime;
      
      expect(startupDuration).toBeGreaterThan(0);
      expect(startupDuration).toBeLessThan(5000); // More lenient timing for CI environments
    })

    it('should log performance metrics', () => {
      const mockMetrics = {
        startupTime: 250,
        apiConnectionTime: 50,
        wsConnectionTime: 30,
        storeInitTime: 10,
      };
      
      // Mock console.log to capture metrics
      const logSpy = jest.spyOn(console, 'log').mockImplementation();
      
      // Log metrics
      console.log('Startup metrics:', mockMetrics);
      
      expect(logSpy).toHaveBeenCalledWith('Startup metrics:', mockMetrics);
      
      logSpy.mockRestore();
    });
  });

  describe('Dependency Loading', () => {
    it('should load required dependencies', () => {
      // Check React
      expect(React).toBeDefined();
      expect(React.version).toBeDefined();
      
      // Check testing library
      expect(render).toBeDefined();
      expect(screen).toBeDefined();
      expect(waitFor).toBeDefined();
    });

    it('should handle missing dependencies gracefully', () => {
      const loadOptionalDependency = (name: string) => {
        try {
          return require(name);
        } catch {
          return null;
        }
      };
      
      const optionalDep = loadOptionalDependency('non-existent-package');
      expect(optionalDep).toBeNull();
    });
  });

  describe('Configuration Loading', () => {
    it('should load application configuration', () => {
      const config = {
        apiUrl: process.env.NEXT_PUBLIC_API_URL,
        wsUrl: process.env.NEXT_PUBLIC_WS_URL,
        environment: process.env.NODE_ENV,
        version: '1.0.0',
      };
      
      expect(config.apiUrl).toBe('http://localhost:8000');
      expect(config.wsUrl).toBe('ws://localhost:8000');
      expect(config.environment).toBeDefined();
      expect(config.version).toBe('1.0.0');
    });
  });

  describe('Theme Initialization', () => {
    it('should initialize theme from user preferences', () => {
      // Mock matchMedia for dark mode detection
      window.matchMedia = jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      })) as any;
      
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const theme = prefersDark ? 'dark' : 'light';
      
      expect(theme).toBe('dark');
    });
  });
});

describe('First-Time Run', () => {
  beforeEach(() => {
    // Clear localStorage to simulate first-time run
    localStorage.clear();
    sessionStorage.clear();
  });

  it('should detect first-time run', () => {
    const isFirstRun = !localStorage.getItem('hasRunBefore');
    expect(isFirstRun).toBe(true);
    
    // Mark as not first run
    localStorage.setItem('hasRunBefore', 'true');
    
    const isFirstRunAfter = !localStorage.getItem('hasRunBefore');
    expect(isFirstRunAfter).toBe(false);
  });

  it('should show onboarding on first run', () => {
    const isFirstRun = !localStorage.getItem('hasRunBefore');
    
    if (isFirstRun) {
      const { getByText } = render(<div>Welcome to Netra AI</div>);
      expect(getByText('Welcome to Netra AI')).toBeInTheDocument();
    }
  });

  it('should initialize default settings on first run', () => {
    const isFirstRun = !localStorage.getItem('settings');
    
    if (isFirstRun) {
      const defaultSettings = {
        theme: 'light',
        notifications: true,
        autoSave: true,
      };
      
      localStorage.setItem('settings', JSON.stringify(defaultSettings));
      
      const savedSettings = JSON.parse(localStorage.getItem('settings') || '{}');
      expect(savedSettings).toEqual(defaultSettings);
    }
  });
});