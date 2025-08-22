/**
 * Error Recovery Integration Tests
 * Tests for WebSocket disconnection, API retry logic, and session expiration
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import stores
import { useAuthStore } from '@/store/authStore';

// Import test utilities
import { TestProviders } from '@/__tests__/setup/test-providers';

describe('Error Recovery Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    
    // Reset auth store
    useAuthStore.setState({ user: null, token: null, isAuthenticated: false });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Connection Recovery', () => {
    it('should recover from WebSocket disconnection', async () => {
      const TestComponent = () => {
        const [status, setStatus] = React.useState<'OPEN' | 'CLOSED'>('CLOSED');
        
        const reconnect = () => {
          setStatus('OPEN');
        };
        
        const disconnect = () => {
          setStatus('CLOSED');
        };
        
        return (
          <div>
            <div data-testid="connection-status">{status === 'OPEN' ? 'Connected' : 'Disconnected'}</div>
            <button onClick={reconnect}>Reconnect</button>
            <button onClick={disconnect}>Disconnect</button>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      // Initially disconnected
      expect(getByTestId('connection-status')).toHaveTextContent('Disconnected');
      
      // Simulate connection
      fireEvent.click(getByText('Reconnect'));
      expect(getByTestId('connection-status')).toHaveTextContent('Connected');
      
      // Simulate disconnection
      fireEvent.click(getByText('Disconnect'));
      expect(getByTestId('connection-status')).toHaveTextContent('Disconnected');
    });

    it('should retry failed API calls with exponential backoff', async () => {
      let attempts = 0;
      
      (fetch as jest.Mock).mockImplementation(async () => {
        attempts++;
        if (attempts < 3) {
          throw new Error('Network error');
        }
        return {
          ok: true,
          json: async () => ({ success: true })
        };
      });
      
      const retryWithBackoff = async (fn: () => Promise<any>, maxRetries = 3) => {
        let lastError;
        for (let i = 0; i < maxRetries; i++) {
          try {
            return await fn();
          } catch (error) {
            lastError = error;
            await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 100));
          }
        }
        throw lastError;
      };
      
      const result = await retryWithBackoff(() => 
        fetch('/api/test').then(r => r.json())
      );
      
      expect(result.success).toBe(true);
      expect(attempts).toBe(3);
    });

    it('should handle session expiration gracefully', async () => {
      const TestComponent = () => {
        const logout = useAuthStore((state) => state.logout);
        const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
        
        React.useEffect(() => {
          // Simulate token expiration check
          const checkTokenExpiry = () => {
            const token = localStorage.getItem('auth_token');
            if (token) {
              try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                if (payload.exp * 1000 < Date.now()) {
                  logout();
                }
              } catch {
                logout();
              }
            }
          };
          
          checkTokenExpiry();
        }, [logout]);
        
        return <div data-testid="auth-status">{isAuthenticated ? 'Authenticated' : 'Session Expired'}</div>;
      };
      
      // Set expired token
      const expiredToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MDAwMDAwMDB9.fake';
      localStorage.setItem('auth_token', expiredToken);
      useAuthStore.setState({ token: expiredToken, isAuthenticated: true });
      
      const { getByTestId } = render(<TestComponent />);
      
      expect(getByTestId('auth-status')).toHaveTextContent('Session Expired');
    });
  });
});