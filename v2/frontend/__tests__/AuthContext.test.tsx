
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { AuthProvider } from '@/contexts/AuthContext';
import { authService } from '@/services/auth';
import { authService } from '@/services/auth';
import { mockUser, mockAuthConfig } from '@/mocks/auth';

// Mock the authService
jest.mock('@/services/auth');

const TestComponent = () => {
  const { user, login, logout } = authService.useAuth();
  return user ? (
    <div>
      <span>Welcome, {user.full_name}</span>
      <button onClick={logout}>Logout</button>
    </div>
  ) : (
    <button onClick={login}>Login with Google</button>
  );
};

describe('AuthProvider', () => {
  beforeEach(() => {
    // Reset the mock before each test
    (authService.getAuthConfig as jest.Mock).mockClear();
    (authService.handleLogin as jest.Mock).mockClear();
    (authService.handleLogout as jest.Mock).mockClear();
  });

  it('should show loading state initially, then login button', async () => {
    (authService.getAuthConfig as jest.Mock).mockResolvedValue(mockAuthConfig);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    expect(screen.getByText('Login with Google')).toBeInTheDocument();
  });

  it('should show user info when authenticated', async () => {
    (authService.getAuthConfig as jest.Mock).mockResolvedValue({ ...mockAuthConfig, user: mockUser });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(`Welcome, ${mockUser.full_name}`)).toBeInTheDocument();
    });
  });

  it('should call login function on button click', async () => {
    (authService.getAuthConfig as jest.Mock).mockResolvedValue(mockAuthConfig);
    const mockLogin = (authService.handleLogin as jest.Mock);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      fireEvent.click(screen.getByText('Login with Google'));
    });

    expect(mockLogin).toHaveBeenCalled();
  });

  it('should call logout function on button click', async () => {
    (authService.getAuthConfig as jest.Mock).mockResolvedValue({ ...mockAuthConfig, user: mockUser });
    const mockLogout = (authService.handleLogout as jest.Mock);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      fireEvent.click(screen.getByText('Logout'));
    });

    expect(mockLogout).toHaveBeenCalled();
  });
});
