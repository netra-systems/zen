import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/app/contexts/AuthContext';
import * as auth from '@/services/auth';
import { mockAuthConfig, mockUser } from '@/mocks/auth';

jest.mock('@/services/auth');

const mockGetAuthConfig = auth.getAuthConfig as jest.Mock;

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
  return <button onClick={login}>Login with Google</button>;
};

describe('AuthProvider', () => {
  it('should show loading state initially', () => {
    mockGetAuthConfig.mockResolvedValueOnce(mockAuthConfig);
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('should show login button when not authenticated', async () => {
    mockGetAuthConfig.mockResolvedValueOnce(mockAuthConfig);
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    await waitFor(() => {
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });

  it('should show user info when authenticated', async () => {
    mockGetAuthConfig.mockResolvedValueOnce({ ...mockAuthConfig, user: mockUser });
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
    mockGetAuthConfig.mockResolvedValueOnce(mockAuthConfig);
    const mockLogin = jest.spyOn(auth, 'handleLogin');

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    await waitFor(() => {
        const loginButton = screen.getByText('Login with Google');
        loginButton.click();
        expect(mockLogin).toHaveBeenCalledWith(mockAuthConfig);
    });
  });
});