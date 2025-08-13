import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AuthProvider } from '@/auth/context';

// Mock next/navigation for Next.js components
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      pathname: '/',
      query: {},
      asPath: '/',
      route: '/',
      events: {
        on: jest.fn(),
        off: jest.fn(),
        emit: jest.fn(),
      },
    };
  },
  usePathname() {
    return '/';
  },
  useSearchParams() {
    return new URLSearchParams();
  },
  useParams() {
    return {};
  },
}));

// Mock WebSocket
global.WebSocket = jest.fn(() => ({
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN,
})) as any;

interface AllTheProvidersProps {
  children: React.ReactNode;
}

// All providers wrapper for tests
export function AllTheProviders({ children }: AllTheProvidersProps) {
  return (
    <AuthProvider>
      <WebSocketProvider url="ws://localhost:8000/ws">
        {children}
      </WebSocketProvider>
    </AuthProvider>
  );
}

// Custom render function that includes all providers
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options });

// Re-export everything
export * from '@testing-library/react';
export { customRender as render };

// Utility to wrap component with auth and websocket
export function withProviders(component: ReactElement) {
  return (
    <AuthProvider>
      <WebSocketProvider url="ws://localhost:8000/ws">
        {component}
      </WebSocketProvider>
    </AuthProvider>
  );
}

// Utility to wrap component with WebSocket provider only
export function withWebSocket(component: ReactElement) {
  return (
    <WebSocketProvider url="ws://localhost:8000/ws">
      {component}
    </WebSocketProvider>
  );
}

// Utility to wrap component with auth provider only
export function withAuth(component: ReactElement) {
  return <AuthProvider>{component}</AuthProvider>;
}

// Mock implementations for common hooks
export const mockUseRouter = () => ({
  push: jest.fn(),
  replace: jest.fn(),
  prefetch: jest.fn(),
  back: jest.fn(),
  pathname: '/',
  query: {},
  asPath: '/',
  route: '/',
});

export const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN,
};

// Helper to create mock WebSocket message events
export const createWebSocketMessage = (data: any) => {
  return new MessageEvent('message', {
    data: typeof data === 'string' ? data : JSON.stringify(data),
  });
};

// Helper to wait for async updates
export const waitForAsync = () => new Promise(resolve => setTimeout(resolve, 0));