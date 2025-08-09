import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from '../../auth/context';
import { authService } from '../../auth/service';
import { useRouter } from 'next/navigation';

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

jest.mock('../../auth/service');

describe('Authentication Flow', () => {
  const mockRouter = {
    push: jest.fn(),
    refresh: jest.fn(),
    replace: jest.fn(),
  };

  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    localStorage.clear();
    sessionStorage.clear();
    jest.clearAllMocks();
  });

  describe('Login Flow', () => {
    it('should handle successful login with JWT token', async () => {
      const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';
      const mockUser = { id: '123', email: 'test@example.com', name: 'John Doe' };

      (authService.login as jest.Mock).mockResolvedValue({
        token: mockToken,
        user: mockUser,
      });

      const TestComponent = () => {
        const { login, isAuthenticated, user } = useAuth();
        
        return (
          <div>
            <button onClick={() => login('test@example.com', 'password123')}>
              Login
            </button>
            {isAuthenticated && <div>Welcome {user?.name}</div>}
          </div>
        );
      };

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const loginButton = screen.getByText('Login');
      await userEvent.click(loginButton);

      await waitFor(() => {
        expect(screen.getByText('Welcome John Doe')).toBeInTheDocument();
      });

      expect(localStorage.getItem('authToken')).toBe(mockToken);
      expect(mockRouter.push).toHaveBeenCalledWith('/chat');
    });

    it('should handle login failure with error message', async () => {
      (authService.login as jest.Mock).mockRejectedValue(
        new Error('Invalid credentials')
      );

      const TestComponent = () => {
        const { login, error } = useAuth();
        
        return (
          <div>
            <button onClick={() => login('test@example.com', 'wrong')}>
              Login
            </button>
            {error && <div role="alert">{error}</div>}
          </div>
        );
      };

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const loginButton = screen.getByText('Login');
      await userEvent.click(loginButton);

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent('Invalid credentials');
      });

      expect(localStorage.getItem('authToken')).toBeNull();
      expect(mockRouter.push).not.toHaveBeenCalled();
    });

    it('should validate email format before submission', async () => {
      const TestComponent = () => {
        const [email, setEmail] = React.useState('');
        const [emailError, setEmailError] = React.useState('');
        
        const validateEmail = (value: string) => {
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
          if (!emailRegex.test(value)) {
            setEmailError('Invalid email format');
          } else {
            setEmailError('');
          }
        };
        
        return (
          <div>
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                validateEmail(e.target.value);
              }}
              aria-label="Email"
            />
            {emailError && <div role="alert">{emailError}</div>}
          </div>
        );
      };

      render(<TestComponent />);

      const emailInput = screen.getByLabelText('Email');
      await userEvent.type(emailInput, 'invalid-email');

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent('Invalid email format');
      });
    });

    it('should handle session timeout and redirect to login', async () => {
      jest.useFakeTimers();
      
      const TestComponent = () => {
        const { checkSession, isAuthenticated } = useAuth();
        
        React.useEffect(() => {
          const interval = setInterval(checkSession, 60000);
          return () => clearInterval(interval);
        }, [checkSession]);
        
        return (
          <div>
            {isAuthenticated ? 'Authenticated' : 'Not authenticated'}
          </div>
        );
      };

      localStorage.setItem('authToken', 'expired-token');
      localStorage.setItem('tokenExpiry', String(Date.now() - 1000));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      jest.advanceTimersByTime(60000);

      await waitFor(() => {
        expect(screen.getByText('Not authenticated')).toBeInTheDocument();
      });

      expect(mockRouter.replace).toHaveBeenCalledWith('/login');
      jest.useRealTimers();
    });
  });

  describe('Logout Flow', () => {
    it('should clear all auth data on logout', async () => {
      const mockToken = 'valid-token';
      localStorage.setItem('authToken', mockToken);
      
      (authService.logout as jest.Mock).mockResolvedValue(undefined);

      const TestComponent = () => {
        const { logout, isAuthenticated } = useAuth();
        
        return (
          <div>
            <button onClick={logout}>Logout</button>
            {isAuthenticated ? 'Logged in' : 'Logged out'}
          </div>
        );
      };

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);

      await waitFor(() => {
        expect(screen.getByText('Logged out')).toBeInTheDocument();
      });

      expect(localStorage.getItem('authToken')).toBeNull();
      expect(mockRouter.push).toHaveBeenCalledWith('/login');
    });

    it('should disconnect WebSocket on logout', async () => {
      const mockDisconnect = jest.fn();
      
      (window as any).webSocketService = {
        disconnect: mockDisconnect,
      };

      const TestComponent = () => {
        const { logout } = useAuth();
        return <button onClick={logout}>Logout</button>;
      };

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);

      await waitFor(() => {
        expect(mockDisconnect).toHaveBeenCalled();
      });
    });
  });

  describe('Token Refresh', () => {
    it('should refresh token before expiration', async () => {
      jest.useFakeTimers();
      
      const mockNewToken = 'new-token';
      (authService.refreshToken as jest.Mock).mockResolvedValue({
        token: mockNewToken,
      });

      const TestComponent = () => {
        const { refreshToken } = useAuth();
        
        React.useEffect(() => {
          const timer = setTimeout(() => refreshToken(), 50000);
          return () => clearTimeout(timer);
        }, [refreshToken]);
        
        return <div>App</div>;
      };

      localStorage.setItem('authToken', 'old-token');
      localStorage.setItem('tokenExpiry', String(Date.now() + 60000));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      jest.advanceTimersByTime(50000);

      await waitFor(() => {
        expect(localStorage.getItem('authToken')).toBe(mockNewToken);
      });

      jest.useRealTimers();
    });

    it('should handle refresh token failure', async () => {
      (authService.refreshToken as jest.Mock).mockRejectedValue(
        new Error('Refresh failed')
      );

      const TestComponent = () => {
        const { refreshToken, error } = useAuth();
        
        return (
          <div>
            <button onClick={refreshToken}>Refresh</button>
            {error && <div role="alert">{error}</div>}
          </div>
        );
      };

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const refreshButton = screen.getByText('Refresh');
      await userEvent.click(refreshButton);

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent('Refresh failed');
      });

      expect(mockRouter.replace).toHaveBeenCalledWith('/login');
    });
  });

  describe('Protected Routes', () => {
    it('should redirect unauthenticated users to login', () => {
      const ProtectedComponent = () => {
        const { isAuthenticated } = useAuth();
        
        React.useEffect(() => {
          if (!isAuthenticated) {
            mockRouter.replace('/login');
          }
        }, [isAuthenticated]);
        
        return isAuthenticated ? <div>Protected Content</div> : null;
      };

      render(
        <AuthProvider>
          <ProtectedComponent />
        </AuthProvider>
      );

      expect(mockRouter.replace).toHaveBeenCalledWith('/login');
    });

    it('should allow authenticated users to access protected routes', async () => {
      localStorage.setItem('authToken', 'valid-token');
      
      (authService.validateToken as jest.Mock).mockResolvedValue({
        valid: true,
        user: { id: '123', email: 'test@example.com' },
      });

      const ProtectedComponent = () => {
        const { isAuthenticated } = useAuth();
        return isAuthenticated ? <div>Protected Content</div> : <div>Loading...</div>;
      };

      render(
        <AuthProvider>
          <ProtectedComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument();
      });

      expect(mockRouter.replace).not.toHaveBeenCalled();
    });
  });
});