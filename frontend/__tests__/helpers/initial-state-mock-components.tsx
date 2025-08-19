/**
 * Initial State Mock Components Setup
 * Centralized mock setup for components used in initial state tests
 * Each function ≤8 lines per architecture requirements
 */

import { jest } from '@jest/globals';

export const setupInitialStateMockComponents = () => {
  // Mock Next.js
  jest.mock('next/navigation', () => ({
    useRouter: () => ({
      push: jest.fn(),
      replace: jest.fn(),
      pathname: '/',
      query: {},
      asPath: '/'
    })
  }));

  // Mock store modules
  jest.mock('@/store/app');
  jest.mock('@/store/authStore', () => ({
    useAuthStore: jest.fn(() => ({
      isAuthenticated: false,
      user: null,
      token: null,
      login: jest.fn(),
      logout: jest.fn()
    }))
  }));

  // Mock WebSocket service
  jest.mock('@/services/webSocketService', () => ({
    webSocketService: {
      connect: jest.fn(),
      disconnect: jest.fn(),
      isConnected: () => false,
      send: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn()
    }
  }));

  // Mock components
  jest.mock('@/components/chat/ChatSidebar', () => ({
    ChatSidebar: () => <div data-testid="chat-sidebar">Chat Sidebar</div>
  }));

  jest.mock('@/components/Header', () => ({
    Header: ({ toggleSidebar }: { toggleSidebar: () => void }) => (
      <div data-testid="header">
        <button onClick={toggleSidebar} data-testid="toggle-sidebar">
          Toggle Sidebar
        </button>
      </div>
    )
  }));
};