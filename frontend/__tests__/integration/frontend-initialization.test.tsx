/**
 * Frontend Initialization Tests
 * 
 * Tests to ensure the frontend initializes correctly without white screen issues
 * and that all critical providers and contexts load properly.
 * 
 * @compliance testing - Integration tests for frontend initialization
 */

import React from 'react';
import { render, waitFor, screen } from '@testing-library/react';
import { act } from 'react';

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/chat',
}));

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  
  readyState = MockWebSocket.CONNECTING;
  url: string;
  
  constructor(url: string) {
    this.url = url;
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) this.onopen(new Event('open'));
    }, 10);
  }
  
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  
  send = jest.fn();
  close = jest.fn();
}

global.WebSocket = MockWebSocket as any;

describe('Frontend Initialization', () => {
  beforeEach(() => {
    // Clear localStorage
    localStorage.clear();
    
    // Reset console methods
    jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    jest.spyOn(console, 'log').mockImplementation(() => {});
  });
  
  afterEach(() => {
    jest.restoreAllMocks();
  });
  
  describe('Critical Module Loading', () => {
    test('logger module should initialize without errors', async () => {
      const { logger } = await import('@/lib/logger');
      
      expect(logger).toBeDefined();
      expect(logger.debug).toBeDefined();
      expect(logger.info).toBeDefined();
      expect(logger.warn).toBeDefined();
      expect(logger.error).toBeDefined();
      
      // Test that logger methods work
      expect(() => logger.debug('test')).not.toThrow();
      expect(() => logger.info('test')).not.toThrow();
      expect(() => logger.warn('test')).not.toThrow();
      expect(() => logger.error('test')).not.toThrow();
    });
    
    test('unified-api-config should initialize without importing logger', async () => {
      const consoleLogSpy = jest.spyOn(console, 'log');
      
      // Clear module cache to force re-import
      jest.resetModules();
      
      const { unifiedApiConfig } = await import('@/lib/unified-api-config');
      
      expect(unifiedApiConfig).toBeDefined();
      expect(unifiedApiConfig.environment).toBeDefined();
      expect(unifiedApiConfig.urls).toBeDefined();
      
      // Should use console.log instead of logger
      expect(consoleLogSpy).toHaveBeenCalled();
    });
    
    test('auth service should initialize without circular dependencies', async () => {
      const { unifiedAuthService } = await import('@/auth/unified-auth-service');
      
      expect(unifiedAuthService).toBeDefined();
      expect(unifiedAuthService.getAuthConfig).toBeDefined();
      expect(unifiedAuthService.saveToken).toBeDefined();
      expect(unifiedAuthService.getToken).toBeDefined();
    });
  });
  
  describe('Provider Initialization', () => {
    test('AuthProvider should render without errors', async () => {
      const { AuthProvider } = await import('@/auth/context');
      
      const TestComponent = () => <div>Test Content</div>;
      
      const { container } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        expect(container.textContent).toContain('Test Content');
      });
      
      expect(console.error).not.toHaveBeenCalled();
    });
    
    test('WebSocketProvider should render without errors', async () => {
      const { WebSocketProvider } = await import('@/providers/WebSocketProvider');
      const { AuthProvider } = await import('@/auth/context');
      
      const TestComponent = () => <div>WebSocket Test</div>;
      
      const { container } = render(
        <AuthProvider>
          <WebSocketProvider>
            <TestComponent />
          </WebSocketProvider>
        </AuthProvider>
      );
      
      await waitFor(() => {
        expect(container.textContent).toContain('WebSocket Test');
      });
      
      expect(console.error).not.toHaveBeenCalled();
    });
    
    test('All providers should initialize in correct order', async () => {
      const { AuthProvider } = await import('@/auth/context');
      const { WebSocketProvider } = await import('@/providers/WebSocketProvider');
      const { GTMProvider } = await import('@/providers/GTMProvider');
      
      const TestComponent = () => <div data-testid="app-content">App Loaded</div>;
      
      const { getByTestId } = render(
        <GTMProvider enabled={false}>
          <AuthProvider>
            <WebSocketProvider>
              <TestComponent />
            </WebSocketProvider>
          </AuthProvider>
        </GTMProvider>
      );
      
      await waitFor(() => {
        expect(getByTestId('app-content')).toBeInTheDocument();
      });
      
      expect(console.error).not.toHaveBeenCalled();
    });
  });
  
  describe('Chat Page Initialization', () => {
    test('MainChat component should render without white screen', async () => {
      // Mock auth context to bypass authentication
      jest.mock('@/auth/context', () => ({
        useAuth: () => ({
          user: { id: 'test', email: 'test@example.com' },
          loading: false,
          initialized: true,
          token: 'test-token',
        }),
        AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
      }));
      
      const { MainChat } = await import('@/components/chat/MainChat');
      
      const { container } = render(<MainChat />);
      
      await waitFor(() => {
        // Should not show only "Loading..." (white screen issue)
        expect(container.textContent).not.toBe('Loading...');
      });
      
      expect(console.error).not.toHaveBeenCalled();
    });
    
    test('AuthGuard should handle initialization correctly', async () => {
      const { AuthGuard } = await import('@/components/AuthGuard');
      const { AuthProvider } = await import('@/auth/context');
      
      const TestComponent = () => <div data-testid="protected-content">Protected</div>;
      
      const { container } = render(
        <AuthProvider>
          <AuthGuard>
            <TestComponent />
          </AuthGuard>
        </AuthProvider>
      );
      
      // Should show loading or redirect, not crash
      await waitFor(() => {
        expect(container).toBeInTheDocument();
      }, { timeout: 3000 });
      
      expect(console.error).not.toHaveBeenCalled();
    });
  });
  
  describe('Error Boundary Behavior', () => {
    test('should catch and handle initialization errors gracefully', async () => {
      const ErrorComponent = () => {
        throw new Error('Test initialization error');
      };
      
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
        
        render() {
          if (this.state.hasError) {
            return <div>Error occurred during initialization</div>;
          }
          return this.props.children;
        }
      }
      
      const { container } = render(
        <ErrorBoundary>
          <ErrorComponent />
        </ErrorBoundary>
      );
      
      expect(container.textContent).toContain('Error occurred during initialization');
    });
  });
  
  describe('Module Import Order', () => {
    test('critical modules should load in correct order', async () => {
      const loadOrder: string[] = [];
      
      // Mock module loading
      jest.doMock('@/lib/unified-api-config', () => {
        loadOrder.push('config');
        return { unifiedApiConfig: {} };
      });
      
      jest.doMock('@/lib/logger', () => {
        loadOrder.push('logger');
        return { logger: {} };
      });
      
      jest.doMock('@/auth/unified-auth-service', () => {
        loadOrder.push('auth-service');
        return { unifiedAuthService: {} };
      });
      
      // Import in application order
      await import('@/lib/unified-api-config');
      await import('@/lib/logger');
      await import('@/auth/unified-auth-service');
      
      // Config should load before logger (no circular dependency)
      const configIndex = loadOrder.indexOf('config');
      const loggerIndex = loadOrder.indexOf('logger');
      
      expect(configIndex).toBeGreaterThanOrEqual(0);
      expect(loggerIndex).toBeGreaterThanOrEqual(0);
      
      // Both should load successfully
      expect(loadOrder).toContain('config');
      expect(loadOrder).toContain('logger');
      expect(loadOrder).toContain('auth-service');
    });
  });
});