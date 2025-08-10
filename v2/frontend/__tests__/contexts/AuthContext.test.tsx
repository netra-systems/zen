import React from 'react';
import { render, waitFor, screen } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/auth/context';
import { authService } from '@/auth/service';
import { useRouter } from 'next/navigation';

// Mock dependencies
jest.mock('@/auth/service');
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  refresh: jest.fn(),
};

// Test component to access auth context
const TestComponent = () => {
  const { user, isAuthenticated, loading, login, logout } = useAuth();
  return (
    <div>
      <div data-testid="loading">{loading.toString()}</div>
      <div data-testid="isAuthenticated">{isAuthenticated.toString()}</div>
      <div data-testid="user">{user ? user.email : 'no-user'}</div>
      <button onClick={() => login('test@example.com', 'password')}>Login</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    localStorage.clear();
    
    // Initialize mocks properly
    (authService.checkAuth as jest.Mock) = jest.fn();
    (authService.handleDevLogin as jest.Mock) = jest.fn();
    (authService.login as jest.Mock) = jest.fn();
    (authService.logout as jest.Mock) = jest.fn();
  });

  describe('Auto-login in development mode', () => {
    it('should automatically login in development mode', async () => {
      const mockCheckAuth = authService.checkAuth as jest.Mock;
      const mockHandleDevLogin = authService.handleDevLogin as jest.Mock;
      
      // Mock development mode response
      mockCheckAuth.mockResolvedValue({
        authenticated: false,
        development_mode: true,
        user: null,
      });

      // Mock successful dev login
      mockHandleDevLogin.mockResolvedValue({
        access_token: 'dev-token',
        user: { id: 'dev-user', email: 'dev@example.com' },
      });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Initially loading
      expect(screen.getByTestId('loading')).toHaveTextContent('true');

      // Wait for auto-login to complete
      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      // Should be authenticated after auto-login
      expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('user')).toHaveTextContent('dev@example.com');
      expect(mockHandleDevLogin).toHaveBeenCalledWith({
        authenticated: false,
        development_mode: true,
        user: null,
      });
    });

    it('should not auto-login in production mode', async () => {
      const mockCheckAuth = authService.checkAuth as jest.Mock;
      const mockHandleDevLogin = authService.handleDevLogin as jest.Mock;
      
      // Mock production mode response
      mockCheckAuth.mockResolvedValue({
        authenticated: false,
        development_mode: false,
        user: null,
      });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      // Should not be authenticated
      expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
      expect(screen.getByTestId('user')).toHaveTextContent('no-user');
    });
  });

  describe('Normal authentication flow', () => {
    it('should handle successful login', async () => {
      const mockLogin = authService.login as jest.Mock;
      mockLogin.mockResolvedValue({
        access_token: 'test-token',
        user: { id: '123', email: 'test@example.com' },
      });

      const mockCheckAuth = authService.checkAuth as jest.Mock;
      mockCheckAuth.mockResolvedValue({
        authenticated: false,
        development_mode: false,
        user: null,
      });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      // Click login button
      screen.getByText('Login').click();

      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      });

      expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      expect(mockRouter.push).toHaveBeenCalledWith('/chat');
    });

    it('should handle logout', async () => {
      const mockCheckAuth = authService.checkAuth as jest.Mock;
      mockCheckAuth.mockResolvedValue({
        authenticated: true,
        development_mode: false,
        user: { id: '123', email: 'test@example.com' },
      });

      const mockLogout = authService.logout as jest.Mock;
      mockLogout.mockResolvedValue(undefined);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      });

      // Click logout button
      screen.getByText('Logout').click();

      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
      });

      expect(screen.getByTestId('user')).toHaveTextContent('no-user');
      expect(mockRouter.push).toHaveBeenCalledWith('/login');
    });
  });

  describe('Token persistence', () => {
    it('should restore authentication from localStorage', async () => {
      // Set token in localStorage
      localStorage.setItem('access_token', 'stored-token');

      const mockCheckAuth = authService.checkAuth as jest.Mock;
      mockCheckAuth.mockResolvedValue({
        authenticated: true,
        development_mode: false,
        user: { id: '123', email: 'stored@example.com' },
      });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('user')).toHaveTextContent('stored@example.com');
    });
  });
});