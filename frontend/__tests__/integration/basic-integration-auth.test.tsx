/**
 * Authentication Integration Tests
 * Tests for login, logout, and error handling functionality
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

import { useAuthStore } from '@/store/authStore';
import { LoginComponent, LogoutComponent } from './helpers/test-components';
import { setupTestEnvironment, clearStorages, resetStores, setupGlobalFetch, cleanupWebSocket } from './helpers/test-setup';
import { createMockUser, createMockToken } from './helpers/test-builders';
import { assertTextContent, assertAuthState } from './helpers/test-assertions';

// Mock Next.js
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

describe('Authentication Integration Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    server = setupTestEnvironment();
    clearStorages();
    resetStores();
    setupGlobalFetch();
  });

  afterEach(() => {
    cleanupWebSocket();
  });

  describe('Authentication Flow', () => {
    it('should handle login and authentication', async () => {
      const mockUser = createMockUser();
      const mockToken = createMockToken();
      
      const handleLogin = async () => {
        await useAuthStore.getState().login(mockUser, mockToken);
      };
      
      const { getByText, getByTestId } = render(
        <LoginComponent onLogin={handleLogin} />
      );
      
      await assertTextContent(getByTestId('auth-status'), 'Not logged in');
      
      fireEvent.click(getByText('Login'));
      
      await assertTextContent(getByTestId('auth-status'), 'Logged in as test@example.com');
      assertAuthState(true, mockToken);
    });

    it('should handle logout and cleanup', async () => {
      const mockUser = createMockUser();
      const mockToken = createMockToken();
      
      useAuthStore.setState({
        user: mockUser,
        token: mockToken,
        isAuthenticated: true
      });
      
      const { getByText, getByTestId } = render(<LogoutComponent />);
      
      await assertTextContent(getByTestId('auth-status'), 'Logged in');
      
      fireEvent.click(getByText('Logout'));
      
      await assertTextContent(getByTestId('auth-status'), 'Logged out');
      assertAuthState(false, null);
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      const ErrorComponent = () => {
        const [error, setError] = React.useState(null);
        const [loading, setLoading] = React.useState(false);
        
        const fetchData = async () => {
          setLoading(true);
          setError(null);
          
          try {
            const response = await fetch('/api/data');
            if (!response.ok) throw new Error('Network error');
            await response.json();
          } catch (err) {
            setError(err.message);
          } finally {
            setLoading(false);
          }
        };
        
        return (
          <div>
            <button onClick={fetchData}>Fetch Data</button>
            {loading && <div data-testid="loading">Loading...</div>}
            {error && <div data-testid="error">{error}</div>}
          </div>
        );
      };
      
      (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
      
      const { getByText, getByTestId } = render(<ErrorComponent />);
      
      fireEvent.click(getByText('Fetch Data'));
      
      await assertTextContent(getByTestId('error'), 'Network error');
    });

    it('should handle WebSocket disconnection', async () => {
      const ReconnectComponent = () => {
        const [connected, setConnected] = React.useState(false);
        const [reconnectAttempts, setReconnectAttempts] = React.useState(0);
        
        const connect = () => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onopen = () => {
            setConnected(true);
            setReconnectAttempts(0);
          };
          
          ws.onclose = () => {
            setConnected(false);
            setTimeout(() => {
              setReconnectAttempts(prev => prev + 1);
              connect();
            }, 1000);
          };
          
          return ws;
        };
        
        React.useEffect(() => {
          const ws = connect();
          return () => ws.close();
        }, []);
        
        return (
          <div>
            <div data-testid="connection">
              {connected ? 'Connected' : 'Disconnected'}
            </div>
            <div data-testid="attempts">
              Reconnect attempts: {reconnectAttempts}
            </div>
          </div>
        );
      };
      
      const { getByTestId } = render(<ReconnectComponent />);
      
      await server.connected;
      await assertTextContent(getByTestId('connection'), 'Connected');
      
      server.close();
      
      await assertTextContent(getByTestId('connection'), 'Disconnected');
    });
  });
});