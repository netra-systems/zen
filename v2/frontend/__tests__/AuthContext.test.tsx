
import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../app/contexts/AuthContext';
import { getAuthConfig } from '../services/auth';
import { AuthConfigResponse, User } from '@testing-library/react';

jest.mock('../services/auth');

const mockGetAuthConfig = getAuthConfig as jest.Mock;

const TestComponent = () => {
  const { user, login, logout, loading } = useAuth();
  if (loading) return <div>Loading...</div>;
  if (user) {
    return (
      <div>
        <span>Welcome, {user.full_name}</span>
        <button onClick={logout}>Logout</button>
      </div>
    );
  }
  return <button onClick={login}>Login</button>;
};

describe('AuthProvider', () => {
  it('should show loading state initially', () => {
    mockGetAuthConfig.mockResolvedValueOnce({ development_mode: true, user: null });
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('should show login button when not authenticated', async () => {
    mockGetAuthConfig.mockResolvedValueOnce({ development_mode: false, user: null });
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    await waitFor(() => {
      expect(screen.getByText('Login')).toBeInTheDocument();
    });
  });

  it('should show user info when authenticated', async () => {
    const user: User = { id: '1', email: 'test@example.com', full_name: 'Test User', is_active: true, is_superuser: false, picture: '' };
    mockGetAuthConfig.mockResolvedValueOnce({ development_mode: false, user });
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    await waitFor(() => {
      expect(screen.getByText('Welcome, Test User')).toBeInTheDocument();
    });
  });

  it('should call login function on button click', async () => {
    const login = jest.fn();
    mockGetAuthConfig.mockResolvedValueOnce({ development_mode: false, user: null, endpoints: { login: '/api/auth/login/google' } });
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    await waitFor(() => {
        const loginButton = screen.getByText('Login');
        loginButton.click();
        // Not a great way to test this, but it's a start
        expect(window.location.href).toBe('http://localhost/api/auth/login/google');
    });
  });
});
