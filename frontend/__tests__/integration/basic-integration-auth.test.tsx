/**
 * Authentication Integration Tests
 * Tests for login, logout, and error handling functionality
 */

import React from 'react';
import { render, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

import { useAuthStore } from '@/store/authStore';
import { LoginComponent, LogoutComponent } from './helpers/test-components';
import { setupTestEnvironment, clearStorages, resetStores, setupGlobalFetch, cleanupWebSocket } from './helpers/test-setup';
import { createMockUser, createMockToken, createMockAuthResponse, createAuthenticatedRequest } from './helpers/test-builders';
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
    it('should handle login and authentication with JWT token', async () => {
      const mockUser = createMockUser();
      const mockToken = createMockToken();
      const mockAuthResponse = createMockAuthResponse();
      
      // Mock fetch to return auth response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockAuthResponse)
      });
      
      const handleLogin = async () => {
        await useAuthStore.getState().login(mockUser, mockToken);
        // Verify token is stored in localStorage
        expect(localStorage.getItem('token')).toBe(mockToken);
        expect(localStorage.getItem('auth_token')).toBe(mockToken);
      };
      
      const { getByText, getByTestId } = render(
        <LoginComponent onLogin={handleLogin} />
      );
      
      await assertTextContent(getByTestId('auth-status'), 'Not logged in');
      
      await act(async () => {
        fireEvent.click(getByText('Login'));
      });
      
      await assertTextContent(getByTestId('auth-status'), 'Logged in as test@example.com');
      assertAuthState(true, mockToken);
    });

    it('should handle logout and cleanup', async () => {
      const mockUser = createMockUser();
      const mockToken = createMockToken();
      
      // Set up authenticated state
      localStorage.setItem('token', mockToken);
      localStorage.setItem('auth_token', mockToken);
      
      useAuthStore.setState({
        user: mockUser,
        token: mockToken,
        isAuthenticated: true
      });
      
      const { getByText, getByTestId } = render(<LogoutComponent />);
      
      await assertTextContent(getByTestId('auth-status'), 'Logged in');
      
      await act(async () => {
        fireEvent.click(getByText('Logout'));
      });
      
      await assertTextContent(getByTestId('auth-status'), 'Logged out');
      // Verify tokens are removed from localStorage
      expect(localStorage.getItem('token')).toBeNull();
      expect(localStorage.getItem('auth_token')).toBeNull();
      assertAuthState(false, null);
    });
  });

  describe('Error Handling', () => {
    it('should handle authenticated network requests', async () => {
      const AuthenticatedRequestComponent = () => {
        const [data, setData] = React.useState(null);
        const [error, setError] = React.useState(null);
        const [loading, setLoading] = React.useState(false);
        
        const fetchAuthenticatedData = async () => {
          setLoading(true);
          setError(null);
          
          try {
            const token = localStorage.getItem('token');
            if (!token) throw new Error('No auth token');
            
            const response = await fetch('/api/protected-data', {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            });
            
            if (!response.ok) {
              if (response.status === 401) throw new Error('Authentication failed');
              throw new Error('Request failed');
            }
            
            const result = await response.json();
            setData(result);
          } catch (err) {
            setError(err.message);
          } finally {
            setLoading(false);
          }
        };
        
        return (
          <div>
            <button onClick={fetchAuthenticatedData}>Fetch Protected Data</button>
            {loading && <div data-testid="loading">Loading...</div>}
            {error && <div data-testid="error">{error}</div>}
            {data && <div data-testid="data">Data loaded</div>}
          </div>
        );
      };
      
      // Mock successful authenticated request
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ message: 'Protected data' })
      });
      
      const { getByText, getByTestId } = render(<AuthenticatedRequestComponent />);
      
      await act(async () => {
        fireEvent.click(getByText('Fetch Protected Data'));
      });
      
      await assertTextContent(getByTestId('data'), 'Data loaded');
    });

    it('should handle authentication failures', async () => {
      const FailedAuthComponent = () => {
        const [error, setError] = React.useState(null);
        
        const fetchWithBadToken = async () => {
          try {
            const response = await fetch('/auth/verify', {
              headers: {
                'Authorization': 'Bearer invalid_token'
              }
            });
            
            if (!response.ok) throw new Error('Authentication failed');
          } catch (err) {
            setError(err.message);
          }
        };
        
        return (
          <div>
            <button onClick={fetchWithBadToken}>Test Bad Token</button>
            {error && <div data-testid="error">{error}</div>}
          </div>
        );
      };
      
      // Mock 401 response for invalid token
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ valid: false, error: 'Invalid token' })
      });
      
      const { getByText, getByTestId } = render(<FailedAuthComponent />);
      
      await act(async () => {
        fireEvent.click(getByText('Test Bad Token'));
      });
      
      await assertTextContent(getByTestId('error'), 'Authentication failed');
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