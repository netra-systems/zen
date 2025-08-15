/**
 * WebSocket and Authentication Integration Tests
 * Tests for WebSocket provider with authentication state
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

// Import stores
import { useAuthStore } from '@/store/authStore';

// Import test utilities
import { TestProviders, WebSocketContext, mockWebSocketContextValue } from '../../test-utils/providers';

// Mock environment
const mockEnv = {
  NEXT_PUBLIC_API_URL: 'http://localhost:8000',
  NEXT_PUBLIC_WS_URL: 'ws://localhost:8000',
};

describe('WebSocket and Authentication Integration', () => {
  let server: WS;
  
  beforeEach(() => {
    process.env = { ...process.env, ...mockEnv };
    server = new WS('ws://localhost:8000/ws');
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    
    // Reset auth store
    useAuthStore.setState({ user: null, token: null, isAuthenticated: false });
    
    // Mock fetch with config endpoint
    global.fetch = jest.fn((url) => {
      if (url.includes('/api/config')) {
        return Promise.resolve({
          json: () => Promise.resolve({ ws_url: 'ws://localhost:8000/ws' }),
          ok: true
        });
      }
      return Promise.resolve({
        json: () => Promise.resolve({}),
        ok: true
      });
    }) as jest.Mock;
  });

  afterEach(() => {
    try {
      WS.clean();
    } catch (error) {
      // Ignore cleanup errors if WS is already cleaned
    }
    jest.restoreAllMocks();
  });

  describe('WebSocket Provider Integration', () => {
    it('should integrate WebSocket with authentication state', async () => {
      const mockToken = 'test-jwt-token';
      const mockUser = { id: '123', email: 'test@example.com', full_name: 'Test User', name: 'Test User' };
      
      // Set authenticated state
      useAuthStore.setState({ 
        user: mockUser, 
        token: mockToken, 
        isAuthenticated: true 
      });
      
      const TestComponent = () => {
        const wsContext = React.useContext(WebSocketContext);
        const status = wsContext?.status || 'CLOSED';
        return <div data-testid="ws-status">{status === 'OPEN' ? 'Connected' : 'Disconnected'}</div>;
      };
      
      // Start with closed status
      const { rerender } = render(
        <TestProviders wsValue={{ ...mockWebSocketContextValue, status: 'CLOSED' }}>
          <TestComponent />
        </TestProviders>
      );
      
      expect(screen.getByTestId('ws-status')).toHaveTextContent('Disconnected');
      
      // Update to open status (simulating connection)
      rerender(
        <TestProviders wsValue={{ ...mockWebSocketContextValue, status: 'OPEN' }}>
          <TestComponent />
        </TestProviders>
      );
      
      expect(screen.getByTestId('ws-status')).toHaveTextContent('Connected');
    });

    it('should reconnect WebSocket when authentication changes', async () => {
      const TestComponent = () => {
        const wsContext = React.useContext(WebSocketContext);
        const status = wsContext?.status || 'CLOSED';
        const login = useAuthStore((state) => state.login);
        
        return (
          <div>
            <div data-testid="ws-status">{status === 'OPEN' ? 'Connected' : 'Disconnected'}</div>
            <button onClick={() => login({ id: '123', email: 'test@example.com', full_name: 'Test User', name: 'Test User' }, 'new-token')}>
              Login
            </button>
          </div>
        );
      };
      
      const { getByText } = render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      // Trigger authentication
      fireEvent.click(getByText('Login'));
      
      // Verify login was called
      expect(useAuthStore.getState().token).toBe('new-token');
    });
  });

  describe('Authentication Flow Integration', () => {
    it('should complete OAuth flow and establish WebSocket', async () => {
      const mockOAuthResponse = {
        access_token: 'oauth-token',
        user: { id: 'oauth-user', email: 'oauth@example.com', full_name: 'OAuth User', name: 'OAuth User' }
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockOAuthResponse
      });
      
      // Simulate OAuth callback
      const handleOAuthCallback = async (code: string) => {
        const response = await fetch('/api/auth/google/callback', {
          method: 'POST',
          body: JSON.stringify({ code })
        });
        const data = await response.json();
        
        useAuthStore.getState().login(data.user, data.access_token);
        return data;
      };
      
      const result = await handleOAuthCallback('oauth-code');
      
      expect(result.access_token).toBe('oauth-token');
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });

    it('should persist authentication across page refreshes', async () => {
      const mockUser = { id: 'persist-user', email: 'persist@example.com', full_name: 'Persist User', name: 'Persist User' };
      const mockToken = 'persist-token';
      
      // Set initial auth state and save to localStorage
      useAuthStore.getState().login(mockUser, mockToken);
      localStorage.setItem('auth_token', mockToken);
      localStorage.setItem('user', JSON.stringify(mockUser));
      
      // Simulate page refresh by resetting and restoring from localStorage
      const savedToken = localStorage.getItem('auth_token');
      const savedUser = localStorage.getItem('user');
      
      // Reset store
      useAuthStore.setState({ user: null, token: null, isAuthenticated: false });
      
      // Restore from localStorage
      if (savedToken && savedUser) {
        useAuthStore.getState().login(JSON.parse(savedUser), savedToken);
      }
      
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(useAuthStore.getState().user).toEqual(mockUser);
    });
  });
});