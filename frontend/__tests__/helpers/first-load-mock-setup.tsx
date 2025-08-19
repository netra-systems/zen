/**
 * First Load Mock Setup
 * Centralized mock setup for first load integration tests
 * Each function ≤8 lines per architecture requirements
 */

import { jest } from '@jest/globals';

// Mock Next.js router
export const mockPush = jest.fn();
export const mockReplace = jest.fn();

export const setupFirstLoadMockComponents = () => {
  jest.mock('next/navigation', () => ({
    useRouter: jest.fn(() => ({
      push: mockPush,
      replace: mockReplace,
      pathname: '/',
      query: {},
      asPath: '/'
    }))
  }));

  // Mock auth service
  jest.mock('@/auth', () => ({
    authService: {
      useAuth: jest.fn(),
      getAuthConfig: jest.fn(),
      getToken: jest.fn(),
      handleLogin: jest.fn(),
      handleLogout: jest.fn()
    },
    AuthProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>
  }));

  // Mock WebSocket provider
  jest.mock('@/providers/WebSocketProvider', () => ({
    WebSocketProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>
  }));

  // Mock AppWithLayout
  jest.mock('@/components/AppWithLayout', () => ({
    AppWithLayout: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="app-layout">{children}</div>
    )
  }));
};